# 블럭 분할 모델

`wapul-ml/` — 풀이 코드를 문장 단위로 나누고, 문장마다 종류를 붙이고, 로직 문장을 블럭으로 묶는 모델.

## 하는 일

코드를 tree-sitter AST의 **문장 단위**로 나눈 뒤 두 가지를 예측합니다.

| 단계 | 출력 |
|------|------|
| 종류 분류 | 문장마다 `input` / `output` / `logic` / `none` |
| 블럭 묶기 | `logic` 문장마다 로직 블럭 번호. 같은 블럭이 떨어져 있을 수 있음 |

라벨 기준은 데이터 저장소의 라벨링 가이드(`data/docs/labeling-guide.md`)를 따릅니다. 설계와 참고 연구는 [설계](design.md)에 있습니다.

## 구조

```
wapul-ml/
├── wapul_ml/
│   ├── normalize.py   # 코드 정규화 (입력 형식)
│   ├── units.py       # 문장 단위 분할 (입력 형식)
│   ├── ast_features.py # 문장별 AST 정보 (변수 흐름, 감싸는 제어문, 문장 범주)
│   ├── data.py        # 라벨과 corpus를 문장 단위 데이터로 불러오기
│   ├── metrics.py     # 블럭 묶기 평가 지표
│   ├── baseline.py    # 분류기 학습과 교차 검증
│   ├── learning_curve.py # 라벨 수에 따른 효과와 평가 잡음
│   ├── tsdae.py       # 라벨 없는 corpus로 임베딩 도메인 적응 (검토 후 제외)
│   └── contrastive.py # 라벨 쌍으로 임베딩 대조 학습 (SetFit식)
├── Dockerfile         # 실험 실행 환경
└── data/              # 비공개 데이터 저장소 (git에서 무시)
```

`data/`는 비공개 저장소 `wapul-data-private`를 clone한 것입니다. 원본 풀이, 출처, corpus 생성 스크립트, 라벨이 들어 있고 모노레포에는 올리지 않습니다. 준비 방법은 그 저장소의 README를 따릅니다.

## 입력 형식은 학습과 추론이 같아야 한다

모델에 들어가는 코드는 학습 때와 똑같이 **`normalize()` → `units()`**를 거쳐야 합니다. 줄바꿈, 보이지 않는 문자, 줄 끝 공백이 다르면 문장 위치와 텍스트가 학습 데이터와 달라집니다.

- 원본은 `wapul_ml/normalize.py`와 `wapul_ml/units.py` 하나뿐입니다. 데이터 저장소의 스크립트도 이 파일을 가져다 씁니다.
- 두 파일은 데이터에 대한 정보를 담지 않습니다. 출처나 작성자가 드러나는 코드는 데이터 저장소에 둡니다.
- 둘 중 하나를 고치면 데이터 저장소에서 아래를 다시 돌려, corpus와 `labels/labels.jsonl`이 그대로인지 확인합니다. 달라지면 기존 라벨과 문장 단위가 어긋난 것입니다.

```bash
cd wapul-ml/data
python scripts/build_corpus.py
python scripts/sample_for_labeling.py
uv run scripts/finalize_labels.py
git status labels/
```

## 실행

실험은 Docker에서 GPU로 돌립니다. 이미지에는 PyTorch와 의존성만 들어 있고, 코드와 데이터는 실행할 때 마운트합니다.

```bash
cd wapul-ml
docker build -t wapul-ml .
docker run --rm --gpus all \
  -v "$(pwd):/work" \
  -v wapul-hf:/root/.cache/huggingface \
  wapul-ml python -m wapul_ml.baseline
```

- 같은 방식으로 다른 모듈을 돌립니다.
  - `python -m wapul_ml.baseline --model <모델 이름 또는 models/ 경로>`: 임베딩 모델 바꾸기
  - `python -m wapul_ml.baseline --sweep`: α마다 테스트 점수도 출력 (분석용)
  - `python -m wapul_ml.baseline --setfit`: fold마다 대조 학습한 모델로 평가
  - `python -m wapul_ml.tsdae --model intfloat/e5-base-v2`: 도메인 적응 모델을 `models/`에 저장
- 학습한 모델은 `wapul-ml/models/`에 저장됩니다(git에서 무시).
- Windows Git Bash에서는 `/work` 같은 경로가 Windows 경로로 바뀌어 마운트가 깨집니다. 명령 앞에 `MSYS_NO_PATHCONV=1`을 붙입니다. PowerShell에서는 `-v "${PWD}:/work"`로 씁니다.
- `wapul-hf` 볼륨에 임베딩 모델 가중치가 남아서 두 번째부터는 다시 받지 않습니다.
- 문장 임베딩은 `wapul-ml/cache/`에 저장됩니다(git에서 무시). 같은 모델과 입력이면 다시 계산하지 않습니다.
- Windows 호스트에서는 애플리케이션 제어 정책이 PyTorch DLL을 막을 수 있어서, 호스트 Python 대신 Docker를 씁니다.
- GPU 드라이버가 지원하는 CUDA보다 높은 버전의 이미지는 돌지 않습니다. `nvidia-smi`의 `CUDA Version`을 넘지 않는 태그를 고릅니다.

## 평가

사람이 검토한 풀이(`source: human`)만 채점합니다. 학습에는 LLM 초안(`source: auto`)도 씁니다. 풀이 단위 5-fold 교차 검증입니다.

| 대상 | 지표 |
|------|------|
| 종류 분류 | 문장 단위 macro-F1 |
| 블럭 묶기 | B³, CEAF-e, 같은 블럭 쌍 F1 |

블럭은 떨어져 있을 수 있어서 텍스트 분할 지표(Pk, WindowDiff)는 쓰지 않습니다. MUC는 한 문장짜리 블럭을 무시하고 블럭을 적게 만들수록 점수가 오르므로 쓰지 않습니다.

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
│   ├── normalize.py       # 코드 정규화 (입력 형식)
│   ├── units.py           # 문장 단위 분할 (입력 형식)
│   ├── ast_features.py    # 문장별 AST 정보 (변수 흐름, 감싸는 제어문, 문장 범주)
│   ├── data.py            # 라벨과 corpus를 문장 단위 데이터로 불러오기
│   ├── metrics.py         # 블럭 묶기 평가 지표
│   ├── codeseg.py         # 종류 분류: CodeBERT 미세조정과 교차 검증
│   ├── disentangle_ast.py # 블럭 묶기: 후보 중 고르기, 점수기 비교와 교차 검증
│   ├── model.py           # 최종 모델: 학습, 예측, 검토 화면
│   ├── baseline.py        # 비교 기준: 쌍 분류 + α 군집, 전체(end to end) 교차 검증
│   └── cpu_time.py        # 최종 모델의 CPU 추론 시간
├── models/                # 학습한 모델 (git에서 무시)
├── Dockerfile             # 실험 실행 환경
└── data/                  # 비공개 데이터 저장소 (git에서 무시)
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
  - `python -m wapul_ml.codeseg`: 종류 분류 교차 검증
  - `python -m wapul_ml.disentangle_ast [blocks-ensemble | blocks-mlp | blocks-lgbm | mlp | lgbm | ensemble]`: 블럭 묶기 교차 검증
  - `python -m wapul_ml.baseline [--sweep] [--pair-features structural]`: 비교 기준과 전체 점수
  - `python -m wapul_ml.cpu_time`: CPU 추론 시간. `--gpus all` 없이 돌립니다
- 서로 다른 실험은 순서대로 돌립니다. 컨테이너마다 PyTorch와 LightGBM이 CPU 코어를 전부 쓰려 해서, 동시에 띄우면 서로 느려집니다.

### 최종 모델

```bash
python -m wapul_ml.model train                    # 라벨 전체로 학습해 models/segmenter-v1/에 저장
python -m wapul_ml.model predict FILE LANGUAGE    # 파일 하나의 문장 라벨을 JSON으로 출력
python -m wapul_ml.model review [N]               # 라벨 없는 corpus 풀이 N개를 cache/review.html로
```

- 학습한 모델은 `models/segmenter-vN/`에 저장됩니다(git에서 무시). 다시 학습할 때는 `model.py`의 버전을 올립니다. 이미 모델이 있는 폴더에는 `train`이 저장하지 않습니다.
- `models/` 아래의 학습된 모델은 지우지 않고 옮깁니다. git에서 무시되어 지우면 되돌릴 수 없습니다.
- `predict`는 `labels.jsonl`과 같은 형식으로, 문장마다 `start` / `end`(줄은 1부터, 열은 0부터 글자 단위, 끝은 포함하지 않음), `kind`, logic이면 `block`(1부터)을 냅니다. 같은 블럭 번호가 떨어져 있을 수 있습니다.
- `cache/review.html`은 비공개 데이터를 담으므로 로컬에서만 엽니다(예: `cd cache && python -m http.server 8765 --bind 127.0.0.1`).
- Windows Git Bash에서는 `/work` 같은 경로가 Windows 경로로 바뀌어 마운트가 깨집니다. 명령 앞에 `MSYS_NO_PATHCONV=1`을 붙입니다. PowerShell에서는 `-v "${PWD}:/work"`로 씁니다.
- `wapul-hf` 볼륨에 임베딩 모델 가중치가 남아서 두 번째부터는 다시 받지 않습니다.
- 문장 임베딩과 실행 로그는 `wapul-ml/cache/`에 저장됩니다(git에서 무시). 같은 모델과 입력이면 임베딩을 다시 계산하지 않습니다.
- Windows 호스트에서는 애플리케이션 제어 정책이 PyTorch DLL을 막을 수 있어서, 호스트 Python 대신 Docker를 씁니다.
- GPU 드라이버가 지원하는 CUDA보다 높은 버전의 이미지는 돌지 않습니다. `nvidia-smi`의 `CUDA Version`을 넘지 않는 태그를 고릅니다.

## 평가

사람이 검토한 풀이(`source: human`)만 채점합니다. 풀이 단위 5-fold 교차 검증이고, 임계값이나 조기 종료처럼 고르는 값은 학습 풀이에서 떼어 낸 dev로만 정합니다.

| 대상 | 지표 |
|------|------|
| 종류 분류 | 문장 단위 macro-F1 |
| 블럭 묶기 | B³, CEAF-e, 같은 블럭 쌍 F1 |

블럭은 떨어져 있을 수 있어서 텍스트 분할 지표(Pk, WindowDiff)는 쓰지 않습니다. MUC는 한 문장짜리 블럭을 무시하고 블럭을 적게 만들수록 점수가 오르므로 쓰지 않습니다.

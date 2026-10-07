# 배포

wapul-ml에서 학습한 모델을 다른 시스템이 WASM으로 쓰게 하는 구성입니다. `segmenter-v3`에서 실험합니다. `segmenter-v2`는 모델 경량화 실험의 결과로 고정되어 있고, 이 구성의 대상이 아닙니다.

아래 결정은 검토를 마친 것입니다. 바꾸려면 "다시 볼 조건"에 해당하는지 먼저 확인합니다.

## 구성

```
wapul/
├── wapul-seg/                  # 배포 패키지 소스
│   ├── src/                    # Rust → WASM: 문장 나누기부터 블럭 묶기까지
│   ├── js/                     # JS: 정규화, 파싱, 트리 넘기기, WASM 호출
│   └── model/                  # wapul-ml에서 학습한 모델 파일 (사람이 커밋)
└── wapul-fe/SEGMENTER_VERSION  # 프론트엔드가 쓰는 릴리즈 버전 (seg-vX.Y.Z)
```

```
segment(code, language)                                           ← 프론트엔드가 부르는 함수 하나
  │
  ├─ JS    normalize(code)
  ├─ JS    web-tree-sitter로 파싱 (그 언어의 문법 .wasm을 처음 쓸 때 받음)
  ├─ JS    트리를 typed array로 펼침 (위치는 UTF-8 바이트)
  │
  ├─ WASM  트리 재구성 → 문장 나누기 → AST 정보 → 종류 특징 → 종류 분류(LightGBM)
  ├─ WASM  블럭 후보 특징 → 블럭 점수(LightGBM) → 블럭 묶기
  │
  └─ 결과  문장마다 {start, end, kind, block?}  (labels.jsonl과 같은 형식)
```

## 경계

| 단계 | 위치 | 이유 |
|------|------|------|
| `normalize` | JS (`wapul-seg/js/`) | 파싱 전에 돌아야 하고 파싱이 JS에 있음. 깨진 한글 복구는 브라우저 내장 `TextDecoder("euc-kr")`(웹 표준에서 CP949 전체)로 되어, WASM에 인코딩 표를 넣지 않아도 됨 |
| 파싱 | JS, web-tree-sitter | 아래 "하지 않는 것"의 첫 줄 참고 |
| 트리 펼치기 | JS | 파싱한 쪽에서 한 번에 펼쳐야 경계를 한 번만 넘음 |
| 문장 나누기, 특징, 추론, 블럭 묶기 | WASM (`wapul-seg/src/`) | 모델 로직은 한 벌만 둠 |
| 모델 | WASM 안 | 아래 "모델" 참고 |

- 프론트엔드는 `segment(code, language)` 하나만 부릅니다. JS 쪽 코드는 문법 버전, WASM과 짝이 맞아야 하므로 프론트엔드가 아니라 `wapul-seg/js/`에 두고 같은 릴리즈로 배포합니다.
- 입력 형식의 원본은 여전히 wapul-ml의 `normalize.py`와 `units.py`입니다. JS의 `normalize`와 WASM의 문장 나누기는 사본이고, 아래 "검증"을 통과해야 합니다.

## 모델

- wapul-ml에서 학습한 LightGBM 텍스트 모델 파일을 `wapul-seg/model/`에 커밋하고, 빌드할 때 WASM 안에 넣습니다(`include_bytes!`). 처음 `segment`를 부를 때 한 번 읽어 둡니다.
- 모델 버전은 릴리즈 버전과 같습니다. 모델과 로직이 항상 짝이 맞고, 프론트엔드가 받는 파일이 하나 줄어듭니다.
- 모델을 바꾸면 WASM을 다시 빌드해야 하지만, `wapul-seg/`가 바뀌면 CI가 어차피 다시 빌드합니다.
- 학습에는 비공개 데이터가 필요해서 CI는 학습하지 않고 빌드만 합니다.

## 트리 넘기기

파싱한 트리를 전위 순회해 노드마다 아래 값을 열 단위 typed array에 담고, WASM의 함수 하나에 원본 코드와 함께 넘깁니다.

| 열 | 형식 | 내용 |
|----|------|------|
| `kind` | `Uint16Array` | 문법의 노드 종류 번호 |
| `field` | `Uint16Array` | 부모 안에서의 필드 번호, 없으면 0 |
| `parent` | `Uint32Array` | 부모 노드 순번, 루트는 `0xFFFFFFFF` |
| `start`, `end` | `Uint32Array` | 정규화한 코드의 UTF-8 바이트 위치 |
| `named` | `Uint8Array` | named 노드면 1 |

- 종류와 필드의 번호 → 이름 대응표는 언어마다 한 번만 넘깁니다. Rust 쪽은 이름으로 비교합니다.
- 경계는 wasm-bindgen의 슬라이스 인자(`&[u16]`, `&[u32]` 등)로 넘습니다. typed array가 한 번에 복사되며, 추가 라이브러리를 쓰지 않습니다.
- web-tree-sitter가 UTF-16 위치를 주면 펼칠 때 UTF-8 바이트로 바꿉니다.
- 결과(문장마다 종류와 블럭)처럼 작은 값은 `tsify`로 TypeScript 타입과 함께 돌려줍니다.
- Rust 쪽은 이 배열 위에 지금 파이썬 코드가 쓰는 노드 기능(`type`, `children`, `named_children`, `parent`, `child_by_field_name`, `field_name_for_child`, `descendant_for_byte_range`, `text`)만 구현합니다.

## 검증

릴리즈 패키지를 **Node에서 그대로** 돌려 corpus 전체를 파이썬 구현과 비교합니다. 브라우저와 같은 JS, 같은 WASM, 같은 문법 파일을 쓰므로 여기서 같으면 브라우저에서도 같습니다.

| 비교 | 파이썬 쪽 | 같아야 하는 것 |
|------|-----------|----------------|
| `normalize` | `normalize.py` | 결과 문자열 |
| 파싱 | py-tree-sitter (같은 문법 버전)로 펼친 배열 | 트리 배열 |
| 문장 나누기 | `units.py` | 문장 위치 |
| 종류 특징, 예측 | `kind_features.py`, LightGBM | 특징 사전, 예측 점수(오차 1e-9) |
| 블럭 | `BlockCandidates`, LightGBM | 블럭 번호 |

두 구현이 조용히 어긋나면 성능이 떨어져도 드러나지 않으므로, 이 비교는 릴리즈 전에 반드시 통과해야 합니다.

## 결정

| 항목 | 결정 | 이유 |
|------|------|------|
| 로직 언어 | Rust → `wasm32-unknown-unknown` | GC 런타임을 함께 올리는 방식(Pyodide 등)보다 작음 |
| 파서 | web-tree-sitter, 파이썬과 같은 문법 버전 (cpp 0.23.4, java 0.23.5, python 0.25.0, rust 0.24.2) | 라벨이 tree-sitter 문장 단위에 붙어 있음 |
| 문법 파일 | 위 버전 태그에서 tree-sitter CLI로 직접 빌드한 언어별 `.wasm` | 미리 빌드된 배포본은 버전이 다를 수 있음. 고른 언어만 받으면 됨 |
| 트리 넘기기 | 평평한 typed array, 한 번의 호출 | 노드를 하나씩 경계 너머로 읽으면 노드 수만큼 호출이 생김. 배열 몇 개의 대량 복사는 우리 크기(노드 수천 개)에서 1ms 안팎 |
| LightGBM 추론 | [bosk](https://github.com/stanwarp/bosk)(Apache-2.0 / MIT)의 순수 Rust 텍스트 모델 파서를 가져와 다중 클래스와 희소 입력을 더함 | LightGBM과 예측이 같도록 검증된 구현. 원본은 다중 클래스를 거부하고 밀집 입력만 받음. 만든 사람이 한 명이라 의존성 대신 저장소로 가져옴 |
| 종류 특징 | 글자 n-gram 추가 | 학습하지 않은 언어(Rust)에서 macro-F1 0.663 → 0.870 ([실험 23](experiments.md)) |
| 배포물 | GitHub Release `seg-vX.Y.Z`: JS 모듈, `wapul-seg` WASM(모델 포함), web-tree-sitter 런타임, 언어별 문법 `.wasm` | 바이너리를 git 기록에 쌓지 않고, 프론트엔드가 버전을 고정할 수 있음 |
| 버전 | CI가 계산. 손으로 올리지 않음 | 백엔드, 프론트엔드와 같은 규칙 |
| 프론트엔드가 받는 시점 | 빌드할 때, `SEGMENTER_VERSION`에 적힌 릴리즈 | 릴리즈 파일 주소는 다른 도메인으로 리다이렉트되어 브라우저 `fetch`가 CORS에 막힐 수 있고, 실행 중 GitHub 의존을 피함 |
| 학습 | wapul-ml의 파이썬 그대로 | `wapul-seg`는 파이썬 구현과 같은 결과를 내는 배포용 사본. 일치는 "검증"으로 보장 |

## 하지 않는 것

| 하지 않는 것 | 이유 | 다시 볼 조건 |
|--------------|------|--------------|
| tree-sitter와 문법 C 코드를 Rust WASM 안에 같이 컴파일 | C → `wasm32-unknown-unknown` 빌드에 clang과 sysroot가 필요함. 현재 이 빌드는 외부 스캐너의 문자 판별이 ASCII 전용이고 할당기가 범용이 아님([tree-sitter #5851](https://github.com/tree-sitter/tree-sitter/pull/5851)). 모든 문법이 한 파일에 들어가 언어별로 나눠 받을 수 없음 | tree-sitter 0.27에서 #5851이 들어가고, 문법을 별도 WASM 모듈로 불러올 수 있게 될 때 |
| 노드 단위로 JS 트리를 읽는 바인딩 (`tree-sitter-facade`, `web-tree-sitter-sys`) | 노드 하나, 필드 하나마다 경계 호출이 생김 | 없음 |
| `serde-wasm-bindgen`, JSON으로 트리 넘기기 | 객체를 필드 단위로 읽거나 텍스트로 바꿔 느림 | 없음 |
| Apache Arrow, FlatBuffers 등 직렬화 형식 | 우리 트리는 숫자 열 몇 개라 typed array로 충분하고, 라이브러리가 WASM과 JS 번들을 키움 | 넘길 구조가 복잡해질 때 |
| `normalize`를 WASM에 두기 | 파싱(JS) 전에 돌아야 해 WASM을 한 번 더 오가고, 깨진 한글 복구에 CP949 표(`encoding_rs`)가 WASM에 들어가 수백 KB 커짐 | 없음 |
| ONNX | LightGBM 트리를 실행할 수 있는 브라우저 런타임은 ONNX Runtime Web(13.6MB)뿐이고, tract는 ONNX-ML 트리를 실행하지 못함 | 신경망 모델을 다시 쓰게 될 때 |
| Pyodide 등 파이썬을 브라우저에서 실행 | GC 런타임째 받아야 하고, Pyodide의 tree-sitter는 0.23.2에 C++·Rust 문법이 없음 | 없음 |
| 문장 나누기, 특징, 추론을 JS/TS로 작성 | 사본이 커지고 Rust와 JS 두 벌을 맞춰야 함. JS에는 정규화와 트리 펼치기만 둠 | 없음 |
| 모델 파일을 WASM 밖에 따로 두기 | 모델과 로직의 짝이 어긋날 수 있음 | 모델만 자주 바뀌어 WASM 빌드가 부담이 될 때 |
| 실행 중에 릴리즈에서 받기 | 위 "프론트엔드가 받는 시점" 참고 | 없음 |
| 파이썬에서 wasmtime으로 WASM 실행 | wasm-bindgen 출력은 JS 연결 코드를 전제로 해 다른 호스트에서 바로 부르기 어려움. 검증은 Node로 함 | 백엔드가 서버에서 모델을 돌려야 할 때. 이때는 WASM에 JS 없이 부를 수 있는 함수를 따로 내보냄 |

## 정하지 않은 것

- **모델의 특징 이름을 해시로 바꿀지.** 저장소가 공개라 릴리즈의 모델 파일도 공개됩니다. 종류 분류 모델의 특징 이름에는 학습 풀이의 식별자 토큰과 n-gram이 들어 있습니다.

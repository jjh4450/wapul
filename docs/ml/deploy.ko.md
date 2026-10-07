# 배포

wapul-ml에서 학습한 모델을 다른 시스템(프론트엔드, 백엔드)이 WASM으로 쓰게 하는 구성입니다. `segmenter-v3`에서 실험합니다. `segmenter-v2`는 모델 경량화 실험의 결과로 고정되어 있고, 이 구성의 대상이 아닙니다.

아래 결정은 검토를 마친 것입니다. 바꾸려면 "다시 볼 조건"에 해당하는지 먼저 확인합니다.

## 구성

```
wapul/
├── wapul-seg/                  # Rust 크레이트: 문장 나누기, 특징, 추론, 블럭 묶기
│   └── model/                  # wapul-ml에서 학습한 모델 파일 (사람이 커밋)
└── wapul-fe/SEGMENTER_VERSION  # 프론트엔드가 쓰는 릴리즈 버전 (seg-vX.Y.Z)
```

```
브라우저:  코드 → web-tree-sitter (언어별 문법 .wasm) → 평평한 트리 배열 ─┐
                                                                         ├→ wapul-seg WASM → 문장 종류, 로직 블럭
파이썬:    코드 → py-tree-sitter                      → 평평한 트리 배열 ─┘   (파이썬은 wasmtime으로 실행)
```

- **파싱은 각 환경의 tree-sitter가 합니다.** 브라우저는 web-tree-sitter, 파이썬(백엔드, 학습)은 py-tree-sitter입니다.
- **로직은 `wapul-seg` WASM 하나입니다.** 문장 나누기, 특징, LightGBM 추론, 블럭 묶기가 모두 여기 있고, 어느 환경에서나 같은 바이너리가 돕니다.
- **둘 사이는 평평한 트리 배열로 한 번에 넘깁니다.** 아래 "트리 넘기기"를 따릅니다.

## 트리 넘기기

파싱한 트리를 전위 순회해 노드마다 아래 값을 열 단위 typed array에 담고, `wapul-seg`의 함수 하나에 원본 코드와 함께 넘깁니다.

| 열 | 형식 | 내용 |
|----|------|------|
| `kind` | `Uint16Array` | 문법의 노드 종류 번호 |
| `field` | `Uint16Array` | 부모 안에서의 필드 번호, 없으면 0 |
| `parent` | `Uint32Array` | 부모 노드 순번, 루트는 `0xFFFFFFFF` |
| `start`, `end` | `Uint32Array` | 원본 코드의 UTF-8 바이트 위치 |
| `named` | `Uint8Array` | named 노드면 1 |

- 종류와 필드의 번호 → 이름 대응표는 언어마다 한 번만 넘깁니다. Rust 쪽은 이름으로 비교합니다.
- 경계는 wasm-bindgen의 슬라이스 인자(`&[u16]`, `&[u32]` 등)로 넘습니다. typed array가 한 번에 복사되며, 추가 라이브러리를 쓰지 않습니다.
- 위치는 넘기기 전에 UTF-8 바이트로 맞춥니다. web-tree-sitter가 UTF-16 위치를 주면 JS 쪽에서 한 번 변환합니다.
- Rust 쪽은 이 배열 위에 지금 파이썬 코드가 쓰는 노드 기능(`type`, `children`, `named_children`, `parent`, `child_by_field_name`, `field_name_for_child`, `descendant_for_byte_range`, `text`)만 구현합니다.

## 결정

| 항목 | 결정 | 이유 |
|------|------|------|
| 로직 언어 | Rust → `wasm32-unknown-unknown` | GC 런타임을 함께 올리는 방식(Pyodide 등)보다 작음. 같은 바이너리를 브라우저와 파이썬(wasmtime)이 함께 씀 |
| 파서 | 각 환경의 tree-sitter, 파이썬과 같은 문법 버전 (cpp 0.23.4, java 0.23.5, python 0.25.0, rust 0.24.2) | 라벨이 tree-sitter 문장 단위에 붙어 있음 |
| 브라우저 문법 | 위 버전 태그에서 tree-sitter CLI로 직접 빌드한 `.wasm`, 언어별 파일 | 미리 빌드된 배포본은 버전이 다를 수 있음. 고른 언어만 받으면 됨 |
| 트리 넘기기 | 평평한 typed array, 한 번의 호출 | 노드를 하나씩 경계 너머로 읽으면 노드 수만큼 호출이 생김. 배열 몇 개의 대량 복사는 우리 크기(노드 수천 개)에서 1ms 안팎 |
| LightGBM 추론 | [bosk](https://github.com/stanwarp/bosk)(Apache-2.0 / MIT)의 순수 Rust 텍스트 모델 파서를 가져와 다중 클래스와 희소 입력을 더함 | LightGBM과 예측이 같도록 검증된 구현. 원본은 다중 클래스를 거부하고 밀집 입력만 받음. 만든 사람이 한 명이라 의존성 대신 저장소로 가져옴 |
| 모델 형식 | LightGBM 텍스트 모델을 그대로 읽음 | 아래 "하지 않는 것"의 ONNX 참고 |
| 종류 특징 | 글자 n-gram 추가 | 학습하지 않은 언어(Rust)에서 macro-F1 0.663 → 0.870 ([실험 23](experiments.md)) |
| 배포물 | GitHub Release `seg-vX.Y.Z`: `wapul-seg` WASM과 JS 연결 코드, 언어별 문법 `.wasm` | 바이너리를 git 기록에 쌓지 않고, 프론트엔드가 버전을 고정할 수 있음 |
| 버전 | CI가 계산. 손으로 올리지 않음 | 백엔드, 프론트엔드와 같은 규칙 |
| 프론트엔드가 받는 시점 | 빌드할 때, `SEGMENTER_VERSION`에 적힌 릴리즈 | 릴리즈 파일 주소는 다른 도메인으로 리다이렉트되어 브라우저 `fetch`가 CORS에 막힐 수 있고, 실행 중 GitHub 의존을 피함 |
| 모델 파일 | wapul-ml에서 학습해 `wapul-seg/model/`에 사람이 커밋 | 학습에 비공개 데이터가 필요해 CI는 학습하지 않고 빌드만 함 |
| 검증 | corpus 전체에서 web-tree-sitter와 py-tree-sitter의 트리 배열이 같은지, `wapul-seg`의 문장 단위·특징·예측이 파이썬 구현과 같은지 비교 | 두 구현이 조용히 어긋나면 성능이 떨어져도 드러나지 않음 |

## 하지 않는 것

| 하지 않는 것 | 이유 | 다시 볼 조건 |
|--------------|------|--------------|
| tree-sitter와 문법 C 코드를 Rust WASM 안에 같이 컴파일 | C → `wasm32-unknown-unknown` 빌드에 clang과 sysroot가 필요함. 현재 이 빌드는 외부 스캐너의 문자 판별이 ASCII 전용이고 할당기가 범용이 아님([tree-sitter #5851](https://github.com/tree-sitter/tree-sitter/pull/5851)). 모든 문법이 한 파일에 들어가 언어별로 나눠 받을 수 없음 | tree-sitter 0.27에서 #5851이 들어가고, 문법을 별도 WASM 모듈로 불러올 수 있게 될 때 |
| 노드 단위로 JS 트리를 읽는 바인딩 (`tree-sitter-facade`, `web-tree-sitter-sys`) | 노드 하나, 필드 하나마다 경계 호출이 생김 | 없음 |
| `serde-wasm-bindgen`, JSON으로 트리 넘기기 | 객체를 필드 단위로 읽거나 텍스트로 바꿔 느림. 결과(문장마다 종류와 블럭)처럼 작은 값은 `tsify`(내부적으로 `serde-wasm-bindgen`)로 넘겨도 됨 | 없음 |
| Apache Arrow, FlatBuffers 등 직렬화 형식 | 우리 트리는 숫자 열 몇 개라 typed array로 충분하고, 라이브러리가 WASM과 JS 번들을 키움 | 넘길 구조가 복잡해질 때 |
| ONNX | LightGBM 트리를 실행할 수 있는 브라우저 런타임은 ONNX Runtime Web(13.6MB)뿐이고, tract는 ONNX-ML 트리를 실행하지 못함 | 신경망 모델을 다시 쓰게 될 때 |
| Pyodide 등 파이썬을 브라우저에서 실행 | GC 런타임째 받아야 하고, Pyodide의 tree-sitter는 0.23.2에 C++·Rust 문법이 없음 | 없음 |
| 분석 로직을 JS/TS로 작성 | 학습(파이썬)과 추론(JS) 두 벌 구현이 됨 | 없음 |
| 실행 중에 릴리즈에서 받기 | 위 "프론트엔드가 받는 시점" 참고 | 없음 |

## 정하지 않은 것

- **모델의 특징 이름을 해시로 바꿀지.** 저장소가 공개라 릴리즈의 모델 파일도 공개됩니다. 종류 분류 모델의 특징 이름에는 학습 풀이의 식별자 토큰과 n-gram이 들어 있습니다.
- **학습도 `wapul-seg`의 특징 코드를 쓸지.** 쓰면 특징 코드가 한 벌이 되고, 쓰지 않으면 `wapul-seg`는 파이썬 구현과 같은 결과를 내는 배포용 사본이 됩니다.
- **모델 파일을 WASM에 넣을지, 릴리즈에 따로 올릴지.** 넣으면 로직과 모델이 항상 짝이 맞고, 따로 두면 모델만 바꿀 때 WASM을 다시 빌드하지 않아도 됩니다.

# 배포

wapul-ml에서 학습한 모델을 브라우저가 쓰게 하는 구성입니다. `segmenter-v3`가 대상입니다. `segmenter-v2`는 모델 경량화 실험의 결과로 고정되어 있고, 이 구성의 대상이 아닙니다.

아래 결정은 검토를 마친 것입니다. 바꾸려면 "다시 볼 조건"에 해당하는지 먼저 확인합니다.

## 구성

```
wapul/
├── model/                      # 출시할 모델 파일 (wapul-ml에서 학습, 사람이 커밋)
├── wapul-seg/
│   ├── js/                     # TS (vite 라이브러리): segment(), 파싱, 문장 나누기, 특징
│   └── src/                    # Rust → WASM: 특징을 받아 종류와 블럭을 돌려줌
└── wapul-fe/package.json       # 프론트엔드가 쓰는 버전: 의존성 wapul-seg@X.Y.Z
```

```mermaid
flowchart TB
    call["segment(code, language)<br/>프론트엔드가 부르는 함수 하나"]
    subgraph ts["TS (js/)"]
        direction TB
        n["normalize(code)"]
        p["web-tree-sitter 파싱<br/>문법 .wasm은 언어마다 처음 쓸 때 받음"]
        u["문장 나누기 → 문장별 AST 정보 → 종류 특징 이름"]
        f["로직 문장의 own 특징과 쌍(pair) 특징"]
    end
    subgraph wasm["WASM (src/)"]
        direction TB
        k["kinds(특징) → 문장마다 종류<br/>LightGBM"]
        b["blocks(own, pairs) → 로직 문장마다 블럭 번호<br/>후보 행 → LightGBM 점수 → 묶기"]
    end
    model[("모델 파일 (model/)<br/>처음 쓸 때 받아 WASM에 넘김")]
    out["문장마다 {start, end, kind, block?}<br/>labels.jsonl과 같은 형식"]

    call --> n --> p --> u --> k --> f --> b --> out
    model -.-> k
    model -.-> b
```

## 쓰기

```ts
// pnpm add wapul-seg. 패키지의 dist/(아래)를 정적 파일 /seg/ 아래에 복사해 두었을 때
import { segment, fetchAssets } from 'wapul-seg';

const labeled = await segment(code, 'cpp', fetchAssets('/seg/'));
// [{ start: [1, 0], end: [1, 19], kind: 'none' }, ..., { start: [7, 4], end: [7, 25], kind: 'logic', block: 2 }, ...]
```

- 패키지는 npm의 `wapul-seg`입니다. 모듈과 타입 선언 외에 WASM, 문법 `.wasm`, 모델 파일이 `dist/`에 그대로 들어 있고 `wapul-seg/grammars/tree-sitter-cpp.wasm`처럼 경로로 import할 수 있습니다. 이 파일들은 번들에 못 들어가므로 프론트엔드 빌드가 정적 파일로 복사해야 합니다.
- `assets`는 그 파일들이 있는 곳입니다. 생략하면 모듈 파일과 같은 폴더를 씁니다(번들러를 거치면 맞지 않으므로 보통 넘깁니다). 처음 부를 때 WASM, 모델 파일, web-tree-sitter 런타임을 받고, 문법 `.wasm`은 언어마다 처음 쓸 때 받습니다.
- 위치는 `normalize(code)` 기준입니다. 줄은 1부터, 칸은 0부터 문자(코드 포인트) 단위, 끝은 포함하지 않습니다. `normalize`도 내보내므로 프론트엔드가 같은 문자열을 보여줄 수 있습니다.

패키지 `dist/`의 모양:

```
wapul-seg.js            # 모듈 (web-tree-sitter와 WASM 글루 포함)
wapul_seg_bg.wasm       # Rust
web-tree-sitter.wasm    # 파서 런타임
grammars/tree-sitter-<lang>.wasm
model/kinds-lgbm.txt, kinds-features.txt, blocks-lgbm.txt, model.json
```

## 경계

| 단계 | 위치 | 이유 |
|------|------|------|
| `normalize` | TS | 파싱 전에 돌아야 함. 깨진 한글 복구는 브라우저 내장 `TextDecoder("euc-kr")`(웹 표준에서 CP949 전체)로 되어 인코딩 표가 필요 없음 |
| 파싱 | TS, web-tree-sitter | 아래 "하지 않는 것"의 첫 줄 참고 |
| 문장 나누기, AST 정보, 특징 | TS (`wapul-seg/js/`) | 파이썬 원본이 tree-sitter 노드 API(`children`, `child_by_field_name`, `descendant_for_byte_range` …)를 그대로 쓰므로 web-tree-sitter 위에서 1:1로 옮겨짐. 트리를 다른 런타임으로 넘길 필요가 없음 |
| 특징 이름 → 열 번호, LightGBM 추론, 블럭 후보 행과 묶기 | WASM (`wapul-seg/src/`) | 모델에 속한 것: 특징 어휘는 모델 파일과 같이 움직이고, 후보 행 형식은 랭커가 학습된 형식 그 자체. 숫자 배열만 쓰고 트리를 보지 않음 |
| 모델 파일 | 루트 `model/`, 릴리즈에 포함, TS가 처음 쓸 때 받음 | 아래 "모델" 참고 |

- 프론트엔드는 `segment(code, language)` 하나만 부릅니다. TS 코드는 문법 버전, WASM과 짝이 맞아야 하므로 프론트엔드가 아니라 `wapul-seg/js/`에 두고 같은 릴리즈로 배포합니다.
- 입력 형식의 원본은 여전히 wapul-ml의 `normalize.py`, `units.py`, `features/`, `models/block_ranker.py`입니다. TS와 Rust는 사본이고, 아래 "검증"을 통과해야 합니다. 원본을 고치면 사본도 같이 고칩니다.
- 언어별 노드 규칙(문장 단위를 이루는 노드, 문장 범주, 쓰기 대상 노드)은 파이썬 원본의 표를 TS로 옮긴 것입니다. 언어를 더할 때 늘어나는 것은 이 표뿐입니다.

## 지원 언어

13개: C++, Python, Java, Rust, C, Kotlin, JavaScript, Go, C#, Swift, Ruby, Scala, PHP. 언어 이름은 corpus의 것(`cpp`, `csharp`, `javascript` …)을 씁니다.

| 언어 | 문법 | 버전 | 파이썬(wapul-ml) | 검증 |
|------|------|------|------------------|------|
| cpp, java, python | npm `tree-sitter-*` | 0.23.4, 0.23.5, 0.25.0 | 같은 버전 | 파이썬과 단계별 일치 |
| rust | npm `tree-sitter-rust` | 0.24.0 (npm에 0.24.2 없음) | 0.24.2 | 파이썬과 단계별 일치 |
| c, javascript, go, csharp, ruby, scala, php | npm `tree-sitter-*` | 0.24.1, 0.25.0, 0.25.0, 0.23.5, 0.23.1, 0.24.0, 0.24.1 | 없음 | 통합 테스트 |
| kotlin | npm `@tree-sitter-grammars/tree-sitter-kotlin` | 1.1.0 | 없음 | 통합 테스트 |
| swift | GitHub 릴리즈 `alex-pinkus/tree-sitter-swift` (npm 패키지에 `.wasm` 없음) | 0.7.3 | 없음 | 통합 테스트 |

- **문법은 언어별 `.wasm`이고, 브라우저는 사용자가 고른 언어의 것만 처음 쓸 때 받습니다.** 13개를 한꺼번에 받으면 너무 큽니다(C++ 3.4MB, C# 5.4MB). 프론트엔드는 전부 정적 파일로 함께 배포하지만, 페이지를 열 때는 하나도 받지 않습니다.
- 문법 `.wasm`은 npm 패키지(또는 그 저장소의 릴리즈)에 들어 있는 것을 그대로 씁니다. 직접 빌드하지 않습니다. 출처는 `js/tools/grammars.ts`, 버전은 `js/package.json`에 고정합니다.
- 언어별 노드 규칙(문장 단위, 범주, 쓰기 대상, 식별자 노드)은 `js/src/languages.ts`에 있습니다. 표는 노드 이름으로 언어를 가리지 않으므로, 한 언어를 위해 더한 이름이 다른 언어의 출력을 바꾸면 안 됩니다. 원래 4개 언어는 parity 테스트가 지킵니다.
- 모델은 C++, Java, Python으로만 학습했고, 다른 언어는 글자 n-gram으로 대응합니다([실험 23](experiments.md)). 언어마다 품질이 다를 수 있습니다.
- 뒤에 더한 9개 언어는 파이썬 쪽(`units.py`, `unit_ast.py`)에 아직 없어서 파이썬과 대조하지 못하고, corpus 풀이로 돌려 보는 통합 테스트로 확인합니다. 파이썬에 넣으려면 같은 규칙 표와 같은 버전의 py-tree-sitter 패키지를 wapul-ml에 더하고, `make_cases.py`의 `LANGUAGE` 표에 확장자를 더합니다.

알아 둘 동작(원래 4개 언어와 같은 규칙에서 나옵니다):

- Kotlin, Swift, Ruby, Scala는 식이 곧 문장이라 `cat=other`로 갑니다. 그 노드 이름(`assignment`, `call_expression` …)은 원래 언어들의 문장 안에도 나와서 범주에 넣을 수 없습니다. 이 언어들은 문장 소유 노드를 올릴 때 컨테이너 바로 아래에서 멈춥니다(`BARE_EXPRESSION_LANGUAGES`).
- C 계열(C, C++, Java, JavaScript, PHP)의 `else if` 사슬은 `else_clause` 아래 `if`가 통째로 한 문장입니다. Kotlin, Swift, Rust, Go, C#은 나뉩니다.
- Kotlin의 끝 람다(`repeat(n) { … }`)와 Ruby의 블록(`each do … end`)은 문장으로 나뉘고, Swift의 끝 클로저와 Java·C++·JS의 람다는 식의 일부라 나뉘지 않습니다.

## 모델

- 출시할 모델은 루트 `model/`에 둡니다(`kinds-lgbm.txt`, `kinds-features.txt`, `blocks-lgbm.txt`, `model.json`). `openapi/`처럼 패키지 밖의 계약 파일이고, wapul-ml의 `models/segmenter-vN/`에서 사람이 복사해 커밋합니다. 학습에는 비공개 데이터가 필요해서 CI는 학습하지 않고, 모델은 자주 바뀌지 않습니다.
- WASM에 넣지 않고 문법 `.wasm`처럼 릴리즈의 별도 파일로 둡니다. TS가 처음 `segment`를 부를 때 세 파일을 받아 `new Model(...)`에 텍스트로 넘깁니다.
- 모델 파일은 패키지와 함께 버전이 갑니다. 프론트엔드는 `wapul-seg@X.Y.Z` 하나로 WASM, 문법, 모델을 한 벌로 받으므로 짝이 어긋나지 않습니다.
- wapul-seg의 Rust 테스트는 루트 `model/`의 모델을 읽습니다.

## WASM 호출

풀이 하나에 호출 두 번입니다. TS는 특징만 만들고, 결과는 WASM이 바로 돌려줍니다.

| 함수 | 입력 | 출력 |
|------|------|------|
| `new Model(kindsModel, kindsFeatures, blocksModel)` | 모델 파일 세 개의 텍스트 | 모델 객체. 처음 한 번 만들어 둠 |
| `kinds(features)` | 문장마다 특징 이름을 줄로, 문장 사이는 빈 줄. 값이 1이 아니면 `이름	값` | 문장마다 종류 번호 `Uint8Array` (`input`, `output`, `logic`, `none` 순). 모르는 이름은 무시 |
| `blocks(own, pairs)` | 로직 문장마다 own 특징 11개 `Float32Array`; 로직 문장 쌍마다 pair 특징 14개 `Float32Array` (뒤 문장 순, 그 안에서 앞 문장 순) | 로직 문장마다 블럭 번호 `Uint32Array` (0부터) |

- 경계는 wasm-bindgen의 슬라이스 인자로 넘습니다. typed array가 한 번에 복사되며, 추가 라이브러리를 쓰지 않습니다.
- 종류 모델의 입력은 희소 행이고 없는 특징은 0입니다. 값은 파이썬이 float32 행렬로 넣으므로 Rust도 float32로 읽습니다.
- 블럭 후보 행(`blocks.rs`)은 파이썬 `BlockCandidates.block_rows`와 같은 순서와 float32 계산입니다. own은 `candidates.py`의 `unit_features`, pair는 `unit_ast.py`의 `segment_features` 11개에 인접 여부, log 거리, 깊이 차를 더한 것입니다.

## 검증

TS를 **Node에서 그대로** 돌려 파이썬 구현과 단계마다 비교합니다. 브라우저와 같은 TS, 같은 WASM, 같은 문법 파일을 쓰므로 여기서 같으면 브라우저에서도 같습니다.

| 비교 | 파이썬 쪽 | 같아야 하는 것 |
|------|-----------|----------------|
| `normalize` | `normalize.py` | 결과 문자열 |
| 문장 나누기 | `units.py` | 문장 위치와 텍스트 |
| AST 정보 | `features/unit_ast.py` | 범주, 읽기·쓰기 식별자, 깊이, 소속 |
| 종류 특징, 예측 | `features/kind_features.py`, LightGBM | 특징 사전, 종류 |
| 블럭 | `features/candidates.py`, `models/block_ranker.py`, LightGBM | own·pair 특징, 블럭 번호 |

두 구현이 조용히 어긋나면 성능이 떨어져도 드러나지 않으므로, 이 비교는 릴리즈 전에 반드시 통과해야 합니다.

- 기대값은 `js/tests/make_cases.py`가 wapul-ml 이미지 안에서 파이썬 모델을 돌려 씁니다. `js/tests/cases/`의 공개 예제 네 개 → `js/tests/cases.json`은 커밋하고 `pnpm test`가 늘 돌립니다.
- 릴리즈 전에는 `--corpus N`으로 비공개 corpus에서 N개를 뽑아 같은 검사를 합니다. 결과는 `wapul-ml/cache/seg-parity/`에 두고(git 무시) `WAPUL_SEG_CASES`로 가리킵니다.

```bash
# 모노레포 루트에서, wapul-ml 이미지로
docker run --rm -v "$(pwd):/wapul" -e PYTHONPATH=/wapul/wapul-ml wapul-ml python /wapul/wapul-seg/js/tests/make_cases.py --corpus 500
cd wapul-seg/js
WAPUL_SEG_CASES=../../wapul-ml/cache/seg-parity/cases.json pnpm test
```

## 빌드

```bash
cd wapul-seg
sh scripts/build-wasm.sh   # cargo + wasm-bindgen-cli → pkg/ (js/가 import)
cd js && pnpm build        # tsc, vite 라이브러리 빌드, 릴리즈 파일을 dist/에 모음
```

- CI: `seg-ci.yml`이 PR마다 Rust fmt·clippy·test와 `pnpm lint`·`check`·`test`를 돌리고, `seg-release.yml`이 main에서 같은 빌드로 릴리즈를 만듭니다. 둘 다 `.github/actions/seg-build`의 빌드 단계를 씁니다.
- wasm-bindgen-cli는 `Cargo.lock`의 `wasm-bindgen`과 같은 버전이어야 합니다. CI는 그 버전을 읽어 설치합니다.
- Windows에서는 cargo가 막혀 있어 Rust 쪽을 `rust:1-slim` 컨테이너에서 돌립니다(CLAUDE.md).

## 결정

| 항목 | 결정 | 이유 |
|------|------|------|
| 모델 로직 언어 | TS (vite 라이브러리 모드, vitest) | 파이썬 원본이 tree-sitter 노드 API 위에 쓰여 있고 web-tree-sitter가 같은 API를 줌. 프론트엔드와 같은 도구 |
| 추론 언어 | Rust → `wasm32-unknown-unknown` | LightGBM 트리 실행은 수치 계산뿐이라 WASM이 맞고, 모델을 안에 넣을 수 있음 |
| 파서 | web-tree-sitter, 파이썬과 같은 문법 버전 ("지원 언어" 표) | 라벨이 tree-sitter 문장 단위에 붙어 있음 |
| 문법 파일 | 그 문법의 npm 패키지에 들어 있는 `.wasm` | 직접 빌드하면 emscripten이 필요하고 버전이 어긋날 수 있음. 언어별 파일이라 고른 언어만 받음 |
| LightGBM 추론 | [bosk](https://github.com/stanwarp/bosk)(Apache-2.0 / MIT)의 순수 Rust 텍스트 모델 파서를 가져와 다중 클래스와 희소 입력을 더함 | LightGBM과 예측이 같도록 검증된 구현. 원본은 다중 클래스를 거부하고 밀집 입력만 받음. 만든 사람이 한 명이라 의존성 대신 저장소로 가져옴 |
| 종류 특징 | 글자 n-gram 추가 | 학습하지 않은 언어(Rust)에서 macro-F1 0.663 → 0.870 ([실험 23](experiments.md)) |
| 배포물 | npm 패키지 `wapul-seg@X.Y.Z`: `js/dist/` 그대로(JS 모듈과 타입 선언, `wapul-seg` WASM, web-tree-sitter 런타임, 언어별 문법 `.wasm`, 모델 파일). 모노레포의 `wapul-seg/js`에서 냄 | 바이너리를 git 기록에 쌓지 않고, 프론트엔드가 package.json에서 버전을 고정함. 저장소를 따로 두지 않아도 되고, 루트 `model/`과 파이썬 원본 옆에 있어야 사본 규칙을 지킬 수 있음 |
| 버전 | CI(`seg-release.yml`)가 계산. Y는 `model/`의 모델 파일이 바뀌면, Z는 그 외 릴리스마다, X는 수동 `major`. 손으로 올리지 않음 | 백엔드, 프론트엔드와 같은 규칙. 모델이 바뀌면 결과가 달라지므로 Y로 드러냄 |
| npm 인증 | 워크플로는 trusted publishing(OIDC)을 먼저 시도하고, 실패하면 `NPM_TOKEN` 시크릿(granular token)으로 올림. 지금은 토큰이 쓰임 | 이 저장소는 2026-07-15 이후 생성이라 OIDC `sub`가 immutable 형식(`repo:owner@id/repo@id`)인데 npm이 아직 받지 않음([npm/cli#9969](https://github.com/npm/cli/issues/9969)). 고쳐지면 npmjs.com 패키지 설정에 저장소 `jjh4450/wapul`과 워크플로 `seg-release.yml`을 등록하고 시크릿을 지움 |
| 프론트엔드가 받는 시점 | `pnpm install` 때, package.json에 고정한 버전 | 실행 중 외부 의존이 없고, 버전 갱신이 PR로 드러남 |
| 학습 | wapul-ml의 파이썬 그대로 | `wapul-seg`는 파이썬 구현과 같은 결과를 내는 배포용 사본. 일치는 "검증"으로 보장 |

## 하지 않는 것

| 하지 않는 것 | 이유 | 다시 볼 조건 |
|--------------|------|--------------|
| 문장 나누기, AST 정보, 특징을 Rust로 작성 | 트리를 평평한 배열로 WASM에 넘기고 그 위에 노드 연산을 다시 구현해야 하며, 언어별 규칙 표를 두 언어로 유지하게 됨 | TS 쪽이 느려서 사용자가 체감할 때 |
| 블럭 묶기 루프와 특징 어휘를 TS에 두고 WASM은 점수만 내기 | 호출 수는 문제가 아니지만, 모델이 바뀌면 고칠 곳이 파이썬·Rust·TS 세 군데가 됨. 숫자만 다루는 부분은 모델과 같이 Rust에 둠 | 없음 |
| tree-sitter와 문법 C 코드를 Rust WASM 안에 같이 컴파일 | C → `wasm32-unknown-unknown` 빌드에 clang과 sysroot가 필요함. 현재 이 빌드는 외부 스캐너의 문자 판별이 ASCII 전용이고 할당기가 범용이 아님([tree-sitter #5851](https://github.com/tree-sitter/tree-sitter/pull/5851)). 모든 문법이 한 파일에 들어가 언어별로 나눠 받을 수 없음 | tree-sitter 0.27에서 #5851이 들어가고, 문법을 별도 WASM 모듈로 불러올 수 있게 될 때 |
| 문법 `.wasm`을 직접 빌드 | emscripten 도구 체인이 필요하고, npm 패키지가 이미 같은 버전의 파일을 줌 | npm에 없는 버전을 꼭 써야 할 때 |
| `normalize`를 WASM에 두기 | 파싱(TS) 전에 돌아야 해 WASM을 한 번 더 오가고, 깨진 한글 복구에 CP949 표(`encoding_rs`)가 WASM에 들어가 수백 KB 커짐 | 없음 |
| LightGBM 추론을 TS로 작성 | 검증된 Rust 구현이 이미 있고, 트리 수천 개를 문장마다 도는 계산이라 WASM이 빠름 | 없음 |
| ONNX | LightGBM 트리를 실행할 수 있는 브라우저 런타임은 ONNX Runtime Web(13.6MB)뿐이고, tract는 ONNX-ML 트리를 실행하지 못함 | 신경망 모델을 다시 쓰게 될 때 |
| Pyodide 등 파이썬을 브라우저에서 실행 | GC 런타임째 받아야 하고, Pyodide의 tree-sitter는 0.23.2에 C++·Rust 문법이 없음 | 없음 |
| 모델 파일을 WASM 안에 넣기 (`include_bytes!`) | 모델이 바뀔 때마다 WASM을 다시 빌드해야 하고, 7MB 모델이 바이너리에 들어가 WASM을 받는 순간부터 무거움. 따로 두면 문법처럼 지연 로드할 수 있음 | 없음 |
| 실행 중에 npm이나 GitHub에서 받기 | 위 "프론트엔드가 받는 시점" 참고 | 없음 |
| GitHub Release의 tar.gz로 배포 | 프론트엔드가 빌드 때 내려받는 단계와 버전 파일이 따로 필요함. npm이면 의존성 하나 | 없음 |
| 파이썬에서 wasmtime으로 WASM 실행 | wasm-bindgen 출력은 JS 연결 코드를 전제로 해 다른 호스트에서 바로 부르기 어려움. 검증은 Node로 함 | 백엔드가 서버에서 모델을 돌려야 할 때. 이때는 WASM에 JS 없이 부를 수 있는 함수를 따로 내보냄 |

## 정하지 않은 것

- **Rust 문법 버전.** wapul-ml은 `tree-sitter-rust==0.24.2`인데 npm에는 0.24.0까지만 있습니다. 파이썬을 0.24.0으로 내리고 Rust 라벨·corpus가 그대로인지 확인하거나, 0.24.2 태그에서 직접 빌드해야 합니다.
- **모델의 특징 이름을 해시로 바꿀지.** 저장소가 공개라 릴리즈의 모델 파일도 공개됩니다. 종류 분류 모델의 특징 이름에는 학습 풀이의 식별자 토큰과 n-gram이 들어 있습니다.

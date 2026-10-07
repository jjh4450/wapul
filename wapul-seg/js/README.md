<div align="center">

<a id="top"></a>

# wapul-seg

**wapul 블럭 분할 모델의 브라우저 배포 패키지**

[![npm](https://img.shields.io/npm/v/wapul-seg?style=flat-square&logo=npm&logoColor=white&color=CB3837)](https://www.npmjs.com/package/wapul-seg)
[![Rust](https://img.shields.io/badge/Rust-WASM-000000?style=flat-square&logo=rust&logoColor=white)](https://www.rust-lang.org)
[![tree-sitter](https://img.shields.io/badge/web--tree--sitter-0.27-4B8BBE?style=flat-square)](https://tree-sitter.github.io/tree-sitter/)
[![LightGBM](https://img.shields.io/badge/LightGBM-inference-9ACD32?style=flat-square)](https://lightgbm.readthedocs.io)

**[문서](https://jjh4450.github.io/wapul/ml/deploy/)** • **[모델](https://jjh4450.github.io/wapul/ml/)**

</div>

---

## 하는 일

풀이 코드를 받아 `segment(code, language)` 한 번으로 문장을 나누고, 문장마다 종류(`input` / `output` / `logic` / `none`)와 로직 블럭 번호를 돌려줍니다. [wapul-ml](https://github.com/jjh4450/wapul/tree/main/wapul-ml)에서 학습한 모델(segmenter-v3)을 브라우저에서 그대로 돌리는 것으로, 트리를 읽는 일(정규화, web-tree-sitter 파싱, 문장 나누기, 특징)은 TypeScript가, 모델(특징 어휘, LightGBM 추론, 블럭 묶기)은 Rust → WASM이 맡습니다.

지원 언어 13개: C++, Python, Java, Rust, C, Kotlin, JavaScript, Go, C#, Swift, Ruby, Scala, PHP. 모델은 C++·Java·Python으로 학습했고 다른 언어는 글자 n-gram으로 대응하므로 언어마다 품질이 다를 수 있습니다.

## 쓰기

```bash
pnpm add wapul-seg
```

```ts
import { segment, blockTags, fetchAssets, LANGUAGES, type Language } from 'wapul-seg';

// 패키지의 dist/ 파일(WASM, 문법 .wasm, 모델)을 정적 경로 /seg/ 아래에 복사해 두었을 때
const labeled = await segment(code, 'cpp', fetchAssets('/seg/'));
// [{ start: [1, 0], end: [1, 19], kind: 'none', condition: false, loop: false, recursion: false }, ...,
//  { start: [7, 4], end: [7, 25], kind: 'logic', block: 2, condition: true, loop: false, recursion: false }, ...]

blockTags(labeled); // Map { 1 => { condition: false, loop: true, recursion: false }, 2 => { condition: true, ... } }

LANGUAGES; // ['cpp', 'java', 'python', 'rust', 'c', 'kotlin', 'javascript', 'go', 'csharp', 'swift', 'ruby', 'scala', 'php']
```

- 패키지는 모듈과 타입 선언 외에 WASM, 언어별 문법 `.wasm`, 모델(`wapul-seg.model`, 2MB)을 담고 있습니다. 이 파일들은 번들에 들어가지 않으므로 빌드가 정적 파일로 복사해야 하고, `fetchAssets`에 그 위치를 넘깁니다. `wapul-seg/grammars/tree-sitter-cpp.wasm`처럼 경로로 import할 수도 있습니다.
- 처음 부를 때 WASM, 런타임, 모델을 받고, 문법은 그 언어를 처음 쓸 때만 받습니다(C++ 3.4MB, C# 5.4MB). 페이지를 열 때는 아무것도 받지 않습니다.
- 위치는 `normalize(code)` 기준입니다. 줄은 1부터, 칸은 0부터 문자 단위, 끝은 포함하지 않습니다. `normalize`도 내보냅니다.
- `condition`(분기 머리, 비교 연산, 삼항식), `loop`(반복문 머리), `recursion`(감싼 함수를 다시 부름)은 모델이 아니라 트리에서 정합니다. 경계 질문과 구조 질문을 붙일 블럭을 고를 때 `blockTags`로 블럭 단위로 모아 씁니다.

## 구조

```
wapul-seg/
├── js/            # TypeScript (vite 라이브러리): segment(), 파싱, 문장 나누기, 특징, 언어별 규칙 표
│   ├── src/languages.ts   # 13개 언어의 노드 규칙
│   └── tests/             # 파이썬 모델과의 단계별 일치 검사
├── src/           # Rust → WASM: 특징 어휘, LightGBM, 쌍 특징과 블럭 묶기
│   ├── lgbm/      # 순수 Rust LightGBM 추론 (bosk에서 가져옴)
│   └── bin/       # model-pack: wapul-ml의 텍스트 모델을 wapul-seg.model로 묶음
└── scripts/build-wasm.sh
```

TypeScript와 Rust는 wapul-ml의 파이썬(`normalize.py`, `units.py`, `features/`, `models/block_ranker.py`)의 사본이고 파이썬이 원본입니다. 출시할 모델(묶은 바이너리)은 모노레포 루트 `model/`에 있습니다.

## 개발

```bash
# Rust (wasm32-unknown-unknown 타깃, Cargo.lock 버전의 wasm-bindgen-cli 필요)
cd wapul-seg
sh scripts/build-wasm.sh   # WASM + 글루 → pkg/, model/wapul-seg.model → pkg/ (js/가 import)
cargo fmt --check
cargo clippy --release --target wasm32-unknown-unknown --no-default-features
cargo test --release       # 루트 model/wapul-seg.model을 읽음

# TypeScript
cd js
pnpm install
pnpm format     # prettier 적용
pnpm lint       # prettier 검사 + eslint + oxlint(anti-slop)
pnpm check      # 타입 검사
pnpm test       # 파이썬 모델과 단계별 비교 (tests/cases.json)
pnpm build      # dist/: 모듈, 타입 선언, WASM, 문법 .wasm 13개, wapul-seg.model
```

- `tests/cases.json`은 `tests/make_cases.py`가 wapul-ml 이미지에서 파이썬 모델을 돌려 쓴 기대값입니다. 파이썬 원본이 바뀌면 다시 만들고, 릴리스 전에는 `--corpus N`으로 비공개 corpus에서도 같은 검사를 합니다.
- 언어를 더할 때는 `js/src/languages.ts`의 규칙 표와 `js/tools/grammars.ts`의 문법 출처를 더합니다. 표는 노드 이름으로 언어를 가리지 않으므로 다른 언어의 출력이 바뀌지 않는지 parity 테스트로 확인해 주세요.

## 릴리스

CI(`seg-release.yml`)가 main에서 Segmenter CI를 통과한 커밋만 `wapul-seg@X.Y.Z`로 npm에 올리고 `seg-vX.Y.Z` 태그를 답니다. Y는 루트 `model/wapul-seg.model`이 바뀔 때, Z는 그 외 릴리스마다, X는 수동 `major`입니다.

자세한 결정과 구조는 [배포 문서](https://jjh4450.github.io/wapul/ml/deploy/)에 있습니다.

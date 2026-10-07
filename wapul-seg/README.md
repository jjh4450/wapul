# wapul-seg

**wapul 블럭 분할 모델의 브라우저 배포 패키지**: `segment(code, language)` 하나로 풀이 코드를 문장으로 나누고, 문장마다 종류(`input` / `output` / `logic` / `none`)와 로직 블럭 번호를 돌려줍니다. 트리를 읽는 일(정규화, web-tree-sitter 파싱, 문장 나누기, 특징)은 `js/`의 TypeScript가, 모델(LightGBM 추론, 블럭 묶기)은 `src/`의 Rust → WASM이 맡습니다. 모델 파일은 루트 `model/`에서 옵니다.

**[문서: 배포](https://jjh4450.github.io/wapul/ml/deploy/)** (원본: `docs/ml/deploy.ko.md`)

```bash
# Rust → WASM (wasm32-unknown-unknown 타깃, Cargo.lock 버전의 wasm-bindgen-cli 필요)
sh scripts/build-wasm.sh   # → pkg/ (js/가 import)
cargo fmt --check && cargo clippy --target wasm32-unknown-unknown && cargo test --release

# TypeScript
cd js
pnpm install
pnpm format     # prettier 적용
pnpm lint       # prettier 검사 + eslint + oxlint(anti-slop)
pnpm check      # 타입 검사
pnpm test       # 파이썬 모델과 단계별 비교 (tests/cases.json)
pnpm build      # dist/: 모듈, WASM, 문법 .wasm 13개, 모델 파일
```

- `tests/cases.json`은 `tests/make_cases.py`가 wapul-ml 이미지에서 파이썬 모델을 돌려 만든 기대값입니다. 파이썬 원본(`normalize.py`, `units.py`, `features/`)이 바뀌면 다시 만듭니다.
- 릴리스 `seg-vX.Y.Z`는 CI(`seg-release.yml`)가 main에서 만듭니다. 손으로 태그를 만들지 않습니다.
- Windows에서는 cargo가 막혀 있을 수 있습니다. 그때는 `rust:1-slim` 컨테이너에서 Rust 쪽을 돌립니다.

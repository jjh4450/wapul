#!/bin/sh
# Build the WASM and its JS glue into pkg/, which js/ imports, and pack the root model/ into
# pkg/wapul-seg.model. Needs cargo with the wasm32-unknown-unknown target and wasm-bindgen-cli at
# the version Cargo.toml pins.
set -eu
cd "$(dirname "$0")/.."
mkdir -p pkg
cargo run --release --bin model-pack -- ../model pkg/wapul-seg.model
cargo build --release --target wasm32-unknown-unknown --no-default-features
wasm-bindgen --target web --omit-default-module-path --out-dir pkg \
  "${CARGO_TARGET_DIR:-target}/wasm32-unknown-unknown/release/wapul_seg.wasm"

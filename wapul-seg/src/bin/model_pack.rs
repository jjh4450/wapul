//! Pack the model files wapul-ml trains into the one binary the WASM loads:
//!
//!     model-pack <model dir> <out file>
//!     cargo run --release --bin model-pack -- ../wapul-ml/models/segmenter-vN ../model/wapul-seg.model
//!
//! `<model dir>` holds `kinds-lgbm.txt`, `kinds-features.txt` and `blocks-lgbm.txt`. The output
//! keeps the trees as evaluated and replaces feature names by their hashes; only it is committed,
//! as the root `model/wapul-seg.model` (docs/ml/deploy.ko.md, "모델").

use std::{env, fs, process};

use wapul_seg::Segmenter;

fn main() {
    let args: Vec<String> = env::args().collect();
    let [_, dir, out] = args.as_slice() else {
        eprintln!("usage: model-pack <model dir> <out file>");
        process::exit(2);
    };
    let read = |name: &str| {
        fs::read_to_string(format!("{dir}/{name}")).unwrap_or_else(|e| {
            eprintln!("{dir}/{name}: {e}");
            process::exit(1);
        })
    };
    let segmenter = Segmenter::from_text(
        &read("kinds-lgbm.txt"),
        &read("kinds-features.txt"),
        &read("blocks-lgbm.txt"),
    )
    .unwrap_or_else(|e| {
        eprintln!("{dir}: {e}");
        process::exit(1);
    });
    let bytes = segmenter.to_bytes();
    if let Err(e) = Segmenter::from_bytes(&bytes) {
        eprintln!("packed model does not read back: {e}");
        process::exit(1);
    }
    fs::write(out, &bytes).unwrap_or_else(|e| {
        eprintln!("{out}: {e}");
        process::exit(1);
    });
    println!("{out}: {} bytes", bytes.len());
}

//! LightGBM inference for the block model, built to WASM. Everything that reads the syntax
//! tree (parsing, statement units, AST facts, feature names) is the TS in `js/`; this crate
//! takes the features and returns kinds and blocks. The model comes packed in one binary
//! (`model-pack`), which the caller fetches and hands in. Decisions and layout:
//! `docs/ml/deploy.ko.md`.
//!
//! [`Segmenter`] is the plain Rust API, which the tests and the packer use; [`Model`] wraps it
//! for JS.

pub mod blocks;
pub mod lgbm;

use std::fmt;

use lgbm::binary::{Reader, Writer};
use lgbm::{LgbModel, SparseRow};
use wasm_bindgen::prelude::*;

/// Kind names in the kind model's class order.
pub const KINDS: [&str; 4] = ["input", "output", "logic", "none"];

const MAGIC: &[u8; 4] = b"WSEG";
const FORMAT: u32 = 1;

/// A model file this crate cannot use, or input of the wrong shape.
#[derive(Debug)]
pub struct Error(pub String);

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

impl std::error::Error for Error {}

impl From<lgbm::Error> for Error {
    fn from(e: lgbm::Error) -> Self {
        Error(e.to_string())
    }
}

/// FNV-1a over the feature name's UTF-8 bytes: how the packed model keys its columns, so the
/// names themselves (identifier tokens of the training solutions) are not shipped.
fn hash(name: &str) -> u64 {
    name.bytes().fold(0xcbf29ce484222325, |h, b| {
        (h ^ u64::from(b)).wrapping_mul(0x100000001b3)
    })
}

/// The trained segmenter-v3 models: the kind classifier (multiclass over sparse string
/// features) and the block ranker (LambdaRank over candidate rows).
pub struct Segmenter {
    kinds: LgbModel,
    /// (hash of feature name, column), sorted by hash.
    columns: Vec<(u64, u32)>,
    blocks: LgbModel,
}

impl Segmenter {
    /// From the model files wapul-ml trains, as text: `kinds-lgbm.txt`, `kinds-features.txt`
    /// (one feature name per line, in column order) and `blocks-lgbm.txt`.
    #[cfg(feature = "text")]
    pub fn from_text(
        kinds_model: &str,
        kinds_features: &str,
        blocks_model: &str,
    ) -> Result<Self, Error> {
        let mut columns: Vec<(u64, u32)> = kinds_features
            .lines()
            .enumerate()
            .map(|(i, name)| (hash(name), i as u32))
            .collect();
        columns.sort_unstable();
        if let Some(w) = columns.windows(2).find(|w| w[0].0 == w[1].0) {
            return Err(Error(format!(
                "feature names of columns {} and {} share a hash",
                w[0].1, w[1].1
            )));
        }
        Self::check(
            LgbModel::parse(kinds_model)?,
            columns,
            LgbModel::parse(blocks_model)?,
        )
    }

    fn check(kinds: LgbModel, columns: Vec<(u64, u32)>, blocks: LgbModel) -> Result<Self, Error> {
        if kinds.num_outputs() != KINDS.len() {
            return Err(Error(format!(
                "kind model has {} classes, expected {}",
                kinds.num_outputs(),
                KINDS.len()
            )));
        }
        if columns.len() != kinds.num_features() {
            return Err(Error(format!(
                "kind model has {} features, feature list has {}",
                kinds.num_features(),
                columns.len()
            )));
        }
        if blocks.num_features() != blocks::WIDTH {
            return Err(Error(format!(
                "block ranker has {} features, expected {}",
                blocks.num_features(),
                blocks::WIDTH
            )));
        }
        Ok(Self {
            kinds,
            columns,
            blocks,
        })
    }

    /// The packed form (`model-pack` writes it to `pkg/wapul-seg.model`).
    pub fn to_bytes(&self) -> Vec<u8> {
        let mut w = Writer(Vec::new());
        w.0.extend_from_slice(MAGIC);
        w.u32(FORMAT);
        self.kinds.write(&mut w);
        w.list(&self.columns, |w, &(h, c)| {
            w.u64(h);
            w.u32(c);
        });
        self.blocks.write(&mut w);
        w.0
    }

    /// Read the packed form.
    pub fn from_bytes(bytes: &[u8]) -> Result<Self, Error> {
        let bad = |message: String| Error(format!("packed model: {message}"));
        if bytes.len() < 8 || &bytes[..4] != MAGIC {
            return Err(bad("not a wapul-seg model".into()));
        }
        let mut r = Reader::new(&bytes[4..]);
        let format = r.u32()?;
        if format != FORMAT {
            return Err(bad(format!("format {format}, this build reads {FORMAT}")));
        }
        let kinds = LgbModel::read(&mut r)?;
        let columns = r.list(12, |r| Ok((r.u64()?, r.u32()?)))?;
        if !columns.is_sorted() {
            return Err(bad("feature hashes are not sorted".into()));
        }
        let blocks = LgbModel::read(&mut r)?;
        if !r.is_empty() {
            return Err(bad("trailing bytes".into()));
        }
        Self::check(kinds, columns, blocks)
    }

    fn column(&self, name: &str) -> Option<u32> {
        let h = hash(name);
        self.columns
            .binary_search_by_key(&h, |&(hash, _)| hash)
            .ok()
            .map(|i| self.columns[i].1)
    }

    /// The kind of every unit, as an index into [`KINDS`]: the most probable, the first on a
    /// tie. `features` holds the units separated by a blank line; each line is one feature,
    /// `name` for value 1 or `name\tvalue`. Names the model does not know are ignored; a
    /// repeated name keeps its last value.
    pub fn kinds(&self, features: &str) -> Result<Vec<u8>, Error> {
        let features = features.trim_end_matches('\n');
        if features.is_empty() {
            return Ok(Vec::new());
        }
        features
            .split("\n\n")
            .map(|unit| {
                let mut pairs = Vec::new();
                for line in unit.lines() {
                    let (name, value) = match line.split_once('\t') {
                        Some((name, v)) => {
                            let v: f32 = v.parse().map_err(|_| {
                                Error(format!("feature {name:?} has a non-numeric value {v:?}"))
                            })?;
                            (name, f64::from(v))
                        }
                        None => (line, 1.0),
                    };
                    if let Some(c) = self.column(name) {
                        pairs.push((c, value));
                    }
                }
                let p = self.kinds.predict_sparse(&SparseRow::new(pairs));
                Ok((0..p.len()).fold(0, |b, i| if p[i] > p[b] { i } else { b }) as u8)
            })
            .collect()
    }

    /// Block number from 0 for every logic unit, in order. The inputs describe the logic units
    /// as [`blocks::Logic`] takes them.
    pub fn blocks(
        &self,
        own: &[f32],
        facts: &[i32],
        reads_offsets: &[u32],
        reads: &[u32],
        writes_offsets: &[u32],
        writes: &[u32],
    ) -> Result<Vec<u32>, Error> {
        let logic = blocks::Logic::new(own, facts, reads_offsets, reads, writes_offsets, writes)
            .map_err(Error)?;
        Ok(blocks::decode(&logic, |rows| {
            rows.chunks(blocks::WIDTH)
                .map(|r| self.blocks.predict_raw_with(|i| f64::from(r[i]))[0])
                .collect()
        }))
    }
}

/// [`Segmenter`] for JS; see `docs/ml/deploy.ko.md`, "WASM 호출".
#[wasm_bindgen]
pub struct Model(Segmenter);

#[wasm_bindgen]
impl Model {
    /// From the packed model (`wapul-seg.model`). Keep one instance.
    #[wasm_bindgen(constructor)]
    pub fn new(packed: &[u8]) -> Result<Model, JsError> {
        Ok(Model(Segmenter::from_bytes(packed)?))
    }

    pub fn kinds(&self, features: &str) -> Result<Vec<u8>, JsError> {
        Ok(self.0.kinds(features)?)
    }

    pub fn blocks(
        &self,
        own: &[f32],
        facts: &[i32],
        reads_offsets: &[u32],
        reads: &[u32],
        writes_offsets: &[u32],
        writes: &[u32],
    ) -> Result<Vec<u32>, JsError> {
        Ok(self
            .0
            .blocks(own, facts, reads_offsets, reads, writes_offsets, writes)?)
    }

    /// Every pair's features, ordered by the later unit then the earlier: for the parity check
    /// against the Python model, not for segmenting.
    #[wasm_bindgen(js_name = pairFeatures)]
    pub fn pair_features(
        &self,
        own: &[f32],
        facts: &[i32],
        reads_offsets: &[u32],
        reads: &[u32],
        writes_offsets: &[u32],
        writes: &[u32],
    ) -> Result<Vec<f32>, JsError> {
        let logic = blocks::Logic::new(own, facts, reads_offsets, reads, writes_offsets, writes)
            .map_err(|e| JsError::new(&e))?;
        Ok(logic.all_pairs())
    }
}

#[cfg(all(test, feature = "text"))]
mod tests {
    use super::*;

    /// The release model at the repo root (docs/ml/deploy.ko.md, "모델").
    fn release_model() -> Segmenter {
        let read = |name: &str| {
            std::fs::read_to_string(
                concat!(env!("CARGO_MANIFEST_DIR"), "/../model/").to_owned() + name,
            )
            .unwrap()
        };
        Segmenter::from_text(
            &read("kinds-lgbm.txt"),
            &read("kinds-features.txt"),
            &read("blocks-lgbm.txt"),
        )
        .unwrap()
    }

    const FEATURES: &str = "lang=cpp\ncat=expression\nt:cin\nt:>>\nt:n\nheader\t0\ndepth\t0\npos\t0.5\n\n\
                            lang=cpp\ncat=return\nt:return\nt:NUM\nheader\t0\ndepth\t0\npos\t1\n";

    #[test]
    fn kinds_one_per_unit() {
        let m = release_model();
        let kinds = m.kinds(FEATURES).unwrap();
        assert_eq!(kinds.len(), 2);
        assert!(kinds.iter().all(|&k| (k as usize) < KINDS.len()));
        assert!(m.kinds("").unwrap().is_empty());
        assert!(m.kinds("t:x\tabc").is_err());
    }

    #[test]
    fn blocks_one_per_logic_unit() {
        let m = release_model();
        let n = 5;
        let own = vec![0.0f32; n * blocks::N_OWN];
        let facts = vec![0; n * blocks::N_FACTS];
        let offsets: Vec<u32> = (0..=n as u32).collect();
        let ids: Vec<u32> = (0..n as u32).collect();
        let b = m
            .blocks(&own, &facts, &offsets, &ids, &[0; 6], &[])
            .unwrap();
        assert_eq!(b.len(), n);
        assert_eq!(b[0], 0);
        assert!(b.iter().all(|&x| (x as usize) < n));
        assert!(
            m.blocks(&own, &facts[1..], &offsets, &ids, &[0; 6], &[])
                .is_err()
        );
    }

    #[test]
    fn packed_model_reads_back_the_same() {
        let m = release_model();
        let bytes = m.to_bytes();
        let packed = Segmenter::from_bytes(&bytes).unwrap();
        assert_eq!(packed.kinds(FEATURES).unwrap(), m.kinds(FEATURES).unwrap());
        assert_eq!(packed.columns, m.columns);
        let own = vec![0.0f32; 3 * blocks::N_OWN];
        let facts = vec![0; 3 * blocks::N_FACTS];
        assert_eq!(
            packed
                .blocks(&own, &facts, &[0; 4], &[], &[0; 4], &[])
                .unwrap(),
            m.blocks(&own, &facts, &[0; 4], &[], &[0; 4], &[]).unwrap()
        );
        assert!(Segmenter::from_bytes(&bytes[..bytes.len() / 2]).is_err());
        assert!(Segmenter::from_bytes(b"nope").is_err());
        let mut wrong_format = bytes.clone();
        wrong_format[4] = 9;
        assert!(Segmenter::from_bytes(&wrong_format).is_err());
    }

    #[test]
    fn rejects_models_of_the_wrong_shape() {
        let multiclass = include_str!("../tests/fixtures/lgbm/tiny_multiclass.lgb");
        let rank = include_str!("../tests/fixtures/lgbm/tiny_rank.lgb");
        let names: String = (0..302).map(|i| format!("f{i}\n")).collect();
        assert!(
            Segmenter::from_text(multiclass, &names, rank).is_err(),
            "ranker width"
        );
        assert!(
            Segmenter::from_text(multiclass, "f0\n", rank).is_err(),
            "list length"
        );
        assert!(Segmenter::from_text("not a model", &names, rank).is_err());
    }
}

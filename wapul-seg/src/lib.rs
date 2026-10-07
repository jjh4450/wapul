//! LightGBM inference for the block model, built to WASM. Everything that reads the syntax
//! tree (parsing, statement units, AST facts, features) is the TS in `js/`; this crate takes
//! the features and returns kinds and blocks. The model files are fetched by the caller and
//! handed in as text. Decisions and layout: `docs/ml/deploy.ko.md`.
//!
//! [`Segmenter`] is the plain Rust API, which the tests use; [`Model`] wraps it for JS.

pub mod blocks;
pub mod lgbm;

use std::collections::HashMap;
use std::fmt;

use lgbm::{LgbModel, SparseRow};
use wasm_bindgen::prelude::*;

/// Kind names in the kind model's class order.
pub const KINDS: [&str; 4] = ["input", "output", "logic", "none"];

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

/// The trained segmenter-v3 models: the kind classifier (multiclass over sparse string
/// features) and the block ranker (LambdaRank over candidate rows).
pub struct Segmenter {
    kinds: LgbModel,
    /// Feature name -> column of the kind model.
    columns: HashMap<String, u32>,
    blocks: LgbModel,
}

impl Segmenter {
    /// From the model files wapul-ml trains, as text: `kinds-lgbm.txt`, `kinds-features.txt`
    /// (one feature name per line, in column order) and `blocks-lgbm.txt`.
    pub fn new(kinds_model: &str, kinds_features: &str, blocks_model: &str) -> Result<Self, Error> {
        let kinds = LgbModel::parse(kinds_model)?;
        let blocks = LgbModel::parse(blocks_model)?;
        let columns: HashMap<String, u32> = kinds_features
            .lines()
            .enumerate()
            .map(|(i, name)| (name.to_owned(), i as u32))
            .collect();
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
                    if let Some(&c) = self.columns.get(name) {
                        pairs.push((c, value));
                    }
                }
                let p = self.kinds.predict_sparse(&SparseRow::new(pairs));
                Ok((0..p.len()).fold(0, |b, i| if p[i] > p[b] { i } else { b }) as u8)
            })
            .collect()
    }

    /// Block number from 0 for every logic unit, in order. `own` holds [`blocks::N_OWN`]
    /// values per logic unit and `pairs` [`blocks::N_PAIR`] values per (earlier, later) pair,
    /// ordered by the later unit then the earlier (see [`blocks::Logic`]).
    pub fn blocks(&self, own: &[f32], pairs: &[f32]) -> Result<Vec<u32>, Error> {
        let logic = blocks::Logic::new(own, pairs).map_err(Error)?;
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
    /// Takes a moment; keep one instance.
    #[wasm_bindgen(constructor)]
    pub fn new(
        kinds_model: &str,
        kinds_features: &str,
        blocks_model: &str,
    ) -> Result<Model, JsError> {
        Ok(Model(Segmenter::new(
            kinds_model,
            kinds_features,
            blocks_model,
        )?))
    }

    pub fn kinds(&self, features: &str) -> Result<Vec<u8>, JsError> {
        Ok(self.0.kinds(features)?)
    }

    pub fn blocks(&self, own: &[f32], pairs: &[f32]) -> Result<Vec<u32>, JsError> {
        Ok(self.0.blocks(own, pairs)?)
    }
}

#[cfg(test)]
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
        Segmenter::new(
            &read("kinds-lgbm.txt"),
            &read("kinds-features.txt"),
            &read("blocks-lgbm.txt"),
        )
        .unwrap()
    }

    #[test]
    fn kinds_one_per_unit() {
        let m = release_model();
        let features = "lang=cpp\ncat=expression\nt:cin\nt:>>\nt:n\nheader\t0\ndepth\t0\npos\t0.5\n\n\
                        lang=cpp\ncat=return\nt:return\nt:NUM\nheader\t0\ndepth\t0\npos\t1\n";
        let kinds = m.kinds(features).unwrap();
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
        let pairs = vec![0.0f32; n * (n - 1) / 2 * blocks::N_PAIR];
        let b = m.blocks(&own, &pairs).unwrap();
        assert_eq!(b.len(), n);
        assert_eq!(b[0], 0);
        assert!(b.iter().all(|&x| (x as usize) < n));
        assert!(m.blocks(&own, &pairs[1..]).is_err());
    }

    #[test]
    fn rejects_models_of_the_wrong_shape() {
        let multiclass = include_str!("../tests/fixtures/lgbm/tiny_multiclass.lgb");
        let rank = include_str!("../tests/fixtures/lgbm/tiny_rank.lgb");
        let names: String = (0..302).map(|i| format!("f{i}\n")).collect();
        assert!(
            Segmenter::new(multiclass, &names, rank).is_err(),
            "ranker width"
        );
        assert!(
            Segmenter::new(multiclass, "f0\n", rank).is_err(),
            "list length"
        );
        assert!(Segmenter::new("not a model", &names, rank).is_err());
    }
}

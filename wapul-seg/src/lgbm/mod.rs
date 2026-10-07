//! Pure-Rust LightGBM inference: parses the text model format and predicts, with no C
//! dependency, so it builds for `wasm32-unknown-unknown`.
//!
//! Vendored from bosk (<https://github.com/stanwarp/bosk>, commit `eb7121a`, 2026-07-27,
//! `src/lgb.rs` and `src/error.rs`), licensed MIT OR Apache-2.0: see `LICENSE-MIT` and
//! `LICENSE-APACHE` in this directory. Changes from bosk:
//! - multiclass models (`objective=multiclass`, softmax over `num_class` outputs)
//! - sparse input ([`SparseRow`]): absent features are zero, as in LightGBM's sparse input
//! - predictions are one value per output (one for single-output models)
//! - parsing from text only (the model is embedded in the binary); bosk's `Model` trait,
//!   file loading and the ONNX / CatBoost backends are not vendored
//!
//! Supported: numerical splits with LightGBM's full missing-value semantics (default direction +
//! missing type), categorical splits (bitset lookup), random-forest averaging
//! (`average_output`), and the output transforms of `binary` (with its `sigmoid` parameter),
//! `cross_entropy`, `cross_entropy_lambda`, `poisson` / `gamma` / `tweedie` (exponential link),
//! the regression family (including `reg_sqrt`), ranking (raw scores) and `multiclass`
//! (softmax).
//!
//! Deliberately rejected at load, instead of silently mispredicting: `multiclassova`, linear
//! trees (`is_linear=1`), and objectives or objective tokens this module does not recognise.

#![forbid(unsafe_code)]

pub mod binary;
mod error;

pub use error::{Error, Result};

#[cfg(feature = "text")]
use std::str::FromStr;

/// Output transform implied by the training objective. Applied to the summed (or, under
/// `average_output`, averaged) tree outputs.
#[derive(Debug, Clone, Copy, PartialEq)]
enum Objective {
    /// Raw score: the regression family and ranking objectives.
    Identity,
    /// `sign(raw) * raw^2`: the regression family trained with `reg_sqrt=true`.
    Sqrt,
    /// `1 / (1 + exp(-k * raw))`: `binary` (with its `sigmoid` parameter `k`) and
    /// `cross_entropy` (`k = 1`).
    Sigmoid(f64),
    /// `ln(1 + exp(raw))`: `cross_entropy_lambda`.
    Log1pExp,
    /// `exp(raw)`: `poisson`, `gamma`, `tweedie`.
    Exp,
    /// Softmax over the class outputs: `multiclass` with this many classes.
    Softmax(usize),
}

impl Objective {
    /// Parse the value of the model file's `objective=` line, e.g. `"binary sigmoid:1"`,
    /// `"regression sqrt"` or `"multiclass num_class:4"`.
    #[cfg(feature = "text")]
    ///
    /// Tokens after the objective name are whitelisted per objective: an unrecognised token may
    /// change the output transform (as `sqrt` does), so it is refused rather than skipped. bosk
    /// audited the vocabulary against every LightGBM release from 2.1 through 4.6: `sqrt`,
    /// `sigmoid:<k>` and `num_class:<n>`.
    fn parse(value: &str, lineno: usize) -> Result<Self> {
        let mut tokens = value.split_whitespace();
        let name = tokens.next().unwrap_or("");
        match name {
            "binary" => {
                let mut k: f64 = 1.0;
                for tok in tokens {
                    match tok.strip_prefix("sigmoid:") {
                        Some(v) => k = parse_scalar(v, "objective sigmoid", lineno)?,
                        None => return Err(Self::unknown_token(name, tok)),
                    }
                }
                // `!(finite && positive)` also catches NaN, which passes a plain `k <= 0.0`.
                if !(k.is_finite() && k > 0.0) {
                    return Err(Error::Parse {
                        line: lineno,
                        message: format!("sigmoid parameter must be positive and finite, got {k}"),
                    });
                }
                Ok(Objective::Sigmoid(k))
            }
            "multiclass" => {
                let mut classes = None;
                for tok in tokens {
                    match tok.strip_prefix("num_class:") {
                        Some(v) => {
                            classes = Some(parse_scalar::<usize>(v, "objective num_class", lineno)?)
                        }
                        None => return Err(Self::unknown_token(name, tok)),
                    }
                }
                match classes {
                    Some(n) if n >= 2 => Ok(Objective::Softmax(n)),
                    _ => Err(Error::Parse {
                        line: lineno,
                        message: "multiclass objective needs num_class:<n> with n >= 2".into(),
                    }),
                }
            }
            "multiclassova" => Err(Error::Unsupported {
                message: "objective 'multiclassova' (one-vs-all) is not implemented".into(),
            }),
            // These five append `sqrt` when trained with `reg_sqrt=true` (`huber` does not,
            // even though it accepts the parameter).
            "regression" | "regression_l1" | "fair" | "quantile" | "mape" => {
                let mut sqrt = false;
                for tok in tokens {
                    match tok {
                        "sqrt" => sqrt = true,
                        _ => return Err(Self::unknown_token(name, tok)),
                    }
                }
                Ok(if sqrt {
                    Objective::Sqrt
                } else {
                    Objective::Identity
                })
            }
            "cross_entropy"
            | "cross_entropy_lambda"
            | "poisson"
            | "gamma"
            | "tweedie"
            | "huber"
            | "lambdarank"
            | "rank_xendcg"
            | "custom"
            | "none" => {
                if let Some(tok) = tokens.next() {
                    return Err(Self::unknown_token(name, tok));
                }
                Ok(match name {
                    "cross_entropy" => Objective::Sigmoid(1.0),
                    "cross_entropy_lambda" => Objective::Log1pExp,
                    "poisson" | "gamma" | "tweedie" => Objective::Exp,
                    _ => Objective::Identity,
                })
            }
            other => Err(Error::Unsupported {
                message: format!(
                    "objective '{other}' is not recognised; loading it would produce wrong predictions"
                ),
            }),
        }
    }

    /// The refusal for an objective-line token outside the whitelist.
    #[cfg(feature = "text")]
    fn unknown_token(name: &str, tok: &str) -> Error {
        Error::Unsupported {
            message: format!(
                "objective '{name}' carries unrecognised token {tok:?}, which may change the output \
                 transform; loading it would risk wrong predictions"
            ),
        }
    }

    /// Number of raw outputs per sample (trees per boosting iteration).
    fn outputs(self) -> usize {
        match self {
            Objective::Softmax(n) => n,
            _ => 1,
        }
    }

    fn transform(self, raw: &mut [f64]) {
        match self {
            Objective::Identity => {}
            // sign(raw) * raw^2, as LightGBM's `Common::Sign(input) * input * input`.
            Objective::Sqrt => raw[0] *= raw[0].abs(),
            Objective::Sigmoid(k) => raw[0] = 1.0 / (1.0 + (-k * raw[0]).exp()),
            Objective::Log1pExp => raw[0] = raw[0].exp().ln_1p(),
            Objective::Exp => raw[0] = raw[0].exp(),
            // As LightGBM's `Common::Softmax`: subtract the maximum, exponentiate, normalise.
            Objective::Softmax(_) => {
                let max = raw.iter().copied().fold(f64::NEG_INFINITY, f64::max);
                let mut sum = 0.0;
                for v in raw.iter_mut() {
                    *v = (*v - max).exp();
                    sum += *v;
                }
                for v in raw.iter_mut() {
                    *v /= sum;
                }
            }
        }
    }
}

/// A single decision tree in the ensemble.
///
/// Field arrays follow LightGBM's node encoding: for a tree with `num_leaves` leaves there are
/// `num_leaves - 1` internal nodes, so the per-node arrays have that length and `leaf_value` has
/// `num_leaves` entries. `left_child` / `right_child` hold an internal-node index when `>= 0`,
/// or a leaf index encoded as `!child` when `< 0`.
///
/// For a categorical node (`decision_type` bit 0 set), `threshold` holds an index into
/// `cat_boundaries`, whose consecutive pair `[lo, hi)` delimits the node's bitset in
/// `cat_threshold` (32 category bits per word).
///
/// These invariants are checked once by [`Tree::validate`] at load time, which lets
/// [`Tree::predict`] index without bounds concerns.
#[derive(Debug)]
struct Tree {
    num_leaves: usize,
    split_feature: Vec<usize>,
    threshold: Vec<f64>,
    left_child: Vec<i32>,
    right_child: Vec<i32>,
    leaf_value: Vec<f64>,
    decision_type: Vec<u8>,
    cat_boundaries: Vec<usize>,
    cat_threshold: Vec<u32>,
}

impl Tree {
    /// The raw leaf value for one sample, reading feature `i` as `value(i)`.
    fn predict(&self, value: &impl Fn(usize) -> f64) -> f64 {
        // A stump (single leaf, no splits) has no internal nodes to walk.
        if self.split_feature.is_empty() {
            return self.leaf_value[0];
        }
        let mut node: i32 = 0;
        loop {
            if node < 0 {
                // Leaf node: index = !node = -(node + 1)
                return self.leaf_value[(!node) as usize];
            }
            let idx = node as usize;
            let val = value(self.split_feature[idx]);
            // decision_type bit 0 selects categorical vs numerical.
            node = if self.decision_type[idx] & 1 != 0 {
                self.decide_categorical(idx, val)
            } else {
                self.decide_numerical(idx, val)
            };
        }
    }

    /// LightGBM's numerical decision: `decision_type` bit 1 is the default direction for missing
    /// values (set = left) and bits 2-3 encode the missing type (0 = none, 1 = zero, 2 = NaN).
    fn decide_numerical(&self, idx: usize, mut val: f64) -> i32 {
        let dt = self.decision_type[idx];
        let default_left = (dt & 2) != 0;
        let missing_type = (dt >> 2) & 3;

        // Unless NaN is itself the missing marker, LightGBM treats NaN as 0.
        if val.is_nan() && missing_type != 2 {
            val = 0.0;
        }
        // LightGBM's zero test is a band, not equality: IsZero(v) is |v| <= kZeroThreshold with
        // `const double kZeroThreshold = 1e-35f` (include/LightGBM/meta.h); the f32 literal is
        // deliberate.
        const K_ZERO_THRESHOLD: f64 = 1e-35_f32 as f64;
        let is_missing = (missing_type == 1
            && (-K_ZERO_THRESHOLD..=K_ZERO_THRESHOLD).contains(&val))
            || (missing_type == 2 && val.is_nan());

        if is_missing {
            if default_left {
                self.left_child[idx]
            } else {
                self.right_child[idx]
            }
        } else if val <= self.threshold[idx] {
            self.left_child[idx]
        } else {
            self.right_child[idx]
        }
    }

    /// LightGBM's categorical decision: NaN and negative categories go right; otherwise go left
    /// iff the category's bit is set in the node's bitset (an unseen category beyond the bitset
    /// goes right).
    fn decide_categorical(&self, idx: usize, val: f64) -> i32 {
        if val.is_nan() {
            return self.right_child[idx];
        }
        let cat = val as i64; // saturating cast, truncates toward zero
        if cat < 0 {
            return self.right_child[idx];
        }
        let cat_idx = self.threshold[idx] as usize;
        let bits =
            &self.cat_threshold[self.cat_boundaries[cat_idx]..self.cat_boundaries[cat_idx + 1]];
        let word = (cat as u64 >> 5) as usize;
        let found = word < bits.len() && (bits[word] >> (cat as u64 & 31)) & 1 == 1;
        if found {
            self.left_child[idx]
        } else {
            self.right_child[idx]
        }
    }

    /// Check the structural invariants documented on [`Tree`]. `header_line` is the 1-based line
    /// of the `Tree=` header, used for error context. `max_feature_idx` is the header's declared
    /// feature bound, when present.
    fn validate(&self, header_line: usize, max_feature_idx: Option<usize>) -> Result<()> {
        let err = |message: String| Error::Parse {
            line: header_line,
            message,
        };
        if self.num_leaves == 0 {
            return Err(err("num_leaves must be >= 1".into()));
        }
        if self.leaf_value.len() != self.num_leaves {
            return Err(err(format!(
                "num_leaves={} but {} leaf_value entries",
                self.num_leaves,
                self.leaf_value.len()
            )));
        }

        let internal = self.num_leaves - 1;
        for (name, len) in [
            ("split_feature", self.split_feature.len()),
            ("threshold", self.threshold.len()),
            ("decision_type", self.decision_type.len()),
            ("left_child", self.left_child.len()),
            ("right_child", self.right_child.len()),
        ] {
            if len != internal {
                return Err(err(format!(
                    "{name} has {len} entries, expected num_leaves-1 = {internal}"
                )));
            }
        }

        if self.cat_boundaries.windows(2).any(|w| w[0] > w[1])
            || self.cat_boundaries.last().copied().unwrap_or(0) > self.cat_threshold.len()
        {
            return Err(err(
                "cat_boundaries must be non-decreasing and within cat_threshold".into(),
            ));
        }

        // LightGBM stores feature indices as C ints, so even without a header bound anything
        // larger is corrupt (and keeping indices below i32::MAX means the `+ 1` deriving
        // `num_features` cannot overflow).
        let max_idx = max_feature_idx.unwrap_or(i32::MAX as usize - 1);
        for (k, &feat) in self.split_feature.iter().enumerate() {
            if feat > max_idx {
                return Err(err(format!(
                    "split_feature[{k}] = {feat} exceeds max_feature_idx = {max_idx}"
                )));
            }
        }

        for k in 0..internal {
            if self.decision_type[k] & 1 != 0 {
                let cat_idx = self.threshold[k];
                let max = self.cat_boundaries.len().saturating_sub(1);
                if cat_idx.fract() != 0.0 || cat_idx < 0.0 || cat_idx as usize >= max {
                    return Err(err(format!(
                        "categorical node {k} references invalid bitset index {cat_idx}"
                    )));
                }
            }
            for (side, child) in [
                ("left_child", self.left_child[k]),
                ("right_child", self.right_child[k]),
            ] {
                let ok = if child >= 0 {
                    (child as usize) < internal
                } else {
                    ((!child) as usize) < self.num_leaves
                };
                if !ok {
                    return Err(err(format!("{side}[{k}] = {child} is out of range")));
                }
            }
        }

        // Range checks alone admit cyclic child pointers, which would make `predict` loop
        // forever. Walk from the root: in a well-formed tree every internal node and every leaf
        // is reached exactly once.
        if internal > 0 {
            let mut node_seen = vec![false; internal];
            let mut leaf_seen = vec![false; self.num_leaves];
            let mut stack: Vec<i32> = vec![0];
            while let Some(child) = stack.pop() {
                let seen = if child >= 0 {
                    &mut node_seen[child as usize]
                } else {
                    &mut leaf_seen[(!child) as usize]
                };
                if *seen {
                    return Err(err(format!(
                        "node {child} is reachable more than once; child pointers do not form a tree"
                    )));
                }
                *seen = true;
                if child >= 0 {
                    stack.push(self.left_child[child as usize]);
                    stack.push(self.right_child[child as usize]);
                }
            }
            if node_seen.iter().any(|&v| !v) || leaf_seen.iter().any(|&v| !v) {
                return Err(err(
                    "tree has internal nodes or leaves unreachable from the root".into(),
                ));
            }
        }
        Ok(())
    }
}

/// One sample's non-zero features, sorted by feature index. Absent features read as zero, as
/// in LightGBM's sparse (CSR) input.
#[derive(Debug, Clone, Default)]
pub struct SparseRow {
    indices: Vec<u32>,
    values: Vec<f64>,
}

impl SparseRow {
    /// Build from `(feature index, value)` pairs in any order. For a repeated index the last
    /// pair wins.
    pub fn new(mut pairs: Vec<(u32, f64)>) -> Self {
        pairs.sort_by_key(|&(i, _)| i); // stable: the last of equal indices stays last
        let mut row = SparseRow::default();
        for (i, v) in pairs {
            if row.indices.last() == Some(&i) {
                *row.values.last_mut().unwrap() = v;
            } else {
                row.indices.push(i);
                row.values.push(v);
            }
        }
        row
    }

    /// The value of feature `i`, zero when absent.
    pub fn get(&self, i: usize) -> f64 {
        let Ok(i) = u32::try_from(i) else { return 0.0 };
        match self.indices.binary_search(&i) {
            Ok(k) => self.values[k],
            Err(_) => 0.0,
        }
    }
}

/// A LightGBM model parsed from the text format.
#[derive(Debug)]
pub struct LgbModel {
    trees: Vec<Tree>,
    objective: Objective,
    /// Random-forest mode (`average_output` header): tree outputs are averaged rather than
    /// summed.
    average_output: bool,
    /// Feature count the model was trained on: `max_feature_idx + 1` from the header, or the
    /// highest split feature + 1 when the header is absent.
    num_features: usize,
}

/// Parse a whitespace-separated list of values, attributing any failure to `field` on `line`.
#[cfg(feature = "text")]
fn parse_list<T>(s: &str, field: &str, line: usize) -> Result<Vec<T>>
where
    T: FromStr,
    T::Err: std::fmt::Display,
{
    s.split_whitespace()
        .map(|tok| {
            tok.parse::<T>().map_err(|e| Error::Parse {
                line,
                message: format!("{field}: invalid value {tok:?}: {e}"),
            })
        })
        .collect()
}

/// Parse a single scalar value, attributing any failure to `field` on `line`.
#[cfg(feature = "text")]
fn parse_scalar<T>(s: &str, field: &str, line: usize) -> Result<T>
where
    T: FromStr,
    T::Err: std::fmt::Display,
{
    s.trim().parse::<T>().map_err(|e| Error::Parse {
        line,
        message: format!("{field}: {e}"),
    })
}

impl LgbModel {
    /// Parse a model from the contents of a LightGBM text file. Native only (feature `text`):
    /// the WASM reads the packed form from [`binary`].
    ///
    /// Returns [`Error::Unsupported`] for models this module cannot evaluate faithfully: a
    /// refusal to load is preferred over silently wrong predictions. A file without an
    /// `objective=` line (LightGBM itself always writes one) is evaluated with the identity
    /// transform, i.e. raw scores.
    #[cfg(feature = "text")]
    pub fn parse(content: &str) -> Result<Self> {
        let lines: Vec<&str> = content.lines().collect();

        // Header: everything before the first tree section.
        let mut objective = Objective::Identity;
        let mut average_output = false;
        let mut max_feature_idx: Option<usize> = None;
        let mut num_class: usize = 1;
        let mut trees_per_iteration: usize = 1;
        for (i, line) in lines.iter().enumerate() {
            if line.starts_with("Tree=") {
                break;
            }
            if *line == "average_output" {
                average_output = true;
                continue;
            }
            let Some((key, v)) = line.split_once('=') else {
                continue;
            };
            match key {
                "objective" => objective = Objective::parse(v, i + 1)?,
                "max_feature_idx" => {
                    let m: usize = parse_scalar(v, key, i + 1)?;
                    // LightGBM stores feature indices as C ints; anything larger is a corrupt
                    // file (and `m + 1` below must not overflow).
                    if m >= i32::MAX as usize {
                        return Err(Error::Parse {
                            line: i + 1,
                            message: format!("max_feature_idx = {m} is out of range"),
                        });
                    }
                    max_feature_idx = Some(m);
                }
                "num_class" => num_class = parse_scalar(v, key, i + 1)?,
                "num_tree_per_iteration" => trees_per_iteration = parse_scalar(v, key, i + 1)?,
                _ => {}
            }
        }
        // The objective, the class count and the trees per iteration must agree, or trees
        // would be summed into the wrong outputs.
        let outputs = objective.outputs();
        if num_class != outputs || trees_per_iteration != outputs {
            return Err(Error::Unsupported {
                message: format!(
                    "objective {objective:?} with num_class={num_class} and \
                     num_tree_per_iteration={trees_per_iteration}"
                ),
            });
        }

        let mut trees = Vec::new();
        let mut i = 0;
        while i < lines.len() {
            if !lines[i].starts_with("Tree=") {
                i += 1;
                continue;
            }
            let header_line = i + 1;
            i += 1;

            let mut num_leaves: Option<usize> = None;
            let mut split_feature = Vec::new();
            let mut threshold = Vec::new();
            let mut left_child = Vec::new();
            let mut right_child = Vec::new();
            let mut leaf_value = Vec::new();
            let mut decision_type = Vec::new();
            let mut cat_boundaries = Vec::new();
            let mut cat_threshold = Vec::new();

            while i < lines.len() && !lines[i].starts_with("Tree=") {
                let lineno = i + 1;
                let kv = lines[i].split_once('=');
                i += 1;
                let Some((key, v)) = kv else { continue };
                match key {
                    "num_leaves" => num_leaves = Some(parse_scalar(v, key, lineno)?),
                    "split_feature" => split_feature = parse_list(v, key, lineno)?,
                    "threshold" => threshold = parse_list(v, key, lineno)?,
                    "decision_type" => decision_type = parse_list(v, key, lineno)?,
                    "left_child" => left_child = parse_list(v, key, lineno)?,
                    "right_child" => right_child = parse_list(v, key, lineno)?,
                    "leaf_value" => leaf_value = parse_list(v, key, lineno)?,
                    "cat_boundaries" => cat_boundaries = parse_list(v, key, lineno)?,
                    "cat_threshold" => cat_threshold = parse_list(v, key, lineno)?,
                    "is_linear" => {
                        let is_linear: u8 = parse_scalar(v, key, lineno)?;
                        if is_linear != 0 {
                            return Err(Error::Unsupported {
                                message: "linear trees (is_linear=1) are not supported".into(),
                            });
                        }
                    }
                    _ => {}
                }
            }

            // A section without num_leaves is not a tree body (e.g. trailing metadata that
            // happens to follow the last `Tree=`); skip it.
            let Some(num_leaves) = num_leaves else {
                continue;
            };
            let tree = Tree {
                num_leaves,
                split_feature,
                threshold,
                left_child,
                right_child,
                leaf_value,
                decision_type,
                cat_boundaries,
                cat_threshold,
            };
            tree.validate(header_line, max_feature_idx)?;
            trees.push(tree);
        }

        if trees.is_empty() {
            return Err(Error::EmptyModel);
        }
        if trees.len() % outputs != 0 {
            return Err(Error::Parse {
                line: 0,
                message: format!(
                    "{} trees do not split evenly into {outputs} outputs",
                    trees.len()
                ),
            });
        }

        let max_split = trees.iter().flat_map(|t| &t.split_feature).max().copied();
        let num_features = match (max_feature_idx, max_split) {
            (Some(m), _) => m + 1,
            (None, Some(s)) => s + 1,
            (None, None) => 0,
        };

        Ok(Self {
            trees,
            objective,
            average_output,
            num_features,
        })
    }

    /// The number of features the model was trained on.
    #[must_use]
    pub fn num_features(&self) -> usize {
        self.num_features
    }

    /// The number of trees in the ensemble.
    #[must_use]
    pub fn num_trees(&self) -> usize {
        self.trees.len()
    }

    /// The number of values per prediction: the class count for multiclass, else 1.
    #[must_use]
    pub fn num_outputs(&self) -> usize {
        self.objective.outputs()
    }

    /// Raw scores, one per output, reading feature `i` as `value(i)`. Tree `t` adds to output
    /// `t % num_outputs`, as LightGBM stores one tree per output for each boosting iteration.
    pub fn predict_raw_with(&self, value: impl Fn(usize) -> f64) -> Vec<f64> {
        let outputs = self.num_outputs();
        let mut raw = vec![0.0; outputs];
        for (t, tree) in self.trees.iter().enumerate() {
            raw[t % outputs] += tree.predict(&value);
        }
        if self.average_output {
            let per_output = (self.trees.len() / outputs) as f64;
            for r in &mut raw {
                *r /= per_output;
            }
        }
        raw
    }

    /// Raw scores for a dense feature vector. Refuses a vector whose length is not
    /// [`num_features`](Self::num_features): the missing tail would silently read as missing.
    pub fn predict_raw(&self, features: &[f64]) -> Result<Vec<f64>> {
        self.check_len(features)?;
        Ok(self.predict_raw_with(|i| features.get(i).copied().unwrap_or(f64::NAN)))
    }

    /// Raw scores for a sparse row: absent features are zero.
    #[must_use]
    pub fn predict_raw_sparse(&self, row: &SparseRow) -> Vec<f64> {
        self.predict_raw_with(|i| row.get(i))
    }

    /// Predictions (the objective's output transform applied) for a dense feature vector.
    pub fn predict(&self, features: &[f64]) -> Result<Vec<f64>> {
        let mut out = self.predict_raw(features)?;
        self.objective.transform(&mut out);
        Ok(out)
    }

    /// Predictions (the objective's output transform applied) for a sparse row.
    #[must_use]
    pub fn predict_sparse(&self, row: &SparseRow) -> Vec<f64> {
        let mut out = self.predict_raw_sparse(row);
        self.objective.transform(&mut out);
        out
    }

    fn check_len(&self, features: &[f64]) -> Result<()> {
        if features.len() != self.num_features {
            return Err(Error::FeatureCount {
                expected: self.num_features,
                got: features.len(),
            });
        }
        Ok(())
    }
}

#[cfg(all(test, feature = "text"))]
mod tests;

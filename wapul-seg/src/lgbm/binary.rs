//! A packed binary form of [`LgbModel`]: what the WASM loads instead of parsing LightGBM's text
//! format at runtime. Written by `model-pack` (see `src/bin/model_pack.rs`) from the text model
//! and read back here; the trees are stored as they are evaluated, so predictions are identical.
//!
//! Little-endian throughout. A model is: objective tag `u8` and parameter `f64`,
//! `average_output` `u8`, `num_features` `u32`, tree count `u32`, then each tree as
//! `num_leaves` `u32`, `split_feature` `u32[]`, `threshold` `f64[]`, `decision_type` `u8[]`,
//! `left_child` `i32[]`, `right_child` `i32[]` (each `num_leaves - 1` long), `leaf_value`
//! `f64[num_leaves]`, and the categorical bitsets as `u32` count + `u32[]` twice.

use super::{Error, LgbModel, Objective, Result, Tree};

/// A cursor over packed bytes whose reads fail with the offset instead of panicking.
pub struct Reader<'a> {
    data: &'a [u8],
    pos: usize,
}

impl<'a> Reader<'a> {
    pub fn new(data: &'a [u8]) -> Self {
        Self { data, pos: 0 }
    }

    pub fn is_empty(&self) -> bool {
        self.pos >= self.data.len()
    }

    fn take(&mut self, n: usize) -> Result<&'a [u8]> {
        let end = self.pos.checked_add(n).filter(|&e| e <= self.data.len());
        match end {
            Some(end) => {
                let out = &self.data[self.pos..end];
                self.pos = end;
                Ok(out)
            }
            None => Err(Error::Binary {
                message: format!("truncated at byte {} (wanted {n} more)", self.pos),
            }),
        }
    }

    pub fn u8(&mut self) -> Result<u8> {
        Ok(self.take(1)?[0])
    }

    pub fn u32(&mut self) -> Result<u32> {
        Ok(u32::from_le_bytes(self.take(4)?.try_into().unwrap()))
    }

    pub fn i32(&mut self) -> Result<i32> {
        Ok(i32::from_le_bytes(self.take(4)?.try_into().unwrap()))
    }

    pub fn u64(&mut self) -> Result<u64> {
        Ok(u64::from_le_bytes(self.take(8)?.try_into().unwrap()))
    }

    pub fn f64(&mut self) -> Result<f64> {
        Ok(f64::from_le_bytes(self.take(8)?.try_into().unwrap()))
    }

    /// A length-prefixed list, the length as `u32`. Refuses lengths beyond the remaining bytes
    /// before allocating.
    pub fn list<T>(
        &mut self,
        size: usize,
        read: impl Fn(&mut Self) -> Result<T>,
    ) -> Result<Vec<T>> {
        let n = self.u32()? as usize;
        if n.saturating_mul(size) > self.data.len() - self.pos {
            return Err(Error::Binary {
                message: format!("list of {n} at byte {} runs past the end", self.pos),
            });
        }
        (0..n).map(|_| read(self)).collect()
    }
}

/// Growable output with the same encodings as [`Reader`].
pub struct Writer(pub Vec<u8>);

impl Writer {
    pub fn u8(&mut self, v: u8) {
        self.0.push(v);
    }

    pub fn u32(&mut self, v: u32) {
        self.0.extend_from_slice(&v.to_le_bytes());
    }

    pub fn i32(&mut self, v: i32) {
        self.0.extend_from_slice(&v.to_le_bytes());
    }

    pub fn u64(&mut self, v: u64) {
        self.0.extend_from_slice(&v.to_le_bytes());
    }

    pub fn f64(&mut self, v: f64) {
        self.0.extend_from_slice(&v.to_le_bytes());
    }

    pub fn list<T>(&mut self, items: &[T], write: impl Fn(&mut Self, &T)) {
        self.u32(items.len() as u32);
        for item in items {
            write(self, item);
        }
    }
}

impl Objective {
    fn write(self, w: &mut Writer) {
        let (tag, param) = match self {
            Objective::Identity => (0, 0.0),
            Objective::Sqrt => (1, 0.0),
            Objective::Sigmoid(k) => (2, k),
            Objective::Log1pExp => (3, 0.0),
            Objective::Exp => (4, 0.0),
            Objective::Softmax(n) => (5, n as f64),
        };
        w.u8(tag);
        w.f64(param);
    }

    fn read(r: &mut Reader) -> Result<Self> {
        let tag = r.u8()?;
        let param = r.f64()?;
        Ok(match tag {
            0 => Objective::Identity,
            1 => Objective::Sqrt,
            2 if param.is_finite() && param > 0.0 => Objective::Sigmoid(param),
            3 => Objective::Log1pExp,
            4 => Objective::Exp,
            5 if param >= 2.0 && param.fract() == 0.0 => Objective::Softmax(param as usize),
            _ => {
                return Err(Error::Binary {
                    message: format!("objective tag {tag} with parameter {param}"),
                });
            }
        })
    }
}

impl Tree {
    fn write(&self, w: &mut Writer) {
        w.u32(self.num_leaves as u32);
        for &f in &self.split_feature {
            w.u32(f as u32);
        }
        for &t in &self.threshold {
            w.f64(t);
        }
        for &d in &self.decision_type {
            w.u8(d);
        }
        for &c in &self.left_child {
            w.i32(c);
        }
        for &c in &self.right_child {
            w.i32(c);
        }
        for &v in &self.leaf_value {
            w.f64(v);
        }
        w.list(&self.cat_boundaries, |w, &b| w.u32(b as u32));
        w.list(&self.cat_threshold, |w, &b| w.u32(b));
    }

    fn read(r: &mut Reader, max_feature_idx: usize) -> Result<Self> {
        let num_leaves = r.u32()? as usize;
        let internal = num_leaves.checked_sub(1).ok_or_else(|| Error::Binary {
            message: "tree with no leaves".into(),
        })?;
        let mut split_feature = Vec::with_capacity(internal);
        for _ in 0..internal {
            split_feature.push(r.u32()? as usize);
        }
        let mut threshold = Vec::with_capacity(internal);
        for _ in 0..internal {
            threshold.push(r.f64()?);
        }
        let decision_type = r.take(internal)?.to_vec();
        let mut left_child = Vec::with_capacity(internal);
        for _ in 0..internal {
            left_child.push(r.i32()?);
        }
        let mut right_child = Vec::with_capacity(internal);
        for _ in 0..internal {
            right_child.push(r.i32()?);
        }
        let mut leaf_value = Vec::with_capacity(num_leaves);
        for _ in 0..num_leaves {
            leaf_value.push(r.f64()?);
        }
        let cat_boundaries = r.list(4, |r| Ok(r.u32()? as usize))?;
        let cat_threshold = r.list(4, |r| r.u32())?;
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
        // The same structural checks as the text loader, so corrupt bytes cannot make
        // `predict` loop or index out of range
        tree.validate(0, Some(max_feature_idx))?;
        Ok(tree)
    }
}

impl LgbModel {
    /// Append the packed form to `w`.
    pub fn write(&self, w: &mut Writer) {
        self.objective.write(w);
        w.u8(u8::from(self.average_output));
        w.u32(self.num_features as u32);
        w.list(&self.trees, |w, t| t.write(w));
    }

    /// Read a packed model written by [`LgbModel::write`].
    pub fn read(r: &mut Reader) -> Result<Self> {
        let objective = Objective::read(r)?;
        let average_output = r.u8()? != 0;
        let num_features = r.u32()? as usize;
        let max_feature_idx = num_features.checked_sub(1).ok_or_else(|| Error::Binary {
            message: "model with no features".into(),
        })?;
        let trees = r.list(4, |r| Tree::read(r, max_feature_idx))?;
        if trees.is_empty() {
            return Err(Error::EmptyModel);
        }
        let outputs = objective.outputs();
        if !trees.len().is_multiple_of(outputs) {
            return Err(Error::Binary {
                message: format!(
                    "{} trees do not split evenly into {outputs} outputs",
                    trees.len()
                ),
            });
        }
        Ok(Self {
            trees,
            objective,
            average_output,
            num_features,
        })
    }
}

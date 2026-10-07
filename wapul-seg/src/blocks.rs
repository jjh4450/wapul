//! Logic blocks from candidate rows: a copy of `BlockCandidates.block_rows` in wapul-ml's
//! `features/candidates.py` and `predict_blocks` in `models/block_ranker.py`, the originals.
//! Change them together and rerun the parity check (docs/ml/deploy.ko.md, "검증").
//!
//! Each logic unit, in code order, joins the best-scoring block built so far or opens a new one.
//! Rows are float32, as the original's numpy and torch arrays are, so scores agree.

/// Per-unit features: one flag per category (`CATEGORIES` in `unit_ast.py`), header, depth.
pub const N_OWN: usize = 11;
/// Per-pair features: the 11 SEGMENT rules, adjacent, log distance, depth change.
pub const N_PAIR: usize = 14;
/// Candidate row: new-block flag, pair max, pair mean, size, distance, is-last, own.
pub const WIDTH: usize = 1 + 2 * N_PAIR + 3 + N_OWN;

/// The logic units of one solution: `own` is `N_OWN` values per unit; `pairs` is `N_PAIR`
/// values for every (earlier unit c, unit t) pair, ordered by t then c.
pub struct Logic<'a> {
    own: &'a [f32],
    pairs: &'a [f32],
    n: usize,
}

impl<'a> Logic<'a> {
    pub fn new(own: &'a [f32], pairs: &'a [f32]) -> Result<Self, String> {
        if !own.len().is_multiple_of(N_OWN) {
            return Err(format!(
                "own has {} values, not a multiple of {N_OWN}",
                own.len()
            ));
        }
        let n = own.len() / N_OWN;
        let want = n * n.saturating_sub(1) / 2 * N_PAIR;
        if pairs.len() != want {
            return Err(format!(
                "pairs has {} values, {n} units need {want}",
                pairs.len()
            ));
        }
        Ok(Self { own, pairs, n })
    }

    pub fn len(&self) -> usize {
        self.n
    }

    pub fn is_empty(&self) -> bool {
        self.n == 0
    }

    fn own(&self, t: usize) -> &[f32] {
        &self.own[t * N_OWN..][..N_OWN]
    }

    fn pair(&self, t: usize, c: usize) -> &[f32] {
        &self.pairs[(t * (t - 1) / 2 + c) * N_PAIR..][..N_PAIR]
    }

    /// One row per block built before unit t, then t itself as a new block, back to back.
    pub fn block_rows(&self, t: usize, groups: &[Vec<usize>]) -> Vec<f32> {
        let own = self.own(t);
        let last = groups.iter().filter_map(|g| g.last().copied()).max();
        let mut rows = Vec::with_capacity((groups.len() + 1) * WIDTH);
        for g in groups {
            let mut max = [f32::NEG_INFINITY; N_PAIR];
            let mut sum = [0.0f32; N_PAIR];
            for &c in g {
                for (k, &v) in self.pair(t, c).iter().enumerate() {
                    max[k] = max[k].max(v);
                    sum[k] += v;
                }
            }
            let end = *g.last().expect("a block holds a unit");
            rows.push(0.0);
            rows.extend(max);
            rows.extend(sum.iter().map(|s| s / g.len() as f32));
            rows.push((g.len() as f64).ln_1p() as f32);
            rows.push(((t - end) as f64).ln_1p() as f32);
            rows.push(if Some(end) == last { 1.0 } else { 0.0 });
            rows.extend_from_slice(own);
        }
        rows.push(1.0);
        rows.extend([0.0; 2 * N_PAIR + 3]);
        rows.extend_from_slice(own);
        rows
    }
}

/// Block number from 0 per logic unit. `score` returns one score per `WIDTH`-wide row; the
/// first highest wins, as `numpy.argmax`.
pub fn decode(logic: &Logic, mut score: impl FnMut(&[f32]) -> Vec<f64>) -> Vec<u32> {
    let mut groups: Vec<Vec<usize>> = Vec::new();
    let mut out = Vec::with_capacity(logic.len());
    for t in 0..logic.len() {
        let scores = score(&logic.block_rows(t, &groups));
        let best = (0..scores.len()).fold(0, |b, i| if scores[i] > scores[b] { i } else { b });
        if best == groups.len() {
            groups.push(Vec::new());
        }
        groups[best].push(t);
        out.push(best as u32);
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn logic(n: usize) -> (Vec<f32>, Vec<f32>) {
        let own: Vec<f32> = (0..n * N_OWN).map(|i| i as f32).collect();
        let pairs: Vec<f32> = (0..n * (n - 1) / 2 * N_PAIR)
            .map(|i| (i % 7) as f32)
            .collect();
        (own, pairs)
    }

    #[test]
    fn rejects_wrong_lengths() {
        assert!(Logic::new(&[0.0; N_OWN + 1], &[]).is_err());
        assert!(Logic::new(&[0.0; 2 * N_OWN], &[0.0; N_PAIR - 1]).is_err());
        assert_eq!(Logic::new(&[], &[]).unwrap().len(), 0);
    }

    #[test]
    fn rows_follow_the_python_layout() {
        let (own, pairs) = logic(3);
        let l = Logic::new(&own, &pairs).unwrap();
        // t = 2 with blocks [0] and [1]: two block rows, then the new-block row
        let rows = l.block_rows(2, &[vec![0], vec![1]]);
        assert_eq!(rows.len(), 3 * WIDTH);
        let (r0, r1, new) = (&rows[..WIDTH], &rows[WIDTH..2 * WIDTH], &rows[2 * WIDTH..]);
        assert_eq!(r0[0], 0.0);
        assert_eq!(&r0[1..1 + N_PAIR], l.pair(2, 0));
        assert_eq!(&r0[1 + N_PAIR..1 + 2 * N_PAIR], l.pair(2, 0));
        assert_eq!(r0[1 + 2 * N_PAIR], (2f64).ln() as f32);
        assert_eq!(r0[2 + 2 * N_PAIR], (3f64).ln() as f32);
        assert_eq!(r0[3 + 2 * N_PAIR], 0.0);
        assert_eq!(r1[3 + 2 * N_PAIR], 1.0);
        assert_eq!(&r0[4 + 2 * N_PAIR..], l.own(2));
        assert_eq!(new[0], 1.0);
        assert!(new[1..1 + 2 * N_PAIR + 3].iter().all(|&v| v == 0.0));
        assert_eq!(&new[4 + 2 * N_PAIR..], l.own(2));
    }

    #[test]
    fn decode_follows_the_best_row() {
        let (own, pairs) = logic(4);
        let l = Logic::new(&own, &pairs).unwrap();
        let new_block = |rows: &[f32]| rows.chunks(WIDTH).map(|r| f64::from(r[0])).collect();
        assert_eq!(decode(&l, new_block), vec![0, 1, 2, 3]);
        let first_block = |rows: &[f32]| rows.chunks(WIDTH).map(|r| -f64::from(r[0])).collect();
        assert_eq!(decode(&l, first_block), vec![0, 0, 0, 0]);
        assert!(decode(&Logic::new(&[], &[]).unwrap(), new_block).is_empty());
    }
}

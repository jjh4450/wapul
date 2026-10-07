//! Logic blocks from the units' AST facts: a copy of `segment_features` in wapul-ml's
//! `features/unit_ast.py`, `Units` and `BlockCandidates.block_rows` in `features/candidates.py`
//! and `predict_blocks` in `models/block_ranker.py`, the originals. Change them together and
//! rerun the parity check (docs/ml/deploy.ko.md, "검증").
//!
//! Each logic unit, in code order, joins the best-scoring block built so far or opens a new one.
//! Pair features are computed as each unit is placed, so memory stays linear in the unit count
//! (the original keeps every pair). Rows are float32, as the original's numpy and torch arrays
//! are, so scores agree.

/// Per-unit features: one flag per category (`CATEGORIES` in `unit_ast.py`), header, depth.
pub const N_OWN: usize = 11;
/// Per-unit AST facts, as `i32`: category, node type id, is header, depth, span start, span end,
/// innermost loop, innermost control, enclosing function, parent (start indices, -1 for none).
pub const N_FACTS: usize = 10;
/// Per-pair features: the 11 SEGMENT rules, adjacent, log distance, depth change.
pub const N_PAIR: usize = 14;
/// Candidate row: new-block flag, pair max, pair mean, size, distance, is-last, own.
pub const WIDTH: usize = 1 + 2 * N_PAIR + 3 + N_OWN;

const CATEGORY: usize = 0;
const NODE_TYPE: usize = 1;
const IS_HEADER: usize = 2;
const DEPTH: usize = 3;
const SPAN_START: usize = 4;
const SPAN_END: usize = 5;
const LOOP: usize = 6;
const CONTROL: usize = 7;
const FUNCTION: usize = 8;
const PARENT: usize = 9;

/// The logic units of one solution. `own` is `N_OWN` values and `facts` `N_FACTS` values per
/// unit; `reads` and `writes` hold each unit's identifier ids, sorted, with `*_offsets`
/// delimiting unit t's as `[offsets[t], offsets[t + 1])`.
pub struct Logic<'a> {
    own: &'a [f32],
    facts: &'a [i32],
    reads_offsets: &'a [u32],
    reads: &'a [u32],
    writes_offsets: &'a [u32],
    writes: &'a [u32],
    n: usize,
}

fn check_sets(name: &str, n: usize, offsets: &[u32], ids: &[u32]) -> Result<(), String> {
    if offsets.len() != n + 1 {
        return Err(format!(
            "{name} offsets has {} entries, {n} units need {}",
            offsets.len(),
            n + 1
        ));
    }
    if offsets[0] != 0 || offsets[n] as usize != ids.len() {
        return Err(format!("{name} offsets do not span {} ids", ids.len()));
    }
    for t in 0..n {
        let (s, e) = (offsets[t] as usize, offsets[t + 1] as usize);
        if s > e || !ids[s..e].is_sorted() {
            return Err(format!("{name} of unit {t} are not a sorted range"));
        }
    }
    Ok(())
}

/// How many ids two sorted lists share.
fn shared(a: &[u32], b: &[u32]) -> usize {
    let (mut i, mut j, mut n) = (0, 0, 0);
    while i < a.len() && j < b.len() {
        match a[i].cmp(&b[j]) {
            std::cmp::Ordering::Less => i += 1,
            std::cmp::Ordering::Greater => j += 1,
            std::cmp::Ordering::Equal => {
                n += 1;
                i += 1;
                j += 1;
            }
        }
    }
    n
}

impl<'a> Logic<'a> {
    pub fn new(
        own: &'a [f32],
        facts: &'a [i32],
        reads_offsets: &'a [u32],
        reads: &'a [u32],
        writes_offsets: &'a [u32],
        writes: &'a [u32],
    ) -> Result<Self, String> {
        if !own.len().is_multiple_of(N_OWN) {
            return Err(format!(
                "own has {} values, not a multiple of {N_OWN}",
                own.len()
            ));
        }
        let n = own.len() / N_OWN;
        if facts.len() != n * N_FACTS {
            return Err(format!(
                "facts has {} values, {n} units need {}",
                facts.len(),
                n * N_FACTS
            ));
        }
        check_sets("reads", n, reads_offsets, reads)?;
        check_sets("writes", n, writes_offsets, writes)?;
        Ok(Self {
            own,
            facts,
            reads_offsets,
            reads,
            writes_offsets,
            writes,
            n,
        })
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

    fn fact(&self, t: usize, k: usize) -> i32 {
        self.facts[t * N_FACTS + k]
    }

    fn reads(&self, t: usize) -> &[u32] {
        &self.reads[self.reads_offsets[t] as usize..self.reads_offsets[t + 1] as usize]
    }

    fn writes(&self, t: usize) -> &[u32] {
        &self.writes[self.writes_offsets[t] as usize..self.writes_offsets[t + 1] as usize]
    }

    /// The pair features of unit c before unit t: the SEGMENT rules (data-flow chain, control
    /// block, same syntactic category), adjacency, log distance and depth change.
    pub fn pair(&self, c: usize, t: usize) -> [f32; N_PAIR] {
        let b = |v: bool| if v { 1.0 } else { 0.0 };
        let same = |k: usize| b(self.fact(c, k) == self.fact(t, k));
        let (rc, rt, wc, wt) = (self.reads(c), self.reads(t), self.writes(c), self.writes(t));
        let shared_reads = shared(rc, rt);
        let union = rc.len() + rt.len() - shared_reads;
        [
            b(shared(wc, rt) > 0),
            b(shared(wt, rc) > 0),
            b(shared(wc, wt) > 0),
            (shared_reads as f64 / union.max(1) as f64) as f32,
            b(self.fact(c, IS_HEADER) != 0
                && self.fact(c, SPAN_START) <= self.fact(t, SPAN_START)
                && self.fact(t, SPAN_END) <= self.fact(c, SPAN_END)),
            same(CONTROL),
            same(LOOP),
            same(FUNCTION),
            same(PARENT),
            same(CATEGORY),
            same(NODE_TYPE),
            b(t - c == 1),
            ((t - c) as f64).ln_1p() as f32,
            (self.fact(t, DEPTH) - self.fact(c, DEPTH)) as f32,
        ]
    }

    /// Every pair, ordered by t then c: what the original's `Units.pairs` holds (parity check).
    pub fn all_pairs(&self) -> Vec<f32> {
        let mut out = Vec::with_capacity(self.n * self.n.saturating_sub(1) / 2 * N_PAIR);
        for t in 0..self.n {
            for c in 0..t {
                out.extend(self.pair(c, t));
            }
        }
        out
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
                for (k, v) in self.pair(c, t).into_iter().enumerate() {
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

    /// Three units: `x = 1` (writes x), `if (x)` header spanning the third, `y = x + 1` inside.
    struct Case {
        own: Vec<f32>,
        facts: Vec<i32>,
        reads_offsets: Vec<u32>,
        reads: Vec<u32>,
        writes_offsets: Vec<u32>,
        writes: Vec<u32>,
    }

    fn case() -> Case {
        let mut own = vec![0.0; 3 * N_OWN];
        own[7] = 1.0; // unit 0: expression
        own[N_OWN + 3] = 1.0; // unit 1: branch
        own[N_OWN + 9] = 1.0; // header
        own[2 * N_OWN + 7] = 1.0; // unit 2: expression
        own[2 * N_OWN + 10] = 1.0; // depth 1
        #[rustfmt::skip]
        let facts = vec![
            //cat node hdr depth span0 span1 loop control fn parent
            7, 1, 0, 0, 0, 6, -1, -1, 0, 0,
            3, 2, 1, 0, 8, 30, -1, -1, 0, 0,
            7, 1, 0, 1, 18, 28, -1, 8, 0, 8,
        ];
        Case {
            own,
            facts,
            reads_offsets: vec![0, 1, 2, 4],
            reads: vec![0, 0, 0, 1], // x | x | x y
            writes_offsets: vec![0, 1, 1, 2],
            writes: vec![0, 1], // x | - | y
        }
    }

    fn logic(c: &Case) -> Logic<'_> {
        Logic::new(
            &c.own,
            &c.facts,
            &c.reads_offsets,
            &c.reads,
            &c.writes_offsets,
            &c.writes,
        )
        .unwrap()
    }

    #[test]
    fn rejects_wrong_shapes() {
        let c = case();
        assert!(
            Logic::new(
                &c.own[1..],
                &c.facts,
                &c.reads_offsets,
                &c.reads,
                &c.writes_offsets,
                &c.writes
            )
            .is_err()
        );
        assert!(
            Logic::new(
                &c.own,
                &c.facts[1..],
                &c.reads_offsets,
                &c.reads,
                &c.writes_offsets,
                &c.writes
            )
            .is_err()
        );
        assert!(
            Logic::new(
                &c.own,
                &c.facts,
                &[0, 1, 2],
                &c.reads,
                &c.writes_offsets,
                &c.writes
            )
            .is_err()
        );
        let unsorted = [0, 0, 1, 0];
        assert!(
            Logic::new(
                &c.own,
                &c.facts,
                &c.reads_offsets,
                &unsorted,
                &c.writes_offsets,
                &c.writes
            )
            .is_err()
        );
        assert_eq!(Logic::new(&[], &[], &[0], &[], &[0], &[]).unwrap().len(), 0);
    }

    #[test]
    fn pair_follows_the_segment_rules() {
        let c = case();
        let l = logic(&c);
        // unit 0 writes x, unit 2 reads x: data-flow; different parent and depth; two apart
        let p = l.pair(0, 2);
        assert_eq!(&p[..4], &[1.0, 0.0, 0.0, 0.5]);
        assert_eq!(&p[4..11], &[0.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0]);
        assert_eq!(&p[11..], &[0.0, (3f64).ln() as f32, 1.0]);
        // unit 1 is the header whose span holds unit 2
        let p = l.pair(1, 2);
        assert_eq!(p[4], 1.0);
        assert_eq!(p[11], 1.0);
        assert_eq!(l.all_pairs().len(), 3 * N_PAIR);
    }

    #[test]
    fn rows_follow_the_python_layout() {
        let c = case();
        let l = logic(&c);
        let rows = l.block_rows(2, &[vec![0], vec![1]]);
        assert_eq!(rows.len(), 3 * WIDTH);
        let (r0, r1, new) = (&rows[..WIDTH], &rows[WIDTH..2 * WIDTH], &rows[2 * WIDTH..]);
        assert_eq!(r0[0], 0.0);
        assert_eq!(&r0[1..1 + N_PAIR], &l.pair(0, 2));
        assert_eq!(&r0[1 + N_PAIR..1 + 2 * N_PAIR], &l.pair(0, 2));
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
        let c = case();
        let l = logic(&c);
        let new_block = |rows: &[f32]| rows.chunks(WIDTH).map(|r| f64::from(r[0])).collect();
        assert_eq!(decode(&l, new_block), vec![0, 1, 2]);
        let first_block = |rows: &[f32]| rows.chunks(WIDTH).map(|r| -f64::from(r[0])).collect();
        assert_eq!(decode(&l, first_block), vec![0, 0, 0]);
    }
}

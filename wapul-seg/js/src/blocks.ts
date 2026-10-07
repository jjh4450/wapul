// Block features of the logic units, in the form the WASM `blocks` takes: a copy of `Units`
// in wapul-ml's wapul_ml/features/candidates.py, the original. The candidate rows and the
// grouping are the WASM's (wapul-seg/src/blocks.rs).

import { segmentFeatures, type UnitAst } from './ast.ts';
import { CATEGORIES } from './languages.ts';

/** Per unit: one flag per category, header, depth. */
export const N_OWN = CATEGORIES.length + 2;

/** Per pair: the 11 SEGMENT rules, adjacent, log distance, depth change. */
export const N_PAIR = 14;

export interface BlockFeatures {
  /** N_OWN values per logic unit. */
  own: Float32Array;
  /** N_PAIR values per (earlier unit c, unit t) pair, ordered by t then c. */
  pairs: Float32Array;
}

export function blockFeatures(logic: UnitAst[]): BlockFeatures {
  const n = logic.length;
  const own = new Float32Array(n * N_OWN);
  logic.forEach((a, t) => {
    const row = own.subarray(t * N_OWN);
    CATEGORIES.forEach((c, k) => {
      row[k] = a.category === c ? 1 : 0;
    });
    row[CATEGORIES.length] = a.isHeader ? 1 : 0;
    row[CATEGORIES.length + 1] = a.depth;
  });
  const pairs = new Float32Array(((n * (n - 1)) / 2) * N_PAIR);
  let at = 0;

  for (let t = 0; t < n; t++) {
    for (let c = 0; c < t; c++) {
      pairs.set(segmentFeatures(logic[c], logic[t]), at);
      pairs[at + 11] = t - c === 1 ? 1 : 0;
      pairs[at + 12] = Math.log1p(t - c);
      pairs[at + 13] = logic[t].depth - logic[c].depth;
      at += N_PAIR;
    }
  }

  return { own, pairs };
}

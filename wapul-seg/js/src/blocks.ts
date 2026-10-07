// The logic units' facts in the form the WASM `blocks` takes. The pair features, candidate
// rows and grouping (wapul-ml's `segment_features`, `Units`, `BlockCandidates`,
// `predict_blocks`) are computed in the WASM (wapul-seg/src/blocks.rs) from these, one unit
// at a time, so no n² pair table is built here.

import { type UnitAst } from './ast.ts';
import { CATEGORIES } from './languages.ts';

/** Per unit: one flag per category, header, depth. */
export const N_OWN = CATEGORIES.length + 2;

/** Per unit, as int32: category, node type id, is header, depth, span start, span end, loop,
 * control, function, parent. The order blocks.rs reads. */
export const N_FACTS = 10;

export interface BlockFeatures {
  /** N_OWN values per logic unit. */
  own: Float32Array;
  /** N_FACTS values per logic unit. */
  facts: Int32Array;
  /** Identifier ids each unit reads, sorted; unit t's are reads[readsOffsets[t] .. readsOffsets[t + 1]). */
  readsOffsets: Uint32Array;
  reads: Uint32Array;
  writesOffsets: Uint32Array;
  writes: Uint32Array;
}

/** Numbers for names, so the WASM compares ids instead of strings. */
class Interner {
  private readonly ids = new Map<string, number>();

  id(name: string): number {
    let id = this.ids.get(name);

    if (id === undefined) {
      id = this.ids.size;
      this.ids.set(name, id);
    }

    return id;
  }
}

function idSets(
  logic: UnitAst[],
  pick: (a: UnitAst) => Set<string>,
  names: Interner
): [Uint32Array, Uint32Array] {
  const offsets = new Uint32Array(logic.length + 1);
  const ids: number[] = [];

  logic.forEach((a, t) => {
    const unit = [...pick(a)].map((name) => names.id(name)).sort((x, y) => x - y);

    ids.push(...unit);
    offsets[t + 1] = ids.length;
  });

  return [offsets, Uint32Array.from(ids)];
}

export function blockFeatures(logic: UnitAst[]): BlockFeatures {
  const n = logic.length;
  const own = new Float32Array(n * N_OWN);
  const facts = new Int32Array(n * N_FACTS);
  const nodeTypes = new Interner();

  logic.forEach((a, t) => {
    const row = own.subarray(t * N_OWN);

    CATEGORIES.forEach((c, k) => {
      row[k] = a.category === c ? 1 : 0;
    });
    row[CATEGORIES.length] = a.isHeader ? 1 : 0;
    row[CATEGORIES.length + 1] = a.depth;
    facts.set(
      [
        CATEGORIES.indexOf(a.category),
        nodeTypes.id(a.nodeType),
        a.isHeader ? 1 : 0,
        a.depth,
        a.span[0],
        a.span[1],
        a.loop,
        a.control,
        a.function,
        a.parent
      ],
      t * N_FACTS
    );
  });

  const names = new Interner();
  const [readsOffsets, reads] = idSets(logic, (a) => a.reads, names);
  const [writesOffsets, writes] = idSets(logic, (a) => a.writes, names);

  return { own, facts, readsOffsets, reads, writesOffsets, writes };
}

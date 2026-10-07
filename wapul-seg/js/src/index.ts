// The module the frontend imports: segment(code, language). See docs/ml/deploy.ko.md.

import { analyze } from './ast.ts';
import { type Assets, fetchAssets } from './assets.ts';
import { blockFeatures } from './blocks.ts';
import { featureText, unitFeatures, withNgrams } from './kinds.ts';
import { type Language, LANGUAGES } from './languages.ts';
import { model } from './model.ts';
import { normalize } from './normalize.ts';
import { parse } from './parser.ts';
import { type Point, units } from './units.ts';

export { type Assets, fetchAssets } from './assets.ts';

export { type Language, LANGUAGES } from './languages.ts';

export { normalize } from './normalize.ts';

export const KINDS = ['input', 'output', 'logic', 'none'] as const;

export type Kind = (typeof KINDS)[number];

/** One statement unit, as wapul-ml's labels.jsonl holds it. */
export interface Labeled {
  /** [line, col]: line from 1, col from 0 in characters of the normalized code. */
  start: Point;
  /** Exclusive. */
  end: Point;
  kind: Kind;
  /** Logic block number from 1; blocks may be non-contiguous. */
  block?: number;
}

/** The release files next to this module, unless `segment` is given other assets. */
let defaultAssets: Assets | undefined;

/** Every statement of `code` with its kind and, for logic, its block. `code` is normalized
 * first; the positions refer to `normalize(code)`. */
export async function segment(
  code: string,
  language: Language,
  // The module's own directory, spelled so that the bundler leaves it alone
  assets: Assets = (defaultAssets ??= fetchAssets(import.meta.url.replace(/[^/]*$/, '')))
): Promise<Labeled[]> {
  if (!LANGUAGES.includes(language)) {
    throw new Error(`language must be one of ${LANGUAGES.join(', ')}`);
  }

  code = normalize(code);
  const [m, tree] = await Promise.all([model(assets), parse(code, language, assets)]);

  try {
    const us = units(tree, code);
    const asts = analyze(tree, us, language);
    const kinds = m.kinds(featureText(withNgrams(unitFeatures(code, language, us, asts))));
    const logic = asts.filter((_, j) => KINDS[kinds[j]] === 'logic');
    const f = blockFeatures(logic);
    const blocks = m.blocks(f.own, f.facts, f.readsOffsets, f.reads, f.writesOffsets, f.writes);
    let next = 0;

    return us.map((u, j) => {
      const kind = KINDS[kinds[j]];
      const labeled: Labeled = { start: u.start, end: u.end, kind };

      if (kind === 'logic') {
        labeled.block = blocks[next++] + 1;
      }

      return labeled;
    });
  } finally {
    tree.delete();
  }
}

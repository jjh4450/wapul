// The module the frontend imports: segment(code, language). See docs/ml/deploy.ko.md.

import { analyze } from './ast.ts';
import { type Assets, fetchAssets } from './assets.ts';
import { blockFeatures } from './blocks.ts';
import { featureText, literalSpans, unitFeatures, withNgrams } from './kinds.ts';
import { type Language, LANGUAGES } from './languages.ts';
import { model } from './model.ts';
import { normalize } from './normalize.ts';
import { parse } from './parser.ts';
import { type Tags, unitTags } from './tags.ts';
import { type Point, units } from './units.ts';

export { type Assets, fetchAssets } from './assets.ts';

export { type Language, LANGUAGES } from './languages.ts';

export { normalize } from './normalize.ts';

export { type Tags } from './tags.ts';

export const KINDS = ['input', 'output', 'logic', 'none'] as const;

export type Kind = (typeof KINDS)[number];

/** The most statements `segment` takes. Block grouping compares every pair of logic units, so
 * time grows with the square of the count; real solutions stay under a few hundred. */
export const MAX_UNITS = 1000;

/** One statement unit, as wapul-ml's labels.jsonl holds it, with the questions it raises
 * (Tags: a condition or comparison, a loop header, a recursive call). */
export interface Labeled extends Tags {
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
 * first; the positions refer to `normalize(code)`. Throws a RangeError for code of more than
 * MAX_UNITS statements. */
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
  // Both load at once; settled rather than all, so a tree parsed while the model failed is freed
  const [loaded, parsed] = await Promise.allSettled([model(assets), parse(code, language, assets)]);

  if (loaded.status === 'rejected') {
    if (parsed.status === 'fulfilled') {
      parsed.value.delete();
    }

    throw loaded.reason;
  }

  if (parsed.status === 'rejected') {
    throw parsed.reason;
  }

  const m = loaded.value;
  const tree = parsed.value;

  try {
    const us = units(tree, code);

    if (us.length > MAX_UNITS) {
      throw new RangeError(`code has ${us.length} statements; segment takes at most ${MAX_UNITS}`);
    }

    const asts = analyze(tree, us, language);
    const feats = withNgrams(unitFeatures(code, language, us, asts, literalSpans(tree)));
    const kinds = m.kinds(featureText(feats));
    const logic = asts.filter((_, j) => KINDS[kinds[j]] === 'logic');
    const f = blockFeatures(logic);
    const blocks = m.blocks(f.own, f.facts, f.readsOffsets, f.reads, f.writesOffsets, f.writes);
    const tags = unitTags(tree, us, asts);
    let next = 0;

    return us.map((u, j) => {
      const kind = KINDS[kinds[j]];
      const labeled: Labeled = { start: u.start, end: u.end, kind, ...tags[j] };

      if (kind === 'logic') {
        labeled.block = blocks[next++] + 1;
      }

      return labeled;
    });
  } finally {
    tree.delete();
  }
}

/** Each logic block's tags: a tag is on when any unit of the block has it. */
export function blockTags(labeled: Labeled[]): Map<number, Tags> {
  const out = new Map<number, Tags>();

  for (const u of labeled) {
    if (u.block === undefined) {
      continue;
    }

    const t = out.get(u.block) ?? { condition: false, loop: false, recursion: false };
    out.set(u.block, {
      condition: t.condition || u.condition,
      loop: t.loop || u.loop,
      recursion: t.recursion || u.recursion
    });
  }

  return out;
}

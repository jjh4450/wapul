// Stage-by-stage parity with wapul-ml's Python model on the public snippets in cases/, whose
// expected outputs tests/make_cases.py writes to cases.json (docs/ml/deploy.ko.md, "검증").

import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import path from 'node:path';

import { describe, expect, test } from 'vitest';

import { analyze } from '../src/ast.ts';
import { type Assets } from '../src/assets.ts';
import { blockFeatures } from '../src/blocks.ts';
import { KINDS, segment } from '../src/index.ts';
import { featureText, unitFeatures, withNgrams } from '../src/kinds.ts';
import { grammarFile, type Language, LANGUAGES } from '../src/languages.ts';
import { model } from '../src/model.ts';
import { normalize } from '../src/normalize.ts';
import { parse } from '../src/parser.ts';
import { units } from '../src/units.ts';
import { grammarPath } from '../tools/grammars.ts';

const require = createRequire(import.meta.url);

const root = path.resolve(import.meta.dirname, '..');

/** The release files as the development checkout holds them. */
async function file(name: string): Promise<string> {
  const grammar = LANGUAGES.find((language) => grammarFile(language) === name);

  if (name === 'web-tree-sitter.wasm') {
    return require.resolve('web-tree-sitter/web-tree-sitter.wasm');
  }

  if (grammar !== undefined) {
    return grammarPath(grammar);
  }

  if (name === 'wapul_seg_bg.wasm') {
    return path.join(root, '..', 'pkg', name);
  }

  if (name.startsWith('model/')) {
    return path.join(root, '..', '..', name);
  }

  throw new Error(`unknown asset ${name}`);
}

const assets: Assets = {
  text: async (name) => readFile(await file(name), 'utf8'),
  bytes: async (name) => readFile(await file(name))
};

interface Case {
  id: string;
  language: Language;
  code: string;
  units: { start: [number, number]; end: [number, number]; text: string }[];
  asts: {
    category: string;
    node_type: string;
    is_header: boolean;
    depth: number;
    reads: string[];
    writes: string[];
  }[];
  features: Record<string, number>[];
  kinds: string[];
  own: number[][];
  pairs: number[][];
  blocks: (number | null)[];
}

// WAPUL_SEG_CASES: another cases file, such as make_cases.py --corpus writes from private data
const casesFile = process.env.WAPUL_SEG_CASES ?? path.join(root, 'tests', 'cases.json');

const cases: Case[] = JSON.parse(await readFile(casesFile, 'utf8'));

describe.each(cases)('$id', (c) => {
  const parsed = () => parse(c.code, c.language, assets);

  test('normalize is a fixed point', () => {
    expect(normalize(c.code)).toBe(c.code);
  });

  test('units', async () => {
    const tree = await parsed();
    const got = units(tree, c.code).map(({ start, end, text }) => ({ start, end, text }));

    tree.delete();
    expect(got).toEqual(c.units);
  });

  test('AST facts', async () => {
    const tree = await parsed();

    const got = analyze(tree, units(tree, c.code), c.language).map((a) => ({
      category: a.category,
      node_type: a.nodeType,
      is_header: a.isHeader,
      depth: a.depth,
      reads: [...a.reads].sort(),
      writes: [...a.writes].sort()
    }));

    tree.delete();
    expect(got).toEqual(c.asts);
  });

  test('kind features', async () => {
    const tree = await parsed();
    const us = units(tree, c.code);
    const feats = withNgrams(unitFeatures(c.code, c.language, us, analyze(tree, us, c.language)));

    tree.delete();
    expect(feats.map((f) => Object.fromEntries(f))).toEqual(c.features);
  });

  test('kinds', async () => {
    const m = await model(assets);
    const tree = await parsed();
    const us = units(tree, c.code);
    const feats = withNgrams(unitFeatures(c.code, c.language, us, analyze(tree, us, c.language)));
    const kinds = [...m.kinds(featureText(feats))].map((k) => KINDS[k]);

    tree.delete();
    expect(kinds).toEqual(c.kinds);
  });

  test('block features', async () => {
    const tree = await parsed();
    const us = units(tree, c.code);
    const logic = analyze(tree, us, c.language).filter((_, j) => c.kinds[j] === 'logic');
    const { own, pairs } = blockFeatures(logic);

    tree.delete();
    expect([...own]).toEqual(c.own.flat().map(Math.fround));
    expect([...pairs]).toEqual(c.pairs.flat().map(Math.fround));
  });

  test('segment', async () => {
    const got = await segment(c.code, c.language, assets);

    expect(got.map((l) => l.kind)).toEqual(c.kinds);
    expect(got.map((l) => l.block ?? null)).toEqual(c.blocks);
    expect(got.map((l) => [l.start, l.end])).toEqual(c.units.map((u) => [u.start, u.end]));
  });
});

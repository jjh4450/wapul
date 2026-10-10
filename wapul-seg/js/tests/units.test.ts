// Positions of units, which must match the Python original (wapul_ml/units.py) and the backend.

import { expect, test } from 'vitest';

import { parse } from '../src/parser.ts';
import { units } from '../src/units.ts';
import { assets } from './assets.ts';

test('columns count code points, so an emoji is one column', async () => {
  const code = 'print("🎉")\nx = 1\n';
  const tree = await parse(code, 'python', assets);
  const us = units(tree, code);

  tree.delete();

  // Python's len('print("🎉")') is 10; UTF-16 would give 11
  expect(us.map(({ start, end }) => [start, end])).toEqual([
    [
      [1, 0],
      [1, 10]
    ],
    [
      [2, 0],
      [2, 5]
    ]
  ]);
});

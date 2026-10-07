import { describe, expect, it } from 'vitest';
import type { Labeled } from 'wapul-seg';
import { toBlocks } from './segment.js';

const at = (line: number): Omit<Labeled, 'kind'> => ({
  start: [line, 0],
  end: [line, 5],
  condition: false,
  loop: false,
  recursion: false
});

describe('toBlocks', () => {
  it('orders input, logic blocks by number, then output, and leaves none out', () => {
    const labeled: Labeled[] = [
      { ...at(1), kind: 'none' },
      { ...at(2), kind: 'logic', block: 2 },
      { ...at(3), kind: 'input' },
      { ...at(4), kind: 'logic', block: 1 },
      { ...at(5), kind: 'logic', block: 2 },
      { ...at(6), kind: 'output' }
    ];

    expect(toBlocks(labeled)).toEqual([
      { kind: 'input', units: [2] },
      { kind: 'logic', units: [3] },
      { kind: 'logic', units: [1, 4] },
      { kind: 'output', units: [5] }
    ]);
  });

  it('skips kinds the code does not have', () => {
    expect(toBlocks([{ ...at(1), kind: 'logic', block: 1 }])).toEqual([
      { kind: 'logic', units: [0] }
    ]);
  });
});

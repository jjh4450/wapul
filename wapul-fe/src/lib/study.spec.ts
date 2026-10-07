import { describe, expect, it } from 'vitest';
import type { Span } from './api/client.js';
import { blockLabels, formatDate, truncate, unitLines } from './study.js';

describe('truncate', () => {
  it('keeps text that fits', () => {
    expect(truncate('짧은 예제', 10)).toBe('짧은 예제');
  });

  it('cuts long text and marks it with ...', () => {
    expect(truncate('가나다라마바사', 3)).toBe('가나다...');
  });

  it('does not leave a space before ...', () => {
    expect(truncate('ab cd', 3)).toBe('ab...');
  });
});

describe('formatDate', () => {
  it('reads the backend timestamp format (offset without colon)', () => {
    expect(formatDate('2026-10-05T12:00:00+0000')).toBe('2026. 10. 5.');
  });
});

describe('blockLabels', () => {
  it('numbers only the logic blocks', () => {
    const kinds = ['input', 'logic', 'logic', 'output'] as const;

    expect(blockLabels(kinds.map((kind) => ({ kind })))).toEqual([
      '입력',
      '로직 1',
      '로직 2',
      '출력'
    ]);
  });
});

describe('unitLines', () => {
  it('collects every line the statements cover, once and in order', () => {
    const units = [
      { start: [5, 0], end: [6, 3] },
      { start: [1, 0], end: [1, 9] },
      { start: [6, 4], end: [6, 9] }
    ] satisfies Span[];

    expect(unitLines(units, [0, 1, 2])).toEqual([1, 5, 6]);
  });
});

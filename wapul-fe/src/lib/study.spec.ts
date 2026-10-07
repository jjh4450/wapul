import { describe, expect, it } from 'vitest';
import type { Span } from './api/client.js';
import { blockColors, blockLabels, formatDate, lastLine, truncate } from './study.js';

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

describe('blockColors', () => {
  it('keeps input and output colors and gives each logic block the next color', () => {
    const kinds = ['input', 'logic', 'logic', 'output'] as const;

    const colors = blockColors(kinds.map((kind) => ({ kind })));

    expect(new Set(colors.map((c) => c.bar)).size).toBe(4);
    expect(blockColors([{ kind: 'input' }])[0]).toEqual(colors[0]);
    expect(blockColors([{ kind: 'logic' }, { kind: 'output' }])).toEqual(
      colors.slice(1, 2).concat(colors[3])
    );
  });
});

describe('lastLine', () => {
  it('finds the line where the last of the statements ends, whatever their order', () => {
    const units = [
      { start: [5, 0], end: [6, 3] },
      { start: [1, 0], end: [1, 9] },
      { start: [6, 4], end: [6, 9] }
    ] satisfies Span[];

    expect(lastLine(units, [1, 0])).toBe(6);
    expect(lastLine(units, [1])).toBe(1);
  });
});

import { describe, expect, it } from 'vitest';
import { formatDate, truncate } from './study.js';

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

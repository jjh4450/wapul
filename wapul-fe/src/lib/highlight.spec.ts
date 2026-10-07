import { describe, expect, it } from 'vitest';
import type { Language } from './api/client.js';
import { highlight } from './highlight.js';
import { LANGUAGE_LABEL } from './study.js';

describe('highlight', () => {
  it('colors keywords, functions, strings and comments per line', () => {
    const lines = highlight('#include <cstdio>\nint main() {\n  // hi\n  return 0;\n}\n', 'cpp');

    expect(lines[0]).toContainEqual({ from: 9, to: 17, color: 'text-code-string' });
    expect(lines[1]).toEqual([
      { from: 0, to: 3, color: 'text-code-keyword' },
      { from: 4, to: 8, color: 'text-code-function' }
    ]);
    expect(lines[2]).toEqual([{ from: 2, to: 7, color: 'text-code-comment' }]);
    expect(lines[3]).toEqual([
      { from: 2, to: 8, color: 'text-code-keyword' },
      { from: 9, to: 10, color: 'text-code-constant' }
    ]);
  });

  it('splits a token that spans lines', () => {
    const lines = highlight('/* a\nb */ x', 'c');

    expect(lines[0]).toEqual([{ from: 0, to: 4, color: 'text-code-comment' }]);
    expect(lines[1]).toEqual([{ from: 0, to: 4, color: 'text-code-comment' }]);
  });

  it('counts columns in code points like the statement positions', () => {
    expect(highlight('s = "😀"', 'python')[0]).toEqual([
      { from: 4, to: 7, color: 'text-code-string' }
    ]);
  });

  it('has a grammar for every language', () => {
    // SAFETY: LANGUAGE_LABEL은 satisfies로 Language의 모든 값을, 그 값만 키로 가진다
    const languages = Object.keys(LANGUAGE_LABEL) as Language[];

    for (const language of languages) {
      expect(highlight('x = 1', language)).toHaveLength(1);
    }
  });
});

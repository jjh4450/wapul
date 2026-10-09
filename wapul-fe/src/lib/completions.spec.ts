import { describe, expect, it } from 'vitest';
import { suggest, type Name } from '#lib/completions.js';

const name = (text: string, kind: Name['kind'], lines: number[], count = lines.length): Name => ({
  text,
  kind,
  lines,
  count
});

// 배낭 문제 풀이에서 wapul-seg가 뽑는 꼴의 이름들
const words: Name[] = [
  name('n', 'name', [3, 5, 9], 4),
  name('k', 'name', [3, 4, 7, 9], 4),
  name('map', 'function', [3]),
  name('dp', 'name', [4, 8, 9], 6),
  name('dp[i][j]', 'subscript', [8]),
  name('dp[i - 1][j]', 'subscript', [8], 2),
  name('dp[n][k]', 'subscript', [9]),
  name('w', 'name', [6, 8], 3),
  name('max', 'function', [8]),
  name('maxValue', 'name', [10]),
  name('max_cost', 'name', [11]),
  name('"YES"', 'string', [9])
];

describe('suggest', () => {
  it('puts prefix matches first, then more frequent words', () => {
    // dp가 가장 많이 나오고, 대괄호 식 중에는 두 번 나온 dp[i - 1][j]가 한 번 나온 것보다 먼저다
    expect(
      suggest(words, 'dp')
        .map((w) => w.text)
        .slice(0, 3)
    ).toEqual(['dp', 'dp[i - 1][j]', 'dp[i][j]']);
  });

  it('matches ignoring case and by initials', () => {
    expect(suggest(words, 'MAX_').map((w) => w.text)).toEqual(['max_cost']);
    expect(suggest(words, 'mv').map((w) => w.text)).toEqual(['maxValue']);
  });

  it('only takes prefix matches for a single letter', () => {
    expect(suggest(words, 'k').map((w) => w.text)).toEqual(['k']);
  });

  it('prefers words on the lines of the block being answered', () => {
    // max는 8번 줄에, map은 3번 줄에만 나온다
    expect(suggest(words, 'ma').map((w) => w.text)).toEqual([
      'map()',
      'max()',
      'max_cost',
      'maxValue'
    ]);
    expect(suggest(words, 'ma', new Set([8]))[0].text).toBe('max()');
  });

  it('offers a function with empty parentheses, then with its parameters when defined', () => {
    const knapsack = [...words, { ...name('solve', 'function', [5, 9], 2), params: ['n', 'k'] }];

    expect(suggest(knapsack, 'so').map((w) => w.text)).toEqual(['solve()', 'solve(n, k)']);
    // 매개변수 이름은 맞춰 보지 않는다
    expect(suggest(knapsack, 'nk').map((w) => w.text)).not.toContain('solve(n, k)');
  });

  it('finds string literals inside their quotes', () => {
    expect(suggest(words, 'YE').map((w) => w.text)).toEqual(['"YES"']);
  });

  it('returns nothing when no word matches', () => {
    expect(suggest(words, 'zzz')).toEqual([]);
  });
});

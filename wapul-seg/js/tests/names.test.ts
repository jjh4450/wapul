// The names wapul's answer fields complete, in every supported language.

import { describe, expect, it } from 'vitest';

import { type Language } from '../src/languages.ts';
import { collectNames } from '../src/names.ts';
import { normalize } from '../src/normalize.ts';
import { parse } from '../src/parser.ts';
import { assets } from './assets.ts';

// What `names` in index.ts does after checking the language. index.ts also loads the model's WASM,
// which a checkout without the Rust build (pkg/) does not have.
async function names(code: string, language: Language) {
  const tree = await parse(normalize(code), language, assets);

  try {
    return collectNames(tree);
  } finally {
    tree.delete();
  }
}

// Each sample defines and calls `solve`, indexes with brackets where the language has them, prints
// "YES", and has a comment holding `hidden`, which must not come out.
const SAMPLES: { language: Language; code: string; subscript: string | null; text: string }[] = [
  {
    language: 'cpp',
    code: `#include <bits/stdc++.h>
using namespace std;
int dp[10][10]; // hidden
int solve(int n) { return dp[n][0]; }
int main() { vector<int> v; v.push_back(1); cout << solve(1) << "YES"; }
`,
    subscript: 'dp[n][0]',
    text: '"YES"'
  },
  {
    language: 'c',
    code: `int dp[10][10]; // hidden
int solve(int n) { return dp[n][0]; }
int main(void) { printf("YES"); return solve(1); }
`,
    subscript: 'dp[n][0]',
    text: '"YES"'
  },
  {
    language: 'java',
    code: `class Main {
  static int[][] dp = new int[10][10]; // hidden
  static int solve(int n) { return dp[n][0]; }
  public static void main(String[] args) { System.out.println(solve(1) + "YES"); }
}
`,
    subscript: 'dp[n][0]',
    text: '"YES"'
  },
  {
    language: 'python',
    code: `# hidden
def solve(n):
    return dp[n][0]
dp = [[0] * 10 for _ in range(10)]
print(solve(1), "YES")
`,
    subscript: 'dp[n][0]',
    text: '"YES"'
  },
  {
    language: 'rust',
    code: `// hidden
fn solve(dp: &Vec<Vec<i64>>, n: usize) -> i64 { dp[n][0] }
fn main() { let dp = vec![vec![0; 10]; 10]; println!("YES {}", solve(&dp, 1)); }
`,
    subscript: 'dp[n][0]',
    text: '"YES {}"'
  },
  {
    language: 'kotlin',
    code: `// hidden
val dp = Array(10) { IntArray(10) }
fun solve(n: Int): Int = dp[n][0]
fun main() { println(solve(1).toString() + "YES") }
`,
    subscript: 'dp[n][0]',
    text: '"YES"'
  },
  {
    language: 'javascript',
    code: `// hidden
const dp = [[0]];
function solve(n) { return dp[n][0]; }
console.log(solve(0), "YES");
`,
    subscript: 'dp[n][0]',
    text: '"YES"'
  },
  {
    language: 'go',
    code: `package main

import "fmt"

var dp [10][10]int // hidden

func solve(n int) int { return dp[n][0] }

func main() { fmt.Println(solve(1), "YES") }
`,
    subscript: 'dp[n][0]',
    text: '"YES"'
  },
  {
    language: 'csharp',
    code: `class P {
  static int[,] dp = new int[10, 10]; // hidden
  static int Solve(int n) { return dp[n, 0]; }
  static void Main() { System.Console.WriteLine(Solve(1) + "YES"); }
}
`,
    subscript: 'dp[n, 0]',
    text: '"YES"'
  },
  {
    language: 'swift',
    code: `// hidden
var dp = [[Int]](repeating: [Int](repeating: 0, count: 10), count: 10)
func solve(_ n: Int) -> Int { return dp[n][0] }
print(solve(1), "YES")
`,
    subscript: 'dp[n][0]',
    text: '"YES"'
  },
  {
    language: 'ruby',
    code: `# hidden
def solve(n)
  @dp[n][0]
end
@dp = Array.new(10) { [0] }
puts solve(1), "YES"
`,
    subscript: '@dp[n][0]',
    text: '"YES"'
  },
  {
    language: 'scala',
    code: `object Main {
  val dp = Array.ofDim[Int](10, 10) // hidden
  def solve(n: Int): Int = dp(n)(0)
  def main(args: Array[String]): Unit = println(solve(1) + "YES")
}
`,
    // dp(n)(0) is a call as far as the syntax goes
    subscript: null,
    text: '"YES"'
  },
  {
    language: 'php',
    code: `<?php
$dp = [[0]]; // hidden
function solve($n) { global $dp; return $dp[$n][0]; }
echo solve(0), "YES";
`,
    subscript: '$dp[$n][0]',
    text: '"YES"'
  }
];

// Functions defined with parameters, as definitions and as function values held by variables.
// Types, default values, Swift's argument labels and Python's `self` are not parameter names.
const DEFINITIONS: { language: Language; code: string; params: Record<string, string[]> }[] = [
  {
    language: 'cpp',
    code: `int solve(int n, vector<int>& v, const string &s, int* a, int arr[MAX], long long k = 0) {
  return n;
}
int main() {
  auto dfs = [&](int u, int p) -> void {};
  function<int(int)> f = [&](int x) { return x; };
}
`,
    params: { solve: ['n', 'v', 's', 'a', 'arr', 'k'], dfs: ['u', 'p'], f: ['x'] }
  },
  {
    language: 'c',
    code: `void dfs(int);
void dfs(int u) {}
int h(void) { return 0; }
`,
    // The prototype names no parameters, the definition does
    params: { dfs: ['u'], h: [] }
  },
  {
    language: 'java',
    code: `class Main {
  static int solve(int n, int[] a, List<Integer> list) { return n; }
  void f() { Comparator<int[]> cmp = (a, b) -> a[0] - b[0]; Function<Integer, Integer> g = x -> x; }
}
`,
    params: { solve: ['n', 'a', 'list'], cmp: ['a', 'b'], g: ['x'] }
  },
  {
    language: 'python',
    code: `class Solution:
    def climb(self, n: int, k=0, *args, **kw):
        pass
g = lambda a, b: a + b
`,
    params: { climb: ['n', 'k', 'args', 'kw'], g: ['a', 'b'] }
  },
  {
    language: 'rust',
    code: `fn solve(dp: &Vec<Vec<i64>>, mut n: usize) -> i64 { 0 }
impl S { fn f(&self, x: i32) {} }
fn main() { let g = |a: i32, b| a + b; }
`,
    params: { solve: ['dp', 'n'], f: ['x'], g: ['a', 'b'] }
  },
  {
    language: 'kotlin',
    code: `fun solve(n: Int, k: Int = MAX): Int = n
val g = { a: Int, b: Int -> a + b }
`,
    params: { solve: ['n', 'k'], g: ['a', 'b'] }
  },
  {
    language: 'javascript',
    code: `function solve(n, k = 0, ...rest) {}
const g = (a, b) => a + b;
const h = x => x;
class A { m(x, y) {} }
`,
    params: { solve: ['n', 'k', 'rest'], g: ['a', 'b'], h: ['x'], m: ['x', 'y'] }
  },
  {
    language: 'go',
    code: `package main

func solve(n, k int, s string) int { return n }

func (r *R) m(x int) {}

func main() { g := func(a, b int) int { return a + b }; _ = g }
`,
    params: { solve: ['n', 'k', 's'], m: ['x'], g: ['a', 'b'] }
  },
  {
    language: 'csharp',
    code: `class P {
  static int Solve(int n, ref int k, int m = MAX) { return n; }
  void F() { Func<int, int> g = (x) => x; }
}
`,
    params: { Solve: ['n', 'k', 'm'], g: ['x'] }
  },
  {
    language: 'swift',
    code: `func solve(_ n: Int, from start: Int = 0) -> Int { return n }
`,
    params: { solve: ['n', 'start'] }
  },
  {
    language: 'ruby',
    code: `def solve(n, k = 0, *rest, &blk)
end
g = ->(a, b) { a + b }
`,
    params: { solve: ['n', 'k', 'rest', 'blk'], g: ['a', 'b'] }
  },
  {
    language: 'scala',
    code: `object M { def solve(n: Int, k: Int = 0)(m: Int): Int = n; val g = (a: Int, b: Int) => a + b }
`,
    // Only the first parameter list
    params: { solve: ['n', 'k'], g: ['a', 'b'] }
  },
  {
    language: 'php',
    code: `<?php
function solve($n, int $k = 0, &$a) { return $n; }
$g = function($a, $b) { return $a + $b; };
$h = fn($x) => $x;
`,
    params: { solve: ['$n', '$k', '$a'], $g: ['$a', '$b'], $h: ['$x'] }
  }
];

describe('names', () => {
  for (const { language, code, subscript, text } of SAMPLES) {
    it(`finds ${language} names, functions, subscripts and strings, and skips comments`, async () => {
      const found = await names(code, language);

      const kind = (t: string) => found.find((n) => n.text === t)?.kind;

      expect(kind(language === 'csharp' ? 'Solve' : 'solve')).toBe('function');
      expect(kind(text)).toBe('string');

      if (subscript !== null) {
        expect(kind(subscript)).toBe('subscript');
      }

      expect(found.map((n) => n.text)).not.toContain('hidden');
    });
  }

  it('labels member calls as functions and counts lines of the normalized code', async () => {
    const found = await names(SAMPLES[0].code, 'cpp');

    const get = (t: string) => found.find((n) => n.text === t);

    expect(get('push_back')?.kind).toBe('function');
    expect(get('v')?.kind).toBe('name');
    // dp is declared on line 3 and read on line 4
    expect(get('dp')?.lines).toEqual([3, 4]);
    expect(get('solve')?.count).toBe(2);
    // keywords and names in import lines are not names to write about
    expect(found.map((n) => n.text)).not.toContain('int');
    expect(found.map((n) => n.text)).not.toContain('std');
    expect(found.map((n) => n.text)).not.toContain('<bits/stdc++.h>');
  });

  for (const { language, code, params } of DEFINITIONS) {
    it(`finds the parameters of ${language} functions and function values`, async () => {
      const found = await names(code, language);

      for (const [text, expected] of Object.entries(params)) {
        const name = found.find((n) => n.text === text);

        expect(name?.kind).toBe('function');
        expect(name?.params).toEqual(expected);
      }
    });
  }

  it('gives no parameters to functions only called, nor to argument names', async () => {
    const cpp = await names(SAMPLES[0].code, 'cpp');

    expect(cpp.find((n) => n.text === 'push_back')?.params).toBeUndefined();

    // key= names an argument, not a variable holding the lambda
    const python = await names('xs.sort(key=lambda x: x[1])\n', 'python');

    expect(python.find((n) => n.text === 'key')?.kind).toBe('name');
  });
});

// Tags (condition, loop, recursion) on a small recursive function and a loop in every
// supported language.

import { describe, expect, test } from 'vitest';

import { analyze } from '../src/ast.ts';
import { type Language } from '../src/languages.ts';
import { parse } from '../src/parser.ts';
import { type Tags, unitTags } from '../src/tags.ts';
import { units } from '../src/units.ts';
import { assets } from './assets.ts';

/** Per language: the code, then units picked by the start of their text and the tags they must
 * have (only the tags given are checked). */
const CASES: [Language, string, [string, Partial<Tags>][]][] = [
  [
    'cpp',
    'int f(int n) {\n  if (n <= 1) return 1;\n  return n * f(n - 1);\n}\nint main() {\n  for (int i = 0; i < 3; i++) cout << f(i);\n}\n',
    [
      ['if (n <= 1)', { condition: true, loop: false, recursion: false }],
      ['return 1;', { condition: false, recursion: false }],
      ['return n * f(n - 1);', { condition: false, recursion: true }],
      ['for (int i = 0; i < 3; i++)', { condition: true, loop: true }],
      ['cout << f(i);', { recursion: false }]
    ]
  ],
  [
    'c',
    'int f(int n) {\n  if (n <= 1) return 1;\n  return n * f(n - 1);\n}\nint main() {\n  for (int i = 0; i < 3; i++) printf("%d", f(i));\n}\n',
    [
      ['if (n <= 1)', { condition: true }],
      ['return n * f(n - 1);', { recursion: true }],
      ['for (int i = 0; i < 3; i++)', { loop: true }],
      ['printf', { recursion: false }]
    ]
  ],
  [
    'python',
    'def f(n):\n    if n <= 1:\n        return 1\n    return n * f(n - 1)\nfor i in range(3):\n    print(f(i))\n',
    [
      ['if n <= 1:', { condition: true }],
      ['return n * f(n - 1)', { recursion: true }],
      ['for i in range(3):', { condition: false, loop: true }],
      ['print(f(i))', { recursion: false }]
    ]
  ],
  [
    'java',
    'class Main {\n  static int f(int n) {\n    if (n <= 1) return 1;\n    return n * f(n - 1);\n  }\n  public static void main(String[] a) {\n    for (int i = 0; i < 3; i++) System.out.println(f(i));\n  }\n}\n',
    [
      ['if (n <= 1)', { condition: true }],
      ['return n * f(n - 1);', { recursion: true }],
      ['for (int i = 0; i < 3; i++)', { loop: true }],
      ['System.out.println(f(i));', { recursion: false }]
    ]
  ],
  [
    'rust',
    'fn f(n: u64) -> u64 {\n    if n <= 1 {\n        return 1;\n    }\n    n * f(n - 1)\n}\nfn main() {\n    for i in 0..3 {\n        println!("{}", f(i));\n    }\n}\n',
    [
      ['if n <= 1', { condition: true }],
      ['n * f(n - 1)', { recursion: true }],
      ['for i in 0..3', { condition: false, loop: true }]
    ]
  ],
  [
    'kotlin',
    'fun f(n: Int): Int {\n    if (n <= 1) return 1\n    return n * f(n - 1)\n}\nfun main() {\n    for (i in 0 until 3) {\n        println(f(i))\n    }\n}\n',
    [
      ['return n * f(n - 1)', { recursion: true }],
      ['for (i in 0 until 3)', { loop: true }],
      ['println(f(i))', { recursion: false }]
    ]
  ],
  [
    'javascript',
    'function f(n) {\n  if (n <= 1) return 1;\n  return n * f(n - 1);\n}\nfor (let i = 0; i < 3; i++) console.log(f(i));\n',
    [
      ['if (n <= 1)', { condition: true }],
      ['return n * f(n - 1);', { recursion: true }],
      ['for (let i = 0; i < 3; i++)', { condition: true, loop: true }]
    ]
  ],
  [
    'go',
    'package main\n\nfunc f(n int) int {\n\tif n <= 1 {\n\t\treturn 1\n\t}\n\treturn n * f(n-1)\n}\n\nfunc main() {\n\tfor i := 0; i < 3; i++ {\n\t\tprintln(f(i))\n\t}\n}\n',
    [
      ['if n <= 1', { condition: true }],
      ['return n * f(n-1)', { recursion: true }],
      ['for i := 0; i < 3; i++', { condition: true, loop: true }],
      ['println(f(i))', { recursion: false }]
    ]
  ],
  [
    'csharp',
    'class P {\n  static int F(int n) {\n    if (n <= 1) return 1;\n    return n * F(n - 1);\n  }\n  static void Main() {\n    for (int i = 0; i < 3; i++) System.Console.WriteLine(F(i));\n  }\n}\n',
    [
      ['if (n <= 1)', { condition: true }],
      ['return n * F(n - 1);', { recursion: true }],
      ['for (int i = 0; i < 3; i++)', { loop: true }]
    ]
  ],
  [
    'swift',
    'func f(_ n: Int) -> Int {\n    if n <= 1 {\n        return 1\n    }\n    return n * f(n - 1)\n}\nfor i in 0..<3 {\n    print(f(i))\n}\n',
    [
      ['if n <= 1', { condition: true }],
      ['return n * f(n - 1)', { recursion: true }],
      ['for i in 0..<3', { loop: true }],
      ['print(f(i))', { recursion: false }]
    ]
  ],
  [
    'ruby',
    'def f(n)\n  return 1 if n <= 1\n  n * f(n - 1)\nend\nfor i in 0..2\n  puts f(i)\nend\n',
    [
      ['if n <= 1', { condition: true, recursion: false }],
      ['n * f(n - 1)', { recursion: true }],
      ['for i in 0..2', { loop: true }]
    ]
  ],
  [
    'scala',
    'object Main {\n  def f(n: Int): Int = {\n    if (n <= 1) return 1\n    n * f(n - 1)\n  }\n  def main(args: Array[String]): Unit = {\n    for (i <- 0 until 3) println(f(i))\n  }\n}\n',
    [
      ['if (n <= 1)', { condition: true }],
      ['n * f(n - 1)', { recursion: true }],
      ['for (i <- 0 until 3)', { loop: true }]
    ]
  ],
  [
    'php',
    '<?php\nfunction f($n) {\n  if ($n <= 1) return 1;\n  return $n * f($n - 1);\n}\nfor ($i = 0; $i < 3; $i++) echo f($i);\n',
    [
      ['if ($n <= 1)', { condition: true }],
      ['return $n * f($n - 1);', { recursion: true }],
      ['for ($i = 0; $i < 3; $i++)', { condition: true, loop: true }]
    ]
  ]
];

describe.each(CASES)('%s', (language, code, expected) => {
  test.each(expected)('%s', async (prefix, want) => {
    const tree = await parse(code, language, assets);
    const us = units(tree, code);
    const tags = unitTags(tree, us, analyze(tree, us, language));
    tree.delete();
    const j = us.findIndex((u) => u.text.startsWith(prefix));

    expect(
      j,
      `no unit starts with ${prefix}: ${us.map((u) => u.text).join(' | ')}`
    ).toBeGreaterThanOrEqual(0);
    expect(tags[j]).toMatchObject(want);
  });
});

import { expect, test } from 'vitest';

import { normalize } from './normalize.ts';

// Expected values come from wapul-ml's normalize.py.
const cases: [string, string][] = [
  ['int a;\r\n  int b;  \r\n', 'int a;\n  int b;\n'],
  [
    '\n\n#include <stdio.h>\n\tint main() {\u00a0return 0;\u200b}\n\n\n',
    '#include <stdio.h>\n\tint main() { return 0;}\n'
  ],
  ['x = 1 \u2028\ny = 2\ufffd\n\ue000z\u0007\n', 'x = 1\ny = 2\nz\n'],
  // CP949 bytes read as Latin-1 upstream
  [
    '// \u00bc\u00f6\u00b8\u00a6 \u00b4\u00e3\u00c0\u00bb \u00b9\u00e8\u00bf\u00ad\nint n;\n',
    '// 수를 담을 배열\nint n;\n'
  ],
  ['', '\n'],
  ['a\u3000b \n', 'a b\n']
];

test.each(cases)('normalize(%j)', (input, want) => {
  expect(normalize(input)).toBe(want);
});

/**
 * 코드 색칠 (Prism).
 *
 * 13개 언어의 문법을 모두 싣는다 (gzip으로 20KB 남짓). 색은 layout.css의 --code-* 토큰이
 * 정하고, 밝은·어두운 테마 모두 GitHub의 색을 따른다.
 */
import Prism from 'prismjs';
// 언어 파일은 전역 Prism에 문법을 붙인다. 다른 언어를 바탕으로 하는 언어(cpp는 c, php는
// markup-templating)가 있어 바탕이 먼저 오게 둔다. javascript와 clike는 prismjs에 들어 있다
import 'prismjs/components/prism-c.js';
import 'prismjs/components/prism-cpp.js';
import 'prismjs/components/prism-csharp.js';
import 'prismjs/components/prism-go.js';
import 'prismjs/components/prism-java.js';
import 'prismjs/components/prism-kotlin.js';
import 'prismjs/components/prism-markup-templating.js';
import 'prismjs/components/prism-php.js';
import 'prismjs/components/prism-python.js';
import 'prismjs/components/prism-ruby.js';
import 'prismjs/components/prism-rust.js';
import 'prismjs/components/prism-scala.js';
import 'prismjs/components/prism-swift.js';
import type { Language } from '#lib/api/client.js';

/** 줄 안의 색 조각. from, to는 글자(코드 포인트) 단위 칸이고 to는 포함하지 않는다 */
export type Tint = { from: number; to: number; color: string };

type Leaf = { text: string; color: string | undefined };

// Prism 토큰 종류(또는 별칭)마다 색. 없는 종류(연산자, 괄호 등)는 글자색 그대로 둔다
const COLORS = new Map([
  ['comment', 'text-code-comment'],
  ['keyword', 'text-code-keyword'],
  ['macro', 'text-code-keyword'],
  ['string', 'text-code-string'],
  ['char', 'text-code-string'],
  ['regex', 'text-code-string'],
  ['number', 'text-code-constant'],
  ['boolean', 'text-code-constant'],
  ['constant', 'text-code-constant'],
  ['builtin', 'text-code-constant'],
  ['function', 'text-code-function'],
  ['class-name', 'text-code-type']
]);

/** 토큰을 글자 조각으로 편다. 안쪽 토큰의 색이 바깥 토큰의 색을 덮고, 별칭이 종류보다 먼저다 */
function flatten(stream: Prism.TokenStream, color: string | undefined, out: Leaf[]) {
  if (Array.isArray(stream)) {
    for (const item of stream) flatten(item, color, out);

    return;
  }

  if (stream instanceof Prism.Token) {
    const own = [...[stream.alias ?? []].flat(), stream.type]
      .map((kind) => COLORS.get(kind))
      .find((c) => c !== undefined);

    flatten(stream.content, own ?? color, out);

    return;
  }

  out.push({ text: stream, color });
}

/** 줄마다(0번이 1줄) 색 조각. 색이 없는 글자는 조각에 들지 않는다 */
export function highlight(code: string, language: Language): Tint[][] {
  const leaves: Leaf[] = [];

  flatten(Prism.tokenize(code, Prism.languages[language]), undefined, leaves);

  const lines: Tint[][] = [[]];
  let col = 0;

  for (const { text, color } of leaves) {
    text.split('\n').forEach((part, i) => {
      if (i > 0) {
        lines.push([]);
        col = 0;
      }

      const length = Array.from(part).length;

      if (color !== undefined && length > 0)
        lines.at(-1)?.push({ from: col, to: col + length, color });
      col += length;
    });
  }

  return lines;
}

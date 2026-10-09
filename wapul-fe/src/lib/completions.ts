/**
 * 답 칸 자동완성: 친 글자에 맞는 코드 속 이름을 고른다.
 *
 * IDE처럼 앞글자 몇 개를 치고 Tab으로 넣어, 이름을 칠 때마다 한/영을 바꾸고 백틱으로 감싸는 수고를
 * 던다(AnswerField). 문장을 제안하지 않고 코드에 있는 것만 보여 준다. 이름은 wapul-seg가 트리에서
 * 뽑는다(segment.ts의 codeNames).
 */
import type { Name } from 'wapul-seg';

export type { Name };

/** 이름의 머리글자: 첫 글자, _ 뒤 글자, 대문자 (max_value, maxValue → mv) */
function initials(text: string): string {
  return [...text.matchAll(/^[A-Za-z]|_[A-Za-z]|[A-Z]/g)]
    .map((m) => m[0].replace('_', ''))
    .join('')
    .toLowerCase();
}

/** 순서대로 들어 있는지 */
function subsequence(text: string, query: string): boolean {
  let i = 0;

  for (const c of text) if (c === query[i]) i += 1;

  return i === query.length;
}

/** 맞는 정도. 작을수록 잘 맞고, 안 맞으면 null. 한 글자로는 앞부분이 맞는 것만 */
function tier(text: string, query: string): number | null {
  const lower = query.toLowerCase();

  if (text.startsWith(query)) return 0;

  if (text.toLowerCase().startsWith(lower)) return 1;

  if (initials(text).startsWith(lower)) return 2;

  if (query.length < 2) return null;

  if (text.toLowerCase().includes(lower)) return 3;

  return subsequence(text.toLowerCase(), lower) ? 4 : null;
}

/**
 * 함수는 괄호까지 넣는다. 코드에 정의가 있어 매개변수를 알면 매개변수까지 넣는 후보를 바로 뒤에 둔다:
 * solve → solve(), solve(n, k)
 */
function forms(word: Name): Name[] {
  if (word.kind !== 'function') return [word];

  const call = { ...word, text: `${word.text}()` };

  return word.params === undefined || word.params.length === 0
    ? [call]
    : [call, { ...word, text: `${word.text}(${word.params.join(', ')})` }];
}

/**
 * 친 글자에 맞는 후보. 잘 맞는 것, 이 블럭 줄(near)에 나온 것, 많이 나온 것, 짧은 것 순이다.
 * 맞춰 보기는 이름으로만 하고, 함수는 고른 뒤에 괄호 꼴로 편다
 */
export function suggest(
  words: readonly Name[],
  query: string,
  near: ReadonlySet<number> = new Set(),
  limit = 8
): Name[] {
  const ranked = words.flatMap((word) => {
    const t = tier(word.text, query);

    return t === null ? [] : [{ word, t, close: word.lines.some((l) => near.has(l)) }];
  });

  ranked.sort(
    (a, b) =>
      a.t - b.t ||
      Number(b.close) - Number(a.close) ||
      b.word.count - a.word.count ||
      a.word.text.length - b.word.text.length ||
      a.word.text.localeCompare(b.word.text)
  );

  return ranked.flatMap((r) => forms(r.word)).slice(0, limit);
}

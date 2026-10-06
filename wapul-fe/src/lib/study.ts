import type { BlockKind, Language } from '#lib/api/client.js';

export const LANGUAGE_LABEL = {
  cpp: 'C++',
  python: 'Python',
  java: 'Java'
} satisfies { [K in Language]: string };

export const BLOCK_KIND_LABEL = {
  input: '입력',
  logic: '로직',
  output: '출력'
} satisfies { [K in BlockKind]: string };

/** 예제 답이 답 칸보다 길면 "..."로 줄인다 */
export function truncate(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max).trimEnd()}...` : text;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('ko-KR');
}

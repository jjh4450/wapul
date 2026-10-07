import type { BlockKind, Language, Span } from '#lib/api/client.js';

export const LANGUAGE_LABEL = {
  cpp: 'C++',
  python: 'Python',
  java: 'Java',
  rust: 'Rust',
  c: 'C',
  kotlin: 'Kotlin',
  javascript: 'JavaScript',
  go: 'Go',
  csharp: 'C#',
  swift: 'Swift',
  ruby: 'Ruby',
  scala: 'Scala',
  php: 'PHP'
} satisfies { [K in Language]: string };

export const BLOCK_KIND_LABEL = {
  input: '입력',
  logic: '로직',
  output: '출력'
} satisfies { [K in BlockKind]: string };

/** 블럭에는 이름이 없어 종류와 로직 순번으로 부른다: 입력, 로직 1, 로직 2, 출력 */
export function blockLabels(blocks: { kind: BlockKind }[]): string[] {
  let logic = 0;

  return blocks.map((b) => (b.kind === 'logic' ? `로직 ${++logic}` : BLOCK_KIND_LABEL[b.kind]));
}

/** 문장들이 걸친 줄 번호 (1부터, 오름차순) */
export function unitLines(units: Span[], indices: number[]): number[] {
  const lines = new Set<number>();

  for (const i of indices) {
    for (let line = units[i].start[0]; line <= units[i].end[0]; line++) lines.add(line);
  }

  return [...lines].sort((a, b) => a - b);
}

/** 예제 답이 답 칸보다 길면 "..."로 줄인다 */
export function truncate(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max).trimEnd()}...` : text;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('ko-KR');
}

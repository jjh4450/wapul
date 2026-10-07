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

/**
 * 블럭 색. fill은 문장 바탕, strong은 마우스를 올린 블럭의 바탕, bar는 줄 번호 옆 띠.
 * Tailwind가 찾을 수 있게 클래스 이름을 통째로 적는다
 */
export type BlockColor = { fill: string; strong: string; bar: string };

const INPUT_COLOR = { fill: 'bg-sky-500/20', strong: 'bg-sky-500/45', bar: 'bg-sky-500' };

const OUTPUT_COLOR = { fill: 'bg-violet-500/20', strong: 'bg-violet-500/45', bar: 'bg-violet-500' };

// 로직 블럭은 순번대로 돌려 쓴다. 입력·출력의 파랑·보라와 헷갈리지 않는 색만 둔다
const LOGIC_COLORS = [
  { fill: 'bg-amber-500/25', strong: 'bg-amber-500/50', bar: 'bg-amber-500' },
  { fill: 'bg-emerald-500/20', strong: 'bg-emerald-500/45', bar: 'bg-emerald-500' },
  { fill: 'bg-rose-500/20', strong: 'bg-rose-500/45', bar: 'bg-rose-500' },
  { fill: 'bg-lime-500/25', strong: 'bg-lime-500/50', bar: 'bg-lime-500' },
  { fill: 'bg-fuchsia-500/20', strong: 'bg-fuchsia-500/45', bar: 'bg-fuchsia-500' }
];

/** 블럭 색은 이름(blockLabels)을 따른다: 입력과 출력은 늘 같은 색, 로직 n은 n번째 색 */
export function blockColors(blocks: { kind: BlockKind }[]): BlockColor[] {
  let logic = 0;

  return blocks.map((b) => {
    if (b.kind === 'input') return INPUT_COLOR;

    if (b.kind === 'output') return OUTPUT_COLOR;

    return LOGIC_COLORS[logic++ % LOGIC_COLORS.length];
  });
}

/** 문장들이 끝나는 줄. 블럭의 질문과 블럭 고르는 창을 이 줄 아래에 단다 */
export function lastLine(units: Span[], indices: number[]): number {
  return Math.max(...indices.map((i) => units[i].end[0]));
}

/** 예제 답이 답 칸보다 길면 "..."로 줄인다 */
export function truncate(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max).trimEnd()}...` : text;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('ko-KR');
}

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
 * 블럭 색. style은 요소에 넣을 CSS 변수(--block: 색)이고, fill은 문장 바탕, strong은 마우스를 올린
 * 블럭의 바탕, bar는 줄 번호 옆 띠의 클래스다. 변수는 자식에게 이어져서 안쪽 요소도 bar 등으로 칠할 수 있다
 */
export type BlockColor = { style: string; fill: string; strong: string; bar: string };

const FILL = 'bg-(--block)/25';

const STRONG = 'bg-(--block)/50';

const BAR = 'bg-(--block)';

// Tailwind의 sky-500, violet-500
const INPUT_COLOR = 'oklch(0.685 0.169 237.3)';

const OUTPUT_COLOR = 'oklch(0.606 0.25 292.7)';

// 로직 블럭이 쓰는 색상(hue): 입력(파랑)과 출력(보라) 근처인 205~320도를 뺀 320도부터 245도
const LOGIC_HUE_FROM = 320;

const LOGIC_HUE_SPAN = 245;

const GOLDEN = (Math.sqrt(5) - 1) / 2;

// 로직 색의 밝기와 채도. 밝은 단계는 화면에 담을 수 있게 채도를 낮춘다
const TONES = [
  [0.74, 0.16],
  [0.6, 0.16],
  [0.86, 0.11]
] as const;

/**
 * n번째(0부터) 로직 블럭의 색. 색상을 황금비 간격으로 뽑아 앞 색들과 먼 쪽에 놓으므로 번호가 몇이든
 * 같은 색이 다시 나오지 않는다. 번호로만 정해져서 블럭을 더해도 있던 블럭의 색은 그대로다.
 * 황금비 간격은 5, 8, 13번째 뒤 색상이 가까워지므로 밝기를 세 단계로 돌려 써서 그런 짝도 구분되게
 * 한다. 첫 로직은 노랑(70도)에서 시작한다
 */
function logicColor(n: number): string {
  const hue = (LOGIC_HUE_FROM + ((0.449 + n * GOLDEN) % 1) * LOGIC_HUE_SPAN) % 360;
  const [lightness, chroma] = TONES[n % TONES.length];

  return `oklch(${lightness} ${chroma} ${hue.toFixed(1)})`;
}

function paint(color: string): BlockColor {
  return { style: `--block: ${color}`, fill: FILL, strong: STRONG, bar: BAR };
}

/** 블럭 색은 이름(blockLabels)을 따른다: 입력과 출력은 늘 같은 색, 로직 n은 n번째 색 */
export function blockColors(blocks: { kind: BlockKind }[]): BlockColor[] {
  let logic = 0;

  return blocks.map((b) => {
    if (b.kind === 'input') return paint(INPUT_COLOR);

    if (b.kind === 'output') return paint(OUTPUT_COLOR);

    return paint(logicColor(logic++));
  });
}

/** 문장들이 끝나는 줄. 블럭의 질문과 블럭 고르는 창을 이 줄 아래에 단다 */
export function lastLine(units: Span[], indices: number[]): number {
  return Math.max(...indices.map((i) => units[i].end[0]));
}

/** 문장들이 걸친 줄 */
export function unitLines(units: Span[], indices: number[]): Set<number> {
  const lines = new Set<number>();

  for (const i of indices) for (let l = units[i].start[0]; l <= units[i].end[0]; l++) lines.add(l);

  return lines;
}

/** 예제 답이 답 칸보다 길면 "..."로 줄인다 */
export function truncate(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max).trimEnd()}...` : text;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('ko-KR');
}

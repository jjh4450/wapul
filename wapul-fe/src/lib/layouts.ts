/**
 * 결과물 md 배치안. wapul-be의 app/services/layouts.py를 옮긴 것으로, 브라우저 안의 백엔드(api/local.ts)가 쓴다.
 * 줄은 줄바꿈 문자로만 나눈다. 백엔드의 splitlines()는 폼 피드나 U+2028 같은 글자에서도 나눠서 그런 코드에서만 다르다.
 *
 * 구성: 문제 → 접근 → 구현. 배치안끼리 다른 것은 순서뿐이고,
 * 사용자가 쓴 문장은 그대로 옮긴다. 답이 빈 질문은 싣지 않는다.
 */
import type { BlockOut, LayoutOut, QuestionOut, RecordOut } from '#lib/api/client.js';

function fence(code: string, language: string): string {
  // 코드 안의 백틱 줄보다 긴 펜스를 써야 블럭이 중간에 끊기지 않는다
  const longest = (code.match(/`+/g) ?? []).reduce((most, run) => Math.max(most, run.length), 0);

  const mark = '`'.repeat(Math.max(3, longest + 1));

  return `${mark}${language}\n${code.trimEnd()}\n${mark}`;
}

/** 정렬된 줄 번호를 이어진 구간으로 묶는다 */
function runs(lines: number[]): [number, number][] {
  const result: [number, number][] = [];

  for (const line of lines) {
    const last = result.at(-1);

    if (last && last[1] + 1 === line) last[1] = line;
    else result.push([line, line]);
  }

  return result;
}

const qa = (question: QuestionOut) => `**${question.text}**\n\n${question.answer.trim()}`;

export function buildLayouts(record: RecordOut): LayoutOut[] {
  const { blocks } = record;

  // 문장 위치(units)와 같은 기준으로 줄을 나눈다
  const lines = record.code.split('\n');

  // 블럭에 이름이 없어 종류와 로직 순번으로 부른다
  let logic = 0;

  const labels = new Map<string, string>(
    blocks.map((b) => [
      b.id,
      b.kind === 'logic' ? `로직 ${++logic}` : b.kind === 'input' ? '입력' : '출력'
    ])
  );

  // 질문은 한 번만 나눠 둔다 (블럭마다 전체를 다시 훑으면 질문과 블럭이 많은 기록에서 멈춘다)
  const problem: QuestionOut[] = [];

  const revision: QuestionOut[] = [];

  const loose: QuestionOut[] = [];

  const byBlock = new Map<string, QuestionOut[]>();

  for (const q of record.questions) {
    if (q.answer.trim() === '') continue;

    if (q.kind === 'problem') problem.push(q);
    else if (q.kind === 'revision') revision.push(q);
    else if (q.block_id === null) loose.push(q);
    else {
      const list = byBlock.get(q.block_id);

      if (list) list.push(q);
      else byBlock.set(q.block_id, [q]);
    }
  }

  const notes = (block: BlockOut) => (byBlock.get(block.id) ?? []).map(qa);

  // 블럭마다 줄 구간과 제목은 한 번만 만든다
  const parts = blocks.map((block) => {
    const covered = new Set<number>();

    for (const i of block.units) {
      const { start, end } = record.units[i];

      for (let line = start[0]; line <= end[0]; line++) covered.add(line);
    }

    const blockRuns = runs([...covered].sort((a, b) => a - b));

    const where = blockRuns.map(([a, b]) => (a === b ? `${a}` : `${a}~${b}`)).join(', ');

    return { block, blockRuns, heading: `### ${labels.get(block.id)} (${where}줄)` };
  });

  // 블럭의 문장이 떨어져 있으면 사이를 ...로 줄인다
  const blockCode = (blockRuns: [number, number][]) =>
    fence(
      blockRuns.map(([a, b]) => lines.slice(a - 1, b).join('\n')).join('\n...\n'),
      record.language
    );

  const fullCode = fence(record.code, record.language);

  const head = [
    `# ${record.problem}`,
    '## 문제',
    record.problem,
    '## 접근',
    `**핵심 아이디어**\n\n${record.key_idea}`,
    ...problem.map(qa)
  ].join('\n\n');

  const tail = [
    ...loose.map(qa),
    ...(revision.length === 0
      ? []
      : [
          '### 처음 제출과의 차이',
          // 달라진 점은 처음 제출에서 틀렸다고 표시한 블럭에 붙으므로 어느 블럭인지 함께 적는다
          ...revision.map((q) => {
            const label = q.block_id === null ? undefined : labels.get(q.block_id);

            return label === undefined ? qa(q) : `#### ${label}\n\n${qa(q)}`;
          })
        ])
  ];

  const codeFirst = [
    head,
    '## 구현',
    fullCode,
    ...parts.flatMap((p) => [p.heading, ...notes(p.block)]),
    ...tail
  ];

  const interleaved = [
    head,
    '## 구현',
    ...parts.flatMap((p) => [p.heading, blockCode(p.blockRuns), ...notes(p.block)]),
    ...tail,
    '### 전체 코드',
    fullCode
  ];

  const notesFirst = [
    head,
    '## 구현',
    ...parts.flatMap((p) => [p.heading, ...notes(p.block)]),
    ...tail,
    '### 전체 코드',
    fullCode
  ];

  const join = (parts: string[]) => `${parts.join('\n\n')}\n`;

  return [
    { id: 'code-first', title: '전체 코드 먼저', markdown: join(codeFirst) },
    { id: 'interleaved', title: '블럭마다 코드와 설명', markdown: join(interleaved) },
    { id: 'notes-first', title: '설명 먼저, 코드는 끝에', markdown: join(notesFirst) }
  ];
}

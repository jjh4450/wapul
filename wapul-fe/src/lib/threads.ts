/**
 * 답 쓰기 화면의 질문 묶음 규칙: 진행도, 화면 읽기에 읽히는 이름, 펼칠 질문, 넘어갈 묶음.
 * 화면(AnswerSheet)과 떨어진 순수 함수라 CI(server 프로젝트)에서 돈다.
 */
import type { QuestionKind } from '#lib/api/client.js';
import { filled, hasBlank, skippable, unanswered } from '#lib/closeGuard.svelte.js';
import { truncate } from '#lib/study.js';

/** 진행도를 세는 데 쓰는 질문의 종류와 답 */
type Asked = { kind: QuestionKind; answer: string };

/** answered: 답한 필수 질문 수, total: 필수 질문 수, optional: 건너뛸 수 있는 질문 수 */
export type Progress = { answered: number; total: number; optional: number };

export function progress(questions: Asked[]): Progress {
  const required = questions.filter((q) => !skippable(q));

  return {
    answered: required.filter(filled).length,
    total: required.length,
    optional: questions.length - required.length
  };
}

/** 묶음 막대의 이름. '0/2'는 화면 읽기가 분수나 날짜로 읽어서 풀어 쓴다 */
export function progressName(label: string, p: Progress): string {
  const optional = p.optional > 0 ? `, 선택 질문 ${p.optional}개` : '';

  return `${label}, 질문 ${p.total}개 중 ${p.answered}개 답함${optional}`;
}

/** 한 줄로 접은 질문 단추의 이름 */
export function questionName(q: Asked & { text: string }): string {
  const state = filled(q)
    ? `내 답: ${truncate(q.answer.trim().replace(/\s+/g, ' '), 80)}`
    : '아직 답하지 않음';

  return `${q.text}, ${state}${skippable(q) ? ', 선택' : ''}`;
}

/** 묶음을 열 때 펼칠 질문: 첫 빈 필수 질문, 없으면 첫 빈 질문, 다 답했으면 첫 질문 */
export function firstGap(questions: Asked[]): number {
  const required = questions.findIndex(unanswered);

  if (required !== -1) return required;

  return Math.max(
    0,
    questions.findIndex((q) => !filled(q))
  );
}

/** 펼칠 묶음: 빈 필수 질문이 남은 첫 묶음, 없으면 첫 묶음 */
export function firstOpen<T extends { questions: Asked[] }>(threads: T[]): T | undefined {
  return threads.find((t) => hasBlank(t.questions)) ?? threads[0];
}

/** 묶음 끝에서 넘어갈 묶음: 뒤의 묶음 가운데 펼칠 묶음. 앞으로는 돌아가지 않는다 */
export function nextThread<T extends { key: string; questions: Asked[] }>(
  threads: T[],
  key: string
): T | undefined {
  return firstOpen(threads.slice(threads.findIndex((t) => t.key === key) + 1));
}

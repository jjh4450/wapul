import { describe, expect, it } from 'vitest';
import { filled } from '#lib/closeGuard.svelte.js';
import {
  firstGap,
  firstOpen,
  nextThread,
  progress,
  progressName,
  questionName
} from '#lib/threads.js';

const logic = (answer = '') => ({ kind: 'logic' as const, answer });

const boundary = (answer = '') => ({ kind: 'boundary' as const, answer });

const revision = (answer = '') => ({ kind: 'revision' as const, answer });

describe('progress', () => {
  it('counts the revision question apart, as optional', () => {
    expect(progress([logic(), boundary('x'), revision()])).toEqual({
      answered: 1,
      total: 2,
      optional: 1
    });
  });

  it('takes a blank-only answer as unanswered', () => {
    expect(filled(logic(' \n '))).toBe(false);
    expect(progress([logic('  ')]).answered).toBe(0);
  });
});

describe('names', () => {
  it('spells the progress out for screen readers', () => {
    expect(progressName('로직 1', { answered: 0, total: 2, optional: 1 })).toBe(
      '로직 1, 질문 2개 중 0개 답함, 선택 질문 1개'
    );
    expect(progressName('입력', { answered: 1, total: 2, optional: 0 })).toBe(
      '입력, 질문 2개 중 1개 답함'
    );
  });

  it('names a folded question by its answer, or as unanswered', () => {
    expect(questionName({ text: '왜 그런가요?', ...logic('  정렬했기\n때문이다 ') })).toBe(
      '왜 그런가요?, 내 답: 정렬했기 때문이다'
    );
    expect(questionName({ text: '왜 그런가요?', ...logic('가'.repeat(90)) })).toBe(
      `왜 그런가요?, 내 답: ${'가'.repeat(80)}...`
    );
    expect(questionName({ text: '무엇이 달라졌나요?', ...revision() })).toBe(
      '무엇이 달라졌나요?, 아직 답하지 않음, 선택'
    );
  });
});

describe('firstGap', () => {
  it('opens the first blank required question, then a blank optional one, else the first', () => {
    expect(firstGap([logic('a'), revision(), boundary()])).toBe(2);
    expect(firstGap([logic('a'), revision(), boundary('b')])).toBe(1);
    expect(firstGap([logic('a'), revision('c'), boundary('b')])).toBe(0);
  });
});

describe('nextThread', () => {
  const threads = [
    { key: 'problem', questions: [logic()] },
    { key: 'input', questions: [logic('a')] },
    { key: 'logic', questions: [logic('b'), revision()] },
    { key: 'output', questions: [logic()] },
    { key: 'closing', questions: [logic('c')] }
  ];

  it('goes forward to the first group with a blank required question', () => {
    // 다 답한 입력과, 달라진 점 질문만 빈 로직은 건너뛴다
    expect(nextThread(threads, 'problem')?.key).toBe('output');
  });

  it('opens the first group with a blank required question, else the first', () => {
    expect(firstOpen(threads)?.key).toBe('problem');
    expect(firstOpen(threads.slice(1, 3))?.key).toBe('input');
  });

  it('goes to the very next group when nothing later is blank, and never back', () => {
    expect(nextThread(threads, 'output')?.key).toBe('closing');
    expect(nextThread(threads, 'closing')).toBeUndefined();
  });
});

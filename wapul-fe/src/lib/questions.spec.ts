import { describe, expect, it } from 'vitest';
import type { RecordOut } from './api/client.js';
import { record } from './api/fixtures.js';
import { type BlockFacts, blockFacts, buildQuestions, keepQuestions } from './questions.js';

/** 같은 seed면 같은 수열 */
function seeded(seed: number): () => number {
  let state = seed;

  return () => {
    state = (state * 1103515245 + 12345) % 2 ** 31;

    return state / 2 ** 31;
  };
}

const facts = (kind: BlockFacts['kind'], tags: Partial<BlockFacts> = {}): BlockFacts => ({
  kind,
  condition: false,
  loop: false,
  recursion: false,
  wrong: false,
  ...tags
});

const blocks = [facts('input'), facts('logic', { condition: true }), facts('output')];

describe('buildQuestions', () => {
  it('follows the block kinds and adds a boundary question to blocks with a condition', () => {
    const kinds = buildQuestions(blocks, seeded(1))
      .map((q) => q.kind)
      .filter((k) => k !== 'varying');

    expect(kinds).toEqual([
      'problem',
      'input_meaning',
      'input_condition',
      'logic',
      'boundary',
      'output_meaning',
      'output_format'
    ]);
  });

  it('adds exactly one varying question', () => {
    const questions = buildQuestions(blocks, seeded(2));

    expect(questions.filter((q) => q.kind === 'varying')).toHaveLength(1);
  });

  it('asks the revision question after the questions of each block marked wrong', () => {
    expect(buildQuestions(blocks).some((q) => q.kind === 'revision')).toBe(false);

    const marked = [
      facts('input'),
      facts('logic', { condition: true, wrong: true }),
      facts('output')
    ];

    const kinds = buildQuestions(marked, seeded(4))
      .filter((q) => q.block === 1 && q.kind !== 'varying')
      .map((q) => q.kind);

    expect(kinds).toEqual(['logic', 'boundary', 'revision']);
  });

  it('puts a structure question only on a block with that structure', () => {
    const recursive = [facts('logic', { recursion: true }), facts('logic')];
    const random = seeded(3);

    const structural = Array.from({ length: 300 }, () => buildQuestions(recursive, random))
      .flat()
      .filter((q) => q.kind === 'varying' && /재귀|반복/.test(q.text));

    expect(structural.length).toBeGreaterThan(0);
    expect(new Set(structural.map((q) => q.block))).toEqual(new Set([0]));
  });
});

describe('blockFacts', () => {
  it('turns a tag on when any statement of the block has it', () => {
    const unit = (tags: { condition?: boolean; loop?: boolean } = {}) => ({
      start: [1, 0],
      end: [1, 1],
      condition: false,
      loop: false,
      recursion: false,
      ...tags
    });

    const units = [unit({ loop: true }), unit({ condition: true }), unit()];

    expect(
      blockFacts(units, [
        { kind: 'logic', units: [0, 1] },
        { kind: 'output', units: [2], wrong: true }
      ])
    ).toEqual([facts('logic', { condition: true, loop: true }), facts('output', { wrong: true })]);
  });
});

describe('keepQuestions', () => {
  const old: RecordOut = {
    ...record,
    blocks: [
      { id: 'b-in', kind: 'input', units: [0] },
      { id: 'b-logic', kind: 'logic', units: [1, 2] }
    ],
    questions: [
      { id: 'q1', block_id: null, kind: 'problem', text: '옛 문제 질문', answer: '성질' },
      { id: 'q2', block_id: 'b-in', kind: 'input_meaning', text: '옛 입력 질문', answer: 'n은 수' },
      { id: 'q3', block_id: 'b-logic', kind: 'logic', text: '옛 로직 질문', answer: '보장' },
      { id: 'q4', block_id: 'b-in', kind: 'varying', text: '옛 바뀌는 질문', answer: '관점' }
    ]
  };

  it('carries text and answer for unchanged blocks only', () => {
    // 입력 블럭은 그대로, 로직 블럭은 문장이 바뀌었다
    const kept = keepQuestions(
      buildQuestions([facts('input'), facts('logic')]),
      [
        { kind: 'input', units: [0] },
        { kind: 'logic', units: [1] }
      ],
      old
    );

    expect(kept.find((q) => q.kind === 'problem')).toMatchObject({
      text: '옛 문제 질문',
      answer: '성질'
    });
    expect(kept.find((q) => q.kind === 'input_meaning')).toMatchObject({
      answer: 'n은 수',
      block: 0
    });
    expect(kept.find((q) => q.kind === 'logic')).toMatchObject({ answer: '', block: 1 });
    // 바뀌는 질문이 붙었던 입력 블럭이 남아 있어서 이전 질문을 그대로 쓴다
    expect(kept.filter((q) => q.kind === 'varying')).toEqual([
      { kind: 'varying', text: '옛 바뀌는 질문', answer: '관점', block: 0 }
    ]);
  });

  it('draws a new varying question when its block is gone', () => {
    const kept = keepQuestions(
      buildQuestions([facts('logic')]),
      [{ kind: 'logic', units: [0, 1, 2] }],
      old
    );

    expect(kept.filter((q) => q.kind === 'varying')).toHaveLength(1);
    expect(kept.some((q) => q.text === '옛 바뀌는 질문')).toBe(false);
  });
});

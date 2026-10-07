import { describe, expect, it } from 'vitest';
import type { BlockKind } from './api/client.js';
import { BlockDraft } from './blockDraft.svelte.js';
import type { MarkedBlock } from './questions.js';

const block = (kind: BlockKind, units: number[], wrong = false): MarkedBlock => ({
  kind,
  units,
  wrong
});

const kinds = (draft: BlockDraft) => draft.blocks.map((b) => b.kind);

const units = (draft: BlockDraft) => draft.blocks.map((b) => b.units);

/** 고른 문장을 선택창의 label 버튼으로 넣는다 */
function put(draft: BlockDraft, selected: number[], label: string) {
  const choice = draft.choices.find((c) => c.label === label);

  if (choice === undefined) throw new Error(`no choice ${label}`);

  draft.selected = selected;
  draft.place(choice.into);
}

describe('BlockDraft', () => {
  it('puts input first and output last, keeps logic in order, and sorts the units', () => {
    const draft = new BlockDraft([
      block('output', [9]),
      block('logic', [7, 5]),
      block('logic', [3]),
      block('input', [1])
    ]);

    expect(kinds(draft)).toEqual(['input', 'logic', 'logic', 'output']);
    expect(units(draft)).toEqual([[1], [5, 7], [3], [9]]);
    expect(draft.labels).toEqual(['입력', '로직 1', '로직 2', '출력']);
  });

  it('offers the existing blocks, a new logic before output, and input or output only when missing', () => {
    const labels = (draft: BlockDraft) => draft.choices.map((c) => c.label);

    expect(labels(new BlockDraft())).toEqual(['+ 입력', '+ 로직 1', '+ 출력']);
    expect(labels(new BlockDraft([block('logic', [1])]))).toEqual([
      '+ 입력',
      '로직 1',
      '+ 로직 2',
      '+ 출력'
    ]);
    expect(
      labels(new BlockDraft([block('input', [0]), block('logic', [1]), block('output', [2])]))
    ).toEqual(['입력', '로직 1', '+ 로직 2', '출력']);
  });

  it('keeps piling statements into the same logic block, moving them out of their old block', () => {
    const draft = new BlockDraft([
      block('input', [0, 1]),
      block('logic', [2]),
      block('output', [9])
    ]);

    put(draft, [1], '로직 1');
    put(draft, [5], '로직 1');
    put(draft, [0], '로직 1');

    expect(units(draft)).toEqual([[], [0, 1, 2, 5], [9]]);
    expect(draft.labels).toEqual(['입력', '로직 1', '출력']);
    expect(draft.selected).toEqual([]);
  });

  it('adds a new logic block after the existing ones, before output', () => {
    const draft = new BlockDraft([block('input', [0]), block('logic', [5]), block('output', [9])]);

    put(draft, [2], '+ 로직 2');

    expect(kinds(draft)).toEqual(['input', 'logic', 'logic', 'output']);
    expect(units(draft)).toEqual([[0], [5], [2], [9]]);
    expect(draft.choices.map((c) => c.label)).toEqual([
      '입력',
      '로직 1',
      '로직 2',
      '+ 로직 3',
      '출력'
    ]);
  });

  it('keeps a block that lost all its statements so numbers do not shift, but does not save it', () => {
    const draft = new BlockDraft([block('input', [0]), block('logic', [1]), block('logic', [2])]);

    draft.selected = [1];
    draft.place();

    expect(units(draft)).toEqual([[0], [], [2]]);
    expect(draft.labels).toEqual(['입력', '로직 1', '로직 2']);
    expect(draft.filled).toEqual([block('input', [0]), block('logic', [2])]);
    expect(draft.owned).toEqual([0, 2]);
  });

  it('appends a block turned into logic as the last logic', () => {
    const draft = new BlockDraft([block('input', [0]), block('logic', [1]), block('output', [2])]);

    draft.setKind(2, 'logic');

    expect(kinds(draft)).toEqual(['input', 'logic', 'logic']);
    expect(units(draft)).toEqual([[0], [1], [2]]);
  });

  it('merges into the existing input or output, carrying the wrong mark', () => {
    const draft = new BlockDraft([
      block('input', [0]),
      block('logic', [1], true),
      block('output', [2])
    ]);

    draft.setKind(1, 'output');

    expect(draft.blocks).toEqual([block('input', [0]), block('output', [1, 2], true)]);

    draft.setKind(1, 'input');

    expect(draft.blocks).toEqual([block('input', [0, 1, 2], true)]);
  });

  it('turns a logic block into the missing input and moves it to the front', () => {
    const draft = new BlockDraft([block('logic', [3]), block('logic', [1])]);

    draft.setKind(1, 'input');

    expect(draft.blocks).toEqual([block('input', [1]), block('logic', [3])]);
  });

  it('marks and removes blocks', () => {
    const draft = new BlockDraft([block('input', [0]), block('logic', [1])]);

    draft.setWrong(1, true);

    expect(draft.blocks[1].wrong).toBe(true);

    draft.remove(0);

    expect(draft.blocks).toEqual([block('logic', [1], true)]);
  });

  it('undoes and redoes whole steps, and a new change drops the redo steps', () => {
    const draft = new BlockDraft([block('input', [0]), block('logic', [1])]);

    expect(draft.canUndo).toBe(false);
    expect(draft.canRedo).toBe(false);

    draft.remove(1);
    draft.selected = [0];
    draft.undo();

    expect(draft.blocks).toEqual([block('input', [0]), block('logic', [1])]);
    expect(draft.selected).toEqual([]);
    expect(draft.canRedo).toBe(true);

    draft.redo();

    expect(draft.blocks).toEqual([block('input', [0])]);

    draft.undo();
    draft.setWrong(0, true);

    expect(draft.canRedo).toBe(false);

    draft.redo();

    expect(draft.blocks).toEqual([block('input', [0], true), block('logic', [1])]);
  });

  it('does nothing on undo or redo with no steps', () => {
    const draft = new BlockDraft([block('input', [0])]);

    draft.undo();
    draft.redo();

    expect(draft.blocks).toEqual([block('input', [0])]);
  });
});

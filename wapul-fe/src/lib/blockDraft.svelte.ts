import type { BlockKind } from '#lib/api/client.js';
import type { MarkedBlock } from '#lib/questions.js';
import { BLOCK_KIND_LABEL, blockColors, blockLabels } from '#lib/study.js';

/** 고른 문장을 넣을 곳. into는 고른 문장을 원래 블럭에서 뺀 블럭 목록에 문장을 넣는다 */
export type Choice = {
  label: string;
  bar?: string;
  into: (next: MarkedBlock[], picked: number[]) => void;
};

const RANK = { input: 0, logic: 1, output: 2 } satisfies { [K in BlockKind]: number };

/**
 * 입력을 맨 앞, 출력을 맨 뒤에 둔다. 로직 블럭은 만든 순서 그대로 두고, 문장이 다 빠진 블럭도
 * 남겨 둔다(저장할 때 뺀다). 그래야 고치는 동안 블럭 번호와 색이 바뀌지 않는다
 */
function arrange(next: MarkedBlock[]): MarkedBlock[] {
  return next
    .map((b) => ({ ...b, units: b.units.toSorted((x, y) => x - y) }))
    .sort((a, b) => RANK[a.kind] - RANK[b.kind]);
}

/**
 * 고치는 중인 블럭 목록. 고른 문장 넣기, 종류 바꾸기, 틀렸다는 표시, 블럭 빼기, 되돌리기와 다시 하기를
 * 맡는다. 컴포넌트는 이것을 그리기만 한다
 */
export class BlockDraft {
  blocks = $state<MarkedBlock[]>([]);

  /** 끌어서 고른 문장. 블럭을 바꾸면 비운다 */
  selected = $state<number[]>([]);

  // 되돌리기와 다시 하기. 바꾸기 전 블럭 목록을 통째로 쌓는다
  #past = $state.raw<MarkedBlock[][]>([]);

  #future = $state.raw<MarkedBlock[][]>([]);

  labels = $derived(blockLabels(this.blocks));

  colors = $derived(blockColors(this.blocks));

  /** 블럭에 든 문장 */
  owned = $derived(this.blocks.flatMap((b) => b.units));

  /** 문장이 든 블럭. 문장이 다 빠진 블럭은 저장하지 않는다 */
  filled = $derived(this.blocks.filter((b) => b.units.length > 0));

  // 입력, 지금 있는 로직들, 새 로직(로직 n+1), 출력 순. 입력과 출력은 블럭이 없을 때만 새로 만든다
  choices = $derived.by(() => {
    const newLogic: Choice = {
      label: `+ ${BLOCK_KIND_LABEL.logic} ${this.blocks.filter((b) => b.kind === 'logic').length + 1}`,
      into: (next, picked) => next.push({ kind: 'logic', units: picked, wrong: false })
    };

    const list: Choice[] = [];

    if (this.blocks[0]?.kind !== 'input') {
      list.push({
        label: `+ ${BLOCK_KIND_LABEL.input}`,
        into: (next, picked) => next.push({ kind: 'input', units: picked, wrong: false })
      });
    }

    this.blocks.forEach((b, i) => {
      if (b.kind === 'output') list.push(newLogic);

      list.push({
        label: this.labels[i],
        bar: this.colors[i].bar,
        into: (next, picked) => next[i].units.push(...picked)
      });
    });

    if (this.blocks.at(-1)?.kind !== 'output') {
      list.push(newLogic, {
        label: `+ ${BLOCK_KIND_LABEL.output}`,
        into: (next, picked) => next.push({ kind: 'output', units: picked, wrong: false })
      });
    }

    return list;
  });

  constructor(blocks: MarkedBlock[] = []) {
    this.blocks = arrange(blocks);
  }

  get canUndo(): boolean {
    return this.#past.length > 0;
  }

  get canRedo(): boolean {
    return this.#future.length > 0;
  }

  #change(next: MarkedBlock[]) {
    this.#past = [...this.#past, $state.snapshot(this.blocks)];
    this.#future = [];
    this.blocks = arrange(next);
    this.selected = [];
  }

  undo() {
    const previous = this.#past.at(-1);

    if (previous === undefined) return;

    this.#future = [$state.snapshot(this.blocks), ...this.#future];
    this.#past = this.#past.slice(0, -1);
    this.blocks = previous;
    this.selected = [];
  }

  redo() {
    const [next, ...rest] = this.#future;

    if (next === undefined) return;

    this.#past = [...this.#past, $state.snapshot(this.blocks)];
    this.#future = rest;
    this.blocks = next;
    this.selected = [];
  }

  /** 고른 문장을 원래 블럭에서 빼고, into가 있으면 그 블럭에 넣는다 */
  place(into?: Choice['into']) {
    const picked = $state.snapshot(this.selected);

    const next = $state
      .snapshot(this.blocks)
      .map((b) => ({ ...b, units: b.units.filter((u) => !picked.includes(u)) }));

    into?.(next, picked);
    this.#change(next);
  }

  /** 블럭 하나의 종류를 바꾼다. 입력과 출력은 하나씩이라, 이미 있으면 그 블럭에 합친다 */
  setKind(i: number, kind: BlockKind) {
    const next = $state.snapshot(this.blocks);
    const into = kind === 'logic' ? -1 : next.findIndex((b) => b.kind === kind);

    if (kind === 'logic') {
      // 로직으로 바꾼 블럭은 새 로직(로직 n+1)처럼 맨 뒤에 붙어서, 있던 로직의 번호가 밀리지 않는다
      const [moved] = next.splice(i, 1);

      next.push({ ...moved, kind });
    } else if (into === -1) {
      next[i].kind = kind;
    } else {
      const target = next[into];
      const [moved] = next.splice(i, 1);

      target.units.push(...moved.units);
      target.wrong ||= moved.wrong;
    }

    this.#change(next);
  }

  setWrong(i: number, wrong: boolean) {
    const next = $state.snapshot(this.blocks);

    next[i].wrong = wrong;
    this.#change(next);
  }

  remove(i: number) {
    this.#change($state.snapshot(this.blocks).filter((_, j) => j !== i));
  }
}

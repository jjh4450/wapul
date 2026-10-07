<script lang="ts">
  import { onMount } from 'svelte';
  import { IconArrowBackUp, IconArrowForwardUp } from '@tabler/icons-svelte';
  import { api, type BlockKind, type RecordDraft, type RecordOut } from '#lib/api/client.js';
  import CodeView from '#lib/components/CodeView.svelte';
  import { Button } from '#lib/components/ui/button/index.js';
  import { blockFacts, buildQuestions, keepQuestions, type MarkedBlock } from '#lib/questions.js';
  import { BLOCK_KIND_LABEL, blockColors, blockLabels, lastLine } from '#lib/study.js';
  import { cn } from '#lib/utils.js';

  /** 고른 문장을 넣을 곳. into는 고른 문장을 원래 블럭에서 뺀 블럭 목록에 문장을 넣는다 */
  type Choice = {
    label: string;
    bar?: string;
    into: (next: MarkedBlock[], picked: number[]) => void;
  };

  let {
    id,
    draft,
    onsaved
  }: {
    /** 블럭을 고칠 기록 */
    id?: string;
    /** 아직 저장하지 않은 새 기록. id 대신 준다. 블럭을 하나 이상 만들고 저장할 때 기록을 만든다 */
    draft?: RecordDraft;
    /** 저장한 기록의 id를 받는다 */
    onsaved: (id: string) => void;
  } = $props();

  let record = $state<RecordDraft | null>(null);

  /** 고치는 기록. 새 기록이면 null */
  let old = $state.raw<RecordOut | null>(null);

  let blocks = $state<MarkedBlock[]>([]);

  /** 끌어서 고른 문장. 넣을 블럭을 고르면 비운다 */
  let selected = $state<number[]>([]);

  // 되돌리기와 다시 하기. 바꾸기 전 블럭 목록을 통째로 쌓는다
  let past = $state.raw<MarkedBlock[][]>([]);

  let future = $state.raw<MarkedBlock[][]>([]);

  let error = $state('');

  let saving = $state(false);

  const labels = $derived(blockLabels(blocks));

  const colors = $derived(blockColors(blocks));

  const owned = $derived(new Set(blocks.flatMap((b) => b.units)));

  /** 블럭 고르는 창을 달 줄: 고른 문장이 끝나는 줄 */
  const pickerLine = $derived(
    record && selected.length > 0 ? lastLine(record.units, selected) : null
  );

  // 입력, 로직들, 새 로직, 출력 순. 입력과 출력은 블럭이 없을 때만 새로 만든다
  // 입력, 지금 있는 로직들, 새 로직(로직 n+1), 출력 순. 입력과 출력은 블럭이 없을 때만 새로 만든다
  const choices = $derived.by(() => {
    const newLogic: Choice = {
      label: `+ ${BLOCK_KIND_LABEL.logic} ${blocks.filter((b) => b.kind === 'logic').length + 1}`,
      into: (next, picked) => next.push({ kind: 'logic', units: picked, wrong: false })
    };

    const list: Choice[] = [];

    if (blocks[0]?.kind !== 'input') {
      list.push({
        label: `+ ${BLOCK_KIND_LABEL.input}`,
        into: (next, picked) => next.push({ kind: 'input', units: picked, wrong: false })
      });
    }

    blocks.forEach((b, i) => {
      if (b.kind === 'output') list.push(newLogic);
      list.push({
        label: labels[i],
        bar: colors[i].bar,
        into: (next, picked) => next[i].units.push(...picked)
      });
    });

    if (blocks.at(-1)?.kind !== 'output') {
      list.push(newLogic, {
        label: `+ ${BLOCK_KIND_LABEL.output}`,
        into: (next, picked) => next.push({ kind: 'output', units: picked, wrong: false })
      });
    }

    return list;
  });

  onMount(async () => {
    if (draft !== undefined) {
      record = draft;

      return;
    }

    if (id === undefined) return;

    const result = await api.getRecord(id);

    if (!result.ok) {
      error = result.message;

      return;
    }

    record = result.data;
    old = result.data;
    // 처음 제출에서 틀렸다는 표시는 그 블럭에 붙은 달라진 점 질문으로 남아 있다
    blocks = arrange(
      result.data.blocks.map((b) => ({
        kind: b.kind,
        units: [...b.units],
        wrong: result.data.questions.some((q) => q.kind === 'revision' && q.block_id === b.id)
      }))
    );
  });

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

  function change(next: MarkedBlock[]) {
    past = [...past, $state.snapshot(blocks)];
    future = [];
    blocks = arrange(next);
    selected = [];
  }

  function undo() {
    const previous = past.at(-1);

    if (previous === undefined) return;

    future = [$state.snapshot(blocks), ...future];
    past = past.slice(0, -1);
    blocks = previous;
    selected = [];
  }

  function redo() {
    const [next, ...rest] = future;

    if (next === undefined) return;

    past = [...past, $state.snapshot(blocks)];
    future = rest;
    blocks = next;
    selected = [];
  }

  /** 고른 문장을 원래 블럭에서 빼고, into가 있으면 그 블럭에 넣는다 */
  function place(into?: Choice['into']) {
    const picked = $state.snapshot(selected);

    const next = $state
      .snapshot(blocks)
      .map((b) => ({ ...b, units: b.units.filter((u) => !picked.includes(u)) }));

    into?.(next, picked);
    change(next);
  }

  /** 블럭 하나의 종류를 바꾼다. 입력과 출력은 하나씩이라, 이미 있으면 그 블럭에 합친다 */
  function setKind(i: number, kind: BlockKind) {
    const next = $state.snapshot(blocks);
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

    change(next);
  }

  function setWrong(i: number, wrong: boolean) {
    const next = $state.snapshot(blocks);

    next[i].wrong = wrong;
    change(next);
  }

  function removeBlock(i: number) {
    change($state.snapshot(blocks).filter((_, j) => j !== i));
  }

  function shortcut(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      selected = [];

      return;
    }

    if (!(event.ctrlKey || event.metaKey)) return;

    const key = event.key.toLowerCase();

    if (key === 'z' && !event.shiftKey) undo();
    else if (key === 'z' || key === 'y') redo();
    else return;

    event.preventDefault();
  }

  async function save() {
    // 문장이 다 빠진 블럭은 저장하지 않는다
    const kept = blocks.filter((b) => b.units.length > 0);

    if (!record || kept.length === 0) {
      error = '문장이 든 블럭이 하나는 있어야 해요.';

      return;
    }

    const questions = buildQuestions(blockFacts(record.units, kept));
    const sent = kept.map(({ kind, units }) => ({ kind, units }));

    saving = true;

    // 새 기록은 이제 만든다. 고치는 기록은 질문을 새 블럭으로 다시 만들고, 그대로 남은 블럭의
    // 질문은 문구와 답을 이어 쓴다
    const result =
      old === null
        ? await api.createRecord({ ...$state.snapshot(record), blocks: sent, questions })
        : await api.updateBlocks(old.id, sent, keepQuestions(questions, sent, old));

    saving = false;

    if (result.ok) onsaved(result.data.id);
    else error = result.message;
  }
</script>

<svelte:window onkeydown={shortcut} />

{#snippet picker(line: number)}
  {#if line === pickerLine}
    <div
      class="my-1 mr-3 ml-11 flex flex-wrap items-center gap-2 rounded-xl border bg-background p-2 font-sans shadow-sm"
      role="group"
      aria-label="고른 문장을 넣을 블럭"
    >
      <span class="px-1 text-muted-foreground">문장 {selected.length}개를</span>
      {#each choices as choice (choice.label)}
        <Button variant="outline" size="sm" onclick={() => place(choice.into)}>
          {#if choice.bar}<span class={cn('size-2 rounded-full', choice.bar)}></span>{/if}
          {choice.label}
        </Button>
      {/each}
      {#if selected.some((u) => owned.has(u))}
        <Button variant="ghost" size="sm" onclick={() => place()}>블럭에서 빼기</Button>
      {/if}
      <Button variant="ghost" size="sm" onclick={() => (selected = [])}>취소</Button>
    </div>
  {/if}
{/snippet}

{#if record}
  <h1 class="text-2xl font-semibold">{record.problem}</h1>
  <p class="mt-1 mb-6 text-sm text-muted-foreground">
    코드를 끌어서 문장을 고른 뒤 넣을 블럭을 고르세요. 어디서 끌든 끈 범위에 온전히 든 문장만
    골라요. 줄 번호를 끌면 그 줄의 문장을 모두 골라요. 한 블럭의 문장이 떨어져 있어도 괜찮아요.
    블럭의 종류와 처음 제출에서 틀렸는지는 위의 블럭 이름을 눌러 바꿔요.
  </p>

  <div class="grid max-w-4xl gap-3">
    <div class="flex gap-2">
      <Button variant="outline" size="sm" title="Ctrl+Z" disabled={past.length === 0} onclick={undo}
        ><IconArrowBackUp />되돌리기</Button
      >
      <Button
        variant="outline"
        size="sm"
        title="Ctrl+Shift+Z"
        disabled={future.length === 0}
        onclick={redo}><IconArrowForwardUp />다시 하기</Button
      >
    </div>

    <CodeView
      code={record.code}
      language={record.language}
      units={record.units}
      {blocks}
      {selected}
      onselect={(picked) => (selected = picked)}
      onkind={setKind}
      onwrong={setWrong}
      onremove={removeBlock}
      after={picker}
    />

    {#if error}
      <p class="text-destructive">{error}</p>
    {/if}

    <div class="flex flex-wrap items-center gap-4">
      <Button disabled={saving} onclick={save}>이대로 질문 받기</Button>
      <p class="text-xs text-muted-foreground">
        {old === null
          ? '아직 저장하지 않았어요. 블럭을 하나 이상 만들고 누르면 기록이 만들어져요.'
          : '이미 쓴 답은 문장과 종류가 그대로인 블럭에서만 남아요. 빈 블럭은 저장하지 않아요.'}
      </p>
    </div>
  </div>
{:else if error}
  <p class="text-destructive">{error}</p>
{:else}
  <p class="text-muted-foreground">불러오는 중...</p>
{/if}

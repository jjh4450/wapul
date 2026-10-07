<script lang="ts">
  import { onMount } from 'svelte';
  import { IconArrowBackUp, IconArrowForwardUp } from '@tabler/icons-svelte';
  import { api, type BlockIn, type BlockKind, type RecordOut } from '#lib/api/client.js';
  import CodeView from '#lib/components/CodeView.svelte';
  import { Button } from '#lib/components/ui/button/index.js';
  import { blockFacts, buildQuestions, keepQuestions } from '#lib/questions.js';
  import { BLOCK_KIND_LABEL, blockColors, blockLabels, lastLine } from '#lib/study.js';
  import { cn } from '#lib/utils.js';

  /** 고른 문장을 넣을 곳. into는 고른 문장을 원래 블럭에서 뺀 블럭 목록에 문장을 넣는다 */
  type Choice = { label: string; bar?: string; into: (next: BlockIn[], picked: number[]) => void };

  let { id, onsaved }: { id: string; onsaved: () => void } = $props();

  let record = $state<RecordOut | null>(null);

  let blocks = $state<BlockIn[]>([]);

  /** 끌어서 고른 문장. 넣을 블럭을 고르면 비운다 */
  let selected = $state<number[]>([]);

  // 되돌리기와 다시 하기. 바꾸기 전 블럭 목록을 통째로 쌓는다
  let past = $state.raw<BlockIn[][]>([]);

  let future = $state.raw<BlockIn[][]>([]);

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
  const choices = $derived.by(() => {
    const newLogic: Choice = {
      label: `+ ${BLOCK_KIND_LABEL.logic}`,
      into: (next, picked) => next.push({ kind: 'logic', units: picked })
    };

    const list: Choice[] = [];

    if (blocks[0]?.kind !== 'input') {
      list.push({
        label: `+ ${BLOCK_KIND_LABEL.input}`,
        into: (next, picked) => next.push({ kind: 'input', units: picked })
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
        into: (next, picked) => next.push({ kind: 'output', units: picked })
      });
    }

    return list;
  });

  onMount(async () => {
    const result = await api.getRecord(id);

    if (!result.ok) {
      error = result.message;

      return;
    }

    record = result.data;
    blocks = arrange(result.data.blocks.map((b) => ({ kind: b.kind, units: [...b.units] })));
  });

  /**
   * 빈 블럭을 지우고 입력을 맨 앞, 출력을 맨 뒤에 둔다. 로직 블럭은 첫 문장 순이라
   * 로직 번호와 색이 코드에 나오는 순서를 따른다
   */
  function arrange(next: BlockIn[]): BlockIn[] {
    const rank = (b: BlockIn) =>
      b.kind === 'input' ? -1 : b.kind === 'output' ? Number.MAX_SAFE_INTEGER : b.units[0];

    return next
      .flatMap((b) =>
        b.units.length > 0 ? [{ kind: b.kind, units: b.units.toSorted((x, y) => x - y) }] : []
      )
      .sort((a, b) => rank(a) - rank(b));
  }

  function change(next: BlockIn[]) {
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
      .map((b) => ({ kind: b.kind, units: b.units.filter((u) => !picked.includes(u)) }));

    into?.(next, picked);
    change(next);
  }

  /** 블럭 하나의 종류를 바꾼다. 입력과 출력은 하나씩이라, 이미 있으면 그 블럭에 합친다 */
  function setKind(i: number, kind: BlockKind) {
    const next = $state.snapshot(blocks);
    const into = kind === 'logic' ? -1 : next.findIndex((b) => b.kind === kind);

    if (into === -1) next[i] = { kind, units: next[i].units };
    else next[into].units.push(...next.splice(i, 1)[0].units);

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
    if (!record || blocks.length === 0) {
      error = '문장이 든 블럭이 하나는 있어야 해요.';

      return;
    }

    // 질문을 새 블럭으로 다시 만들고, 그대로 남은 블럭의 질문은 문구와 답을 이어 쓴다
    const questions = keepQuestions(
      buildQuestions(blockFacts(record.units, blocks), record.initially_wrong),
      blocks,
      record
    );

    saving = true;
    const result = await api.updateBlocks(id, blocks, questions);
    saving = false;

    if (result.ok) onsaved();
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
    블럭의 종류는 위의 블럭 이름을 눌러 바꿔요.
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
      onremove={removeBlock}
      after={picker}
    />

    {#if error}
      <p class="text-destructive">{error}</p>
    {/if}

    <div class="flex flex-wrap items-center gap-4">
      <Button disabled={saving} onclick={save}>이대로 질문 받기</Button>
      <p class="text-xs text-muted-foreground">
        이미 쓴 답은 문장과 종류가 그대로인 블럭에서만 남아요.
      </p>
    </div>
  </div>
{:else if error}
  <p class="text-destructive">{error}</p>
{:else}
  <p class="text-muted-foreground">불러오는 중...</p>
{/if}

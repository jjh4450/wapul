<script lang="ts">
  import { onMount } from 'svelte';
  import { IconArrowBackUp, IconArrowForwardUp } from '@tabler/icons-svelte';
  import { api, type RecordDraft, type RecordOut } from '#lib/api/client.js';
  import { BlockDraft } from '#lib/blockDraft.svelte.js';
  import CodeView from '#lib/components/CodeView.svelte';
  import { Button } from '#lib/components/ui/button/index.js';
  import { blockFacts, buildQuestions, keepQuestions } from '#lib/questions.js';
  import { lastLine } from '#lib/study.js';
  import { cn } from '#lib/utils.js';

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

  /** 고치는 중인 블럭. 기록을 불러오면 그 블럭으로 바꿔 끼운다 */
  let editing = $state.raw(new BlockDraft());

  let error = $state('');

  let saving = $state(false);

  /** 블럭 고르는 창을 달 줄: 고른 문장이 끝나는 줄 */
  const pickerLine = $derived(
    record && editing.selected.length > 0 ? lastLine(record.units, editing.selected) : null
  );

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
    editing = new BlockDraft(
      result.data.blocks.map((b) => ({
        kind: b.kind,
        units: [...b.units],
        wrong: result.data.questions.some((q) => q.kind === 'revision' && q.block_id === b.id)
      }))
    );
  });

  function shortcut(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      editing.selected = [];

      return;
    }

    if (!(event.ctrlKey || event.metaKey)) return;

    const key = event.key.toLowerCase();

    if (key === 'z' && !event.shiftKey) editing.undo();
    else if (key === 'z' || key === 'y') editing.redo();
    else return;

    event.preventDefault();
  }

  async function save() {
    const kept = editing.filled;

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
      <span class="px-1 text-muted-foreground">문장 {editing.selected.length}개를</span>
      {#each editing.choices as choice (choice.label)}
        <Button variant="outline" size="sm" onclick={() => editing.place(choice.into)}>
          {#if choice.color}<span
              class={cn('size-2 rounded-full', choice.color.bar)}
              style={choice.color.style}
            ></span>{/if}
          {choice.label}
        </Button>
      {/each}
      {#if editing.selected.some((u) => editing.owned.includes(u))}
        <Button variant="ghost" size="sm" onclick={() => editing.place()}>블럭에서 빼기</Button>
      {/if}
      <Button variant="ghost" size="sm" onclick={() => (editing.selected = [])}>취소</Button>
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
      <Button
        variant="outline"
        size="sm"
        title="Ctrl+Z"
        disabled={!editing.canUndo}
        onclick={() => editing.undo()}><IconArrowBackUp />되돌리기</Button
      >
      <Button
        variant="outline"
        size="sm"
        title="Ctrl+Shift+Z"
        disabled={!editing.canRedo}
        onclick={() => editing.redo()}><IconArrowForwardUp />다시 하기</Button
      >
    </div>

    <CodeView
      code={record.code}
      language={record.language}
      units={record.units}
      blocks={editing.blocks}
      selected={editing.selected}
      onselect={(picked) => (editing.selected = picked)}
      onkind={(i, kind) => editing.setKind(i, kind)}
      onwrong={(i, wrong) => editing.setWrong(i, wrong)}
      onremove={(i) => editing.remove(i)}
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

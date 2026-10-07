<script lang="ts">
  import { onMount } from 'svelte';
  import { api, type BlockIn, type BlockKind, type RecordOut } from '#lib/api/client.js';
  import CodeView from '#lib/components/CodeView.svelte';
  import { Button } from '#lib/components/ui/button/index.js';
  import * as NativeSelect from '#lib/components/ui/native-select/index.js';
  import { blockFacts, buildQuestions, keepQuestions } from '#lib/questions.js';
  import { BLOCK_KIND_LABEL, blockLabels } from '#lib/study.js';
  import { cn } from '#lib/utils.js';

  let { id, onsaved }: { id: string; onsaved: () => void } = $props();

  let record = $state<RecordOut | null>(null);

  let blocks = $state<BlockIn[]>([]);

  /** 문장을 누르면 들어갈 블럭 */
  let active = $state(0);

  let error = $state('');

  let saving = $state(false);

  const kinds: BlockKind[] = ['input', 'logic', 'output'];

  const labels = $derived(blockLabels(blocks));

  const owner = $derived.by(() => {
    const of: (number | null)[] = (record?.units ?? []).map(() => null);

    blocks.forEach((b, i) => {
      for (const unit of b.units) of[unit] = i;
    });

    return of;
  });

  onMount(async () => {
    const result = await api.getRecord(id);

    if (!result.ok) {
      error = result.message;

      return;
    }

    record = result.data;
    blocks = result.data.blocks.map((b) => ({ kind: b.kind, units: [...b.units] }));
  });

  /** 고른 블럭에 든 문장이면 빼고, 아니면 원래 블럭에서 옮겨 넣는다 */
  function pick(unit: number) {
    const from = owner[unit];

    if (from !== null) blocks[from].units = blocks[from].units.filter((u) => u !== unit);

    if (from !== active)
      blocks[active].units = [...blocks[active].units, unit].sort((a, b) => a - b);
  }

  function addBlock() {
    // 출력 블럭은 끝에 남도록 그 앞에 넣는다
    const at = blocks.at(-1)?.kind === 'output' ? blocks.length - 1 : blocks.length;
    blocks.splice(at, 0, { kind: 'logic', units: [] });
    active = at;
  }

  function removeBlock(i: number) {
    blocks.splice(i, 1);
    active = Math.min(active > i ? active - 1 : active, blocks.length - 1);
  }

  async function save() {
    const kept = blocks.filter((b) => b.units.length > 0);

    if (!record || kept.length === 0) {
      error = '문장이 든 블럭이 하나는 있어야 해요.';

      return;
    }

    // 질문을 새 블럭으로 다시 만들고, 그대로 남은 블럭의 질문은 문구와 답을 이어 쓴다
    const questions = keepQuestions(
      buildQuestions(blockFacts(record.units, kept), record.initially_wrong),
      kept,
      record
    );

    saving = true;
    const result = await api.updateBlocks(id, kept, questions);
    saving = false;

    if (result.ok) onsaved();
    else error = result.message;
  }
</script>

{#if record}
  <h1 class="text-2xl font-semibold">{record.problem}</h1>
  <p class="mt-1 mb-6 text-sm text-muted-foreground">
    코드를 입력, 로직, 출력 블럭으로 나눴어요. 블럭을 고른 뒤 코드의 문장을 누르면 그 블럭에 넣거나
    뺄 수 있어요. 한 블럭의 문장이 떨어져 있어도 괜찮아요.
  </p>

  <div class="grid gap-6 lg:grid-cols-2">
    <CodeView
      code={record.code}
      units={record.units}
      {owner}
      {labels}
      onpick={pick}
      class="self-start"
    />

    <div class="grid content-start gap-3">
      {#each blocks as block, i (i)}
        <div
          class={cn(
            'flex items-center gap-2 rounded-2xl border p-3',
            i === active && 'border-primary ring-1 ring-primary'
          )}
        >
          <Button
            variant={i === active ? 'default' : 'outline'}
            size="sm"
            aria-pressed={i === active}
            onclick={() => (active = i)}>{labels[i]}</Button
          >
          <NativeSelect.Root
            size="sm"
            bind:value={block.kind}
            aria-label="블럭 종류"
            class="shrink-0"
          >
            {#each kinds as kind (kind)}
              <NativeSelect.Option value={kind}>{BLOCK_KIND_LABEL[kind]}</NativeSelect.Option>
            {/each}
          </NativeSelect.Root>
          <span class="flex-1 text-sm text-muted-foreground">문장 {block.units.length}개</span>
          <Button
            variant="destructive"
            size="sm"
            disabled={blocks.length === 1}
            onclick={() => removeBlock(i)}>빼기</Button
          >
        </div>
      {/each}

      <Button variant="outline" class="justify-self-start" onclick={addBlock}>블럭 더하기</Button>

      {#if error}
        <p class="text-destructive">{error}</p>
      {/if}

      <Button class="justify-self-start" disabled={saving} onclick={save}>이대로 질문 받기</Button>
      <p class="text-xs text-muted-foreground">
        이미 쓴 답은 문장과 종류가 그대로인 블럭에서만 남아요. 빈 블럭은 저장하지 않아요.
      </p>
    </div>
  </div>
{:else if error}
  <p class="text-destructive">{error}</p>
{:else}
  <p class="text-muted-foreground">불러오는 중...</p>
{/if}

<script lang="ts">
  import { onMount } from 'svelte';
  import { api, type BlockIn, type BlockKind, type RecordOut } from '#lib/api/client.js';
  import CodeView from '#lib/components/CodeView.svelte';
  import { Button } from '#lib/components/ui/button/index.js';
  import { Input } from '#lib/components/ui/input/index.js';
  import * as NativeSelect from '#lib/components/ui/native-select/index.js';
  import { BLOCK_KIND_LABEL } from '#lib/study.js';

  let { id, onsaved }: { id: string; onsaved: () => void } = $props();

  let record = $state<RecordOut | null>(null);

  let blocks = $state<BlockIn[]>([]);

  let error = $state('');

  let saving = $state(false);

  const kinds: BlockKind[] = ['input', 'logic', 'output'];

  const lineCount = $derived(record ? record.code.split('\n').length : 0);

  onMount(async () => {
    const result = await api.getRecord(id);

    if (!result.ok) {
      error = result.message;

      return;
    }

    record = result.data;
    blocks = result.data.blocks.map((b) => ({
      kind: b.kind,
      name: b.name,
      start_line: b.start_line,
      end_line: b.end_line
    }));
  });

  function addBlock() {
    const last = blocks.at(-1)?.end_line ?? 0;
    const start = Math.min(last + 1, lineCount);
    blocks.push({ kind: 'logic', name: '새 블럭', start_line: start, end_line: start });
  }

  async function save() {
    saving = true;
    const result = await api.updateBlocks(id, blocks);
    saving = false;

    if (result.ok) onsaved();
    else error = result.message;
  }
</script>

{#if record}
  <h1 class="text-2xl font-semibold">{record.problem}</h1>
  <p class="mt-1 mb-6 text-sm text-muted-foreground">
    코드를 입력, 로직, 출력 블럭으로 나눴어요. 하나의 하위 목표를 이루는 줄끼리 묶이도록 이름과
    범위를 고치거나 블럭을 더하고 뺄 수 있어요.
  </p>

  <div class="grid gap-6 lg:grid-cols-2">
    <CodeView code={record.code} marks={blocks} class="self-start" />

    <div class="grid content-start gap-3">
      {#each blocks as block, i (i)}
        <div class="grid gap-2 rounded-2xl border p-3">
          <div class="flex items-center gap-2">
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
            <Input bind:value={block.name} aria-label="블럭 이름" class="h-8" />
            <Button
              variant="destructive"
              size="sm"
              disabled={blocks.length === 1}
              onclick={() => blocks.splice(i, 1)}>빼기</Button
            >
          </div>
          <div class="flex items-center gap-2 text-sm">
            <Input
              type="number"
              min={1}
              max={lineCount}
              bind:value={block.start_line}
              aria-label="시작 줄"
              class="h-8 w-20"
            />
            <span>줄부터</span>
            <Input
              type="number"
              min={1}
              max={lineCount}
              bind:value={block.end_line}
              aria-label="끝 줄"
              class="h-8 w-20"
            />
            <span>줄까지</span>
          </div>
        </div>
      {/each}

      <Button variant="outline" class="justify-self-start" onclick={addBlock}>블럭 더하기</Button>

      {#if error}
        <p class="text-destructive">{error}</p>
      {/if}

      <Button class="justify-self-start" disabled={saving} onclick={save}>이대로 질문 받기</Button>
      <p class="text-xs text-muted-foreground">
        이미 쓴 답은 범위와 종류가 그대로인 블럭에서만 남아요.
      </p>
    </div>
  </div>
{:else if error}
  <p class="text-destructive">{error}</p>
{:else}
  <p class="text-muted-foreground">불러오는 중...</p>
{/if}

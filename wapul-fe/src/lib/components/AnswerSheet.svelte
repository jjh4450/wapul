<script lang="ts">
  import { onMount } from 'svelte';
  import { SvelteMap } from 'svelte/reactivity';
  import { resolve } from '$app/paths';
  import { api, type QuestionOut, type RecordOut } from '#lib/api/client.js';
  import AnswerField from '#lib/components/AnswerField.svelte';
  import CodeView from '#lib/components/CodeView.svelte';
  import { Badge } from '#lib/components/ui/badge/index.js';
  import { Button } from '#lib/components/ui/button/index.js';
  import { pickExample } from '#lib/questions.js';
  import { BLOCK_KIND_LABEL, blockLabels, unitLines } from '#lib/study.js';

  let {
    id,
    onfinish,
    onnotowner
  }: {
    id: string;
    /** 모든 답을 저장한 뒤 */
    onfinish: () => void;
    /** 작성자가 아닌 사람이 열었을 때 (답은 작성자만 쓴다) */
    onnotowner: () => void;
  } = $props();

  let record = $state<RecordOut | null>(null);

  let error = $state('');

  let status = $state('');

  /** 질문마다 다른 문제의 예제 답 (답 칸의 회색 안내문) */
  let examples = $state<{ [questionId: string]: string }>({});

  // 마지막으로 저장된 답. 바뀐 칸만 저장한다
  const saved = new SvelteMap<string, string>();

  const problemQuestions = $derived(record?.questions.filter((q) => q.kind === 'problem') ?? []);

  const labels = $derived(blockLabels(record?.blocks ?? []));

  const closingQuestions = $derived(
    record?.questions.filter((q) => q.block_id === null && q.kind !== 'problem') ?? []
  );

  onMount(async () => {
    const result = await api.getRecord(id);

    if (!result.ok) {
      error = result.message;

      return;
    }

    if (!result.data.is_owner) {
      onnotowner();

      return;
    }

    record = result.data;
    examples = Object.fromEntries(result.data.questions.map((q) => [q.id, pickExample(q.kind)]));

    for (const q of result.data.questions) saved.set(q.id, q.answer);
  });

  function blockQuestions(blockId: string): QuestionOut[] {
    return record?.questions.filter((q) => q.block_id === blockId) ?? [];
  }

  async function commit(question: QuestionOut): Promise<boolean> {
    if (saved.get(question.id) === question.answer) return true;
    const result = await api.saveAnswer(id, question.id, question.answer);

    if (!result.ok) {
      status = result.message;

      return false;
    }

    saved.set(question.id, question.answer);
    status = '저장했어요.';

    return true;
  }

  async function finish() {
    for (const q of record?.questions ?? []) {
      if (!(await commit(q))) return;
    }

    onfinish();
  }
</script>

{#snippet field(question: QuestionOut)}
  <AnswerField
    id={question.id}
    question={question.text}
    example={examples[question.id] ?? ''}
    note={question.kind === 'revision' ? '건너뛸 수 있어요.' : undefined}
    bind:value={question.answer}
    oncommit={() => commit(question)}
  />
{/snippet}

{#if record}
  <div class="mb-8 grid gap-1">
    <h1 class="text-2xl font-semibold">{record.problem}</h1>
    <p class="text-muted-foreground">핵심 아이디어: {record.key_idea}</p>
    <a
      href={resolve(`/records/blocks?id=${id}`)}
      class="text-sm text-muted-foreground underline underline-offset-4">블럭 다시 나누기</a
    >
  </div>

  <section class="mb-10 grid max-w-3xl gap-4">
    {#each problemQuestions as question (question.id)}
      {@render field(question)}
    {/each}
  </section>

  <div class="grid gap-10">
    {#each record.blocks as block, i (block.id)}
      {@const units = record.units}
      <section class="grid gap-6 lg:grid-cols-2" aria-labelledby="block-{block.id}">
        <div class="grid content-start gap-2">
          <div class="flex items-center gap-2">
            <Badge variant="secondary">{BLOCK_KIND_LABEL[block.kind]}</Badge>
            <h2 id="block-{block.id}" class="font-medium">{labels[i]}</h2>
          </div>
          <CodeView
            code={record.code}
            {units}
            owner={units.map((_, u) => (block.units.includes(u) ? i : null))}
            lines={unitLines(units, block.units)}
          />
        </div>
        <div class="grid content-start gap-5">
          {#each blockQuestions(block.id) as question (question.id)}
            {@render field(question)}
          {/each}
        </div>
      </section>
    {/each}
  </div>

  {#if closingQuestions.length > 0}
    <section class="mt-10 grid max-w-3xl gap-5">
      {#each closingQuestions as question (question.id)}
        {@render field(question)}
      {/each}
    </section>
  {/if}

  <div class="mt-10 flex items-center gap-4">
    <Button onclick={finish}>다 썼어요</Button>
    <span class="text-sm text-muted-foreground">{status}</span>
  </div>
{:else if error}
  <p class="text-destructive">{error}</p>
{:else}
  <p class="text-muted-foreground">불러오는 중...</p>
{/if}

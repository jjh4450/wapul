<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { SvelteMap } from 'svelte/reactivity';
  import { IconChevronDown, IconChevronRight } from '@tabler/icons-svelte';
  import { resolve } from '$app/paths';
  import { api, type QuestionOut, type RecordOut } from '#lib/api/client.js';
  import AnswerField from '#lib/components/AnswerField.svelte';
  import CodeView from '#lib/components/CodeView.svelte';
  import { Button } from '#lib/components/ui/button/index.js';
  import { pickExample } from '#lib/questions.js';
  import { blockColors, blockLabels, lastLine } from '#lib/study.js';
  import { cn } from '#lib/utils.js';

  /**
   * 한 번에 펼쳐 보는 질문 묶음. 블럭 질문은 블럭이 끝나는 줄(line) 아래에 달고,
   * 기록 단위 질문은 코드 위(문제)와 코드 아래(마무리)에 둔다
   */
  type Thread = {
    key: string;
    label: string;
    block: number | null;
    line: number | null;
    questions: QuestionOut[];
  };

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

  /** 펼친 질문 묶음 */
  let current = $state('');

  // 마지막으로 저장된 답. 바뀐 칸만 저장한다
  const saved = new SvelteMap<string, string>();

  const colors = $derived(blockColors(record?.blocks ?? []));

  // 화면에 나오는 순서: 문제, 블럭(끝나는 줄 순), 마무리
  const threads = $derived.by(() => {
    if (!record) return [];

    const { blocks, questions, units } = record;
    const labels = blockLabels(blocks);

    const byBlock = blocks
      .map((b, i) => ({
        key: b.id,
        label: labels[i],
        block: i,
        line: lastLine(units, b.units),
        questions: questions.filter((q) => q.block_id === b.id)
      }))
      .sort((a, b) => a.line - b.line);

    const list: Thread[] = [
      {
        key: 'problem',
        label: '문제',
        block: null,
        line: null,
        questions: questions.filter((q) => q.kind === 'problem')
      },
      ...byBlock,
      {
        key: 'closing',
        label: '마무리',
        block: null,
        line: null,
        questions: questions.filter((q) => q.block_id === null && q.kind !== 'problem')
      }
    ];

    return list.filter((t) => t.questions.length > 0);
  });

  const top = $derived(threads.find((t) => t.key === 'problem'));

  const closing = $derived(threads.find((t) => t.key === 'closing'));

  /** 펼친 묶음이 블럭 질문이면 그 블럭만 칠한다 */
  const focus = $derived(threads.find((t) => t.key === current)?.block ?? null);

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

    // 이어서 쓸 때는 아직 빈 칸이 있는 첫 묶음부터 연다
    current =
      (threads.find((t) => t.questions.some((q) => q.answer === '')) ?? threads[0])?.key ?? '';
  });

  async function open(key: string) {
    current = key;
    await tick();

    const thread = document.getElementById(`thread-${key}`);

    thread?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    thread?.querySelector('textarea')?.focus({ preventScroll: true });
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

{#snippet thread(t: Thread)}
  {@const expanded = t.key === current}
  {@const answered = t.questions.filter((q) => q.answer.trim() !== '').length}
  {@const next = threads[threads.indexOf(t) + 1]}
  <section
    id="thread-{t.key}"
    aria-label={t.label}
    class="scroll-my-4 rounded-xl border bg-background font-sans text-sm"
  >
    <button
      type="button"
      class="flex w-full cursor-pointer items-center gap-2 px-3 py-2 text-left"
      aria-expanded={expanded}
      onclick={() => open(t.key)}
    >
      {#if expanded}<IconChevronDown class="size-4" />{:else}<IconChevronRight
          class="size-4"
        />{/if}
      <span
        class={cn(
          'rounded-md px-1.5 text-xs',
          t.block === null ? 'bg-muted' : colors[t.block].fill
        )}>{t.label}</span
      >
      <span class="text-muted-foreground">질문 {t.questions.length}개 · {answered}개 답함</span>
    </button>
    {#if expanded}
      <div class="grid gap-5 border-t p-3">
        {#each t.questions as question (question.id)}
          {@render field(question)}
        {/each}
        {#if next}
          <Button
            variant="outline"
            size="sm"
            class="justify-self-start"
            onclick={() => open(next.key)}>다음 질문</Button
          >
        {/if}
      </div>
    {/if}
  </section>
{/snippet}

{#snippet blockThreads(line: number)}
  {#each threads.filter((t) => t.line === line) as t (t.key)}
    <div class="my-2 mr-3 ml-11">{@render thread(t)}</div>
  {/each}
{/snippet}

{#if record}
  <div class="mb-6 grid gap-1">
    <h1 class="text-2xl font-semibold">{record.problem}</h1>
    <p class="text-muted-foreground">핵심 아이디어: {record.key_idea}</p>
    <a
      href={resolve(`/records/blocks?id=${id}`)}
      class="text-sm text-muted-foreground underline underline-offset-4">블럭 다시 나누기</a
    >
  </div>

  <div class="grid max-w-4xl gap-4">
    {#if top}
      {@render thread(top)}
    {/if}

    <CodeView
      code={record.code}
      units={record.units}
      blocks={record.blocks}
      {focus}
      after={blockThreads}
    />

    {#if closing}
      {@render thread(closing)}
    {/if}

    <div class="mt-4 flex items-center gap-4">
      <Button onclick={finish}>다 썼어요</Button>
      <span class="text-sm text-muted-foreground">{status}</span>
    </div>
  </div>
{:else if error}
  <p class="text-destructive">{error}</p>
{:else}
  <p class="text-muted-foreground">불러오는 중...</p>
{/if}

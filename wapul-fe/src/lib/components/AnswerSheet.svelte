<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { SvelteMap } from 'svelte/reactivity';
  import { IconChevronDown, IconChevronRight } from '@tabler/icons-svelte';
  import { resolve } from '$app/paths';
  import { api, type QuestionIn, type QuestionOut, type RecordOut } from '#lib/api/client.js';
  import AnswerField from '#lib/components/AnswerField.svelte';
  import CodeView from '#lib/components/CodeView.svelte';
  import * as AlertDialog from '#lib/components/ui/alert-dialog/index.js';
  import { Button } from '#lib/components/ui/button/index.js';
  import { Checkbox } from '#lib/components/ui/checkbox/index.js';
  import { Label } from '#lib/components/ui/label/index.js';
  import { pickExample, revisionQuestion } from '#lib/questions.js';
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

  // 답하지 않고 묶음을 닫으려 할 때 띄우는 모달의 제목
  const PLEAS = [
    '대답을 안... 하고 넘어가실 거예요?',
    '정말요? 한 줄만 적어도 괜찮은데...',
    '이 블럭은 아직 할 말이 남은 것 같아요...'
  ];

  /** 펼친 묶음에서 답하지 않고 닫기를 누른 횟수. 두 번 누르면 닫기가 풀린다 */
  let closeTries = $state(0);

  let shaking = $state(false);

  // 흔들림 길이 (layout.css의 --animate-shake와 같다). 애니메이션이 끝나는 이벤트에 기대지 않고
  // 시간으로 풀어서, 이벤트를 놓쳐도 닫기가 막힌 채로 남지 않는다
  const SHAKE_MS = 400;

  /** 호소 모달의 제목. 빈 문자열이면 닫혀 있다 */
  let plea = $state('');

  /** 답하지 않은 칸이 있는지. 건너뛸 수 있는 달라진 점 질문은 세지 않는다 */
  function blank(t: Thread): boolean {
    return t.questions.some((q) => q.kind !== 'revision' && q.answer.trim() === '');
  }

  /** 펼친 묶음의 첫 빈 칸에 커서를 둔다 */
  function focusBlank(scroll: boolean) {
    const fields = [
      ...(document.getElementById(`thread-${current}`)?.querySelectorAll('textarea') ?? [])
    ];

    (fields.find((f) => f.value === '') ?? fields[0])?.focus({ preventScroll: !scroll });
  }

  /**
   * 묶음을 펼치고 첫 빈 칸에 커서를 둔다. 다음 질문으로 넘어갈 때(jump)는 펼친 묶음을 화면 위쪽으로
   * 올려 그 위에 블럭 코드가 보이게 하고, 묶음 머리를 눌렀을 때는 화면 밖으로 밀린 만큼만 움직인다
   */
  async function open(key: string, jump: boolean) {
    if (key !== current) {
      closeTries = 0;
      shaking = false;
      markError = '';
    }

    current = key;
    await tick();

    document
      .getElementById(`thread-${key}`)
      ?.scrollIntoView({ block: jump ? 'start' : 'nearest', behavior: 'smooth' });
    focusBlank(false);
  }

  /**
   * 펼친 묶음을 닫는다. 묶음 머리로는 닫히지 않아서, 생각 없이 열고 닫는 대신 답하게 한다. 빈 칸이
   * 있으면 처음 누를 때 묶음을 흔들고 빈 칸을 강조하며 모달로 묻고, 한 번 더 누르면 흔든 뒤에야
   * 닫기가 풀린다
   */
  function close(t: Thread) {
    if (!blank(t) || (closeTries >= 2 && !shaking)) {
      current = '';
      closeTries = 0;

      return;
    }

    // 닫기가 풀리기 전(마지막 흔들림 중)에 누른 것은 세지 않는다
    if (closeTries >= 2) return;

    closeTries += 1;

    if (closeTries === 1) plea = PLEAS[Math.floor(Math.random() * PLEAS.length)];

    shake();
  }

  let shakeTimer: ReturnType<typeof setTimeout> | undefined;

  /** 펼친 묶음을 흔든다. 흔드는 중에 또 흔들면 처음부터 다시 흔든다 */
  async function shake() {
    // 동작 줄이기를 켠 사용자에게는 흔들지 않고 바로 다음 단계로 간다
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    clearTimeout(shakeTimer);
    shaking = false;
    await tick();
    shaking = true;
    shakeTimer = setTimeout(() => (shaking = false), SHAKE_MS);
  }

  /** 처음 제출에서 틀렸다는 표시를 바꾸는 중. 그동안 다시 누르지 못한다 */
  let marking = $state(false);

  /** 표시를 바꾸지 못한 이유. 펼친 묶음의 체크 바로 아래에 보인다 */
  let markError = $state('');

  /**
   * 블럭에 처음 제출에서 틀렸다는 표시를 켜거나 끈다. 표시는 그 블럭의 달라진 점 질문이라, 질문을
   * 넣거나 빼고 블럭과 질문을 통째로 다시 저장한다. 아직 저장하지 않은 답도 함께 보낸다
   */
  async function markWrong(block: number, wrong: boolean) {
    if (!record) return;

    const { blocks, questions } = record;

    const revision = questions.find(
      (q) => q.kind === 'revision' && q.block_id === blocks[block].id
    );

    if (!wrong && revision?.answer.trim() && !confirm('쓴 답이 지워져요. 표시를 끌까요?')) return;

    const position = new Map(blocks.map((b, i) => [b.id, i]));

    // 질문과 그 질문의 예제 답을 같이 들고 가서, 새 id에 예제를 그대로 옮긴다
    const next = questions.flatMap((q): { question: QuestionIn; example: string }[] =>
      q === revision
        ? []
        : [
            {
              question: {
                kind: q.kind,
                text: q.text,
                answer: q.answer,
                block: q.block_id === null ? null : (position.get(q.block_id) ?? null)
              },
              example: examples[q.id] ?? ''
            }
          ]
    );

    // 달라진 점 질문은 그 블럭 질문의 맨 뒤에 붙는다
    if (wrong) {
      const after = next.findLastIndex((n) => n.question.block === block);

      next.splice(after + 1, 0, {
        question: revisionQuestion(block),
        example: pickExample('revision')
      });
    }

    marking = true;

    const result = await api.updateBlocks(
      id,
      blocks.map(({ kind, units }) => ({ kind, units })),
      next.map((n) => n.question)
    );

    marking = false;

    if (!result.ok) {
      markError = `표시를 바꾸지 못했어요. ${result.message}`;

      return;
    }

    markError = '';

    // 블럭과 질문을 다시 만들어 id가 모두 바뀐다. 펼친 묶음, 저장한 답, 예제를 새 id로 옮긴다
    const opened = blocks.findIndex((b) => b.id === current);

    record = result.data;
    examples = Object.fromEntries(
      result.data.questions.map((q, i) => [q.id, next[i]?.example ?? pickExample(q.kind)])
    );
    saved.clear();

    for (const q of result.data.questions) saved.set(q.id, q.answer);

    if (opened !== -1) current = result.data.blocks[opened].id;

    status = '저장했어요.';
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
    invalid={closeTries > 0 && question.kind !== 'revision' && question.answer.trim() === ''}
    bind:value={question.answer}
    oncommit={() => commit(question)}
  />
{/snippet}

{#snippet thread(t: Thread)}
  {@const expanded = t.key === current}
  {@const answered = t.questions.filter((q) => q.answer.trim() !== '').length}
  {@const next = threads[threads.indexOf(t) + 1]}
  {@const closable = !blank(t) || (closeTries >= 2 && !shaking)}
  <section
    id="thread-{t.key}"
    aria-label={t.label}
    class={cn(
      'scroll-mt-[25vh] scroll-mb-4 rounded-xl border bg-background font-sans text-sm',
      expanded && closeTries > 0 && blank(t) && 'ring-2 ring-destructive',
      expanded && shaking && 'animate-shake'
    )}
  >
    <button
      type="button"
      class="flex w-full cursor-pointer items-center gap-2 px-3 py-2 text-left"
      aria-expanded={expanded}
      onclick={() => open(t.key, false)}
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
        {#if t.block !== null}
          {@const block = t.block}
          <Label class="font-normal">
            <!-- 체크는 저장된 상태(달라진 점 질문이 있는지)만 따른다. 저장에 실패하면 그대로 남는다 -->
            <Checkbox
              bind:checked={
                () => t.questions.some((q) => q.kind === 'revision'), (on) => markWrong(block, on)
              }
              disabled={marking}
            />
            이 부분은 처음 제출에서 틀렸어요
          </Label>
          {#if markError}
            <p class="text-xs text-destructive">{markError}</p>
          {/if}
        {/if}
        <div class="flex flex-wrap gap-2">
          {#if next}
            <Button variant="outline" size="sm" onclick={() => open(next.key, true)}
              >다음 질문</Button
            >
          {/if}
          <!-- 막힌 것처럼 보이지만 눌러야 다음 단계로 가므로 disabled가 아니라 aria-disabled다 -->
          <Button
            variant="ghost"
            size="sm"
            aria-disabled={!closable}
            class={cn(!closable && 'opacity-50')}
            onclick={() => close(t)}>닫기</Button
          >
        </div>
      </div>
    {/if}
  </section>
{/snippet}

{#snippet blockThreads(line: number)}
  {#each threads.filter((t) => t.line === line) as t (t.key)}
    <div class="my-2 mr-3 ml-11">{@render thread(t)}</div>
  {/each}
{/snippet}

<AlertDialog.Root
  open={plea !== ''}
  onOpenChange={(open) => {
    if (!open) plea = '';
  }}
>
  <AlertDialog.Content
    onCloseAutoFocus={(event) => {
      event.preventDefault();
      focusBlank(true);
    }}
  >
    <AlertDialog.Header>
      <AlertDialog.Title>{plea}</AlertDialog.Title>
      <AlertDialog.Description>
        한 줄이라도 적어 두면 나중에 다시 볼 때 큰 도움이 돼요.
      </AlertDialog.Description>
    </AlertDialog.Header>
    <AlertDialog.Footer>
      <AlertDialog.Action onclick={() => (plea = '')}>답하러 가기</AlertDialog.Action>
    </AlertDialog.Footer>
  </AlertDialog.Content>
</AlertDialog.Root>

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
      language={record.language}
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

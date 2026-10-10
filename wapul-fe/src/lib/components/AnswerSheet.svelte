<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { SvelteMap } from 'svelte/reactivity';
  import { IconArrowsVertical } from '@tabler/icons-svelte';
  import { resolve } from '$app/paths';
  import {
    BACKEND,
    api,
    type QuestionIn,
    type QuestionOut,
    type RecordOut
  } from '#lib/api/client.js';
  import { CloseGuard, filled, hasBlank, skippable, unanswered } from '#lib/closeGuard.svelte.js';
  import AnswerField from '#lib/components/AnswerField.svelte';
  import CodeView from '#lib/components/CodeView.svelte';
  import { lensVariants } from '#lib/components/lens/index.js';
  import * as AlertDialog from '#lib/components/ui/alert-dialog/index.js';
  import { Button } from '#lib/components/ui/button/index.js';
  import { Checkbox } from '#lib/components/ui/checkbox/index.js';
  import { Label } from '#lib/components/ui/label/index.js';
  import type { Name } from '#lib/completions.js';
  import { pickExample, revisionQuestion } from '#lib/questions.js';
  import { DRAFT_DAYS, browserStorage } from '#lib/drafts.js';
  import { codeNames } from '#lib/segment.js';
  import { blockColors, blockLabels, lastLine, unitLines } from '#lib/study.js';
  import {
    firstGap,
    firstOpen,
    nextThread,
    progress,
    progressName,
    questionName
  } from '#lib/threads.js';
  import { cn } from '#lib/utils.js';

  /**
   * 한 번에 펼쳐 보는 질문 묶음. 블럭 질문은 블럭이 끝나는 줄(line) 아래의 유리 막대로 접어 두고, 펼치면
   * 그 막대 아래에 단다. 기록 단위 질문은 코드 위(문제)와 코드 아래(마무리)에 같은 막대로 둔다
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
    backend = BACKEND,
    persistent = browserStorage() !== null,
    onfinish,
    onnotowner
  }: {
    id: string;
    /** 백엔드를 쓰는지. 없으면 답은 이 브라우저(drafts.ts)에 담긴다 */
    backend?: boolean;
    /** 백엔드가 없을 때 이 브라우저에 담을 수 있는지. 저장소를 못 쓰면 답은 이 탭에만 있다가 새로고침하면 사라진다 */
    persistent?: boolean;
    /** 모든 답을 저장한 뒤 */
    onfinish: () => void;
    /** 작성자가 아닌 사람이 열었을 때 (답은 작성자만 쓴다) */
    onnotowner: () => void;
  } = $props();

  /** 답을 보낸 뒤 알림. 백엔드가 없으면 서버에 저장한 것이 아니므로 어디에 담았는지 말한다 */
  const kept = $derived(
    backend
      ? '저장했어요.'
      : persistent
        ? `이 브라우저에 담아 뒀어요. ${DRAFT_DAYS}일 동안 고치지 않으면 지워져요.`
        : '이 탭에만 담아 뒀어요. 새로고침하면 사라져요.'
  );

  let record = $state<RecordOut | null>(null);

  let error = $state('');

  let status = $state('');

  /** 질문마다 다른 문제의 예제 답 (답 칸의 회색 안내문) */
  let examples = $state<{ [questionId: string]: string }>({});

  /** 펼친 질문 묶음 */
  let current = $state('');

  /** 펼친 묶음에서 답 칸을 펼친 질문의 번호. 나머지 질문은 한 줄로 접는다 */
  let step = $state(0);

  /** 화면 읽기에 따로 알릴 말: 묶음의 질문에 모두 답했을 때(커서 밖의 변화), 두 번째로 접기를 막았을 때 */
  let announcement = $state('');

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

  const currentThread = $derived(threads.find((t) => t.key === current));

  /** 펼친 묶음이 블럭 질문이면 그 블럭만 칠한다 */
  const focus = $derived(currentThread?.block ?? null);

  /** 넘기기로 갈 곳: 묶음 안의 다음 질문, 묶음 끝이면 넘어갈 묶음. 갈 곳이 없으면 null */
  const destination = $derived.by((): { step: number } | { thread: Thread } | null => {
    const t = currentThread;

    if (t === undefined) return null;

    if (step < t.questions.length - 1) return { step: step + 1 };

    const next = nextThread(threads, t.key);

    return next === undefined ? null : { thread: next };
  });

  /** 넘기기 단추의 이름: 갈 곳을 부른다 */
  const target = $derived(
    destination === null
      ? null
      : 'step' in destination
        ? '다음 질문'
        : `${destination.thread.label} 질문으로`
  );

  /** 넘기기 단축키 안내에 쓰는 조합 키 */
  const MOD = /Mac|iPhone|iPad/.test(navigator.userAgent) ? '⌘' : 'Ctrl';

  /** 답 칸 자동완성 후보: 코드 속 이름. 기록을 불러온 뒤 받아 온다 */
  let words = $state<Name[]>([]);

  /** 블럭 id마다 그 블럭 문장이 걸친 줄. 그 블럭을 묻는 질문에서는 그 줄의 이름을 먼저 보여준다 */
  const blockLines = $derived.by(() => {
    const r = record;

    return new Map(r?.blocks.map((b) => [b.id, unitLines(r.units, b.units)]) ?? []);
  });

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
    // 자동완성 후보는 화면을 띄운 뒤 받아 온다. 문법을 못 받으면 자동완성 없이 쓴다
    void codeNames(result.data.code, result.data.language).then(
      (found) => (words = found),
      () => (words = [])
    );
    examples = Object.fromEntries(result.data.questions.map((q) => [q.id, pickExample(q.kind)]));

    for (const q of result.data.questions) saved.set(q.id, q.answer);

    // 이어서 쓸 때는 아직 빈 칸이 있는 첫 묶음의 첫 빈 질문부터 연다
    const first = firstOpen(threads);

    current = first?.key ?? '';
    step = firstGap(first?.questions ?? []);
  });

  const guard = new CloseGuard();

  /** 화면을 굴리는 방식. 동작 줄이기를 켰으면 바로 옮긴다 */
  const glide = (): ScrollBehavior =>
    matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth';

  /** 펼친 묶음에서 답하는 칸에 커서를 둔다. scroll이면 그 칸이 보이게 굴린다 */
  function focusActive(scroll: boolean) {
    const question = currentThread?.questions[step];

    const field = question === undefined ? null : document.getElementById(question.id);

    field?.focus({ preventScroll: true });

    if (scroll) field?.closest('li')?.scrollIntoView({ block: 'nearest', behavior: glide() });
  }

  /** 묶음 안의 i번째 질문의 답 칸을 펼친다 */
  async function goTo(i: number) {
    step = i;
    await tick();
    focusActive(true);
  }

  /**
   * 묶음을 펼치고 첫 빈 질문의 답 칸에 커서를 둔다. 다음 묶음으로 넘어갈 때(jump)는 펼친 묶음을 화면
   * 위쪽으로 올려 그 위에 블럭 코드가 보이게 하고, 막대를 눌렀을 때는 화면 밖으로 밀린 만큼만 움직인다
   */
  async function open(key: string, jump: boolean) {
    if (key !== current) {
      guard.reset();
      markError = '';
      current = key;
      step = firstGap(currentThread?.questions ?? []);
    }

    await tick();

    document
      .getElementById(`thread-${key}`)
      ?.scrollIntoView({ block: jump ? 'start' : 'nearest', behavior: glide() });
    focusActive(false);
  }

  function advance() {
    const to = destination;

    if (to === null) return;

    if ('step' in to) void goTo(to.step);
    else void open(to.thread.key, true);
  }

  /** 코드에서 누른 블럭의 질문 묶음을 펼치고 그리로 옮긴다 */
  function pickBlock(block: number) {
    const found = threads.find((t) => t.block === block);

    if (found) open(found.key, true);
  }

  /** 화면 읽기에 알린다. 같은 말이 다시 와도 읽히게 한 번 비운 뒤 넣는다 */
  async function announce(message: string) {
    announcement = '';
    await tick();
    announcement = message;
  }

  /** 펼친 묶음을 접는다. 빈 칸이 있으면 바로 접히지 않아서, 생각 없이 열고 닫는 대신 답하게 한다 */
  async function close(t: Thread) {
    if (!guard.close(hasBlank(t.questions))) {
      // 처음에는 모달이 뜨지만 두 번째부터는 흔들기만 한다. 흔들림을 못 보는 사람에게는 말로 알린다
      if (guard.tries >= 2) void announce('빈 칸이 남았어요. 한 번 더 누르면 접혀요.');

      return;
    }

    current = '';
    await tick();
    document.getElementById(`rule-${t.key}`)?.focus();
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

    if (result.ok) {
      markError = '';

      // 블럭과 질문을 다시 만들어 id가 모두 바뀐다. 펼친 묶음, 저장한 답, 예제를 새 id로 옮긴다.
      // 펼친 질문은 번호로 기억해서 쓰던 질문이 그대로 남는다
      const opened = blocks.findIndex((b) => b.id === current);

      record = result.data;
      examples = Object.fromEntries(
        result.data.questions.map((q, i) => [q.id, next[i]?.example ?? pickExample(q.kind)])
      );
      saved.clear();

      for (const q of result.data.questions) saved.set(q.id, q.answer);

      if (opened !== -1) current = result.data.blocks[opened].id;

      step = Math.min(step, (currentThread?.questions.length ?? 1) - 1);
      status = kept;
    } else {
      markError = `표시를 바꾸지 못했어요. ${result.message}`;
    }

    // 저장하는 동안 체크가 disabled라 커서가 body로 빠진다. 다른 곳으로 옮기지 않았으면 체크로 돌려준다
    await tick();

    if (document.activeElement === document.body)
      document.getElementById(`wrong-${current}`)?.focus();
  }

  /** 질문마다 저장을 차례로 보낸다. 멈췄을 때와 칸을 벗어날 때의 저장이 겹쳐도 나중 값이 남는다 */
  const sending = new SvelteMap<string, Promise<boolean>>();

  function commit(question: QuestionOut): Promise<boolean> {
    const next = (sending.get(question.id) ?? Promise.resolve(true)).then(() => send(question));

    sending.set(question.id, next);

    return next;
  }

  /** 저장한 답으로 잰 묶음의 빈 칸. 칸의 답은 칠 때마다 바뀌어서 저장한 것만 센다 */
  const savedBlank = (t: Thread) =>
    hasBlank(t.questions.map((q) => ({ kind: q.kind, answer: saved.get(q.id) ?? '' })));

  async function send(question: QuestionOut): Promise<boolean> {
    // 보낸 값만 저장한 것으로 친다. 보내는 동안 더 친 글자는 다음 저장이 보낸다
    const answer = question.answer;

    if (saved.get(question.id) === answer) return true;

    const t = threads.find((x) => x.questions.some((q) => q.id === question.id));

    const before = t !== undefined && savedBlank(t);

    const result = await api.saveAnswer(id, question.id, answer);

    if (!result.ok) {
      status = result.message;

      return false;
    }

    saved.set(question.id, answer);
    status = kept;

    if (t !== undefined && before && !savedBlank(t))
      void announce(`${t.label} 질문 ${progress(t.questions).total}개에 모두 답했어요.`);

    return true;
  }

  async function finish() {
    for (const q of record?.questions ?? []) {
      if (!(await commit(q))) return;
    }

    onfinish();
  }
</script>

{#snippet field(question: QuestionOut, onnext?: () => void)}
  <AnswerField
    id={question.id}
    question={question.text}
    example={examples[question.id] ?? ''}
    note={skippable(question) ? '건너뛸 수 있어요.' : undefined}
    invalid={guard.tries > 0 && unanswered(question)}
    bind:value={question.answer}
    {words}
    near={question.block_id === null ? undefined : blockLines.get(question.block_id)}
    oncommit={() => commit(question)}
    {onnext}
  />
{/snippet}

<!-- 묶음 막대: 돋보기 창과 같은 유리에 필수 질문마다 한 마디를 두고, 답한 마디를 블럭 색으로 비춘다.
     누르면 펼치고, 펼친 막대를 누르면 접는다(빈 칸이 있으면 바로 접히지 않는다) -->
{#snippet rule(t: Thread)}
  {@const expanded = t.key === current}
  {@const name = progressName(t.label, progress(t.questions))}
  <h2 class={cn('flex', t.block !== null && 'pr-3 pl-11')}>
    <button
      type="button"
      id="rule-{t.key}"
      aria-expanded={expanded}
      aria-controls={expanded ? `thread-${t.key}` : undefined}
      aria-label={name}
      title={name}
      class="flex h-5 w-full cursor-pointer items-center gap-2 rounded-full font-sans text-foreground/55 outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-foreground/50"
      style={t.block === null ? '--block: var(--foreground)' : colors[t.block].style}
      onclick={() => (expanded ? close(t) : open(t.key, false))}
    >
      {#if t.block === null}
        <span class="text-[13px] text-foreground/75">{t.label}</span>
      {/if}
      <span
        aria-hidden="true"
        class={cn(
          lensVariants({ size: 'bar', tint: expanded ? 'block' : 'clear' }),
          'flex h-2 flex-1 gap-0.5'
        )}
      >
        {#each t.questions.filter((q) => !skippable(q)) as q (q.id)}
          <span class={cn('flex-1', filled(q) ? 'bg-(--block)/65' : 'bg-(--block)/15')}></span>
        {/each}
      </span>
      <IconArrowsVertical class="size-3.5 shrink-0" aria-hidden="true" />
    </button>
  </h2>
{/snippet}

<!-- 펼친 묶음: 답하는 질문 하나만 답 칸을 펼친 카드로, 나머지는 한 줄로 둔다 -->
{#snippet panel(t: Thread)}
  {@const blank = hasBlank(t.questions)}
  <section
    id="thread-{t.key}"
    aria-label={t.label}
    class={cn(
      'scroll-mt-[25vh] scroll-mb-4 bg-background font-sans text-sm leading-normal',
      t.block === null
        ? 'rounded-xl border p-3'
        : 'relative border-b py-3 pr-3 pl-11 before:absolute before:inset-y-0 before:left-0 before:w-1 before:bg-(--block)',
      guard.tries > 0 && blank && 'ring-2 ring-destructive ring-inset'
    )}
    style={t.block === null ? undefined : colors[t.block].style}
  >
    <div class={cn('grid gap-3', guard.shaking && 'animate-shake')}>
      <ol role="list" class="grid gap-1">
        {#each t.questions as question, i (question.id)}
          {#if i === step}
            <li aria-current="step" class="my-2 grid gap-3 rounded-xl border bg-card p-3 shadow-sm">
              {@render field(question, target === null ? undefined : advance)}
              <div class="flex flex-wrap items-center gap-2">
                {#if target === null}
                  <p class="text-xs text-foreground/70">다 쓰면 아래 '다 썼어요'를 눌러요.</p>
                {:else}
                  <Button
                    variant="outline"
                    size="sm"
                    aria-keyshortcuts="Control+Enter Meta+Enter"
                    onclick={advance}>{target}</Button
                  >
                  <span class="text-xs text-foreground/70 pointer-coarse:hidden" aria-hidden="true"
                    >{MOD}+Enter</span
                  >
                {/if}
              </div>
            </li>
          {:else}
            <li>
              <button
                type="button"
                aria-label={questionName(question)}
                class="flex w-full min-w-0 cursor-pointer items-start gap-2 rounded-md px-2 py-1 text-left outline-none hover:bg-foreground/5 focus-visible:ring-2 focus-visible:ring-foreground/50"
                onclick={() => goTo(i)}
              >
                <span
                  aria-hidden="true"
                  class={cn(
                    'mt-1.5 size-2 shrink-0 rounded-full border',
                    filled(question)
                      ? 'border-transparent bg-foreground/70'
                      : guard.tries > 0 && unanswered(question)
                        ? 'border-destructive'
                        : 'border-foreground/60',
                    skippable(question) && !filled(question) && 'border-dashed'
                  )}
                ></span>
                {#if filled(question)}
                  <span class="max-w-1/2 shrink-0 truncate text-foreground/75">{question.text}</span
                  >
                  <span class="min-w-0 flex-1 truncate" data-clarity-mask="true"
                    >{question.answer}</span
                  >
                {:else}
                  <span class="text-foreground/75">{question.text}</span>
                {/if}
                {#if skippable(question)}
                  <span class="ml-auto shrink-0 text-xs text-foreground/75">선택</span>
                {/if}
              </button>
            </li>
          {/if}
        {/each}
      </ol>
      {#if t.block !== null}
        {@const block = t.block}
        <div class="flex flex-wrap items-center gap-x-4 gap-y-2 border-t pt-3">
          <Label class="font-normal">
            <!-- 체크는 저장된 상태(달라진 점 질문이 있는지)만 따른다. 저장에 실패하면 그대로 남는다 -->
            <Checkbox
              id="wrong-{t.key}"
              bind:checked={
                () => t.questions.some((q) => q.kind === 'revision'), (on) => markWrong(block, on)
              }
              disabled={marking}
            />
            이 부분은 처음 제출에서 틀렸어요
          </Label>
          {#if markError}
            <p class="w-full text-xs text-destructive">{markError}</p>
          {/if}
        </div>
      {/if}
    </div>
  </section>
{/snippet}

<!-- 블럭 묶음은 블럭이 끝나는 줄 아래에 단다. 블럭 번호로 묶어서 틀렸다 표시로 id가 바뀌어도 패널이 남는다 -->
{#snippet blockThreads(line: number)}
  {#each threads.filter((t) => t.line === line) as t (t.block)}
    {@render rule(t)}
    {#if t.key === current}
      {@render panel(t)}
    {/if}
  {/each}
{/snippet}

{#snippet standalone(t: Thread)}
  <div class="grid gap-2">
    {@render rule(t)}
    {#if t.key === current}
      {@render panel(t)}
    {/if}
  </div>
{/snippet}

<AlertDialog.Root
  open={guard.plea !== ''}
  onOpenChange={(open) => {
    if (!open) guard.plea = '';
  }}
>
  <AlertDialog.Content
    onCloseAutoFocus={(event) => {
      event.preventDefault();
      void goTo(firstGap(currentThread?.questions ?? []));
    }}
  >
    <AlertDialog.Header>
      <AlertDialog.Title>{guard.plea}</AlertDialog.Title>
      <AlertDialog.Description>
        한 줄이라도 적어 두면 나중에 다시 볼 때 큰 도움이 돼요.
      </AlertDialog.Description>
    </AlertDialog.Header>
    <AlertDialog.Footer>
      <AlertDialog.Action onclick={() => (guard.plea = '')}>답하러 가기</AlertDialog.Action>
    </AlertDialog.Footer>
  </AlertDialog.Content>
</AlertDialog.Root>

{#if record}
  <div class="mb-6 grid gap-1">
    <h1 class="text-2xl font-semibold" data-clarity-mask="true">{record.problem}</h1>
    <p class="text-muted-foreground">
      핵심 아이디어: <span data-clarity-mask="true">{record.key_idea}</span>
    </p>
    <a
      href={resolve(`/records/blocks?id=${id}`)}
      class="text-sm text-muted-foreground underline underline-offset-4">블럭 다시 나누기</a
    >
  </div>

  <div class="grid max-w-4xl gap-4">
    {#if top}
      {@render standalone(top)}
    {/if}

    <CodeView
      code={record.code}
      language={record.language}
      units={record.units}
      blocks={record.blocks}
      {focus}
      onpick={pickBlock}
      after={blockThreads}
    />

    {#if closing}
      {@render standalone(closing)}
    {/if}

    <div class="mt-4 flex items-center gap-4">
      <Button onclick={finish}>다 썼어요</Button>
      <span class="text-sm text-muted-foreground">{status}</span>
    </div>
    <p class="sr-only" role="status">{announcement}</p>
  </div>
{:else if error}
  <p class="text-destructive">{error}</p>
{:else}
  <p class="text-muted-foreground">불러오는 중...</p>
{/if}

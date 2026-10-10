<script lang="ts">
  import { api, type Language, type RecordDraft } from '#lib/api/client.js';
  import BlockEditor from '#lib/components/BlockEditor.svelte';
  import * as AlertDialog from '#lib/components/ui/alert-dialog/index.js';
  import { Button } from '#lib/components/ui/button/index.js';
  import { Input } from '#lib/components/ui/input/index.js';
  import { Label } from '#lib/components/ui/label/index.js';
  import * as NativeSelect from '#lib/components/ui/native-select/index.js';
  import { Textarea } from '#lib/components/ui/textarea/index.js';
  import { DRAFT_DAYS, browserStorage, clearForm, loadForm, saveForm } from '#lib/drafts.js';
  import { blockFacts, buildQuestions } from '#lib/questions.js';
  import { segmentCode } from '#lib/segment.js';
  import { LANGUAGE_LABEL } from '#lib/study.js';

  let {
    oncreated,
    onsaved
  }: {
    /** 모델이 나눈 블럭으로 기록을 만든 뒤. 블럭을 확인하러 간다 */
    oncreated: (id: string) => void;
    /** 모델이 못 나눠 블럭을 직접 만들고 기록을 만든 뒤. 바로 답을 쓰러 간다 */
    onsaved: (id: string) => void;
  } = $props();

  const storage = browserStorage();

  /** 이 브라우저에 담아 둔, 쓰던 칸 */
  const resumed = loadForm(storage);

  let problem = $state(resumed?.problem ?? '');

  let keyIdea = $state(resumed?.keyIdea ?? '');

  let code = $state(resumed?.code ?? '');

  let language = $state<Language>(resumed?.language ?? 'cpp');

  /** 쓰던 칸을 불러왔다는 안내. 새로 쓰면 닫는다 */
  let restored = $state(resumed !== null);

  // 쓰는 대로 이 브라우저에 담는다. 기록을 만들면 지운다. 처음 한 번은 불러온 그대로라 담지 않는다:
  // 열기만 해서는 DRAFT_DAYS가 다시 시작되지 않게
  let opened = false;

  $effect(() => {
    const draft = { problem, keyIdea, code, language };

    if (opened) saveForm(storage, draft);

    opened = true;
  });

  function startOver() {
    problem = '';
    keyIdea = '';
    code = '';
    language = 'cpp';
    restored = false;
  }

  let error = $state('');

  let submitting = $state(false);

  /** 모델이 블럭을 못 찾은 코드. 모달에서 직접 나누기를 고르면 draft가 된다 */
  let unsplit = $state<RecordDraft | null>(null);

  let unsplitTitle = $state('');

  /** 블럭을 직접 나누는 중인 새 기록 (아직 저장하지 않음) */
  let draft = $state<RecordDraft | null>(null);

  // 핵심 아이디어를 코드보다 먼저 쓰게 한다
  const ideaWritten = $derived(keyIdea.trim() !== '');

  const ready = $derived(problem.trim() !== '' && ideaWritten && code.trim() !== '');

  // SAFETY: LANGUAGE_LABEL은 satisfies로 Language의 모든 값을, 그 값만 키로 가진다
  const languages = Object.keys(LANGUAGE_LABEL) as Language[];

  // 모델이 모든 문장을 어느 블럭에도 넣지 않았을 때 (아주 짧은 코드 등)
  const UNSPLITTABLE = [
    '너무 고귀한 풀이라 나누지 못했어요!',
    '너무 아름다워서 제가 감히 나눌 수 없었어요!',
    '코드가 너무 눈부셔서 제가 나눌 수 없어요!'
  ];

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    submitting = true;
    error = '';

    // 블럭은 브라우저에서 나눈다. 처음 한 번은 모델과 문법 파일을 받느라 몇 초 걸린다
    let segmented;

    try {
      segmented = await segmentCode(code, language);
    } catch {
      submitting = false;
      error = '코드를 블럭으로 나누지 못했어요. 언어를 확인하고 다시 시도해 주세요.';

      return;
    }

    const record = {
      problem: problem.trim(),
      key_idea: keyIdea.trim(),
      language,
      // 처음 제출에서 틀렸는지는 블럭마다 표시한다(그 블럭의 달라진 점 질문). 기록 단위 값은 쓰지 않는다
      initially_wrong: false,
      code: segmented.code,
      units: segmented.units
    };

    // 기록은 블럭이 하나 이상 있어야 만들 수 있다. 블럭을 직접 만들 때까지 저장하지 않는다
    if (segmented.blocks.length === 0) {
      submitting = false;
      unsplitTitle = UNSPLITTABLE[Math.floor(Math.random() * UNSPLITTABLE.length)];
      unsplit = record;

      return;
    }

    const result = await api.createRecord({
      ...record,
      blocks: segmented.blocks,
      questions: buildQuestions(blockFacts(segmented.units, segmented.blocks))
    });

    submitting = false;

    if (!result.ok) {
      error = result.message;

      return;
    }

    clearForm(storage);
    oncreated(result.data.id);
  }
</script>

<AlertDialog.Root
  open={unsplit !== null}
  onOpenChange={(open) => {
    if (!open) unsplit = null;
  }}
>
  <AlertDialog.Content>
    <AlertDialog.Header>
      <AlertDialog.Title>{unsplitTitle}</AlertDialog.Title>
      <AlertDialog.Description>
        블럭을 하나도 찾지 못했어요. 코드를 끌어서 블럭을 직접 만들 수 있어요.
      </AlertDialog.Description>
    </AlertDialog.Header>
    <AlertDialog.Footer>
      <AlertDialog.Cancel>코드 고치기</AlertDialog.Cancel>
      <AlertDialog.Action
        onclick={() => {
          draft = unsplit;
          unsplit = null;
        }}>직접 나누기</AlertDialog.Action
      >
    </AlertDialog.Footer>
  </AlertDialog.Content>
</AlertDialog.Root>

{#if draft}
  <BlockEditor
    {draft}
    onsaved={(id) => {
      clearForm(storage);
      onsaved(id);
    }}
  />
{:else}
  <h1 class="mb-6 text-2xl font-semibold">새 기록</h1>

  {#if restored}
    <p class="-mt-3 mb-6 flex flex-wrap items-center gap-x-2 text-sm text-muted-foreground">
      쓰던 내용을 불러왔어요. 마지막으로 고친 뒤 {DRAFT_DAYS}일 동안 이 브라우저에 남아요.
      <Button variant="link" size="sm" class="h-auto p-0" onclick={startOver}>새로 쓰기</Button>
    </p>
  {/if}

  <form class="grid max-w-3xl gap-6" onsubmit={submit}>
    <div class="grid gap-2">
      <Label for="problem">1. 어떤 문제인가요?</Label>
      <Input
        id="problem"
        bind:value={problem}
        maxlength={__LIMITS__.problem}
        placeholder="문제 제목이나 링크"
      />
    </div>

    <div class="grid gap-2">
      <Label for="key-idea"
        >2. 코드를 붙여넣기 전에, 풀이의 핵심 아이디어를 한 줄로 적어 주세요</Label
      >
      <Input id="key-idea" bind:value={keyIdea} maxlength={__LIMITS__.keyIdea} />
    </div>

    {#if ideaWritten}
      <div class="grid gap-2">
        <Label for="code">3. 맞은 풀이 코드를 붙여넣어 주세요</Label>
        <div class="flex items-center gap-4">
          <NativeSelect.Root size="sm" bind:value={language} aria-label="언어">
            {#each languages as lang (lang)}
              <NativeSelect.Option value={lang}>{LANGUAGE_LABEL[lang]}</NativeSelect.Option>
            {/each}
          </NativeSelect.Root>
        </div>
        <Textarea
          id="code"
          bind:value={code}
          maxlength={__LIMITS__.code}
          rows={16}
          class="font-mono"
          spellcheck={false}
        />
      </div>
    {/if}

    {#if error}
      <p class="text-destructive">{error}</p>
    {/if}

    <Button type="submit" class="justify-self-start" disabled={!ready || submitting}>
      {submitting ? '블럭 나누는 중...' : '블럭 나누기'}
    </Button>
  </form>
{/if}

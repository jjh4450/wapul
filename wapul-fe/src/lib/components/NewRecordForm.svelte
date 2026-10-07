<script lang="ts">
  import { api, type Language } from '#lib/api/client.js';
  import { Button } from '#lib/components/ui/button/index.js';
  import { Checkbox } from '#lib/components/ui/checkbox/index.js';
  import { Input } from '#lib/components/ui/input/index.js';
  import { Label } from '#lib/components/ui/label/index.js';
  import * as NativeSelect from '#lib/components/ui/native-select/index.js';
  import { Textarea } from '#lib/components/ui/textarea/index.js';
  import { blockFacts, buildQuestions } from '#lib/questions.js';
  import { segmentCode } from '#lib/segment.js';
  import { LANGUAGE_LABEL } from '#lib/study.js';

  let { oncreated }: { oncreated: (id: string) => void } = $props();

  let problem = $state('');

  let keyIdea = $state('');

  let code = $state('');

  let language = $state<Language>('cpp');

  let initiallyWrong = $state(false);

  let error = $state('');

  let submitting = $state(false);

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

    if (segmented.blocks.length === 0) {
      submitting = false;
      error = UNSPLITTABLE[Math.floor(Math.random() * UNSPLITTABLE.length)];

      return;
    }

    const result = await api.createRecord({
      problem: problem.trim(),
      key_idea: keyIdea.trim(),
      language,
      initially_wrong: initiallyWrong,
      ...segmented,
      questions: buildQuestions(blockFacts(segmented.units, segmented.blocks), initiallyWrong)
    });

    submitting = false;

    if (result.ok) oncreated(result.data.id);
    else error = result.message;
  }
</script>

<h1 class="mb-6 text-2xl font-semibold">새 기록</h1>

<form class="grid max-w-3xl gap-6" onsubmit={submit}>
  <div class="grid gap-2">
    <Label for="problem">1. 어떤 문제인가요?</Label>
    <Input id="problem" bind:value={problem} placeholder="문제 제목이나 링크" />
  </div>

  <div class="grid gap-2">
    <Label for="key-idea">2. 코드를 붙여넣기 전에, 풀이의 핵심 아이디어를 한 줄로 적어 주세요</Label
    >
    <Input id="key-idea" bind:value={keyIdea} />
  </div>

  {#if ideaWritten}
    <div class="grid gap-2">
      <Label for="code">3. 맞은 풀이 코드를 붙여넣어 주세요</Label>
      <p class="text-xs text-muted-foreground">틀렸던 제출 코드는 받지 않아요.</p>
      <div class="flex items-center gap-4">
        <NativeSelect.Root size="sm" bind:value={language} aria-label="언어">
          {#each languages as lang (lang)}
            <NativeSelect.Option value={lang}>{LANGUAGE_LABEL[lang]}</NativeSelect.Option>
          {/each}
        </NativeSelect.Root>
        <Label class="font-normal">
          <Checkbox bind:checked={initiallyWrong} />
          처음 제출은 틀렸어요
        </Label>
      </div>
      <Textarea id="code" bind:value={code} rows={16} class="font-mono" spellcheck={false} />
    </div>
  {/if}

  {#if error}
    <p class="text-destructive">{error}</p>
  {/if}

  <Button type="submit" class="justify-self-start" disabled={!ready || submitting}>
    {submitting ? '블럭 나누는 중...' : '블럭 나누기'}
  </Button>
</form>

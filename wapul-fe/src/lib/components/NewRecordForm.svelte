<script lang="ts">
  import { api, type Language } from '#lib/api/client.js';
  import { Button } from '#lib/components/ui/button/index.js';
  import { Checkbox } from '#lib/components/ui/checkbox/index.js';
  import { Input } from '#lib/components/ui/input/index.js';
  import { Label } from '#lib/components/ui/label/index.js';
  import * as NativeSelect from '#lib/components/ui/native-select/index.js';
  import { Textarea } from '#lib/components/ui/textarea/index.js';
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

  const languages: Language[] = ['cpp', 'python', 'java'];

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    submitting = true;

    const result = await api.createRecord({
      problem: problem.trim(),
      key_idea: keyIdea.trim(),
      code,
      language,
      initially_wrong: initiallyWrong
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
    블럭 나누기
  </Button>
</form>

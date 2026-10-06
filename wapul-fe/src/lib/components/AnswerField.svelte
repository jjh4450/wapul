<script lang="ts">
  import { Button } from '#lib/components/ui/button/index.js';
  import { Label } from '#lib/components/ui/label/index.js';
  import { Textarea } from '#lib/components/ui/textarea/index.js';
  import { truncate } from '#lib/study.js';

  let {
    id,
    question,
    examples,
    value = $bindable(''),
    note,
    oncommit
  }: {
    id: string;
    question: string;
    /** 다른 문제에 대한 예제 답. 빈 칸에 회색 안내문으로 하나씩 보여준다 */
    examples: string[];
    value?: string;
    /** 질문 아래 덧붙이는 짧은 안내 (예: 건너뛸 수 있어요) */
    note?: string;
    /** 칸을 벗어날 때 저장한다 */
    oncommit?: () => void;
  } = $props();

  let exampleIndex = $state(0);

  const placeholder = $derived(
    examples.length > 0 ? truncate(examples[exampleIndex % examples.length], 90) : ''
  );
</script>

<div class="grid gap-2">
  <Label for={id} class="leading-snug">{question}</Label>
  {#if note}
    <p class="text-xs text-muted-foreground">{note}</p>
  {/if}
  <Textarea {id} bind:value {placeholder} rows={3} onblur={() => oncommit?.()} />
  {#if examples.length > 1 && value === ''}
    <Button
      variant="ghost"
      size="xs"
      class="justify-self-start text-muted-foreground"
      onclick={() => (exampleIndex += 1)}>다른 예시</Button
    >
  {/if}
</div>

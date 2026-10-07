<script lang="ts">
  import { Label } from '#lib/components/ui/label/index.js';
  import { Textarea } from '#lib/components/ui/textarea/index.js';
  import { truncate } from '#lib/study.js';

  let {
    id,
    question,
    example,
    value = $bindable(''),
    note,
    invalid = false,
    oncommit
  }: {
    id: string;
    question: string;
    /** 다른 문제에 대한 예제 답. 빈 칸에 회색 안내문으로 보여준다 */
    example: string;
    value?: string;
    /** 질문 아래 덧붙이는 짧은 안내 (예: 건너뛸 수 있어요) */
    note?: string;
    /** 답해 달라고 강조한다 (설문의 필수 칸처럼) */
    invalid?: boolean;
    /** 칸을 벗어날 때 저장한다 */
    oncommit?: () => void;
  } = $props();

  const placeholder = $derived(truncate(example, 90));
</script>

<div class="grid gap-2">
  <Label for={id} class="leading-snug">{question}</Label>
  {#if note}
    <p class="text-xs text-muted-foreground">{note}</p>
  {/if}
  <Textarea
    {id}
    bind:value
    {placeholder}
    rows={3}
    aria-invalid={invalid || undefined}
    onblur={() => oncommit?.()}
  />
</div>

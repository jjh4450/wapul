<script lang="ts">
  import { cn } from '#lib/utils.js';

  type Mark = { start_line: number; end_line: number; name: string };

  let {
    code,
    from = 1,
    to,
    marks = [],
    class: className
  }: {
    code: string;
    /** 보여줄 첫 줄 (1부터) */
    from?: number;
    /** 보여줄 마지막 줄, 없으면 끝까지 */
    to?: number;
    /** 블럭 범위. 블럭마다 번갈아 배경을 칠하고 첫 줄에 이름을 단다 */
    marks?: Mark[];
    class?: string;
  } = $props();

  const lines = $derived(
    code
      .split('\n')
      .map((text, i) => ({ number: i + 1, text }))
      .slice(from - 1, to)
  );

  function markIndex(line: number): number {
    return marks.findIndex((m) => m.start_line <= line && line <= m.end_line);
  }
</script>

<pre
  class={cn(
    'overflow-x-auto rounded-2xl bg-muted py-3 font-mono text-sm leading-6',
    className
  )}><code
    >{#each lines as line (line.number)}{@const index = markIndex(line.number)}<span
        class={cn(
          'flex',
          index >= 0 && (index % 2 === 0 ? 'bg-primary/10' : 'bg-chart-1/20'),
          index >= 0 && marks[index].start_line === line.number && 'mt-1'
        )}
        ><span class="w-10 shrink-0 pr-3 text-right text-muted-foreground select-none"
          >{line.number}</span
        ><span class="flex-1 pr-3 whitespace-pre">{line.text}</span
        >{#if index >= 0 && marks[index].start_line === line.number}<span
            class="shrink-0 pr-3 font-sans text-xs text-muted-foreground">{marks[index].name}</span
          >{/if}</span
      >{/each}</code
  ></pre>

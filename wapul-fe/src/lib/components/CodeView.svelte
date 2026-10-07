<script lang="ts">
  import type { Span } from '#lib/api/client.js';
  import { cn } from '#lib/utils.js';

  // 떨어진 블럭도 같은 블럭으로 보이게 블럭마다 색을 하나씩 준다
  const COLORS = [
    'bg-sky-500/20',
    'bg-amber-500/25',
    'bg-emerald-500/20',
    'bg-rose-500/20',
    'bg-violet-500/20'
  ];

  type Piece = { text: string; unit: number | null };

  let {
    code,
    units = [],
    owner = [],
    labels = [],
    lines: shown,
    onpick,
    class: className
  }: {
    code: string;
    /** 문장 위치 [줄, 칸]. 칸은 글자(코드 포인트) 단위, end는 포함하지 않는다 */
    units?: Span[];
    /** 문장마다 든 블럭 번호, 없으면 null. 블럭마다 색을 칠한다 */
    owner?: (number | null)[];
    /** 블럭 이름. 블럭의 첫 문장이 있는 줄 끝에 단다 */
    labels?: string[];
    /** 보여줄 줄 번호 (오름차순), 없으면 전부. 건너뛴 줄은 ⋯로 줄인다 */
    lines?: number[];
    /** 주면 문장을 눌러 고를 수 있다 */
    onpick?: (unit: number) => void;
    class?: string;
  } = $props();

  const texts = $derived(code.replace(/\n$/, '').split('\n'));

  /** 줄마다 그 줄에 걸친 문장의 [번호, 시작 칸, 끝 칸] */
  const spans = $derived.by(() => {
    const byLine: [number, number, number][][] = [];

    units.forEach((u, i) => {
      for (let line = u.start[0]; line <= u.end[0]; line++) {
        const from = line === u.start[0] ? u.start[1] : 0;
        const to = line === u.end[0] ? u.end[1] : Infinity;
        (byLine[line] ??= []).push([i, from, to]);
      }
    });

    return byLine;
  });

  const labelAt = $derived.by(() => {
    const at: { [line: number]: string } = {};

    owner.forEach((block, i) => {
      if (block !== null && labels[block] && !owner.slice(0, i).includes(block)) {
        at[units[i].start[0]] = labels[block];
      }
    });

    return at;
  });

  const rows = $derived.by(() => {
    const numbers = shown ?? texts.map((_, i) => i + 1);

    return numbers.map((number, i) => ({ number, gap: i > 0 && numbers[i - 1] + 1 < number }));
  });

  function pieces(number: number): Piece[] {
    const chars = Array.from(texts[number - 1] ?? '');
    const out: Piece[] = [];
    let col = 0;

    for (const [unit, from, to] of spans[number] ?? []) {
      const end = Math.min(to, chars.length);

      if (from > col) out.push({ text: chars.slice(col, from).join(''), unit: null });
      out.push({ text: chars.slice(from, end).join(''), unit });
      col = end;
    }

    if (col < chars.length) out.push({ text: chars.slice(col).join(''), unit: null });

    return out;
  }

  function color(unit: number | null): string | undefined {
    const block = unit === null ? null : (owner[unit] ?? null);

    return block === null ? undefined : COLORS[block % COLORS.length];
  }
</script>

<pre
  class={cn(
    'overflow-x-auto rounded-2xl bg-muted py-3 font-mono text-sm leading-6',
    className
  )}><code
    >{#each rows as row (row.number)}{#if row.gap}<span
          class="flex text-muted-foreground select-none"
          ><span class="w-10 shrink-0 pr-3 text-right">⋯</span></span
        >{/if}<span class="flex"
        ><span class="w-10 shrink-0 pr-3 text-right text-muted-foreground select-none"
          >{row.number}</span
        ><span class="flex-1 pr-3 whitespace-pre"
          >{#each pieces(row.number) as piece, i (i)}{#if onpick && piece.unit !== null}{@const unit =
                piece.unit}<button
                type="button"
                class={cn(
                  'cursor-pointer rounded-sm whitespace-pre hover:ring-2 hover:ring-ring',
                  color(unit)
                )}
                aria-label="{row.number}줄 문장"
                onclick={() => onpick(unit)}>{piece.text}</button
              >{:else}<span class={cn('rounded-sm', color(piece.unit))}>{piece.text}</span
              >{/if}{/each}</span
        >{#if labelAt[row.number]}<span
            class="shrink-0 pr-3 font-sans text-xs text-muted-foreground"
            >{labelAt[row.number]}</span
          >{/if}</span
      >{/each}</code
  ></pre>

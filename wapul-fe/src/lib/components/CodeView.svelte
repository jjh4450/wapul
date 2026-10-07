<script lang="ts">
  import type { Snippet } from 'svelte';
  import { IconChevronDown, IconX } from '@tabler/icons-svelte';
  import type { BlockKind, Language, Span } from '#lib/api/client.js';
  import * as DropdownMenu from '#lib/components/ui/dropdown-menu/index.js';
  import { highlight, type Tint } from '#lib/highlight.js';
  import { BLOCK_KIND_LABEL, blockColors, blockLabels } from '#lib/study.js';
  import { cn } from '#lib/utils.js';

  /** 줄을 문장 경계로 자른 조각. from, to는 칸 */
  type Piece = { unit: number | null; from: number; to: number };

  /** 조각을 다시 문법 색 경계로 자른 글자들. color는 글자색 클래스 */
  type Run = { text: string; color?: string };

  /** 끌어서 고르는 중. 문장에서 시작하면 걸친 문장만, 줄 번호에서 시작하면 그 줄들의 문장을 모두 고른다 */
  type Drag = { by: 'unit' | 'line'; from: number; to: number };

  const kinds: BlockKind[] = ['input', 'logic', 'output'];

  let {
    code,
    language,
    units = [],
    blocks = [],
    focus = null,
    selected = [],
    onselect,
    onkind,
    onremove,
    after,
    class: className
  }: {
    code: string;
    /** 주면 코드에 문법 색을 칠한다 */
    language?: Language;
    /** 문장 위치 [줄, 칸]. 칸은 글자(코드 포인트) 단위, end는 포함하지 않는다 */
    units?: Span[];
    /** 블럭마다 종류와 문장 번호. 블럭마다 색을 칠하고, 첫 문장이 있는 줄에 이름을 단다 */
    blocks?: { kind: BlockKind; units: number[] }[];
    /** 이 블럭의 문장만 칠한다. null이면 모든 블럭을 칠한다 */
    focus?: number | null;
    /** 고른 문장. 테두리를 두른다 */
    selected?: number[];
    /** 주면 문장이나 줄 번호를 끌어서(키보드로는 문장을 눌러서) 문장을 고를 수 있다 */
    onselect?: (units: number[]) => void;
    /** 주면 범례의 블럭 이름을 눌러 종류를 바꿀 수 있다 */
    onkind?: (block: number, kind: BlockKind) => void;
    /** 주면 범례에서 블럭을 뺄 수 있다 */
    onremove?: (block: number) => void;
    /** 줄 아래에 끼울 내용 (질문 스레드, 블럭 고르는 창). 줄 번호를 받는다 */
    after?: Snippet<[number]>;
    class?: string;
  } = $props();

  let drag = $state<Drag | null>(null);

  /** 마우스를 올린 문장이나 블럭 이름의 블럭. 그 블럭의 문장을 모두 진하게 칠한다 */
  let hovered = $state<number | null>(null);

  let root = $state<HTMLDivElement>();

  /** 줄마다(0번이 1줄) 글자 */
  const lines = $derived(
    code
      .replace(/\n$/, '')
      .split('\n')
      .map((line) => Array.from(line))
  );

  /** 줄 번호 (1부터) */
  const numbers = $derived(lines.map((_, i) => i + 1));

  /** 줄마다(0번이 1줄) 문법 색 조각 */
  const tints: Tint[][] = $derived(language === undefined ? [] : highlight(code, language));

  const labels = $derived(blockLabels(blocks));

  const colors = $derived(blockColors(blocks));

  /** 문장마다 든 블럭 번호, 없으면 null */
  const owner = $derived.by(() => {
    const of: (number | null)[] = units.map(() => null);

    blocks.forEach((b, i) => {
      for (const unit of b.units) of[unit] = i;
    });

    return of;
  });

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

  /** 줄마다 그 줄에서 시작하는 블럭들 (블럭 이름을 단다) */
  const startsAt = $derived.by(() => {
    const at: number[][] = [];

    blocks.forEach((b, i) => {
      if (b.units.length > 0) (at[units[Math.min(...b.units)].start[0]] ??= []).push(i);
    });

    return at;
  });

  const highlighted = $derived(new Set(drag === null ? selected : dragged(drag)));

  function dragged({ by, from, to }: Drag): number[] {
    const [lo, hi] = from < to ? [from, to] : [to, from];

    if (by === 'unit') return Array.from({ length: hi - lo + 1 }, (_, k) => lo + k);

    return units.flatMap((u, i) => (u.start[0] <= hi && u.end[0] >= lo ? [i] : []));
  }

  function pieces(number: number): Piece[] {
    const length = lines[number - 1]?.length ?? 0;
    const out: Piece[] = [];
    let col = 0;

    for (const [unit, from, to] of spans[number] ?? []) {
      const end = Math.min(to, length);

      if (from > col) out.push({ unit: null, from: col, to: from });
      out.push({ unit, from, to: end });
      col = end;
    }

    if (col < length) out.push({ unit: null, from: col, to: length });

    return out;
  }

  function runs(number: number, piece: Piece): Run[] {
    const chars = lines[number - 1] ?? [];
    const text = (from: number, to: number) => chars.slice(from, to).join('');
    const out: Run[] = [];
    let col = piece.from;

    for (const tint of tints[number - 1] ?? []) {
      const from = Math.max(col, tint.from);
      const to = Math.min(piece.to, tint.to);

      if (from >= to) continue;

      if (from > col) out.push({ text: text(col, from) });
      out.push({ text: text(from, to), color: tint.color });
      col = to;
    }

    if (col < piece.to) out.push({ text: text(col, piece.to) });

    return out;
  }

  function fill(unit: number | null): string | undefined {
    const block = unit === null ? null : owner[unit];

    if (block === null) return undefined;

    if (block === hovered) return colors[block].strong;

    if (focus !== null && block !== focus) return undefined;

    return colors[block].fill;
  }

  /** 줄 번호 옆 띠는 그 줄의 첫 블럭 색. 칠하지 않는 블럭의 띠는 흐리게 둔다 */
  function bar(number: number): string | undefined {
    const unit = (spans[number] ?? []).find(([u]) => owner[u] !== null)?.[0];
    const block = unit === undefined ? null : owner[unit];

    if (block === null) return undefined;

    return cn(colors[block].bar, focus !== null && block !== focus && 'opacity-30');
  }

  function start(event: PointerEvent, by: Drag['by'], at: number) {
    if (event.button !== 0) return;

    // 터치는 누른 요소가 포인터를 붙잡아 두므로, 놓아 줘야 끄는 동안 지나는 줄과 문장이 잡힌다
    if (event.target instanceof Element && event.target.hasPointerCapture(event.pointerId)) {
      event.target.releasePointerCapture(event.pointerId);
    }

    drag = { by, from: at, to: at };
  }

  function move(event: PointerEvent) {
    if (drag === null || !(event.target instanceof Element)) return;

    const attribute = drag.by === 'unit' ? 'data-unit' : 'data-line';
    const at = event.target.closest(`[${attribute}]`)?.getAttribute(attribute);

    if (at != null) drag.to = Number(at);
  }

  function end() {
    if (drag === null) return;

    const picked = dragged(drag);

    drag = null;
    onselect?.(picked);
  }

  function changeKind(block: number, value: string) {
    const kind = kinds.find((k) => k === value);

    if (kind !== undefined && kind !== blocks[block].kind) onkind?.(block, kind);
  }

  /** 마우스가 이 코드 뷰 밖으로 나가면 다른 곳의 pointerover가 하이라이트를 끈다 */
  function hover(event: PointerEvent) {
    if (drag !== null || !(event.target instanceof Element)) return;

    if (!root?.contains(event.target)) {
      hovered = null;

      return;
    }

    const block = event.target.closest('[data-block]')?.getAttribute('data-block');
    const unit = event.target.closest('[data-unit]')?.getAttribute('data-unit');

    if (block != null) hovered = Number(block);
    else if (unit != null) hovered = owner[Number(unit)];
    else hovered = null;
  }

  /** 키보드로 누른 문장 하나를 고른다. 마우스와 터치는 끌기(start, end)가 맡는다 */
  function press(event: MouseEvent, unit: number) {
    if (event.detail === 0) onselect?.([unit]);
  }
</script>

{#snippet colored(
  number: number,
  piece: Piece
)}{#each runs(number, piece) as run, k (k)}{#if run.color}<span class={run.color}>{run.text}</span
      >{:else}{run.text}{/if}{/each}{/snippet}

<svelte:window
  onpointerover={hover}
  onpointermove={move}
  onpointerup={end}
  onpointercancel={() => (drag = null)}
/>

<div
  bind:this={root}
  class={cn('overflow-hidden rounded-2xl border bg-muted/40 text-sm', className)}
>
  {#if blocks.length > 0}
    <div class="flex flex-wrap items-center gap-2 border-b bg-background px-3 py-2 text-xs">
      {#each labels as label, i (i)}
        <span
          class={cn(
            'inline-flex items-center gap-1.5 rounded-md px-2 py-0.5',
            i === hovered ? colors[i].strong : colors[i].fill
          )}
          data-block={i}
        >
          <span class={cn('size-2 rounded-full', colors[i].bar)}></span>
          {#if onkind}
            <DropdownMenu.Root>
              <DropdownMenu.Trigger
                class="-mx-1 inline-flex cursor-pointer items-center gap-0.5 rounded-sm px-1 hover:bg-foreground/10"
                aria-label="{label} 종류 바꾸기"
                >{label}<IconChevronDown class="size-3" /></DropdownMenu.Trigger
              >
              <DropdownMenu.Content class="w-32" align="start">
                <DropdownMenu.Group>
                  <DropdownMenu.Label>종류</DropdownMenu.Label>
                  <DropdownMenu.RadioGroup
                    value={blocks[i].kind}
                    onValueChange={(value) => changeKind(i, value)}
                  >
                    {#each kinds as kind (kind)}
                      <DropdownMenu.RadioItem value={kind} closeOnSelect
                        >{BLOCK_KIND_LABEL[kind]}</DropdownMenu.RadioItem
                      >
                    {/each}
                  </DropdownMenu.RadioGroup>
                </DropdownMenu.Group>
              </DropdownMenu.Content>
            </DropdownMenu.Root>
          {:else}
            {label}
          {/if}
          {#if onremove}
            <button
              type="button"
              class="-mr-1 cursor-pointer rounded-sm p-0.5 hover:bg-foreground/10"
              aria-label="{label} 블럭 빼기"
              onclick={() => onremove(i)}><IconX class="size-3" /></button
            >
          {/if}
        </span>
      {/each}
      <span class="text-muted-foreground">칠하지 않은 문장은 어느 블럭에도 들지 않아요.</span>
    </div>
  {/if}

  <div class={cn('py-3 font-mono leading-6', onselect && 'select-none')}>
    {#each numbers as number (number)}
      <div class="flex" data-line={number}>
        <span class={cn('w-1 shrink-0', bar(number))}></span>
        {#if onselect}
          <button
            type="button"
            tabindex="-1"
            class="w-10 shrink-0 cursor-pointer touch-none pr-3 text-right text-muted-foreground hover:text-foreground"
            aria-label="{number}줄"
            onpointerdown={(e) => start(e, 'line', number)}>{number}</button
          >
        {:else}
          <span class="w-10 shrink-0 pr-3 text-right text-muted-foreground select-none"
            >{number}</span
          >
        {/if}
        <span class="min-w-0 flex-1 pr-3 wrap-anywhere whitespace-pre-wrap"
          >{#each pieces(number) as piece, i (i)}{@const unit =
              piece.unit}{#if onselect && unit !== null}<button
                type="button"
                class={cn(
                  'cursor-pointer rounded-sm wrap-anywhere whitespace-pre-wrap hover:ring-2 hover:ring-ring',
                  fill(unit),
                  highlighted.has(unit) && 'ring-2 ring-primary'
                )}
                data-unit={unit}
                aria-label="{number}줄 문장"
                aria-pressed={highlighted.has(unit)}
                onpointerdown={(e) => start(e, 'unit', unit)}
                onclick={(e) => press(e, unit)}>{@render colored(number, piece)}</button
              >{:else}<span
                class={cn(
                  'rounded-sm',
                  fill(unit),
                  unit !== null && highlighted.has(unit) && 'ring-2 ring-primary'
                )}
                data-unit={unit}>{@render colored(number, piece)}</span
              >{/if}{/each}</span
        >
        {#each startsAt[number] ?? [] as block (block)}
          <span
            class={cn(
              'mr-3 shrink-0 rounded-md px-1.5 font-sans text-xs',
              block === hovered ? colors[block].strong : colors[block].fill
            )}
            data-block={block}>{labels[block]}</span
          >
        {/each}
      </div>
      {@render after?.(number)}
    {/each}
  </div>
</div>

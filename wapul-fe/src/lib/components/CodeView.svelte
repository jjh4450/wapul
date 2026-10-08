<script lang="ts">
  import type { Snippet } from 'svelte';
  import { SvelteMap } from 'svelte/reactivity';
  import { IconChevronDown, IconChevronUp, IconX } from '@tabler/icons-svelte';
  import type { BlockKind, Language, Span } from '#lib/api/client.js';
  import * as DropdownMenu from '#lib/components/ui/dropdown-menu/index.js';
  import { highlight, type Tint } from '#lib/highlight.js';
  import { BLOCK_KIND_LABEL, blockColors, blockLabels } from '#lib/study.js';
  import { cn } from '#lib/utils.js';

  /** 줄을 문장 경계로 자른 조각. from, to는 칸 */
  type Piece = { unit: number | null; from: number; to: number };

  /** 조각을 다시 문법 색 경계로 자른 글자들. color는 글자색 클래스 */
  type Run = { text: string; color?: string };

  /**
   * 끌어서 고르는 중. 줄 번호에서 시작하면(line) 걸친 줄의 문장을 모두, 코드에서 시작하면(unit) 두 지점
   * 사이의 문장을 고른다. unit의 from, to는 위치(position)다
   */
  type Drag = { by: 'unit' | 'line'; from: number; to: number };

  type Block = { kind: BlockKind; units: number[]; wrong?: boolean };

  /**
   * 화면 위나 아래의 돋보기 창. groups는 이어진 줄끼리 묶은 줄, edge는 창과 화면 사이에 숨은 줄
   * [첫 줄, 끝 줄]이다
   */
  type Pane = { groups: number[][]; edge: [number, number] | null };

  /** 화면보다 위(above)와 아래(below)의 돋보기 창. 띄울 줄이 없으면 null */
  type Lens = { above: Pane | null; below: Pane | null };

  const kinds: BlockKind[] = ['input', 'logic', 'output'];

  /** 돋보기 창에서 ^를 한 번 누를 때 펼치는 줄 수 */
  const UNFOLD_STEP = 10;

  /** 돋보기 창 너비(px). 코드 오른쪽 빈자리에 맞추고, LENS_MIN보다 좁으면 창을 띄우지 않는다 */
  const LENS_MIN = 240;

  const LENS_MAX = 480;

  /** 돋보기 창을 화면 쪽 끝 너머로 끌 수 있는 가장 먼 거리(px) */
  const STRETCH_MAX = 48;

  /** 마지막으로 굴리고 이만큼(ms) 지나면 끌려간 창이 돌아온다 */
  const SETTLE_MS = 140;

  /**
   * 돋보기 창 가장자리에서 안쪽 글자를 끌어오는 가장 먼 거리(px)의 두 배 (feDisplacementMap scale).
   * 가장자리 띠 두께(14px)보다 작아야 글자가 뒤집혀 접히지 않고 가장자리로 갈수록 눌리기만 한다
   */
  const RIM_PULL = 12;

  /**
   * 돋보기 창 가장자리 띠의 굴절 지도. 빨강은 가로, 초록은 세로로 끌어올 방향이고 128이면 제자리다.
   * 바깥 끝일수록 가파르게 멀리서 끌어와 물방울 가장자리처럼 휘어 보인다
   */
  function rimMap(edge: 'top' | 'bottom' | 'left' | 'right'): string {
    const vertical = edge === 'top' || edge === 'bottom';
    const outerFirst = edge === 'top' || edge === 'left';
    const outer = outerFirst ? 255 : 0;

    const stops = [0, 0.25, 0.5, 0.75, 1].map((offset) => {
      const fromOuter = outerFirst ? offset : 1 - offset;
      const v = Math.round(128 + (outer - 128) * (1 - fromOuter) ** 2);
      const color = vertical ? `rgb(128,${v},128)` : `rgb(${v},128,128)`;

      return `<stop offset="${offset}" stop-color="${color}"/>`;
    });

    const svg =
      `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 1 1" preserveAspectRatio="none">` +
      `<linearGradient id="g" x2="${vertical ? 0 : 1}" y2="${vertical ? 1 : 0}">${stops.join('')}</linearGradient>` +
      `<rect width="1" height="1" fill="url(#g)"/></svg>`;

    return `data:image/svg+xml,${encodeURIComponent(svg)}`;
  }

  /** 돋보기 창의 네 가장자리 띠 (두께 3.5 = 14px) */
  const RIMS = [
    { edge: 'top', place: 'inset-x-0 top-0 h-3.5', map: rimMap('top') },
    { edge: 'bottom', place: 'inset-x-0 bottom-0 h-3.5', map: rimMap('bottom') },
    { edge: 'left', place: 'inset-y-0 left-0 w-3.5', map: rimMap('left') },
    { edge: 'right', place: 'inset-y-0 right-0 w-3.5', map: rimMap('right') }
  ];

  let {
    code,
    language,
    units = [],
    blocks = [],
    focus = null,
    selected = [],
    onselect,
    onkind,
    onwrong,
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
    /** wrong은 처음 제출에서 틀렸다고 표시한 블럭. 범례에 함께 적는다 */
    blocks?: Block[];
    /** 이 블럭의 문장만 칠한다. null이면 모든 블럭을 칠한다 */
    focus?: number | null;
    /** 고른 문장. 테두리를 두른다 */
    selected?: number[];
    /** 주면 코드 줄 어디서든 끌어서(키보드로는 문장을 눌러서) 문장을 고를 수 있다 */
    onselect?: (units: number[]) => void;
    /** 주면 범례의 블럭 이름을 눌러 종류를 바꿀 수 있다 */
    onkind?: (block: number, kind: BlockKind) => void;
    /** 주면 범례의 블럭 이름 메뉴에서 처음 제출에서 틀렸는지 표시할 수 있다 */
    onwrong?: (block: number, wrong: boolean) => void;
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

  /** 코드와 돋보기 창을 함께 감싼 틀 */
  let frame = $state<HTMLDivElement>();

  /** 마지막으로 마우스를 올린 블럭. 마우스가 틀 안에 있는 동안 돋보기 창에 남겨 창까지 갈 수 있게 한다 */
  let held = $state<number | null>(null);

  /** 돋보기 창에서 ^로 펼친 줄. 블럭마다 따로 두고, 블럭이 바뀌면(편집) 모두 접힌다 */
  const opened = new SvelteMap<number, number[]>();

  /** opened를 펼칠 때의 블럭 */
  let openedFor = $state.raw<Block[]>([]);

  /** 코드 오른쪽 빈자리의 너비(px) */
  let room = $state(0);

  /** 돋보기 창을 화면 쪽 끝 너머로 더 굴린 양. 저항을 걸어 조금만 끌려가고, 멈추면 튕기듯 돌아온다 */
  let stretch = $state({ top: 0, bottom: 0 });

  let stretching = $state(false);

  let settle: ReturnType<typeof setTimeout> | undefined;

  /** 돋보기 창의 굴절 필터 id 앞부분 */
  const uid = $props.id();

  /** 줄 번호마다 화면에 보이는지. 아직 모르는 줄은 없다 */
  const onscreen = new SvelteMap<number, boolean>();

  let watcher: IntersectionObserver | undefined;

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

  /** 돋보기 창에 띄울 블럭: 마우스를 올린 블럭, 없으면 칠하는 블럭, 없으면 마지막으로 올린 블럭 */
  const peek = $derived(hovered ?? focus ?? held);

  /** 돋보기 창 너비 (코드와 띄움 16px, 화면 끝과 띄움 16px을 뺀다) */
  const lensWidth = $derived(Math.min(LENS_MAX, room - 32));

  /**
   * 돋보기 창. peek 블럭의 문장이 걸친 줄 중 화면 밖의 줄을, 화면보다 위(above)와 아래(below)로
   * 나눠 띄운다
   */
  const lens = $derived.by((): Lens => {
    if (peek === null || peek >= blocks.length) return { above: null, below: null };

    const own = new Set(
      blocks[peek].units.flatMap((unit) => {
        const { start, end } = units[unit];

        return Array.from({ length: end[0] - start[0] + 1 }, (_, k) => start[0] + k);
      })
    );

    const away = [...own].filter((n) => onscreen.get(n) === false);
    const shown = [...onscreen].flatMap(([n, on]) => (on ? [n] : []));
    // 화면에 줄이 하나도 없으면(긴 질문 묶음이 화면을 채울 때) 블럭은 그 묶음보다 위에 있고,
    // 화면과 맞닿은 줄은 모른다
    const first = shown.length === 0 ? Infinity : Math.min(...shown);
    const last = shown.length === 0 ? Infinity : Math.max(...shown);
    const above = away.filter((n) => n < first);
    const below = away.filter((n) => n > last);

    return {
      above: above.length === 0 ? null : paneFor(peek, 'top', above, Math.min(...above), first - 1),
      below:
        below.length === 0 ? null : paneFor(peek, 'bottom', below, last + 1, Math.max(...below))
    };
  });

  /** 돋보기 창에서 덜어 낼 들여쓰기 칸 수: 띄우는 줄 중 가장 얕은 들여쓰기 */
  const indent = $derived(
    Math.min(
      ...[...(lens.above?.groups ?? []), ...(lens.below?.groups ?? [])].flat().map((n) => {
        const at = (lines[n - 1] ?? []).findIndex((c) => c.trim() !== '');

        return at === -1 ? Infinity : at;
      })
    )
  );

  const highlighted = $derived(new Set(drag === null ? selected : dragged(drag)));

  function dragged({ by, from, to }: Drag): number[] {
    const [lo, hi] = from < to ? [from, to] : [to, from];

    if (by === 'line')
      return units.flatMap((u, i) => (u.start[0] <= hi && u.end[0] >= lo ? [i] : []));

    // 빈 곳의 위치는 반 칸이라, 문장을 쪼개지 않고 두 지점 사이에 온전히 든 문장만 남는다
    const first = Math.ceil(lo);
    const last = Math.floor(hi);

    return first > last ? [] : Array.from({ length: last - first + 1 }, (_, k) => first + k);
  }

  /**
   * 코드 위 한 지점의 위치. 문장 위면 그 문장 번호, 빈 곳(들여쓰기, 괄호, 줄 끝 뒤, 빈 줄)이면 그 자리
   * 다음에 오는 첫 문장의 번호 - 0.5. 코드 줄 밖이면 null
   */
  function position(target: Element): number | null {
    const unit = target.closest('[data-unit]')?.getAttribute('data-unit');

    if (unit != null) return Number(unit);

    const line = target.closest('[data-line]')?.getAttribute('data-line');

    if (line == null) return null;

    const col = target.closest('[data-col]')?.getAttribute('data-col');

    // 칸을 모르는 빈 곳(줄 끝 뒤, 빈 줄)은 그 줄의 끝으로 친다
    const [atLine, atCol] = col == null ? [Number(line) + 1, 0] : [Number(line), Number(col)];

    const next = units.findIndex(
      (u) => u.start[0] > atLine || (u.start[0] === atLine && u.start[1] >= atCol)
    );

    return (next === -1 ? units.length : next) - 0.5;
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

  /** block을 펼친 줄 */
  function openedOf(block: number): number[] {
    return (openedFor === blocks ? opened.get(block) : undefined) ?? [];
  }

  /**
   * 줄 from~to를 비추는 창. 블럭의 화면 밖 줄(away)과 그 사이에서 펼친 줄을 이어진 줄끼리 묶고,
   * 화면 쪽 끝(위 창은 아래, 아래 창은 위)과 화면 사이에 숨은 줄을 edge로 둔다
   */
  function paneFor(
    block: number,
    side: 'top' | 'bottom',
    away: number[],
    from: number,
    to: number
  ): Pane {
    const unfolded = openedOf(block).filter((n) => n >= from && n <= to);
    const rows = [...new Set([...away, ...unfolded])].sort((a, b) => a - b);
    const groups: number[][] = [];

    for (const n of rows) {
      const group = groups.at(-1);

      if (group?.at(-1) === n - 1) group.push(n);
      else groups.push([n]);
    }

    const [low, high] = [rows[0], rows[rows.length - 1]];

    if (side === 'top')
      return { groups, edge: high < to && to !== Infinity ? [high + 1, to] : null };

    return { groups, edge: low > from ? [from, low - 1] : null };
  }

  /** 돋보기 창에서 숨은 줄 from~to 중 아래쪽 UNFOLD_STEP줄을 펼친다 (아래 것 바로 위부터 위로) */
  function unfold(block: number, from: number, to: number) {
    const start = Math.max(from, to - UNFOLD_STEP + 1);
    const kept = openedOf(block);

    if (openedFor !== blocks) {
      opened.clear();
      openedFor = blocks;
    }

    opened.set(block, [...kept, ...Array.from({ length: to - start + 1 }, (_, k) => start + k)]);
  }

  /** 끈 양(px)에 저항을 건 거리. 끌수록 덜 끌려가고 STRETCH_MAX를 넘지 않는다 */
  function give(pulled: number): number {
    return (STRETCH_MAX * pulled) / (pulled + STRETCH_MAX * 3);
  }

  /**
   * 창 안을 굴리다 화면 쪽 끝(위 창은 아래 끝, 아래 창은 위 끝)에 닿으면 페이지로 넘기지 않고 저항을
   * 건다. 위 창은 화면 쪽 끝에서 시작한다
   */
  function resist(side: 'top' | 'bottom') {
    return (scroller: HTMLDivElement) => {
      if (side === 'top') scroller.scrollTop = scroller.scrollHeight;

      function wheel(event: WheelEvent) {
        const atEdge =
          side === 'top'
            ? event.deltaY > 0 &&
              scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 1
            : event.deltaY < 0 && scroller.scrollTop <= 0;

        if (!atEdge) return;

        event.preventDefault();
        stretch[side] += Math.abs(event.deltaY);
        stretching = true;
        clearTimeout(settle);
        settle = setTimeout(() => {
          stretching = false;
          stretch = { top: 0, bottom: 0 };
        }, SETTLE_MS);
      }

      // 끝에서 페이지가 대신 굴러가지 않게 막아야 하므로 passive가 아니다
      scroller.addEventListener('wheel', wheel, { passive: false });

      return () => scroller.removeEventListener('wheel', wheel);
    };
  }

  /** 코드 오른쪽 빈자리의 너비를 잰다 */
  function measure(node: HTMLDivElement) {
    const update = () => {
      room = document.documentElement.clientWidth - node.getBoundingClientRect().right;
    };

    const observer = new ResizeObserver(update);

    observer.observe(node);
    window.addEventListener('resize', update);

    return () => {
      observer.disconnect();
      window.removeEventListener('resize', update);
    };
  }

  /** 돋보기 창의 줄 조각. 들여쓰기를 덜어 낸다 */
  function dedented(number: number): Piece[] {
    return pieces(number).flatMap((piece) =>
      piece.to <= indent ? [] : [{ ...piece, from: Math.max(piece.from, indent) }]
    );
  }

  /** 줄이 화면에 들어오고 나가는 것을 지켜본다 */
  function watch(row: HTMLDivElement) {
    const number = Number(row.getAttribute('data-line'));

    watcher ??= new IntersectionObserver((entries) => {
      for (const entry of entries)
        onscreen.set(Number(entry.target.getAttribute('data-line')), entry.isIntersecting);
    });
    watcher.observe(row);

    return () => {
      watcher?.unobserve(row);
      onscreen.delete(number);
    };
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

  /** 문장이 든 블럭의 색 변수 (fill의 클래스가 이 색으로 칠한다) */
  function tint(unit: number | null): string | undefined {
    const block = unit === null ? null : owner[unit];

    return block === null ? undefined : colors[block].style;
  }

  /** 줄의 첫 블럭. 줄 번호 옆 띠를 그 블럭 색으로 칠한다 */
  function lineBlock(number: number): number | null {
    const unit = (spans[number] ?? []).find(([u]) => owner[u] !== null)?.[0];

    return unit === undefined ? null : owner[unit];
  }

  /** 줄 번호 옆 띠. 칠하지 않는 블럭의 띠는 흐리게 둔다 */
  function bar(number: number): string | undefined {
    const block = lineBlock(number);

    if (block === null) return undefined;

    return cn(colors[block].bar, focus !== null && block !== focus && 'opacity-30');
  }

  function barTint(number: number): string | undefined {
    const block = lineBlock(number);

    return block === null ? undefined : colors[block].style;
  }

  function start(event: PointerEvent) {
    const { target } = event;

    if (!onselect || event.button !== 0 || !(target instanceof Element)) return;

    if (!root?.contains(target)) return;

    const gutter = target.closest('[data-gutter]')?.getAttribute('data-gutter');
    const at = gutter == null ? position(target) : Number(gutter);

    // 코드 줄 밖(범례, 블럭 고르는 창, 질문 묶음)에서 누른 것은 끌기가 아니다
    if (at === null) return;

    // 터치는 누른 요소가 포인터를 붙잡아 두므로, 놓아 줘야 끄는 동안 지나는 줄과 문장이 잡힌다
    if (target.hasPointerCapture(event.pointerId)) target.releasePointerCapture(event.pointerId);

    drag = { by: gutter == null ? 'unit' : 'line', from: at, to: at };
  }

  function move(event: PointerEvent) {
    if (drag === null || !(event.target instanceof Element)) return;

    const line = event.target.closest('[data-line]')?.getAttribute('data-line');
    const at = drag.by === 'line' ? (line == null ? null : Number(line)) : position(event.target);

    if (at !== null) drag.to = at;
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

    if (!frame?.contains(event.target)) {
      hovered = null;
      held = null;

      return;
    }

    // 돋보기 창 위에서는 띄운 블럭을 그대로 둔다
    if (!root?.contains(event.target)) return;

    const block = event.target.closest('[data-block]')?.getAttribute('data-block');
    const unit = event.target.closest('[data-unit]')?.getAttribute('data-unit');

    if (block != null) hovered = Number(block);
    else if (unit != null) hovered = owner[Number(unit)];
    else hovered = null;

    if (hovered !== null) held = hovered;
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

{#snippet expander(block: number, from: number, to: number)}
  <button
    type="button"
    class="flex w-full cursor-pointer items-center bg-foreground/5 py-0.5 text-muted-foreground hover:bg-foreground/10 hover:text-foreground"
    aria-label="{Math.max(from, to - UNFOLD_STEP + 1)}~{to}줄 펼치기"
    onclick={() => unfold(block, from, to)}
  >
    <span class="flex w-10 shrink-0 justify-end pr-2"><IconChevronUp class="size-4" /></span>
    {from}~{to}줄
  </button>
{/snippet}

{#snippet lensPane(block: number, pane: Pane, side: 'top' | 'bottom', both: boolean)}
  {@const pulled = give(stretch[side])}
  <!-- 물방울 같은 유리: 반투명 바탕, 비스듬한 반사광(before), 가장자리 굴절 띠, 맨 위의 테두리 빛과 그늘(after).
       바탕을 흐리게(backdrop-blur) 하면 굴절 띠가 반투명한 창 안만 보고 겹쳐 그려지므로 흐리지 않는다 -->
  <div
    class={cn(
      'sticky',
      side === 'top' ? 'top-4' : 'bottom-4 mt-auto',
      'overflow-hidden rounded-2xl bg-white/30 text-xs shadow-[0_12px_32px_-12px_rgb(0_0_0/0.35),0_1px_2px_rgb(0_0_0/0.08)] before:pointer-events-none before:absolute before:inset-0 before:bg-linear-to-br before:from-white/60 before:via-white/0 before:via-35% before:to-(--block)/10 after:pointer-events-none after:absolute after:inset-0 after:rounded-[inherit] after:shadow-[inset_0_0_0_1px_rgb(255_255_255/0.75),inset_0_1px_0_rgb(255_255_255),inset_0_0_16px_rgb(0_0_0/0.08),inset_8px_8px_12px_-10px_rgb(255_255_255),inset_-1px_-1px_0_rgb(0_0_0/0.06)] dark:bg-white/5 dark:before:from-white/15 dark:after:shadow-[inset_0_0_0_1px_rgb(255_255_255/0.15),inset_0_1px_0_rgb(255_255_255/0.3),inset_0_0_16px_rgb(0_0_0/0.4)]'
    )}
    style={colors[block].style}
    role="group"
    aria-label={side === 'top' ? '화면 위' : '화면 아래'}
  >
    <div
      class={cn(
        'relative overflow-y-auto overscroll-contain py-1',
        both ? 'max-h-[calc(50dvh-1.5rem)]' : 'max-h-[calc(100dvh-2rem)]'
      )}
      {@attach resist(side)}
    >
      <!-- 끌려간 만큼 화면 쪽 끝에서 멀어지고, 놓으면 살짝 지나쳤다 돌아온다 -->
      <div
        class={cn(
          !stretching && 'transition-transform duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)]'
        )}
        style="transform: translateY({side === 'top' ? -pulled : pulled}px)"
      >
        <p class="flex items-center gap-1.5 px-4 pt-2 pb-1">
          <span class={cn('size-2 rounded-full', colors[block].bar)}></span>{labels[block]}
        </p>
        {#if side === 'bottom' && pane.edge}
          {@render expander(block, pane.edge[0], pane.edge[1])}
        {/if}
        {#each pane.groups as group, g (group[0])}
          {#if g > 0}
            {@const prev = pane.groups[g - 1]}
            {@render expander(block, prev[prev.length - 1] + 1, group[0] - 1)}
          {/if}
          <div class="py-1 font-mono leading-5">
            {#each group as number (number)}
              <div class="flex">
                <span class="w-10 shrink-0 pr-2 text-right text-muted-foreground select-none"
                  >{number}</span
                >
                <span class="min-w-0 flex-1 pr-4 wrap-anywhere whitespace-pre-wrap"
                  >{#each dedented(number) as piece, i (i)}<span
                      class={cn(
                        'rounded-sm',
                        piece.unit !== null && owner[piece.unit] === block && colors[block].fill
                      )}>{@render colored(number, piece)}</span
                    >{/each}</span
                >
              </div>
            {/each}
          </div>
        {/each}
        {#if side === 'top' && pane.edge}
          {@render expander(block, pane.edge[0], pane.edge[1])}
        {/if}
      </div>
    </div>
    <!-- 가장자리 띠마다 그 밑의 글자를 안쪽에서 끌어와 휘게 한다 (backdrop-filter의 SVG 필터는 Chromium만 그린다) -->
    {#each RIMS as rim (rim.edge)}
      <span
        class={cn('pointer-events-none absolute', rim.place)}
        style="backdrop-filter: url(#{uid}-{rim.edge})"
      ></span>
    {/each}
  </div>
{/snippet}

<svelte:window
  onpointerdown={start}
  onpointerover={hover}
  onpointermove={move}
  onpointerup={end}
  onpointercancel={() => (drag = null)}
/>

<div bind:this={frame} class={cn('relative', className)} {@attach measure}>
  <div bind:this={root} class="overflow-hidden rounded-2xl border bg-muted/40 text-sm">
    {#if blocks.length > 0}
      <div class="flex flex-wrap items-center gap-2 border-b bg-background px-3 py-2 text-xs">
        {#each labels as label, i (i)}
          <span
            class={cn(
              'inline-flex items-center gap-1.5 rounded-md px-2 py-0.5',
              i === hovered ? colors[i].strong : colors[i].fill
            )}
            style={colors[i].style}
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
                  {#if onwrong}
                    <DropdownMenu.Separator />
                    <DropdownMenu.CheckboxItem
                      checked={blocks[i].wrong ?? false}
                      onCheckedChange={(on) => onwrong(i, on)}
                      closeOnSelect>처음 제출에서 틀렸어요</DropdownMenu.CheckboxItem
                    >
                  {/if}
                </DropdownMenu.Content>
              </DropdownMenu.Root>
            {:else}
              {label}
            {/if}
            {#if blocks[i].units.length === 0}
              <span class="text-muted-foreground">· 비어 있음</span>
            {/if}
            {#if blocks[i].wrong}
              <span class="text-muted-foreground">· 처음엔 틀림</span>
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
        <div class="flex" data-line={number} {@attach watch}>
          <span class={cn('w-1 shrink-0', bar(number))} style={barTint(number)}></span>
          {#if onselect}
            <button
              type="button"
              tabindex="-1"
              class="w-10 shrink-0 cursor-pointer touch-none pr-3 text-right text-muted-foreground hover:text-foreground"
              aria-label="{number}줄"
              data-gutter={number}>{number}</button
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
                  style={tint(unit)}
                  data-unit={unit}
                  aria-label="{number}줄 문장"
                  aria-pressed={highlighted.has(unit)}
                  onclick={(e) => press(e, unit)}>{@render colored(number, piece)}</button
                >{:else}<span
                  class={cn(
                    'rounded-sm',
                    fill(unit),
                    unit !== null && highlighted.has(unit) && 'ring-2 ring-primary'
                  )}
                  style={tint(unit)}
                  data-unit={unit}
                  data-col={unit === null ? piece.from : null}
                  >{@render colored(number, piece)}</span
                >{/if}{/each}</span
          >
          {#each startsAt[number] ?? [] as block (block)}
            <span
              class={cn(
                'mr-3 shrink-0 rounded-md px-1.5 font-sans text-xs',
                block === hovered ? colors[block].strong : colors[block].fill
              )}
              style={colors[block].style}
              data-block={block}>{labels[block]}</span
            >
          {/each}
        </div>
        {@render after?.(number)}
      {/each}
    </div>
  </div>

  {#if peek !== null && lensWidth >= LENS_MIN && (lens.above || lens.below)}
    <!-- 코드 오른쪽 빈자리에 띄운다. 화면보다 위의 줄은 화면 위쪽에, 아래의 줄은 화면 아래쪽에 붙어
         따라오고, 넘치면 따로 스크롤한다 -->
    <aside
      class="absolute inset-y-0 left-full flex flex-col gap-4 pl-4"
      style="width: {lensWidth + 16}px"
      aria-label="{labels[peek]} 화면 밖 문장"
    >
      {#if lens.above}
        {@render lensPane(peek, lens.above, 'top', lens.below !== null)}
      {/if}
      {#if lens.below}
        {@render lensPane(peek, lens.below, 'bottom', lens.above !== null)}
      {/if}
      <svg class="pointer-events-none absolute size-0" aria-hidden="true">
        {#each RIMS as rim (rim.edge)}
          <filter
            id="{uid}-{rim.edge}"
            x="0"
            y="0"
            width="1"
            height="1"
            color-interpolation-filters="sRGB"
          >
            <feImage href={rim.map} preserveAspectRatio="none" result="map" />
            <feDisplacementMap
              in="SourceGraphic"
              in2="map"
              scale={RIM_PULL}
              xChannelSelector="R"
              yChannelSelector="G"
            />
          </filter>
        {/each}
      </svg>
    </aside>
  {/if}
</div>

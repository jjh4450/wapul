<script lang="ts">
  import { autoUpdate, computePosition, flip, hide, offset, shift, size } from '@floating-ui/dom';
  import { onDestroy } from 'svelte';
  import { Portal } from 'bits-ui';
  import { InputRange } from 'dom-input-range';
  import { Label } from '#lib/components/ui/label/index.js';
  import { Textarea } from '#lib/components/ui/textarea/index.js';
  import type { NameKind } from 'wapul-seg';
  import { suggest, type Name } from '#lib/completions.js';
  import { truncate } from '#lib/study.js';
  import { cn } from '#lib/utils.js';

  let {
    id,
    question,
    example,
    value = $bindable(''),
    note,
    invalid = false,
    words = [],
    near,
    oncommit,
    onnext
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
    /** 자동완성 후보: 코드에 나오는 이름 (completions.ts). 없으면 자동완성을 띄우지 않는다 */
    words?: readonly Name[];
    /** 이 질문이 묻는 블럭의 줄. 그 줄에 나온 이름을 먼저 보여준다 */
    near?: ReadonlySet<number>;
    /** 치다가 멈추거나 칸을 벗어날 때 저장한다 */
    oncommit?: () => void;
    /** Ctrl(Mac은 ⌘)+Enter로 넘긴다. 칸을 벗어나 저장한(onblur) 뒤 부른다. Enter만 누르면 줄바꿈이다 */
    onnext?: () => void;
  } = $props();

  const placeholder = $derived(truncate(example, 90));

  const KIND_LABEL = {
    name: '이름',
    function: '함수',
    subscript: '대괄호',
    string: '문자열'
  } satisfies Record<NameKind, string>;

  let textarea = $state<HTMLTextAreaElement | null>(null);

  /** 열린 후보 목록. start는 치고 있는 낱말이 시작하는 곳 */
  let menu = $state<{ items: Name[]; active: number; start: number } | null>(null);

  /** Esc로 닫은 낱말(시작 위치:글자). 그 낱말을 고치기 전에는 다시 열지 않는다 */
  let dismissed = '';

  const listId = $derived(`${id}-words`);

  /** 캐럿이 영문 낱말 끝에 있으면 그 낱말로 후보를 찾는다. IDE처럼 치는 대로 열고 닫는다 */
  function update() {
    if (!textarea || words.length === 0) {
      menu = null;

      return;
    }

    const { value: text, selectionStart: caret, selectionEnd } = textarea;

    let start = caret;

    while (start > 0 && /\w/.test(text[start - 1])) start -= 1;

    const word = text.slice(start, caret);

    const typing =
      caret === selectionEnd &&
      /^[A-Za-z_]/.test(word) &&
      !/\w/.test(text[caret] ?? '') &&
      dismissed !== `${start}:${word}`;

    const items = typing ? suggest(words, word, near) : [];

    menu = items.length === 0 ? null : { items, active: 0, start };
  }

  /**
   * 후보 목록을 친 낱말 아래에 띄우고, 자리가 모자라면 위로 올린다. 자리는 Floating UI가 visualViewport로 재서
   * 모바일 키보드가 가린 곳을 빼고, 화면 옆으로 넘치면 안으로 민다. 스크롤하면 낱말을 따라가고 낱말이 화면
   * 밖으로 나가면 숨는다
   */
  function place(popup: HTMLDivElement) {
    if (!textarea || !menu) return;

    const field = textarea;

    const { start } = menu;

    // 친 낱말의 자리를 기준 요소로 삼는다
    const word = {
      getBoundingClientRect: () =>
        new InputRange(field, start, field.selectionEnd).getBoundingClientRect(),
      contextElement: field
    };

    return autoUpdate(word, popup, () => {
      void computePosition(word, popup, {
        strategy: 'fixed',
        placement: 'bottom-start',
        middleware: [
          offset(4),
          // 옆으로 넘치면 정렬을 뒤집지 않고 shift로 민다. 뒤집으면 낱말에서 멀어진다
          flip({ padding: 8, crossAxis: false }),
          shift({ padding: 8 }),
          size({
            padding: 8,
            apply: (state) => {
              popup.style.maxHeight = `${Math.max(0, state.availableHeight)}px`;
            }
          }),
          hide()
        ]
      }).then((position) => {
        popup.style.left = `${position.x}px`;
        popup.style.top = `${position.y}px`;
        popup.style.visibility = position.middlewareData.hide?.referenceHidden ? 'hidden' : '';
      });
    });
  }

  /** 친 낱말을 고른 이름으로 바꿔 백틱으로 감싼다. 이미 백틱을 열고 쳤으면 그 백틱을 쓴다 */
  function accept(word: Name) {
    if (!textarea || !menu) return;

    const text = textarea.value;
    const caret = textarea.selectionStart;
    const opened = text[menu.start - 1] === '`';
    const from = opened ? menu.start - 1 : menu.start;
    const to = opened && text[caret] === '`' ? caret + 1 : caret;
    const insert = `\`${word.text}\``;

    menu = null;
    textarea.focus();
    textarea.setRangeText(insert, from, to, 'end');
    // bind:value가 바뀐 값을 알도록 입력 이벤트를 낸다
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
  }

  function keydown(event: KeyboardEvent) {
    // 한글을 조합하는 중의 키는 입력기 몫이다. Safari는 조합을 끝내는 키에서 isComposing이 거짓이라 Process도 본다
    if (event.isComposing || event.key === 'Process') return;

    // 넘어갈 곳이 없는 마지막 질문에서도 답에 줄을 넣지 않는다
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();

      if (onnext) {
        textarea?.blur();
        onnext();
      }

      return;
    }

    if (!menu) return;

    const { items, active } = menu;

    if (event.key === 'ArrowDown') menu.active = (active + 1) % items.length;
    else if (event.key === 'ArrowUp') menu.active = (active - 1 + items.length) % items.length;
    else if (event.key === 'Tab' && !event.shiftKey) accept(items[active]);
    else if (event.key === 'Escape') {
      dismissed = `${menu.start}:${textarea?.value.slice(menu.start, textarea.selectionStart)}`;
      menu = null;
    } else return;

    event.preventDefault();
  }

  /** 치다가 이만큼 멈추면 저장한다. 칸을 벗어나지 않고 새로고침해도 쓰던 답이 남게 */
  const PAUSE_MS = 500;

  let pause: ReturnType<typeof setTimeout> | undefined;

  function typed() {
    update();
    clearTimeout(pause);
    pause = setTimeout(() => oncommit?.(), PAUSE_MS);
  }

  onDestroy(() => clearTimeout(pause));

  // 캐럿만 옮기는 키. 친 낱말을 벗어나므로 목록을 닫는다
  const MOVES = new Set(['ArrowLeft', 'ArrowRight', 'Home', 'End']);
</script>

<div class="grid gap-2">
  <Label for={id} class="leading-snug">{question}</Label>
  {#if note}
    <p class="text-xs text-muted-foreground">{note}</p>
  {/if}
  <Textarea
    bind:ref={textarea}
    {id}
    bind:value
    {placeholder}
    maxlength={__LIMITS__.answer}
    rows={3}
    aria-invalid={invalid || undefined}
    aria-autocomplete={words.length > 0 ? 'list' : undefined}
    aria-controls={menu ? listId : undefined}
    aria-activedescendant={menu ? `${listId}-${menu.active}` : undefined}
    oninput={typed}
    onkeydown={keydown}
    onkeyup={(event) => MOVES.has(event.key) && (menu = null)}
    onclick={() => (menu = null)}
    onblur={() => {
      menu = null;
      clearTimeout(pause);
      oncommit?.();
    }}
  />
  <p class="sr-only" aria-live="polite">
    {menu ? `코드 속 이름 ${menu.items.length}개. Tab으로 넣어요.` : ''}
  </p>
</div>

{#if menu}
  <Portal>
    <div
      {@attach place}
      data-clarity-mask="true"
      class="fixed top-0 left-0 z-50 flex w-72 max-w-[calc(100vw-1rem)] flex-col overflow-hidden rounded-xl border bg-popover text-sm text-popover-foreground shadow-md"
    >
      <ul
        id={listId}
        role="listbox"
        aria-label="코드 속 이름"
        class="max-h-64 min-h-0 overflow-y-auto p-1"
      >
        {#each menu.items as item, i (item.text)}
          <li
            id="{listId}-{i}"
            role="option"
            tabindex="-1"
            aria-selected={i === menu.active}
            class={cn(
              'flex cursor-pointer items-center justify-between gap-3 rounded-lg px-2 py-1.5 pointer-coarse:py-2.5',
              i === menu.active && 'bg-accent text-accent-foreground'
            )}
            onpointerdown={(event) => event.preventDefault()}
            onpointermove={(event) => event.pointerType === 'mouse' && menu && (menu.active = i)}
            onclick={() => accept(item)}
            onkeydown={keydown}
          >
            <code class="truncate font-mono">{item.text}</code>
            <span class="shrink-0 text-xs text-muted-foreground">{KIND_LABEL[item.kind]}</span>
          </li>
        {/each}
      </ul>
      <!-- 터치 화면에는 키가 없어 누르는 것으로 충분하다 -->
      <p
        class="shrink-0 border-t px-3 py-1.5 text-xs text-muted-foreground pointer-coarse:hidden"
        aria-hidden="true"
      >
        Tab 넣기 · ↑↓ 고르기 · Esc 닫기
      </p>
    </div>
  </Portal>
{/if}

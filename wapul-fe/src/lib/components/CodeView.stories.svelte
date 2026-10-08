<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { expect, fn, waitFor, within } from 'storybook/test';
  import { blockColors } from '#lib/study.js';
  import CodeView from './CodeView.svelte';

  const code = `n = int(input())
meetings = sorted(tuple(map(int, input().split()))[::-1] for _ in range(n))

count, end = 0, 0
for e, s in meetings:
    if s >= end:
        count, end = count + 1, e

print(count)
`;

  const at = (line: number, from: number, to: number) => ({
    start: [line, from],
    end: [line, to]
  });

  const units = [
    at(1, 0, 16),
    at(2, 0, 75),
    at(4, 0, 17),
    at(5, 0, 21),
    at(6, 4, 16),
    at(7, 8, 33),
    at(9, 0, 12)
  ];

  // 입력 블럭에 문장 둘, 로직 블럭은 4줄과 5~7줄, 출력 블럭
  const blocks = [
    { kind: 'input' as const, units: [0, 1] },
    { kind: 'logic' as const, units: [2, 3, 4, 5] },
    { kind: 'output' as const, units: [6] }
  ];

  const colors = blockColors(blocks);

  // 화면보다 긴 코드: 120줄, 줄마다 문장 하나
  const longLines = Array.from({ length: 120 }, (_, i) => `v${i} = ${i}`);

  const longUnits = longLines.map((line, i) => at(i + 1, 0, line.length));

  // 로직 1은 1~2줄, 95~96줄, 119~120줄로 떨어져 있고, 로직 2는 3~4줄
  const farBlocks = [
    { kind: 'logic' as const, units: [0, 1, 94, 95, 118, 119] },
    { kind: 'logic' as const, units: [2, 3] }
  ];

  // 두 블럭이 서로 끼어 있는 코드: 111줄에는 두 블럭의 문장이 하나씩 있다
  const mixedLines = longLines.map((line, i) => (i === 110 ? 'x = 1; y = 2' : line));

  const mixedUnits = mixedLines.flatMap((line, i) =>
    i === 110 ? [at(111, 0, 5), at(111, 7, 12)] : [at(i + 1, 0, line.length)]
  );

  // 문장 번호: 111줄 앞까지는 줄 번호 - 1, 111줄의 x = 1이 110, y = 2가 111, 그 뒤는 줄 번호
  const mixedBlocks = [
    { kind: 'logic' as const, units: [0, 110, 120] },
    { kind: 'logic' as const, units: [2, 111, 116] }
  ];

  // 화면 밖의 아주 긴 줄 (100줄)
  const wideLine = `w = [${Array.from({ length: 120 }, (_, i) => i).join(', ')}]`;

  const wideLines = longLines.map((line, i) => (i === 99 ? wideLine : line));

  const wideUnits = wideLines.map((line, i) => at(i + 1, 0, line.length));

  /** 돋보기 창의 위나 아래 창 */
  const paneIn = (canvas: HTMLElement, name: '화면 위' | '화면 아래') =>
    within(canvas).queryByRole('group', { name });

  /** 그 창에 글이 있으면 그 요소 */
  const inPane = (canvas: HTMLElement, name: '화면 위' | '화면 아래', text: string) => {
    const pane = paneIn(canvas, name);

    return pane === null ? null : within(pane).queryByText(text);
  };

  /** 창의 굴리는 칸을 굴린다. 막혔으면(페이지로 넘기지 않으면) false */
  const wheel = (pane: HTMLElement | null, deltaY: number) =>
    pane?.firstElementChild?.dispatchEvent(new WheelEvent('wheel', { deltaY, cancelable: true }));

  /** 창에 담긴 줄 번호 */
  const rowsIn = (canvas: HTMLElement, name: '화면 위' | '화면 아래') =>
    [...(paneIn(canvas, name)?.querySelectorAll('[data-lens-line]') ?? [])].map((row) =>
      Number(row.getAttribute('data-lens-line'))
    );

  /** 본문의 그 줄이 화면에 (조금이라도) 보이는지 */
  const onScreen = (canvas: HTMLElement, line: number | undefined) => {
    const rect = canvas.querySelector(`[data-line="${line}"]`)?.getBoundingClientRect();

    return rect !== undefined && rect.bottom > 0 && rect.top < window.innerHeight;
  };

  /** 창 안에서 그 줄이 다 보이는지 */
  const inView = (canvas: HTMLElement, name: '화면 위' | '화면 아래', line: number) => {
    const scroller = paneIn(canvas, name)?.firstElementChild;
    const row = scroller?.querySelector(`[data-lens-line="${line}"]`);

    if (!scroller || !row) return false;

    const box = scroller.getBoundingClientRect();
    const { top, bottom } = row.getBoundingClientRect();

    return top >= box.top && bottom <= box.bottom;
  };

  /**
   * 창 스크롤 막대에서 손잡이가 차지하는 [위치, 길이]와, 창 내용에서 보이는 부분의 [위치, 길이].
   * 모두 전체에 대한 비율
   */
  const thumbVsView = (canvas: HTMLElement, name: '화면 위' | '화면 아래') => {
    const pane = paneIn(canvas, name);
    const scroller = pane?.firstElementChild;
    const thumb = pane?.querySelector('[data-lens-thumb]');
    const track = thumb?.parentElement?.getBoundingClientRect();

    if (!scroller || !thumb || !track) return null;

    const { top, height } = thumb.getBoundingClientRect();
    const { scrollTop, scrollHeight, clientHeight } = scroller;

    return {
      thumb: [(top - track.top) / track.height, height / track.height],
      view: [scrollTop / scrollHeight, clientHeight / scrollHeight]
    };
  };

  /** 그 줄 눈금의 트랙 위 위치와, 창 내용에서 그 줄의 위치. 모두 전체에 대한 비율 */
  const markVsRow = (canvas: HTMLElement, name: '화면 위' | '화면 아래', line: number) => {
    const pane = paneIn(canvas, name);
    const scroller = pane?.firstElementChild;
    const row = scroller?.querySelector(`[data-lens-line="${line}"]`);

    const mark =
      pane === null ? null : within(pane).queryByRole('button', { name: `${line}줄로 가기` });

    const track = mark?.parentElement?.getBoundingClientRect();

    if (!scroller || !(row instanceof HTMLElement) || !mark || !track) return null;

    return [
      (mark.getBoundingClientRect().top - track.top) / track.height,
      row.offsetTop / scroller.scrollHeight
    ];
  };

  /** 창의 굴리는 칸 안에서 끌려가는 내용의 style */
  const pulled = (pane: HTMLElement | null) =>
    pane?.firstElementChild?.firstElementChild?.getAttribute('style');

  /** 요소가 칠해진 블럭 색 (--block 값) */
  const colorOf = (el: HTMLElement | null) => el?.style.getPropertyValue('--block').trim();

  /** blocks[i]의 색 */
  const color = (i: number) => colors[i].style.replace('--block:', '').trim();

  const { Story } = defineMeta({
    title: 'Components/CodeView',
    component: CodeView,
    tags: ['autodocs'],
    args: { code }
  });
</script>

<Story
  name="Default"
  play={async ({ canvas }) => {
    await expect(canvas.getByText('n = int(input())')).toBeInTheDocument();
    await expect(canvas.getByText('print(count)')).toBeInTheDocument();
  }}
/>

<Story
  name="WithBlocks"
  args={{ units, blocks }}
  play={async ({ canvas }) => {
    // 범례에 한 번, 블럭의 첫 문장이 있는 줄에 한 번 이름이 붙는다
    await expect(canvas.getAllByText('입력')).toHaveLength(2);
    await expect(canvas.getAllByText('로직 1')).toHaveLength(2);
    await expect(canvas.getAllByText('출력')).toHaveLength(2);
    await expect(
      canvas.getByText('칠하지 않은 문장은 어느 블럭에도 들지 않아요.')
    ).toBeInTheDocument();
    // 문장만 칠하고 들여쓰기는 칠하지 않는다
    await expect(canvas.getByText('if s >= end:')).toHaveClass('bg-(--block)/25');
    await expect(colorOf(canvas.getByText('if s >= end:'))).toBe(color(1));
  }}
/>

<Story
  name="Focused"
  args={{ units, blocks, focus: 2 }}
  play={async ({ canvas }) => {
    // 고른 블럭만 칠하고, 다른 블럭은 줄 옆 띠로만 보인다
    await expect(canvas.getByText('print(count)')).toHaveClass('bg-(--block)/25');
    await expect(canvas.getByText('if s >= end:')).not.toHaveClass('bg-(--block)/25');
  }}
/>

<Story
  name="Highlighted"
  args={{ units, blocks, language: 'python' }}
  play={async ({ canvas }) => {
    // 문법 색은 글자색, 블럭 색은 바탕이라 둘이 겹쳐도 보인다
    await expect(canvas.getAllByText('int')[0]).toHaveClass('text-code-constant');
    const loop = canvas.getAllByText('for')[1];

    await expect(loop).toHaveClass('text-code-keyword');
    await expect(loop.parentElement).toHaveClass('bg-(--block)/25');
    await expect(colorOf(loop.parentElement)).toBe(color(1));
  }}
/>

<Story
  name="HoverBlock"
  args={{ units, blocks, focus: 2 }}
  play={async ({ canvas, userEvent }) => {
    const condition = canvas.getByText('if s >= end:');

    // 문장에 마우스를 올리면 떨어진 문장까지 그 블럭 전부를 진하게 칠한다. 칠하지 않던 블럭도
    await userEvent.hover(canvas.getByText('count, end = 0, 0'));
    await expect(condition).toHaveClass('bg-(--block)/50');

    await userEvent.unhover(canvas.getByText('count, end = 0, 0'));
    await userEvent.hover(canvas.getByText('n = int(input())'));
    await expect(condition).not.toHaveClass('bg-(--block)/50');
    await expect(canvas.getByText(/^meetings = /)).toHaveClass('bg-(--block)/50');

    // 범례의 블럭 이름에 올려도 같다
    await userEvent.hover(canvas.getAllByText('로직 1')[0]);
    await expect(condition).toHaveClass('bg-(--block)/50');
  }}
/>

<Story
  name="Lens"
  args={{
    code: longLines.join('\n'),
    units: longUnits,
    blocks: farBlocks,
    focus: 0,
    class: 'max-w-2xl'
  }}
  play={async ({ canvas, canvasElement, userEvent }) => {
    const lens = () => canvas.queryByRole('complementary');
    const pane = (name: '화면 위' | '화면 아래') => paneIn(canvasElement, name);
    const shows = (name: '화면 위' | '화면 아래', text: string) =>
      inPane(canvasElement, name, text);
    const rows = (name: '화면 위' | '화면 아래') => rowsIn(canvasElement, name);
    const seen = (line: number | undefined) => onScreen(canvasElement, line);

    // 칠하는 블럭의 줄 중 화면보다 아래인 줄(95, 96, 119, 120줄)이 있으면 화면 아래쪽 창을 띄운다
    await waitFor(() => expect(shows('화면 아래', 'v119 = 119')).toBeInTheDocument());
    await expect(lens()).toHaveAttribute('aria-label', '로직 1 화면 밖 문장');
    await expect(pane('화면 위')).toBeNull();

    // 아래 창은 화면 끝 두 줄부터 마지막 줄까지, 블럭이 아닌 줄도 다 담는다
    const below = rows('화면 아래');

    await expect(below.at(-1)).toBe(120);
    await expect(seen(below[0])).toBe(true);
    await expect(seen(below[1])).toBe(true);
    await expect(seen(below[2])).toBe(false);
    await expect(shows('화면 아래', 'v100 = 100')).toBeInTheDocument();

    // 칠하는 것은 본문과 같다
    await expect(shows('화면 아래', 'v94 = 94')).toHaveClass('bg-(--block)/25');
    await expect(shows('화면 아래', 'v100 = 100')).not.toHaveClass('bg-(--block)/25');

    // 창이 뜨면 그 블럭에서 화면에 가장 가까운 줄(95줄)이 보인다. 떨어진 줄은 눈금을 눌러 찾아간다
    await expect(inView(canvasElement, '화면 아래', 95)).toBe(true);
    await expect(inView(canvasElement, '화면 아래', 120)).toBe(false);

    // 스크롤 막대 손잡이의 위치와 길이는 창에 보이는 부분과 같다. 눈금은 그 줄이 있는 곳에 있다
    const matches = () => {
      const bar = thumbVsView(canvasElement, '화면 아래');

      expect(bar?.thumb[0]).toBeCloseTo(bar?.view[0] ?? -1, 2);
      expect(bar?.thumb[1]).toBeCloseTo(bar?.view[1] ?? -1, 2);
    };

    await waitFor(matches);
    await canvas.findByRole('button', { name: '119줄로 가기' });

    const [mark, row] = markVsRow(canvasElement, '화면 아래', 119) ?? [-1, 1];

    await expect(mark).toBeCloseTo(row, 2);

    await userEvent.click(canvas.getByRole('button', { name: '119줄로 가기' }));
    await waitFor(() => expect(inView(canvasElement, '화면 아래', 119)).toBe(true));
    await waitFor(matches);

    // 손잡이를 끌면 끈 만큼 창이 굴러간다
    const scroller = pane('화면 아래')?.firstElementChild;

    if (scroller) scroller.scrollTop = 0;

    const thumb = pane('화면 아래')?.querySelector('[data-lens-thumb]') ?? document.body;
    const grip = thumb.getBoundingClientRect().top + 5;

    await userEvent.pointer([
      { keys: '[MouseLeft>]', target: thumb, coords: { clientY: grip } },
      { target: thumb, coords: { clientY: grip + 100 } },
      { keys: '[/MouseLeft]' }
    ]);
    await expect(scroller?.scrollTop).toBeGreaterThan(100);

    // 칠하는 블럭(답 쓰기에서 펼친 질문의 블럭)이 있으면 다른 블럭에 마우스를 올려도 창은 그대로다
    await userEvent.hover(canvas.getByText('v2 = 2'));
    await expect(lens()).toHaveAttribute('aria-label', '로직 1 화면 밖 문장');
    await userEvent.hover(canvasElement);

    // 아래 창의 화면 쪽 끝(위)에서 더 굴리면 페이지로 넘기지 않고, 창이 조금 끌려갔다 돌아온다
    if (scroller) scroller.scrollTop = 0;
    await expect(wheel(pane('화면 아래'), -100)).toBe(false);
    await expect(pulled(pane('화면 아래'))).toMatch(/translateY\([1-9]/);
    await waitFor(() => expect(pulled(pane('화면 아래'))).toContain('translateY(0px)'));
    // 반대쪽으로는 막지 않는다
    await expect(wheel(pane('화면 아래'), 100)).toBe(true);

    // 가운데로 내리면 위아래 두 창을 다 띄운다. 위 창은 1줄부터 화면 첫 두 줄까지 담는다
    window.scrollTo(0, (document.documentElement.scrollHeight - window.innerHeight) / 2);
    await waitFor(() => expect(shows('화면 위', 'v0 = 0')).toBeInTheDocument());
    await expect(shows('화면 아래', 'v119 = 119')).toBeInTheDocument();
    await waitFor(() => {
      const above = rows('화면 위');

      expect(above[0]).toBe(1);
      expect(seen(above.at(-1))).toBe(true);
      expect(seen(above.at(-2))).toBe(true);
      expect(seen(above.at(-3))).toBe(false);
    });

    // 위 창의 화면 쪽 끝은 아래다
    const top = pane('화면 위')?.firstElementChild;

    if (top) top.scrollTop = top.scrollHeight;
    await expect(wheel(pane('화면 위'), 100)).toBe(false);
    await expect(pulled(pane('화면 위'))).toMatch(/translateY\(-[1-9]/);

    // 끝까지 내리면 위 창만 남는다
    window.scrollTo(0, document.documentElement.scrollHeight);
    await waitFor(() => expect(pane('화면 아래')).toBeNull());
    await expect(shows('화면 위', 'v1 = 1')).toBeInTheDocument();
    window.scrollTo(0, 0);
  }}
/>

<Story
  name="LensKeepsLastHovered"
  args={{
    code: longLines.join('\n'),
    units: longUnits,
    blocks: farBlocks,
    class: 'max-w-2xl'
  }}
  play={async ({ canvas, canvasElement, userEvent }) => {
    const lens = () => canvas.queryByRole('complementary');

    // 칠하는 블럭이 없으면 마우스를 올린 블럭을 띄운다
    await expect(lens()).toBeNull();
    await userEvent.hover(canvas.getByText('v0 = 0'));
    await waitFor(() => expect(lens()).toHaveAttribute('aria-label', '로직 1 화면 밖 문장'));

    // 코드의 빈 곳을 지나 창으로 가는 동안에도 남고, 코드와 창 밖으로 나가면 닫는다
    await userEvent.hover(canvasElement.querySelector('[data-line="5"]') ?? document.body);
    await expect(lens()).toHaveAttribute('aria-label', '로직 1 화면 밖 문장');
    await userEvent.hover(canvasElement);
    await expect(lens()).toBeNull();
  }}
/>

<Story
  name="LensManyBlocks"
  args={{
    code: mixedLines.join('\n'),
    units: mixedUnits,
    blocks: mixedBlocks,
    class: 'max-w-2xl'
  }}
  play={async ({ canvas, canvasElement, userEvent }) => {
    const lens = () => canvas.queryByRole('complementary');
    const shows = (text: string) => inPane(canvasElement, '화면 아래', text);
    const unit = (n: number) => canvasElement.querySelector(`[data-unit="${n}"]`) ?? document.body;

    // 칠하는 블럭이 없으면(블럭 편집) 마우스를 올린 블럭을 띄운다.
    // 로직 1은 1, 111, 120줄, 로직 2는 3, 111, 116줄이다
    await userEvent.hover(unit(0));
    await waitFor(() => expect(lens()).toHaveAttribute('aria-label', '로직 1 화면 밖 문장'));

    // 창은 본문처럼 칠한다. 띄운 블럭은 진하게, 다른 블럭은 옅게. 한 줄에 두 블럭이 있어도 같다
    await expect(shows('x = 1')).toHaveClass('bg-(--block)/50');
    await expect(shows('y = 2')).toHaveClass('bg-(--block)/25');
    await expect(shows('v115 = 115')).toHaveClass('bg-(--block)/25');

    // 눈금은 띄운 블럭의 줄에만 단다 (창 크기를 잰 뒤에 그린다)
    await expect(await canvas.findByRole('button', { name: '120줄로 가기' })).toBeInTheDocument();
    await expect(canvas.queryByRole('button', { name: '116줄로 가기' })).toBeNull();

    // 다른 블럭에 올리면 그 블럭을 띄운다
    await userEvent.hover(unit(2));
    await waitFor(() => expect(lens()).toHaveAttribute('aria-label', '로직 2 화면 밖 문장'));
    await expect(shows('y = 2')).toHaveClass('bg-(--block)/50');
    await expect(shows('x = 1')).toHaveClass('bg-(--block)/25');
    await expect(await canvas.findByRole('button', { name: '116줄로 가기' })).toBeInTheDocument();
    await expect(canvas.queryByRole('button', { name: '120줄로 가기' })).toBeNull();
  }}
/>

<Story
  name="LensWideLine"
  args={{
    code: wideLines.join('\n'),
    units: wideUnits,
    blocks: [{ kind: 'logic' as const, units: [0, 99] }],
    focus: 0,
    class: 'max-w-2xl'
  }}
  play={async ({ canvasElement }) => {
    const pane = () => paneIn(canvasElement, '화면 아래');

    await waitFor(() => expect(inPane(canvasElement, '화면 아래', wideLine)).toBeInTheDocument());

    // 창 너비는 코드 오른쪽 빈자리에 맞추되 정한 범위를 넘지 않는다
    const width = pane()?.getBoundingClientRect().width ?? 0;

    await expect(width).toBeGreaterThanOrEqual(240);
    await expect(width).toBeLessThanOrEqual(480);

    // 아주 긴 줄은 창 안에서 줄을 바꿔, 창도 페이지도 가로로 넓어지지 않는다
    const row = inPane(canvasElement, '화면 아래', wideLine)?.getBoundingClientRect().height ?? 0;
    const scroller = pane()?.firstElementChild;

    await expect(row).toBeGreaterThan(60);
    await expect(scroller?.scrollWidth).toBe(scroller?.clientWidth);
    await expect(document.documentElement.scrollWidth).toBe(document.documentElement.clientWidth);
  }}
/>

<Story
  name="LensNoRoom"
  args={{
    code: longLines.join('\n'),
    units: longUnits,
    blocks: farBlocks,
    focus: 0
  }}
  play={async ({ canvas }) => {
    // 코드가 화면 너비를 다 쓰면 창을 둘 빈자리가 없다. 창을 띄우지 않고 가로 스크롤도 생기지 않는다
    await expect(canvas.getByText('v119 = 119')).toBeInTheDocument();
    await expect(canvas.queryByRole('complementary')).toBeNull();
    await expect(document.documentElement.scrollWidth).toBe(document.documentElement.clientWidth);
  }}
/>

<Story
  name="DragStatements"
  args={{ units, blocks, onselect: fn() }}
  play={async ({ canvas, userEvent, args }) => {
    // 문장에서 끌기 시작하면 지나간 문장까지 코드 순서대로 고른다
    await userEvent.pointer([
      { keys: '[MouseLeft>]', target: canvas.getByRole('button', { name: '4줄 문장' }) },
      { target: canvas.getByRole('button', { name: '6줄 문장' }) },
      { keys: '[/MouseLeft]' }
    ]);
    await expect(args.onselect).toHaveBeenLastCalledWith([2, 3, 4]);

    // 거꾸로 끌어도 같다
    await userEvent.pointer([
      { keys: '[MouseLeft>]', target: canvas.getByRole('button', { name: '6줄 문장' }) },
      { target: canvas.getByRole('button', { name: '4줄 문장' }) },
      { keys: '[/MouseLeft]' }
    ]);
    await expect(args.onselect).toHaveBeenLastCalledWith([2, 3, 4]);
  }}
/>

<Story
  name="DragLineNumbers"
  args={{ units, blocks, onselect: fn() }}
  play={async ({ canvas, userEvent, args }) => {
    // 줄 번호에서 끌면 그 줄들에 걸친 문장을 모두 고른다. 빈 줄은 건너뛴다
    await userEvent.pointer([
      { keys: '[MouseLeft>]', target: canvas.getByRole('button', { name: '3줄' }) },
      { target: canvas.getByRole('button', { name: '5줄' }) },
      { keys: '[/MouseLeft]' }
    ]);
    await expect(args.onselect).toHaveBeenLastCalledWith([2, 3]);
  }}
/>

<Story
  name="DragFromBlankSpace"
  args={{ units, blocks, onselect: fn() }}
  play={async ({ canvasElement, userEvent, args }) => {
    // 문장 밖(빈 줄, 들여쓰기, 줄 끝 뒤)에서 시작해도 끌린다. 빈 곳은 가장 가까운 문장 경계로 맞춘다
    const row = (line: number) => canvasElement.querySelector(`[data-line="${line}"]`) ?? undefined;
    const indent = (line: number) =>
      canvasElement.querySelector(`[data-line="${line}"] [data-col="0"]`) ?? undefined;

    // 빈 3줄부터 6줄 끝 뒤까지: 4, 5, 6줄 문장
    await userEvent.pointer([
      { keys: '[MouseLeft>]', target: row(3) },
      { target: row(6) },
      { keys: '[/MouseLeft]' }
    ]);
    await expect(args.onselect).toHaveBeenLastCalledWith([2, 3, 4]);

    // 7줄 들여쓰기부터 위로 6줄 문장까지: 6줄 문장만 (7줄 문장은 시작점 뒤에 있다)
    await userEvent.pointer([
      { keys: '[MouseLeft>]', target: indent(7) },
      { target: canvasElement.querySelector('[data-unit="4"]') ?? undefined },
      { keys: '[/MouseLeft]' }
    ]);
    await expect(args.onselect).toHaveBeenLastCalledWith([4]);

    // 빈 곳을 누르기만 하면 아무것도 고르지 않는다 (블럭 고르는 창이 닫힌다)
    await userEvent.click(row(8) ?? document.body);
    await expect(args.onselect).toHaveBeenLastCalledWith([]);
  }}
/>

<Story
  name="KeyboardPick"
  args={{ units, blocks, onselect: fn(), selected: [6] }}
  play={async ({ canvas, userEvent, args }) => {
    // 고른 문장은 눌린 상태로 보인다
    await expect(canvas.getByRole('button', { name: '9줄 문장' })).toHaveAttribute(
      'aria-pressed',
      'true'
    );

    // 키보드로는 문장을 하나씩 고른다. 줄 번호는 탭 순서에 들지 않는다
    canvas.getByRole('button', { name: '6줄 문장' }).focus();
    await userEvent.keyboard('{Enter}');
    await expect(args.onselect).toHaveBeenLastCalledWith([4]);
    await expect(canvas.getByRole('button', { name: '6줄' })).toHaveAttribute('tabindex', '-1');
  }}
/>

<Story
  name="PickBlock"
  args={{ units, blocks, onpick: fn() }}
  play={async ({ canvas, canvasElement, userEvent, args }) => {
    // 문장을 누르면 그 문장이 든 블럭을 고른다
    await userEvent.click(canvas.getByText('if s >= end:'));
    await expect(args.onpick).toHaveBeenLastCalledWith(1);

    // 블럭 이름을 눌러도 같다
    await userEvent.click(canvas.getAllByText('출력')[0]);
    await expect(args.onpick).toHaveBeenLastCalledWith(2);

    // 블럭에 들지 않은 곳(빈 줄)은 고르지 않는다
    await userEvent.click(canvasElement.querySelector('[data-line="3"]') ?? document.body);
    await expect(args.onpick).toHaveBeenCalledTimes(2);
  }}
/>

<Story
  name="RemovableBlocks"
  args={{ units, blocks, onremove: fn() }}
  play={async ({ canvas, userEvent, args }) => {
    await userEvent.click(canvas.getByRole('button', { name: '로직 1 블럭 빼기' }));
    await expect(args.onremove).toHaveBeenCalledWith(1);
  }}
/>

<Story
  name="KindMenu"
  args={{ units, blocks, onkind: fn() }}
  play={async ({ canvas, userEvent, args }) => {
    // 블럭 이름을 누르면 종류 메뉴가 뜬다. 메뉴는 포털로 body에 그려진다
    const body = within(document.body);

    await userEvent.click(canvas.getByRole('button', { name: '로직 1 종류 바꾸기' }));
    await expect(await body.findByRole('menuitemradio', { name: '로직' })).toBeChecked();
    await userEvent.click(body.getByRole('menuitemradio', { name: '출력' }));
    await expect(args.onkind).toHaveBeenCalledWith(1, 'output');
    // bits-ui는 메뉴가 닫히고도 잠깐 body의 클릭을 막는다. 다음 story로 새지 않게 풀릴 때까지 기다린다
    await waitFor(() => expect(document.body).not.toHaveStyle({ pointerEvents: 'none' }));
  }}
/>

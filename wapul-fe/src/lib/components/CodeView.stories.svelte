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

    // 칠하는 블럭의 문장 중 화면보다 아래인 95, 96, 119, 120줄을 화면 아래쪽 창에 띄운다.
    // 위치를 짐작하게 위아래 두 줄(93~98, 117~120줄)도 함께 띄운다
    await waitFor(() => expect(shows('화면 아래', 'v119 = 119')).toBeInTheDocument());
    await expect(lens()).toHaveAttribute('aria-label', '로직 1 화면 밖 문장');
    await expect(shows('화면 아래', 'v94 = 94')).toBeInTheDocument();
    await expect(shows('화면 아래', 'v92 = 92')).toBeInTheDocument();
    await expect(shows('화면 아래', 'v92 = 92')).not.toHaveClass('bg-(--block)/25');
    await expect(shows('화면 아래', 'v91 = 91')).toBeNull();
    await expect(shows('화면 아래', 'v116 = 116')).toBeInTheDocument();
    await expect(shows('화면 아래', 'v0 = 0')).toBeNull();
    await expect(pane('화면 위')).toBeNull();

    // 마우스를 올린 블럭이 먼저다. 그 블럭이 다 화면 안에 있으면 창을 띄우지 않는다
    await userEvent.hover(canvas.getByText('v2 = 2'));
    await expect(lens()).toBeNull();
    await userEvent.hover(canvasElement);
    await expect(lens()).toHaveAttribute('aria-label', '로직 1 화면 밖 문장');

    // 떨어진 줄 사이(99~116줄)는 ↑로 아래 덩어리에 이어 위로, ↓로 위 덩어리에 이어 아래로 열 줄씩
    // 펼친다
    await expect(canvas.getByRole('button', { name: '99~108줄 펼치기' })).toBeInTheDocument();
    await userEvent.click(canvas.getByRole('button', { name: '107~116줄 펼치기' }));
    await expect(shows('화면 아래', 'v106 = 106')).toBeInTheDocument();
    await expect(shows('화면 아래', 'v115 = 115')).toBeInTheDocument();
    await expect(shows('화면 아래', 'v105 = 105')).toBeNull();

    // 남은 줄이 열 줄 이하면 한 번에 다 펼친다
    await expect(canvas.queryByRole('button', { name: '99~108줄 펼치기' })).toBeNull();
    await userEvent.click(canvas.getByRole('button', { name: '99~106줄 펼치기' }));
    await expect(shows('화면 아래', 'v98 = 98')).toBeInTheDocument();

    // 화면과 창 사이에 숨은 줄도 펼친다. 아래 창에서는 맨 위에 있고, ↓는 화면 바로 아래부터 펼친다
    const upward = canvas.getByRole('button', { name: /^\d+~92줄 펼치기$/ });
    const downward = upward.previousElementSibling ?? upward;
    const [first] = (downward.getAttribute('aria-label') ?? '').split('~').map(Number);

    await userEvent.click(downward);
    await expect(shows('화면 아래', `v${first - 1} = ${first - 1}`)).toBeInTheDocument();
    await expect(shows('화면 아래', `v${first - 2} = ${first - 2}`)).toBeNull();

    // 아래 창의 화면 쪽 끝(위)에서 더 굴리면 페이지로 넘기지 않고, 창이 조금 끌려갔다 돌아온다
    await expect(wheel(pane('화면 아래'), -100)).toBe(false);
    await expect(pulled(pane('화면 아래'))).toMatch(/translateY\([1-9]/);
    await waitFor(() => expect(pulled(pane('화면 아래'))).toContain('translateY(0px)'));
    // 반대쪽으로는 막지 않는다
    await expect(wheel(pane('화면 아래'), 100)).toBe(true);

    // 가운데로 내리면 위아래 두 창을 다 띄운다. 위 창의 화면 쪽 끝은 아래다
    window.scrollTo(0, (document.documentElement.scrollHeight - window.innerHeight) / 2);
    await waitFor(() => expect(shows('화면 위', 'v0 = 0')).toBeInTheDocument());
    await expect(shows('화면 위', 'v3 = 3')).toBeInTheDocument();
    await expect(shows('화면 위', 'v4 = 4')).toBeNull();
    await expect(shows('화면 아래', 'v119 = 119')).toBeInTheDocument();
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

    // 창에는 한 번에 블럭 하나만 띄운다. 로직 1은 1, 111, 120줄, 로직 2는 3, 111, 116줄이다
    await userEvent.hover(unit(0));
    await waitFor(() => expect(lens()).toHaveAttribute('aria-label', '로직 1 화면 밖 문장'));

    // 한 줄에 두 블럭의 문장이 있으면 줄은 통째로 띄우고, 띄운 블럭의 문장만 칠한다
    await expect(shows('x = 1')).toHaveClass('bg-(--block)/25');
    await expect(shows('y = 2')).not.toHaveClass('bg-(--block)/25');

    // 펼친 줄에 든 다른 블럭의 문장도 칠하지 않는다
    await userEvent.click(canvas.getByRole('button', { name: '114~117줄 펼치기' }));
    await expect(shows('v115 = 115')).not.toHaveClass('bg-(--block)/25');

    // 다른 블럭으로 바꾸면 그 블럭의 줄을 띄운다. 펼친 줄은 블럭마다 따로다
    await userEvent.hover(unit(2));
    await waitFor(() => expect(lens()).toHaveAttribute('aria-label', '로직 2 화면 밖 문장'));
    await expect(shows('y = 2')).toHaveClass('bg-(--block)/25');
    await expect(shows('x = 1')).not.toHaveClass('bg-(--block)/25');
    await expect(shows('v115 = 115')).toHaveClass('bg-(--block)/25');
    await expect(shows('v117 = 117')).toBeInTheDocument();
    await expect(shows('v118 = 118')).toBeNull();

    // 돌아오면 그 블럭에서 펼쳐 둔 줄이 그대로다
    await userEvent.hover(unit(0));
    await waitFor(() => expect(lens()).toHaveAttribute('aria-label', '로직 1 화면 밖 문장'));
    await expect(shows('v114 = 114')).toBeInTheDocument();
    await expect(canvas.queryByRole('button', { name: '114~117줄 펼치기' })).toBeNull();
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

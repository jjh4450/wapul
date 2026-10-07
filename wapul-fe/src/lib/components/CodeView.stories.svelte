<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { expect, fn, waitFor, within } from 'storybook/test';
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
    await expect(canvas.getByText('if s >= end:')).toHaveClass('bg-amber-500/25');
  }}
/>

<Story
  name="Focused"
  args={{ units, blocks, focus: 2 }}
  play={async ({ canvas }) => {
    // 고른 블럭만 칠하고, 다른 블럭은 줄 옆 띠로만 보인다
    await expect(canvas.getByText('print(count)')).toHaveClass('bg-violet-500/20');
    await expect(canvas.getByText('if s >= end:')).not.toHaveClass('bg-amber-500/25');
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
    await expect(loop.parentElement).toHaveClass('bg-amber-500/25');
  }}
/>

<Story
  name="HoverBlock"
  args={{ units, blocks, focus: 2 }}
  play={async ({ canvas, userEvent }) => {
    const condition = canvas.getByText('if s >= end:');

    // 문장에 마우스를 올리면 떨어진 문장까지 그 블럭 전부를 진하게 칠한다. 칠하지 않던 블럭도
    await userEvent.hover(canvas.getByText('count, end = 0, 0'));
    await expect(condition).toHaveClass('bg-amber-500/50');

    await userEvent.unhover(canvas.getByText('count, end = 0, 0'));
    await userEvent.hover(canvas.getByText('n = int(input())'));
    await expect(condition).not.toHaveClass('bg-amber-500/50');
    await expect(canvas.getByText(/^meetings = /)).toHaveClass('bg-sky-500/45');

    // 범례의 블럭 이름에 올려도 같다
    await userEvent.hover(canvas.getAllByText('로직 1')[0]);
    await expect(condition).toHaveClass('bg-amber-500/50');
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

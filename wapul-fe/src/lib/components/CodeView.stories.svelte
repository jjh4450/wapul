<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { expect, fn } from 'storybook/test';
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
  const owner = [0, 0, 1, 1, 1, 1, 2];

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
  args={{ units, owner, labels: ['입력', '로직 1', '출력'] }}
  play={async ({ canvas }) => {
    // 블럭 이름은 블럭의 첫 문장이 있는 줄에 한 번만 붙는다
    await expect(canvas.getAllByText('입력')).toHaveLength(1);
    await expect(canvas.getAllByText('로직 1')).toHaveLength(1);
    await expect(canvas.getAllByText('출력')).toHaveLength(1);
    // 문장만 칠하고 들여쓰기는 칠하지 않는다
    await expect(canvas.getByText('if s >= end:')).toHaveClass('bg-amber-500/25');
  }}
/>

<Story
  name="SomeLines"
  args={{ units, owner: [null, null, 1, 1, null, null, null], lines: [1, 4, 5] }}
  play={async ({ canvas }) => {
    // 고른 줄만 보이고, 건너뛴 줄은 ⋯로 줄인다. 줄 번호는 원래 코드의 번호를 쓴다
    await expect(canvas.getByText('count, end = 0, 0')).toBeInTheDocument();
    await expect(canvas.getByText('4')).toBeInTheDocument();
    await expect(canvas.getAllByText('⋯')).toHaveLength(1);
    await expect(canvas.queryByText('print(count)')).not.toBeInTheDocument();
  }}
/>

<Story
  name="Pickable"
  args={{ units, owner, onpick: fn() }}
  play={async ({ canvas, userEvent, args }) => {
    // 같은 줄의 들여쓰기는 누를 수 없고 문장만 누를 수 있다
    await expect(canvas.getAllByRole('button')).toHaveLength(units.length);
    await userEvent.click(canvas.getByRole('button', { name: '6줄 문장' }));
    await expect(args.onpick).toHaveBeenCalledWith(4);
  }}
/>

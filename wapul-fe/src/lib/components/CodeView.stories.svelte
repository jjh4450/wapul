<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { expect } from 'storybook/test';
  import CodeView from './CodeView.svelte';

  const code = `n = int(input())
meetings = sorted(tuple(map(int, input().split()))[::-1] for _ in range(n))

count, end = 0, 0
for e, s in meetings:
    if s >= end:
        count, end = count + 1, e

print(count)`;

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
  args={{
    marks: [
      { start_line: 1, end_line: 2, name: '입력 받기' },
      { start_line: 4, end_line: 7, name: '회의 고르기' },
      { start_line: 9, end_line: 9, name: '결과 출력' }
    ]
  }}
  play={async ({ canvas }) => {
    // 블럭 이름은 블럭 첫 줄에 한 번만 붙는다
    await expect(canvas.getAllByText('입력 받기')).toHaveLength(1);
    await expect(canvas.getAllByText('회의 고르기')).toHaveLength(1);
    await expect(canvas.getAllByText('결과 출력')).toHaveLength(1);
  }}
/>

<Story
  name="Range"
  args={{ from: 4, to: 7 }}
  play={async ({ canvas }) => {
    // 고른 줄만 보이고 줄 번호는 원래 코드의 번호를 쓴다
    await expect(canvas.getByText('count, end = 0, 0')).toBeInTheDocument();
    await expect(canvas.getByText('4')).toBeInTheDocument();
    await expect(canvas.getByText('7')).toBeInTheDocument();
    await expect(canvas.queryByText('n = int(input())')).not.toBeInTheDocument();
    await expect(canvas.queryByText('print(count)')).not.toBeInTheDocument();
  }}
/>

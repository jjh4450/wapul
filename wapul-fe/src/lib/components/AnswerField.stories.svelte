<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { expect, fn } from 'storybook/test';
  import AnswerField from './AnswerField.svelte';

  const question = '이 부분이 끝나면 무엇이 보장되고, 그게 왜 성립하나요?';

  const example = '정렬이 끝나면 회의가 끝나는 시간 순서로 놓인다.';

  const { Story } = defineMeta({
    title: 'Components/AnswerField',
    component: AnswerField,
    tags: ['autodocs'],
    args: { id: 'q1', question, example, oncommit: fn() }
  });
</script>

<Story
  name="Empty"
  play={async ({ canvas }) => {
    // 예제는 빈 칸의 회색 안내문 하나뿐이고 넘겨 볼 버튼은 없다
    await expect(canvas.getByLabelText(question)).toHaveAttribute('placeholder', example);
    await expect(canvas.queryByRole('button')).not.toBeInTheDocument();
  }}
/>

<Story
  name="LongExample"
  args={{ example: '가'.repeat(120) }}
  play={async ({ canvas }) => {
    // 칸보다 긴 예제는 ...로 줄인다
    await expect(canvas.getByLabelText(question)).toHaveAttribute(
      'placeholder',
      `${'가'.repeat(90)}...`
    );
  }}
/>

<Story
  name="Answered"
  args={{
    question: '처음 제출에서 무엇이 달라졌고, 왜 그게 필요했나요?',
    note: '건너뛸 수 있어요.',
    value: '시작 시간도 함께 정렬했다.'
  }}
  play={async ({ canvas }) => {
    await expect(canvas.getByText('건너뛸 수 있어요.')).toBeInTheDocument();
    await expect(canvas.getByRole('textbox')).toHaveValue('시작 시간도 함께 정렬했다.');
  }}
/>

<Story
  name="CommitOnBlur"
  play={async ({ canvas, userEvent, args }) => {
    await userEvent.type(canvas.getByLabelText(question), '정렬 순서가 보장된다');
    await expect(args.oncommit).not.toHaveBeenCalled();
    await userEvent.tab();
    await expect(args.oncommit).toHaveBeenCalledOnce();
  }}
/>

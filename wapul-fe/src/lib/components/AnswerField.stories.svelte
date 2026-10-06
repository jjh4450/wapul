<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { expect, fn } from 'storybook/test';
  import AnswerField from './AnswerField.svelte';

  const question = '이 부분이 끝나면 무엇이 보장되고, 그게 왜 성립하나요?';

  const examples = [
    '정렬이 끝나면 회의가 끝나는 시간 순서로 놓인다.',
    '이 부분이 끝나면 cur와 prev에는 F(i)와 F(i-1)이 들어 있다.'
  ];

  const { Story } = defineMeta({
    title: 'Components/AnswerField',
    component: AnswerField,
    tags: ['autodocs'],
    args: { id: 'q1', question, examples, oncommit: fn() }
  });
</script>

<Story
  name="Empty"
  play={async ({ canvas, userEvent }) => {
    const field = canvas.getByLabelText(question);

    const next = canvas.getByRole('button', { name: '다른 예시' });

    // 예제는 하나씩만 보이고, 다른 예시로 넘기면 끝에서 처음으로 돌아온다
    await expect(field).toHaveAttribute('placeholder', examples[0]);
    await userEvent.click(next);
    await expect(field).toHaveAttribute('placeholder', examples[1]);
    await userEvent.click(next);
    await expect(field).toHaveAttribute('placeholder', examples[0]);
  }}
/>

<Story
  name="LongExample"
  args={{ examples: ['가'.repeat(120)] }}
  play={async ({ canvas }) => {
    // 칸보다 긴 예제는 ...로 줄이고, 예제가 하나면 넘길 버튼이 없다
    await expect(canvas.getByLabelText(question)).toHaveAttribute(
      'placeholder',
      `${'가'.repeat(90)}...`
    );
    await expect(canvas.queryByRole('button', { name: '다른 예시' })).not.toBeInTheDocument();
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
    // 답을 쓰고 나면 예제를 넘길 일이 없다
    await expect(canvas.queryByRole('button', { name: '다른 예시' })).not.toBeInTheDocument();
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

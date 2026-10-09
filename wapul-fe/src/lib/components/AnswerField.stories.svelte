<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { expect, fn, within } from 'storybook/test';
  import type { Name } from '#lib/completions.js';
  import AnswerField from './AnswerField.svelte';

  const question = '이 부분이 끝나면 무엇이 보장되고, 그게 왜 성립하나요?';

  const example = '정렬이 끝나면 회의가 끝나는 시간 순서로 놓인다.';

  const { Story } = defineMeta({
    title: 'Components/AnswerField',
    component: AnswerField,
    tags: ['autodocs'],
    args: { id: 'q1', question, example, oncommit: fn() }
  });

  const name = (text: string, kind: Name['kind'], lines: number[], count = lines.length) => ({
    text,
    kind,
    lines,
    count
  });

  // 코드 속 이름 (wapul-seg의 names가 주는 꼴)
  const words: Name[] = [
    name('dp', 'name', [4, 8, 9], 6),
    name('dp[i - 1][j]', 'subscript', [8], 2),
    name('dp[i][j]', 'subscript', [8]),
    name('max', 'function', [8]),
    name('map', 'function', [3])
  ];

  /** 목록은 body에 붙는다 */
  const list = (canvasElement: HTMLElement) => within(canvasElement.ownerDocument.body);
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

<Story
  name="CompletesCodeNames"
  args={{ words }}
  play={async ({ canvas, canvasElement, userEvent }) => {
    const field = canvas.getByLabelText(question);

    // 앞글자를 치면 코드 속 이름이 뜨고, Tab으로 백틱에 감싸 넣는다. 칸을 벗어나지 않는다
    await userEvent.type(field, 'd');

    const options = list(canvasElement).getAllByRole('option');

    await expect(options[0]).toHaveTextContent('dp');
    await expect(options[0]).toHaveAttribute('aria-selected', 'true');
    await userEvent.keyboard('{Tab}');
    await expect(field).toHaveValue('`dp`');
    await expect(field).toHaveFocus();
    await expect(list(canvasElement).queryByRole('listbox')).not.toBeInTheDocument();
  }}
/>

<Story
  name="PicksBracketExpression"
  args={{ words }}
  play={async ({ canvas, canvasElement, userEvent }) => {
    const field = canvas.getByLabelText(question);

    // 대괄호 식은 많이 나온 것부터. 화살표로 골라 넣는다
    await userEvent.type(field, '갱신은 dp');
    await userEvent.keyboard('{ArrowDown}');
    await expect(list(canvasElement).getAllByRole('option')[1]).toHaveAttribute(
      'aria-selected',
      'true'
    );
    await userEvent.keyboard('{Tab}');
    await expect(field).toHaveValue('갱신은 `dp[i - 1][j]`');
  }}
/>

<Story
  name="UsesOpenedBacktick"
  args={{ words }}
  play={async ({ canvas, userEvent }) => {
    const field = canvas.getByLabelText(question);

    // 이미 백틱을 열고 쳤으면 그 백틱으로 감싼다
    await userEvent.type(field, '`ma');
    await userEvent.keyboard('{Tab}');
    await expect(field).toHaveValue('`map`');
  }}
/>

<Story
  name="EscapeAndEnter"
  args={{ words }}
  play={async ({ canvas, canvasElement, userEvent }) => {
    const field = canvas.getByLabelText(question);

    // Esc로 닫으면 그 낱말로는 다시 열지 않고, Enter는 언제나 줄바꿈이다
    await userEvent.type(field, 'ma');
    await expect(list(canvasElement).getByRole('listbox')).toBeInTheDocument();
    await userEvent.keyboard('{Escape}');
    await expect(list(canvasElement).queryByRole('listbox')).not.toBeInTheDocument();
    await userEvent.keyboard('{Enter}');
    await expect(field).toHaveValue('ma\n');
  }}
/>

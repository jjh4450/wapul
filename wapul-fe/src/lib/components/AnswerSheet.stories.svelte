<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { expect, fn, waitFor, within } from 'storybook/test';
  import { FakeApi, empty, reply } from '#lib/api/fake.js';
  import { record, sharedRecord } from '#lib/api/fixtures.js';
  import { EXAMPLES } from '#lib/questions.js';
  import { truncate } from '#lib/study.js';
  import AnswerSheet from './AnswerSheet.svelte';

  const { Story } = defineMeta({
    title: 'Components/AnswerSheet',
    component: AnswerSheet,
    args: { id: 'record-1', onfinish: fn(), onnotowner: fn() }
  });

  const writing = new FakeApi([
    ['GET /v1/records/:id', reply(record)],
    ['PATCH /v1/records/:id/answers', empty()]
  ]);

  // 문제 질문에 이미 답한 기록
  const resumed = new FakeApi([
    [
      'GET /v1/records/:id',
      reply({
        ...record,
        questions: record.questions.map((q) =>
          q.kind === 'problem' ? { ...q, answer: '끝나는 시간이 빠를수록 남는 시간이 넓다' } : q
        )
      })
    ]
  ]);

  const saveFails = new FakeApi([
    ['GET /v1/records/:id', reply(record)],
    ['PATCH /v1/records/:id/answers', reply({ detail: 'x' }, 500)]
  ]);

  const viewer = new FakeApi([['GET /v1/records/:id', reply(sharedRecord)]]);

  const problemQuestion = record.questions[0].text;

  /** 질문 묶음 바로 위에 있는 코드 줄의 번호 */
  const lineAbove = (thread: HTMLElement) =>
    thread.parentElement?.previousElementSibling?.getAttribute('data-line');
</script>

<Story
  name="ThreadsUnderBlocks"
  beforeEach={() => writing.install()}
  play={async ({ canvas, canvasElement }) => {
    // 전체 코드가 보이고, 블럭 질문은 블럭이 끝나는 줄 바로 아래에 달린다
    const logic = await canvas.findByRole('region', { name: '로직 1' });

    await expect(canvasElement.querySelector('[data-line="1"]')).toHaveTextContent(
      '#include <bits/stdc++.h>'
    );
    await expect(lineAbove(logic)).toBe('12');
    await expect(lineAbove(canvas.getByRole('region', { name: '입력' }))).toBe('7');
    await expect(lineAbove(canvas.getByRole('region', { name: '출력' }))).toBe('15');

    // 처음에는 빈 칸이 있는 첫 묶음(문제)만 펼친다
    await expect(canvas.getAllByRole('textbox')).toHaveLength(1);
    await expect(within(logic).getByRole('button', { expanded: false })).toHaveTextContent(
      '질문 2개 · 0개 답함'
    );

    // 빈 칸에는 다른 문제에서 가져온 예제가 회색 안내문으로 뜬다
    const placeholder = canvas.getByLabelText(problemQuestion).getAttribute('placeholder');

    await expect(EXAMPLES.problem.map((e) => truncate(e, 90))).toContain(placeholder);
  }}
/>

<Story
  name="OneThreadAtATime"
  beforeEach={() => writing.install()}
  play={async ({ canvas, userEvent }) => {
    // 다음 질문은 코드에서 다음에 나오는 묶음(입력)을 연다. 앞 묶음은 접힌다
    await userEvent.click(await canvas.findByRole('button', { name: '다음 질문' }));

    const inputThread = canvas.getByRole('region', { name: '입력' });
    const input = within(inputThread);

    // 화면을 그 묶음으로 옮기고, 첫 빈 칸에 커서를 둔다
    await waitFor(() => {
      const { top } = inputThread.getBoundingClientRect();

      expect(top).toBeGreaterThanOrEqual(0);
      expect(top).toBeLessThan(window.innerHeight);
    });
    await expect(input.getByLabelText(/입력 조건/)).toHaveFocus();

    await expect(input.getByLabelText(/입력을 담은 변수/)).toHaveValue(
      'm은 (끝나는 시간, 시작 시간) 쌍의 목록이다.'
    );
    await expect(input.getByRole('button', { expanded: true })).toHaveTextContent(
      '질문 2개 · 1개 답함'
    );
    await expect(canvas.queryByLabelText(problemQuestion)).not.toBeInTheDocument();

    // 접힌 묶음은 눌러서 바로 연다
    const logic = within(canvas.getByRole('region', { name: '로직 1' }));

    await userEvent.click(logic.getByRole('button', { expanded: false }));
    await expect(logic.getByLabelText('이 설명이 통하지 않는 입력은 뭘까요?')).toBeInTheDocument();
    await expect(input.queryByRole('textbox')).not.toBeInTheDocument();

    // 기록 단위의 나머지 질문은 코드 아래 마무리에 있고, 처음 제출과 달라진 점은 건너뛸 수 있다
    const closing = within(canvas.getByRole('region', { name: '마무리' }));

    await userEvent.click(closing.getByRole('button', { expanded: false }));
    await expect(closing.getByText('건너뛸 수 있어요.')).toBeInTheDocument();
    await expect(closing.queryByRole('button', { name: '다음 질문' })).not.toBeInTheDocument();
  }}
/>

<Story
  name="ResumesAtFirstGap"
  beforeEach={() => resumed.install()}
  play={async ({ canvas }) => {
    // 문제 질문에 답했으면 빈 칸이 남은 입력 묶음부터 연다
    const input = within(await canvas.findByRole('region', { name: '입력' }));

    await expect(input.getByRole('button', { expanded: true })).toBeInTheDocument();
    await expect(canvas.queryByLabelText(problemQuestion)).not.toBeInTheDocument();
  }}
/>

<Story
  name="SavesOnlyChangedAnswers"
  beforeEach={() => writing.install()}
  play={async ({ canvas, userEvent, args }) => {
    const field = await canvas.findByLabelText(problemQuestion);

    await userEvent.type(field, '가장 일찍 끝나는 회의를 고르면 남는 시간이 가장 넓다');
    await userEvent.tab();

    await waitFor(() =>
      expect(writing.callsTo('PATCH', '/v1/records/record-1/answers')).toHaveLength(1)
    );
    await expect(canvas.getByText('저장했어요.')).toBeInTheDocument();
    await expect(JSON.parse(writing.calls.at(-1)?.body ?? '')).toEqual({
      answers: [
        { question_id: 'q-problem', answer: '가장 일찍 끝나는 회의를 고르면 남는 시간이 가장 넓다' }
      ]
    });

    // 바뀌지 않은 칸은 다시 보내지 않는다
    await userEvent.click(field);
    await userEvent.tab();
    await userEvent.click(canvas.getByRole('button', { name: '다 썼어요' }));

    await waitFor(() => expect(args.onfinish).toHaveBeenCalledOnce());
    await expect(writing.callsTo('PATCH', '/v1/records/record-1/answers')).toHaveLength(1);
  }}
/>

<Story
  name="SaveFails"
  beforeEach={() => saveFails.install()}
  play={async ({ canvas, userEvent, args }) => {
    await userEvent.type(await canvas.findByLabelText(problemQuestion), '성질');
    await userEvent.click(canvas.getByRole('button', { name: '다 썼어요' }));

    await expect(await canvas.findByText('요청을 처리하지 못했어요. (500)')).toBeInTheDocument();
    await expect(args.onfinish).not.toHaveBeenCalled();
  }}
/>

<Story
  name="NotTheAuthor"
  beforeEach={() => viewer.install()}
  play={async ({ canvas, args }) => {
    await waitFor(() => expect(args.onnotowner).toHaveBeenCalledOnce());
    await expect(canvas.queryByRole('textbox')).not.toBeInTheDocument();
  }}
/>

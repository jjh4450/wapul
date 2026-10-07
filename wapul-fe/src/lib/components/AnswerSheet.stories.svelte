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

  const saveFails = new FakeApi([
    ['GET /v1/records/:id', reply(record)],
    ['PATCH /v1/records/:id/answers', reply({ detail: 'x' }, 500)]
  ]);

  const viewer = new FakeApi([['GET /v1/records/:id', reply(sharedRecord)]]);

  const problemQuestion = record.questions[0].text;
</script>

<Story
  name="QuestionsBesideCode"
  beforeEach={() => writing.install()}
  play={async ({ canvas }) => {
    // 블럭마다 코드와 그 블럭의 질문이 한 영역에 나란히 있다
    const logic = within(await canvas.findByRole('region', { name: '로직 1' }));

    await expect(logic.getByText('sort(m.begin(), m.end());')).toBeInTheDocument();
    await expect(logic.getByLabelText(/무엇이 보장되고/)).toBeInTheDocument();
    await expect(logic.getByLabelText('이 설명이 통하지 않는 입력은 뭘까요?')).toBeInTheDocument();
    await expect(logic.queryByLabelText(/입력을 담은 변수/)).not.toBeInTheDocument();

    const input = within(canvas.getByRole('region', { name: '입력' }));

    await expect(input.getByLabelText(/입력을 담은 변수/)).toHaveValue(
      'm은 (끝나는 시간, 시작 시간) 쌍의 목록이다.'
    );

    // 빈 칸에는 다른 문제에서 가져온 예제가 회색 안내문으로 뜬다
    const placeholder = canvas.getByLabelText(problemQuestion).getAttribute('placeholder');

    await expect(EXAMPLES.problem.map((e) => truncate(e, 90))).toContain(placeholder);

    // 처음 제출과 달라진 점은 건너뛸 수 있다
    await expect(canvas.getByText('건너뛸 수 있어요.')).toBeInTheDocument();
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

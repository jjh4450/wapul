<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { expect, fn, waitFor, within } from 'storybook/test';
  import type { QuestionIn } from '#lib/api/client.js';
  import { reply } from '#lib/api/fake.js';
  import { record, sharedRecord } from '#lib/api/fixtures.js';
  import { localApi } from '#lib/api/local.js';
  import { EXAMPLES } from '#lib/questions.js';
  import { truncate } from '#lib/study.js';
  import AnswerSheet from './AnswerSheet.svelte';

  const { Story } = defineMeta({
    title: 'Components/AnswerSheet',
    component: AnswerSheet,
    args: { id: 'record-1', backend: true, onfinish: fn(), onnotowner: fn() }
  });

  // 기록은 브라우저 안의 백엔드가 답한다. 블럭을 고치면 백엔드처럼 블럭과 질문에 새 id가 붙는다
  const writing = localApi([record]);

  // 문제 질문에 이미 답한 기록
  const resumed = localApi([
    {
      ...record,
      questions: record.questions.map((q) =>
        q.kind === 'problem' ? { ...q, answer: '끝나는 시간이 빠를수록 남는 시간이 넓다' } : q
      )
    }
  ]);

  const saveFails = localApi(
    [record],
    [['PATCH /v1/records/:id/answers', reply({ detail: 'x' }, 500)]]
  );

  const viewer = localApi([sharedRecord]);

  const markFails = localApi(
    [record],
    [['PUT /v1/records/:id/blocks', reply({ detail: 'x' }, 500)]]
  );

  const problemQuestion = record.questions[0].text;

  /** 모달이 닫히고 페이지가 다시 눌릴 때까지. bits-ui는 모달이 닫히고도 잠깐 body의 클릭을 막는다 */
  const modalClosed = () =>
    waitFor(() => {
      expect(document.querySelector('[role="alertdialog"]')).toBeNull();
      expect(document.body).not.toHaveStyle({ pointerEvents: 'none' });
    });

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
      '질문 3개 · 0개 답함'
    );

    // 빈 칸에는 다른 문제에서 가져온 예제가 회색 안내문으로 뜬다
    const placeholder = canvas.getByLabelText(problemQuestion).getAttribute('placeholder');

    await expect(EXAMPLES.problem.map((e) => truncate(e, 90))).toContain(placeholder);
  }}
/>

<Story
  name="PickBlockInCode"
  beforeEach={() => writing.install()}
  play={async ({ canvas, canvasElement, userEvent }) => {
    const expanded = (label: string) =>
      within(canvas.getByRole('region', { name: label })).queryByRole('button', { expanded: true });

    // 코드에서 블럭의 문장을 누르면 그 블럭의 질문 묶음을 열고 그리로 옮긴다. 앞 묶음은 접힌다
    await canvas.findByRole('region', { name: '출력' });
    await userEvent.click(canvasElement.querySelector('[data-unit="14"]') ?? document.body);
    await expect(expanded('출력')).toBeInTheDocument();
    await expect(expanded('문제')).toBeNull();

    const outputThread = canvas.getByRole('region', { name: '출력' });

    await waitFor(() => {
      const { top } = outputThread.getBoundingClientRect();

      expect(top).toBeGreaterThanOrEqual(0);
      expect(top).toBeLessThan(window.innerHeight);
    });

    // 블럭 이름을 눌러도 같다
    await userEvent.click(canvasElement.querySelector('[data-block="1"]') ?? document.body);
    await expect(expanded('로직 1')).toBeInTheDocument();
    await expect(expanded('출력')).toBeNull();
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

    // 처음 제출에서 틀렸다고 표시한 블럭에는 건너뛸 수 있는 달라진 점 질문이 붙는다
    await expect(logic.getByRole('checkbox', { name: /처음 제출에서 틀렸어요/ })).toBeChecked();
    await expect(logic.getByText('건너뛸 수 있어요.')).toBeInTheDocument();

    // 기록 단위의 나머지 질문은 코드 아래 마무리에 있다. 블럭이 아니라 틀렸다는 표시는 없다
    const closing = within(canvas.getByRole('region', { name: '마무리' }));

    await userEvent.click(closing.getByRole('button', { expanded: false }));
    await expect(closing.getByLabelText(/입력이 하나뿐이라면/)).toBeInTheDocument();
    await expect(closing.queryByRole('checkbox')).not.toBeInTheDocument();
    await expect(closing.queryByRole('button', { name: '다음 질문' })).not.toBeInTheDocument();
  }}
/>

<Story
  name="MarkWrongInThread"
  beforeEach={() => writing.install()}
  play={async ({ canvas, userEvent }) => {
    await userEvent.click(await canvas.findByRole('button', { name: '다음 질문' }));

    const input = () => within(canvas.getByRole('region', { name: '입력' }));

    await userEvent.type(input().getByLabelText(/입력 조건/), 'N은 10만 이하');

    // 답 쓰다가 틀렸던 블럭이라고 켜면 그 묶음 끝에 달라진 점 질문이 붙는다. 쓰던 답도 함께 저장된다
    await userEvent.click(input().getByRole('checkbox', { name: /처음 제출에서 틀렸어요/ }));

    // 저장하면 블럭과 질문의 id가 바뀌어 묶음을 새로 그리므로 매번 다시 찾는다
    await waitFor(() => expect(input().getByText('건너뛸 수 있어요.')).toBeInTheDocument());
    await expect(input().getByLabelText(/입력 조건/)).toHaveValue('N은 10만 이하');

    const [call] = writing.callsTo('PUT', '/v1/records/record-1/blocks');

    const sent = JSON.parse(call.body).questions.map((q: QuestionIn) => [q.kind, q.block]);

    await expect(sent.slice(1, 4)).toEqual([
      ['input_meaning', 0],
      ['input_condition', 0],
      ['revision', 0]
    ]);
  }}
/>

<Story
  name="MarkWrongFails"
  beforeEach={() => markFails.install()}
  play={async ({ canvas, userEvent }) => {
    await userEvent.click(await canvas.findByRole('button', { name: '다음 질문' }));

    const input = within(canvas.getByRole('region', { name: '입력' }));
    const mark = input.getByRole('checkbox', { name: /처음 제출에서 틀렸어요/ });

    // 저장하지 못하면 체크가 켜진 채로 남지 않고, 이유가 체크 바로 아래에 뜬다
    await userEvent.click(mark);
    await expect(await input.findByText(/표시를 바꾸지 못했어요/)).toBeInTheDocument();
    await expect(mark).not.toBeChecked();
    await expect(input.queryByText('건너뛸 수 있어요.')).not.toBeInTheDocument();
  }}
/>

<Story
  name="CloseTakesThreeTries"
  beforeEach={() => writing.install()}
  play={async ({ canvas, userEvent }) => {
    const body = within(document.body);
    const problem = within(await canvas.findByRole('region', { name: '문제' }));
    const close = problem.getByRole('button', { name: '닫기' });

    // 빈 칸이 있으면 닫기는 막힌 것처럼 보인다. 묶음 머리를 눌러도 닫히지 않는다
    await expect(close).toHaveAttribute('aria-disabled', 'true');
    await userEvent.click(problem.getByRole('button', { expanded: true }));
    await expect(problem.getByRole('button', { expanded: true })).toBeInTheDocument();

    // 1번: 묶음이 흔들리고 빈 칸이 필수 칸처럼 강조되며 모달이 뜬다
    await userEvent.click(close);

    const dialog = await body.findByRole('alertdialog');

    await expect(dialog).toHaveTextContent(/넘어가실|한 줄만|할 말이/);
    await expect(problem.getByLabelText(problemQuestion)).toHaveAttribute('aria-invalid', 'true');
    await userEvent.click(within(dialog).getByRole('button', { name: '답하러 가기' }));
    await modalClosed();
    await expect(problem.getByLabelText(problemQuestion)).toHaveFocus();

    // 2번: 흔들린 뒤에 닫기가 풀린다
    await userEvent.click(close);
    await waitFor(() => expect(close).toHaveAttribute('aria-disabled', 'false'));
    await expect(body.queryByRole('alertdialog')).not.toBeInTheDocument();

    // 3번: 닫힌다
    await userEvent.click(close);
    await expect(problem.getByRole('button', { expanded: false })).toBeInTheDocument();
    await expect(canvas.queryByRole('textbox')).not.toBeInTheDocument();
  }}
/>

<Story
  name="CloseRightAwayWhenAnswered"
  beforeEach={() => writing.install()}
  play={async ({ canvas, userEvent }) => {
    const logic = within(await canvas.findByRole('region', { name: '로직 1' }));

    await userEvent.click(logic.getByRole('button', { expanded: false }));
    await userEvent.type(logic.getByLabelText(/무엇이 보장되고/), '끝나는 시간 순서로 놓인다');
    await userEvent.type(logic.getByLabelText(/통하지 않는 입력/), '끝나는 시간이 같을 때');

    // 건너뛸 수 있는 달라진 점 질문은 비어 있어도 바로 닫힌다
    const close = logic.getByRole('button', { name: '닫기' });

    await expect(close).toHaveAttribute('aria-disabled', 'false');
    await userEvent.click(close);
    await expect(logic.getByRole('button', { expanded: false })).toBeInTheDocument();
    await expect(within(document.body).queryByRole('alertdialog')).not.toBeInTheDocument();
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
  name="NoBackendKeepsInTab"
  args={{ backend: false }}
  beforeEach={() => writing.install()}
  play={async ({ canvas, userEvent }) => {
    await userEvent.type(
      await canvas.findByLabelText(problemQuestion),
      '끝나는 시간이 빠를수록 남는 시간이 넓다'
    );
    await userEvent.tab();

    // 백엔드가 없으면 답은 이 탭에만 있으니 저장했다고 하지 않는다
    await expect(
      await canvas.findByText('이 탭에만 담아 뒀어요. 새로고침하면 사라져요.')
    ).toBeInTheDocument();
    await expect(canvas.queryByText('저장했어요.')).not.toBeInTheDocument();
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

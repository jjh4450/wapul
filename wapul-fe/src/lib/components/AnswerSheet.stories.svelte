<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { expect, fn, waitFor, within } from 'storybook/test';
  import type { QuestionIn } from '#lib/api/client.js';
  import { type FakeApi, reply } from '#lib/api/fake.js';
  import { record, sharedRecord } from '#lib/api/fixtures.js';
  import { localApi } from '#lib/api/local.js';
  import { EXAMPLES } from '#lib/questions.js';
  import { truncate } from '#lib/study.js';
  import { PAUSE_MS } from './AnswerField.svelte';
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

  /** 답 저장이 늦게 돌아오는 백엔드. 언제 돌려보낼지는 story가 정한다 */
  const replies: (() => void)[] = [];

  const slowSave = localApi(
    [record],
    [
      [
        'PATCH /v1/records/:id/answers',
        () =>
          new Promise<Response>((done) =>
            replies.push(() => done(new Response(null, { status: 204 })))
          )
      ]
    ]
  );

  /**
   * 블럭 저장(틀렸다 표시)의 답이 늦게 돌아오는 백엔드. 백엔드처럼 바로 바꾸고 답만 붙잡아서, 그동안 옛 id로
   * 보낸 저장은 찾지 못한다. 언제 돌려보낼지는 story가 정한다
   */
  const marks: (() => void)[] = [];

  function slowMark(api: FakeApi) {
    const restore = api.install();

    const local = globalThis.fetch;

    globalThis.fetch = async (input, init) => {
      const method = input instanceof Request ? input.method : (init?.method ?? 'GET');

      const response = await local(input, init);

      if (method === 'PUT') await new Promise<void>((done) => marks.push(done));

      return response;
    };

    return restore;
  }

  /** 치다 멈춘 자동 저장이 돌 만큼 기다린다 */
  const autosaved = () => new Promise((done) => setTimeout(done, PAUSE_MS + 100));

  /** '다 썼어요'가 끝났을 때 마지막으로 저장된 답 */
  let finishedWith = '';

  /** 모달이 닫히고 페이지가 다시 눌릴 때까지. bits-ui는 모달이 닫히고도 잠깐 body의 클릭을 막는다 */
  const modalClosed = () =>
    waitFor(() => {
      expect(document.querySelector('[role="alertdialog"]')).toBeNull();
      expect(document.body).not.toHaveStyle({ pointerEvents: 'none' });
    });

  /** 질문 묶음 막대(펼치고 접는 단추). 이름이 '로직 1, 질문 2개 중 0개 답함…' 꼴이다 */
  const rule = (root: HTMLElement, label: string) =>
    within(root).getByRole('button', { name: new RegExp(`^${label}, 질문 \\d+개 중`) });

  /** 막대 바로 위에 있는 코드 줄의 번호 */
  const lineAbove = (bar: HTMLElement) =>
    bar.closest('h2')?.previousElementSibling?.getAttribute('data-line');

  /** 화면 안에 들어왔는지 */
  const onScreen = (element: HTMLElement) =>
    waitFor(() => {
      const { top } = element.getBoundingClientRect();

      expect(top).toBeGreaterThanOrEqual(0);
      expect(top).toBeLessThan(window.innerHeight);
    });
</script>

<Story
  name="ThreadsUnderBlocks"
  beforeEach={() => writing.install()}
  play={async ({ canvas, canvasElement }) => {
    // 전체 코드가 보이고, 블럭 질문 묶음은 블럭이 끝나는 줄 바로 아래의 막대로 접어 둔다
    const logic = await canvas.findByRole('button', { name: /^로직 1, 질문/ });

    await expect(canvasElement.querySelector('[data-line="1"]')).toHaveTextContent(
      '#include <bits/stdc++.h>'
    );
    await expect(lineAbove(logic)).toBe('12');
    await expect(lineAbove(rule(canvasElement, '입력'))).toBe('7');
    await expect(lineAbove(rule(canvasElement, '출력'))).toBe('15');

    // 막대는 진행도를 이름으로 읽힌다. 건너뛸 수 있는 질문은 따로 센다
    await expect(logic).toHaveAccessibleName('로직 1, 질문 2개 중 0개 답함, 선택 질문 1개');
    await expect(rule(canvasElement, '입력')).toHaveAccessibleName('입력, 질문 2개 중 1개 답함');

    // 막대의 유리에는 필수 질문마다 한 마디가 있고, 답한 마디를 블럭 색으로 칠한다
    const glass = (bar: HTMLElement) => bar.querySelector('span[aria-hidden]');

    const [answered, blank] = glass(rule(canvasElement, '입력'))?.children ?? [];

    await expect(glass(logic)?.children).toHaveLength(2);
    await expect(answered).toHaveClass('bg-(--block)');
    await expect(blank).toHaveClass('bg-(--block)/15');

    // 막대는 얇아도 위아래로 조금 더 눌린다
    logic.scrollIntoView({ block: 'center' });

    const box = logic.getBoundingClientRect();

    await expect(document.elementFromPoint(box.left + box.width / 2, box.top - 1)).toBe(logic);
    await expect(document.elementFromPoint(box.left + box.width / 2, box.bottom)).toBe(logic);

    // 처음에는 빈 칸이 있는 첫 묶음(문제)만 펼치고, 펼친 막대는 블럭 색으로 물든다
    await expect(rule(canvasElement, '문제')).toHaveAttribute('aria-expanded', 'true');
    await expect(logic).toHaveAttribute('aria-expanded', 'false');
    await expect(glass(rule(canvasElement, '문제'))).toHaveClass('bg-(--block)/15');
    await expect(glass(logic)).toHaveClass('bg-white/30');
    await expect(canvas.getAllByRole('textbox')).toHaveLength(1);

    // 빈 칸에는 다른 문제에서 가져온 예제가 회색 안내문으로 뜬다
    const placeholder = canvas
      .getByRole('textbox', { name: problemQuestion })
      .getAttribute('placeholder');

    await expect(EXAMPLES.problem.map((e) => truncate(e, 90))).toContain(placeholder);
  }}
/>

<Story
  name="PickBlockInCode"
  beforeEach={() => writing.install()}
  play={async ({ canvas, canvasElement, userEvent }) => {
    // 코드에서 블럭의 문장을 누르면 그 블럭의 질문 묶음을 막대 아래에 열고 그리로 옮긴다. 앞 묶음은 접힌다
    await canvas.findByRole('button', { name: /^출력, 질문/ });
    await userEvent.click(canvasElement.querySelector('[data-unit="14"]') ?? document.body);

    const output = await canvas.findByRole('region', { name: '출력' });

    await expect(output.previousElementSibling).toBe(rule(canvasElement, '출력').closest('h2'));
    await expect(canvas.queryByRole('region', { name: '문제' })).toBeNull();
    await onScreen(output);

    // 블럭 이름을 눌러도 같다
    await userEvent.click(canvasElement.querySelector('[data-block="1"]') ?? document.body);
    await expect(await canvas.findByRole('region', { name: '로직 1' })).toBeInTheDocument();
    await expect(canvas.queryByRole('region', { name: '출력' })).toBeNull();
  }}
/>

<Story
  name="OneThreadAtATime"
  beforeEach={() => writing.install()}
  play={async ({ canvas, canvasElement, userEvent }) => {
    // 넘기기 단추는 갈 곳을 말한다. 묶음의 마지막 질문에서는 빈 칸이 남은 다음 묶음(입력)으로 간다
    await userEvent.click(await canvas.findByRole('button', { name: '입력 질문으로' }));

    const inputThread = canvas.getByRole('region', { name: '입력' });

    const input = within(inputThread);

    // 화면을 그 묶음으로 옮기고, 첫 빈 질문의 답 칸에 커서를 둔다. 답한 질문은 한 줄로 답 앞부분을 보인다
    await onScreen(inputThread);
    await expect(input.getByRole('textbox', { name: /입력 조건/ })).toHaveFocus();
    await expect(
      input.getByRole('button', {
        name: '입력을 담은 변수와 자료구조는 각각 무엇을 나타내나요?, 내 답: m은 (끝나는 시간, 시작 시간) 쌍의 목록이다.'
      })
    ).toBeInTheDocument();
    await expect(rule(canvasElement, '입력')).toHaveAttribute('aria-expanded', 'true');
    await expect(canvas.queryByRole('region', { name: '문제' })).toBeNull();

    // 접힌 묶음은 막대를 눌러 바로 연다
    await userEvent.click(rule(canvasElement, '로직 1'));

    const logic = within(canvas.getByRole('region', { name: '로직 1' }));

    await expect(
      logic.getByRole('button', { name: '이 설명이 통하지 않는 입력은 뭘까요?, 아직 답하지 않음' })
    ).toBeInTheDocument();
    await expect(canvas.queryByRole('region', { name: '입력' })).toBeNull();

    // 처음 제출에서 틀렸다고 표시한 블럭에는 건너뛸 수 있는 달라진 점 질문이 붙는다
    await expect(logic.getByRole('checkbox', { name: /처음 제출에서 틀렸어요/ })).toBeChecked();
    await expect(
      logic.getByRole('button', { name: /^처음 제출에서 무엇이.*, 선택$/ })
    ).toBeInTheDocument();

    // 기록 단위의 나머지 질문은 코드 아래 마무리에 있다. 틀렸다는 표시가 없고, 갈 곳이 없어 넘기기도 없다
    await userEvent.click(rule(canvasElement, '마무리'));

    const closing = within(canvas.getByRole('region', { name: '마무리' }));

    await expect(closing.getByRole('textbox', { name: /입력이 하나뿐이라면/ })).toBeInTheDocument();
    await expect(closing.queryByRole('checkbox')).not.toBeInTheDocument();
    await expect(
      closing.queryByRole('button', { name: /다음 질문|질문으로$/ })
    ).not.toBeInTheDocument();
    await expect(closing.getByText("다 쓰면 아래 '다 썼어요'를 눌러요.")).toBeInTheDocument();
  }}
/>

<Story
  name="MarkWrongInThread"
  beforeEach={() => writing.install()}
  play={async ({ canvas, canvasElement, userEvent }) => {
    await userEvent.click(await canvas.findByRole('button', { name: '입력 질문으로' }));

    const input = () => within(canvas.getByRole('region', { name: '입력' }));

    await userEvent.type(input().getByRole('textbox', { name: /입력 조건/ }), 'N은 10만 이하');

    // 답 쓰다가 틀렸던 블럭이라고 켜면 그 묶음 끝에 달라진 점 질문이 붙는다. 쓰던 답도 함께 저장된다
    await userEvent.click(input().getByRole('checkbox', { name: /처음 제출에서 틀렸어요/ }));

    // 저장하면 블럭과 질문의 id가 바뀌어 묶음을 새로 그리므로 매번 다시 찾는다. 쓰던 질문은 그대로 펼쳐져 있다
    await waitFor(() =>
      expect(
        input().getByRole('button', { name: /^처음 제출(에서|과).*, 선택$/ })
      ).toBeInTheDocument()
    );
    await expect(input().getByRole('textbox', { name: /입력 조건/ })).toHaveValue('N은 10만 이하');
    await expect(rule(canvasElement, '입력')).toHaveAccessibleName(
      '입력, 질문 2개 중 2개 답함, 선택 질문 1개'
    );

    // 저장하는 동안 체크가 꺼져 커서가 빠졌다가 체크로 돌아온다
    await waitFor(() =>
      expect(input().getByRole('checkbox', { name: /처음 제출에서 틀렸어요/ })).toHaveFocus()
    );

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
    await userEvent.click(await canvas.findByRole('button', { name: '입력 질문으로' }));

    const input = within(canvas.getByRole('region', { name: '입력' }));

    const mark = input.getByRole('checkbox', { name: /처음 제출에서 틀렸어요/ });

    // 저장하지 못하면 체크가 켜진 채로 남지 않고, 이유가 체크 바로 아래에 뜬다
    await userEvent.click(mark);
    await expect(await input.findByText(/표시를 바꾸지 못했어요/)).toBeInTheDocument();
    await expect(mark).not.toBeChecked();
    await expect(input.queryByRole('button', { name: /^처음 제출/ })).not.toBeInTheDocument();
    await waitFor(() => expect(mark).toHaveFocus());
  }}
/>

<Story
  name="KeepsTypingWhileMarking"
  beforeEach={() => {
    marks.length = 0;

    return slowMark(writing);
  }}
  play={async ({ canvas, userEvent }) => {
    await userEvent.click(await canvas.findByRole('button', { name: '입력 질문으로' }));

    const input = () => within(canvas.getByRole('region', { name: '입력' }));

    const field = () => input().getByRole('textbox', { name: /입력 조건/ });

    const patches = () => writing.callsTo('PATCH', '/v1/records/record-1/answers');

    // 틀렸다 표시를 저장하는 동안 답 칸으로 돌아가 더 친다
    await userEvent.type(field(), 'N은');
    await userEvent.click(input().getByRole('checkbox', { name: /처음 제출에서 틀렸어요/ }));
    await waitFor(() => expect(marks).toHaveLength(1));

    const sent = patches().length;

    await userEvent.type(field(), ' 10만 이하');

    // 표시를 저장하는 동안에는 치다 멈춰도 옛 id로 보내지 않는다
    await autosaved();
    await expect(patches()).toHaveLength(sent);
    marks.shift()?.();

    // 칸을 새 id로 다시 그려도 더 친 글자와 커서는 그 칸에 남고, 더 친 답은 새 id로 저장한다
    await waitFor(() =>
      expect(
        input().getByRole('button', { name: /^처음 제출(에서|과).*, 선택$/ })
      ).toBeInTheDocument()
    );
    await expect(field()).toHaveValue('N은 10만 이하');
    await expect(field()).toHaveFocus();
    await waitFor(() => {
      const [last] = patches().slice(-1);

      expect(JSON.parse(last.body).answers[0].answer).toBe('N은 10만 이하');
    });
    await expect(canvas.getByText('저장했어요.')).toBeInTheDocument();
  }}
/>

<Story
  name="KeepsTypingWhenMarkFails"
  beforeEach={() => {
    marks.length = 0;

    return slowMark(markFails);
  }}
  play={async ({ canvas, userEvent }) => {
    await userEvent.click(await canvas.findByRole('button', { name: '입력 질문으로' }));

    const input = within(canvas.getByRole('region', { name: '입력' }));

    const field = input.getByRole('textbox', { name: /입력 조건/ });

    await userEvent.type(field, 'N은');
    await userEvent.click(input.getByRole('checkbox', { name: /처음 제출에서 틀렸어요/ }));
    await waitFor(() => expect(marks).toHaveLength(1));
    await userEvent.type(field, ' 10만 이하');
    // 표시를 저장하는 동안 치다 멈춘 자동 저장은 표시가 끝날 때까지 미룬다
    await autosaved();
    marks.shift()?.();

    // 표시를 못 바꾸면 질문은 그대로라, 미룬 답을 원래 질문으로 보낸다
    await expect(await input.findByText(/표시를 바꾸지 못했어요/)).toBeInTheDocument();
    await expect(field).toHaveFocus();
    await waitFor(() => {
      const [last] = markFails.callsTo('PATCH', '/v1/records/record-1/answers').slice(-1);

      expect(JSON.parse(last.body).answers[0]).toEqual({
        question_id: 'q-input-condition',
        answer: 'N은 10만 이하'
      });
    });
  }}
/>

<Story
  name="FinishWaitsForMark"
  args={{
    onfinish: fn(() => {
      const [last] = writing.callsTo('PATCH', '/v1/records/record-1/answers').slice(-1);

      finishedWith = last === undefined ? '' : JSON.parse(last.body).answers[0].answer;
    })
  }}
  beforeEach={() => {
    marks.length = 0;
    finishedWith = '';

    return slowMark(writing);
  }}
  play={async ({ canvas, userEvent, args }) => {
    await userEvent.click(await canvas.findByRole('button', { name: '입력 질문으로' }));

    const input = within(canvas.getByRole('region', { name: '입력' }));

    await userEvent.click(input.getByRole('checkbox', { name: /처음 제출에서 틀렸어요/ }));
    await waitFor(() => expect(marks).toHaveLength(1));
    await userEvent.type(input.getByRole('textbox', { name: /입력 조건/ }), 'N은 10만 이하');

    // 표시를 저장하는 중에 다 썼다고 하면, 표시가 끝나고 그사이 친 답까지 저장한 뒤에 끝낸다
    await userEvent.click(canvas.getByRole('button', { name: '다 썼어요' }));
    await expect(args.onfinish).not.toHaveBeenCalled();
    marks.shift()?.();
    await waitFor(() => expect(args.onfinish).toHaveBeenCalledOnce());
    await expect(finishedWith).toBe('N은 10만 이하');
  }}
/>

<Story
  name="CloseTakesThreeTries"
  beforeEach={() => writing.install()}
  play={async ({ canvas, canvasElement, userEvent }) => {
    const body = within(document.body);

    const problem = await canvas.findByRole('region', { name: '문제' });

    const bar = rule(canvasElement, '문제');

    const field = () => canvas.getByRole('textbox', { name: problemQuestion });

    // 빈 칸이 있으면 막대를 눌러도 바로 접히지 않는다.
    // 1번: 묶음이 흔들리고 빈 칸이 필수 칸처럼 강조되며 모달이 뜬다
    await userEvent.click(bar);

    const dialog = await body.findByRole('alertdialog');

    await expect(dialog).toHaveTextContent(/넘어가실|한 줄만|할 말이/);
    await expect(field()).toHaveAttribute('aria-invalid', 'true');
    await userEvent.click(within(dialog).getByRole('button', { name: '답하러 가기' }));
    await modalClosed();
    await expect(field()).toHaveFocus();
    await expect(bar).toHaveAttribute('aria-expanded', 'true');

    // 2번: 흔들린 뒤에야 접기가 풀린다. 흔들림을 못 보는 사람에게는 말로 알린다
    await userEvent.click(bar);
    await expect(body.queryByRole('alertdialog')).not.toBeInTheDocument();
    await expect(bar).toHaveAttribute('aria-expanded', 'true');
    await waitFor(() =>
      expect(canvas.getByRole('status')).toHaveTextContent(
        '빈 칸이 남았어요. 한 번 더 누르면 접혀요.'
      )
    );
    await waitFor(() => expect(problem.querySelector('.animate-shake')).toBeNull());

    // 3번: 접히고, 커서는 막대로 돌아온다
    await userEvent.click(bar);
    await expect(bar).toHaveAttribute('aria-expanded', 'false');
    await expect(canvas.queryByRole('textbox')).not.toBeInTheDocument();
    await expect(bar).toHaveFocus();
  }}
/>

<Story
  name="CloseRightAwayWhenAnswered"
  beforeEach={() => writing.install()}
  play={async ({ canvas, canvasElement, userEvent }) => {
    await userEvent.click(await canvas.findByRole('button', { name: /^로직 1, 질문/ }));

    const logic = within(canvas.getByRole('region', { name: '로직 1' }));

    await userEvent.type(
      logic.getByRole('textbox', { name: /무엇이 보장되고/ }),
      '끝나는 시간 순서로 놓인다'
    );
    await userEvent.click(logic.getByRole('button', { name: '다음 질문' }));
    await userEvent.type(
      logic.getByRole('textbox', { name: /통하지 않는 입력/ }),
      '끝나는 시간이 같을 때'
    );

    // 건너뛸 수 있는 달라진 점 질문은 비어 있어도 바로 접힌다
    const bar = rule(canvasElement, '로직 1');

    await userEvent.click(bar);
    await expect(canvas.queryByRole('region', { name: '로직 1' })).toBeNull();
    await expect(bar).toHaveAttribute('aria-expanded', 'false');
    await expect(bar).toHaveFocus();
    await expect(within(document.body).queryByRole('alertdialog')).not.toBeInTheDocument();
  }}
/>

<Story
  name="ResumesAtFirstGap"
  beforeEach={() => resumed.install()}
  play={async ({ canvas, canvasElement }) => {
    // 문제 질문에 답했으면 빈 칸이 남은 입력 묶음의 빈 질문부터 연다
    const input = within(await canvas.findByRole('region', { name: '입력' }));

    await expect(rule(canvasElement, '입력')).toHaveAttribute('aria-expanded', 'true');
    await expect(input.getAllByRole('textbox')).toHaveLength(1);
    await expect(input.getByRole('textbox', { name: /입력 조건/ }).closest('li')).toHaveAttribute(
      'aria-current',
      'step'
    );
    await expect(canvas.queryByRole('textbox', { name: problemQuestion })).not.toBeInTheDocument();
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
  name="NoBackendKeepsInBrowser"
  args={{ backend: false, persistent: true }}
  beforeEach={() => writing.install()}
  play={async ({ canvas, userEvent }) => {
    await userEvent.type(
      await canvas.findByLabelText(problemQuestion),
      '끝나는 시간이 빠를수록 남는 시간이 넓다'
    );
    await userEvent.tab();

    // 백엔드가 없으면 답은 이 브라우저에 담기고, 언제 지워지는지 알려 준다
    await expect(
      await canvas.findByText('이 브라우저에 담아 뒀어요. 7일 동안 고치지 않으면 지워져요.')
    ).toBeInTheDocument();
    await expect(canvas.queryByText('저장했어요.')).not.toBeInTheDocument();
  }}
/>

<Story
  name="NoBackendKeepsInTab"
  args={{ backend: false, persistent: false }}
  beforeEach={() => writing.install()}
  play={async ({ canvas, userEvent }) => {
    await userEvent.type(
      await canvas.findByLabelText(problemQuestion),
      '끝나는 시간이 빠를수록 남는 시간이 넓다'
    );
    await userEvent.tab();

    // 저장소를 못 쓰는 브라우저에서는 답이 이 탭에만 있으니 저장했다고 하지 않는다
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

<Story
  name="SendsWhatWasTypedWhileSaving"
  beforeEach={() => {
    replies.length = 0;

    return slowSave.install();
  }}
  play={async ({ canvas, userEvent }) => {
    const field = await canvas.findByLabelText(problemQuestion);

    const patches = () => slowSave.callsTo('PATCH', '/v1/records/record-1/answers');

    // 치다가 멈추면 저장을 보낸다. 답이 오기 전에 더 친다
    await userEvent.type(field, '정렬했기');
    await waitFor(() => expect(patches()).toHaveLength(1));
    await userEvent.type(field, ' 때문이다');
    replies.shift()?.();

    // 보내는 동안 친 글자는 저장된 것으로 치지 않아서, 칸을 벗어날 때 다시 보낸다
    await userEvent.tab();
    await waitFor(() => expect(patches()).toHaveLength(2));
    await expect(JSON.parse(patches()[1].body).answers[0].answer).toBe('정렬했기 때문이다');
    replies.shift()?.();
  }}
/>

<Story
  name="ProgressPerBlock"
  beforeEach={() => writing.install()}
  play={async ({ canvas, canvasElement, userEvent }) => {
    const field = await canvas.findByRole('textbox', { name: problemQuestion });

    const status = canvas.getByRole('status');

    const done = '문제 질문 1개에 모두 답했어요.';

    // 알림 칸의 글자가 바뀔 때마다 남긴다. 같은 글자를 다시 넣으면 바뀌지 않아 읽히지 않는다
    const said: string[] = [];

    const observer = new MutationObserver(() => said.push(status.textContent ?? ''));

    observer.observe(status, { childList: true, characterData: true, subtree: true });

    // 치는 대로 막대의 진행도가 바뀐다. 묶음을 다 답했다는 알림은 저장한 뒤에 한 번만 나온다
    await expect(rule(canvasElement, '문제')).toHaveAccessibleName('문제, 질문 1개 중 0개 답함');
    await userEvent.type(field, '성');
    await expect(rule(canvasElement, '문제')).toHaveAccessibleName('문제, 질문 1개 중 1개 답함');
    await expect(status).toHaveTextContent('');
    await userEvent.tab();
    await waitFor(() => expect(status).toHaveTextContent(done));

    // 비웠다가 다시 다 답하면 같은 말이라도 다시 알린다
    await userEvent.clear(field);
    await userEvent.tab();
    await userEvent.type(field, '성');
    await userEvent.tab();
    await waitFor(() => expect(said.filter((text) => text === done)).toHaveLength(2));
    observer.disconnect();
  }}
/>

<Story
  name="OneQuestionAtATime"
  beforeEach={() => writing.install()}
  play={async ({ canvas, canvasElement, userEvent }) => {
    await userEvent.click(await canvas.findByRole('button', { name: /^로직 1, 질문/ }));

    const logic = within(canvas.getByRole('region', { name: '로직 1' }));

    const guarantee = () => logic.getByRole('textbox', { name: /무엇이 보장되고/ });

    // 질문 셋 중 답하는 하나만 답 칸을 펼친 카드다
    await expect(logic.getAllByRole('listitem')).toHaveLength(3);
    await expect(logic.getAllByRole('textbox')).toHaveLength(1);
    await expect(guarantee().closest('li')).toHaveAttribute('aria-current', 'step');
    await expect(guarantee()).toHaveFocus();

    // Enter는 줄바꿈이고, Ctrl+Enter는 저장하고 다음 질문으로 넘긴다
    await userEvent.type(guarantee(), '정렬이 끝나면{Enter}끝나는 시간 순서로 놓인다');
    await expect(guarantee()).toHaveValue('정렬이 끝나면\n끝나는 시간 순서로 놓인다');
    await userEvent.keyboard('{Control>}{Enter}{/Control}');
    await expect(logic.getByRole('textbox', { name: /통하지 않는 입력/ })).toHaveFocus();

    const answered = logic.getByRole('button', {
      name: /무엇이 보장되고.*, 내 답: 정렬이 끝나면 끝나는 시간 순서로 놓인다$/
    });

    await expect(answered).toBeInTheDocument();
    await waitFor(() =>
      expect(writing.callsTo('PATCH', '/v1/records/record-1/answers')).toHaveLength(1)
    );
    await expect(rule(canvasElement, '로직 1')).toHaveAccessibleName(
      '로직 1, 질문 2개 중 1개 답함, 선택 질문 1개'
    );

    // 한 줄로 접힌 질문을 누르면 쓴 답 그대로 다시 카드가 된다
    await userEvent.click(answered);
    await expect(guarantee()).toHaveValue('정렬이 끝나면\n끝나는 시간 순서로 놓인다');
    await expect(guarantee()).toHaveFocus();

    // 묶음의 마지막 질문에서는 넘기기 단추가 다음 묶음을 부른다
    await userEvent.click(logic.getByRole('button', { name: /^처음 제출에서 무엇이.*, 선택$/ }));
    await expect(logic.getByRole('button', { name: '출력 질문으로' })).toBeInTheDocument();
  }}
/>

<Story
  name="NextThreadByName"
  beforeEach={() => writing.install()}
  play={async ({ canvas, canvasElement, userEvent }) => {
    // 문제 칸에서 Ctrl+Enter를 누르면 저장하고 빈 칸이 남은 입력 묶음의 빈 질문으로 간다
    await userEvent.type(
      await canvas.findByRole('textbox', { name: problemQuestion }),
      '끝나는 시간이 빠를수록 남는 시간이 넓다'
    );
    await userEvent.keyboard('{Control>}{Enter}{/Control}');

    const input = within(await canvas.findByRole('region', { name: '입력' }));

    await expect(canvas.queryByRole('region', { name: '문제' })).toBeNull();
    await expect(input.getByRole('textbox', { name: /입력 조건/ })).toHaveFocus();
    await expect(rule(canvasElement, '문제')).toHaveAttribute('aria-expanded', 'false');
    await expect(rule(canvasElement, '문제')).toHaveAccessibleName('문제, 질문 1개 중 1개 답함');
    await waitFor(() =>
      expect(writing.callsTo('PATCH', '/v1/records/record-1/answers')).toHaveLength(1)
    );
    await waitFor(() =>
      expect(canvas.getByRole('status')).toHaveTextContent('문제 질문 1개에 모두 답했어요.')
    );

    // 넘기기 단추는 다음 묶음의 이름을 부르고, 단축키를 알린다
    await expect(input.getByRole('button', { name: '로직 1 질문으로' })).toHaveAttribute(
      'aria-keyshortcuts',
      'Control+Enter Meta+Enter'
    );
  }}
/>

<Story
  name="PleaLeadsToBlank"
  beforeEach={() => writing.install()}
  play={async ({ canvas, canvasElement, userEvent }) => {
    await userEvent.click(await canvas.findByRole('button', { name: '입력 질문으로' }));

    const input = within(canvas.getByRole('region', { name: '입력' }));

    // 답한 질문을 펼쳐 둔 채로 접으려 하면, 모달을 닫은 뒤 빈 질문으로 데려간다
    await userEvent.click(input.getByRole('button', { name: /^입력을 담은 변수.*, 내 답:/ }));
    await userEvent.click(rule(canvasElement, '입력'));

    const dialog = await within(document.body).findByRole('alertdialog');

    await userEvent.click(within(dialog).getByRole('button', { name: '답하러 가기' }));
    await modalClosed();

    const blank = input.getByRole('textbox', { name: /입력 조건/ });

    await expect(blank.closest('li')).toHaveAttribute('aria-current', 'step');
    await expect(blank).toHaveFocus();
    await expect(blank).toHaveAttribute('aria-invalid', 'true');
  }}
/>

<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { expect, fn, waitFor, within } from 'storybook/test';
  import { reply } from '#lib/api/fake.js';
  import { localApi } from '#lib/api/local.js';
  import NewRecordForm from './NewRecordForm.svelte';

  const { Story } = defineMeta({
    title: 'Components/NewRecordForm',
    component: NewRecordForm,
    args: { oncreated: fn(), onsaved: fn() }
  });

  // 새 기록은 브라우저 안의 백엔드가 새 id로 만든다
  const created = localApi();

  const rejected = localApi([], [['POST /v1/records', reply({ detail: [] }, 422)]]);

  /** 모달이 닫히고 페이지가 다시 눌릴 때까지. bits-ui는 모달이 닫히고도 잠깐 body의 클릭을 막는다 */
  const modalClosed = () =>
    waitFor(() => {
      expect(document.querySelector('[role="alertdialog"]')).toBeNull();
      expect(document.body).not.toHaveStyle({ pointerEvents: 'none' });
    });
</script>

<Story
  name="KeyIdeaBeforeCode"
  beforeEach={() => created.install()}
  play={async ({ canvas, userEvent }) => {
    const submit = canvas.getByRole('button', { name: '블럭 나누기' });

    // 핵심 아이디어를 쓰기 전에는 코드 칸이 없다
    await expect(canvas.queryByLabelText(/맞은 풀이 코드/)).not.toBeInTheDocument();
    await expect(submit).toBeDisabled();

    await userEvent.type(canvas.getByLabelText(/어떤 문제인가요/), 'BOJ 1931 회의실 배정');
    await userEvent.type(canvas.getByLabelText(/핵심 아이디어/), '끝나는 시간이 빠른 회의부터');

    await expect(await canvas.findByLabelText(/맞은 풀이 코드/)).toBeInTheDocument();
    await expect(canvas.getByText('틀렸던 제출 코드는 받지 않아요.')).toBeInTheDocument();
    // 처음 제출에서 틀렸는지는 여기서 묻지 않는다 (블럭마다 표시한다)
    await expect(canvas.queryByRole('checkbox')).not.toBeInTheDocument();
    await expect(submit).toBeDisabled();
  }}
/>

<Story
  name="Submit"
  beforeEach={() => created.install()}
  play={async ({ canvas, userEvent, args }) => {
    await userEvent.type(canvas.getByLabelText(/어떤 문제인가요/), '  BOJ 1000 A+B ');
    await userEvent.type(canvas.getByLabelText(/핵심 아이디어/), '두 수를 더한다');
    await userEvent.type(
      await canvas.findByLabelText(/맞은 풀이 코드/),
      'a, b = map(int, input().split())  \nprint(a + b)'
    );
    await userEvent.selectOptions(canvas.getByLabelText('언어'), 'python');
    await userEvent.click(canvas.getByRole('button', { name: '블럭 나누기' }));

    // 브라우저에서 실제 모델로 나눈다. 처음에는 모델과 문법 파일을 받는다
    await waitFor(
      () => expect(args.oncreated).toHaveBeenCalledWith(expect.stringMatching(/^local-/)),
      {
        timeout: 15000
      }
    );

    const [call] = created.callsTo('POST', '/v1/records');

    const { questions, ...body } = JSON.parse(call.body);

    // 코드는 normalize되고(줄 끝 공백 제거, 끝 줄바꿈), 문장 번호로 블럭을 보낸다
    await expect(body).toEqual({
      problem: 'BOJ 1000 A+B',
      key_idea: '두 수를 더한다',
      code: 'a, b = map(int, input().split())\nprint(a + b)\n',
      language: 'python',
      initially_wrong: false,
      units: [
        { start: [1, 0], end: [1, 32], condition: false, loop: false, recursion: false },
        { start: [2, 0], end: [2, 12], condition: false, loop: false, recursion: false }
      ],
      blocks: [
        { kind: 'input', units: [0] },
        { kind: 'output', units: [1] }
      ]
    });

    // 질문도 브라우저가 블럭을 보고 만든다. 처음 제출에서 틀렸는지는 여기서 묻지 않고 블럭마다 표시한다
    await expect(questions.map((q: { kind: string }) => q.kind)).toEqual([
      'problem',
      'input_meaning',
      'input_condition',
      'output_meaning',
      'output_format',
      'varying'
    ]);
  }}
/>

<Story
  name="Unsplittable"
  beforeEach={() => created.install()}
  play={async ({ canvas, userEvent, args }) => {
    const body = within(document.body);

    await userEvent.type(canvas.getByLabelText(/어떤 문제인가요/), 'BOJ 2557');
    await userEvent.type(canvas.getByLabelText(/핵심 아이디어/), '출력한다');
    await userEvent.type(await canvas.findByLabelText(/맞은 풀이 코드/), 'print(1)');
    await userEvent.selectOptions(canvas.getByLabelText('언어'), 'python');
    await userEvent.click(canvas.getByRole('button', { name: '블럭 나누기' }));

    // 모델이 문장을 모두 none으로 보면 모달로 알리고, 아직 기록을 만들지 않는다
    const dialog = await body.findByRole('alertdialog', {}, { timeout: 15000 });

    await expect(dialog).toHaveTextContent(/나누지 못했어요|나눌 수 없었어요|나눌 수 없어요/);
    await userEvent.click(within(dialog).getByRole('button', { name: '직접 나누기' }));
    await modalClosed();

    // 저장하지 않은 편집 화면에서 블럭을 직접 만든다
    await expect(created.callsTo('POST', '/v1/records')).toHaveLength(0);
    await userEvent.click(canvas.getByRole('button', { name: '이대로 질문 받기' }));
    await expect(canvas.getByText('문장이 든 블럭이 하나는 있어야 해요.')).toBeInTheDocument();

    await userEvent.click(canvas.getByRole('button', { name: '1줄' }));
    await userEvent.click(canvas.getByRole('button', { name: '+ 로직 1' }));
    await userEvent.click(canvas.getByRole('button', { name: '이대로 질문 받기' }));

    // 블럭이 생긴 뒤에야 기록을 만들고, 바로 답을 쓰러 간다
    await waitFor(() =>
      expect(args.onsaved).toHaveBeenCalledWith(expect.stringMatching(/^local-/))
    );
    await expect(args.oncreated).not.toHaveBeenCalled();

    const [call] = created.callsTo('POST', '/v1/records');

    const sent = JSON.parse(call.body);

    await expect(sent.problem).toBe('BOJ 2557');
    await expect(sent.blocks).toEqual([{ kind: 'logic', units: [0] }]);
    await expect(sent.questions.map((q: { kind: string }) => q.kind)).toEqual([
      'problem',
      'logic',
      'varying'
    ]);
  }}
/>

<Story
  name="UnsplittableBack"
  beforeEach={() => created.install()}
  play={async ({ canvas, userEvent }) => {
    const body = within(document.body);

    await userEvent.type(canvas.getByLabelText(/어떤 문제인가요/), 'BOJ 2557');
    await userEvent.type(canvas.getByLabelText(/핵심 아이디어/), '출력한다');
    await userEvent.type(await canvas.findByLabelText(/맞은 풀이 코드/), 'print(1)');
    await userEvent.selectOptions(canvas.getByLabelText('언어'), 'python');
    await userEvent.click(canvas.getByRole('button', { name: '블럭 나누기' }));

    // 코드 고치기를 고르면 쓴 내용 그대로 폼으로 돌아간다
    const dialog = await body.findByRole('alertdialog', {}, { timeout: 15000 });

    await userEvent.click(within(dialog).getByRole('button', { name: '코드 고치기' }));
    await modalClosed();
    await expect(canvas.getByLabelText(/맞은 풀이 코드/)).toHaveValue('print(1)');
    await expect(created.callsTo('POST', '/v1/records')).toHaveLength(0);
  }}
/>

<Story
  name="Rejected"
  beforeEach={() => rejected.install()}
  play={async ({ canvas, userEvent, args }) => {
    await userEvent.type(canvas.getByLabelText(/어떤 문제인가요/), 'BOJ 1931');
    await userEvent.type(canvas.getByLabelText(/핵심 아이디어/), '그리디');
    await userEvent.type(await canvas.findByLabelText(/맞은 풀이 코드/), 'int n; cin >> n;');
    await userEvent.click(canvas.getByRole('button', { name: '블럭 나누기' }));

    await expect(
      await canvas.findByText('입력한 내용을 다시 확인해 주세요.', {}, { timeout: 15000 })
    ).toBeInTheDocument();
    await expect(args.oncreated).not.toHaveBeenCalled();
  }}
/>

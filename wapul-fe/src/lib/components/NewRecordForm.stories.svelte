<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { expect, fn, waitFor } from 'storybook/test';
  import { FakeApi, reply } from '#lib/api/fake.js';
  import { record } from '#lib/api/fixtures.js';
  import NewRecordForm from './NewRecordForm.svelte';

  const { Story } = defineMeta({
    title: 'Components/NewRecordForm',
    component: NewRecordForm,
    args: { oncreated: fn() }
  });

  const created = new FakeApi([['POST /v1/records', reply(record, 201)]]);

  const rejected = new FakeApi([['POST /v1/records', reply({ detail: [] }, 422)]]);
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
    await userEvent.click(canvas.getByRole('checkbox', { name: /처음 제출은 틀렸어요/ }));
    await userEvent.click(canvas.getByRole('button', { name: '블럭 나누기' }));

    // 브라우저에서 실제 모델로 나눈다. 처음에는 모델과 문법 파일을 받는다
    await waitFor(() => expect(args.oncreated).toHaveBeenCalledWith('record-1'), {
      timeout: 15000
    });

    const [call] = created.callsTo('POST', '/v1/records');

    const { questions, ...body } = JSON.parse(call.body);

    // 코드는 normalize되고(줄 끝 공백 제거, 끝 줄바꿈), 문장 번호로 블럭을 보낸다
    await expect(body).toEqual({
      problem: 'BOJ 1000 A+B',
      key_idea: '두 수를 더한다',
      code: 'a, b = map(int, input().split())\nprint(a + b)\n',
      language: 'python',
      initially_wrong: true,
      units: [
        { start: [1, 0], end: [1, 32], condition: false, loop: false, recursion: false },
        { start: [2, 0], end: [2, 12], condition: false, loop: false, recursion: false }
      ],
      blocks: [
        { kind: 'input', units: [0] },
        { kind: 'output', units: [1] }
      ]
    });

    // 질문도 브라우저가 블럭을 보고 만든다. 처음에 틀렸으니 달라진 점 질문이 끝에 붙는다
    await expect(questions.map((q: { kind: string }) => q.kind)).toEqual([
      'problem',
      'input_meaning',
      'input_condition',
      'output_meaning',
      'output_format',
      'varying',
      'revision'
    ]);
  }}
/>

<Story
  name="Unsplittable"
  beforeEach={() => created.install()}
  play={async ({ canvas, userEvent, args }) => {
    await userEvent.type(canvas.getByLabelText(/어떤 문제인가요/), 'BOJ 2557');
    await userEvent.type(canvas.getByLabelText(/핵심 아이디어/), '출력한다');
    await userEvent.type(await canvas.findByLabelText(/맞은 풀이 코드/), 'print(1)');
    await userEvent.selectOptions(canvas.getByLabelText('언어'), 'python');
    await userEvent.click(canvas.getByRole('button', { name: '블럭 나누기' }));

    // 모델이 문장을 모두 none으로 보면 기록을 만들지 않는다
    await expect(
      await canvas.findByText(
        /나누지 못했어요|나눌 수 없었어요|나눌 수 없어요/,
        {},
        { timeout: 15000 }
      )
    ).toBeInTheDocument();
    await expect(created.callsTo('POST', '/v1/records')).toHaveLength(0);
    await expect(args.oncreated).not.toHaveBeenCalled();
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

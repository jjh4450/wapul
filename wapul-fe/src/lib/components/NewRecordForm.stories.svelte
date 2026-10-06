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
    await userEvent.type(canvas.getByLabelText(/어떤 문제인가요/), '  BOJ 1931 회의실 배정 ');
    await userEvent.type(canvas.getByLabelText(/핵심 아이디어/), '끝나는 시간이 빠른 회의부터');
    await userEvent.type(await canvas.findByLabelText(/맞은 풀이 코드/), 'print(1)');
    await userEvent.selectOptions(canvas.getByLabelText('언어'), 'python');
    await userEvent.click(canvas.getByRole('checkbox', { name: /처음 제출은 틀렸어요/ }));
    await userEvent.click(canvas.getByRole('button', { name: '블럭 나누기' }));

    await waitFor(() => expect(args.oncreated).toHaveBeenCalledWith('record-1'));

    const [call] = created.callsTo('POST', '/v1/records');

    await expect(JSON.parse(call.body)).toEqual({
      problem: 'BOJ 1931 회의실 배정',
      key_idea: '끝나는 시간이 빠른 회의부터',
      code: 'print(1)',
      language: 'python',
      initially_wrong: true
    });
  }}
/>

<Story
  name="Rejected"
  beforeEach={() => rejected.install()}
  play={async ({ canvas, userEvent, args }) => {
    await userEvent.type(canvas.getByLabelText(/어떤 문제인가요/), 'BOJ 1931');
    await userEvent.type(canvas.getByLabelText(/핵심 아이디어/), '그리디');
    await userEvent.type(await canvas.findByLabelText(/맞은 풀이 코드/), 'print(1)');
    await userEvent.click(canvas.getByRole('button', { name: '블럭 나누기' }));

    await expect(await canvas.findByText('입력한 내용을 다시 확인해 주세요.')).toBeInTheDocument();
    await expect(args.oncreated).not.toHaveBeenCalled();
  }}
/>

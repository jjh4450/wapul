<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { expect, fn, waitFor } from 'storybook/test';
  import { FakeApi, reply } from '#lib/api/fake.js';
  import { record } from '#lib/api/fixtures.js';
  import BlockEditor from './BlockEditor.svelte';

  const { Story } = defineMeta({
    title: 'Components/BlockEditor',
    component: BlockEditor,
    args: { id: 'record-1', onsaved: fn() }
  });

  const editing = new FakeApi([
    ['GET /v1/records/:id', reply(record)],
    ['PUT /v1/records/:id/blocks', reply(record)]
  ]);

  const oneBlock = new FakeApi([
    ['GET /v1/records/:id', reply({ ...record, blocks: [record.blocks[1]] })]
  ]);

  const rejected = new FakeApi([
    ['GET /v1/records/:id', reply(record)],
    ['PUT /v1/records/:id/blocks', reply({ detail: 'overlap' }, 422)]
  ]);

  const missing = new FakeApi([['GET /v1/records/:id', reply({ detail: 'x' }, 404)]]);
</script>

<Story
  name="ProposedBlocks"
  beforeEach={() => editing.install()}
  play={async ({ canvas }) => {
    const kinds = await canvas.findAllByLabelText('블럭 종류');

    await expect(kinds.map((k) => (k as HTMLSelectElement).value)).toEqual([
      'input',
      'logic',
      'output'
    ]);
    await expect(canvas.getByText('문장 6개')).toBeInTheDocument();
    // 처음에는 첫 블럭이 골라져 있다
    await expect(canvas.getByRole('button', { name: '입력', pressed: true })).toBeInTheDocument();
  }}
/>

<Story
  name="MoveStatementsAndSave"
  beforeEach={() => editing.install()}
  play={async ({ canvas, userEvent, args }) => {
    // 새 로직 블럭은 출력 블럭 앞에 들어가고 골라진다
    await userEvent.click(await canvas.findByRole('button', { name: '블럭 더하기' }));
    await expect(canvas.getByRole('button', { name: '로직 2', pressed: true })).toBeInTheDocument();

    // sort 문장을 로직 1에서 새 블럭으로 옮긴다
    await userEvent.click(canvas.getAllByRole('button', { name: '9줄 문장' })[0]);
    await expect(canvas.getAllByText(/^문장 \d+개$/).map((e) => e.textContent)).toEqual([
      '문장 5개',
      '문장 5개',
      '문장 1개',
      '문장 1개'
    ]);

    // 출력 블럭을 고르고, 들어 있던 출력 문장을 다시 누르면 빠진다
    await userEvent.click(canvas.getByRole('button', { name: '출력' }));
    await userEvent.click(canvas.getByRole('button', { name: '15줄 문장' }));

    await userEvent.click(canvas.getByRole('button', { name: '이대로 질문 받기' }));
    await waitFor(() => expect(args.onsaved).toHaveBeenCalledOnce());

    const [call] = editing.callsTo('PUT', '/v1/records/record-1/blocks');

    const { blocks, questions } = JSON.parse(call.body);

    // 빈 출력 블럭은 보내지 않는다
    await expect(blocks).toEqual([
      { kind: 'input', units: [3, 4, 5, 6, 7] },
      { kind: 'logic', units: [9, 10, 11, 12, 13] },
      { kind: 'logic', units: [8] }
    ]);

    // 질문을 다시 만든다. 조건 문장이 든 로직 블럭에만 경계 질문이 붙고,
    // 그대로 남은 입력 블럭과 기록 단위 질문은 이전 문구와 답을 이어 쓴다
    await expect(questions.map((q: { kind: string }) => q.kind)).toEqual([
      'problem',
      'input_meaning',
      'input_condition',
      'logic',
      'boundary',
      'logic',
      'varying',
      'revision'
    ]);
    await expect(questions[1]).toEqual({
      kind: 'input_meaning',
      text: record.questions[1].text,
      answer: record.questions[1].answer,
      block: 0
    });
    await expect(questions[6].text).toBe(record.questions[7].text);
  }}
/>

<Story
  name="LastBlockStays"
  beforeEach={() => oneBlock.install()}
  play={async ({ canvas }) => {
    await expect(await canvas.findByRole('button', { name: '빼기' })).toBeDisabled();
  }}
/>

<Story
  name="Rejected"
  beforeEach={() => rejected.install()}
  play={async ({ canvas, userEvent, args }) => {
    await userEvent.click(await canvas.findByRole('button', { name: '이대로 질문 받기' }));

    await expect(await canvas.findByText('입력한 내용을 다시 확인해 주세요.')).toBeInTheDocument();
    await expect(args.onsaved).not.toHaveBeenCalled();
  }}
/>

<Story
  name="NotFound"
  beforeEach={() => missing.install()}
  play={async ({ canvas }) => {
    await expect(await canvas.findByText('찾을 수 없어요.')).toBeInTheDocument();
  }}
/>

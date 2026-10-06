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
    const names = await canvas.findAllByLabelText('블럭 이름');

    await expect(names).toHaveLength(3);
    await expect(names[0]).toHaveValue('입력 받기');
    await expect(names[1]).toHaveValue('회의 고르기');
    await expect(canvas.getAllByLabelText('시작 줄')[1]).toHaveValue(9);
    await expect(canvas.getAllByLabelText('끝 줄')[1]).toHaveValue(13);

    // 코드 옆에도 블럭 이름이 붙는다
    await expect(canvas.getByText('회의 고르기')).toBeInTheDocument();
  }}
/>

<Story
  name="EditAndSave"
  beforeEach={() => editing.install()}
  play={async ({ canvas, userEvent, args }) => {
    const [firstName] = await canvas.findAllByLabelText('블럭 이름');

    await userEvent.clear(firstName);
    await userEvent.type(firstName, '회의 읽기');
    await userEvent.selectOptions(canvas.getAllByLabelText('블럭 종류')[2], 'logic');

    await userEvent.click(canvas.getByRole('button', { name: '블럭 더하기' }));
    await expect(canvas.getAllByLabelText('블럭 이름')).toHaveLength(4);
    await expect(canvas.getAllByLabelText('블럭 이름')[3]).toHaveValue('새 블럭');

    await userEvent.click(canvas.getAllByRole('button', { name: '빼기' })[3]);
    await expect(canvas.getAllByLabelText('블럭 이름')).toHaveLength(3);

    await userEvent.click(canvas.getByRole('button', { name: '이대로 질문 받기' }));
    await waitFor(() => expect(args.onsaved).toHaveBeenCalledOnce());

    const [call] = editing.callsTo('PUT', '/v1/records/record-1/blocks');

    await expect(JSON.parse(call.body)).toEqual({
      blocks: [
        { kind: 'input', name: '회의 읽기', start_line: 4, end_line: 7 },
        { kind: 'logic', name: '회의 고르기', start_line: 9, end_line: 13 },
        { kind: 'logic', name: '결과 출력', start_line: 15, end_line: 16 }
      ]
    });
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

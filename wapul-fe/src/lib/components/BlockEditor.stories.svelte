<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { expect, fn, waitFor, within } from 'storybook/test';
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

  const creating = new FakeApi([['POST /v1/records', reply(record, 201)]]);

  const { problem, key_idea, language, code, units } = record;

  /** 저장하지 않은 새 기록 */
  const draft = { problem, key_idea, language, code, units, initially_wrong: false };

  /** 메뉴를 고른 뒤 페이지가 다시 눌릴 때까지. bits-ui는 메뉴가 닫히고도 잠깐 body의 클릭을 막는다 */
  const menuClosed = () =>
    waitFor(() => expect(document.body).not.toHaveStyle({ pointerEvents: 'none' }));
</script>

<Story
  name="ProposedBlocks"
  beforeEach={() => editing.install()}
  play={async ({ canvas }) => {
    // 범례가 블럭마다 색과 이름을 알려 준다
    await expect(
      (await canvas.findAllByRole('button', { name: /블럭 빼기$/ })).map((b) =>
        b.getAttribute('aria-label')
      )
    ).toEqual(['입력 블럭 빼기', '로직 1 블럭 빼기', '출력 블럭 빼기']);
    await expect(canvas.getByRole('button', { name: '되돌리기' })).toBeDisabled();
    await expect(canvas.getByRole('button', { name: '다시 하기' })).toBeDisabled();
  }}
/>

<Story
  name="DragIntoBlocksAndSave"
  beforeEach={() => editing.install()}
  play={async ({ canvas, userEvent, args }) => {
    // 줄 번호 하나를 누르면 그 줄의 문장을 고르고, 그 아래에 넣을 블럭을 고르는 창이 뜬다
    await userEvent.click(await canvas.findByRole('button', { name: '9줄' }));

    const picker = within(canvas.getByRole('group', { name: '고른 문장을 넣을 블럭' }));

    await expect(picker.getByText('문장 1개를')).toBeInTheDocument();

    // sort 문장을 새 로직 블럭으로. 로직 번호는 코드에 나오는 순서라 새 블럭이 로직 1이 된다
    await userEvent.click(picker.getByRole('button', { name: '+ 로직' }));
    await expect(canvas.queryByRole('group')).not.toBeInTheDocument();
    await expect(canvas.getByRole('button', { name: '로직 2 블럭 빼기' })).toBeInTheDocument();

    // 출력 문장을 끌어서 고르고 어느 블럭에도 넣지 않는다. 빈 출력 블럭은 사라진다
    await userEvent.pointer([
      { keys: '[MouseLeft>]', target: canvas.getByRole('button', { name: '15줄 문장' }) },
      { keys: '[/MouseLeft]' }
    ]);
    await userEvent.click(canvas.getByRole('button', { name: '블럭에서 빼기' }));
    await expect(canvas.queryByRole('button', { name: '출력 블럭 빼기' })).not.toBeInTheDocument();

    await userEvent.click(canvas.getByRole('button', { name: '이대로 질문 받기' }));
    await waitFor(() => expect(args.onsaved).toHaveBeenCalledOnce());

    const [call] = editing.callsTo('PUT', '/v1/records/record-1/blocks');

    const { blocks, questions } = JSON.parse(call.body);

    await expect(blocks).toEqual([
      { kind: 'input', units: [3, 4, 5, 6, 7] },
      { kind: 'logic', units: [8] },
      { kind: 'logic', units: [9, 10, 11, 12, 13] }
    ]);

    // 질문을 다시 만든다. 조건 문장이 든 로직 블럭에만 경계 질문이 붙고, 처음 제출에서 틀렸다는
    // 표시는 원래 로직 블럭을 따라가 그 블럭 질문 뒤에 달라진 점 질문이 붙는다.
    // 그대로 남은 입력 블럭과 기록 단위 질문은 이전 문구와 답을 이어 쓴다
    await expect(questions.map((q: { kind: string; block?: number }) => [q.kind, q.block])).toEqual(
      [
        ['problem', undefined],
        ['input_meaning', 0],
        ['input_condition', 0],
        ['logic', 1],
        ['logic', 2],
        ['boundary', 2],
        ['revision', 2],
        ['varying', undefined]
      ]
    );
    await expect(questions[1]).toEqual({
      kind: 'input_meaning',
      text: record.questions[1].text,
      answer: record.questions[1].answer,
      block: 0
    });
    await expect(questions[7].text).toBe(record.questions.find((q) => q.kind === 'varying')?.text);
  }}
/>

<Story
  name="UndoRedo"
  beforeEach={() => editing.install()}
  play={async ({ canvas, userEvent }) => {
    const blockNames = () =>
      canvas
        .getAllByRole('button', { name: /블럭 빼기$/ })
        .map((b) => b.getAttribute('aria-label'));

    await userEvent.click(await canvas.findByRole('button', { name: '로직 1 블럭 빼기' }));
    await expect(blockNames()).toEqual(['입력 블럭 빼기', '출력 블럭 빼기']);

    await userEvent.click(canvas.getByRole('button', { name: '되돌리기' }));
    await expect(blockNames()).toEqual(['입력 블럭 빼기', '로직 1 블럭 빼기', '출력 블럭 빼기']);

    await userEvent.click(canvas.getByRole('button', { name: '다시 하기' }));
    await expect(blockNames()).toEqual(['입력 블럭 빼기', '출력 블럭 빼기']);

    // 단축키: Ctrl+Z로 되돌리고 Ctrl+Shift+Z로 다시 한다
    await userEvent.keyboard('{Control>}z{/Control}');
    await expect(blockNames()).toHaveLength(3);
    await userEvent.keyboard('{Control>}{Shift>}z{/Shift}{/Control}');
    await expect(blockNames()).toHaveLength(2);
  }}
/>

<Story
  name="ChangeKind"
  beforeEach={() => editing.install()}
  play={async ({ canvas, userEvent, args }) => {
    const body = within(document.body);

    const blockNames = () =>
      canvas
        .getAllByRole('button', { name: /블럭 빼기$/ })
        .map((b) => b.getAttribute('aria-label'));

    // 출력을 로직으로 바꾸면 로직 블럭이 하나 는다
    await userEvent.click(await canvas.findByRole('button', { name: '출력 종류 바꾸기' }));
    await userEvent.click(await body.findByRole('menuitemradio', { name: '로직' }));
    await menuClosed();
    await expect(blockNames()).toEqual(['입력 블럭 빼기', '로직 1 블럭 빼기', '로직 2 블럭 빼기']);

    // 출력은 하나뿐이라, 로직 블럭을 출력으로 바꾸면 이미 있는 출력과 합친다
    await userEvent.click(canvas.getByRole('button', { name: '되돌리기' }));
    await userEvent.click(canvas.getByRole('button', { name: '로직 1 종류 바꾸기' }));
    await userEvent.click(await body.findByRole('menuitemradio', { name: '출력' }));
    await menuClosed();
    await expect(blockNames()).toEqual(['입력 블럭 빼기', '출력 블럭 빼기']);

    await userEvent.click(canvas.getByRole('button', { name: '이대로 질문 받기' }));
    await waitFor(() => expect(args.onsaved).toHaveBeenCalledOnce());

    const [call] = editing.callsTo('PUT', '/v1/records/record-1/blocks');

    await expect(JSON.parse(call.body).blocks).toEqual([
      { kind: 'input', units: [3, 4, 5, 6, 7] },
      { kind: 'output', units: [8, 9, 10, 11, 12, 13, 14] }
    ]);
  }}
/>

<Story
  name="MarkWrong"
  beforeEach={() => editing.install()}
  play={async ({ canvas, userEvent, args }) => {
    const body = within(document.body);

    // 처음 제출에서 틀렸다는 표시는 블럭 이름 메뉴에서 켜고 끈다. 범례에도 적힌다
    await expect(await canvas.findByText('· 처음엔 틀림')).toBeInTheDocument();
    await userEvent.click(canvas.getByRole('button', { name: '로직 1 종류 바꾸기' }));
    await userEvent.click(
      await body.findByRole('menuitemcheckbox', { name: '처음 제출에서 틀렸어요', checked: true })
    );
    await menuClosed();
    await expect(canvas.queryByText('· 처음엔 틀림')).not.toBeInTheDocument();

    await userEvent.click(canvas.getByRole('button', { name: '입력 종류 바꾸기' }));
    await userEvent.click(
      await body.findByRole('menuitemcheckbox', { name: '처음 제출에서 틀렸어요' })
    );
    await menuClosed();

    await userEvent.click(canvas.getByRole('button', { name: '이대로 질문 받기' }));
    await waitFor(() => expect(args.onsaved).toHaveBeenCalledOnce());

    const [call] = editing.callsTo('PUT', '/v1/records/record-1/blocks');

    const revisions = JSON.parse(call.body).questions.filter(
      (q: { kind: string }) => q.kind === 'revision'
    );

    await expect(revisions.map((q: { block: number }) => q.block)).toEqual([0]);
  }}
/>

<Story
  name="CancelSelection"
  beforeEach={() => editing.install()}
  play={async ({ canvas, userEvent }) => {
    // 줄 하나에 문장이 셋이면 셋을 고른다
    await userEvent.click(await canvas.findByRole('button', { name: '12줄' }));
    await expect(canvas.getByText('문장 3개를')).toBeInTheDocument();

    await userEvent.keyboard('{Escape}');
    await expect(canvas.queryByRole('group')).not.toBeInTheDocument();
    // 아무것도 바꾸지 않았으니 되돌릴 것도 없다
    await expect(canvas.getByRole('button', { name: '되돌리기' })).toBeDisabled();
  }}
/>

<Story
  name="NothingLeft"
  beforeEach={() => oneBlock.install()}
  play={async ({ canvas, userEvent, args }) => {
    await userEvent.click(await canvas.findByRole('button', { name: '로직 1 블럭 빼기' }));
    await userEvent.click(canvas.getByRole('button', { name: '이대로 질문 받기' }));

    await expect(canvas.getByText('문장이 든 블럭이 하나는 있어야 해요.')).toBeInTheDocument();
    await expect(args.onsaved).not.toHaveBeenCalled();
  }}
/>

<Story
  name="Draft"
  args={{ id: undefined, draft }}
  beforeEach={() => creating.install()}
  play={async ({ canvas, userEvent, args }) => {
    // 블럭 없이 시작하고, 블럭을 하나 이상 만들어 저장할 때 기록을 만든다
    await expect(canvas.queryByRole('button', { name: /블럭 빼기$/ })).not.toBeInTheDocument();
    await expect(canvas.getByText(/아직 저장하지 않았어요/)).toBeInTheDocument();

    await userEvent.click(canvas.getByRole('button', { name: '15줄' }));
    await userEvent.click(canvas.getByRole('button', { name: '+ 출력' }));
    await userEvent.click(canvas.getByRole('button', { name: '이대로 질문 받기' }));

    await waitFor(() => expect(args.onsaved).toHaveBeenCalledWith('record-1'));

    const [call] = creating.callsTo('POST', '/v1/records');

    const sent = JSON.parse(call.body);

    await expect(sent).toMatchObject({ ...draft, blocks: [{ kind: 'output', units: [14] }] });
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

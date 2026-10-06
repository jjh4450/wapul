<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { expect, fn, spyOn, waitFor, type MockInstance } from 'storybook/test';
  import { FakeApi, empty, reply } from '#lib/api/fake.js';
  import { groups, layouts, record, sharedRecord } from '#lib/api/fixtures.js';
  import RecordResult from './RecordResult.svelte';

  const { Story } = defineMeta({
    title: 'Components/RecordResult',
    component: RecordResult,
    args: { id: 'record-1', ondeleted: fn() }
  });

  function ownerApi(groupList = groups) {
    return new FakeApi([
      ['GET /v1/records/:id', reply(record)],
      ['GET /v1/records/:id/layouts', reply(layouts)],
      ['GET /v1/groups', reply(groupList)],
      ['PUT /v1/records/:id/groups', reply(['group-1'])],
      ['DELETE /v1/records/:id', empty()]
    ]);
  }

  const owner = ownerApi();

  const ownerWithoutGroups = ownerApi([]);

  const viewer = new FakeApi([
    ['GET /v1/records/:id', reply(sharedRecord)],
    ['GET /v1/records/:id/layouts', reply(layouts)]
  ]);

  const oddTitle = new FakeApi([
    ['GET /v1/records/:id', reply({ ...record, problem: 'A/B: 회의실?' })],
    ['GET /v1/records/:id/layouts', reply(layouts)],
    ['GET /v1/groups', reply(groups)]
  ]);

  // 브라우저 기능(클립보드, 파일 받기, 확인 창)은 story마다 갈아 끼우고 끝나면 되돌린다
  let clipboardWrite: MockInstance<Clipboard['writeText']>;

  let anchorClick: MockInstance<HTMLAnchorElement['click']>;

  function withBrowserStubs(api: FakeApi) {
    return () => {
      const restoreApi = api.install();

      clipboardWrite = spyOn(navigator.clipboard, 'writeText').mockResolvedValue();
      anchorClick = spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

      // 확인 창은 처음엔 취소, 그다음부터는 확인을 누른 것으로 한다
      const confirmDialog = spyOn(window, 'confirm')
        .mockReturnValueOnce(false)
        .mockReturnValue(true);

      return () => {
        restoreApi();
        clipboardWrite.mockRestore();
        anchorClick.mockRestore();
        confirmDialog.mockRestore();
      };
    };
  }
</script>

<Story
  name="JustFinished"
  args={{ done: true }}
  beforeEach={() => owner.install()}
  play={async ({ canvas, userEvent }) => {
    await expect(await canvas.findByText('글감이 완성됐어요!')).toBeInTheDocument();

    // 배치안 여러 개를 탭으로 바꿔 본다
    const codeFirst = canvas.getByText(/```cpp\s+int main\(\) \{\}/);

    await expect(codeFirst).toBeVisible();
    await userEvent.click(canvas.getByRole('tab', { name: '블럭마다 코드와 설명' }));
    await expect(canvas.getByText(/int n; cin >> n;/)).toBeVisible();
    await expect(codeFirst).not.toBeVisible();
  }}
/>

<Story
  name="CopyAndDownload"
  beforeEach={withBrowserStubs(owner)}
  play={async ({ canvas, userEvent }) => {
    await userEvent.click(await canvas.findByRole('tab', { name: '설명 먼저, 코드는 끝에' }));
    await userEvent.click(canvas.getByRole('button', { name: 'md 복사' }));

    // 고른 배치안의 md가 그대로 복사된다
    await expect(clipboardWrite).toHaveBeenCalledWith(layouts[2].markdown);
    await expect(await canvas.findByText('md를 복사했어요.')).toBeInTheDocument();

    await userEvent.click(canvas.getByRole('button', { name: 'md 받기' }));
    await expect(anchorClick.mock.contexts[0]).toHaveProperty(
      'download',
      'BOJ 1931 회의실 배정.md'
    );
  }}
/>

<Story
  name="FileNameIsSafe"
  beforeEach={withBrowserStubs(oddTitle)}
  play={async ({ canvas, userEvent }) => {
    await userEvent.click(await canvas.findByRole('button', { name: 'md 받기' }));

    // 파일 이름에 쓸 수 없는 글자는 _로 바꾼다
    await expect(anchorClick.mock.contexts[0]).toHaveProperty('download', 'A_B_ 회의실_.md');
  }}
/>

<Story
  name="ShareToGroup"
  beforeEach={() => owner.install()}
  play={async ({ canvas, userEvent }) => {
    await userEvent.click(await canvas.findByRole('checkbox', { name: 'PS 스터디' }));
    await expect(canvas.getByRole('checkbox', { name: '알고리즘 동아리' })).not.toBeChecked();
    await userEvent.click(canvas.getByRole('button', { name: '공유 저장' }));

    await expect(await canvas.findByText('공유 범위를 저장했어요.')).toBeInTheDocument();

    const [call] = owner.callsTo('PUT', '/v1/records/record-1/groups');

    await expect(JSON.parse(call.body)).toEqual({ group_ids: ['group-1'] });
  }}
/>

<Story
  name="NoGroupsYet"
  beforeEach={() => ownerWithoutGroups.install()}
  play={async ({ canvas }) => {
    await expect(await canvas.findByText(/속한 그룹이 없어요/)).toBeInTheDocument();
    await expect(canvas.getByRole('link', { name: '그룹 만들기·가입' })).toHaveAttribute(
      'href',
      '/groups'
    );
  }}
/>

<Story
  name="GroupMemberView"
  beforeEach={() => viewer.install()}
  play={async ({ canvas }) => {
    await expect(await canvas.findByText('BOJ 1931 회의실 배정')).toBeInTheDocument();
    await expect(canvas.getByRole('button', { name: 'md 받기' })).toBeInTheDocument();

    // 작성자가 아니면 고치기, 지우기, 공유가 없고 내 그룹 목록도 부르지 않는다
    await expect(canvas.queryByRole('link', { name: '답 고치기' })).not.toBeInTheDocument();
    await expect(canvas.queryByRole('button', { name: '지우기' })).not.toBeInTheDocument();
    await expect(canvas.queryByText('그룹에 공유')).not.toBeInTheDocument();
    await expect(viewer.callsTo('GET', '/v1/groups')).toHaveLength(0);
  }}
/>

<Story
  name="DeleteAfterConfirm"
  beforeEach={withBrowserStubs(owner)}
  play={async ({ canvas, userEvent, args }) => {
    const remove = await canvas.findByRole('button', { name: '지우기' });

    // 확인 창에서 취소하면 지우지 않는다
    await userEvent.click(remove);
    await expect(owner.callsTo('DELETE', '/v1/records/record-1')).toHaveLength(0);

    await userEvent.click(remove);
    await waitFor(() => expect(args.ondeleted).toHaveBeenCalledOnce());
    await expect(owner.callsTo('DELETE', '/v1/records/record-1')).toHaveLength(1);
  }}
/>

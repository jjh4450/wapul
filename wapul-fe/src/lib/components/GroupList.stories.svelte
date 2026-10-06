<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { expect, fn, waitFor } from 'storybook/test';
  import { FakeApi, reply } from '#lib/api/fake.js';
  import { groups } from '#lib/api/fixtures.js';
  import GroupList from './GroupList.svelte';

  const { Story } = defineMeta({
    title: 'Components/GroupList',
    component: GroupList,
    args: { onopen: fn() }
  });

  const listing = new FakeApi([
    ['GET /v1/groups', reply(groups)],
    ['POST /v1/groups', reply({ ...groups[0], id: 'group-new', name: '새 스터디' }, 201)],
    ['POST /v1/groups/join', reply(groups[1])]
  ]);

  const none = new FakeApi([['GET /v1/groups', reply([])]]);

  const badCode = new FakeApi([
    ['GET /v1/groups', reply([])],
    ['POST /v1/groups/join', reply({ detail: 'Invalid invite code' }, 404)]
  ]);
</script>

<Story
  name="MyGroups"
  beforeEach={() => listing.install()}
  play={async ({ canvas }) => {
    await expect(await canvas.findByText('PS 스터디')).toBeInTheDocument();
    await expect(canvas.getByText('멤버 3명')).toBeInTheDocument();
    await expect(canvas.getByText('그룹장')).toBeInTheDocument();
    await expect(canvas.getByText('멤버')).toBeInTheDocument();
    await expect(canvas.getByRole('link', { name: /PS 스터디/ })).toHaveAttribute(
      'href',
      '/groups/view?id=group-1'
    );
  }}
/>

<Story
  name="NoGroups"
  beforeEach={() => none.install()}
  play={async ({ canvas }) => {
    await expect(await canvas.findByText('아직 속한 그룹이 없어요.')).toBeInTheDocument();
  }}
/>

<Story
  name="CreateGroup"
  beforeEach={() => listing.install()}
  play={async ({ canvas, userEvent, args }) => {
    const create = canvas.getByRole('button', { name: '만들기' });

    await expect(create).toBeDisabled();
    await userEvent.type(canvas.getByLabelText('새 그룹 만들기'), ' 새 스터디 ');
    await userEvent.click(create);

    await waitFor(() => expect(args.onopen).toHaveBeenCalledWith('group-new'));

    const [call] = listing.callsTo('POST', '/v1/groups');

    await expect(JSON.parse(call.body)).toEqual({ name: '새 스터디' });
  }}
/>

<Story
  name="JoinWithInviteCode"
  beforeEach={() => listing.install()}
  play={async ({ canvas, userEvent, args }) => {
    await userEvent.type(canvas.getByLabelText('초대 코드로 가입'), ' wxyz6789 ');
    await userEvent.click(canvas.getByRole('button', { name: '가입' }));

    await waitFor(() => expect(args.onopen).toHaveBeenCalledWith('group-2'));

    const [call] = listing.callsTo('POST', '/v1/groups/join');

    await expect(JSON.parse(call.body)).toEqual({ invite_code: 'wxyz6789' });
  }}
/>

<Story
  name="UnknownInviteCode"
  beforeEach={() => badCode.install()}
  play={async ({ canvas, userEvent, args }) => {
    await userEvent.type(canvas.getByLabelText('초대 코드로 가입'), 'NOPE');
    await userEvent.click(canvas.getByRole('button', { name: '가입' }));

    await expect(await canvas.findByText('찾을 수 없어요.')).toBeInTheDocument();
    await expect(args.onopen).not.toHaveBeenCalled();
  }}
/>

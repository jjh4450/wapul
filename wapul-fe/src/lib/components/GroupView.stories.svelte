<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { expect, within } from 'storybook/test';
  import { FakeApi, reply } from '#lib/api/fake.js';
  import { groupDetail } from '#lib/api/fixtures.js';
  import GroupView from './GroupView.svelte';

  const { Story } = defineMeta({
    title: 'Components/GroupView',
    component: GroupView,
    args: { id: 'group-1' }
  });

  const shared = new FakeApi([['GET /v1/groups/:id', reply(groupDetail)]]);

  const nothingShared = new FakeApi([
    ['GET /v1/groups/:id', reply({ ...groupDetail, records: [] })]
  ]);

  const outsider = new FakeApi([['GET /v1/groups/:id', reply({ detail: 'x' }, 404)]]);
</script>

<Story
  name="SharedRecords"
  beforeEach={() => shared.install()}
  play={async ({ canvas }) => {
    await expect(await canvas.findByText('ABCD2345')).toBeInTheDocument();

    const members = within(canvas.getByRole('list'));

    await expect(members.getAllByRole('listitem')).toHaveLength(3);
    await expect(members.getByText('그룹장')).toBeInTheDocument();

    await expect(canvas.getByRole('link', { name: /BOJ 1931 회의실 배정/ })).toHaveAttribute(
      'href',
      '/records/view?id=record-1'
    );
  }}
/>

<Story
  name="NothingShared"
  beforeEach={() => nothingShared.install()}
  play={async ({ canvas }) => {
    await expect(await canvas.findByText('아직 공유된 기록이 없어요.')).toBeInTheDocument();
  }}
/>

<Story
  name="NotAMember"
  beforeEach={() => outsider.install()}
  play={async ({ canvas }) => {
    await expect(await canvas.findByText('찾을 수 없어요.')).toBeInTheDocument();
  }}
/>

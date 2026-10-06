<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { expect } from 'storybook/test';
  import { FakeApi, offline, pending, reply } from '#lib/api/fake.js';
  import { records } from '#lib/api/fixtures.js';
  import RecordList from './RecordList.svelte';

  // 화면 story는 가짜 API를 story마다 바꿔 끼우므로 여러 story를 한 페이지에 모으는 autodocs는 쓰지 않는다
  const { Story } = defineMeta({
    title: 'Components/RecordList',
    component: RecordList
  });

  const loading = new FakeApi([['GET /v1/records', pending]]);

  const empty = new FakeApi([['GET /v1/records', reply([])]]);

  const filled = new FakeApi([['GET /v1/records', reply(records)]]);

  const failing = new FakeApi([['GET /v1/records', reply({ detail: 'error' }, 500)]]);

  const disconnected = new FakeApi([['GET /v1/records', offline]]);
</script>

<Story
  name="Loading"
  beforeEach={() => loading.install()}
  play={async ({ canvas }) => {
    await expect(canvas.getByText('불러오는 중...')).toBeInTheDocument();
  }}
/>

<Story
  name="Empty"
  beforeEach={() => empty.install()}
  play={async ({ canvas }) => {
    await expect(await canvas.findByText(/아직 기록이 없어요/)).toBeInTheDocument();
  }}
/>

<Story
  name="WithRecords"
  beforeEach={() => filled.install()}
  play={async ({ canvas }) => {
    await expect(await canvas.findByText('BOJ 1931 회의실 배정')).toBeInTheDocument();
    await expect(canvas.getByText('BOJ 12865 평범한 배낭')).toBeInTheDocument();
    await expect(canvas.getByText('C++')).toBeInTheDocument();
    await expect(canvas.getByText('Python')).toBeInTheDocument();

    // 기록마다 이어서 쓰기와 결과물로 가는 링크가 있다
    const [write] = canvas.getAllByRole('link', { name: '이어서 쓰기' });

    const [view] = canvas.getAllByRole('link', { name: '결과물' });

    await expect(write).toHaveAttribute('href', '/records/write?id=record-1');
    await expect(view).toHaveAttribute('href', '/records/view?id=record-1');
  }}
/>

<Story
  name="ServerError"
  beforeEach={() => failing.install()}
  play={async ({ canvas }) => {
    await expect(await canvas.findByText('요청을 처리하지 못했어요. (500)')).toBeInTheDocument();
  }}
/>

<Story
  name="Offline"
  beforeEach={() => disconnected.install()}
  play={async ({ canvas }) => {
    await expect(await canvas.findByText('서버에 연결할 수 없어요.')).toBeInTheDocument();
  }}
/>

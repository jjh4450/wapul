import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { FakeApi, empty, offline, reply } from './fake.js';

// node에는 페이지 주소가 없어서 상대 경로 요청을 만들 수 없다. 클라이언트를 불러오기 전에 baseUrl을 정한다
vi.stubEnv('VITE_API_BASE_URL', 'http://api.test');

const { api } = await import('./client.js');

const fake = new FakeApi([
  [
    'GET /v1/groups',
    reply([{ id: 'g1', name: '스터디', invite_code: 'ABCD2345', role: 'owner', member_count: 1 }])
  ],
  ['PUT /v1/records/:id/groups', reply(['g1'])],
  ['PATCH /v1/records/:id/answers', empty()],
  ['GET /v1/records/r404', reply({ detail: 'x' }, 404)],
  ['GET /v1/records/r403', reply({ detail: 'x' }, 403)],
  ['GET /v1/records/r422', reply({ detail: 'x' }, 422)],
  ['GET /v1/records/r500', reply({ detail: 'x' }, 500)],
  ['GET /v1/records', offline]
]);

let restore: () => void;

beforeEach(() => {
  restore = fake.install();
});

afterEach(() => restore());

describe('api', () => {
  it('returns parsed data on success', async () => {
    expect(await api.listGroups()).toEqual({
      ok: true,
      data: [{ id: 'g1', name: '스터디', invite_code: 'ABCD2345', role: 'owner', member_count: 1 }]
    });
  });

  it('sends path params and body', async () => {
    await api.updateShares('r1', ['g1']);

    const [call] = fake.callsTo('PUT', '/v1/records/r1/groups');

    expect(JSON.parse(call.body)).toEqual({ group_ids: ['g1'] });
  });

  it('accepts an empty 204 response', async () => {
    expect(await api.saveAnswer('r1', 'q1', '답')).toEqual({ ok: true, data: null });
    expect(JSON.parse(fake.calls[0].body)).toEqual({
      answers: [{ question_id: 'q1', answer: '답' }]
    });
  });

  it.each([
    ['r404', '찾을 수 없어요.'],
    ['r403', '작성자만 바꿀 수 있어요.'],
    ['r422', '입력한 내용을 다시 확인해 주세요.'],
    ['r500', '요청을 처리하지 못했어요. (500)']
  ])('turns the error status of %s into a message', async (id, message) => {
    expect(await api.getRecord(id)).toEqual({ ok: false, message });
  });

  it('reports a network failure', async () => {
    expect(await api.listRecords()).toEqual({ ok: false, message: '서버에 연결할 수 없어요.' });
  });
});

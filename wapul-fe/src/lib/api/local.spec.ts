import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { RecordCreate } from './client.js';
import { record, sharedRecord } from './fixtures.js';

// node에는 페이지 주소가 없어서 상대 경로 요청을 만들 수 없다. 클라이언트를 불러오기 전에 baseUrl을 정한다
vi.stubEnv('VITE_API_BASE_URL', 'http://api.test');

const { api } = await import('./client.js');

const { localApi } = await import('./local.js');

const backend = localApi([record, { ...sharedRecord, id: 'shared-1' }]);

let restore: () => void;

beforeEach(() => {
  restore = backend.install();
});

afterEach(() => restore());

/** 화면이 보내는 꼴의 새 기록 */
const create: RecordCreate = {
  problem: record.problem,
  key_idea: record.key_idea,
  language: record.language,
  code: record.code,
  units: record.units,
  blocks: record.blocks.map(({ kind, units }) => ({ kind, units })),
  questions: [{ kind: 'logic', text: '왜 그런가요?', block: 1, answer: '' }]
};

describe('local backend', () => {
  it('serves the record flow the screens use, through the real api client', async () => {
    const created = await api.createRecord(create);

    if (!created.ok) throw new Error(created.message);

    const { id } = created.data;

    expect(id).toMatch(/^local-/);
    expect(created.data.questions[0].block_id).toBe(created.data.blocks[1].id);

    const listed = await api.listRecords();

    // 백엔드처럼 내 기록만, 최근에 고친 것부터
    expect(listed.ok && listed.data.map((r) => r.id)).toEqual([id, 'record-1']);

    // 블럭을 고치면 질문도 새로 정해진다
    const updated = await api.updateBlocks(
      id,
      [{ kind: 'logic', units: create.units.map((_, i) => i) }],
      [{ kind: 'logic', text: '왜 그런가요?', block: 0, answer: '' }]
    );

    if (!updated.ok) throw new Error(updated.message);

    const [question] = updated.data.questions;

    expect(question.block_id).toBe(updated.data.blocks[0].id);
    expect(await api.saveAnswer(id, question.id, '정렬했기 때문이다')).toEqual({
      ok: true,
      data: null
    });

    const layouts = await api.getLayouts(id);

    expect(layouts.ok && layouts.data[0].markdown).toContain('정렬했기 때문이다');
    expect(await api.deleteRecord(id)).toEqual({ ok: true, data: null });
    expect(await api.getRecord(id)).toEqual({ ok: false, message: '찾을 수 없어요.' });
  });

  it('starts over from its records on every install', async () => {
    expect(await api.deleteRecord('record-1')).toEqual({ ok: true, data: null });
    expect((await api.getRecord('record-1')).ok).toBe(false);
    restore();
    restore = backend.install();

    expect((await api.getRecord('record-1')).ok).toBe(true);
  });

  it('drops keys outside the contract like the backend', async () => {
    // 분할 결과의 문장에는 계약 밖의 키도 있다
    const units = record.units.map((u) => ({ ...u, text: 'x' }));

    const created = await api.createRecord({ ...create, units });

    expect(created.ok && created.data.units).toEqual(record.units);
  });

  it('lets only the owner change a record', async () => {
    const forbidden = { ok: false, message: '작성자만 바꿀 수 있어요.' };

    expect((await api.getRecord('shared-1')).ok).toBe(true);
    expect(await api.saveAnswer('shared-1', sharedRecord.questions[0].id, '답')).toEqual(forbidden);
    expect(await api.deleteRecord('shared-1')).toEqual(forbidden);
  });

  it('answers 500 instead of failing the connection when a handler breaks', async () => {
    // 화면은 보내지 않는 값이다(백엔드라면 422). 브라우저 안의 백엔드는 검사하지 않아 처리 중에 깨지는데,
    // 그때 연결 실패가 아니라 500으로 답한다
    expect(
      await api.updateBlocks(
        'record-1',
        [{ kind: 'logic', units: [0] }],
        [{ kind: 'logic', text: '왜?', block: 5, answer: '' }]
      )
    ).toEqual({ ok: false, message: '요청을 처리하지 못했어요. (500)' });
  });

  it('answers 404 for a record or question it does not have', async () => {
    const missing = { ok: false, message: '찾을 수 없어요.' };

    expect(await api.getRecord('local-nope')).toEqual(missing);
    expect(await api.saveAnswer('record-1', crypto.randomUUID(), '답')).toEqual(missing);
  });
});

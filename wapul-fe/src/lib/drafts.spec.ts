import { afterEach, describe, expect, it, vi } from 'vitest';
import type { RecordCreate, RecordOut } from '#lib/api/client.js';
import { record } from '#lib/api/fixtures.js';
import { create } from '#lib/api/local.js';
import { DRAFT_DAYS, clearForm, loadForm, openRecords, saveForm } from '#lib/drafts.js';

// node에는 페이지 주소가 없어서 상대 경로 요청을 만들 수 없다. 클라이언트를 불러오기 전에 baseUrl을 정한다
vi.stubEnv('VITE_API_BASE_URL', 'http://api.test');

const { api } = await import('#lib/api/client.js');

const { localApi } = await import('#lib/api/local.js');

const DAY = 24 * 60 * 60 * 1000;

/** 메모리에만 두는 저장소. capacity 글자를 넘게 담으면 브라우저처럼 QuotaExceededError를 던진다 */
function memoryStorage(capacity = Infinity): Storage {
  const items = new Map<string, string>();

  return {
    get length() {
      return items.size;
    },
    clear: () => items.clear(),
    getItem: (key) => items.get(key) ?? null,
    key: (index) => [...items.keys()][index] ?? null,
    removeItem: (key) => {
      items.delete(key);
    },
    setItem: (key, value) => {
      const used = [...items].reduce((sum, [k, v]) => (k === key ? sum : sum + v.length), 0);

      if (used + value.length > capacity) throw new DOMException('full', 'QuotaExceededError');

      items.set(key, value);
    }
  };
}

/** 화면이 보내는 꼴의 새 기록 */
const body: RecordCreate = {
  problem: record.problem,
  key_idea: record.key_idea,
  language: record.language,
  code: record.code,
  units: record.units,
  blocks: record.blocks.map(({ kind, units }) => ({ kind, units })),
  questions: [
    { kind: 'problem', text: '어떤 성질을 발견했나요?', block: null, answer: '' },
    { kind: 'logic', text: '왜 그런가요?', block: 1, answer: '' }
  ]
};

const answered = (r: RecordOut, answer: string): RecordOut => ({
  ...r,
  questions: r.questions.map((q) => ({ ...q, answer }))
});

let restore = () => {};

afterEach(() => restore());

describe('records kept in this browser', () => {
  it('serves records again after a reload, with the same ids and answers', async () => {
    const storage = memoryStorage();

    const store = await openRecords(storage);

    restore = localApi(store).install();

    const created = await api.createRecord(body);

    if (!created.ok) throw new Error(created.message);

    const { id, questions } = created.data;

    await api.saveAnswer(id, questions[1].id, '정렬했기 때문이다');
    await store.settled();
    restore();

    // 새로고침: 저장소에서 다시 꺼낸 기록으로 답한다
    const reopened = await openRecords(storage);

    restore = localApi(reopened).install();

    const again = await api.getRecord(id);

    expect(again).toEqual({ ok: true, data: store.get(id) });
    expect(again.ok && again.data.questions[1]).toMatchObject({
      id: questions[1].id,
      answer: '정렬했기 때문이다'
    });

    expect(await api.deleteRecord(id)).toEqual({ ok: true, data: null });
    expect(storage.length).toBe(0);
  });

  it(`forgets records left untouched for ${DRAFT_DAYS} days`, async () => {
    const storage = memoryStorage();

    const store = await openRecords(storage);

    const now = Date.now();

    const fresh = create(body);

    const stale = {
      ...create(body),
      updated_at: new Date(now - (DRAFT_DAYS + 1) * DAY).toISOString()
    };

    store.set(fresh.id, fresh);
    store.set(stale.id, stale);
    await store.settled();

    const reopened = await openRecords(storage, now);

    expect([...reopened.values()].map((r) => r.id)).toEqual([fresh.id]);
    expect(storage.length).toBe(1);
  });

  it('serves only values it can revive, and keeps the rest until they expire', async () => {
    const storage = memoryStorage();

    const store = await openRecords(storage);

    const kept = create(body);

    store.set(kept.id, kept);
    await store.settled();

    const value = new URLSearchParams(storage.getItem(`wapul:record:${kept.id}`) ?? '');

    const tampered = (name: string, text: string) => {
      const copy = new URLSearchParams(value);

      copy.set(name, text);

      return copy.toString();
    };

    // 이 앱이 열 수 없는 값: 깨진 본문, 질문 수와 맞지 않는 id, 앱이 만들지 않은 id.
    // 고친 앱은 열 수 있을지 모르니 만료될 때까지 둔다
    storage.setItem(`wapul:record:${create(body).id}`, tampered('body', 'v1.AAAA'));
    storage.setItem(`wapul:record:${create(body).id}`, tampered('questions', kept.questions[0].id));
    storage.setItem('wapul:record:record-1', value.toString());
    // 시각을 읽을 수 없으면 앱이 담은 값이 아니라서 지운다
    storage.setItem(`wapul:record:${create(body).id}`, tampered('updated', 'yesterday'));
    storage.setItem(`wapul:record:${create(body).id}`, '<script>');

    const reopened = await openRecords(storage);

    expect([...reopened.values()].map((r) => r.id)).toEqual([kept.id]);
    expect(storage.length).toBe(4);
  });

  it('keeps the latest change when an earlier write finishes late', async () => {
    const storage = memoryStorage();

    const store = await openRecords(storage);

    const first = create(body);

    store.set(first.id, answered(first, '처음 쓴 답'.repeat(200)));
    store.set(first.id, answered(first, '고친 답'));
    await store.settled();

    const reopened = await openRecords(storage);

    expect(reopened.get(first.id)?.questions[0].answer).toBe('고친 답');
  });

  it('does not bring back a record deleted while it was being written', async () => {
    const storage = memoryStorage();

    const store = await openRecords(storage);

    const doomed = create(body);

    store.set(doomed.id, doomed);
    store.delete(doomed.id);
    await store.settled();

    expect(storage.length).toBe(0);
  });

  it("takes another tab's changes so it does not write back older answers", async () => {
    const storage = memoryStorage();

    const tab = await openRecords(storage);

    const other = await openRecords(storage);

    const shared = create(body);

    tab.set(shared.id, shared);
    await tab.settled();

    const key = `wapul:record:${shared.id}`;

    // 다른 탭이 같은 기록을 열어 답을 쓴다
    await other.receive(key, storage.getItem(key));
    other.set(shared.id, answered(shared, '다른 탭의 답'));
    await other.settled();

    const newer = storage.getItem(key);

    // 이 탭이 예전 기록을 담기 시작한 뒤에 다른 탭의 값이 오면, 받은 값이 이긴다
    tab.set(shared.id, shared);
    await tab.receive(key, newer);
    await tab.settled();

    expect(tab.get(shared.id)?.questions[0]).toEqual({
      ...shared.questions[0],
      answer: '다른 탭의 답'
    });
    expect((await openRecords(storage)).get(shared.id)?.questions[0].answer).toBe('다른 탭의 답');

    // 다른 탭이 지운 기록은 이 탭에서도 사라진다
    await tab.receive(key, null);

    expect(tab.get(shared.id)).toBeUndefined();
  });

  it('does not bring back a record another tab deleted while an earlier value was being read', async () => {
    const storage = memoryStorage();

    const tab = await openRecords(storage);

    const other = await openRecords(storage);

    const doomed = create(body);

    other.set(doomed.id, doomed);
    await other.settled();

    const key = `wapul:record:${doomed.id}`;

    // 얼어 있던 탭이 깨어나 쌓인 이벤트를 한꺼번에 받는다: 담은 값, 그다음 지운 것
    const reading = tab.receive(key, storage.getItem(key));

    await tab.receive(key, null);
    await reading;

    expect(tab.get(doomed.id)).toBeUndefined();
  });

  it('keeps answering from memory when the storage is full', async () => {
    const store = await openRecords(memoryStorage(10));

    const big = create(body);

    store.set(big.id, big);
    await store.settled();

    expect(store.get(big.id)).toEqual(big);
  });
});

describe('new record form draft', () => {
  const draft = {
    problem: 'BOJ 1931',
    keyIdea: '끝나는 시간 순',
    code: '',
    language: 'python' as const
  };

  it('comes back as it was written', () => {
    const storage = memoryStorage();

    saveForm(storage, draft);

    expect(loadForm(storage)).toEqual(draft);

    clearForm(storage);

    expect(loadForm(storage)).toBeNull();
  });

  it('is not kept when every field is blank', () => {
    const storage = memoryStorage();

    saveForm(storage, draft);
    saveForm(storage, { ...draft, problem: ' ', keyIdea: '' });

    expect(storage.length).toBe(0);
  });

  it(`is forgotten ${DRAFT_DAYS} days after the last change, or when it is not ours`, () => {
    const storage = memoryStorage();

    const now = Date.now();

    saveForm(storage, draft, now - (DRAFT_DAYS + 1) * DAY);

    expect(loadForm(storage, now)).toBeNull();
    expect(storage.length).toBe(0);

    storage.setItem('wapul:new-record', 'problem=x&language=brainfuck&saved=' + String(now));

    expect(loadForm(storage, now)).toBeNull();
  });
});

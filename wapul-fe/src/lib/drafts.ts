/**
 * 쓰던 것을 이 브라우저(localStorage)에 담아 둔다. 새로고침하거나 브라우저를 다시 열어도 이어 쓰게 한다.
 *
 * - 백엔드를 끈 배포에서는 브라우저 안의 백엔드(api/local.ts)가 기록을 여기에 담는다. 기록의 내용은 저장
 *   링크와 같은 본문(share.ts의 packRecord)이고, 여기서는 시각과 블럭·질문 id만 더한다. 꺼낼 때도 링크를
 *   열 때와 같은 검사(unpackRecord)를 거친다.
 * - 새 기록 폼은 기록을 만들기 전까지 쓴 칸을 담는다.
 *
 * 값은 이름=값 꼴(URLSearchParams)로 담는다. 마지막으로 고친 뒤 DRAFT_DAYS가 지나면 지운다.
 * 저장소를 못 쓰는 브라우저(쿠키 차단 등)에서는 예전처럼 탭에만 둔다.
 */
import type { Language, RecordOut } from '#lib/api/client.js';
import { create, type RecordStore } from '#lib/api/local.js';
import { LANGUAGE_LABEL } from '#lib/study.js';

/** 마지막으로 고친 뒤 이만큼 지나면 지운다 */
export const DRAFT_DAYS = 7;

const TTL = DRAFT_DAYS * 24 * 60 * 60 * 1000;

const RECORD = 'wapul:record:';

const FORM = 'wapul:new-record';

const UUID = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}';

/** 브라우저 안의 백엔드가 붙이는 기록 id */
const LOCAL_ID = new RegExp(`^local-${UUID}$`);

const BLOCK_ID = new RegExp(`^${UUID}$`);

/** 앱이 다루는 언어인지 (LANGUAGE_LABEL의 키) */
function isLanguage(text: string | null): text is Language {
  return text !== null && Object.hasOwn(LANGUAGE_LABEL, text);
}

/** 담은 시각에서 TTL이 지났는지. 시각을 못 읽으면 지난 것으로 본다 */
const expired = (time: number, now: number) => !(now - time <= TTL);

let probed: Storage | null | undefined;

/** 이 브라우저의 저장소. 쿠키를 막았거나 저장소가 없으면 null */
export function browserStorage(): Storage | null {
  if (probed !== undefined) return probed;

  try {
    localStorage.setItem('wapul:probe', '');
    localStorage.removeItem('wapul:probe');
    probed = localStorage;
  } catch {
    probed = null;
  }

  return probed;
}

/** 쉼표로 이은 블럭·질문 id. id가 아닌 것이 섞였으면 null */
function ids(text: string | null): string[] | null {
  const list = text === null || text === '' ? [] : text.split(',');

  return list.every((id) => BLOCK_ID.test(id)) ? list : null;
}

/** 담는 값: 기록의 본문(링크와 같은 꼴)에 시각과 블럭·질문 id를 더한다 */
async function keepValue(record: RecordOut): Promise<string> {
  const { packRecord } = await import('#lib/share.js');

  return new URLSearchParams({
    created: record.created_at,
    updated: record.updated_at,
    blocks: record.blocks.map((b) => b.id).join(','),
    questions: record.questions.map((q) => q.id).join(','),
    body: await packRecord(record)
  }).toString();
}

/**
 * 담아 둔 값에서 기록을 되살린다. 깨졌거나 이 앱이 열 수 없는 값이면 null.
 * 값을 검사할 코드(share.ts)를 받지 못하면(오프라인, 새로 배포됨) 던진다
 */
async function revive(id: string, value: string): Promise<RecordOut | null> {
  const saved = new URLSearchParams(value);

  const createdAt = saved.get('created') ?? '';

  const updatedAt = saved.get('updated') ?? '';

  const blockIds = ids(saved.get('blocks'));

  const questionIds = ids(saved.get('questions'));

  const { unpackRecord } = await import('#lib/share.js');

  let body;

  try {
    body = await unpackRecord(saved.get('body') ?? '');
  } catch {
    return null;
  }

  if (
    !LOCAL_ID.test(id) ||
    [createdAt, updatedAt].some((time) => Number.isNaN(Date.parse(time))) ||
    blockIds?.length !== body.blocks.length ||
    questionIds?.length !== body.questions.length
  )
    return null;

  // 블럭·질문 id는 담을 때 것을 쓴다. 같은 기록을 연 다른 탭이 그 id로 답을 보낸다
  const record = create(body);

  const blockId = new Map(record.blocks.map((b, i) => [b.id, blockIds[i]]));

  return {
    ...record,
    id,
    created_at: createdAt,
    updated_at: updatedAt,
    blocks: record.blocks.map((b, i) => ({ ...b, id: blockIds[i] })),
    questions: record.questions.map((q, i) => ({
      ...q,
      id: questionIds[i],
      block_id: q.block_id === null ? null : (blockId.get(q.block_id) ?? null)
    }))
  };
}

/**
 * 브라우저 안의 백엔드가 기록을 두는 곳. 이 탭은 메모리의 기록으로 답하고, 고칠 때마다 저장소에 담는다.
 * 다른 탭이 고친 기록은 receive로 받아 와서, 같은 기록을 두 탭에서 고쳐도 다른 탭의 답을 예전 것으로
 * 덮어쓰지 않는다
 */
export class BrowserRecords implements RecordStore {
  readonly #storage: Storage;

  readonly #records: Map<string, RecordOut>;

  /**
   * 기록마다 마지막으로 시작한 쓰기나 받기. 본문을 줄이고 푸는 데 시간이 걸려서, 늦게 끝난 예전 것이 새 값을
   * 덮지 않게 한다
   */
  readonly #turns = new Map<string, number>();

  readonly #writing = new Set<Promise<void>>();

  constructor(storage: Storage, records: RecordOut[]) {
    this.#storage = storage;
    this.#records = new Map(records.map((r) => [r.id, r]));
  }

  get(id: string): RecordOut | undefined {
    return this.#records.get(id);
  }

  values(): Iterable<RecordOut> {
    return this.#records.values();
  }

  set(id: string, record: RecordOut): void {
    this.#records.set(id, record);

    const writing = this.#write(id, record, this.#turn(id));

    this.#writing.add(writing);
    void writing.then(() => this.#writing.delete(writing));
  }

  delete(id: string): void {
    this.#records.delete(id);
    this.#turn(id);
    this.#storage.removeItem(RECORD + id);
  }

  /** 담는 중인 기록이 모두 담길 때까지 */
  async settled(): Promise<void> {
    await Promise.all(this.#writing);
  }

  /** 다른 탭이 담거나 지운 기록을 받는다 (storage 이벤트의 key와 newValue) */
  async receive(key: string | null, value: string | null): Promise<void> {
    if (key === null || !key.startsWith(RECORD)) return;

    const id = key.slice(RECORD.length);

    // 이 탭이 담던 예전 값이 받은 값을 덮지 않게 한다
    const turn = this.#turn(id);

    if (value === null) {
      this.#records.delete(id);

      return;
    }

    const record = await revive(id, value).catch(() => null);

    // 푸는 사이에 더 새 값을 받았거나(지운 것 포함) 이 탭이 고쳤으면 버린다
    if (record !== null && this.#turns.get(id) === turn) this.#records.set(id, record);
  }

  #turn(id: string): number {
    const turn = (this.#turns.get(id) ?? 0) + 1;

    this.#turns.set(id, turn);

    return turn;
  }

  async #write(id: string, record: RecordOut, turn: number): Promise<void> {
    try {
      const value = await keepValue(record);

      if (this.#turns.get(id) === turn) this.#storage.setItem(RECORD + id, value);
    } catch {
      // 자리가 모자라면 이 탭에만 둔다. 기록 하나가 몇 KB라 DRAFT_DAYS 안에 다 차기는 어렵다
    }
  }
}

/**
 * 담아 둔 기록을 꺼낸다. 만료된 것은 지운다. 되살리지 못한 값은 지우지 않고 만료될 때까지 둔다: 이 앱이 못
 * 여는 값이라도 고친 앱은 열 수 있다
 */
export async function openRecords(storage: Storage, now = Date.now()): Promise<BrowserRecords> {
  const keys = Array.from({ length: storage.length }, (_, i) => storage.key(i)).filter(
    (key): key is string => key?.startsWith(RECORD) ?? false
  );

  const records: RecordOut[] = [];

  for (const key of keys) {
    const value = storage.getItem(key) ?? '';

    if (expired(Date.parse(new URLSearchParams(value).get('updated') ?? ''), now)) {
      storage.removeItem(key);

      continue;
    }

    try {
      const record = await revive(key.slice(RECORD.length), value);

      if (record !== null) records.push(record);
    } catch {
      // 검사할 코드를 받지 못했다. 앱은 띄우고, 담긴 것은 그대로 둔 채 이번에는 꺼낸 것까지만 쓴다
      break;
    }
  }

  return new BrowserRecords(storage, records);
}

/** 백엔드를 끈 배포가 기록을 두는 곳. 다른 탭이 고친 기록도 받아 온다. 저장소를 못 쓰면 null */
export async function browserRecords(): Promise<BrowserRecords | null> {
  const storage = browserStorage();

  if (storage === null) return null;

  const records = await openRecords(storage);

  addEventListener('storage', (event) => {
    if (event.storageArea === storage) void records.receive(event.key, event.newValue);
  });

  return records;
}

/** 새 기록 폼에 쓰던 칸 */
export type FormDraft = { problem: string; keyIdea: string; code: string; language: Language };

/** 쓰던 새 기록 폼. 없거나 만료됐으면 null */
export function loadForm(storage: Storage | null, now = Date.now()): FormDraft | null {
  const value = storage?.getItem(FORM) ?? null;

  if (value === null) return null;

  const saved = new URLSearchParams(value);

  const language = saved.get('language');

  if (!isLanguage(language) || expired(Number(saved.get('saved')), now)) {
    storage?.removeItem(FORM);

    return null;
  }

  return {
    problem: saved.get('problem') ?? '',
    keyIdea: saved.get('key_idea') ?? '',
    code: saved.get('code') ?? '',
    language
  };
}

/** 쓰는 대로 담는다. 칸이 모두 비면 지운다 */
export function saveForm(storage: Storage | null, draft: FormDraft, now = Date.now()): void {
  if (storage === null) return;

  if ([draft.problem, draft.keyIdea, draft.code].every((text) => text.trim() === '')) {
    storage.removeItem(FORM);

    return;
  }

  try {
    storage.setItem(
      FORM,
      new URLSearchParams({
        problem: draft.problem,
        key_idea: draft.keyIdea,
        code: draft.code,
        language: draft.language,
        saved: String(now)
      }).toString()
    );
  } catch {
    // 자리가 모자라면 담지 않는다. 쓰던 칸은 화면에 그대로 있다
  }
}

/** 기록을 만들었거나 새로 쓰기로 했을 때 */
export function clearForm(storage: Storage | null): void {
  storage?.removeItem(FORM);
}

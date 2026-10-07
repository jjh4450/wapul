import createClient from 'openapi-fetch';
import type { components, paths } from './schema';

type Schemas = components['schemas'];

export type Language = Schemas['Language'];

export type BlockKind = Schemas['BlockKind'];

export type QuestionKind = Schemas['QuestionKind'];

export type Unit = Schemas['Unit'];

/** 문장의 위치만 */
export type Span = Pick<Unit, 'start' | 'end'>;

export type BlockIn = Schemas['BlockIn'];

export type BlockOut = Schemas['BlockOut'];

export type QuestionIn = Schemas['QuestionIn'];

export type QuestionOut = Schemas['QuestionOut'];

export type RecordCreate = Schemas['RecordCreate'];

export type RecordOut = Schemas['RecordOut'];

export type RecordSummary = Schemas['RecordSummary'];

export type LayoutOut = Schemas['LayoutOut'];

export type GroupOut = Schemas['GroupOut'];

export type GroupDetail = Schemas['GroupDetail'];

export type Result<T> = { ok: true; data: T } | { ok: false; message: string };

// 개발 중에는 빈 baseUrl로 두고 vite 프록시가 /v1 요청을 백엔드로 넘긴다.
// fetch는 호출할 때마다 globalThis에서 읽는다. story와 테스트가 가짜 API(fake.ts)로 바꿔 끼울 수 있게 하려는 것.
const client = createClient<paths>({
  baseUrl: import.meta.env.VITE_API_BASE_URL ?? '',
  fetch: (request) => globalThis.fetch(request)
});

function describe(status: number): string {
  if (status === 404) return '찾을 수 없어요.';

  if (status === 403) return '작성자만 바꿀 수 있어요.';

  if (status === 422) return '입력한 내용을 다시 확인해 주세요.';

  return `요청을 처리하지 못했어요. (${status})`;
}

async function call<T>(request: Promise<{ data?: T; response: Response }>): Promise<Result<T>> {
  try {
    const { data, response } = await request;

    if (!response.ok || data === undefined)
      return { ok: false, message: describe(response.status) };

    return { ok: true, data };
  } catch {
    return { ok: false, message: '서버에 연결할 수 없어요.' };
  }
}

async function callEmpty(request: Promise<{ response: Response }>): Promise<Result<null>> {
  try {
    const { response } = await request;

    if (!response.ok) return { ok: false, message: describe(response.status) };

    return { ok: true, data: null };
  } catch {
    return { ok: false, message: '서버에 연결할 수 없어요.' };
  }
}

const byId = (id: string) => ({ params: { path: { record_id: id } } });

export const api = {
  listRecords: () => call(client.GET('/v1/records')),
  createRecord: (body: RecordCreate) => call(client.POST('/v1/records', { body })),
  getRecord: (id: string) => call(client.GET('/v1/records/{record_id}', byId(id))),
  deleteRecord: (id: string) => callEmpty(client.DELETE('/v1/records/{record_id}', byId(id))),
  updateBlocks: (id: string, blocks: BlockIn[], questions: QuestionIn[]) =>
    call(
      client.PUT('/v1/records/{record_id}/blocks', { ...byId(id), body: { blocks, questions } })
    ),
  saveAnswer: (id: string, questionId: string, answer: string) =>
    callEmpty(
      client.PATCH('/v1/records/{record_id}/answers', {
        ...byId(id),
        body: { answers: [{ question_id: questionId, answer }] }
      })
    ),
  getLayouts: (id: string) => call(client.GET('/v1/records/{record_id}/layouts', byId(id))),
  updateShares: (id: string, groupIds: string[]) =>
    call(
      client.PUT('/v1/records/{record_id}/groups', { ...byId(id), body: { group_ids: groupIds } })
    ),
  listGroups: () => call(client.GET('/v1/groups')),
  createGroup: (name: string) => call(client.POST('/v1/groups', { body: { name } })),
  joinGroup: (inviteCode: string) =>
    call(client.POST('/v1/groups/join', { body: { invite_code: inviteCode } })),
  getGroup: (id: string) =>
    call(client.GET('/v1/groups/{group_id}', { params: { path: { group_id: id } } }))
};

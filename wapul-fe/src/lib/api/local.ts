/**
 * 브라우저 안의 백엔드. 기록 API(/v1/records)를 메모리에서 백엔드(app/api/v1/records.py)처럼 답한다.
 *
 * 백엔드를 끈 배포(hooks.client.ts)와 story·테스트가 같이 쓰므로, story가 보는 동작이 배포되는 동작이다.
 * 요청은 같은 계약 타입으로 묶인 API 클라이언트에서만 와서 런타임에 다시 검사하지 않는다. 대신 route마다
 * 본문과 답을 openapi에서 생성한 타입(schema.ts)에 묶어, 계약이 바뀌면 타입 검사(pnpm check)에서 걸린다.
 * 누구나 만들 수 있는 링크는 여는 쪽(share.ts)이 검사한다. 기록은 새로고침하면 사라지고, 그룹은 없다.
 */
import { buildLayouts } from '#lib/layouts.js';
import type { BlockIn, QuestionIn, RecordCreate, RecordOut, RecordSummary } from './client.js';
import { FakeApi, type FakeHandler } from './fake.js';
import type { paths } from './schema';

type Method = 'get' | 'post' | 'put' | 'patch' | 'delete';

/** 계약에 있는 경로·메서드의 operation. 계약에 없는 메서드면 never라서 route를 만들 수 없다 */
type Operation<P extends keyof paths, M extends Method> = Exclude<paths[P][M], undefined>;

type RequestBody<O> = O extends { requestBody: { content: { 'application/json': infer B } } }
  ? B
  : undefined;

type Responses<O> = O extends { responses: infer R } ? R : never;

/** 응답 본문. 본문이 없는 응답(204)은 null */
type ResponseBody<R> = R extends { content: { 'application/json': infer B } } ? B : null;

/** 계약에는 적히지 않았지만 백엔드가 내는 실패: 없는 기록(404), 작성자가 아님(403) */
class Failure {
  constructor(readonly status: 403 | 404) {}
}

/**
 * 계약에 묶인 route. 본문은 그 경로·메서드의 requestBody 타입, 답은 그 상태의 응답 타입이다.
 * 본문 JSON은 같은 타입으로 보낸 클라이언트가 만든 것이라 타입만 붙인다
 */
function route<
  P extends keyof paths,
  M extends Method,
  S extends keyof Responses<Operation<P, M>> & number
>(
  method: M,
  path: P,
  status: S,
  handler: (request: {
    id: string;
    body: RequestBody<Operation<P, M>>;
  }) => ResponseBody<Responses<Operation<P, M>>[S]> | Failure
): [string, FakeHandler] {
  return [
    `${method.toUpperCase()} ${path.replaceAll(/\{\w+\}/g, ':id')}`,
    (call) => {
      let reply;

      // 백엔드처럼 처리 중에 난 오류는 500으로 답한다. 던지면 화면에는 연결 실패로 보인다
      try {
        reply = handler({
          id: call.path.split('/')[3],
          body: call.body === '' ? undefined : JSON.parse(call.body)
        });
      } catch {
        return new Response(null, { status: 500 });
      }

      if (reply instanceof Failure) return new Response(null, { status: reply.status });

      return reply === null ? new Response(null, { status }) : Response.json(reply, { status });
    }
  ];
}

/** 블럭과 질문을 통째로 바꾼다. 백엔드처럼 새 id를 붙이고 블럭의 문장은 순서대로 둔다 */
function withBlocks(record: RecordOut, blocks: BlockIn[], questions: QuestionIn[]): RecordOut {
  const made = blocks.map((b) => ({
    id: crypto.randomUUID(),
    kind: b.kind,
    units: [...b.units].sort((x, y) => x - y)
  }));

  return {
    ...record,
    updated_at: new Date().toISOString(),
    blocks: made,
    questions: questions.map((q) => ({
      id: crypto.randomUUID(),
      block_id: q.block == null ? null : made[q.block].id,
      kind: q.kind,
      text: q.text,
      answer: q.answer
    }))
  };
}

function create(body: RecordCreate): RecordOut {
  const now = new Date().toISOString();

  const record: RecordOut = {
    // 백엔드가 준 id와 섞이지 않게 접두사를 붙인다
    id: `local-${crypto.randomUUID()}`,
    problem: body.problem,
    key_idea: body.key_idea,
    language: body.language,
    owner_name: '나',
    created_at: now,
    updated_at: now,
    code: body.code,
    // 백엔드처럼 계약 밖의 키는 버린다 (분할 결과의 문장에는 다른 키도 있다)
    units: body.units.map(({ start, end, condition, loop, recursion }) => ({
      start,
      end,
      condition,
      loop,
      recursion
    })),
    is_owner: true,
    group_ids: [],
    blocks: [],
    questions: []
  };

  return withBlocks(record, body.blocks, body.questions);
}

function summary(record: RecordOut): RecordSummary {
  const { id, problem, key_idea, language, owner_name, created_at, updated_at } = record;

  return { id, problem, key_idea, language, owner_name, created_at, updated_at };
}

function recordRoutes(records: Map<string, RecordOut>): [string, FakeHandler][] {
  /** 경로의 기록을 넘긴다. 고치는 요청은 작성자만 (백엔드의 _get_own) */
  const withRecord = <T>(id: string, own: boolean, use: (record: RecordOut) => T) => {
    const record = records.get(id);

    if (record === undefined) return new Failure(404);

    return own && !record.is_owner ? new Failure(403) : use(record);
  };

  const keep = (record: RecordOut) => {
    records.set(record.id, record);

    return record;
  };

  return [
    // 백엔드의 list_my_records처럼 내 기록만
    route('get', '/v1/records', 200, () =>
      [...records.values()]
        .filter((r) => r.is_owner)
        .sort((a, b) => b.updated_at.localeCompare(a.updated_at))
        .map(summary)
    ),
    route('post', '/v1/records', 201, ({ body }) => keep(create(body))),
    route('get', '/v1/records/{record_id}', 200, ({ id }) => withRecord(id, false, (r) => r)),
    route('get', '/v1/records/{record_id}/layouts', 200, ({ id }) =>
      withRecord(id, false, buildLayouts)
    ),
    route('put', '/v1/records/{record_id}/blocks', 200, ({ id, body }) =>
      withRecord(id, true, (r) => keep(withBlocks(r, body.blocks, body.questions)))
    ),
    route('patch', '/v1/records/{record_id}/answers', 204, ({ id, body }) =>
      withRecord(id, true, (r) => {
        const answers = new Map(body.answers.map((a) => [a.question_id, a.answer]));

        if ([...answers.keys()].some((qid) => !r.questions.some((q) => q.id === qid)))
          return new Failure(404);

        keep({
          ...r,
          updated_at: new Date().toISOString(),
          questions: r.questions.map((q) => ({ ...q, answer: answers.get(q.id) ?? q.answer }))
        });

        return null;
      })
    ),
    route('delete', '/v1/records/{record_id}', 204, ({ id }) =>
      withRecord(id, true, (r) => {
        records.delete(r.id);

        return null;
      })
    )
  ];
}

/**
 * 브라우저 안의 백엔드를 끼운 가짜 API. records로 시작하고, install할 때마다 그 상태로 돌아간다.
 * overrides는 먼저 맞춰 보는 route다. story가 불러오는 중·오류나 그룹 응답을 정할 때 쓴다
 */
export function localApi(
  records: RecordOut[] = [],
  overrides: [string, FakeHandler][] = []
): FakeApi {
  return new FakeApi(() => [...overrides, ...recordRoutes(new Map(records.map((r) => [r.id, r])))]);
}

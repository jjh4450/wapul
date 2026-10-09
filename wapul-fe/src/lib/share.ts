/**
 * 기록을 링크 하나에 담는다. 백엔드가 없을 때는 링크가 곧 저장소다.
 *
 * 링크는 /share#v1.<본문>. 본문은 기록(RecordCreate)의 JSON을 deflate(LZ77 계열)로 줄인 base64url이다.
 * #뒤는 서버로 가지 않는다. v1은 나중에 형식이 바뀌어도 예전 링크를 알아보려고 붙인다: 계약이 바뀌어
 * 이미 건넨 링크가 열리지 않게 되면(share.spec.ts의 저장해 둔 링크 테스트가 깨진다) v1의 꼴을 고정해
 * 두고 지금 꼴로 옮기는 코드를 더한다. 백엔드가 없을 때는 그 링크가 기록의 유일한 사본이다.
 *
 * 링크는 누구나 만들 수 있어서, 앱에서 런타임에 값을 검사하는 곳은 여기뿐이다. 크기를 제한하며 풀고,
 * 백엔드가 받는 값만 받는다: API 계약(openapi.json의 RecordCreate)과 문장·블럭 규칙(app/api/v1/records.py).
 */
import { Validator } from '@cfworker/json-schema';
import type {
  BlockIn,
  QuestionIn,
  RecordCreate,
  RecordOut,
  Result,
  Unit
} from '#lib/api/client.js';

const PREFIX = 'v1.';

/** 본문 글자 수와 푼 JSON 바이트 수 한도. 작은 링크가 아주 큰 내용으로 풀리는 것을 막는다 */
const MAX_PAYLOAD = 400_000;

const MAX_JSON = 4_000_000;

/** 배치안이 블럭마다 다시 싣는 코드 글자 수 한도. 한 줄에 블럭이 몰리면 그 줄이 블럭 수만큼 반복된다 */
const MAX_BLOCK_CODE = 4_000_000;

/** 기록을 다시 만들 때 보내는 꼴. 질문은 블럭 id 대신 블럭 순번으로 가리킨다 */
function toCreate(record: RecordOut): RecordCreate {
  const position = new Map(record.blocks.map((b, i) => [b.id, i]));

  return {
    problem: record.problem,
    key_idea: record.key_idea,
    language: record.language,
    code: record.code,
    units: record.units,
    blocks: record.blocks.map(({ kind, units }) => ({ kind, units })),
    questions: record.questions.map(({ kind, text, answer, block_id }) => ({
      kind,
      text,
      answer,
      block: block_id === null ? null : position.get(block_id)
    }))
  };
}

let contract: Validator | undefined;

/** API 계약의 RecordCreate에 맞는지 (vite.config.ts가 넣은 스키마). 검사기는 처음 쓸 때 만든다 */
function isRecordCreate(value: unknown): value is RecordCreate {
  contract ??= new Validator(
    { ...__CONTRACT__, $ref: '#/components/schemas/RecordCreate' },
    '2020-12'
  );

  return contract.validate(value).valid;
}

/** 문장은 코드 안에 있고, 순서대로 겹치지 않는다. 칸은 백엔드처럼 글자(코드 포인트)로 센다 */
function unitsFit(code: string, units: Unit[]): boolean {
  const lengths = code.split('\n').map((line) => [...line].length);

  const inside = ([line, col]: number[]) =>
    line >= 1 && line <= lengths.length && col >= 0 && col <= lengths[line - 1];

  const before = (a: number[], b: number[]) => a[0] < b[0] || (a[0] === b[0] && a[1] < b[1]);

  let previous = [1, 0];

  for (const { start, end } of units) {
    if (!inside(start) || !inside(end) || before(start, previous) || !before(start, end))
      return false;

    previous = end;
  }

  return true;
}

/** 문장 번호는 범위 안에 있고 한 블럭에만 든다. 질문은 있는 블럭을 가리킨다 */
function blocksFit(unitCount: number, blocks: BlockIn[], questions: QuestionIn[]): boolean {
  const units = blocks.flatMap((b) => b.units);

  return (
    units.every((u) => u >= 0 && u < unitCount) &&
    new Set(units).size === units.length &&
    questions.every((q) => q.block == null || (q.block >= 0 && q.block < blocks.length))
  );
}

/** 배치안(layouts.ts)이 블럭마다 싣는 줄의 글자 수 합. 문장과 블럭이 맞는 기록에만 쓴다 */
function blockCodeSize({ code, units, blocks }: RecordCreate): number {
  const lengths = code.split('\n').map((line) => line.length + 1);

  let total = 0;

  for (const block of blocks) {
    const covered = new Set<number>();

    for (const i of block.units)
      for (let line = units[i].start[0]; line <= units[i].end[0]; line++) covered.add(line);

    for (const line of covered) total += lengths[line - 1];
  }

  return total;
}

function toBase64Url(bytes: Uint8Array): string {
  let binary = '';

  // 한 번에 펼치면 큰 기록에서 호출 스택이 넘친다
  for (let i = 0; i < bytes.length; i += 0x8000)
    binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));

  return btoa(binary).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
}

function fromBase64Url(text: string): Uint8Array<ArrayBuffer> {
  if (!/^[A-Za-z0-9_-]+$/.test(text)) throw new Error('Not base64url');

  return Uint8Array.from(atob(text.replaceAll('-', '+').replaceAll('_', '/')), (c) =>
    c.charCodeAt(0)
  );
}

/** 지나간 바이트가 max를 넘으면 스트림을 멈춘다. 앞 단계(압축 풀기)도 함께 멈춘다 */
function capped(max: number): TransformStream<Uint8Array, Uint8Array> {
  let total = 0;

  return new TransformStream({
    transform(chunk, controller) {
      total += chunk.byteLength;

      if (total > max) controller.error(new Error('Link content is too large'));
      else controller.enqueue(chunk);
    }
  });
}

/** 링크의 본문을 기록으로 푼다. 깨졌거나, 너무 크거나, 백엔드가 받지 않을 값이면 던진다 */
export async function decodeShare(payload: string): Promise<RecordCreate> {
  if (!payload.startsWith(PREFIX) || payload.length > MAX_PAYLOAD)
    throw new Error('Not a share link');

  const json = new Blob([fromBase64Url(payload.slice(PREFIX.length))])
    .stream()
    .pipeThrough(new DecompressionStream('deflate-raw'))
    .pipeThrough(capped(MAX_JSON));

  const text = new TextDecoder('utf-8', { fatal: true }).decode(
    await new Response(json).arrayBuffer()
  );

  const record: unknown = JSON.parse(text);

  if (
    !isRecordCreate(record) ||
    !unitsFit(record.code, record.units) ||
    !blocksFit(record.units.length, record.blocks, record.questions) ||
    blockCodeSize(record) > MAX_BLOCK_CODE
  )
    throw new Error('Link does not hold a record');

  return record;
}

/** 링크의 #뒤에 넣을 본문 */
export async function encodeShare(record: RecordOut): Promise<Result<string>> {
  const json = new TextEncoder().encode(JSON.stringify(toCreate(record)));

  const packed = new Blob([json]).stream().pipeThrough(new CompressionStream('deflate-raw'));

  const payload = PREFIX + toBase64Url(new Uint8Array(await new Response(packed).arrayBuffer()));

  // 여는 쪽과 같은 검사로 한 번 열어 본다. 브라우저 안의 백엔드는 길이를 검사하지 않아서
  // 계약보다 긴 답이 들어 있을 수 있고, 그런 링크는 열리지 않으니 건네지 않는다
  try {
    await decodeShare(payload);
  } catch {
    return {
      ok: false,
      message: '링크에 담지 못했어요. 너무 긴 답이나 내용이 있는지 확인해 주세요.'
    };
  }

  return { ok: true, data: payload };
}

import { deflateRawSync } from 'node:zlib';
import { describe, expect, it } from 'vitest';
import type { RecordCreate } from '#lib/api/client.js';
import { record } from '#lib/api/fixtures.js';
import { encodeShare, holds, unpackRecord } from '#lib/share.js';

/** 링크 본문을 node의 deflate로 따로 만든다. 앱이 표준 형식을 읽는지도 함께 본다 */
const pack = (text: string) => `v1.${deflateRawSync(Buffer.from(text)).toString('base64url')}`;

/** 링크에 담기는 기록: 질문은 블럭 id 대신 블럭 순번으로 가리킨다 */
const created: RecordCreate = {
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
    block: block_id === null ? null : record.blocks.findIndex((b) => b.id === block_id)
  }))
};

/**
 * 이미 사용자에게 건넨 꼴의 링크. 백엔드가 없을 때는 링크가 기록의 유일한 사본이라, API 계약이 바뀌어
 * 이 테스트가 깨지면 계약을 되돌리거나 v1의 꼴을 고정해 지금 꼴로 옮기는 코드를 더해야 한다
 */
const SAVED_V1 =
  'v1.nZHRahNBFIZf5XCuEjrIbrxbELGX3vgA7VImyRiHbGbX3Vm0lEDUqMG2EG22ibKRXrQEoRdrXAShT7Rz8g4ysdpU77ybw8_5zjf8BxjFYTMQPfRw-9FDcB3HgQdb28iwK_b3ZFtw9NC8HwONZubiCszxZJXl5vAcGQZcdVLeEehhtK-fhAoZtsK2nTmDJtyDHo9qUmkGUkWprtXvJFEgda1e31VRLJWucdiCZn3XbqZK6gS9nQNMNI81ejsuc3yGQrXX77sN3-JVW2oZKvQe8yARDIMwjP4MsWilcXIT99kNrbFBazD3f2g-w2YQtrq_NLvSsnD9tQ1_x7dXr8Mw1bdT17eUp6lI7N1boN9NMNTiuUYP6bQ0p-dAw6-0GNF8CKbIq-XlKitpmAPNSzDFF7PMbEQnRbU8AjMem5cz-jS5j9eu6Kk0CBhylTwTsS3zeEGvRzQfAI1yGub0cQD06kVVDmj6xhb7j_5eT3AlVWfD7Htuzi5W2cy8m0BVfFjTss80HVszszgyJ2dQLYvq2xXNZ2AuS5q-pekYVllpDn_Yxb8t3Q1F7Pv9nw';

describe('share link', () => {
  it('still opens a link handed out before', async () => {
    const opened = await unpackRecord(SAVED_V1);

    expect(opened.problem).toBe('BOJ 1000 A+B');
    expect(opened.questions.map((q) => q.answer)).toEqual(['덧셈은 순서와 상관없다', '']);
  });

  it('tells whether a kept record still holds what a link carries', async () => {
    const link = await encodeShare(record);

    if (!link.ok) throw new Error(link.message);

    const content = await unpackRecord(link.data);

    expect(holds(record, content)).toBe(true);
    // 링크를 연 뒤 답을 고친 기록은 다른 기록이다
    expect(
      holds(
        { ...record, questions: record.questions.map((q) => ({ ...q, answer: `${q.answer}!` })) },
        content
      )
    ).toBe(false);
  });

  it('round-trips a record', async () => {
    const link = await encodeShare(record);

    if (!link.ok) throw new Error(link.message);

    expect(link.data).toMatch(/^v1\.[\w-]+$/);
    expect(await unpackRecord(link.data)).toEqual(created);
  });

  it('reads a link made by any standard deflate', async () => {
    expect(await unpackRecord(pack(JSON.stringify(created)))).toEqual(created);
  });

  it('rejects text that is not one of our links', async () => {
    const plain = pack(JSON.stringify(created));

    await expect(unpackRecord(plain.slice(3))).rejects.toThrow();
    await expect(unpackRecord(`v2.${plain.slice(3)}`)).rejects.toThrow();
    await expect(unpackRecord('v1.not base64!')).rejects.toThrow();
    await expect(unpackRecord('v1.AAAA')).rejects.toThrow();
    await expect(unpackRecord(`v1.${'A'.repeat(400_000)}`)).rejects.toThrow();
  });

  it('rejects content outside the API contract', async () => {
    const bad = [
      '{"hello":"world"}',
      'null',
      JSON.stringify({ ...created, language: '__proto__' }),
      JSON.stringify({ ...created, problem: 'x'.repeat(501) }),
      JSON.stringify({ ...created, code: 42 }),
      JSON.stringify({ ...created, blocks: [{ kind: 'script', units: [0] }] }),
      JSON.stringify({ ...created, units: undefined })
    ];

    for (const json of bad) await expect(unpackRecord(pack(json))).rejects.toThrow();
  });

  it('rejects sentences and blocks the backend would not take', async () => {
    const unit = (start: number[], end: number[]) => ({
      start,
      end,
      condition: false,
      loop: false,
      recursion: false
    });

    const ask = (block: number) => [{ kind: 'logic', text: '왜?', block, answer: '' }];

    const one = [{ kind: 'logic', units: [0] }];

    // 하나씩 규칙 하나만 어긴다: 없는 문장, 두 블럭에 든 문장, 코드 밖 문장, 순서가 거꾸로인 문장, 없는 블럭
    const bad = [
      { ...created, blocks: [{ kind: 'logic', units: [999] }], questions: ask(0) },
      { ...created, blocks: [...one, { kind: 'input', units: [0] }], questions: ask(0) },
      { ...created, units: [unit([1, 0], [99, 0])], blocks: one, questions: ask(0) },
      { ...created, units: [unit([1, 5], [1, 2])], blocks: one, questions: ask(0) },
      { ...created, questions: ask(-1) },
      { ...created, questions: ask(created.blocks.length) }
    ];

    for (const json of bad)
      await expect(unpackRecord(pack(JSON.stringify(json)))).rejects.toThrow();
  });

  it('counts columns in characters (code points) like the backend', async () => {
    // "😀"는 한 글자지만 UTF-16으로는 두 칸이라, 이 줄은 7글자다
    const line = (end: number) => ({
      ...created,
      code: 'x = "😀"\n',
      units: [{ start: [1, 0], end: [1, end], condition: false, loop: false, recursion: false }],
      blocks: [{ kind: 'logic', units: [0] }],
      questions: [{ kind: 'logic', text: '왜?', block: 0, answer: '' }]
    });

    await expect(unpackRecord(pack(JSON.stringify(line(7))))).resolves.toEqual(line(7));
    await expect(unpackRecord(pack(JSON.stringify(line(8))))).rejects.toThrow();
  });

  it('rejects a link whose layouts would repeat one long line per block', async () => {
    // 한 줄(2만 글자)에 블럭 2만 개: 배치안이 그 줄을 블럭마다 다시 실어 400MB가 된다
    const n = 20_000;

    const line = {
      ...created,
      code: `${'x'.repeat(n)}\n`,
      units: Array.from({ length: n }, (_, i) => ({
        start: [1, i],
        end: [1, i + 1],
        condition: false,
        loop: false,
        recursion: false
      })),
      questions: [{ kind: 'logic', text: '왜?', block: 0, answer: '' }]
    };

    const flood = {
      ...line,
      blocks: Array.from({ length: n }, (_, i) => ({ kind: 'logic', units: [i] }))
    };

    // 같은 문장을 블럭 하나에 담으면 그 줄은 한 번만 실려서 열린다
    const single = { ...line, blocks: [{ kind: 'logic', units: line.units.map((_, i) => i) }] };

    await expect(unpackRecord(pack(JSON.stringify(flood)))).rejects.toThrow();
    await expect(unpackRecord(pack(JSON.stringify(single)))).resolves.toEqual(single);
  });

  it('stops inflating at the size limit', async () => {
    // 5MB가 몇 KB로 줄어드는 링크
    const bomb = pack(JSON.stringify('a'.repeat(5_000_000)));

    expect(bomb.length).toBeLessThan(10_000);
    await expect(unpackRecord(bomb)).rejects.toThrow('too large');
  });

  it('refuses to make a link it could not open again', async () => {
    const refused = {
      ok: false,
      message: '링크에 담지 못했어요. 너무 긴 답이나 내용이 있는지 확인해 주세요.'
    };

    // 브라우저 안의 백엔드는 길이를 보지 않아서 계약보다 긴 답이 들어올 수 있다
    const longAnswer = {
      ...record,
      questions: [{ ...record.questions[0], answer: '가'.repeat(10_001) }]
    };

    const huge = {
      ...record,
      questions: Array.from({ length: 500 }, () => ({
        ...record.questions[0],
        answer: '가'.repeat(10_000)
      }))
    };

    expect(await encodeShare(longAnswer)).toEqual(refused);
    expect(await encodeShare(huge)).toEqual(refused);
  });
});

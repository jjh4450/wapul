/**
 * 브라우저에서 코드를 블럭으로 나눈다 (wapul-seg).
 *
 * 패키지의 WASM, 모델, 문법 파일은 번들에 못 들어가서 ?url로 빌드에 정적 파일로 싣는다.
 * 모듈과 파일은 처음 나눌 때 받고, 문법은 그 언어를 처음 쓸 때만 받는다.
 */
import type { Assets, Labeled } from 'wapul-seg';
import model from 'wapul-seg/wapul-seg.model?url';
import wasm from 'wapul-seg/wapul_seg_bg.wasm?url';
import runtime from 'wapul-seg/web-tree-sitter.wasm?url';
import c from 'wapul-seg/grammars/tree-sitter-c.wasm?url';
import cpp from 'wapul-seg/grammars/tree-sitter-cpp.wasm?url';
import csharp from 'wapul-seg/grammars/tree-sitter-csharp.wasm?url';
import go from 'wapul-seg/grammars/tree-sitter-go.wasm?url';
import java from 'wapul-seg/grammars/tree-sitter-java.wasm?url';
import javascript from 'wapul-seg/grammars/tree-sitter-javascript.wasm?url';
import kotlin from 'wapul-seg/grammars/tree-sitter-kotlin.wasm?url';
import php from 'wapul-seg/grammars/tree-sitter-php.wasm?url';
import python from 'wapul-seg/grammars/tree-sitter-python.wasm?url';
import ruby from 'wapul-seg/grammars/tree-sitter-ruby.wasm?url';
import rust from 'wapul-seg/grammars/tree-sitter-rust.wasm?url';
import scala from 'wapul-seg/grammars/tree-sitter-scala.wasm?url';
import swift from 'wapul-seg/grammars/tree-sitter-swift.wasm?url';
import type { BlockIn, Language, Unit } from '#lib/api/client.js';

const grammars = {
  c,
  cpp,
  csharp,
  go,
  java,
  javascript,
  kotlin,
  php,
  python,
  ruby,
  rust,
  scala,
  swift
} satisfies { [K in Language]: string };

const urls = new Map<string, string>([
  ['wapul-seg.model', model],
  ['wapul_seg_bg.wasm', wasm],
  ['web-tree-sitter.wasm', runtime],
  ...Object.entries(grammars).map(([language, url]): [string, string] => [
    `grammars/tree-sitter-${language}.wasm`,
    url
  ])
]);

async function fetchFile(name: string): Promise<Response> {
  const url = urls.get(name);

  if (url === undefined) throw new Error(`${name}: not in the release`);

  const response = await fetch(url);

  if (!response.ok) throw new Error(`${name}: ${response.status}`);

  return response;
}

const assets: Assets = {
  text: async (name) => (await fetchFile(name)).text(),
  bytes: async (name) => new Uint8Array(await (await fetchFile(name)).arrayBuffer())
};

export type Segmented = { code: string; units: Unit[]; blocks: BlockIn[] };

/** 문장 목록을 블럭으로 묶는다: 입력, 로직 블럭(모델의 번호 순), 출력. none 문장은 어느 블럭에도 들지 않는다 */
export function toBlocks(labeled: Labeled[]): BlockIn[] {
  const input: number[] = [];
  const output: number[] = [];
  const logic = new Map<number, number[]>();

  labeled.forEach((unit, i) => {
    if (unit.kind === 'input') input.push(i);
    else if (unit.kind === 'output') output.push(i);
    else if (unit.kind === 'logic') {
      const block = unit.block ?? 1;
      logic.set(block, [...(logic.get(block) ?? []), i]);
    }
  });

  const blocks: BlockIn[] = [];

  if (input.length > 0) blocks.push({ kind: 'input', units: input });

  for (const block of [...logic.keys()].sort((a, b) => a - b)) {
    blocks.push({ kind: 'logic', units: logic.get(block) ?? [] });
  }

  if (output.length > 0) blocks.push({ kind: 'output', units: output });

  return blocks;
}

/** 코드를 normalize하고 나눈다. 돌려준 code가 문장 위치의 기준이라 이것을 저장한다 */
export async function segmentCode(code: string, language: Language): Promise<Segmented> {
  const { normalize, segment } = await import('wapul-seg');
  const normalized = normalize(code);
  const labeled = await segment(normalized, language, assets);

  return {
    code: normalized,
    // 조건·반복·재귀 표시는 BE가 블럭마다 모아 경계 질문과 구조별 질문을 붙이는 데 쓴다
    units: labeled.map(({ start, end, condition, loop, recursion }) => ({
      start,
      end,
      condition,
      loop,
      recursion
    })),
    blocks: toBlocks(labeled)
  };
}

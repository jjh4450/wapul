// Where each language's grammar `.wasm` comes from: the grammar's npm package, pinned in
// package.json at the version wapul-ml's py-tree-sitter package has, or a GitHub release when
// the npm package ships no `.wasm` (docs/ml/deploy.ko.md, "지원 언어"). Downloads go to
// js/.cache/ once.

import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import path from 'node:path';

import { type Language } from '../src/languages.ts';

export type GrammarSource = { package: string; file: string } | { url: string };

const SWIFT_RELEASE = 'https://github.com/alex-pinkus/tree-sitter-swift/releases/download/0.7.3';

export const GRAMMAR_SOURCES: Record<Language, GrammarSource> = {
  cpp: { package: 'tree-sitter-cpp', file: 'tree-sitter-cpp.wasm' },
  java: { package: 'tree-sitter-java', file: 'tree-sitter-java.wasm' },
  python: { package: 'tree-sitter-python', file: 'tree-sitter-python.wasm' },
  rust: { package: 'tree-sitter-rust', file: 'tree-sitter-rust.wasm' },
  c: { package: 'tree-sitter-c', file: 'tree-sitter-c.wasm' },
  kotlin: { package: '@tree-sitter-grammars/tree-sitter-kotlin', file: 'tree-sitter-kotlin.wasm' },
  javascript: { package: 'tree-sitter-javascript', file: 'tree-sitter-javascript.wasm' },
  go: { package: 'tree-sitter-go', file: 'tree-sitter-go.wasm' },
  csharp: { package: 'tree-sitter-c-sharp', file: 'tree-sitter-c_sharp.wasm' },
  swift: { url: `${SWIFT_RELEASE}/tree-sitter-swift.wasm` },
  ruby: { package: 'tree-sitter-ruby', file: 'tree-sitter-ruby.wasm' },
  scala: { package: 'tree-sitter-scala', file: 'tree-sitter-scala.wasm' },
  php: { package: 'tree-sitter-php', file: 'tree-sitter-php.wasm' }
};

const require = createRequire(import.meta.url);

const cache = path.resolve(import.meta.dirname, '..', '.cache');

async function download(url: string): Promise<string> {
  const target = path.join(cache, path.basename(url));

  try {
    await readFile(target);
  } catch {
    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`${url}: ${response.status} ${response.statusText}`);
    }

    await mkdir(cache, { recursive: true });
    await writeFile(target, new Uint8Array(await response.arrayBuffer()));
  }

  return target;
}

/** The grammar's `.wasm` on disk, from node_modules or the download cache. */
export async function grammarPath(language: Language): Promise<string> {
  const source = GRAMMAR_SOURCES[language];

  if ('url' in source) {
    return download(source.url);
  }

  return path.join(path.dirname(require.resolve(`${source.package}/package.json`)), source.file);
}

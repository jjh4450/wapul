// The release files as the development checkout holds them, for tests that parse or load the
// model without a built dist/.

import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import path from 'node:path';

import { type Assets } from '../src/assets.ts';
import { grammarFile, LANGUAGES } from '../src/languages.ts';
import { grammarPath } from '../tools/grammars.ts';

const require = createRequire(import.meta.url);

const root = path.resolve(import.meta.dirname, '..');

/** The release files as the development checkout holds them. */
async function file(name: string): Promise<string> {
  const grammar = LANGUAGES.find((language) => grammarFile(language) === name);

  if (name === 'web-tree-sitter.wasm') {
    return require.resolve('web-tree-sitter/web-tree-sitter.wasm');
  }

  if (grammar !== undefined) {
    return grammarPath(grammar);
  }

  if (name === 'wapul_seg_bg.wasm' || name === 'wapul-seg.model') {
    return path.join(root, '..', 'pkg', name);
  }

  throw new Error(`unknown asset ${name}`);
}

export const assets: Assets = {
  text: async (name) => readFile(await file(name), 'utf8'),
  bytes: async (name) => readFile(await file(name))
};

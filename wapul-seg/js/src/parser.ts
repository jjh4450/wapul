// web-tree-sitter, with its runtime and each grammar loaded once per asset location. A failed
// load is forgotten, so the next call tries again.
//
// Node indices (`startIndex`, `endIndex`, `descendantForIndex`) are UTF-16 code units, where
// py-tree-sitter gives UTF-8 bytes. The model uses positions only to compare and to slice the
// same string, so either works as long as everything here uses the same one.

import { Language as Grammar, Parser, type Tree } from 'web-tree-sitter';

import { type Assets } from './assets.ts';
import { grammarFile, type Language } from './languages.ts';

const RUNTIME = 'web-tree-sitter.wasm';

let runtime: Promise<void> | undefined;

const grammars = new Map<Language, Promise<Grammar>>();

function grammar(language: Language, assets: Assets): Promise<Grammar> {
  let loading = grammars.get(language);

  if (loading === undefined) {
    loading = assets.bytes(grammarFile(language)).then((bytes) => Grammar.load(bytes));
    grammars.set(language, loading);
    // Callers still see the failure; this branch only forgets it
    loading.catch(() => grammars.delete(language));
  }

  return loading;
}

/** Parse normalized code. The caller deletes the tree when done with it. */
export async function parse(code: string, language: Language, assets: Assets): Promise<Tree> {
  if (runtime === undefined) {
    runtime = assets.bytes(RUNTIME).then((wasmBinary) => Parser.init({ wasmBinary }));
    runtime.catch(() => {
      runtime = undefined;
    });
  }

  await runtime;
  const parser = new Parser();

  try {
    parser.setLanguage(await grammar(language, assets));
    const tree = parser.parse(code);

    if (tree === null) {
      throw new Error(`parsing ${language} returned no tree`);
    }

    return tree;
  } finally {
    parser.delete();
  }
}

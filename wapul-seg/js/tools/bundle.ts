// Assemble the release under dist/ after `vite build`: the module, the WASM, the runtime and
// grammar .wasm files, and the model from the repo root (docs/ml/deploy.ko.md, "구성"). Run
// from js/: `node tools/bundle.ts`.

import { copyFile, mkdir } from 'node:fs/promises';
import { createRequire } from 'node:module';
import path from 'node:path';

import { grammarFile, LANGUAGES } from '../src/languages.ts';
import { grammarPath } from './grammars.ts';

const require = createRequire(import.meta.url);

const js = path.resolve(import.meta.dirname, '..');

const repo = path.resolve(js, '..', '..');

const dist = path.join(js, 'dist');

const files: [string, string][] = [
  [path.join(js, '..', 'pkg', 'wapul_seg_bg.wasm'), 'wapul_seg_bg.wasm'],
  [require.resolve('web-tree-sitter/web-tree-sitter.wasm'), 'web-tree-sitter.wasm'],
  ...(await Promise.all(
    LANGUAGES.map(async (language): Promise<[string, string]> => [
      await grammarPath(language),
      grammarFile(language)
    ])
  )),
  ...['kinds-lgbm.txt', 'kinds-features.txt', 'blocks-lgbm.txt', 'model.json'].map(
    (name): [string, string] => [path.join(repo, 'model', name), `model/${name}`]
  )
];

for (const [from, to] of files) {
  await mkdir(path.dirname(path.join(dist, to)), { recursive: true });
  await copyFile(from, path.join(dist, to));
  console.log(to);
}

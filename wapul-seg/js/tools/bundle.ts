// Assemble the release under dist/ after `vite build`: the module, the WASM, the runtime and
// grammar .wasm files, and the packed model (docs/ml/deploy.ko.md, "구성"). Run
// from js/: `node tools/bundle.ts`.

import { copyFile, mkdir } from 'node:fs/promises';
import { createRequire } from 'node:module';
import path from 'node:path';

import { grammarFile, LANGUAGES } from '../src/languages.ts';
import { grammarPath } from './grammars.ts';

const require = createRequire(import.meta.url);

const js = path.resolve(import.meta.dirname, '..');

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
  // The root model/ packed by scripts/build-wasm.sh
  [path.join(js, '..', 'pkg', 'wapul-seg.model'), 'wapul-seg.model']
];

for (const [from, to] of files) {
  await mkdir(path.dirname(path.join(dist, to)), { recursive: true });
  await copyFile(from, path.join(dist, to));
  console.log(to);
}

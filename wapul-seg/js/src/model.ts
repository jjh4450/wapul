// The WASM with the model loaded, once per page: the first assets given are used
// (docs/ml/deploy.ko.md, "모델").

import init, { Model } from '../../pkg/wapul_seg.js';

import { type Assets } from './assets.ts';

const WASM = 'wapul_seg_bg.wasm';

const MODEL_FILES = ['model/kinds-lgbm.txt', 'model/kinds-features.txt', 'model/blocks-lgbm.txt'];

let loading: Promise<Model> | undefined;

export function model(assets: Assets): Promise<Model> {
  loading ??= Promise.all([
    assets.bytes(WASM).then((bytes) => init({ module_or_path: bytes })),
    ...MODEL_FILES.map((f) => assets.text(f))
  ]).then(([, kinds, features, blocks]) => new Model(kinds, features, blocks));

  return loading;
}

// The WASM with the packed model loaded, once per page: the first assets given are used
// (docs/ml/deploy.ko.md, "모델").

import init, { Model } from '../../pkg/wapul_seg.js';

import { type Assets } from './assets.ts';

const WASM = 'wapul_seg_bg.wasm';

const PACKED_MODEL = 'wapul-seg.model';

let loading: Promise<Model> | undefined;

export function model(assets: Assets): Promise<Model> {
  loading ??= Promise.all([
    assets.bytes(WASM).then((bytes) => init({ module_or_path: bytes })),
    assets.bytes(PACKED_MODEL)
  ]).then(([, packed]) => new Model(packed));

  return loading;
}

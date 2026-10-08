// Loading failures: a failed fetch is retried on the next call, and a tree parsed while the
// model failed to load is freed. Each test imports the modules afresh, so no load is cached yet.

import { beforeEach, expect, test, vi } from 'vitest';

import { type Assets } from '../src/assets.ts';
import { assets } from './assets.ts';

const CODE = 'n = int(input())\nprint(n * 2)\n';

const MODEL_FILES = ['wapul_seg_bg.wasm', 'wapul-seg.model'];

beforeEach(() => {
  vi.resetModules();
});

/** The release files, failing the first request for each name. */
function flaky(): Assets {
  const seen = new Set<string>();

  const once = (name: string): void => {
    if (!seen.has(name)) {
      seen.add(name);
      throw new Error(`offline: ${name}`);
    }
  };

  return {
    text: async (name) => (once(name), assets.text(name)),
    bytes: async (name) => (once(name), assets.bytes(name))
  };
}

test('a failed load is tried again on the next call', async () => {
  const { segment } = await import('../src/index.ts');
  const from = flaky();

  // 1st: the runtime and the model files fail; 2nd: the grammar fails; 3rd: everything loads
  await expect(segment(CODE, 'python', from)).rejects.toThrow('offline');
  await expect(segment(CODE, 'python', from)).rejects.toThrow(
    'offline: grammars/tree-sitter-python.wasm'
  );
  expect((await segment(CODE, 'python', from)).map((u) => u.kind)).toHaveLength(2);
});

test('the tree is freed when the model fails to load', async () => {
  const { Tree } = await import('web-tree-sitter');
  const { segment } = await import('../src/index.ts');
  const freed = vi.spyOn(Tree.prototype, 'delete');

  const noModel: Assets = {
    text: (name) => assets.text(name),
    bytes: async (name) => {
      if (MODEL_FILES.includes(name)) {
        throw new Error(`offline: ${name}`);
      }

      return assets.bytes(name);
    }
  };

  await expect(segment(CODE, 'python', noModel)).rejects.toThrow('offline');
  expect(freed).toHaveBeenCalledOnce();
});

import { type Plugin } from 'vite';
import dts from 'vite-plugin-dts';
import { defineConfig } from 'vitest/config';

// In library mode Vite inlines every `new URL(file, import.meta.url)` asset as base64, which
// would put web-tree-sitter's runtime .wasm into the module. The module never uses that
// default path (parser.ts passes the bytes from its assets), so drop it from the dependency.
function noRuntimeWasmUrl(): Plugin {
  return {
    name: 'no-runtime-wasm-url',
    transform(code, id) {
      if (id.endsWith('/web-tree-sitter/web-tree-sitter.js')) {
        return code.replace('new URL("web-tree-sitter.wasm", import.meta.url).href', '""');
      }

      return null;
    }
  };
}

export default defineConfig({
  // One bundled declaration file next to the module, for the package's `types`
  plugins: [noRuntimeWasmUrl(), dts({ bundleTypes: true, include: ['src'] })],
  build: {
    lib: {
      entry: 'src/index.ts',
      formats: ['es'],
      fileName: 'wapul-seg'
    },
    // Library ES output keeps its whitespace by design (Vite: minifying it would drop the
    // pure annotations); the frontend's own build minifies the module with the rest.
    rollupOptions: {
      output: { inlineDynamicImports: true }
    }
  },
  test: {
    environment: 'node'
  }
});

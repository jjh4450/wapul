// Where the release files come from: the WASM, the model files and the grammars
// (docs/ml/deploy.ko.md, "구성"). The browser fetches them; tests read them from disk.

export interface Assets {
  /** A text file of the release, by its path in the release. */
  text(name: string): Promise<string>;
  /** A binary file of the release, by its path in the release. */
  bytes(name: string): Promise<Uint8Array>;
}

async function fetchOk(url: URL): Promise<Response> {
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`${url}: ${response.status} ${response.statusText}`);
  }

  return response;
}

/** The release files served under `base` (a directory URL; a trailing slash is added). */
export function fetchAssets(base: string | URL): Assets {
  const root = new URL(base, typeof document === 'undefined' ? undefined : document.baseURI);

  if (!root.pathname.endsWith('/')) {
    root.pathname += '/';
  }

  const url = (name: string): URL => new URL(name, root);

  return {
    text: async (name) => (await fetchOk(url(name))).text(),
    bytes: async (name) => new Uint8Array(await (await fetchOk(url(name))).arrayBuffer())
  };
}

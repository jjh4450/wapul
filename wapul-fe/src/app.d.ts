// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
import type { Schema } from '@cfworker/json-schema';

declare global {
  /** API 계약(openapi.json)에서 뽑은 스키마. vite.config.ts의 define이 빌드할 때 넣는다 */
  const __CONTRACT__: Schema;

  namespace App {
    // interface Error {}
    // interface Locals {}
    // interface PageData {}
    // interface PageState {}
    // interface Platform {}
  }
}

export {};

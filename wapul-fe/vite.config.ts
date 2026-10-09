import { mdsvex } from 'mdsvex';
import { defineConfig } from 'vitest/config';
import { playwright } from '@vitest/browser-playwright';
import { enhancedImages } from '@sveltejs/enhanced-img';
import tailwindcss from '@tailwindcss/vite';
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import path from 'node:path';
import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { storybookTest } from '@storybook/addon-vitest/vitest-plugin';
import type { Schema } from '@cfworker/json-schema';

const dirname =
  typeof __dirname !== 'undefined' ? __dirname : path.dirname(fileURLToPath(import.meta.url));

// VERSION은 deploy/fe 브랜치에만 있다 (fe-deploy 워크플로가 커밋). 없으면 SvelteKit 기본값(빌드 시각).
const versionFile = path.join(dirname, 'VERSION');

const appVersion = existsSync(versionFile) ? readFileSync(versionFile, 'utf8').trim() : undefined;

// API 계약(openapi.json). 저장 링크를 열 때 검사할 스키마(src/lib/share.ts)와 입력 칸의 글자 수 한도를
// 빌드할 때 여기서 뽑는다. 계약이 바뀌면 함께 바뀌고, 쓰는 값이 계약에 없으면 빌드가 멈춘다
const schemas: Record<string, Schema> = JSON.parse(
  readFileSync(path.join(dirname, '../openapi/openapi.json'), 'utf8')
).components.schemas;

function schema(name: string): Schema {
  if (!(name in schemas)) throw new Error(`API 계약에 ${name} 스키마가 없다`);

  return schemas[name];
}

/** roots와 그것이 가리키는 스키마만. 계약 전체를 넣지 않는다 */
function contractSchemas(roots: string[]) {
  const picked: Record<string, Schema> = {};

  const pending = [...roots];

  for (let name = pending.pop(); name !== undefined; name = pending.pop()) {
    if (name in picked) continue;

    picked[name] = schema(name);

    for (const [, ref] of JSON.stringify(picked[name]).matchAll(
      /"#\/components\/schemas\/([^"]+)"/g
    ))
      pending.push(ref);
  }

  return { components: { schemas: picked } };
}

function maxLength(name: string, field: string): number {
  const property = schema(name).properties?.[field];

  const limit =
    property === undefined || property === true || property === false
      ? undefined
      : property.maxLength;

  if (limit === undefined) throw new Error(`API 계약의 ${name}.${field}에 maxLength가 없다`);

  return limit;
}

// More info at: https://storybook.js.org/docs/next/writing-tests/integrations/vitest-addon
export default defineConfig({
  plugins: [
    enhancedImages(),
    tailwindcss(),
    sveltekit({
      compilerOptions: {
        // Force runes mode for the project, except for libraries. Can be removed in svelte 6.
        runes: ({ filename }) =>
          filename.split(/[/\\]/).includes('node_modules') ? undefined : true
      },
      adapter: adapter(),
      version: { name: appVersion },
      preprocess: [
        mdsvex({
          extensions: ['.svx', '.md']
        })
      ],
      extensions: ['.svelte', '.svx', '.md']
    })
  ],
  define: {
    __CONTRACT__: JSON.stringify(contractSchemas(['RecordCreate'])),
    __LIMITS__: JSON.stringify({
      problem: maxLength('RecordCreate', 'problem'),
      keyIdea: maxLength('RecordCreate', 'key_idea'),
      code: maxLength('RecordCreate', 'code'),
      // 답은 저장할 때(AnswerIn)와 링크에 담을 때(QuestionIn) 모두 맞아야 한다
      answer: Math.min(maxLength('AnswerIn', 'answer'), maxLength('QuestionIn', 'answer'))
    })
  },
  // VITE_BACKEND=on으로 띄우면 개발 중 API 요청을 로컬 백엔드(wapul-be)로 넘긴다. 배포에서는 VITE_API_BASE_URL을 쓴다.
  server: {
    proxy: { '/v1': 'http://localhost:2614' }
  },
  test: {
    expect: {
      requireAssertions: true
    },
    projects: [
      {
        extends: './vite.config.ts',
        test: {
          name: 'client',
          browser: {
            enabled: true,
            provider: playwright({ launchOptions: { channel: 'chromium' } }),
            instances: [
              {
                browser: 'chromium',
                headless: true
              }
            ]
          },
          include: ['src/**/*.svelte.{test,spec}.{js,ts}'],
          exclude: ['src/lib/server/**']
        }
      },
      {
        extends: './vite.config.ts',
        test: {
          name: 'server',
          environment: 'node',
          include: ['src/**/*.{test,spec}.{js,ts}'],
          exclude: ['src/**/*.svelte.{test,spec}.{js,ts}']
        }
      },
      {
        extends: true,
        plugins: [
          // The plugin will run tests for the stories defined in your Storybook config
          // See options at: https://storybook.js.org/docs/next/writing-tests/integrations/vitest-addon#storybooktest
          storybookTest({
            configDir: path.join(dirname, '.storybook')
          })
        ],
        test: {
          name: 'storybook',
          browser: {
            enabled: true,
            headless: true,
            provider: playwright({ launchOptions: { channel: 'chromium' } }),
            instances: [
              {
                browser: 'chromium'
              }
            ]
          }
        }
      }
    ]
  }
});

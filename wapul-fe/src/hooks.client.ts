import Clarity from '@microsoft/clarity';
import type { ClientInit } from '@sveltejs/kit/hooks';
import { dev } from '$app/env';
import { BACKEND } from '#lib/api/client.js';
import { localApi } from '#lib/api/local.js';
import { browserRecords } from '#lib/drafts.js';

/** 방문 분석(Microsoft Clarity)의 이 사이트 프로젝트 */
const CLARITY_PROJECT = 'yv8v08ure4';

export const init: ClientInit = async () => {
  // 백엔드를 끈 배포는 화면이 뜨기 전에 /v1 요청을 브라우저 안의 백엔드가 받게 한다.
  // 기록은 이 브라우저에 담아 두고, 저장소를 못 쓰면 탭에만 둔다
  if (!BACKEND) localApi((await browserRecords()) ?? []).install({ record: false });

  // 개발 서버의 방문은 세지 않는다
  if (!dev) Clarity.init(CLARITY_PROJECT);
};

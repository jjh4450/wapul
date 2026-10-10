import type { ClientInit } from '@sveltejs/kit/hooks';
import { resolve } from '$app/paths';
import { BACKEND } from '#lib/api/client.js';
import { localApi } from '#lib/api/local.js';
import { startAnalytics } from '#lib/analytics.js';
import { browserRecords } from '#lib/drafts.js';

export const init: ClientInit = async () => {
  // 백엔드를 끈 배포는 화면이 뜨기 전에 /v1 요청을 브라우저 안의 백엔드가 받게 한다.
  // 기록은 이 브라우저에 담아 두고, 저장소를 못 쓰면 탭에만 둔다
  if (!BACKEND) localApi((await browserRecords()) ?? []).install({ record: false });

  // 저장 링크(/share#…)는 주소에 기록 전체를 담고 있어서, 링크를 열고 주소를 바꾼 뒤에 켠다(share 페이지)
  if (location.pathname !== resolve('/share')) startAnalytics();
};

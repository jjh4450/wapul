import type { ClientInit } from '@sveltejs/kit/hooks';
import { BACKEND } from '#lib/api/client.js';
import { localApi } from '#lib/api/local.js';

// 백엔드를 끈 배포는 화면이 뜨기 전에 /v1 요청을 브라우저 안의 백엔드가 받게 한다
export const init: ClientInit = () => {
  if (!BACKEND) localApi().install({ record: false });
};

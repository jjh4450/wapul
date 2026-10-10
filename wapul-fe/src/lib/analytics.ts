/**
 * 방문 분석(Microsoft Clarity). 녹화에서 사용자가 쓴 내용(코드, 답, 문제, 자동완성 후보)은 그 요소에
 * data-clarity-mask를 달아 가린다. 입력 칸의 글자는 Clarity가 늘 가린다. 개발 서버의 방문은 세지 않는다.
 */
import Clarity from '@microsoft/clarity';
import { dev } from '$app/env';

/** 이 사이트의 Clarity 프로젝트 */
const CLARITY_PROJECT = 'yv8v08ure4';

/** 분석을 켠다. 여러 번 불러도 한 번만 켜진다 */
export function startAnalytics(): void {
  if (!dev) Clarity.init(CLARITY_PROJECT);
}

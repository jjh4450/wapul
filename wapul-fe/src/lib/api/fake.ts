/**
 * 백엔드 없이 화면을 돌리기 위한 가짜 API.
 *
 * story와 테스트에서 globalThis.fetch를 바꿔 끼운다. 화면은 실제 API 클라이언트를 그대로 쓰고
 * 응답만 여기서 정한다. 받은 요청은 calls에 남아서 화면이 무엇을 보냈는지 검사할 수 있다.
 */

export type FakeCall = { method: string; path: string; body: string };

export type FakeHandler = (call: FakeCall) => Response | Promise<Response>;

type Route = { method: string; segments: string[]; handler: FakeHandler };

/** JSON 응답 */
export function reply<T>(body: T, status = 200): FakeHandler {
  return () =>
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' }
    });
}

/** 본문 없는 응답 (204 등) */
export function empty(status = 204): FakeHandler {
  return () => new Response(null, { status });
}

/** 끝나지 않는 응답. 불러오는 중 상태를 보여줄 때 쓴다 */
export const pending: FakeHandler = () => new Promise<Response>(() => {});

function matches(segments: string[], pathname: string): boolean {
  const parts = pathname.split('/');

  return (
    parts.length === segments.length &&
    segments.every((segment, i) => segment.startsWith(':') || segment === parts[i])
  );
}

export class FakeApi {
  readonly calls: FakeCall[] = [];

  readonly #routes: Route[];

  /** routes: ['GET /v1/records/:id', handler] 꼴. ':'로 시작하는 조각은 아무 값과 맞는다 */
  constructor(routes: [string, FakeHandler][]) {
    this.#routes = routes.map(([route, handler]) => {
      const [method, path] = route.split(' ');

      return { method, segments: path.split('/'), handler };
    });
  }

  /** globalThis.fetch를 이 가짜로 바꾸고 되돌리는 함수를 돌려준다. story의 beforeEach에서 그대로 반환한다.
   * API(/v1/) 요청만 가로채고, 분할 모델 파일 같은 그 밖의 요청은 원래 fetch로 보낸다 */
  install(): () => void {
    const original = globalThis.fetch;

    this.calls.length = 0;
    globalThis.fetch = (input, init) => {
      const request = new Request(input, init);

      return new URL(request.url).pathname.startsWith('/v1/')
        ? this.#handle(request)
        : original(request);
    };

    return () => {
      globalThis.fetch = original;
    };
  }

  /** method와 경로(쿼리 제외)가 맞는 요청만 */
  callsTo(method: string, path: string): FakeCall[] {
    return this.calls.filter((call) => call.method === method && call.path === path);
  }

  async #handle(request: Request): Promise<Response> {
    const { pathname } = new URL(request.url);

    const call = { method: request.method, path: pathname, body: await request.text() };

    this.calls.push(call);

    const route = this.#routes.find(
      (r) => r.method === call.method && matches(r.segments, pathname)
    );

    if (route === undefined) {
      // 정하지 않은 요청을 조용히 넘기면 화면이 엉뚱한 에러 상태로 보여 원인을 찾기 어렵다
      console.error(`가짜 API에 정하지 않은 요청: ${call.method} ${pathname}`);

      return new Response(null, { status: 501 });
    }

    return route.handler(call);
  }
}

/** 서버에 닿지 못한 요청 (네트워크 끊김) */
export const offline: FakeHandler = () => Promise.reject(new TypeError('Failed to fetch'));

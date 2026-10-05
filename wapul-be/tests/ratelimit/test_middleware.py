"""
Rate Limit Middleware 통합 테스트

rate_limit_client fixture를 사용하여 레이트 리밋이 활성화된 환경에서 테스트.
다른 테스트와 완전히 격리됩니다.
"""

import pytest

from app.ratelimit.config import get_rule_for_request

pytestmark = pytest.mark.ratelimit

# 라우트 존재 여부와 무관하게 /v1/* 요청은 레이트 리밋 대상
PATH = "/v1/ping"


class TestRateLimitMiddleware:
    """레이트 리밋 미들웨어 통합 테스트"""

    def test_rate_limit_headers_present(self, rate_limit_client):
        """응답에 레이트 리밋 헤더 포함"""
        response = rate_limit_client.get(PATH)

        # 성공 응답이든 에러든 헤더는 있어야 함
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    def test_rate_limit_remaining_decreases(self, rate_limit_client):
        """요청마다 remaining 감소"""
        response1 = rate_limit_client.get(PATH)
        remaining1 = int(response1.headers["X-RateLimit-Remaining"])

        response2 = rate_limit_client.get(PATH)
        remaining2 = int(response2.headers["X-RateLimit-Remaining"])

        assert remaining2 == remaining1 - 1

    def test_rate_limit_exceeded_returns_429(self, rate_limit_client):
        """한도 초과 시 429 반환"""
        # config에서 실제 한도 가져오기
        rule = get_rule_for_request("GET", PATH)
        assert rule is not None, f"GET {PATH} 규칙이 없습니다"
        max_requests = rule.max_requests

        # 한도까지 요청
        for _ in range(max_requests):
            response = rate_limit_client.get(PATH)
            assert response.status_code != 429

        # 한도 초과
        response = rate_limit_client.get(PATH)

        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert response.json()["detail"] == "요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요."

    def test_non_api_endpoints_not_rate_limited(self, rate_limit_client):
        """비 API 경로는 레이트 리밋 미적용"""
        # /docs나 /openapi.json 같은 경로
        response = rate_limit_client.get("/docs")

        # 레이트 리밋 헤더 없음
        assert "X-RateLimit-Limit" not in response.headers

    def test_limit_header_matches_rule(self, rate_limit_client):
        """응답 헤더의 한도가 config와 일치"""
        rule = get_rule_for_request("GET", PATH)
        assert rule is not None

        response = rate_limit_client.get(PATH)

        assert int(response.headers["X-RateLimit-Limit"]) == rule.max_requests

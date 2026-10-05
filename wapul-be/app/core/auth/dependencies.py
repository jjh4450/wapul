"""
인증 의존성 (FastAPI Dependency)

- get_current_user: 인증 게이트(실패 시 401). AuthMiddleware가 채운 request.state를 재사용.
- get_optional_current_user: 선택적 인증(미인증 허용 엔드포인트용).
"""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.auth.client import oidc_client
from app.core.auth.model import CurrentUser
from app.core.config import settings

# HTTP Bearer 스키마
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> CurrentUser:
    """
    FastAPI Dependency: 현재 인증된 사용자 반환

    - AuthMiddleware에서 이미 검증된 경우 request.state에서 가져옴 (중복 검증 방지)
    - 그렇지 않으면 Authorization: Bearer <token> 헤더에서 토큰 추출 후 검증
    - CurrentUser 객체 반환

    OIDC_ENABLED=false인 경우 테스트용 mock 사용자 반환
    """
    # AuthMiddleware에서 이미 검증된 경우 재사용
    if hasattr(request.state, "current_user") and request.state.current_user:
        return request.state.current_user

    # 인증 비활성화 시 테스트용 사용자 반환
    if not settings.OIDC_ENABLED:
        return CurrentUser.mock()

    # 토큰 없음
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 토큰 검증
    claims = await oidc_client.verify_token(credentials.credentials)

    # sub 클레임 필수
    sub = claims.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing 'sub' claim",
        )

    return CurrentUser.from_claims(claims)


async def get_optional_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> CurrentUser | None:
    """
    FastAPI Dependency: 선택적 인증 (인증 없어도 접근 가능한 엔드포인트용)

    토큰이 없으면 None 반환, 토큰이 있으면 검증 후 CurrentUser 반환
    """
    # AuthMiddleware에서 이미 검증된 경우 재사용
    if hasattr(request.state, "current_user") and request.state.current_user:
        return request.state.current_user

    if not settings.OIDC_ENABLED:
        return CurrentUser.mock()

    if not credentials:
        return None

    try:
        return await get_current_user(request, credentials)
    except HTTPException:
        return None

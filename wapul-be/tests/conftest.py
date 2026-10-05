import os

# 테스트 환경 기본 설정 - 다른 모듈 임포트 전에 설정 필요!
os.environ["OIDC_ENABLED"] = "false"
os.environ["RATE_LIMIT_ENABLED"] = "false"  # 기본 비활성화, 레이트 리밋 테스트에서만 활성화
os.environ["WS_RATE_LIMIT_ENABLED"] = "false"  # WebSocket 레이트 리밋 비활성화

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine, Session

from app.core.auth import CurrentUser


# ============ DB 타입 헬퍼 함수 ============

def _get_test_database_url() -> str | None:
    """TEST_DATABASE_URL 환경변수 반환 (없으면 None)"""
    return os.environ.get("TEST_DATABASE_URL")


def _is_postgresql(url: str) -> bool:
    """PostgreSQL URL인지 확인"""
    return url.startswith("postgresql")


def _get_async_url(url: str) -> str:
    """동기 URL을 비동기 URL로 변환"""
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


@pytest.fixture
def test_user() -> CurrentUser:
    """테스트용 사용자 (OIDC 비활성화 시 반환되는 mock 사용자와 동일)"""
    return CurrentUser(
        sub="test-user-id",
        email="test@example.com",
        email_verified=True,
        name="Test User",
    )


@pytest.fixture
def test_engine():
    """
    테스트용 DB 엔진
    
    TEST_DATABASE_URL 환경변수가 설정되면 해당 DB 사용,
    없으면 SQLite 메모리 DB 사용
    """
    test_db_url = _get_test_database_url()

    if test_db_url and _is_postgresql(test_db_url):
        # PostgreSQL 사용
        engine = create_engine(
            test_db_url,
            echo=False,
            pool_pre_ping=True,
        )

        # 테스트용 테이블 생성
        SQLModel.metadata.create_all(engine)

        yield engine

        # 테스트 후 정리 (테이블 삭제)
        SQLModel.metadata.drop_all(engine)
        engine.dispose()
    else:
        # SQLite 메모리 DB 사용 (기본값)
        engine = create_engine(
            "sqlite:///:memory:",
            echo=False,
            connect_args={"check_same_thread": False},
        )

        # SQLite에서 외래 키 제약 조건 활성화 (각 연결마다)
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        # 테스트용 테이블 생성
        SQLModel.metadata.create_all(engine)

        yield engine

        # 테스트 후 정리
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def test_session(test_engine):
    """트랜잭션 기반 테스트 세션"""
    with Session(test_engine) as session:
        # 트랜잭션 시작
        transaction = session.begin()
        try:
            yield session
            # 각 테스트 후 자동 rollback
            transaction.rollback()
        except Exception:
            transaction.rollback()
            raise


@pytest_asyncio.fixture
async def test_async_engine():
    """
    테스트용 비동기 DB 엔진
    
    TEST_DATABASE_URL 환경변수가 설정되면 해당 DB 사용,
    없으면 SQLite 메모리 DB 사용
    """
    test_db_url = _get_test_database_url()

    if test_db_url and _is_postgresql(test_db_url):
        # PostgreSQL 비동기 엔진 생성
        async_url = _get_async_url(test_db_url)
        engine = create_async_engine(
            async_url,
            echo=False,
            pool_pre_ping=True,
        )

        # 테스트용 테이블 생성
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

        yield engine

        # 테스트 후 정리
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
        await engine.dispose()
    else:
        # SQLite 비동기 엔진 생성 (기본값)
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        # SQLite에서 외래 키 제약 조건 활성화
        @event.listens_for(engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        # 테스트용 테이블 생성
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

        yield engine

        # 테스트 후 정리
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
        await engine.dispose()


@pytest_asyncio.fixture
async def test_async_session(test_async_engine):
    """트랜잭션 기반 비동기 테스트 세션"""
    async_session_maker = async_sessionmaker(
        test_async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        # 트랜잭션 시작
        transaction = await session.begin()
        try:
            yield session
            # 각 테스트 후 자동 rollback
            await transaction.rollback()
        except Exception:
            await transaction.rollback()
            raise


# ============ E2E 다중 사용자 시뮬레이션 ============

def _create_test_engine():
    """E2E용 테스트 엔진 생성 헬퍼"""
    test_db_url = _get_test_database_url()

    if test_db_url and _is_postgresql(test_db_url):
        # PostgreSQL 사용
        return create_engine(
            test_db_url,
            echo=False,
            pool_pre_ping=True,
        )
    else:
        # SQLite 메모리 DB 사용 (기본값)
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )

        # SQLite에서 외래 키 제약 조건 활성화 (각 연결마다)
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine


def make_user(sub: str, email: str = None, name: str = None) -> CurrentUser:
    """테스트용 사용자 생성 헬퍼 (이메일은 검증된 것으로 간주)"""
    return CurrentUser(
        sub=sub,
        email=email or f"{sub}@example.com",
        email_verified=True,
        name=name or f"User {sub}",
    )


@pytest.fixture
def e2e_client():
    """
    E2E 테스트용 FastAPI 클라이언트
    
    TEST_DATABASE_URL 환경변수가 설정되면 해당 DB 사용,
    없으면 SQLite 메모리 DB 사용
    
    Bug Fix: StaticPool 사용 (SQLite 전용)
    - SQLite 메모리 DB는 커넥션마다 별도 인스턴스를 가짐
    - StaticPool을 사용하여 모든 커넥션이 동일한 메모리 DB 인스턴스를 공유하도록 함
    
    Bug Fix: settings 재로드 + 스토리지 초기화
    - 레이트 리밋 테스트 후 settings가 변경될 수 있으므로 재로드하여 비활성화 보장
    - 레이트 리밋 스토리지도 초기화하여 이전 테스트의 카운트가 영향을 주지 않도록 함
    """
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db.session import _session_manager

    # 환경변수를 명시적으로 설정하고 settings 재로드
    # (레이트 리밋 테스트에서 환경변수가 변경될 수 있음)
    os.environ["RATE_LIMIT_ENABLED"] = "false"
    os.environ["OIDC_ENABLED"] = "false"
    os.environ["WS_RATE_LIMIT_ENABLED"] = "false"  # WebSocket 레이트 리밋 비활성화

    from app.core.config import Settings
    import app.core.config as config_module
    # 전역 settings 객체 교체는 반드시 finally에서 원본으로 복원 —
    # 미복원 시 모듈 레벨에서 settings를 바인딩한 코드(alembic env.py 등)가
    # 다른 객체를 보게 되어 테스트 간 간섭이 생긴다
    original_settings = config_module.settings
    config_module.settings = Settings()

    # 레이트 리밋 스토리지 초기화 (이전 테스트의 카운트 제거)
    from app.ratelimit.storage.memory import reset_storage
    from app.ratelimit.websocket import reset_ws_limiter
    reset_storage()
    reset_ws_limiter()  # WebSocket 리미터도 초기화

    test_engine = _create_test_engine()

    # SessionManager의 엔진을 테스트용으로 임시 교체 (init_db 전에 교체)
    original_engine = _session_manager.engine
    _session_manager.engine = test_engine

    # 테이블 생성 (교체된 엔진에 대해)
    SQLModel.metadata.create_all(test_engine)

    try:
        # TestClient 생성 (lifespan이 실행되지만 이미 테이블이 생성되어 있음)
        client = TestClient(app)
        yield client
    finally:
        # 원래 엔진으로 복원
        _session_manager.engine = original_engine
        # 테스트용 엔진 정리
        SQLModel.metadata.drop_all(test_engine)
        test_engine.dispose()
        # 전역 settings 원본 복원
        config_module.settings = original_settings


@pytest.fixture
def multi_user_e2e():
    """
    다중 사용자 E2E 테스트용 fixture
    
    여러 사용자를 시뮬레이션하여 사용자 간 기능을 테스트합니다.
    
    사용법:
        def test_shared_resource(multi_user_e2e):
            client_a = multi_user_e2e.as_user("user-a")
            client_b = multi_user_e2e.as_user("user-b")
            
            # user-a로 리소스 생성
            response = client_a.post("/v1/items", json={...})
            
            # user-b로 친구 요청 수락 등
            ...
    """
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.auth import get_current_user, get_optional_current_user
    from app.db.session import _session_manager

    # 환경변수 설정 및 settings 재로드
    os.environ["RATE_LIMIT_ENABLED"] = "false"
    os.environ["OIDC_ENABLED"] = "false"
    os.environ["WS_RATE_LIMIT_ENABLED"] = "false"  # WebSocket 레이트 리밋 비활성화

    from app.core.config import Settings
    import app.core.config as config_module
    # 전역 settings 객체 교체는 finally에서 원본 복원 (e2e_client와 동일 이유)
    original_settings = config_module.settings
    config_module.settings = Settings()

    from app.ratelimit.storage.memory import reset_storage
    from app.ratelimit.websocket import reset_ws_limiter
    reset_storage()
    reset_ws_limiter()  # WebSocket 리미터도 초기화

    test_engine = _create_test_engine()

    original_engine = _session_manager.engine
    _session_manager.engine = test_engine

    SQLModel.metadata.create_all(test_engine)

    class UserBoundClient:
        """
        특정 사용자로 바인딩된 TestClient 래퍼
        
        각 요청 전에 올바른 사용자 override를 설정합니다.
        """

        def __init__(self, client: TestClient, user: CurrentUser, app_ref, get_current_user_ref,
                     get_optional_current_user_ref):
            self._client = client
            self._user = user
            self._app = app_ref
            self._get_current_user = get_current_user_ref
            self._get_optional_current_user = get_optional_current_user_ref

        def _set_user_override(self):
            """요청 전에 현재 사용자로 override 설정"""
            user = self._user
            self._app.dependency_overrides[self._get_current_user] = lambda: user
            self._app.dependency_overrides[self._get_optional_current_user] = lambda: user

        def get(self, *args, **kwargs):
            self._set_user_override()
            return self._client.get(*args, **kwargs)

        def post(self, *args, **kwargs):
            self._set_user_override()
            return self._client.post(*args, **kwargs)

        def put(self, *args, **kwargs):
            self._set_user_override()
            return self._client.put(*args, **kwargs)

        def patch(self, *args, **kwargs):
            self._set_user_override()
            return self._client.patch(*args, **kwargs)

        def delete(self, *args, **kwargs):
            self._set_user_override()
            return self._client.delete(*args, **kwargs)

    class MultiUserTestClient:
        """
        다중 사용자 테스트 클라이언트
        
        각 사용자별로 독립적인 UserBoundClient를 반환합니다.
        동일한 DB를 공유하지만 인증된 사용자가 다릅니다.
        """

        def __init__(self):
            self._users: dict[str, CurrentUser] = {}
            self._client = TestClient(app)
            self._original_dependency = app.dependency_overrides.get(get_current_user)

        def as_user(self, user_id: str, email: str = None, name: str = None) -> UserBoundClient:
            """
            특정 사용자로 인증된 클라이언트 반환
            
            :param user_id: 사용자 ID (sub claim)
            :param email: 이메일 (기본값: {user_id}@example.com)
            :param name: 이름 (기본값: User {user_id})
            :return: 해당 사용자로 인증된 클라이언트
            """
            if user_id not in self._users:
                self._users[user_id] = make_user(user_id, email, name)

            return UserBoundClient(
                self._client,
                self._users[user_id],
                app,
                get_current_user,
                get_optional_current_user
            )

        def get_user(self, user_id: str) -> CurrentUser:
            """특정 사용자 ID에 대한 CurrentUser 객체 반환"""
            if user_id in self._users:
                return self._users[user_id]
            return make_user(user_id)

        def cleanup(self):
            """클라이언트 정리 및 override 복원"""
            self._client.close()
            self._users.clear()

            # 원래 dependency 복원
            if self._original_dependency is not None:
                app.dependency_overrides[get_current_user] = self._original_dependency
            elif get_current_user in app.dependency_overrides:
                del app.dependency_overrides[get_current_user]

            # get_optional_current_user override도 정리
            if get_optional_current_user in app.dependency_overrides:
                del app.dependency_overrides[get_optional_current_user]

    multi_client = MultiUserTestClient()

    try:
        yield multi_client
    finally:
        multi_client.cleanup()
        _session_manager.engine = original_engine
        SQLModel.metadata.drop_all(test_engine)
        test_engine.dispose()
        # 전역 settings 원본 복원
        config_module.settings = original_settings


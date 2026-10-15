"""Fixture dùng chung. T0.6 sẽ mở rộng (DB test từ migration, fixture đăng nhập, factories)."""

import io
import json
import logging
from contextlib import asynccontextmanager

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.log import BoLocRequestId, JsonFormatter
from scripts.so_sanh_schema import cau_truc_tu_model, chay_alembic, db_tam


@pytest.fixture
async def engine_tam():
    """CSDL tạm riêng cho một test: tạo mới trước test, xóa sau test (không đụng DB dev)."""
    async with db_tam(settings.DATABASE_URL, "nha_thuoc_t") as engine:
        yield engine


@pytest.fixture
async def engine_co_bang(engine_tam):
    """CSDL tạm đã có đủ 65 bảng tạo từ model (create_all)."""
    await cau_truc_tu_model(engine_tam)
    return engine_tam


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def engine_migration():
    """Database tạm dựng bằng `alembic upgrade head`, dùng chung cho cả module.

    Module dùng fixture này phải đặt `pytestmark = pytest.mark.asyncio(loop_scope="module")`. T0.6 sẽ thay bằng một DB
    cho cả phiên test.
    """
    async with db_tam(settings.DATABASE_URL, "nha_thuoc_mig") as engine:
        await chay_alembic(engine, "upgrade", "head")
        yield engine


@pytest_asyncio.fixture(loop_scope="module")
async def db(engine_migration):
    """Session cho một test, nằm trong transaction được rollback khi test xong (`flush()` thấy dữ liệu, không lưu lại).

    `commit()` trong code được test chỉ giải phóng savepoint, không ghi thật.
    """
    async with engine_migration.connect() as conn:
        giao_dich = await conn.begin()
        session = AsyncSession(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await giao_dich.rollback()


@pytest.fixture
def mo_client():
    """Trả hàm mở httpx client gọi thẳng vào một app ASGI."""

    @asynccontextmanager
    async def _mo(app, **tuy_chon):
        transport = httpx.ASGITransport(app=app, **tuy_chon)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    return _mo


@pytest.fixture
def bat_log():
    """Gắn handler JSON vào logger "app" và trả hàm đọc lại các dòng log đã ghi."""
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(BoLocRequestId())
    logger = logging.getLogger("app")
    cu = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    def doc_dong():
        return [json.loads(d) for d in buf.getvalue().splitlines() if d.strip()]

    yield doc_dong
    logger.removeHandler(handler)
    logger.setLevel(cu)

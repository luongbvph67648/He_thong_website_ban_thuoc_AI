"""Fixture dùng chung. T0.6 sẽ mở rộng (DB test từ migration, fixture đăng nhập, factories)."""

import uuid
from contextlib import asynccontextmanager

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings


@pytest.fixture
async def engine_tam():
    """CSDL tạm riêng cho một test: tạo mới trước test, xóa sau test (không đụng DB dev)."""
    goc = make_url(settings.DATABASE_URL)
    ten = f"nha_thuoc_t_{uuid.uuid4().hex[:12]}"
    admin = create_async_engine(goc.set(database="postgres"), isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{ten}"'))
    engine = create_async_engine(goc.set(database=ten))
    try:
        yield engine
    finally:
        await engine.dispose()
        async with admin.connect() as conn:
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{ten}" WITH (FORCE)'))
        await admin.dispose()


@pytest.fixture
def mo_client():
    """Trả hàm mở httpx client gọi thẳng vào một app ASGI."""

    @asynccontextmanager
    async def _mo(app, **tuy_chon):
        transport = httpx.ASGITransport(app=app, **tuy_chon)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    return _mo

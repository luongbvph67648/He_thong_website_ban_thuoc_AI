"""Fixture dùng chung. T0.6 sẽ mở rộng (DB test từ migration, fixture đăng nhập, factories)."""

import io
import json
import logging
from contextlib import asynccontextmanager

import httpx
import pytest

from app.core.config import settings
from app.core.log import BoLocRequestId, JsonFormatter
from scripts.so_sanh_schema import cau_truc_tu_model, db_tam


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

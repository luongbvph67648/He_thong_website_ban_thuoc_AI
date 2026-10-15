"""T0.1: GET /api/v1/health truy vấn thật xuống CSDL."""

import httpx
import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.db import get_engine
from app.main import app


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def test_health_ok(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"trang_thai": "ok", "db": "ok"}


async def test_health_db_loi_tra_503(client):
    # Cổng 1 không có CSDL nào lắng nghe.
    engine = create_async_engine("postgresql+asyncpg://x:x@127.0.0.1:1/x")
    app.dependency_overrides[get_engine] = lambda: engine
    try:
        resp = await client.get("/api/v1/health")
    finally:
        await engine.dispose()
    assert resp.status_code == 503
    assert resp.json() == {"trang_thai": "loi", "db": "loi"}

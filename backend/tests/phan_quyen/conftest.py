import pytest_asyncio

from app.core.bao_mat import tao_access_token
from tests.factories import tao_nhan_vien
from tests.phan_quyen.ma_tran import VAI_TRO


@pytest_asyncio.fixture
async def clients_theo_vai_tro(app, db):
    """Ba client đã đăng nhập, mỗi vai trò một: `{"PHARMACIST": client, "WAREHOUSE": ..., "ADMIN": ...}`."""
    import httpx

    clients = {}
    for vai_tro in VAI_TRO:
        nv = await tao_nhan_vien(db, vai_tro)
        clients[vai_tro] = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {tao_access_token(nv.id, 'noi_bo')}"},
        )
    yield clients
    for c in clients.values():
        await c.aclose()

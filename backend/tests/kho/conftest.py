"""Mọi test của module `kho` dùng `db` đều kết thúc bằng kiểm tra bất biến tồn kho (spec 10 mục 4)."""

import pytest_asyncio

from tests.bat_bien.kiem_tra import kiem_tra_bat_bien


@pytest_asyncio.fixture
async def db(db, request):
    """Ghi đè `db` dùng chung: kiểm tra trước khi `db` rollback. Test cố ý làm sai số liệu thì đánh dấu
    `@pytest.mark.khong_kiem_bat_bien`."""
    yield db
    if request.node.get_closest_marker("khong_kiem_bat_bien") is None:
        assert await kiem_tra_bat_bien(db) == []

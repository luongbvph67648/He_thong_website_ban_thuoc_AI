"""T8.2: nhật ký hệ thống chỉ INSERT, được bảo đảm ở DB bằng trigger (migration 0003)."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.nhat_ky import ghi_nhat_ky


async def test_khong_sua_duoc_nhat_ky(db):
    dong = await ghi_nhat_ky(db, nhan_vien_id=None, hanh_dong="tao", bang="san_pham", ban_ghi_id="1")
    with pytest.raises(DBAPIError, match="chỉ được INSERT"):
        async with db.begin_nested():
            await db.execute(text("UPDATE nhat_ky_he_thong SET hanh_dong = 'xoa' WHERE id = :i"), {"i": dong.id})


async def test_khong_xoa_duoc_nhat_ky(db):
    dong = await ghi_nhat_ky(db, nhan_vien_id=None, hanh_dong="tao", bang="san_pham", ban_ghi_id="1")
    with pytest.raises(DBAPIError, match="chỉ được INSERT"):
        async with db.begin_nested():
            await db.execute(text("DELETE FROM nhat_ky_he_thong WHERE id = :i"), {"i": dong.id})


async def test_van_insert_duoc_va_co_index_created_at(db):
    await ghi_nhat_ky(db, nhan_vien_id=None, hanh_dong="sua", bang="san_pham", ban_ghi_id="2")
    ten = await db.scalar(text("SELECT indexname FROM pg_indexes WHERE indexname = 'ix_nhat_ky_he_thong__created_at'"))
    assert ten == "ix_nhat_ky_he_thong__created_at"

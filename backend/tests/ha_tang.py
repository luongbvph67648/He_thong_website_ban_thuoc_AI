"""Hạ tầng database cho test: tạo lại database test và dọn dữ liệu sau các test commit thật."""

import re

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.seed.co_ban import seed_co_ban

# Dữ liệu seed cơ bản giữ nguyên giữa các test. `cau_hinh` có khóa ngoại tới `nhan_vien` nên phải TRUNCATE cùng
# `nhan_vien` rồi seed lại. `quyen` và `vai_tro_quyen` cũng TRUNCATE rồi seed lại: seed cố ý không ghi đè phân quyền
# đã có (để không phá chỉnh sửa của Admin), nên test AD18 commit thật sẽ để lại ma trận lệch cho test sau.
BANG_GIU_LAI = ("vai_tro", "alembic_version")


async def tao_lai_database(url: str) -> None:
    """Xóa (nếu có) rồi tạo mới database trong `url`.

    Chỉ chấp nhận tên có chữ "test" để một biến môi trường trỏ nhầm vào database dev không bị xóa mất dữ liệu.
    """
    goc = make_url(url)
    ten = goc.database or ""
    if not re.fullmatch(r"[A-Za-z0-9_]+", ten) or "test" not in ten.lower():
        raise ValueError(f"Từ chối xóa database {ten!r}: tên phải gồm chữ/số/gạch dưới và có chữ 'test'")
    admin = create_async_engine(goc.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{ten}" WITH (FORCE)'))
            await conn.execute(text(f'CREATE DATABASE "{ten}"'))
    finally:
        await admin.dispose()


async def don_dep_sau_commit(engine: AsyncEngine) -> None:
    """Xóa mọi dữ liệu test đã commit thật, giữ lại vai trò và khôi phục quyền, phân quyền, cấu hình về mặc định."""
    async with engine.begin() as conn:
        ten_bang = (
            await conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND NOT (tablename = ANY(:giu))"),
                {"giu": list(BANG_GIU_LAI)},
            )
        ).scalars()
        danh_sach = ", ".join(f'"{b}"' for b in ten_bang)  # tên bảng lấy từ catalog, không từ input
        await conn.execute(text(f"TRUNCATE {danh_sach} RESTART IDENTITY"))
    async with AsyncSession(engine) as session, session.begin():
        await seed_co_ban(session)

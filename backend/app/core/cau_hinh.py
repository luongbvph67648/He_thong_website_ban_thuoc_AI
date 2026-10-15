"""Đọc cấu hình động từ bảng `cau_hinh` (Admin sửa được lúc chạy, spec 02 mục 6)."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.he_thong import CauHinh


async def doc_cau_hinh(db: AsyncSession, khoa: str, mac_dinh: Any) -> Any:
    """Giá trị của `khoa`; chưa có (hoặc JSON null) thì trả `mac_dinh`. Đọc mỗi lần để Admin đổi là có hiệu lực ngay."""
    gia_tri = (await db.execute(select(CauHinh.gia_tri).where(CauHinh.khoa == khoa))).scalar_one_or_none()
    return mac_dinh if gia_tri is None else gia_tri

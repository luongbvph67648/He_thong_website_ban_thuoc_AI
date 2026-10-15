"""Phân trang theo spec 06 mục 5: tham số trang/kich_thuoc, phản hồi {du_lieu, tong, trang, kich_thuoc}."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Query
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

KICH_THUOC_MAC_DINH = 20
KICH_THUOC_TOI_DA = 100
TRANG_TOI_DA = 1_000_000  # OFFSET quá lớn gây tràn int64 ở CSDL


@dataclass(frozen=True)
class ThamSoPhanTrang:
    trang: int = 1
    kich_thuoc: int = KICH_THUOC_MAC_DINH

    @property
    def offset(self) -> int:
        return (self.trang - 1) * self.kich_thuoc

    @property
    def limit(self) -> int:
        return self.kich_thuoc


def tham_so_phan_trang(
    trang: Annotated[int, Query(ge=1, le=TRANG_TOI_DA, description="Số trang, bắt đầu từ 1")] = 1,
    kich_thuoc: Annotated[
        int, Query(ge=1, le=KICH_THUOC_TOI_DA, description="Số dòng mỗi trang")
    ] = KICH_THUOC_MAC_DINH,
) -> ThamSoPhanTrang:
    return ThamSoPhanTrang(trang=trang, kich_thuoc=kich_thuoc)


PhanTrang = Annotated[ThamSoPhanTrang, Depends(tham_so_phan_trang)]
"""Dùng làm tham số của route: `async def ds(tp: PhanTrang): ...`"""


class Trang[T](BaseModel):
    """Phản hồi danh sách. Dùng làm `response_model=Trang[TenSchema]`."""

    du_lieu: list[T]
    tong: int
    trang: int
    kich_thuoc: int


def tao_trang[T](du_lieu: Sequence[T], tong: int, tham_so: ThamSoPhanTrang) -> Trang[T]:
    return Trang[T](du_lieu=list(du_lieu), tong=tong, trang=tham_so.trang, kich_thuoc=tham_so.kich_thuoc)


async def dem_tong(db: AsyncSession, stmt: Select[Any]) -> int:
    """Đếm tổng số dòng của truy vấn (bỏ ORDER BY cho nhẹ)."""
    return await db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0


async def lay_trang(db: AsyncSession, stmt: Select[Any], tham_so: ThamSoPhanTrang) -> tuple[Sequence[Any], int]:
    """Lấy một trang của truy vấn đã có ORDER BY. Trả (các dòng, tổng). Truy vấn chọn một thực thể/cột (scalars)."""
    tong = await dem_tong(db, stmt)
    ket_qua = await db.scalars(stmt.limit(tham_so.limit).offset(tham_so.offset))
    return ket_qua.all(), tong

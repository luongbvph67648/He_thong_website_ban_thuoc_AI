"""Phân trang theo spec 06 mục 5: tham số trang/kich_thuoc, phản hồi {du_lieu, tong, trang, kich_thuoc}."""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Query
from pydantic import BaseModel
from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu

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

SapXepQuery = Annotated[
    str | None,
    Query(
        max_length=40,
        pattern=r"^-?[a-z][a-z0-9_]{0,38}$",
        description="Sắp xếp theo một trường, dấu `-` phía trước là giảm dần, ví dụ `-created_at`",
    ),
]
"""Tham số `sap_xep` của route danh sách; truyền tiếp cho `sap_xep_theo` cùng danh sách trường cho phép của endpoint."""

_KHOP_SAP_XEP = re.compile(r"^(-?)([a-z][a-z0-9_]*)$")


def sap_xep_theo(
    stmt: Select[Any],
    sap_xep: str | None,
    cho_phep: Mapping[str, ColumnElement[Any]],
    *,
    mac_dinh: str,
    khoa_phu: ColumnElement[Any],
) -> Select[Any]:
    """Thêm ORDER BY theo `sap_xep` (spec 06 mục 5): `ten_truong` tăng dần, `-ten_truong` giảm dần.

    `cho_phep` ánh xạ tên trường trong API sang cột/biểu thức SQL; tên ngoài danh sách là `400` (không bao giờ ghép tên
    do client gửi vào SQL). `khoa_phu` (thường là id) được thêm sau cùng, cùng chiều, để thứ tự ổn định giữa các trang
    khi giá trị trùng nhau. NULL luôn xếp cuối.
    """
    if mac_dinh.removeprefix("-") not in cho_phep:
        raise ValueError(f"mac_dinh {mac_dinh!r} phải nằm trong danh sách trường cho phép")
    gia_tri = mac_dinh if sap_xep is None else sap_xep
    khop = _KHOP_SAP_XEP.match(gia_tri)
    if khop is None or khop.group(2) not in cho_phep:
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE",
            "Dữ liệu không hợp lệ",
            chi_tiet=[{"truong": "sap_xep", "loi": f"Chỉ sắp xếp được theo: {', '.join(sorted(cho_phep))}"}],
        )
    cot = cho_phep[khop.group(2)]
    giam = khop.group(1) == "-"
    return stmt.order_by(
        cot.desc().nulls_last() if giam else cot.asc().nulls_last(),
        khoa_phu.desc() if giam else khoa_phu.asc(),
    )


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


async def lay_trang(
    db: AsyncSession, stmt: Select[Any], tham_so: ThamSoPhanTrang, *, nhieu_cot: bool = False
) -> tuple[Sequence[Any], int]:
    """Lấy một trang của truy vấn đã có ORDER BY. Trả (các dòng, tổng).

    Mặc định truy vấn chọn một thực thể/cột và trả giá trị đó (scalars); truy vấn chọn nhiều cột (thực thể kèm số
    đếm...) đặt `nhieu_cot=True` để nhận từng dòng là một `Row`."""
    tong = await dem_tong(db, stmt)
    ket_qua = await db.execute(stmt.limit(tham_so.limit).offset(tham_so.offset))
    return (ket_qua.all() if nhieu_cot else ket_qua.scalars().all()), tong

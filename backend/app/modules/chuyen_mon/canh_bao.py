"""Cảnh báo tương tác thuốc và dị ứng (DS10, dùng lại ở DS04, DS05, DS07, DS08 và lọc gợi ý của AI).

Cả hai hàm chỉ trả CẢNH BÁO có mức độ, không trả dữ liệu gốc: `kiem_tra_di_ung` đọc bảng `di_ung` (dữ liệu sức khỏe,
CLAUDE.md quy tắc 7) bên trong service nhưng không trả `ghi_chu` hay danh sách dị ứng của khách; cũng không ghi gì ra
log. Người gọi quyết định ai được xem cảnh báo (khách xem của mình, dược sĩ khi đang xử lý yêu cầu của khách đó); hàm
này không phải là "cổng đọc hồ sơ" nên không thay `duoc_doc_ho_so_suc_khoe` (spec 03 mục 5.1).
"""

from collections.abc import Iterable
from itertools import product
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.enums import MucDoTuongTac
from app.models.khach_hang import DiUng
from app.models.san_pham import HoatChat, SanPham, ThanhPhan, TuongTacHoatChat
from app.modules.chuyen_mon.tuong_tac import MUC_DO_NANG_DAN


class CanhBaoTuongTac(BaseModel):
    """Hai hoạt chất tương tác khi dùng cùng nhau, nằm ở hai sản phẩm KHÁC nhau trong danh sách đang kiểm."""

    loai: Literal["tuong_tac"] = "tuong_tac"
    muc_do: MucDoTuongTac
    hoat_chat_a_id: int
    ten_hoat_chat_a: str
    san_pham_a_id: int
    """Sản phẩm chứa hoạt chất A (id nhỏ hơn)."""
    hoat_chat_b_id: int
    ten_hoat_chat_b: str
    san_pham_b_id: int
    co_che: str | None
    khuyen_cao: str


class CanhBaoDiUng(BaseModel):
    """Sản phẩm chứa hoạt chất mà khách đã khai dị ứng. Cố ý KHÔNG có ghi chú hay chi tiết hồ sơ của khách."""

    loai: Literal["di_ung"] = "di_ung"
    muc_do: MucDoTuongTac = MucDoTuongTac.chong_chi_dinh
    """Dị ứng với hoạt chất luôn là chống chỉ định (bảng `di_ung` không có mức độ riêng)."""
    san_pham_id: int
    ten_san_pham: str
    hoat_chat_id: int
    ten_hoat_chat: str


def _ids(ds: Iterable[int]) -> list[int]:
    return sorted(set(ds))


async def kiem_tra_tuong_tac(db: AsyncSession, ds_san_pham_id: Iterable[int]) -> list[CanhBaoTuongTac]:
    """Cảnh báo cho mọi cặp hoạt chất có tương tác mà hai hoạt chất nằm ở hai sản phẩm KHÁC nhau của danh sách.

    Hai hoạt chất cùng nằm trong một sản phẩm duy nhất (thuốc phối hợp do nhà sản xuất bào chế) không bị báo. Sắp xếp
    nặng nhất trước (`chong_chi_dinh`, `nghiem_trong`, `trung_binh`, `nhe`); mỗi cặp hoạt chất và mỗi cặp sản phẩm
    một dòng.
    """
    san_pham_ids = _ids(ds_san_pham_id)
    if len(san_pham_ids) < 2:
        return []
    thanh_phan = (
        await db.execute(
            select(ThanhPhan.san_pham_id, ThanhPhan.hoat_chat_id).where(ThanhPhan.san_pham_id.in_(san_pham_ids))
        )
    ).all()
    san_pham_cua: dict[int, set[int]] = {}
    for sp_id, hc_id in thanh_phan:
        san_pham_cua.setdefault(hc_id, set()).add(sp_id)
    if len(san_pham_cua) < 2:
        return []
    a, b = aliased(HoatChat), aliased(HoatChat)
    cac_cap = (
        await db.execute(
            select(TuongTacHoatChat, a.ten, b.ten)
            .join(a, a.id == TuongTacHoatChat.hoat_chat_a_id)
            .join(b, b.id == TuongTacHoatChat.hoat_chat_b_id)
            .where(
                TuongTacHoatChat.hoat_chat_a_id.in_(san_pham_cua),
                TuongTacHoatChat.hoat_chat_b_id.in_(san_pham_cua),
            )
        )
    ).all()
    canh_bao: list[CanhBaoTuongTac] = []
    for tt, ten_a, ten_b in cac_cap:
        for sp_a, sp_b in product(sorted(san_pham_cua[tt.hoat_chat_a_id]), sorted(san_pham_cua[tt.hoat_chat_b_id])):
            if sp_a == sp_b:
                continue
            canh_bao.append(
                CanhBaoTuongTac(
                    muc_do=tt.muc_do,
                    hoat_chat_a_id=tt.hoat_chat_a_id,
                    ten_hoat_chat_a=ten_a,
                    san_pham_a_id=sp_a,
                    hoat_chat_b_id=tt.hoat_chat_b_id,
                    ten_hoat_chat_b=ten_b,
                    san_pham_b_id=sp_b,
                    co_che=tt.co_che,
                    khuyen_cao=tt.khuyen_cao,
                )
            )
    canh_bao.sort(
        key=lambda c: (-MUC_DO_NANG_DAN[c.muc_do], c.hoat_chat_a_id, c.hoat_chat_b_id, c.san_pham_a_id, c.san_pham_b_id)
    )
    return canh_bao


async def kiem_tra_di_ung(db: AsyncSession, khach_hang_id: int, ds_san_pham_id: Iterable[int]) -> list[CanhBaoDiUng]:
    """Sản phẩm trong danh sách chứa hoạt chất mà khách đã khai dị ứng. Chỉ trả cảnh báo, không trả hồ sơ."""
    san_pham_ids = _ids(ds_san_pham_id)
    if not san_pham_ids:
        return []
    dong = (
        await db.execute(
            select(SanPham.id, SanPham.ten, HoatChat.id, HoatChat.ten)
            .join(ThanhPhan, ThanhPhan.san_pham_id == SanPham.id)
            .join(DiUng, DiUng.hoat_chat_id == ThanhPhan.hoat_chat_id)
            .join(HoatChat, HoatChat.id == ThanhPhan.hoat_chat_id)
            .where(DiUng.khach_hang_id == khach_hang_id, SanPham.id.in_(san_pham_ids))
            .order_by(SanPham.id, HoatChat.id)
        )
    ).all()
    return [
        CanhBaoDiUng(san_pham_id=sp_id, ten_san_pham=ten_sp, hoat_chat_id=hc_id, ten_hoat_chat=ten_hc)
        for sp_id, ten_sp, hc_id, ten_hc in dong
    ]

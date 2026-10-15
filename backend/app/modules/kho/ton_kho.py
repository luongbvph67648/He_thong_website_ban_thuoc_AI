"""Dịch vụ tồn kho: nơi DUY NHẤT được đổi `so_luong_ton`, `so_luong_giu`, `so_luong_biet_tru` (CLAUDE.md quy tắc 2).

Mọi hàm nhận `db` đang trong transaction, tự khóa các lô liên quan bằng `SELECT ... FOR UPDATE` theo id tăng dần rồi mới
tính toán, và ghi `bien_dong_kho` trong cùng transaction (spec 04 mục 3). Hiện mới có phần nhập kho; các hàm giữ hàng,
xuất, hoàn nhập, biệt trữ, trừ tồn, điều chỉnh thêm ở T3.1 và T4.x.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.thoi_gian import bay_gio_utc
from app.models.enums import KhuTon, LoaiBienDong
from app.models.kho import BienDongKho, LoThuoc


@dataclass(frozen=True)
class ChungTu:
    """Chứng từ gây ra biến động: `loai` là tên bảng (`phieu_nhap`, `don_hang`...). `nhan_vien_id` None = hệ thống."""

    loai: str
    id: int
    nhan_vien_id: int | None = None


async def khoa_cac_lo(db: AsyncSession, lo_ids: Iterable[int]) -> list[LoThuoc]:
    """Khóa các lô (FOR UPDATE) theo id tăng dần và trả về theo thứ tự đó.

    Thứ tự cố định giữa mọi giao dịch để hai giao dịch khóa chung nhiều lô không bao giờ chờ vòng tròn (deadlock).
    Các đối tượng đã nạp từ trước được làm mới theo dòng vừa khóa, nên số liệu tồn luôn là bản đã commit mới nhất.
    """
    ids = sorted(set(lo_ids))
    if not ids:
        return []
    truy_van = (
        select(LoThuoc)
        .where(LoThuoc.id.in_(ids))
        .order_by(LoThuoc.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    lo_thuoc = list((await db.execute(truy_van)).scalars())
    thieu = set(ids) - {lo.id for lo in lo_thuoc}
    if thieu:
        raise LookupError(f"Không tìm thấy lô: {sorted(thieu)}")
    return lo_thuoc


def _kiem_tra_so_luong(so_luong: int) -> None:
    if isinstance(so_luong, bool) or not isinstance(so_luong, int):
        raise TypeError(f"so_luong phải là số nguyên, nhận {type(so_luong).__name__}")
    if so_luong <= 0:
        raise ValueError("so_luong phải lớn hơn 0")


async def nhap_kho(db: AsyncSession, lo: LoThuoc, so_luong: int, chung_tu: ChungTu) -> BienDongKho:
    """Cộng `so_luong` (đơn vị cơ sở) vào tồn kho bán của lô và ghi thẻ kho `nhap_kho`."""
    _kiem_tra_so_luong(so_luong)
    (lo_khoa,) = await khoa_cac_lo(db, [lo.id])
    lo_khoa.so_luong_ton += so_luong
    lo_khoa.updated_at = bay_gio_utc()
    bien_dong = BienDongKho(
        lo_id=lo_khoa.id,
        loai=LoaiBienDong.nhap_kho,
        khu=KhuTon.kho_ban,
        so_luong=so_luong,
        ton_sau=lo_khoa.so_luong_ton,
        chung_tu_loai=chung_tu.loai,
        chung_tu_id=chung_tu.id,
        nhan_vien_id=chung_tu.nhan_vien_id,
    )
    db.add(bien_dong)
    await db.flush()
    return bien_dong

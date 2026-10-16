"""Hàm dùng chung của test cửa hàng công khai (KVL01–KVL03)."""

from datetime import timedelta

from sqlalchemy import select

from app.core.thoi_gian import bay_gio_utc
from app.models.ban_hang import CtDonHang
from app.models.he_thong import Banner
from app.models.khach_hang import DanhGia, KhachHang
from app.models.san_pham import SanPham
from tests.factories import tao_don, tao_khach, tao_lo, tao_san_pham

GOC = "/api/v1"


def ten_the(phan_hoi) -> list[str]:
    return [sp["ten"] for sp in phan_hoi.json()["du_lieu"]]


async def sp_ban_duoc(db, ten: str | None = None, ton: int = 10, **truong) -> SanPham:
    """Sản phẩm hiển thị được, có `ton` đơn vị cơ sở ở lô đang bán còn hạn dài."""
    if ten is not None:
        truong["ten"] = ten
    sp = await tao_san_pham(db, **truong)
    if ton:
        await tao_lo(db, sp, so_luong=ton)
    return sp


async def dat_ban_chay(db, sp: SanPham, so_dong: int, *, tuoi_ngay: int = 1, trang_thai: str = "hoan_tat") -> None:
    """`so_dong` đơn một dòng của `sp`, tạo cách đây `tuoi_ngay` ngày."""
    khach = await tao_khach(db)
    for _ in range(so_dong):
        await tao_don(
            db,
            khach,
            trang_thai=trang_thai,
            dong=[{"san_pham": sp, "so_luong": 1}],
            created_at=bay_gio_utc() - timedelta(days=tuoi_ngay),
        )


async def tao_danh_gia(db, sp: SanPham, khach: KhachHang, so_sao: int, **truong) -> DanhGia:
    don = await tao_don(db, khach, trang_thai="hoan_tat", dong=[{"san_pham": sp, "so_luong": 1}])
    ct_id = await db.scalar(select(CtDonHang.id).where(CtDonHang.don_hang_id == don.id))
    dg = DanhGia(san_pham_id=sp.id, khach_hang_id=khach.id, ct_don_hang_id=ct_id, so_sao=so_sao, **truong)
    db.add(dg)
    await db.flush()
    return dg


async def tao_banner(db, vi_tri: str = "trang_chu_chinh", **truong) -> Banner:
    b = Banner(**{"anh_url": "/api/v1/tep/banner/a.jpg", "vi_tri": vi_tri, **truong})
    db.add(b)
    await db.flush()
    return b

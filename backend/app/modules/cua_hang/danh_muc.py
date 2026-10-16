"""Danh mục và banner công khai (KVL01)."""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc
from app.models.he_thong import Banner
from app.models.san_pham import DanhMuc
from app.modules.cua_hang.hien_thi import CayHienThi, nap_cay_hien_thi
from app.modules.cua_hang.schemas import BannerCongKhai, DanhMucChiTiet, DanhMucCongKhai, MucDuongDan


def _nut(cay: CayHienThi, d: DanhMuc) -> DanhMucCongKhai:
    return DanhMucCongKhai(
        id=d.id, ten=d.ten, slug=d.slug, anh_url=d.anh_url, con=[_nut(cay, c) for c in cay.con.get(d.id, [])]
    )


async def cay_cong_khai(db: AsyncSession) -> list[DanhMucCongKhai]:
    cay = await nap_cay_hien_thi(db)
    return [_nut(cay, d) for d in cay.con.get(None, [])]


async def chi_tiet_theo_slug(db: AsyncSession, slug: str) -> DanhMucChiTiet:
    cay = await nap_cay_hien_thi(db)
    d = cay.theo_slug(slug)
    if d is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy danh mục")
    return DanhMucChiTiet(
        id=d.id,
        ten=d.ten,
        slug=d.slug,
        anh_url=d.anh_url,
        duong_dan=[MucDuongDan(ten=m.ten, slug=m.slug) for m in cay.duong_dan(d.id)],
        con=[_nut(cay, c) for c in cay.con.get(d.id, [])],
    )


async def banner_dang_hien(db: AsyncSession, vi_tri: str | None = None) -> list[BannerCongKhai]:
    """Banner `dang_hien` trong khoảng thời gian hiệu lực (bỏ trống một đầu là không giới hạn đầu đó)."""
    bay_gio = bay_gio_utc()
    stmt = select(Banner).where(
        Banner.dang_hien.is_(True),
        or_(Banner.bat_dau.is_(None), Banner.bat_dau <= bay_gio),
        or_(Banner.ket_thuc.is_(None), Banner.ket_thuc > bay_gio),
    )
    if vi_tri is not None:
        stmt = stmt.where(Banner.vi_tri == vi_tri)
    dong = (await db.execute(stmt.order_by(Banner.thu_tu, Banner.id))).scalars()
    return [
        BannerCongKhai(id=b.id, tieu_de=b.tieu_de, anh_url=b.anh_url, lien_ket=b.lien_ket, vi_tri=b.vi_tri)
        for b in dong
    ]

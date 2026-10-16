"""Tra cứu tồn kho (KHO05, spec 06 mục 3.16). Dược sĩ chỉ thấy tồn khả dụng; giá nhập, số đang giữ và biệt trữ chỉ
dành cho vai trò có quyền nhập kho (`stock.import`)."""

from datetime import date

from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.core.phan_trang import ThamSoPhanTrang, Trang, lay_trang, tao_trang
from app.core.thoi_gian import hom_nay_vn
from app.core.tien import TienDoc
from app.core.tim_kiem import mau_tim_like
from app.models.enums import TrangThaiLo
from app.models.kho import LoThuoc
from app.models.san_pham import SanPham
from app.modules.cua_hang.hien_thi import ton_kha_dung


class TonSanPham(BaseModel):
    san_pham_id: int
    sku: str
    ten: str
    don_vi_co_so: str
    ton_kha_dung: int
    ton_toi_thieu: int
    thap: bool
    tong_ton: int | None
    tong_giu: int | None
    tong_biet_tru: int | None
    so_lo: int


class TonLo(BaseModel):
    lo_id: int
    so_lo: str
    ngay_san_xuat: date | None
    han_su_dung: date
    trang_thai: TrangThaiLo
    kha_dung: int
    so_luong_ton: int | None
    so_luong_giu: int | None
    so_luong_biet_tru: int | None
    gia_nhap: TienDoc | None


async def danh_sach(
    db: AsyncSession, q: str | None, chi_thap: bool, tp: ThamSoPhanTrang, *, xem_day_du: bool
) -> Trang[TonSanPham]:
    kd = ton_kha_dung(hom_nay_vn())
    tong = lambda cot: (  # noqa: E731
        select(func.coalesce(func.sum(cot), 0))
        .where(LoThuoc.san_pham_id == SanPham.id)
        .correlate(SanPham)
        .scalar_subquery()
    )
    so_lo = select(func.count()).where(LoThuoc.san_pham_id == SanPham.id).correlate(SanPham).scalar_subquery()
    stmt = select(
        SanPham,
        kd.label("kd"),
        tong(LoThuoc.so_luong_ton).label("ton"),
        tong(LoThuoc.so_luong_giu).label("giu"),
        tong(LoThuoc.so_luong_biet_tru).label("bt"),
        so_lo.label("so_lo"),
    ).where(SanPham.deleted_at.is_(None))
    if q and q.strip():
        mau = mau_tim_like(q)
        stmt = stmt.where(
            or_(
                func.f_unaccent(func.lower(SanPham.ten)).like(func.f_unaccent(func.lower(mau)), escape="\\"),
                func.upper(SanPham.sku).like(func.upper(mau), escape="\\"),
            )
        )
    if chi_thap:
        stmt = stmt.where(SanPham.ton_toi_thieu > 0, kd < SanPham.ton_toi_thieu)
    dong, so = await lay_trang(db, stmt.order_by(SanPham.ten, SanPham.id), tp, nhieu_cot=True)
    return tao_trang(
        [
            TonSanPham(
                san_pham_id=sp.id,
                sku=sp.sku,
                ten=sp.ten,
                don_vi_co_so=sp.don_vi_co_so,
                ton_kha_dung=int(k),
                ton_toi_thieu=sp.ton_toi_thieu,
                thap=sp.ton_toi_thieu > 0 and k < sp.ton_toi_thieu,
                tong_ton=int(t) if xem_day_du else None,
                tong_giu=int(g) if xem_day_du else None,
                tong_biet_tru=int(b) if xem_day_du else None,
                so_lo=n,
            )
            for sp, k, t, g, b, n in dong
        ],
        so,
        tp,
    )


async def cac_lo(db: AsyncSession, san_pham_id: int, *, xem_day_du: bool) -> list[TonLo]:
    if await db.scalar(select(SanPham.id).where(SanPham.id == san_pham_id, SanPham.deleted_at.is_(None))) is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy sản phẩm")
    lo_thuoc = (
        (
            await db.execute(
                select(LoThuoc).where(LoThuoc.san_pham_id == san_pham_id).order_by(LoThuoc.han_su_dung, LoThuoc.id)
            )
        )
        .scalars()
        .all()
    )
    return [
        TonLo(
            lo_id=lo.id,
            so_lo=lo.so_lo,
            ngay_san_xuat=lo.ngay_san_xuat,
            han_su_dung=lo.han_su_dung,
            trang_thai=lo.trang_thai,
            kha_dung=lo.so_luong_ton - lo.so_luong_giu,
            so_luong_ton=lo.so_luong_ton if xem_day_du else None,
            so_luong_giu=lo.so_luong_giu if xem_day_du else None,
            so_luong_biet_tru=lo.so_luong_biet_tru if xem_day_du else None,
            gia_nhap=lo.gia_nhap if xem_day_du else None,
        )
        for lo in lo_thuoc
    ]

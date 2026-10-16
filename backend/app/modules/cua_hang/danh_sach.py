"""Danh sách sản phẩm công khai: trang chủ, lọc và sắp xếp theo danh mục, bộ lọc (KVL01, KVL02)."""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.core.phan_trang import ThamSoPhanTrang, Trang, tao_trang
from app.core.thoi_gian import hom_nay_vn
from app.core.tim_kiem import mau_tim_like
from app.models.enums import LoaiSanPham
from app.models.san_pham import AnhSanPham, DonViQuyDoi, SanPham, ThuongHieu
from app.modules.cua_hang import danh_muc as dich_vu_danh_muc
from app.modules.cua_hang.hien_thi import (
    CayHienThi,
    ban_chay_30_ngay,
    chon_don_vi_gia,
    gia_hien_thi,
    la_hien_thi,
    nap_cay_hien_thi,
    ton_kha_dung,
)
from app.modules.cua_hang.schemas import BoLocSanPham, SanPhamThe, ThuongHieuLoc, TrangChu

SO_SAN_PHAM_TRANG_CHU = 12
TOI_DA_DOI_TUONG_LOC = 30
SapXep = Literal["moi", "gia_tang", "gia_giam", "ban_chay", "ten"]


@dataclass
class BoLoc:
    danh_muc_slug: str | None = None
    loai: LoaiSanPham | None = None
    thuong_hieu_ids: list[int] = field(default_factory=list)
    gia_tu: int | None = None
    gia_den: int | None = None
    doi_tuong: str | None = None
    con_hang: bool = False
    sap_xep: SapXep = "moi"


def _cac_dieu_kien(cay: CayHienThi, loc: BoLoc, gia: ColumnElement, ton: ColumnElement) -> list[ColumnElement[bool]]:
    pham_vi = cay.ids
    if loc.danh_muc_slug is not None:
        danh_muc = cay.theo_slug(loc.danh_muc_slug)
        if danh_muc is None:
            raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy danh mục")
        pham_vi = cay.con_chau_ids(danh_muc.id)
    dieu_kien = [la_hien_thi(pham_vi)]
    if loc.loai is not None:
        dieu_kien.append(SanPham.loai_san_pham == loc.loai)
    if loc.thuong_hieu_ids:
        dieu_kien.append(SanPham.thuong_hieu_id.in_(loc.thuong_hieu_ids))
    if loc.gia_tu is not None:
        dieu_kien.append(gia >= loc.gia_tu)
    if loc.gia_den is not None:
        dieu_kien.append(gia <= loc.gia_den)
    if loc.doi_tuong:
        mau = func.f_unaccent(func.lower(mau_tim_like(loc.doi_tuong)))
        dieu_kien.append(func.f_unaccent(func.lower(SanPham.doi_tuong_su_dung)).like(mau, escape="\\"))
    if loc.con_hang:
        dieu_kien.append(ton > 0)
    return dieu_kien


async def dung_the(db: AsyncSession, dong: Sequence) -> list[SanPhamThe]:
    """Dựng thẻ từ các dòng `(SanPham, ten_thuong_hieu, ton_kha_dung)`; đơn vị và ảnh cả trang nạp bằng 2 truy vấn."""
    if not dong:
        return []
    ids = [sp.id for sp, _, _ in dong]
    don_vi: dict[int, list[DonViQuyDoi]] = defaultdict(list)
    for d in (await db.execute(select(DonViQuyDoi).where(DonViQuyDoi.san_pham_id.in_(ids)))).scalars():
        don_vi[d.san_pham_id].append(d)
    anh: dict[int, str] = {}
    for a in (
        await db.execute(
            select(AnhSanPham)
            .where(AnhSanPham.san_pham_id.in_(ids))
            .order_by(AnhSanPham.la_anh_chinh.desc(), AnhSanPham.thu_tu, AnhSanPham.id)
        )
    ).scalars():
        anh.setdefault(a.san_pham_id, a.url)  # dòng đầu tiên của mỗi sản phẩm: ảnh chính, hoặc ảnh có thứ tự nhỏ nhất
    the = []
    for sp, thuong_hieu, ton in dong:
        dv = chon_don_vi_gia(don_vi[sp.id])
        the.append(
            SanPhamThe(
                id=sp.id,
                ten=sp.ten,
                slug=sp.slug,
                loai_san_pham=sp.loai_san_pham,
                can_tu_van=sp.loai_san_pham == LoaiSanPham.thuoc_ke_don,
                thuong_hieu=thuong_hieu,
                quy_cach=sp.quy_cach,
                anh_chinh_url=anh.get(sp.id),
                gia=dv.gia_ban if dv else None,
                ten_don_vi_gia=dv.ten_don_vi if dv else None,
                con_hang=ton > 0,
            )
        )
    return the


def chon_the() -> Select:
    return select(SanPham, ThuongHieu.ten, ton_kha_dung()).outerjoin(
        ThuongHieu, ThuongHieu.id == SanPham.thuong_hieu_id
    )


async def danh_sach(db: AsyncSession, loc: BoLoc, tp: ThamSoPhanTrang) -> Trang[SanPhamThe]:
    if loc.gia_tu is not None and loc.gia_den is not None and loc.gia_tu > loc.gia_den:
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE",
            "Dữ liệu không hợp lệ",
            chi_tiet=[{"truong": "gia_tu", "loi": "Giá từ không được lớn hơn giá đến"}],
        )
    cay = await nap_cay_hien_thi(db)
    gia, ton = gia_hien_thi(), ton_kha_dung(hom_nay_vn())
    ban_chay = ban_chay_30_ngay()
    dieu_kien = _cac_dieu_kien(cay, loc, gia, ton)
    sap_xep: dict[str, list[ColumnElement]] = {
        "moi": [SanPham.created_at.desc(), SanPham.id.desc()],
        "gia_tang": [gia.asc().nulls_last(), SanPham.id],
        "gia_giam": [gia.desc().nulls_last(), SanPham.id],
        "ban_chay": [func.coalesce(ban_chay.c.so_dong, 0).desc(), SanPham.id],
        "ten": [func.lower(SanPham.ten), SanPham.id],
    }
    tong = await db.scalar(select(func.count()).select_from(SanPham).where(*dieu_kien)) or 0
    truy_van = chon_the()
    if loc.sap_xep == "ban_chay":
        truy_van = truy_van.outerjoin(ban_chay, ban_chay.c.san_pham_id == SanPham.id)
    truy_van = truy_van.where(*dieu_kien).order_by(*sap_xep[loc.sap_xep]).limit(tp.limit).offset(tp.offset)
    dong = (await db.execute(truy_van)).all()
    return tao_trang(await dung_the(db, dong), tong, tp)


async def trang_chu(db: AsyncSession) -> TrangChu:
    """Banner, nổi bật và bán chạy. Hai khu quảng bá loại thuốc kê đơn ngay ở truy vấn (quy tắc CLAUDE.md số 6)."""
    cay = await nap_cay_hien_thi(db)
    hien = la_hien_thi(cay.ids)
    khong_ke_don = SanPham.loai_san_pham != LoaiSanPham.thuoc_ke_don
    noi_bat = (
        await db.execute(
            chon_the()
            .where(hien, khong_ke_don, SanPham.la_noi_bat.is_(True))
            .order_by(SanPham.created_at.desc(), SanPham.id.desc())
            .limit(SO_SAN_PHAM_TRANG_CHU)
        )
    ).all()
    gop = ban_chay_30_ngay()
    ban_chay = (
        await db.execute(
            chon_the()
            .join(gop, gop.c.san_pham_id == SanPham.id)
            .where(hien, khong_ke_don)
            .order_by(gop.c.so_dong.desc(), SanPham.id)
            .limit(SO_SAN_PHAM_TRANG_CHU)
        )
    ).all()
    banner = await dich_vu_danh_muc.banner_dang_hien(db)
    return TrangChu(
        banner_chinh=[b for b in banner if b.vi_tri == "trang_chu_chinh"],
        banner_phu=[b for b in banner if b.vi_tri == "trang_chu_phu"],
        noi_bat=await dung_the(db, noi_bat),
        ban_chay=await dung_the(db, ban_chay),
    )


async def bo_loc(db: AsyncSession, danh_muc_slug: str | None) -> BoLocSanPham:
    cay = await nap_cay_hien_thi(db)
    dieu_kien = _cac_dieu_kien(cay, BoLoc(danh_muc_slug=danh_muc_slug), gia_hien_thi(), ton_kha_dung())
    thuong_hieu = (
        await db.execute(
            select(ThuongHieu.id, ThuongHieu.ten)
            .where(ThuongHieu.id.in_(select(SanPham.thuong_hieu_id).where(*dieu_kien)))
            .order_by(func.lower(ThuongHieu.ten), ThuongHieu.id)
        )
    ).all()
    doi_tuong = (
        (
            await db.execute(
                select(SanPham.doi_tuong_su_dung)
                .where(*dieu_kien, SanPham.doi_tuong_su_dung.is_not(None), SanPham.doi_tuong_su_dung != "")
                .group_by(SanPham.doi_tuong_su_dung)
                .order_by(func.lower(SanPham.doi_tuong_su_dung))
                .limit(TOI_DA_DOI_TUONG_LOC)
            )
        )
        .scalars()
        .all()
    )
    gia = gia_hien_thi()
    thap, cao = (await db.execute(select(func.min(gia), func.max(gia)).select_from(SanPham).where(*dieu_kien))).one()
    return BoLocSanPham(
        thuong_hieu=[ThuongHieuLoc(id=i, ten=t) for i, t in thuong_hieu],
        doi_tuong=list(doi_tuong),
        gia_thap_nhat=Decimal(thap) if thap is not None else None,
        gia_cao_nhat=Decimal(cao) if cao is not None else None,
    )

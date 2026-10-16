"""Cảnh báo kho (KHO06) và thông báo HT02: sản phẩm tồn thấp, lô cận hạn, lô hết hạn còn hàng."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.thoi_gian import dau_ngay_vn, hom_nay_vn
from app.models.enums import TrangThaiKinhDoanh, TrangThaiLo, TrangThaiTaiKhoan
from app.models.he_thong import NhanVien, VaiTro
from app.models.khach_hang import ThongBao
from app.models.kho import LoThuoc
from app.models.san_pham import SanPham
from app.modules.cua_hang.hien_thi import ton_kha_dung
from app.modules.thong_bao.service import gui_cho_nhan_vien

LOAI_THONG_BAO = {"ton_thap": "canh_bao_ton_thap", "can_han": "canh_bao_can_han", "het_han": "canh_bao_het_han"}
GIOI_HAN_DONG = 200
MA_VAI_TRO_KHO = "WAREHOUSE"


@dataclass
class CanhBaoKho:
    ton_thap: list  # (SanPham, ton khả dụng)
    tong_ton_thap: int
    can_han: list  # (LoThuoc, SanPham)
    tong_can_han: int
    het_han: list
    tong_het_han: int


async def _lo_theo_trang_thai(db: AsyncSession, trang_thai: TrangThaiLo) -> tuple[list, int]:
    truy_van = (
        select(LoThuoc, SanPham)
        .join(SanPham, SanPham.id == LoThuoc.san_pham_id)
        .where(
            LoThuoc.trang_thai == trang_thai,
            LoThuoc.so_luong_ton + LoThuoc.so_luong_biet_tru > 0,
            SanPham.deleted_at.is_(None),
        )
    )
    tong = len((await db.execute(truy_van.with_only_columns(LoThuoc.id))).all())
    dong = (await db.execute(truy_van.order_by(LoThuoc.han_su_dung, LoThuoc.id).limit(GIOI_HAN_DONG))).all()
    return [(lo, sp) for lo, sp in dong], tong


async def lay_canh_bao(db: AsyncSession, hom_nay: date | None = None) -> CanhBaoKho:
    kha_dung = ton_kha_dung(hom_nay or hom_nay_vn()).label("kha_dung")
    truy_van = (
        select(SanPham, kha_dung)
        .where(
            SanPham.deleted_at.is_(None),
            SanPham.trang_thai == TrangThaiKinhDoanh.dang_kinh_doanh,
            SanPham.ton_toi_thieu > 0,
        )
        .order_by(SanPham.ten, SanPham.id)
    )
    tat_ca = [(sp, int(kd)) for sp, kd in (await db.execute(truy_van)).all() if kd < sp.ton_toi_thieu]
    can_han, tong_ch = await _lo_theo_trang_thai(db, TrangThaiLo.can_han)
    het_han, tong_hh = await _lo_theo_trang_thai(db, TrangThaiLo.het_han)
    return CanhBaoKho(tat_ca[:GIOI_HAN_DONG], len(tat_ca), can_han, tong_ch, het_han, tong_hh)


async def nhan_vien_kho(db: AsyncSession) -> list[int]:
    """Id nhân viên kho đang hoạt động (người nhận cảnh báo kho)."""
    return list(
        (
            await db.execute(
                select(NhanVien.id)
                .join(VaiTro, VaiTro.id == NhanVien.vai_tro_id)
                .where(
                    VaiTro.ma == MA_VAI_TRO_KHO,
                    NhanVien.trang_thai == TrangThaiTaiKhoan.hoat_dong,
                    NhanVien.deleted_at.is_(None),
                )
                .order_by(NhanVien.id)
            )
        ).scalars()
    )


async def gui_thong_bao_ht02(db: AsyncSession) -> int:
    """HT02: mỗi nhân viên kho đang hoạt động nhận tối đa một thông báo mỗi loại mỗi ngày (giờ VN), chỉ loại có mục.
    Trả số thông báo đã gửi."""
    cb = await lay_canh_bao(db)
    can_gui = {
        "ton_thap": (cb.tong_ton_thap, "sản phẩm tồn dưới mức tối thiểu"),
        "can_han": (cb.tong_can_han, "lô cận hạn còn hàng"),
        "het_han": (cb.tong_het_han, "lô hết hạn còn hàng, cần lập phiếu hủy"),
    }
    nhan_vien = await nhan_vien_kho(db)
    dau_ngay = dau_ngay_vn(hom_nay_vn())
    da_gui = 0
    for loai, (so, nhan) in can_gui.items():
        if so == 0:
            continue
        for nv_id in nhan_vien:
            ma = LOAI_THONG_BAO[loai]
            co = await db.scalar(
                select(ThongBao.id)
                .where(ThongBao.nhan_vien_id == nv_id, ThongBao.loai == ma, ThongBao.created_at >= dau_ngay)
                .limit(1)
            )
            if co is None:
                await gui_cho_nhan_vien(
                    db, nv_id, loai=ma, tieu_de=f"Cảnh báo kho: {so} {nhan}", lien_ket="/nhan-vien/canh-bao"
                )
                da_gui += 1
    return da_gui

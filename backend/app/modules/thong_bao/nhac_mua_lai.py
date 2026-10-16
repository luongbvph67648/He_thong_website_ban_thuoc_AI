"""HT07: nhắc mua lại sản phẩm dùng định kỳ (KTV14). Chạy mỗi ngày 08:00 giờ VN, idempotent.

Ngày hết dự kiến = ngày giao + số lượng cơ sở x `so_ngay_dung_moi_don_vi`. Nhắc khi còn <= 3 ngày (kể cả đã quá hạn
không quá 30 ngày), mỗi lần mua chỉ nhắc một lần (khóa dedupe nằm ở `lien_ket`).
"""

import math
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.thoi_gian import VN_TZ, hom_nay_vn
from app.models.ban_hang import CtDonHang, DonHang, LichSuTrangThai
from app.models.enums import LoaiSanPham, TrangThaiDon
from app.models.khach_hang import ThongBao
from app.models.san_pham import SanPham
from app.modules.thong_bao.service import gui_cho_khach

NHAC_TRUOC_NGAY = 3
BO_QUA_SAU_NGAY = 30
SO_LAN_TOI_DA_MOI_LAN_CHAY = 2000


@dataclass
class KetQuaHt07:
    da_nhac: int = 0


def ngay_het_du_kien(ngay_giao: date, so_luong_co_so: int, so_ngay_moi_don_vi) -> date:
    return ngay_giao + timedelta(days=math.ceil(so_luong_co_so * float(so_ngay_moi_don_vi)))


async def nhac_mua_lai(db: AsyncSession, hom_nay: date | None = None) -> KetQuaHt07:
    hom_nay = hom_nay or hom_nay_vn()
    ngay_giao = (
        select(LichSuTrangThai.don_hang_id, func.max(LichSuTrangThai.created_at).label("luc"))
        .where(LichSuTrangThai.den_trang_thai == TrangThaiDon.da_giao)
        .group_by(LichSuTrangThai.don_hang_id)
        .subquery()
    )
    dong = (
        await db.execute(
            select(CtDonHang, DonHang, SanPham, ngay_giao.c.luc)
            .join(DonHang, DonHang.id == CtDonHang.don_hang_id)
            .join(SanPham, SanPham.id == CtDonHang.san_pham_id)
            .join(ngay_giao, ngay_giao.c.don_hang_id == DonHang.id)
            .where(
                SanPham.dung_dinh_ky.is_(True),
                SanPham.loai_san_pham != LoaiSanPham.thuoc_ke_don,  # không nhắc/quảng bá thuốc kê đơn (quy tắc 6)
                SanPham.so_ngay_dung_moi_don_vi.is_not(None),
                SanPham.deleted_at.is_(None),
                DonHang.khach_hang_id.is_not(None),
                DonHang.trang_thai.in_((TrangThaiDon.da_giao, TrangThaiDon.hoan_tat)),
            )
            .order_by(ngay_giao.c.luc.desc(), CtDonHang.id.desc())
            .limit(SO_LAN_TOI_DA_MOI_LAN_CHAY)
        )
    ).all()
    ket_qua = KetQuaHt07()
    da_xet: set[tuple[int, int]] = set()
    for ct, don, sp, luc in dong:
        khoa = (don.khach_hang_id, sp.id)
        if khoa in da_xet:  # chỉ xét lần mua gần nhất của từng sản phẩm
            continue
        da_xet.add(khoa)
        het = ngay_het_du_kien(luc.astimezone(VN_TZ).date(), ct.so_luong * ct.he_so, sp.so_ngay_dung_moi_don_vi)
        if not (het - timedelta(days=NHAC_TRUOC_NGAY) <= hom_nay <= het + timedelta(days=BO_QUA_SAU_NGAY)):
            continue
        lien_ket = f"/san-pham/{sp.slug}?nhac={ct.id}"
        da_nhac = await db.scalar(
            select(ThongBao.id).where(
                ThongBao.khach_hang_id == don.khach_hang_id,
                ThongBao.loai == "nhac_mua_lai",
                ThongBao.lien_ket == lien_ket,
            )
        )
        if da_nhac is not None:
            continue
        con = (het - hom_nay).days
        await gui_cho_khach(
            db,
            don.khach_hang_id,
            loai="nhac_mua_lai",
            tieu_de=f"{sp.ten} sắp hết, mua lại?",
            noi_dung=(f"Dự kiến hết sau {con} ngày." if con > 0 else "Dự kiến đã hết.") + " Bấm để xem sản phẩm.",
            lien_ket=lien_ket,
        )
        ket_qua.da_nhac += 1
    return ket_qua

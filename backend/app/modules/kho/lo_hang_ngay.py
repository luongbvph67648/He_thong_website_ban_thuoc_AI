"""HT01: cập nhật trạng thái lô theo hạn sử dụng (spec 04 mục 1.4, spec 05 HT01). Gọi từ job nền, mỗi ngày một lần.

Chỉ đổi lô `dang_ban`/`can_han` (lô `khoa`, `thu_hoi` do Admin quyết định, `het_han` là trạng thái cuối). Lô hết hạn
được gỡ khỏi các đơn chưa xuất (`phan_bo_lo` `dang_giu`) và phân bổ lại theo FEFO sang lô khác còn hạn; đơn nào không
còn đủ hàng thì giữ nguyên số đã phân được, và báo cho nhân viên kho kèm mã đơn để xử lý.
"""

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cau_hinh import doc_cau_hinh
from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc, hom_nay_vn
from app.models.ban_hang import CtDonHang, DonHang, PhanBoLo
from app.models.enums import KenhBan, TrangThaiLo, TrangThaiPhanBo
from app.models.kho import LoThuoc
from app.modules.kho import ton_kho
from app.modules.kho.lo import trang_thai_theo_han
from app.modules.kho.ton_kho import YeuCauGiu

TRANG_THAI_THEO_HAN = (TrangThaiLo.dang_ban, TrangThaiLo.can_han)


@dataclass
class KetQuaHt01:
    sang_can_han: int = 0
    ve_dang_ban: int = 0
    sang_het_han: int = 0
    phan_bo_lai: int = 0
    don_thieu_hang: list[str] = field(default_factory=list)


async def _phan_bo_lai(db: AsyncSession, lo_het_han_ids: list[int], ket_qua: KetQuaHt01) -> None:
    """Nhả mọi phân bổ `dang_giu` trên lô hết hạn rồi giữ lại cùng số lượng từ các lô còn bán được."""
    if not lo_het_han_ids:
        return
    giu = (
        (
            await db.execute(
                select(PhanBoLo)
                .where(PhanBoLo.lo_id.in_(lo_het_han_ids), PhanBoLo.trang_thai == TrangThaiPhanBo.dang_giu)
                .order_by(PhanBoLo.id)
            )
        )
        .scalars()
        .all()
    )
    if not giu:
        return
    cac_dong = {
        d.id: d
        for d in (
            await db.execute(select(CtDonHang).where(CtDonHang.id.in_({p.ct_don_hang_id for p in giu})))
        ).scalars()
    }
    kenh = dict(
        (
            await db.execute(
                select(DonHang.id, DonHang.kenh_ban).where(DonHang.id.in_({d.don_hang_id for d in cac_dong.values()}))
            )
        ).all()
    )
    ma_don = dict((await db.execute(select(DonHang.id, DonHang.ma_don).where(DonHang.id.in_(list(kenh))))).all())
    await ton_kho.nha_giu(db, giu)
    for p in giu:
        dong = cac_dong[p.ct_don_hang_id]
        try:
            await ton_kho.giu_hang_nhieu(
                db,
                [YeuCauGiu(dong.id, dong.san_pham_id, p.so_luong_co_so)],
                cho_phep_can_han=kenh[dong.don_hang_id] == KenhBan.tai_quay,
            )
            ket_qua.phan_bo_lai += 1
        except LoiNghiepVu:
            ket_qua.don_thieu_hang.append(ma_don[dong.don_hang_id])


async def cap_nhat_trang_thai_lo(db: AsyncSession) -> KetQuaHt01:
    """Chạy HT01 trong transaction của người gọi (job commit sau khi hàm trả về)."""
    hom_nay = hom_nay_vn()
    nguong = int(await doc_cau_hinh(db, "nguong_can_han_ngay", 90))
    ids = (
        (await db.execute(select(LoThuoc.id).where(LoThuoc.trang_thai.in_(TRANG_THAI_THEO_HAN)).order_by(LoThuoc.id)))
        .scalars()
        .all()
    )
    ket_qua = KetQuaHt01()
    het_han: list[int] = []
    for lo in await ton_kho.khoa_cac_lo(db, ids):
        if lo.trang_thai not in TRANG_THAI_THEO_HAN:  # Admin vừa khóa lô giữa lúc chọn và lúc khóa
            continue
        moi = trang_thai_theo_han(lo.han_su_dung, hom_nay, nguong)
        if moi == lo.trang_thai:
            continue
        if moi == TrangThaiLo.het_han:
            ket_qua.sang_het_han += 1
            het_han.append(lo.id)
        elif moi == TrangThaiLo.can_han:
            ket_qua.sang_can_han += 1
        else:
            ket_qua.ve_dang_ban += 1
        lo.trang_thai = moi
        lo.updated_at = bay_gio_utc()
    await db.flush()
    await _phan_bo_lai(db, het_han, ket_qua)
    return ket_qua

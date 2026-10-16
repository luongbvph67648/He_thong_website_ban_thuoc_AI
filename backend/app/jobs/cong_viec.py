"""Các job nền: HT01 (trạng thái lô), HT02 (cảnh báo kho), dọn lịch sử xem và tìm kiếm."""

from datetime import timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.thoi_gian import bay_gio_utc
from app.models.ai import LichSuTimKiem, LichSuXem
from app.modules.kho.canh_bao import gui_thong_bao_ht02, nhan_vien_kho
from app.modules.kho.lo_hang_ngay import KetQuaHt01, cap_nhat_trang_thai_lo
from app.modules.thong_bao.service import gui_cho_nhan_vien

GIU_LICH_SU_NGAY = 90


async def ht01_cap_nhat_lo(db: AsyncSession) -> KetQuaHt01:
    ket_qua = await cap_nhat_trang_thai_lo(db)
    if ket_qua.don_thieu_hang:
        for nv_id in await nhan_vien_kho(db):
            await gui_cho_nhan_vien(
                db,
                nv_id,
                loai="canh_bao_don_thieu_hang",
                tieu_de="Lô hết hạn làm đơn thiếu hàng",
                noi_dung="Các đơn cần xử lý lại: " + ", ".join(ket_qua.don_thieu_hang[:20]),
                lien_ket="/nhan-vien/canh-bao",
            )
    return ket_qua


async def ht02_canh_bao_kho(db: AsyncSession) -> int:
    return await gui_thong_bao_ht02(db)


async def don_lich_su(db: AsyncSession) -> int:
    """Xóa lịch sử xem và tìm kiếm quá `GIU_LICH_SU_NGAY` ngày (dữ liệu hành vi không giữ vô thời hạn)."""
    han = bay_gio_utc() - timedelta(days=GIU_LICH_SU_NGAY)
    tong = 0
    for mo_hinh in (LichSuXem, LichSuTimKiem):
        tong += (await db.execute(delete(mo_hinh).where(mo_hinh.created_at < han))).rowcount or 0
    return tong

"""Các job nền: HT01 (lô), HT02 (cảnh báo kho), HT03 (hủy đơn quá hạn), HT08 (tự hoàn tất đơn), dọn lịch sử."""

from datetime import timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc
from app.models.ai import LichSuTimKiem, LichSuXem
from app.modules.ai_quan_tri.tri_thuc import KetQuaDongBo
from app.modules.ai_quan_tri.tri_thuc import dong_bo as dong_bo_tri_thuc
from app.modules.ban_hang.het_han import KetQuaHt03, huy_don_qua_han
from app.modules.ban_hang.tu_hoan_tat import KetQuaHt08Don, tu_hoan_tat_don
from app.modules.don_thuoc.doc_anh_ai import KetQuaAi06, doc_don_thuoc_moi
from app.modules.kho.canh_bao import gui_thong_bao_ht02, nhan_vien_kho
from app.modules.kho.lo_hang_ngay import KetQuaHt01, cap_nhat_trang_thai_lo
from app.modules.thong_bao.nhac_mua_lai import KetQuaHt07, nhac_mua_lai
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


async def ht03_huy_qua_han(db: AsyncSession) -> KetQuaHt03:
    return await huy_don_qua_han(db)


async def ht07_nhac_mua_lai(db: AsyncSession) -> KetQuaHt07:
    return await nhac_mua_lai(db)


async def ai_dong_bo_tri_thuc(db: AsyncSession) -> KetQuaDongBo | None:
    """AD10 hằng đêm; đang có lần đồng bộ khác (Admin bấm tay) thì bỏ qua đêm nay."""
    try:
        return await dong_bo_tri_thuc(db)
    except LoiNghiepVu:
        return None


async def ht08_tu_hoan_tat(db: AsyncSession) -> KetQuaHt08Don:
    return await tu_hoan_tat_don(db)


async def ai06_doc_don_thuoc(db: AsyncSession) -> KetQuaAi06:
    """AI06 mỗi phút: đọc ảnh các yêu cầu đơn thuốc mới để gợi ý cho dược sĩ."""
    return await doc_don_thuoc_moi(db)


async def don_lich_su(db: AsyncSession) -> int:
    """Xóa lịch sử xem và tìm kiếm quá `GIU_LICH_SU_NGAY` ngày (dữ liệu hành vi không giữ vô thời hạn)."""
    han = bay_gio_utc() - timedelta(days=GIU_LICH_SU_NGAY)
    tong = 0
    for mo_hinh in (LichSuXem, LichSuTimKiem):
        tong += (await db.execute(delete(mo_hinh).where(mo_hinh.created_at < han))).rowcount or 0
    return tong

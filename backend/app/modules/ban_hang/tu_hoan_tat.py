"""HT08 (phần đơn hàng): đơn `da_giao` hết thời hạn đổi trả → `hoan_tat` (dòng 29); đơn nhận tại nhà thuốc quá hạn
nhận → `da_huy` (dòng 21, hoàn nhập và hoàn tiền do hook). Mốc thời gian lấy từ lịch sử trạng thái."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cau_hinh import doc_cau_hinh
from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc
from app.models.ban_hang import DonHang, LichSuTrangThai, YeuCauDoiTra
from app.models.enums import HinhThucNhan, TrangThaiDoiTra, TrangThaiDon
from app.modules.ban_hang.trang_thai import NGUON_HE_THONG, TacNhan, chuyen_trang_thai

TT = TrangThaiDon

DOI_TRA_DONG = (TrangThaiDoiTra.tu_choi, TrangThaiDoiTra.hoan_tat)  # các trạng thái đã đóng; còn lại là yêu cầu mở


@dataclass
class KetQuaHt08Don:
    hoan_tat: list[str] = field(default_factory=list)
    da_huy_qua_han_quay: list[str] = field(default_factory=list)
    bo_qua: list[str] = field(default_factory=list)


def _moc_vao_trang_thai(trang_thai: TrangThaiDon):
    """Thời điểm đơn vào trạng thái hiện tại (lần chuyển gần nhất), mặc định lúc tạo đơn nếu thiếu lịch sử."""
    moc = (
        select(func.max(LichSuTrangThai.created_at))
        .where(LichSuTrangThai.don_hang_id == DonHang.id, LichSuTrangThai.den_trang_thai == trang_thai)
        .scalar_subquery()
    )
    return func.coalesce(moc, DonHang.created_at)


async def _ids_qua_han(db: AsyncSession, trang_thai: TrangThaiDon, han: datetime, *, tai_quay: bool = False):
    q = select(DonHang.id).where(DonHang.trang_thai == trang_thai, _moc_vao_trang_thai(trang_thai) < han)
    if tai_quay:
        q = q.where(DonHang.hinh_thuc_nhan == HinhThucNhan.nhan_tai_nha_thuoc)
    else:
        q = q.where(
            ~exists().where(YeuCauDoiTra.don_hang_id == DonHang.id, YeuCauDoiTra.trang_thai.notin_(DOI_TRA_DONG))
        )
    return (await db.execute(q.order_by(DonHang.id))).scalars().all()


async def tu_hoan_tat_don(db: AsyncSession) -> KetQuaHt08Don:
    """Mỗi đơn chuyển trong savepoint riêng; đơn vừa phát sinh yêu cầu đổi trả hoặc vừa đổi trạng thái bị bỏ qua."""
    bay_gio = bay_gio_utc()
    ngay_doi_tra = int(await doc_cau_hinh(db, "thoi_han_doi_tra_ngay", 7))
    ngay_tai_quay = int(await doc_cau_hinh(db, "thoi_han_nhan_tai_quay_ngay", 3))
    ket_qua = KetQuaHt08Don()
    han_doi_tra = bay_gio - timedelta(days=ngay_doi_tra)
    han_tai_quay = bay_gio - timedelta(days=ngay_tai_quay)
    viec = (
        (await _ids_qua_han(db, TT.da_giao, han_doi_tra), TT.hoan_tat, None, ket_qua.hoan_tat),
        (
            await _ids_qua_han(db, TT.cho_lay_hang, han_tai_quay, tai_quay=True),
            TT.da_huy,
            "Quá hạn nhận hàng tại nhà thuốc",
            ket_qua.da_huy_qua_han_quay,
        ),
    )
    for ids, dich, ly_do, nhat_ky in viec:
        for don_id in ids:
            don = await db.get(DonHang, don_id)
            assert don is not None
            try:
                async with db.begin_nested():
                    await chuyen_trang_thai(db, don, dich, TacNhan.he_thong(), NGUON_HE_THONG, ly_do)
                nhat_ky.append(don.ma_don)
            except LoiNghiepVu:
                ket_qua.bo_qua.append(don.ma_don)
    return ket_qua

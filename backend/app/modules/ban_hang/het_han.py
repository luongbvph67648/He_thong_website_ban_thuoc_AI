"""HT03: hủy đơn quá hạn thanh toán hoặc quá hạn xác nhận (spec 04 mục 1.1 dòng 9 và 12)."""

from dataclasses import dataclass, field

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc
from app.models.ban_hang import DonHang
from app.models.enums import TrangThaiDon
from app.modules.ban_hang.trang_thai import NGUON_HE_THONG, TacNhan, chuyen_trang_thai


@dataclass
class KetQuaHt03:
    da_huy: list[str] = field(default_factory=list)
    bo_qua: list[str] = field(default_factory=list)


async def huy_don_qua_han(db: AsyncSession) -> KetQuaHt03:
    """Mỗi đơn hủy qua `chuyen_trang_thai` (nhả giữ hàng, trả lượt mã giảm giá do hook) trong savepoint riêng: một đơn
    lỗi hoặc vừa nhận IPN thành công (điều kiện dòng 12 không còn đúng) không làm hỏng các đơn khác."""
    bay_gio = bay_gio_utc()
    ids = (
        (
            await db.execute(
                select(DonHang.id)
                .where(
                    or_(
                        and_(DonHang.trang_thai == TrangThaiDon.cho_thanh_toan, DonHang.han_thanh_toan < bay_gio),
                        and_(DonHang.trang_thai == TrangThaiDon.cho_khach_xac_nhan, DonHang.han_xac_nhan < bay_gio),
                    )
                )
                .order_by(DonHang.id)
            )
        )
        .scalars()
        .all()
    )
    ket_qua = KetQuaHt03()
    for don_id in ids:
        don = await db.get(DonHang, don_id)
        assert don is not None
        ly_do = "Quá hạn thanh toán" if don.trang_thai == TrangThaiDon.cho_thanh_toan else "Quá hạn xác nhận của khách"
        try:
            async with db.begin_nested():
                await chuyen_trang_thai(db, don, TrangThaiDon.da_huy, TacNhan.he_thong(), NGUON_HE_THONG, ly_do)
            ket_qua.da_huy.append(don.ma_don)
        except LoiNghiepVu:
            ket_qua.bo_qua.append(don.ma_don)
    return ket_qua

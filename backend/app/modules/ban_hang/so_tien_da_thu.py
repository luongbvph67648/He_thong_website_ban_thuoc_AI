"""Sổ tiền đã thu của một đơn (thanh toán, hoàn tiền) và trạng thái thanh toán suy ra từ đó.

Một đơn có thể có NHIỀU giao dịch thanh toán thành công (khách mở hai tab, cổng báo trễ sau khi đơn đã hủy) và nhiều
giao dịch hoàn (hủy đơn, đổi trả, hoàn khoản trả thừa). `trang_thai_tt` vì vậy không được đoán từ một giao dịch mà
phải tính từ tổng: đây là nơi duy nhất làm việc đó (IPN, hủy đơn và xác nhận hoàn tiền cùng dùng).
"""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ban_hang import DonHang, ThanhToan
from app.models.enums import LoaiGiaoDich, TrangThaiDon, TrangThaiGiaoDich, TrangThaiThanhToan

TG = TrangThaiGiaoDich


@dataclass(frozen=True)
class SoTien:
    thu: Decimal  # Σ giao dịch thanh toán thành công
    hoan_xong: Decimal  # Σ hoàn đã xác nhận
    hoan_cho: Decimal  # Σ hoàn đang chờ Admin xác nhận

    @property
    def con_phai_hoan(self) -> Decimal:
        """Số tiền khách đã trả mà chưa có giao dịch hoàn nào (kể cả đang chờ) bao phủ."""
        return max(self.thu - self.hoan_xong - self.hoan_cho, Decimal(0))


async def tinh_so_tien(db: AsyncSession, don_id: int) -> SoTien:
    async def tong(loai: LoaiGiaoDich, *trang_thai: TG) -> Decimal:
        return Decimal(
            await db.scalar(
                select(func.coalesce(func.sum(ThanhToan.so_tien), 0)).where(
                    ThanhToan.don_hang_id == don_id, ThanhToan.loai == loai, ThanhToan.trang_thai.in_(trang_thai)
                )
            )
            or 0
        )

    return SoTien(
        await tong(LoaiGiaoDich.thanh_toan, TG.thanh_cong),
        await tong(LoaiGiaoDich.hoan_tien, TG.thanh_cong),
        await tong(LoaiGiaoDich.hoan_tien, TG.khoi_tao),
    )


def trang_thai_thanh_toan(don: DonHang, so: SoTien) -> TrangThaiThanhToan:
    """Trạng thái thanh toán của đơn theo sổ tiền.

    `giu` là phần tiền nhà thuốc được giữ nếu không có đổi trả: toàn bộ `tong_tien` khi đơn còn hiệu lực, 0 khi đã hủy.
    Hoàn khoản trả THỪA (hai lần thanh toán) chỉ kéo tiền thu thuần về đúng `giu` nên không làm đơn thành "hoàn tiền".
    """
    if so.thu <= 0:
        return don.trang_thai_tt
    giu = Decimal(0) if don.trang_thai == TrangThaiDon.da_huy else don.tong_tien
    if so.hoan_cho > 0:
        con_lai_neu_hoan_het = so.thu - so.hoan_xong - so.hoan_cho
        return (
            TrangThaiThanhToan.cho_hoan_tien
            if con_lai_neu_hoan_het < giu or giu == 0
            else TrangThaiThanhToan.da_thanh_toan
        )
    rong = so.thu - so.hoan_xong
    if rong <= 0:
        return TrangThaiThanhToan.da_hoan_tien
    return TrangThaiThanhToan.hoan_tien_mot_phan if rong < giu else TrangThaiThanhToan.da_thanh_toan

"""Cổng thanh toán (spec 08 mục 2-4): VNPay, MoMo và bản giả. Code nghiệp vụ chỉ biết `CongThanhToan`."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from app.core.config import settings
from app.models.ban_hang import DonHang, ThanhToan
from app.models.enums import PhuongThucThanhToan


def tham_chieu(don: DonHang, giao_dich: ThanhToan) -> str:
    """`vnp_TxnRef`/`orderId`: duy nhất cho mỗi lần thanh toán để thanh toán lại được sau khi lần trước thất bại."""
    return f"{don.ma_don}-{giao_dich.id}"


@dataclass
class KetQuaIpn:
    chu_ky_hop_le: bool
    tham_chieu: str = ""
    so_tien: Decimal | None = None
    ma_giao_dich_cong: str | None = None
    thanh_cong: bool = False
    du_lieu: dict[str, Any] = field(default_factory=dict)
    """Payload thô đã bỏ chữ ký, lưu vào `thanh_toan.du_lieu_ipn`."""


@dataclass
class KetQuaHoan:
    thanh_cong: bool
    ma_giao_dich_cong: str | None = None
    thong_diep: str | None = None


@runtime_checkable
class CongThanhToan(Protocol):
    async def tao_url_thanh_toan(self, don: DonHang, giao_dich: ThanhToan, ip: str) -> str: ...

    def xac_thuc_ipn(self, tham_so: dict[str, Any]) -> KetQuaIpn: ...

    async def hoan_tien(self, giao_dich_goc: ThanhToan, so_tien: Decimal, ly_do: str) -> KetQuaHoan: ...


def lay_cong(phuong_thuc: PhuongThucThanhToan) -> CongThanhToan:
    """Chọn bản theo `THANH_TOAN_CHE_DO`; `gia` dùng một bản cho cả VNPay và MoMo."""
    if settings.THANH_TOAN_CHE_DO == "gia":
        from app.tich_hop.thanh_toan.gia import CongGia

        return CongGia()
    if phuong_thuc == PhuongThucThanhToan.vnpay:
        from app.tich_hop.thanh_toan.vnpay import CongVnpay

        return CongVnpay()
    if phuong_thuc == PhuongThucThanhToan.momo:
        from app.tich_hop.thanh_toan.momo import CongMomo

        return CongMomo()
    raise ValueError(f"Phương thức {phuong_thuc} không đi qua cổng thanh toán online")

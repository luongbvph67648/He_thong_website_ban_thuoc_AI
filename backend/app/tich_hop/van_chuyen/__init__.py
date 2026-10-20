"""Đơn vị vận chuyển (spec 08 mục 5, 8): địa giới (T4.1), tính phí (T4.4), vận đơn và webhook (T4.7)."""

from decimal import Decimal
from functools import lru_cache
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel


class DonViHanhChinh(BaseModel):
    ma: str
    ten: str


@runtime_checkable
class DanhMucDiaGioi(Protocol):
    """Danh mục tỉnh/xã theo MÃ CỦA ĐƠN VỊ VẬN CHUYỂN (mô hình 2 cấp từ 01/07/2025)."""

    def danh_sach_tinh(self) -> list[DonViHanhChinh]: ...

    def danh_sach_xa(self, ma_tinh: str) -> list[DonViHanhChinh] | None:
        """`None` khi không có tỉnh mang mã này."""
        ...


@lru_cache(maxsize=1)
def lay_danh_muc_dia_gioi() -> DanhMucDiaGioi:
    """Bản giả (file JSON). Bản GHN master data (cache 24 giờ) thay vào đây cùng adapter vận chuyển ở T4.7."""
    from app.tich_hop.van_chuyen.gia import DanhMucDiaGioiGia

    return DanhMucDiaGioiGia()


class DiaChiGiao(BaseModel):
    ma_tinh: str
    ma_phuong_xa: str
    dia_chi_chi_tiet: str


class KetQuaVanDon(BaseModel):
    ma_van_don: str
    phi: Decimal


class SuKienVanChuyen(BaseModel):
    """Sự kiện webhook đã xác thực: mã vận đơn, trạng thái gốc của đối tác và payload thô."""

    ma_van_don: str
    trang_thai_doi_tac: str
    du_lieu: dict[str, Any]


class WebhookKhongHopLe(Exception):
    """Token webhook sai hoặc thân không đúng định dạng."""


@runtime_checkable
class DonViVanChuyen(Protocol):
    ten: str  # ghi vào `van_don.don_vi_van_chuyen`

    async def tinh_phi(self, dia_chi: DiaChiGiao, khoi_luong_gram: int, gia_tri: Decimal) -> Decimal:
        """Phí giao hàng (đồng). Lỗi đối tác thì ném ngoại lệ; nơi gọi dùng `phi_ship_mac_dinh`."""
        ...

    async def tao_van_don(self, don: Any, loai: Literal["giao_hang", "tra_hang"], khoi_luong_gram: int) -> KetQuaVanDon:
        """Tạo vận đơn cho `DonHang` (đã nạp `chi_tiet`). Lỗi đối tác thì ném ngoại lệ."""
        ...

    async def huy_van_don(self, ma_van_don: str) -> None: ...

    def xac_thuc_webhook(self, headers: dict[str, str], body: dict[str, Any]) -> SuKienVanChuyen:
        """Kiểm token và tách sự kiện; sai thì ném `WebhookKhongHopLe`."""
        ...


def lay_don_vi_van_chuyen() -> DonViVanChuyen:
    """Adapter theo `VAN_CHUYEN_CHE_DO`: `gia` (mặc định), `mo_phong` (GHN thật tới GHN mô phỏng) hoặc `ghn`."""
    from app.core.config import settings

    if settings.VAN_CHUYEN_CHE_DO in ("ghn", "mo_phong"):
        from app.tich_hop.van_chuyen.ghn import VanChuyenGhn

        return VanChuyenGhn()
    from app.tich_hop.van_chuyen.gia import VanChuyenGia

    return VanChuyenGia()

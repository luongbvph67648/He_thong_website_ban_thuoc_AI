"""Đơn vị vận chuyển (spec 08 mục 5, 8): địa giới (T4.1), tính phí (T4.4); vận đơn và webhook ở T4.7."""

from decimal import Decimal
from functools import lru_cache
from typing import Protocol, runtime_checkable

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


@runtime_checkable
class DonViVanChuyen(Protocol):
    async def tinh_phi(self, dia_chi: DiaChiGiao, khoi_luong_gram: int, gia_tri: Decimal) -> Decimal:
        """Phí giao hàng (đồng). Lỗi đối tác thì ném ngoại lệ; nơi gọi dùng `phi_ship_mac_dinh`."""
        ...


@lru_cache(maxsize=1)
def lay_don_vi_van_chuyen() -> DonViVanChuyen:
    """Bản giả (công thức cố định). Bản GHN thay vào đây ở T4.7."""
    from app.tich_hop.van_chuyen.gia import VanChuyenGia

    return VanChuyenGia()

"""Đơn vị vận chuyển (spec 08 mục 5, 8). T4.1 chỉ có danh mục địa giới; vận đơn và webhook thêm ở T4.7."""

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

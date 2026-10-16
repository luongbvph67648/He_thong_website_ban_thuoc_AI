"""Schema khách xác nhận đơn do dược sĩ tạo từ đơn thuốc (KTV07, spec 06 mục 3.30)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.kieu_du_lieu import kieu_ten, van_ban_tuy_chon
from app.models.enums import HinhThucNhan, PhuongThucThanhToan
from app.modules.ban_hang.schemas import DonHangRa
from app.modules.ban_hang.schemas_dat_ho import DiaChiGiaoVao
from app.modules.tai_khoan.schemas import SoDienThoai


class XacNhanVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hinh_thuc_nhan: HinhThucNhan
    phuong_thuc_tt: Literal[PhuongThucThanhToan.cod, PhuongThucThanhToan.vnpay, PhuongThucThanhToan.momo]
    dia_chi_id: int | None = Field(default=None, ge=1, le=2_147_483_647)
    """Địa chỉ trong sổ địa chỉ (chỉ thành viên)."""
    dia_chi: DiaChiGiaoVao | None = None
    """Địa chỉ nhập tay (khách vãng lai hoặc thành viên không dùng sổ)."""
    ten_nguoi_nhan: kieu_ten(150) | None = None
    sdt_nguoi_nhan: SoDienThoai | None = None
    ghi_chu: van_ban_tuy_chon(500, nhieu_dong=True) = None


class DonXacNhanRa(BaseModel):
    don: DonHangRa
    co_the_xac_nhan: bool
    """Đơn còn `cho_khach_xac_nhan` và chưa quá `han_xac_nhan`."""
    co_the_thanh_toan: bool
    """Đơn `cho_thanh_toan` bằng cổng online, còn hạn."""

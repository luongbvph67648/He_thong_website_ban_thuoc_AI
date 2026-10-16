"""Schema tạo đơn hộ khách (DS07) và giao đơn tại quầy (DS15), spec 06 mục 3.26."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.kieu_du_lieu import kieu_ten, van_ban_tuy_chon
from app.core.tien import TienDoc
from app.models.enums import HinhThucNhan, PhuongThucThanhToan, TrangThaiThanhToan
from app.modules.ban_hang.schemas import DonHangRa
from app.modules.dia_chi.schemas import DiaChiRa
from app.modules.tai_khoan.schemas import SoDienThoai


class DongDonHoVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    san_pham_id: int = Field(ge=1, le=2_147_483_647)
    don_vi_id: int = Field(ge=1, le=2_147_483_647)
    so_luong: int = Field(ge=1, le=9999)


class DiaChiGiaoVao(BaseModel):
    """Địa chỉ giao nhập tay khi gọi điện; tên tỉnh/xã do máy chủ điền từ danh mục."""

    model_config = ConfigDict(extra="forbid")

    dia_chi_chi_tiet: str = Field(min_length=5, max_length=300)
    ma_tinh: str = Field(min_length=1, max_length=20)
    ma_phuong_xa: str = Field(min_length=1, max_length=20)


class DonHoVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sdt_khach: SoDienThoai | None = None
    ten_nguoi_nhan: kieu_ten(150)
    sdt_nguoi_nhan: SoDienThoai
    hinh_thuc_nhan: HinhThucNhan
    phuong_thuc_tt: Literal[PhuongThucThanhToan.cod, PhuongThucThanhToan.vnpay, PhuongThucThanhToan.momo]
    dia_chi: DiaChiGiaoVao | None = None
    dong: list[DongDonHoVao] = Field(min_length=1, max_length=50)
    ma_giam_gia: str | None = Field(default=None, max_length=40)
    ghi_chu: van_ban_tuy_chon(500, nhieu_dong=True) = None


class KhachTimRa(BaseModel):
    ho_ten: str
    so_dien_thoai: str
    dia_chi: list[DiaChiRa]


class DonHoRa(BaseModel):
    don: DonHangRa
    lien_ket_thanh_toan: str | None
    """Đường dẫn trang thanh toán của khách (đơn online), để đọc cho khách hoặc gửi SMS (KTV13)."""


class DongQuayRa(BaseModel):
    ten_san_pham: str
    ten_don_vi: str
    so_luong: int


class DonQuayRa(BaseModel):
    id: int
    ma_don: str
    ten_nguoi_nhan: str | None
    sdt_nguoi_nhan: str | None
    tong_tien: TienDoc
    phuong_thuc_tt: PhuongThucThanhToan | None
    trang_thai_tt: TrangThaiThanhToan
    dong: list[DongQuayRa]


class GiaoQuayVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phuong_thuc_thu: Literal[PhuongThucThanhToan.tien_mat, PhuongThucThanhToan.chuyen_khoan] | None = None

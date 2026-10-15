"""Schema API quản lý khách hàng của Admin (AD02, spec 06 mục 3.6).

Cố ý khai báo từng trường thay vì dùng chung `KhachHangDoc` của khách: Admin KHÔNG được thấy hồ sơ sức khỏe, dị ứng
(spec 03 mục 5.1) và không bao giờ có mật khẩu hay hash. Thêm trường vào đây là quyết định có chủ ý, có test khẳng định.
"""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

from app.core.tien import Tien
from app.models.enums import KenhBan, TrangThaiDon, TrangThaiTaiKhoan, TrangThaiThanhToan


class KhachHangTomTat(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ho_ten: str
    email: str | None
    so_dien_thoai: str
    trang_thai: TrangThaiTaiKhoan
    khoa_den: datetime | None
    created_at: datetime


class KhachHangChiTiet(KhachHangTomTat):
    gioi_tinh: str | None
    dong_y_chinh_sach_luc: datetime
    updated_at: datetime | None
    so_don_hang: int


class DonHangCuaKhach(BaseModel):
    """Một dòng lịch sử mua. Không có địa chỉ giao, người nhận, ghi chú hay token truy cập."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ma_don: str
    kenh_ban: KenhBan
    trang_thai: TrangThaiDon
    trang_thai_tt: TrangThaiThanhToan
    tong_tien: Tien
    created_at: datetime


class KhoaKhachYeuCau(BaseModel):
    """Thân (tùy chọn) của `POST /khoa`. `ly_do` chỉ ghi vào nhật ký hệ thống, không lưu ở hồ sơ khách."""

    model_config = ConfigDict(extra="forbid")

    ly_do: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] | None = None

    @field_validator("ly_do")
    @classmethod
    def _rong_la_khong_co(cls, gia_tri: str | None) -> str | None:
        return gia_tri or None

"""Schema API tài khoản khách (spec 06). Tên trường giữ đúng tên cột ERD."""

import re
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.core.bao_mat import mat_khau_du_manh
from app.core.dien_thoai import chuan_hoa_sdt

SoDienThoai = Annotated[str, BeforeValidator(chuan_hoa_sdt)]
"""Số di động Việt Nam, tự chuẩn hóa về `0xxxxxxxxx` ngay khi nhận (`+84 912 345 678` -> `0912345678`)."""

_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
EMAIL_TOI_DA = 150


def _chuan_hoa_email(gia_tri: object) -> str | None:
    if gia_tri is None:
        return None
    if not isinstance(gia_tri, str):
        raise ValueError("Email không hợp lệ")
    email = gia_tri.strip().lower()
    if email == "":
        return None
    if len(email) > EMAIL_TOI_DA or not _EMAIL.fullmatch(email):
        raise ValueError("Email không hợp lệ")
    return email


EmailTuyChon = Annotated[str | None, BeforeValidator(_chuan_hoa_email)]


def _email_bat_buoc(gia_tri: object) -> str:
    email = _chuan_hoa_email(gia_tri)
    if email is None:
        raise ValueError("Email không được để trống")
    return email


EmailBatBuoc = Annotated[str, BeforeValidator(_email_bat_buoc)]
"""Email bắt buộc: cắt khoảng trắng, đổi sang chữ thường, kiểm tra định dạng (dùng cho tài khoản nhân viên)."""


class OtpYeuCau(BaseModel):
    so_dien_thoai: SoDienThoai
    # `don_thuoc_khach`: khách vãng lai xác thực SĐT trước khi gửi ảnh đơn thuốc (KVL08)
    muc_dich: Literal["dang_ky", "quen_mat_khau", "don_thuoc_khach"]
    # Gửi mã qua email của tài khoản (chỉ để lấy lại mật khẩu). Tài khoản chưa có email thì tự gửi SMS.
    kenh: Literal["sms", "email"] = "sms"

    @model_validator(mode="after")
    def _email_chi_de_lay_lai_mat_khau(self) -> "OtpYeuCau":
        if self.kenh == "email" and self.muc_dich != "quen_mat_khau":
            raise ValueError("Chỉ gửi mã qua email khi lấy lại mật khẩu")
        return self


class OtpPhanHoi(BaseModel):
    da_gui: bool
    het_han_giay: int


class DangKyYeuCau(BaseModel):
    so_dien_thoai: SoDienThoai
    otp: Annotated[str, Field(pattern=r"^[0-9]{6}$")]
    mat_khau: Annotated[str, Field(max_length=128)]
    ho_ten: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
    email: EmailTuyChon = None
    dong_y_chinh_sach: bool

    @field_validator("mat_khau")
    @classmethod
    def _mat_khau_du_manh(cls, gia_tri: str) -> str:
        if not mat_khau_du_manh(gia_tri):
            raise ValueError("Mật khẩu cần tối thiểu 8 ký tự, gồm cả chữ và số")
        return gia_tri

    @field_validator("dong_y_chinh_sach")
    @classmethod
    def _phai_dong_y(cls, gia_tri: bool) -> bool:
        if not gia_tri:
            raise ValueError("Bạn cần đồng ý với chính sách của nhà thuốc để đăng ký")
        return gia_tri


class KhachHangDoc(BaseModel):
    """Hồ sơ khách trả về cho chính họ. Không bao giờ chứa mật khẩu, hash hay trạng thái khóa."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ho_ten: str
    so_dien_thoai: str
    email: str | None


class DangNhapYeuCau(BaseModel):
    """`ten_dang_nhap` là số điện thoại hoặc email đã đăng ký."""

    ten_dang_nhap: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
    mat_khau: Annotated[str, Field(min_length=1, max_length=128)]


class CapTokenPhanHoi(BaseModel):
    """Refresh token KHÔNG nằm trong thân phản hồi: nó chỉ đi trong cookie httpOnly."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    het_han_giay: int


class DangNhapPhanHoi(CapTokenPhanHoi):
    khach_hang: KhachHangDoc


class DatLaiMatKhauYeuCau(BaseModel):
    so_dien_thoai: SoDienThoai
    otp: Annotated[str, Field(pattern=r"^[0-9]{6}$")]
    mat_khau_moi: Annotated[str, Field(max_length=128)]

    @field_validator("mat_khau_moi")
    @classmethod
    def _mat_khau_du_manh(cls, gia_tri: str) -> str:
        if not mat_khau_du_manh(gia_tri):
            raise ValueError("Mật khẩu cần tối thiểu 8 ký tự, gồm cả chữ và số")
        return gia_tri


class DatLaiMatKhauPhanHoi(BaseModel):
    da_dat_lai: bool

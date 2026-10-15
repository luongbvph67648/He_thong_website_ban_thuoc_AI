"""Schema API xác thực và hồ sơ nhân viên (spec 06 mục 3.3). Không bao giờ chứa mật khẩu hay hash."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.core.bao_mat import mat_khau_du_manh
from app.core.dien_thoai import chuan_hoa_sdt
from app.modules.tai_khoan.schemas import CapTokenPhanHoi

HoTen = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]


class VaiTroDoc(BaseModel):
    ma: str
    ten: str


class NhanVienToi(BaseModel):
    """Hồ sơ của chính nhân viên đang đăng nhập, kèm quyền để giao diện ẩn/hiện menu (lớp phụ, backend vẫn kiểm tra)."""

    id: int
    ma_nhan_vien: str
    ho_ten: str
    email: str
    so_dien_thoai: str | None
    vai_tro: VaiTroDoc
    phai_doi_mat_khau: bool
    quyen: dict[str, Literal["day_du", "chi_xem"]]


class DangNhapNhanVienYeuCau(BaseModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
    mat_khau: Annotated[str, Field(min_length=1, max_length=128)]


class PhienNhanVienPhanHoi(CapTokenPhanHoi):
    """Phản hồi đăng nhập và đổi mật khẩu: token mới kèm hồ sơ để giao diện khỏi gọi thêm `/noi-bo/toi`."""

    nhan_vien: NhanVienToi


class DoiMatKhauYeuCau(BaseModel):
    mat_khau_cu: Annotated[str, Field(min_length=1, max_length=128)]
    mat_khau_moi: Annotated[str, Field(max_length=128)]

    @field_validator("mat_khau_moi")
    @classmethod
    def _du_manh_va_khac_mat_khau_cu(cls, gia_tri: str, info) -> str:
        if not mat_khau_du_manh(gia_tri):
            raise ValueError("Mật khẩu cần tối thiểu 8 ký tự, gồm cả chữ và số")
        if gia_tri == info.data.get("mat_khau_cu"):
            raise ValueError("Mật khẩu mới phải khác mật khẩu cũ")
        return gia_tri


class CapNhatHoSoYeuCau(BaseModel):
    """Chỉ gửi trường cần đổi. `so_dien_thoai = null` (hoặc rỗng) là xóa số. Email do Admin quản lý (AD01): gửi lên
    thì bị từ chối (400) thay vì lặng lẽ bỏ qua."""

    model_config = ConfigDict(extra="forbid")

    ho_ten: HoTen | None = None
    so_dien_thoai: str | None = None

    @field_validator("so_dien_thoai", mode="before")
    @classmethod
    def _chuan_hoa_sdt(cls, gia_tri: object) -> str | None:
        if gia_tri is None or (isinstance(gia_tri, str) and gia_tri.strip() == ""):
            return None
        return chuan_hoa_sdt(gia_tri)  # type: ignore[arg-type]

    @field_validator("ho_ten", mode="before")
    @classmethod
    def _ho_ten_khong_duoc_null(cls, gia_tri: object) -> object:
        if gia_tri is None:
            raise ValueError("Họ tên không được để trống")
        return gia_tri

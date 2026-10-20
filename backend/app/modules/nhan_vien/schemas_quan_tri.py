"""Schema API quản lý tài khoản nhân viên của Admin (AD01, spec 06 mục 3.4). Không bao giờ chứa mật khẩu hay hash,
(mật khẩu tạm chỉ gửi qua email cho nhân viên)."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

from app.core.dien_thoai import chuan_hoa_sdt
from app.models.enums import TrangThaiTaiKhoan
from app.modules.nhan_vien.schemas import HoTen, VaiTroDoc
from app.modules.tai_khoan.schemas import EmailBatBuoc

MaVaiTro = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]


def _chuan_hoa_sdt_tuy_chon(gia_tri: object) -> str | None:
    if gia_tri is None or (isinstance(gia_tri, str) and gia_tri.strip() == ""):
        return None
    return chuan_hoa_sdt(gia_tri)  # type: ignore[arg-type]


class NhanVienQuanTriDoc(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ma_nhan_vien: str
    ho_ten: str
    email: str
    so_dien_thoai: str | None
    vai_tro: VaiTroDoc
    trang_thai: TrangThaiTaiKhoan
    phai_doi_mat_khau: bool
    khoa_den: datetime | None
    created_at: datetime
    updated_at: datetime | None


class NhanVienTao(BaseModel):
    ho_ten: HoTen
    email: EmailBatBuoc
    so_dien_thoai: str | None = None
    vai_tro: MaVaiTro

    _chuan_hoa_sdt = field_validator("so_dien_thoai", mode="before")(_chuan_hoa_sdt_tuy_chon)


class NhanVienSua(BaseModel):
    """Chỉ gửi trường cần đổi. Đổi `vai_tro` thu hồi mọi phiên của nhân viên đó."""

    model_config = ConfigDict(extra="forbid")

    ho_ten: HoTen | None = None
    email: EmailBatBuoc | None = None
    so_dien_thoai: str | None = None
    vai_tro: MaVaiTro | None = None

    _chuan_hoa_sdt = field_validator("so_dien_thoai", mode="before")(_chuan_hoa_sdt_tuy_chon)

    @field_validator("ho_ten", "email", "vai_tro", mode="before")
    @classmethod
    def _khong_duoc_null(cls, gia_tri: object) -> object:
        if gia_tri is None:
            raise ValueError("Không được để trống")
        return gia_tri


class NhanVienDaGuiMatKhau(NhanVienQuanTriDoc):
    """Phản hồi tạo tài khoản và đặt lại mật khẩu: mật khẩu tạm gửi tới email của nhân viên, Admin không nhận được."""

    gui_den: str
    """Email nhận mật khẩu tạm, đã che (`a***@mien.vn`)."""

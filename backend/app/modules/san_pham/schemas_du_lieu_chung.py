"""Schema API dữ liệu dùng chung: thương hiệu, nhà sản xuất, hoạt chất (AD05, spec 06 mục 3.10)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.kieu_du_lieu import DuongDanTuyChon, kieu_ten, van_ban_tuy_chon

TenThuongHieu = kieu_ten(150)
TenNhaSanXuat = kieu_ten(200)
TenHoatChat = kieu_ten(200)
QuocGia = van_ban_tuy_chon(100)
TenKhac = van_ban_tuy_chon(1000)
MoTa = van_ban_tuy_chon(2000, nhieu_dong=True)


class _Doc(BaseModel):
    id: int
    created_at: datetime
    so_san_pham: int
    """Số sản phẩm (kể cả đã xóa mềm) gắn với bản ghi; hoạt chất: số dòng `thanh_phan`."""


class _KhongNhanNull(BaseModel):
    """PATCH: `ten` là bắt buộc nên gửi `null` là lỗi (khác với trường tùy chọn, `null` nghĩa là xóa giá trị)."""

    @field_validator("ten", check_fields=False, mode="before")
    @classmethod
    def _ten_khong_null(cls, gia_tri: object) -> object:
        if gia_tri is None:
            raise ValueError("Không được để trống")
        return gia_tri


# --- Thương hiệu -----------------------------------------------------------------------------------------------------


class ThuongHieuDoc(_Doc):
    ten: str
    logo_url: str | None


class ThuongHieuTao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ten: TenThuongHieu
    logo_url: DuongDanTuyChon = None


class ThuongHieuSua(_KhongNhanNull):
    model_config = ConfigDict(extra="forbid")

    ten: TenThuongHieu | None = None
    logo_url: DuongDanTuyChon = None


# --- Nhà sản xuất ----------------------------------------------------------------------------------------------------


class NhaSanXuatDoc(_Doc):
    ten: str
    quoc_gia: str | None


class NhaSanXuatTao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ten: TenNhaSanXuat
    quoc_gia: QuocGia = None


class NhaSanXuatSua(_KhongNhanNull):
    model_config = ConfigDict(extra="forbid")

    ten: TenNhaSanXuat | None = None
    quoc_gia: QuocGia = None


# --- Hoạt chất -------------------------------------------------------------------------------------------------------


class HoatChatDoc(_Doc):
    ten: str
    ten_khac: str | None
    mo_ta: str | None


class HoatChatTao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ten: TenHoatChat
    ten_khac: TenKhac = None
    mo_ta: MoTa = None


class HoatChatSua(_KhongNhanNull):
    model_config = ConfigDict(extra="forbid")

    ten: TenHoatChat | None = None
    ten_khac: TenKhac = None
    mo_ta: MoTa = None

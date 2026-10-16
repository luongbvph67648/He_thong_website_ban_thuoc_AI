"""Schema API quản lý danh mục (AD03, spec 06 mục 3.9)."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.kieu_du_lieu import DuongDanTuyChon, kieu_ten
from app.core.slug import tao_slug

IdDanhMuc = Annotated[int, Field(ge=1, le=2_147_483_647)]
TenDanhMuc = kieu_ten(150)


def _ten_phai_co_chu(ten: str) -> str:
    try:
        tao_slug(ten)
    except ValueError as loi:
        raise ValueError("Tên phải có ít nhất một chữ hoặc số") from loi
    return ten


class DanhMucNut(BaseModel):
    """Một nút của cây danh mục; `con` đã xếp theo `thu_tu` rồi `id`."""

    id: int
    ten: str
    slug: str
    danh_muc_cha_id: int | None
    anh_url: str | None
    thu_tu: int
    dang_hien_thi: bool
    cap: int
    """1 đến 3."""
    so_san_pham: int
    """Số sản phẩm chưa xóa nằm TRỰC TIẾP trong danh mục này."""
    con: list["DanhMucNut"]


class DanhMucTao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ten: TenDanhMuc
    danh_muc_cha_id: IdDanhMuc | None = None
    anh_url: DuongDanTuyChon = None
    dang_hien_thi: bool = True

    _ten_co_chu = field_validator("ten")(_ten_phai_co_chu)


class DanhMucSua(BaseModel):
    """Chỉ gửi trường cần đổi. Chuyển cha và sắp xếp dùng `PUT .../vi-tri`, không dùng PATCH."""

    model_config = ConfigDict(extra="forbid")

    ten: TenDanhMuc | None = None
    anh_url: DuongDanTuyChon = None
    dang_hien_thi: bool | None = None

    @field_validator("ten", "dang_hien_thi", mode="before")
    @classmethod
    def _khong_duoc_null(cls, gia_tri: object) -> object:
        if gia_tri is None:
            raise ValueError("Không được để trống")
        return gia_tri

    @field_validator("ten")
    @classmethod
    def _ten_co_chu(cls, ten: str | None) -> str | None:
        return None if ten is None else _ten_phai_co_chu(ten)


class ViTriDanhMuc(BaseModel):
    model_config = ConfigDict(extra="forbid")

    danh_muc_cha_id: IdDanhMuc | None
    """Bắt buộc phải gửi (không có thì lỗi): `null` là đặt ở gốc."""
    vi_tri: Annotated[int, Field(ge=0, le=100_000)]
    """Chỉ số trong các danh mục cùng cha, từ 0; lớn hơn số anh em thì đặt cuối."""

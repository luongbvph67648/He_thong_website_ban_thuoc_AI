"""Schema API cấu hình hệ thống (AD08) và nhật ký hệ thống (AD15), spec 06 mục 3.7 và 3.8."""

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.core.cau_hinh_khoa import KieuCauHinh


class NhanVienTomTat(BaseModel):
    """Người thực hiện: chỉ id, mã và tên (không email, không số điện thoại)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ma_nhan_vien: str
    ho_ten: str


class TruongSoDoc(BaseModel):
    ten: str
    nhan: str
    don_vi: str | None
    toi_thieu: int
    toi_da: int


class CauHinhDoc(BaseModel):
    khoa: str
    nhom: str
    nhan: str
    mo_ta: str | None
    kieu: KieuCauHinh
    don_vi: str | None
    toi_thieu: int | None
    toi_da: int | None
    truong: list[TruongSoDoc]
    gia_tri: Any
    """`None` khi khóa chưa có trong bảng (chưa seed)."""
    phien_ban: str
    nhan_vien_cap_nhat: NhanVienTomTat | None
    updated_at: datetime | None


class CauHinhCapNhat(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gia_tri: Any
    phien_ban: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{16}$")]
    """`phien_ban` của lần đọc mà bản sửa này dựa trên; lệch là `409 DU_LIEU_DA_THAY_DOI`."""


class NhatKyDoc(BaseModel):
    id: int
    created_at: datetime
    nhan_vien: NhanVienTomTat | None
    hanh_dong: str
    bang: str
    ban_ghi_id: str | None
    gia_tri_cu: Any
    gia_tri_moi: Any
    ip: str | None


class GiaTriLocNhatKy(BaseModel):
    bang: list[str]
    hanh_dong: list[str]

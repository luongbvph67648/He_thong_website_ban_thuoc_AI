"""Schema API nhà cung cấp (KHO01, spec 06 mục 3.15)."""

import re
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, field_validator

from app.core.dien_thoai import chuan_hoa_sdt
from app.core.kieu_du_lieu import kieu_ten, van_ban_tuy_chon
from app.modules.tai_khoan.schemas import _email_bat_buoc

TenNhaCungCap = kieu_ten(200)
_MST = re.compile(r"(\d{10})(?:-?(\d{3}))?")


def _ma_so_thue_tuy_chon(gia_tri: Any) -> str | None:
    """Mã số thuế 10 số hoặc 13 số (đơn vị phụ thuộc); lưu `xxxxxxxxxx` hoặc `xxxxxxxxxx-xxx`. Trống là `None`."""
    if gia_tri is None:
        return None
    if not isinstance(gia_tri, str):
        raise ValueError("Phải là chuỗi")
    s = gia_tri.strip()
    if s == "":
        return None
    khop = _MST.fullmatch(s.replace(" ", ""))
    if khop is None or not s.isascii():
        raise ValueError("Mã số thuế gồm 10 hoặc 13 chữ số")
    chinh, phu = khop.groups()
    return chinh if phu is None else f"{chinh}-{phu}"


def _sdt_tuy_chon(gia_tri: Any) -> str | None:
    if gia_tri is None or (isinstance(gia_tri, str) and gia_tri.strip() == ""):
        return None
    return chuan_hoa_sdt(gia_tri)


def _email_tuy_chon(gia_tri: Any) -> Any:
    if gia_tri is None or (isinstance(gia_tri, str) and gia_tri.strip() == ""):
        return None
    email = _email_bat_buoc(gia_tri)
    if len(email) > 150:
        raise ValueError("Tối đa 150 ký tự")
    return email


MaSoThue = Annotated[str | None, BeforeValidator(_ma_so_thue_tuy_chon)]
SoDienThoaiTuyChon = Annotated[str | None, BeforeValidator(_sdt_tuy_chon)]
EmailTuyChon = Annotated[str | None, BeforeValidator(_email_tuy_chon)]
DiaChi = van_ban_tuy_chon(500)
NguoiLienHe = van_ban_tuy_chon(150)


class NhaCungCapRa(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ten: str
    ma_so_thue: str | None
    dia_chi: str | None
    nguoi_lien_he: str | None
    so_dien_thoai: str | None
    email: str | None
    dang_hop_tac: bool
    created_at: datetime
    phien_ban: str


class NhaCungCapTao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ten: TenNhaCungCap
    ma_so_thue: MaSoThue = None
    dia_chi: DiaChi = None
    nguoi_lien_he: NguoiLienHe = None
    so_dien_thoai: SoDienThoaiTuyChon = None
    email: EmailTuyChon = None


class NhaCungCapSua(BaseModel):
    """Chỉ các trường gửi lên được đổi; `null` ở trường tùy chọn là xóa giá trị, `null` ở `ten` là lỗi."""

    model_config = ConfigDict(extra="forbid")

    phien_ban: str
    ten: TenNhaCungCap | None = None
    ma_so_thue: MaSoThue = None
    dia_chi: DiaChi = None
    nguoi_lien_he: NguoiLienHe = None
    so_dien_thoai: SoDienThoaiTuyChon = None
    email: EmailTuyChon = None

    @field_validator("ten", mode="before")
    @classmethod
    def _ten_khong_null(cls, v: Any) -> Any:
        if v is None:
            raise ValueError("Không được để trống")
        return v

"""Schema API vai trò và phân quyền (AD18, spec 06 mục 3.5)."""

from typing import Literal

from pydantic import BaseModel

MucQuyenApi = Literal["day_du", "chi_xem"]


class VaiTroTomTat(BaseModel):
    ma: str
    ten: str
    mo_ta: str | None
    so_nhan_vien: int
    so_quyen: int
    chinh_sua_duoc: bool


class QuyenTrongVaiTro(BaseModel):
    """Một mã quyền và mức mà vai trò đang có (`null` là không có)."""

    ma: str
    nhom: str | None
    mo_ta: str | None
    muc: MucQuyenApi | None
    bat_buoc: bool
    """Quyền mọi vai trò phải có ở mức đầy đủ (không gỡ, không hạ được)."""
    chi_cho_vai_tro: str | None
    """Quyền chỉ được cấp cho đúng một vai trò (spec 03 mục 7); vai trò khác không gán được."""


class VaiTroChiTiet(BaseModel):
    ma: str
    ten: str
    mo_ta: str | None
    so_nhan_vien: int
    chinh_sua_duoc: bool
    quyen: list[QuyenTrongVaiTro]


class CapNhatQuyenYeuCau(BaseModel):
    """Thay TOÀN BỘ quyền của vai trò: mã nào không có trong `quyen` thì vai trò không còn quyền đó."""

    quyen: dict[str, MucQuyenApi]

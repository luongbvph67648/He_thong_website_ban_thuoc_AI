"""Schema API vai trò và phân quyền (AD18, spec 06 mục 3.5)."""

from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints

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
    """Quyền chỉ được cấp cho đúng một vai trò: nội dung chuyên môn chỉ PHARMACIST (spec 03 mục 7), quyền quản trị mà
    ma trận chỉ cấp cho ADMIN thì chỉ ADMIN. Vai trò khác không gán được."""


class VaiTroChiTiet(BaseModel):
    ma: str
    ten: str
    mo_ta: str | None
    so_nhan_vien: int
    chinh_sua_duoc: bool
    phien_ban: str
    """Dấu vân tay của tập (mã quyền, mức) hiện có; gửi lại khi lưu để không ghi đè thay đổi của Admin khác."""
    quyen: list[QuyenTrongVaiTro]


class CapNhatQuyenYeuCau(BaseModel):
    """Thay TOÀN BỘ quyền của vai trò: mã nào không có trong `quyen` thì vai trò không còn quyền đó."""

    quyen: dict[str, MucQuyenApi]
    phien_ban: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{16}$")]
    """`phien_ban` của lần đọc mà bản sửa này dựa trên. Lệch với bản hiện tại là `409 DU_LIEU_DA_THAY_DOI`."""

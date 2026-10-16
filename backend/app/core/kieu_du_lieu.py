"""Kiểu dữ liệu Pydantic dùng chung cho các schema nhập liệu của Admin (tên, đường dẫn ảnh)."""

import re
import unicodedata
from typing import Annotated, Any

from pydantic import BeforeValidator, StringConstraints

# `/\host` và `//host` đều là "cùng giao thức, máy khác" với trình duyệt (nó đổi `\` thành `/`): cấm cả hai.
_DUONG_DAN = re.compile(r"(https?://[^\s]+|/(?![/\\])[^\s]*)")
DO_DAI_DUONG_DAN_TOI_DA = 500
_LOAI_KHONG_HOP_LE = frozenset({"Cc", "Cf", "Cs"})
THONG_DIEP_KY_TU_CAM = "Không được chứa ký tự điều khiển hoặc ký tự vô hình"


def _co_ky_tu_dieu_khien(chuoi: str, cho_phep: str = "") -> bool:
    """Ký tự không nên có trong dữ liệu nhập, ngoài `cho_phep`.

    - `Cc` điều khiển (NUL làm PostgreSQL từ chối nên request thành 500);
    - `Cf` định dạng vô hình (U+200B, BOM, dấu bidi...): hai tên trông giống hệt nhau mà không bị coi là trùng;
    - `Cs` surrogate đơn lẻ (JSON `"\\ud800"`): Python giữ được nhưng không mã hóa UTF-8, asyncpg báo lỗi 500.
    """
    return any(unicodedata.category(c) in _LOAI_KHONG_HOP_LE and c not in cho_phep for c in chuoi)


def _gon(gia_tri: Any) -> Any:
    """Bỏ khoảng trắng đầu cuối và gộp khoảng trắng liên tiếp; không phải chuỗi thì để Pydantic báo lỗi kiểu."""
    if not isinstance(gia_tri, str):
        return gia_tri
    gon = " ".join(gia_tri.split())
    if _co_ky_tu_dieu_khien(gon):
        raise ValueError(THONG_DIEP_KY_TU_CAM)
    return gon


def kieu_ten(toi_da: int):
    """Tên hiển thị: không rỗng, đã gọn khoảng trắng, tối đa `toi_da` ký tự."""
    return Annotated[str, BeforeValidator(_gon), StringConstraints(min_length=1, max_length=toi_da)]


def _duong_dan_tuy_chon(gia_tri: Any) -> str | None:
    if gia_tri is None:
        return None
    if not isinstance(gia_tri, str):
        raise ValueError("Phải là chuỗi")
    s = gia_tri.strip()
    if s == "":
        return None
    if len(s) > DO_DAI_DUONG_DAN_TOI_DA or _co_ky_tu_dieu_khien(s) or not _DUONG_DAN.fullmatch(s):
        raise ValueError(
            "Đường dẫn phải bắt đầu bằng / hoặc http(s)://, không có khoảng trắng, "
            f"tối đa {DO_DAI_DUONG_DAN_TOI_DA} ký tự"
        )
    return s


DuongDanTuyChon = Annotated[str | None, BeforeValidator(_duong_dan_tuy_chon)]
"""Đường dẫn ảnh/logo: trống là `None`; chỉ nhận `/...` hoặc `http(s)://...` (không `javascript:`, `data:`)."""


def chuan_hoa_van_ban(gia_tri: Any, toi_da: int, *, nhieu_dong: bool = False) -> str | None:
    """Chuẩn hóa văn bản tùy chọn: trống (hoặc chỉ khoảng trắng) là `None`; một dòng thì gộp khoảng trắng, nhiều dòng
    thì chỉ cắt đầu cuối và cho phép xuống dòng, tab; từ chối ký tự điều khiển/vô hình và chuỗi dài quá `toi_da`."""
    if gia_tri is None:
        return None
    if not isinstance(gia_tri, str):
        raise ValueError("Phải là chuỗi")
    s = gia_tri.strip() if nhieu_dong else " ".join(gia_tri.split())
    if s == "":
        return None
    if _co_ky_tu_dieu_khien(s, "\n\r\t" if nhieu_dong else ""):
        raise ValueError(THONG_DIEP_KY_TU_CAM)
    if len(s) > toi_da:
        raise ValueError(f"Tối đa {toi_da} ký tự")
    return s


def van_ban_tuy_chon(toi_da: int, *, nhieu_dong: bool = False):
    """Kiểu văn bản tùy chọn (xem `chuan_hoa_van_ban`)."""

    def kiem_tra(gia_tri: Any) -> str | None:
        return chuan_hoa_van_ban(gia_tri, toi_da, nhieu_dong=nhieu_dong)

    return Annotated[str | None, BeforeValidator(kiem_tra)]

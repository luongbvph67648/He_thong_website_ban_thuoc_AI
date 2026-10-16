"""Kiểu dữ liệu Pydantic dùng chung cho các schema nhập liệu của Admin (tên, đường dẫn ảnh)."""

import re
import unicodedata
from typing import Annotated, Any

from pydantic import BeforeValidator, StringConstraints

_DUONG_DAN = re.compile(r"(https?://[^\s]+|/(?!/)[^\s]*)")
DO_DAI_DUONG_DAN_TOI_DA = 500
_KY_TU_DIEU_KHIEN = re.compile(r"[\x00-\x1f\x7f]")


def _co_ky_tu_dieu_khien(chuoi: str, cho_phep: str = "") -> bool:
    """Ký tự điều khiển (kể cả NUL, mà PostgreSQL từ chối khiến request thành 500) ngoài `cho_phep`."""
    return any(unicodedata.category(c) == "Cc" and c not in cho_phep for c in chuoi)


def _gon(gia_tri: Any) -> Any:
    """Bỏ khoảng trắng đầu cuối và gộp khoảng trắng liên tiếp; không phải chuỗi thì để Pydantic báo lỗi kiểu."""
    if not isinstance(gia_tri, str):
        return gia_tri
    gon = " ".join(gia_tri.split())
    if _co_ky_tu_dieu_khien(gon):
        raise ValueError("Không được chứa ký tự điều khiển")
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
    if len(s) > DO_DAI_DUONG_DAN_TOI_DA or _KY_TU_DIEU_KHIEN.search(s) or not _DUONG_DAN.fullmatch(s):
        raise ValueError(
            "Đường dẫn phải bắt đầu bằng / hoặc http(s)://, không có khoảng trắng, "
            f"tối đa {DO_DAI_DUONG_DAN_TOI_DA} ký tự"
        )
    return s


DuongDanTuyChon = Annotated[str | None, BeforeValidator(_duong_dan_tuy_chon)]
"""Đường dẫn ảnh/logo: trống là `None`; chỉ nhận `/...` hoặc `http(s)://...` (không `javascript:`, `data:`)."""


def van_ban_tuy_chon(toi_da: int, *, nhieu_dong: bool = False):
    """Văn bản tùy chọn: trống (hoặc chỉ khoảng trắng) là `None`; một dòng thì gộp khoảng trắng, nhiều dòng thì chỉ cắt
    đầu cuối và cho phép xuống dòng, tab; luôn từ chối ký tự điều khiển khác và chuỗi dài quá `toi_da`."""

    def kiem_tra(gia_tri: Any) -> str | None:
        if gia_tri is None:
            return None
        if not isinstance(gia_tri, str):
            raise ValueError("Phải là chuỗi")
        s = gia_tri.strip() if nhieu_dong else " ".join(gia_tri.split())
        if s == "":
            return None
        if _co_ky_tu_dieu_khien(s, "\n\r\t" if nhieu_dong else ""):
            raise ValueError("Không được chứa ký tự điều khiển")
        if len(s) > toi_da:
            raise ValueError(f"Tối đa {toi_da} ký tự")
        return s

    return Annotated[str | None, BeforeValidator(kiem_tra)]

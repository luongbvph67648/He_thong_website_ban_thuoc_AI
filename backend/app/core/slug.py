"""Slug URL từ tên tiếng Việt: bỏ dấu, chữ thường, nối bằng dấu gạch ngang."""

import re
import unicodedata

_KHONG_PHAI_CHU_SO = re.compile(r"[^a-z0-9]+")


def tao_slug(ten: str, toi_da: int = 150) -> str:
    """`"Thuốc ho Bổ phế"` -> `"thuoc-ho-bo-phe"`. Quá dài thì cắt ở ranh giới từ, không để thừa dấu gạch."""
    khong_dau = unicodedata.normalize("NFD", ten.replace("đ", "d").replace("Đ", "D"))
    khong_dau = "".join(k for k in khong_dau if not unicodedata.combining(k))
    slug = _KHONG_PHAI_CHU_SO.sub("-", khong_dau.lower()).strip("-")
    if not slug:
        raise ValueError(f"Không tạo được slug từ {ten!r}: không có chữ hoặc số")
    if len(slug) > toi_da:
        cat = slug[:toi_da]
        if slug[toi_da] != "-" and "-" in cat:  # đang cắt dở một từ: bỏ từ đó
            cat = cat.rsplit("-", 1)[0]
        slug = cat.strip("-")
    return slug

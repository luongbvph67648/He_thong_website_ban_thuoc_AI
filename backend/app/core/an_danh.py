"""Che thông tin cá nhân trong văn bản tự do trước khi cho Admin/dược sĩ xem lại hội thoại (AD11, DS12).

Chỉ là nỗ lực tốt nhất: bắt số điện thoại, email, dãy số dài (CCCD, thẻ), tên đầy đủ của chính khách đăng nhập (và từng
từ của tên từ 3 ký tự) và cụm tự xưng "tên tôi là ...". Không đảm bảo bắt mọi cách khách tự viết tên hay địa chỉ, vì vậy
màn hình chỉ gọi là "đã ẩn danh" và không bao giờ kèm id khách, mã phiên hay IP."""

import re
from collections.abc import Iterable

_EMAIL = re.compile(r"[\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+")
_SDT = re.compile(r"(?<!\d)(?:\+?84|0)(?:[\s.\-]?\d){8,10}(?!\d)")
_DAY_SO = re.compile(r"(?<!\d)\d(?:[\s.\-]?\d){7,}(?!\d)")
_TU_XUNG = re.compile(
    r"\b([Tt]ên(?: tôi| mình| em| con| cháu| bé)?(?: là)?)\s+[A-ZÀ-Ỹ][a-zà-ỹ]*(?: [A-ZÀ-Ỹ][a-zà-ỹ]*){0,3}"
)
_CACH = re.compile(r"\s+")
TU_TOI_THIEU = 3


def _mau_ten(ten: str) -> list[str]:
    day_du = _CACH.sub(" ", ten.strip())
    if not day_du:
        return []
    cac_tu = {t for t in day_du.split(" ") if len(t) >= TU_TOI_THIEU}
    return [day_du, *sorted(cac_tu, key=len, reverse=True)]


def che_thong_tin(van_ban: str | None, ten_khach: str | None = None, ten_khac: Iterable[str] = ()) -> str:
    """Trả bản đã che; `None` thành chuỗi rỗng."""
    if not van_ban:
        return ""
    kq = _EMAIL.sub("[email]", van_ban)
    kq = _SDT.sub("[SĐT]", kq)
    kq = _DAY_SO.sub("[số]", kq)
    kq = _TU_XUNG.sub(lambda m: f"{m.group(1)} [tên]", kq)
    for ten in (ten_khach, *ten_khac):
        for mau in _mau_ten(ten or ""):
            kq = re.sub(rf"(?<!\w){re.escape(mau)}(?!\w)", "[tên]", kq, flags=re.IGNORECASE)
    return kq

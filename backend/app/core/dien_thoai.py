"""Số điện thoại di động Việt Nam: chuẩn hóa về `0xxxxxxxxx` và che bớt khi ghi log."""

import re

_KY_TU_NGAN_CACH = re.compile(r"[ .\-]")
_DI_DONG = re.compile(r"0[35789][0-9]{8}")  # đầu số 03x, 05x, 07x, 08x, 09x, 10 chữ số ASCII
# (không dùng \d vì \d của Python nhận cả chữ số Unicode)


def chuan_hoa_sdt(gia_tri: object) -> str:
    """`"+84 912 345 678"` -> `"0912345678"`. Chỉ nhận số di động Việt Nam; sai thì ném ValueError (tiếng Việt)."""
    if not isinstance(gia_tri, str):
        raise ValueError("Số điện thoại không hợp lệ")
    so = _KY_TU_NGAN_CACH.sub("", gia_tri.strip())
    if so.startswith("+84"):
        so = "0" + so[3:]
    elif so.startswith("84") and len(so) == 11:
        so = "0" + so[2:]
    if not _DI_DONG.fullmatch(so):
        raise ValueError("Số điện thoại không hợp lệ (cần số di động Việt Nam 10 chữ số)")
    return so


def che_sdt(so: str) -> str:
    """`0912345678` -> `091***678`: chỉ dùng khi ghi log, không bao giờ ghi số đầy đủ."""
    return f"{so[:3]}***{so[-3:]}" if len(so) >= 8 else "***"

"""Cookie refresh token `HttpOnly; SameSite=Lax; Secure`, chỉ gửi tới nhóm đường dẫn xác thực của từng loại (spec 06).

Khách và nhân viên dùng tên cookie và `Path` khác nhau, nên trình duyệt đang đăng nhập cả hai chỉ gửi đúng cookie cho
đúng nhóm endpoint.
"""

from fastapi import Response

from app.core.config import settings
from app.modules.tai_khoan.phien import LoaiPhien

TEN_COOKIE_REFRESH_KHACH = "refresh_token"
TEN_COOKIE_REFRESH_NOI_BO = "refresh_token_noi_bo"

_COOKIE: dict[LoaiPhien, tuple[str, str]] = {
    "khach": (TEN_COOKIE_REFRESH_KHACH, "/api/v1/auth"),
    "noi_bo": (TEN_COOKIE_REFRESH_NOI_BO, "/api/v1/noi-bo/auth"),
}


def ten_cookie_refresh(loai: LoaiPhien) -> str:
    return _COOKIE[loai][0]


def duong_dan_cookie_refresh(loai: LoaiPhien) -> str:
    return _COOKIE[loai][1]


def dat_cookie_refresh(response: Response, refresh_token: str, loai: LoaiPhien = "khach") -> None:
    ten, duong_dan = _COOKIE[loai]
    response.set_cookie(
        ten,
        refresh_token,
        max_age=settings.REFRESH_NGAY * 24 * 3600,
        path=duong_dan,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
    )


def xoa_cookie_refresh(response: Response, loai: LoaiPhien = "khach") -> None:
    ten, duong_dan = _COOKIE[loai]
    response.delete_cookie(ten, path=duong_dan, httponly=True, secure=settings.COOKIE_SECURE, samesite="lax")

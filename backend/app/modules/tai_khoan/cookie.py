"""Cookie refresh token của khách: `HttpOnly; SameSite=Lax; Secure`, chỉ gửi tới `/api/v1/auth` (spec 06 mục 3)."""

from fastapi import Response

from app.core.config import settings

TEN_COOKIE_REFRESH_KHACH = "refresh_token"
DUONG_COOKIE_REFRESH_KHACH = "/api/v1/auth"


def dat_cookie_refresh(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        TEN_COOKIE_REFRESH_KHACH,
        refresh_token,
        max_age=settings.REFRESH_NGAY * 24 * 3600,
        path=DUONG_COOKIE_REFRESH_KHACH,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
    )


def xoa_cookie_refresh(response: Response) -> None:
    response.delete_cookie(
        TEN_COOKIE_REFRESH_KHACH,
        path=DUONG_COOKIE_REFRESH_KHACH,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
    )

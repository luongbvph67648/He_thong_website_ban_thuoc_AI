"""Hàm dùng chung cho test đăng nhập, phiên và quên mật khẩu của khách (T1.2)."""

from http.cookies import SimpleCookie

from tests.factories import MAT_KHAU_TEST

SDT = "0912345678"
URL_DANG_NHAP = "/api/v1/auth/dang-nhap"
URL_LAM_MOI = "/api/v1/auth/lam-moi"
URL_DANG_XUAT = "/api/v1/auth/dang-xuat"
TEN_COOKIE = "refresh_token"


async def dang_nhap(client, ten_dang_nhap=SDT, mat_khau=MAT_KHAU_TEST):
    return await client.post(URL_DANG_NHAP, json={"ten_dang_nhap": ten_dang_nhap, "mat_khau": mat_khau})


def cookie_refresh(phan_hoi, ten: str = TEN_COOKIE) -> str | None:
    """Giá trị cookie refresh trong `Set-Cookie` của phản hồi (chuỗi rỗng nếu cookie bị xóa, None nếu không đặt)."""
    for dong in phan_hoi.headers.get_list("set-cookie"):
        cookie = SimpleCookie()
        cookie.load(dong)
        if ten in cookie:
            return cookie[ten].value
    return None


def dong_set_cookie(phan_hoi, ten: str = TEN_COOKIE) -> str:
    (dong,) = [d for d in phan_hoi.headers.get_list("set-cookie") if d.startswith(f"{ten}=")]
    return dong


def kem_cookie(refresh_token: str, ten: str = TEN_COOKIE) -> dict[str, str]:
    """Header `Cookie` gửi tay: tách khỏi cookie jar của client để test từng token cụ thể."""
    return {"Cookie": f"{ten}={refresh_token}"}


async def _goi_voi_cookie(client, url: str, refresh_token: str | None, ten: str = TEN_COOKIE):
    """POST kèm đúng cookie chỉ định. `None` nghĩa là KHÔNG gửi cookie nào: xóa cả cookie jar của client, vì cookie
    không `Secure` (khi dev tắt `COOKIE_SECURE`) sẽ được httpx tự lưu và gửi lại."""
    if refresh_token is None:
        client.cookies.clear()
        return await client.post(url)
    return await client.post(url, headers=kem_cookie(refresh_token, ten))


async def lam_moi(client, refresh_token: str | None):
    return await _goi_voi_cookie(client, URL_LAM_MOI, refresh_token)


async def dang_xuat(client, refresh_token: str | None):
    return await _goi_voi_cookie(client, URL_DANG_XUAT, refresh_token)

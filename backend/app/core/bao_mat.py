"""Bảo mật: băm mật khẩu Argon2id và access token JWT (spec 01 mục 5, spec 06 mục 3).

Refresh token, cookie và các dependency `khach_hien_tai`/`nhan_vien_hien_tai` làm ở T1.x; ở đây chỉ có phần tạo và
kiểm tra chữ ký token.
"""

import uuid
from datetime import timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import settings
from app.core.thoi_gian import bay_gio_utc

_hasher = PasswordHasher()  # Argon2id với tham số mặc định của argon2-cffi (theo khuyến nghị RFC 9106)

MAT_KHAU_TOI_THIEU = 8


def bam_mat_khau(mat_khau: str) -> str:
    """Băm mật khẩu bằng Argon2id, có salt ngẫu nhiên (cùng mật khẩu cho hai chuỗi băm khác nhau)."""
    return _hasher.hash(mat_khau)


def kiem_tra_mat_khau(mat_khau: str, ma_bam: str) -> bool:
    """Đúng/sai. Chuỗi băm hỏng hoặc không đúng định dạng cũng trả False, không ném lỗi."""
    try:
        return _hasher.verify(ma_bam, mat_khau)
    except (VerificationError, InvalidHashError):
        return False


def mat_khau_du_manh(mat_khau: str) -> bool:
    """Tối thiểu 8 ký tự, có ít nhất một chữ và một số (spec 06 mục 2)."""
    return (
        len(mat_khau) >= MAT_KHAU_TOI_THIEU
        and any(k.isalpha() for k in mat_khau)
        and any(k.isdigit() for k in mat_khau)
    )


# --- Access token JWT -----------------------------------------------------------------------------------------------

DOI_TUONG_HOP_LE = ("khach", "noi_bo")  # claim `aud`: khách hàng hoặc nhân viên (không dùng chung token)
KHOA_JWT_TOI_THIEU = 32
TIEN_TO_GIA_TRI_MAU = "doi-"
"""Giá trị mẫu trong `.env.example` đều bắt đầu bằng "doi-" (ví dụ `doi-gia-tri-nay-...`): đã công khai trong repo nên
không được dùng làm bí mật thật."""
_THUAT_TOAN = "HS256"


def _khoa_jwt() -> str:
    khoa = settings.JWT_SECRET.get_secret_value()
    if len(khoa) < KHOA_JWT_TOI_THIEU:
        raise RuntimeError(f"JWT_SECRET chưa đặt hoặc ngắn hơn {KHOA_JWT_TOI_THIEU} ký tự (xem backend/.env.example)")
    if khoa.startswith(TIEN_TO_GIA_TRI_MAU):
        raise RuntimeError("JWT_SECRET vẫn là giá trị mẫu của .env.example: hãy sinh chuỗi ngẫu nhiên riêng")
    return khoa


def tao_access_token(sub: int, aud: str, het_han_phut: int | None = None) -> str:
    """JWT HS256 với claim `sub` (id), `aud` (`khach` | `noi_bo`), `exp` (mặc định `JWT_ACCESS_PHUT`), `iat`, `jti`.

    Không chứa quyền: quyền luôn đọc từ DB (spec 03 mục 8).
    """
    if aud not in DOI_TUONG_HOP_LE:
        raise ValueError(f"aud phải là một trong {DOI_TUONG_HOP_LE}, nhận {aud!r}")
    bay_gio = bay_gio_utc()
    phut = settings.JWT_ACCESS_PHUT if het_han_phut is None else het_han_phut
    claim = {
        "sub": str(sub),
        "aud": aud,
        "iat": bay_gio,
        "exp": bay_gio + timedelta(minutes=phut),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(claim, _khoa_jwt(), algorithm=_THUAT_TOAN)


def giai_ma_access_token(token: str, aud: str) -> dict:
    """Kiểm tra chữ ký, hạn và `aud`, trả về claim. Sai thì ném lỗi của PyJWT (`ExpiredSignatureError`,
    `InvalidAudienceError`, `InvalidSignatureError`... đều là `jwt.InvalidTokenError`); `alg=none` bị từ chối."""
    return jwt.decode(
        token,
        _khoa_jwt(),
        algorithms=[_THUAT_TOAN],
        audience=aud,
        options={"require": ["exp", "iat", "sub", "aud", "jti"]},
    )

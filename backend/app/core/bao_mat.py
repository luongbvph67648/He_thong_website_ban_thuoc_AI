"""Bảo mật: băm mật khẩu Argon2id (spec 01 mục 5, spec 06 mục 2). JWT và hash refresh token thêm ở T1.x."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

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

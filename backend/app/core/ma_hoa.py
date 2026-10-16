"""Mã hóa mức ứng dụng cho dữ liệu sức khỏe (Fernet, khóa `KHOA_MA_HOA`; spec 03 mục 5.1).

Chỉ dùng cho `ho_so_suc_khoe.benh_nen`. Thiếu khóa, khóa sai định dạng hay bản mã không giải được đều báo lỗi hệ thống
với thông điệp chung, không kèm giá trị rõ hay bản mã.
"""

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet() -> Fernet:
    khoa = settings.KHOA_MA_HOA.get_secret_value()
    if not khoa or khoa.startswith("doi-"):
        raise RuntimeError("KHOA_MA_HOA chưa đặt hoặc vẫn là giá trị mẫu (xem backend/.env.example)")
    try:
        return Fernet(khoa.encode())
    except ValueError as loi:
        raise RuntimeError("KHOA_MA_HOA không phải khóa Fernet hợp lệ") from loi


def ma_hoa(ban_ro: str) -> str:
    return _fernet().encrypt(ban_ro.encode()).decode()


def giai_ma(ban_ma: str) -> str:
    try:
        return _fernet().decrypt(ban_ma.encode()).decode()
    except InvalidToken as loi:
        raise RuntimeError("Không giải mã được dữ liệu: sai khóa KHOA_MA_HOA hoặc dữ liệu hỏng") from loi

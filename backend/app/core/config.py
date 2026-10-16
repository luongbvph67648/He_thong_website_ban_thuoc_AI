from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Cấu hình đọc từ biến môi trường hoặc `backend/.env`. Chỉ khai báo trường đang dùng."""

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/nha_thuoc"
    CORS_ORIGINS: str = "http://localhost:5173"
    DATABASE_URL_TEST: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/nha_thuoc_test"
    # Khóa ký access token (HS256), tối thiểu 32 ký tự. Không có giá trị mặc định: để trống thì không tạo/giải mã token.
    JWT_SECRET: SecretStr = SecretStr("")
    JWT_ACCESS_PHUT: int = 15
    REFRESH_NGAY: int = 14
    # Cookie refresh token luôn `HttpOnly; SameSite=Lax`; `Secure` mặc định bật (trình duyệt hiện đại vẫn nhận trên http://localhost).
    COOKIE_SECURE: bool = True
    # Tin nhắn (OTP, thông báo): `gia` ghi SMS ra log, email qua SMTP tới Mailpit; `that` cần nhà cung cấp (spec 08).
    TIN_NHAN_CHE_DO: Literal["gia", "that"] = "gia"
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_NGUOI_GUI: str = "Nhà thuốc AI <no-reply@nhathuoc.local>"
    # Tài khoản Admin đầu tiên do `python -m app.seed` tạo. Để trống thì seed báo lỗi (không có giá trị mặc định
    # để khỏi vô tình tạo Admin với mật khẩu đoán được).
    ADMIN_EMAIL: str = ""
    ADMIN_MAT_KHAU: SecretStr = SecretStr("")
    # Thanh toán online (spec 08 mục 2-4): `gia` chạy offline với trang "cổng giả"; `sandbox` gọi VNPay/MoMo thật.
    THANH_TOAN_CHE_DO: Literal["gia", "sandbox"] = "gia"
    FRONTEND_URL: str = "http://localhost:5173"
    VNPAY_TMN_CODE: str = ""
    VNPAY_HASH_SECRET: SecretStr = SecretStr("")
    VNPAY_URL: str = ""
    VNPAY_RETURN_URL: str = ""
    MOMO_PARTNER_CODE: str = ""
    MOMO_ACCESS_KEY: str = ""
    MOMO_SECRET_KEY: SecretStr = SecretStr("")
    MOMO_ENDPOINT: str = ""
    MOMO_RETURN_URL: str = ""
    MOMO_IPN_URL: str = ""
    # Thư mục lưu file (spec 08 mục 6). Đường dẫn tương đối tính từ `backend/`, không phụ thuộc thư mục đang chạy.
    LUU_TRU_THU_MUC: str = "./storage"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()

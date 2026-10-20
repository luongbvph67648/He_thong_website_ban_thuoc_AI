from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Cấu hình đọc từ biến môi trường hoặc `backend/.env`. Chỉ khai báo trường đang dùng."""

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    # `production` bật chốt chặn khởi động (`kiem_tra_san_xuat`): cấm cổng giả, bắt buộc bí mật và cookie Secure.
    MOI_TRUONG: Literal["dev", "production"] = "dev"
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
    # Khóa Fernet mã hóa `ho_so_suc_khoe.benh_nen` (cách sinh khóa: xem .env.example).
    KHOA_MA_HOA: SecretStr = SecretStr("")
    # AI (spec 07): `AI_GIA_LAP=true` dùng client giả (`ai/gia_lap.py`), không gọi mạng và không cần khóa.
    ANTHROPIC_API_KEY: SecretStr = SecretStr("")
    CLAUDE_MODEL: str = "claude-opus-5-5"
    AI_GIA_LAP: bool = True
    AI_GIA_INPUT: float = 4  # USD / 1 triệu token
    AI_GIA_OUTPUT: float = 20
    AI_GIA_CACHE_READ: float = 0.20
    AI_NGAN_SACH_NGAY_USD: float = 2
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_GIA_LAP: bool = True
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
    # Vận chuyển (spec 08 mục 5): `gia` chạy offline kèm webhook giả; `ghn` gọi GHN thật.
    VAN_CHUYEN_CHE_DO: Literal["gia", "ghn"] = "gia"
    GHN_TOKEN: SecretStr = SecretStr("")
    GHN_SHOP_ID: str = ""
    GHN_URL: str = ""
    GHN_WEBHOOK_TOKEN: SecretStr = SecretStr("")
    # Thư mục lưu file (spec 08 mục 6). Đường dẫn tương đối tính từ `backend/`, không phụ thuộc thư mục đang chạy.
    LUU_TRU_THU_MUC: str = "./storage"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    def kiem_tra_san_xuat(self) -> list[str]:
        """Danh sách cấu hình không an toàn khi `MOI_TRUONG=production` (rỗng nếu đạt hoặc đang dev)."""
        if self.MOI_TRUONG != "production":
            return []
        loi: list[str] = []
        for ten, gia_tri in (
            ("JWT_SECRET", self.JWT_SECRET.get_secret_value()),
            ("KHOA_MA_HOA", self.KHOA_MA_HOA.get_secret_value()),
        ):
            if not gia_tri:
                loi.append(f"{ten} đang trống")
        if not self.COOKIE_SECURE:
            loi.append("COOKIE_SECURE phải là true")
        if self.THANH_TOAN_CHE_DO != "sandbox":
            loi.append("THANH_TOAN_CHE_DO=gia (cổng giả) không được dùng ở production")
        elif not (self.VNPAY_HASH_SECRET.get_secret_value() and self.MOMO_SECRET_KEY.get_secret_value()):
            loi.append("VNPAY_HASH_SECRET và MOMO_SECRET_KEY không được để trống")
        if self.VAN_CHUYEN_CHE_DO != "ghn":
            loi.append("VAN_CHUYEN_CHE_DO=gia (vận chuyển giả) không được dùng ở production")
        elif not self.GHN_WEBHOOK_TOKEN.get_secret_value():
            loi.append("GHN_WEBHOOK_TOKEN không được để trống")
        if self.AI_GIA_LAP:
            loi.append(
                "AI_GIA_LAP=true (Claude giả) không được dùng ở production: chatbot sẽ chuyển mọi câu cho dược sĩ"
            )
        if self.TIN_NHAN_CHE_DO != "that":
            loi.append("TIN_NHAN_CHE_DO=gia ghi OTP ra log, phải dùng `that`")
        return loi


settings = Settings()

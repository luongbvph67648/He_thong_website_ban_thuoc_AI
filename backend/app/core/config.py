from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Cấu hình đọc từ biến môi trường hoặc `backend/.env`. Chỉ khai báo trường đang dùng."""

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/nha_thuoc"
    CORS_ORIGINS: str = "http://localhost:5173"
    # Tài khoản Admin đầu tiên do `python -m app.seed` tạo. Để trống thì seed báo lỗi (không có giá trị mặc định
    # để khỏi vô tình tạo Admin với mật khẩu đoán được).
    ADMIN_EMAIL: str = ""
    ADMIN_MAT_KHAU: SecretStr = SecretStr("")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()

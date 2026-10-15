"""Import đủ mọi module để `Base.metadata` chứa toàn bộ 65 bảng (Alembic và create_all dựa vào việc này)."""

from app.models import ai, ban_hang, enums, he_thong, khach_hang, kho, san_pham  # noqa: F401
from app.models.base import Base

__all__ = ["Base"]

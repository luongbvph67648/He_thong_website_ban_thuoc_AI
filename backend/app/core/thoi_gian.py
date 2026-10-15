"""Thời gian: lưu UTC, ngày "hôm nay" tính theo giờ Việt Nam (spec 02 mục 3)."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def bay_gio_utc() -> datetime:
    return datetime.now(UTC)


def hom_nay_vn(bay_gio: datetime | None = None) -> date:
    """Ngày hiện tại theo giờ Việt Nam (so sánh hạn sử dụng, hạn đổi trả...). `bay_gio` để test."""
    if bay_gio is None:
        bay_gio = bay_gio_utc()
    if bay_gio.tzinfo is None:
        raise ValueError("bay_gio phải có múi giờ")
    return bay_gio.astimezone(VN_TZ).date()

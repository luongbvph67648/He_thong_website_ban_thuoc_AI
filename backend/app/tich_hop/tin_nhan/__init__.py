"""Kênh tin nhắn (SMS, email) cho OTP và thông báo (spec 08 mục 7).

Mẫu nội dung ở `mau/`. Không đưa dữ liệu sức khỏe vào SMS hoặc email.
"""

from typing import Protocol, runtime_checkable

from app.core.config import settings


class LoiGuiTinNhan(Exception):  # noqa: N818 - tên theo ngữ cảnh nghiệp vụ
    """Không gửi được tin nhắn (nhà cung cấp lỗi hoặc chưa cấu hình)."""


@runtime_checkable
class KenhTinNhan(Protocol):
    async def gui_sms(self, so_dien_thoai: str, noi_dung: str) -> None: ...

    async def gui_email(self, den: str, tieu_de: str, noi_dung_html: str) -> None: ...


def lay_kenh_tin_nhan() -> KenhTinNhan:
    """Chọn kênh theo `TIN_NHAN_CHE_DO` (`gia` mặc định). Dùng làm dependency FastAPI để test thay bằng kênh ghi nhớ."""
    from app.tich_hop.tin_nhan.gia import KenhTinNhanGia
    from app.tich_hop.tin_nhan.that import KenhTinNhanThat

    return KenhTinNhanThat() if settings.TIN_NHAN_CHE_DO == "that" else KenhTinNhanGia()

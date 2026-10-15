"""Bản thật: chọn nhà cung cấp SMS và SMTP lúc deploy, ghi vào `docs/spec/12-quyet-dinh.md` (spec 08 mục 7)."""

from app.tich_hop.tin_nhan import LoiGuiTinNhan

_CHUA_CAU_HINH = (
    "Chưa cấu hình nhà cung cấp tin nhắn thật (TIN_NHAN_CHE_DO=that). Chọn nhà cung cấp SMS/SMTP rồi cài vào "
    "app/tich_hop/tin_nhan/that.py (xem spec 08 mục 7)."
)


class KenhTinNhanThat:
    async def gui_sms(self, so_dien_thoai: str, noi_dung: str) -> None:
        raise LoiGuiTinNhan(_CHUA_CAU_HINH)

    async def gui_email(self, den: str, tieu_de: str, noi_dung_html: str) -> None:
        raise LoiGuiTinNhan(_CHUA_CAU_HINH)

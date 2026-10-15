"""Bản giả: SMS ghi ra log (hiện cả mã OTP, CHỈ ở chế độ giả); email gửi qua SMTP tới Mailpit (http://localhost:8025)."""

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings
from app.core.dien_thoai import che_sdt

logger = logging.getLogger(__name__)

THOI_GIAN_SMTP_GIAY = 5


class KenhTinNhanGia:
    async def gui_sms(self, so_dien_thoai: str, noi_dung: str) -> None:
        logger.info("SMS giả tới %s: %s", che_sdt(so_dien_thoai), noi_dung)

    async def gui_email(self, den: str, tieu_de: str, noi_dung_html: str) -> None:
        # Ghi log để dev đọc được nội dung (mã OTP) ngay cả khi chưa chạy Mailpit; chỉ ở chế độ giả.
        logger.info("Email giả tới %s, tiêu đề %r: %s", _che_email(den), tieu_de, noi_dung_html)
        thu = EmailMessage()
        thu["From"] = settings.SMTP_NGUOI_GUI
        thu["To"] = den
        thu["Subject"] = tieu_de
        thu.set_content(noi_dung_html, subtype="html", charset="utf-8")
        try:
            await asyncio.to_thread(_gui_smtp, thu)
        except (OSError, smtplib.SMTPException):
            logger.warning(
                "Không gửi được email giả qua SMTP %s:%s (Mailpit chưa chạy?)", settings.SMTP_HOST, settings.SMTP_PORT
            )


def _gui_smtp(thu: EmailMessage) -> None:
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=THOI_GIAN_SMTP_GIAY) as may_chu:
        may_chu.send_message(thu)


def _che_email(email: str) -> str:
    phan_dau, _, mien = email.partition("@")
    return f"{phan_dau[:1]}***@{mien}" if mien else "***"

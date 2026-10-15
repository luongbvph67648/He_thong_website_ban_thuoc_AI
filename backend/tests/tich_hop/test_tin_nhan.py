"""Adapter tin nhắn (spec 08 mục 7): bản giả ghi SMS ra log, email gửi qua SMTP (Mailpit khi dev)."""

import asyncio
import socket
from email import message_from_bytes
from email.header import decode_header, make_header

import pytest
from aiosmtpd.controller import Controller

from app.core.config import settings
from app.tich_hop.tin_nhan import KenhTinNhan, LoiGuiTinNhan, lay_kenh_tin_nhan
from app.tich_hop.tin_nhan.gia import KenhTinNhanGia
from app.tich_hop.tin_nhan.mau.otp import email_otp, sms_da_co_tai_khoan, sms_otp
from app.tich_hop.tin_nhan.that import KenhTinNhanThat


class BoNhanThu:
    """Máy chủ SMTP giả trong tiến trình test: gom thư nhận được."""

    def __init__(self) -> None:
        self.thu: list = []

    async def handle_DATA(self, server, session, envelope):  # noqa: N802 - tên do aiosmtpd quy định
        self.thu.append((envelope.mail_from, envelope.rcpt_tos, message_from_bytes(envelope.original_content)))
        return "250 OK"


def cong_trong() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def smtp_gia(monkeypatch):
    bo_nhan = BoNhanThu()
    cong = cong_trong()
    may_chu = Controller(bo_nhan, hostname="127.0.0.1", port=cong)
    may_chu.start()
    monkeypatch.setattr(settings, "SMTP_HOST", "127.0.0.1")
    monkeypatch.setattr(settings, "SMTP_PORT", cong)
    yield bo_nhan
    may_chu.stop()


def test_mac_dinh_la_ban_gia_va_dung_giao_dien_kenh(monkeypatch):
    monkeypatch.setattr(settings, "TIN_NHAN_CHE_DO", "gia")
    kenh = lay_kenh_tin_nhan()
    assert isinstance(kenh, KenhTinNhanGia)
    assert isinstance(kenh, KenhTinNhan)  # Protocol runtime-checkable


def test_che_do_that_dung_ban_that(monkeypatch):
    monkeypatch.setattr(settings, "TIN_NHAN_CHE_DO", "that")
    assert isinstance(lay_kenh_tin_nhan(), KenhTinNhanThat)


async def test_ban_that_chua_cau_hinh_nha_cung_cap_thi_bao_loi_ro_rang():
    kenh = KenhTinNhanThat()
    with pytest.raises(LoiGuiTinNhan, match="nhà cung cấp"):
        await kenh.gui_sms("0912345678", "x")
    with pytest.raises(LoiGuiTinNhan, match="nhà cung cấp"):
        await kenh.gui_email("a@example.com", "Tiêu đề", "<p>x</p>")


async def test_sms_gia_ghi_log_noi_dung_nhung_che_so_dien_thoai(bat_log):
    await KenhTinNhanGia().gui_sms("0912345678", "Ma OTP: 123456")
    dong = [d for d in bat_log() if "SMS" in d["thong_diep"]]
    assert dong and "Ma OTP: 123456" in dong[0]["thong_diep"]  # chế độ giả được phép hiện mã OTP (spec 08)
    toan_bo = str(bat_log())
    assert "0912345678" not in toan_bo and "091***678" in toan_bo


async def test_email_gia_gui_that_qua_smtp(smtp_gia, bat_log):
    await KenhTinNhanGia().gui_email(
        "khach@example.com", "Mã xác thực của bạn", "<p>Mã: <b>654321</b> — tiếng Việt</p>"
    )
    assert len(smtp_gia.thu) == 1
    gui, nhan, thu = smtp_gia.thu[0]
    assert nhan == ["khach@example.com"] and "no-reply@nhathuoc.local" in gui
    assert str(make_header(decode_header(thu["Subject"]))) == "Mã xác thực của bạn"
    noi_dung = thu.get_payload(decode=True).decode("utf-8")
    assert "654321" in noi_dung and "tiếng Việt" in noi_dung
    assert thu.get_content_type() == "text/html"


async def test_email_gia_van_ghi_log_de_dev_doc_ma_khi_khong_co_mailpit(monkeypatch, bat_log):
    """Không có Mailpit (SMTP từ chối kết nối): không làm hỏng luồng nghiệp vụ, chỉ cảnh báo và vẫn có nội dung trong log."""
    monkeypatch.setattr(settings, "SMTP_HOST", "127.0.0.1")
    monkeypatch.setattr(settings, "SMTP_PORT", cong_trong())  # cổng không có ai nghe
    await asyncio.wait_for(KenhTinNhanGia().gui_email("a@example.com", "Chủ đề", "<p>Mã 111222</p>"), timeout=10)
    nhat_ky = bat_log()
    assert any("111222" in d["thong_diep"] for d in nhat_ky)
    assert any(d["muc"] == "WARNING" for d in nhat_ky)


def test_mau_sms_otp_khong_dau_ngan_gon_va_co_ma_va_thoi_han():
    noi_dung = sms_otp("123456", 5)
    assert "123456" in noi_dung and "5 phut" in noi_dung
    assert noi_dung.isascii() and len(noi_dung) <= 160  # một tin SMS


def test_mau_sms_da_co_tai_khoan_khong_chua_ma():
    noi_dung = sms_da_co_tai_khoan()
    assert noi_dung.isascii() and len(noi_dung) <= 160
    assert not any(c.isdigit() for c in noi_dung)


def test_mau_email_otp_co_ma_thoi_han_va_canh_bao_khong_chia_se():
    tieu_de, html = email_otp("246810", 5)
    assert "246810" in html and "5 phút" in html and "không chia sẻ" in html.lower()
    assert tieu_de and "246810" not in tieu_de  # mã không nằm trong tiêu đề (hiện ở thông báo khóa màn hình)

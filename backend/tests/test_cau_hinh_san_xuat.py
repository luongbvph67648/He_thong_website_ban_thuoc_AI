"""Chốt chặn production: cấu hình giả/thiếu bí mật thì từ chối khởi động (T8.2)."""

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.main import create_app


def _san_xuat(**ghi_de) -> Settings:
    mac_dinh = dict(
        _env_file=None,
        MOI_TRUONG="production",
        JWT_SECRET=SecretStr("k" * 40),
        KHOA_MA_HOA=SecretStr("f" * 44),
        COOKIE_SECURE=True,
        THANH_TOAN_CHE_DO="sandbox",
        VNPAY_HASH_SECRET=SecretStr("a"),
        MOMO_SECRET_KEY=SecretStr("b"),
        VAN_CHUYEN_CHE_DO="ghn",
        GHN_WEBHOOK_TOKEN=SecretStr("t"),
        TIN_NHAN_CHE_DO="that",
        AI_GIA_LAP=False,
    )
    return Settings(**{**mac_dinh, **ghi_de})


def test_dev_khong_bi_chan():
    assert Settings(_env_file=None, MOI_TRUONG="dev").kiem_tra_san_xuat() == []


def test_san_xuat_day_du_thi_dat():
    assert _san_xuat().kiem_tra_san_xuat() == []


@pytest.mark.parametrize(
    "ghi_de",
    [
        {"THANH_TOAN_CHE_DO": "gia"},
        {"VAN_CHUYEN_CHE_DO": "gia"},
        {"TIN_NHAN_CHE_DO": "gia"},
        {"AI_GIA_LAP": True},
        {"COOKIE_SECURE": False},
        {"JWT_SECRET": SecretStr("")},
        {"KHOA_MA_HOA": SecretStr("")},
        {"VNPAY_HASH_SECRET": SecretStr("")},
        {"MOMO_SECRET_KEY": SecretStr("")},
        {"GHN_WEBHOOK_TOKEN": SecretStr("")},
    ],
)
def test_san_xuat_thieu_hoac_gia_thi_bi_chan(ghi_de):
    assert _san_xuat(**ghi_de).kiem_tra_san_xuat()


def test_create_app_tu_choi_khoi_dong(monkeypatch):
    monkeypatch.setattr("app.main.settings", _san_xuat(THANH_TOAN_CHE_DO="gia"))
    with pytest.raises(RuntimeError, match="THANH_TOAN_CHE_DO"):
        create_app()


def test_seed_mau_bi_tu_choi_o_production(monkeypatch):
    from app.seed.__main__ import LoiCauHinh, kiem_tra_duoc_nap_mau

    monkeypatch.setattr("app.seed.__main__.settings", _san_xuat())
    with pytest.raises(LoiCauHinh):
        kiem_tra_duoc_nap_mau("postgresql+asyncpg://u:p@localhost/x", True)

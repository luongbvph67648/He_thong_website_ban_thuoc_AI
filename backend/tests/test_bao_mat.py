"""Mật khẩu: băm Argon2id và kiểm tra độ mạnh (spec 06 mục 2: tối thiểu 8 ký tự, có chữ và số)."""

import pytest

from app.core.bao_mat import bam_mat_khau, kiem_tra_mat_khau, mat_khau_du_manh


def test_bam_ra_argon2id_khong_chua_mat_khau_goc():
    ma_bam = bam_mat_khau("Abc12345")
    assert ma_bam.startswith("$argon2id$")
    assert "Abc12345" not in ma_bam


def test_hai_lan_bam_cung_mat_khau_cho_ket_qua_khac_nhau_vi_co_salt():
    assert bam_mat_khau("Abc12345") != bam_mat_khau("Abc12345")


def test_kiem_tra_dung_va_sai():
    ma_bam = bam_mat_khau("Abc12345")
    assert kiem_tra_mat_khau("Abc12345", ma_bam) is True
    assert kiem_tra_mat_khau("abc12345", ma_bam) is False
    assert kiem_tra_mat_khau("", ma_bam) is False


@pytest.mark.parametrize("ma_bam", ["", "khong-phai-ma-bam", "$argon2id$hong", "x" * 300])
def test_ma_bam_hong_tra_false_khong_nem_loi(ma_bam):
    assert kiem_tra_mat_khau("Abc12345", ma_bam) is False


def test_mat_khau_tieng_viet_co_dau_bam_va_kiem_tra_duoc():
    ma_bam = bam_mat_khau("Mậtkhẩu123")
    assert kiem_tra_mat_khau("Mậtkhẩu123", ma_bam) is True
    assert kiem_tra_mat_khau("Matkhau123", ma_bam) is False


@pytest.mark.parametrize(
    ("mat_khau", "du_manh"),
    [
        ("abc12345", True),
        ("Mậtkhẩu123", True),
        ("a1b2c3d4", True),
        ("doi-mat-khau-nay-123", True),
        ("abc1234", False),  # 7 ký tự
        ("abcdefgh", False),  # không có số
        ("12345678", False),  # không có chữ
        ("        1a", True),  # đủ 8 ký tự, có chữ và số (dấu cách vẫn tính ký tự)
        ("", False),
    ],
)
def test_mat_khau_du_manh(mat_khau, du_manh):
    assert mat_khau_du_manh(mat_khau) is du_manh

"""Chuẩn hóa số điện thoại di động Việt Nam về dạng 0xxxxxxxxx (spec 05 KVL09)."""

import pytest

from app.core.dien_thoai import che_sdt, chuan_hoa_sdt


@pytest.mark.parametrize(
    ("vao", "ra"),
    [
        ("0912345678", "0912345678"),
        ("0912 345 678", "0912345678"),
        ("0912.345.678", "0912345678"),
        ("0912-345-678", "0912345678"),
        ("+84912345678", "0912345678"),
        ("84912345678", "0912345678"),
        ("+84 912 345 678", "0912345678"),
        ("  0386123456  ", "0386123456"),
        ("0561234567", "0561234567"),
        ("0701234567", "0701234567"),
        ("0851234567", "0851234567"),
    ],
)
def test_chuan_hoa_ve_dang_0xxxxxxxxx(vao, ra):
    assert chuan_hoa_sdt(vao) == ra


@pytest.mark.parametrize(
    "vao",
    [
        "",
        "   ",
        "091234567",  # thiếu số
        "09123456789",  # thừa số
        "0212345678",  # đầu số 02 là máy bàn
        "0112345678",
        "0412345678",
        "0612345678",
        "abcdefghij",
        "09123x5678",
        "+849123456",
        "++84912345678",
        "0912345678 ext 1",
        "٠٩١٢٣٤٥٦٧٨",  # chữ số Ả Rập-Ấn Độ, không phải 0-9
        "09١٢٣٤٥٦٧٨",  # lẫn chữ số Unicode sau tiền tố ASCII
        "0912345678\n0987654321",
    ],
)
def test_so_khong_hop_le_bi_tu_choi(vao):
    with pytest.raises(ValueError, match="Số điện thoại"):
        chuan_hoa_sdt(vao)


def test_khong_nhan_kieu_khong_phai_chuoi():
    for gia_tri in (None, 912345678, 0.912):
        with pytest.raises(ValueError, match="Số điện thoại"):
            chuan_hoa_sdt(gia_tri)  # type: ignore[arg-type]


def test_che_sdt_chi_de_lai_dau_va_cuoi_cho_log():
    assert che_sdt("0912345678") == "091***678"
    assert "345" not in che_sdt("0912345678")
    assert che_sdt("") == "***"

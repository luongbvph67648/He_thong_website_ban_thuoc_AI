"""Slug URL từ tên tiếng Việt."""

import pytest

from app.core.slug import tao_slug


@pytest.mark.parametrize(
    ("ten", "slug"),
    [
        ("Thuốc ho Bổ phế", "thuoc-ho-bo-phe"),
        ("Đau đầu 500mg", "dau-dau-500mg"),
        ("ĐƯỜNG HUYẾT", "duong-huyet"),
        ("Paracetamol 500mg (Hộp 10 vỉ x 10 viên)", "paracetamol-500mg-hop-10-vi-x-10-vien"),
        ("  nhiều   khoảng   trắng  ", "nhieu-khoang-trang"),
        ("A/B & C_D", "a-b-c-d"),
        ("--đã-có-gạch--", "da-co-gach"),
    ],
)
def test_tao_slug(ten, slug):
    assert tao_slug(ten) == slug


def test_slug_cat_theo_do_dai_toi_da_khong_de_dau_gach_cuoi():
    ket_qua = tao_slug("một hai ba bốn năm sáu bảy", toi_da=12)
    assert len(ket_qua) <= 12 and not ket_qua.endswith("-")
    assert ket_qua == "mot-hai-ba"


@pytest.mark.parametrize("ten", ["", "   ", "!!!", "---"])
def test_ten_khong_co_chu_hoac_so_bi_tu_choi(ten):
    with pytest.raises(ValueError, match="slug"):
        tao_slug(ten)

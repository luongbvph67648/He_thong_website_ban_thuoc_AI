"""core/tien.py: làm tròn VND, cộng/trừ Decimal, kiểu Tien cho schema."""

from decimal import Decimal

import pytest
from pydantic import BaseModel, ValidationError

from app.core.tien import Tien, cong, lam_tron_vnd, tru


@pytest.mark.parametrize(
    ("vao", "ra"),
    [
        (Decimal("0.5"), Decimal("1")),
        (Decimal("1.5"), Decimal("2")),
        (Decimal("2.5"), Decimal("3")),  # half-up, KHÔNG phải làm tròn chẵn của ngân hàng
        (Decimal("2.4999"), Decimal("2")),
        (Decimal("-2.5"), Decimal("-3")),
        ("1234.49", Decimal("1234")),
        (1000, Decimal("1000")),
        (Decimal("125000.00"), Decimal("125000")),
    ],
)
def test_lam_tron_vnd(vao, ra):
    kq = lam_tron_vnd(vao)
    assert kq == ra
    assert kq.as_tuple().exponent == 0  # không còn phần thập phân


@pytest.mark.parametrize("sai", [1.5, 0.1, 3.0, True, None, [1]])
def test_tu_choi_float_bool_va_kieu_la(sai):
    with pytest.raises(TypeError):
        lam_tron_vnd(sai)


@pytest.mark.parametrize("sai", ["abc", "", "NaN", "Infinity", Decimal("NaN")])
def test_tu_choi_gia_tri_khong_phai_so_huu_han(sai):
    with pytest.raises(ValueError):
        lam_tron_vnd(sai)


def test_cong_lam_tron_mot_lan_o_cuoi():
    assert cong(1, 2, 3) == Decimal("6")
    assert cong() == Decimal("0")
    # 100.4 + 200 + 50.4 = 350.8, làm tròn một lần ở cuối thành 351 (không làm tròn từng số hạng)
    assert cong(Decimal("100.4"), 200, "50.4") == Decimal("351")


def test_tru():
    assert tru(1000, "250") == Decimal("750")
    assert tru(100, 300) == Decimal("-200")  # số dư âm hợp lệ (ví dụ chênh lệch hoàn tiền)


def test_cong_tru_tu_choi_float():
    with pytest.raises(TypeError):
        cong(0.1, 0.2)
    with pytest.raises(TypeError):
        tru(10, 0.5)


class _Gia(BaseModel):
    gia: Tien


def test_tien_xuat_json_dang_chuoi_hai_so_le():
    assert _Gia(gia=Decimal("125000")).model_dump_json() == '{"gia":"125000.00"}'
    assert _Gia(gia=125000).model_dump(mode="json") == {"gia": "125000.00"}


def test_tien_python_mode_giu_decimal():
    assert _Gia(gia=5).model_dump()["gia"] == Decimal("5")


@pytest.mark.parametrize("vao", ["125000", 125000, 125000.0, Decimal("125000.00"), "125000.00"])
def test_tien_nhan_so_dong_nguyen(vao):
    assert _Gia(gia=vao).gia == Decimal("125000")


@pytest.mark.parametrize("sai", [Decimal("1000.5"), 1000.5, "1000.5", "abc", True, None, "NaN"])
def test_tien_tu_choi_so_le_va_gia_tri_la(sai):
    with pytest.raises(ValidationError):
        _Gia(gia=sai)


def test_tien_tu_choi_so_le_khi_doc_tu_json():
    with pytest.raises(ValidationError):
        _Gia.model_validate_json('{"gia": 125000.5}')
    assert _Gia.model_validate_json('{"gia": 125000}').gia == Decimal("125000")

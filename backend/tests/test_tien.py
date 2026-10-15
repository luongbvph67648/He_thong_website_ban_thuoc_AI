"""core/tien.py: làm tròn VND, cộng/trừ Decimal, kiểu Tien cho schema."""

from decimal import Decimal

import pytest
from pydantic import BaseModel, ValidationError

from app.core.tien import Tien, TienCoDau, cong, lam_tron_vnd, tru


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


def test_khong_bao_gio_tra_ve_am_khong():
    """-0 serialize ra "-0.00", dễ làm hiển thị sai (Decimal("-0.4") làm tròn về 0 vẫn mang dấu âm)."""
    for kq in (lam_tron_vnd(Decimal("-0.4")), lam_tron_vnd("-0"), tru(100, Decimal("100.4"))):
        assert kq == 0
        assert not kq.is_signed()


@pytest.mark.parametrize("qua_lon", [10**30, "1e30", "99999999999999999999999999999"])
def test_so_qua_lon_la_value_error_khong_phai_invalid_operation(qua_lon):
    with pytest.raises(ValueError):
        lam_tron_vnd(qua_lon)


@pytest.mark.parametrize("sai", [10**12, "1000000000000", 10**30, "1e30", "99999999999999999999999999999"])
def test_tien_tu_choi_so_vuot_gioi_han_bang_loi_validate(sai):
    """Phải là ValidationError (400) chứ không phải lỗi hệ thống (500) hay lỗi tràn NUMERIC ở DB."""
    with pytest.raises(ValidationError):
        _Gia(gia=sai)


def test_tien_nhan_so_sat_gioi_han():
    assert _Gia(gia=10**12 - 1).gia == Decimal(10**12 - 1)


@pytest.mark.parametrize("sai", [-1, "-5000", Decimal("-1")])
def test_tien_mac_dinh_khong_nhan_so_am(sai):
    with pytest.raises(ValidationError):
        _Gia(gia=sai)


def test_tien_am_khong_duoc_chuan_hoa_thanh_khong():
    m = _Gia(gia="-0")
    assert not m.gia.is_signed()
    assert m.model_dump(mode="json") == {"gia": "0.00"}


class _GiaCoDau(BaseModel):
    gia: TienCoDau


def test_tien_co_dau_nhan_so_am_va_van_gioi_han_do_lon():
    assert _GiaCoDau(gia=-5000).model_dump(mode="json") == {"gia": "-5000.00"}
    with pytest.raises(ValidationError):
        _GiaCoDau(gia=-(10**12))

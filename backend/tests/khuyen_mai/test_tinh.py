"""Thuật toán giảm giá (spec 04 mục 4): làm tròn, trần giảm, phân bổ vào dòng, thuốc kê đơn bị loại."""

from decimal import Decimal

import pytest

from app.models.enums import LoaiGiamGia
from app.modules.khuyen_mai.tinh import DongTinh, tinh_giam

D = Decimal


def dong(*gia, hop_le=True):
    return [DongTinh(i, D(g), hop_le) for i, g in enumerate(gia)]


def test_phan_tram_lam_tron_half_up_va_tran_giam():
    kq = tinh_giam(dong(333, 100), LoaiGiamGia.phan_tram, D(10), None)  # 43.3 -> 43
    assert kq.giam == 43 and kq.co_so_giam == 433
    assert tinh_giam(dong(1005), LoaiGiamGia.phan_tram, D(10), None).giam == 101  # 100.5 -> 101 (half-up)
    assert tinh_giam(dong(1_000_000), LoaiGiamGia.phan_tram, D(20), D(50_000)).giam == 50_000


def test_so_tien_khong_vuot_co_so():
    assert tinh_giam(dong(30_000), LoaiGiamGia.so_tien, D(50_000), None).giam == 30_000
    assert tinh_giam(dong(80_000), LoaiGiamGia.so_tien, D(50_000), None).giam == 50_000


def test_phan_bo_tong_bang_giam_phan_du_don_vao_dong_hop_le_cuoi():
    d = dong(100, 100, 100)
    kq = tinh_giam(d, LoaiGiamGia.so_tien, D(100), None)  # chia 3: 33 + 33 + 34
    assert [kq.phan_bo[i] for i in range(3)] == [33, 33, 34] and sum(kq.phan_bo.values()) == kq.giam == 100


def test_dong_khong_hop_le_khong_duoc_giam_va_khong_nam_trong_co_so():
    d = [DongTinh(0, D(500), True), DongTinh(1, D(9_000), False), DongTinh(2, D(500), True)]
    kq = tinh_giam(d, LoaiGiamGia.phan_tram, D(50), None)
    assert kq.co_so_giam == 1000 and kq.giam == 500
    assert kq.phan_bo == {0: 250, 1: 0, 2: 250}
    # dòng không hợp lệ ở cuối: phần dư vẫn dồn vào dòng HỢP LỆ cuối
    d2 = [DongTinh(0, D(100), True), DongTinh(1, D(100), True), DongTinh(2, D(100), True), DongTinh(3, D(777), False)]
    kq2 = tinh_giam(d2, LoaiGiamGia.so_tien, D(100), None)
    assert kq2.phan_bo[3] == 0 and sum(kq2.phan_bo.values()) == 100 and kq2.phan_bo[2] == 34


def test_khong_co_dong_hop_le_thi_khong_giam():
    kq = tinh_giam(dong(1000, hop_le=False), LoaiGiamGia.phan_tram, D(50), None)
    assert kq.giam == 0 and kq.co_so_giam == 0 and kq.phan_bo == {0: 0}


@pytest.mark.parametrize("gia", [[1], [7, 13, 29], [999_999, 1], [10, 10, 10, 10, 10, 10, 10]])
@pytest.mark.parametrize("phan_tram", [D("0.5"), D(7), D("33.33"), D(100)])
def test_tong_phan_bo_luon_dung_bang_giam(gia, phan_tram):
    kq = tinh_giam(dong(*gia), LoaiGiamGia.phan_tram, phan_tram, None)
    assert sum(kq.phan_bo.values()) == kq.giam <= kq.co_so_giam
    assert all(v >= 0 and v == v.to_integral_value() for v in kq.phan_bo.values())

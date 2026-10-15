"""Bộ giới hạn tần suất cửa sổ trượt trong bộ nhớ (spec 01 mục 4: khóa theo IP, phiên, SĐT)."""

import pytest

from app.core.gioi_han import GioiHanCuaSoTruot


class DongHo:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


@pytest.fixture
def dong_ho():
    return DongHo()


def test_cho_phep_toi_da_n_luot_trong_cua_so_roi_chan(dong_ho):
    gh = GioiHanCuaSoTruot(dong_ho)
    assert [gh.thu("ip1", 3, 3600) for _ in range(3)] == [None, None, None]
    cho = gh.thu("ip1", 3, 3600)
    assert cho is not None and cho == pytest.approx(3600)


def test_thoi_gian_cho_la_den_khi_luot_cu_nhat_het_han(dong_ho):
    gh = GioiHanCuaSoTruot(dong_ho)
    gh.thu("k", 2, 100)  # t=1000
    dong_ho.t += 30
    gh.thu("k", 2, 100)  # t=1030
    dong_ho.t += 10  # t=1040: lượt đầu còn 60 giây nữa mới hết
    assert gh.thu("k", 2, 100) == pytest.approx(60)


def test_het_cua_so_thi_duoc_phep_lai(dong_ho):
    gh = GioiHanCuaSoTruot(dong_ho)
    gh.thu("k", 1, 60)
    assert gh.thu("k", 1, 60) is not None
    dong_ho.t += 60.001
    assert gh.thu("k", 1, 60) is None


def test_luot_bi_chan_khong_duoc_tinh_vao_cua_so(dong_ho):
    """Bị chặn rồi thử lại liên tục không làm kéo dài thời gian chặn."""
    gh = GioiHanCuaSoTruot(dong_ho)
    gh.thu("k", 1, 100)  # t=1000
    for _ in range(50):
        dong_ho.t += 1
        assert gh.thu("k", 1, 100) is not None
    dong_ho.t = 1100.5  # đủ 100 giây kể từ lượt được phép duy nhất
    assert gh.thu("k", 1, 100) is None


def test_moi_khoa_dem_rieng(dong_ho):
    gh = GioiHanCuaSoTruot(dong_ho)
    assert gh.thu("a", 1, 60) is None and gh.thu("b", 1, 60) is None
    assert gh.thu("a", 1, 60) is not None


def test_gioi_han_thay_doi_giua_chung_ap_dung_ngay(dong_ho):
    """Giới hạn đọc từ cau_hinh có thể đổi lúc chạy: lượt đã ghi vẫn được tính theo giới hạn mới."""
    gh = GioiHanCuaSoTruot(dong_ho)
    for _ in range(3):
        gh.thu("k", 10, 60)
    assert gh.thu("k", 3, 60) is not None  # hạ xuống 3: đã đủ
    assert gh.thu("k", 5, 60) is None  # nâng lên 5: còn chỗ


def test_bo_nho_bi_chan_tren_khi_co_rat_nhieu_khoa(dong_ho):
    gh = GioiHanCuaSoTruot(dong_ho, toi_da_khoa=100)
    for i in range(1000):
        gh.thu(f"ip{i}", 5, 3600)
    assert gh.so_khoa() <= 100


def test_khoa_het_han_duoc_don_dep(dong_ho):
    gh = GioiHanCuaSoTruot(dong_ho, toi_da_khoa=10)
    for i in range(10):
        gh.thu(f"cu{i}", 5, 60)
    dong_ho.t += 120
    gh.thu("moi", 5, 60)
    assert gh.so_khoa() == 1


def test_xoa_dat_lai_toan_bo(dong_ho):
    gh = GioiHanCuaSoTruot(dong_ho)
    gh.thu("k", 1, 60)
    gh.xoa()
    assert gh.thu("k", 1, 60) is None


@pytest.mark.parametrize(("toi_da", "cua_so"), [(0, 60), (-1, 60), (1, 0), (1, -5)])
def test_tham_so_khong_hop_le_bi_tu_choi(dong_ho, toi_da, cua_so):
    with pytest.raises(ValueError):
        GioiHanCuaSoTruot(dong_ho).thu("k", toi_da, cua_so)

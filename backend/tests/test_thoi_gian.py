"""core/thoi_gian.py: giờ UTC và ngày hiện tại theo giờ Việt Nam (UTC+7)."""

from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from app.core.thoi_gian import bay_gio_utc, hom_nay_vn


def test_bay_gio_utc_co_mui_gio_utc():
    t = bay_gio_utc()
    assert t.tzinfo is not None
    assert t.utcoffset() == timedelta(0)


@pytest.mark.parametrize(
    ("utc", "ngay_vn"),
    [
        (datetime(2026, 10, 15, 0, 0, tzinfo=UTC), date(2026, 10, 15)),  # 07:00 VN
        (datetime(2026, 10, 15, 16, 59, 59, tzinfo=UTC), date(2026, 10, 15)),  # 23:59:59 VN
        (datetime(2026, 10, 15, 17, 0, 0, tzinfo=UTC), date(2026, 10, 16)),  # 00:00 VN hôm sau
        (datetime(2026, 12, 31, 17, 0, tzinfo=UTC), date(2027, 1, 1)),  # qua năm
    ],
)
def test_hom_nay_vn_theo_gio_viet_nam(utc, ngay_vn):
    assert hom_nay_vn(utc) == ngay_vn


def test_hom_nay_vn_nhan_datetime_mui_gio_khac():
    # 00:30 ngày 16 giờ VN -> vẫn là 16
    assert hom_nay_vn(datetime(2026, 10, 16, 0, 30, tzinfo=timezone(timedelta(hours=7)))) == date(2026, 10, 16)
    # 23:00 ngày 15 giờ UTC-5 = 04:00 UTC ngày 16 = 11:00 VN ngày 16
    assert hom_nay_vn(datetime(2026, 10, 15, 23, 0, tzinfo=timezone(timedelta(hours=-5)))) == date(2026, 10, 16)


def test_hom_nay_vn_tu_choi_datetime_khong_co_mui_gio():
    with pytest.raises(ValueError):
        hom_nay_vn(datetime(2026, 10, 15, 12, 0))


def test_hom_nay_vn_mac_dinh_dung_gio_hien_tai():
    truoc = hom_nay_vn(bay_gio_utc())
    kq = hom_nay_vn()
    sau = hom_nay_vn(bay_gio_utc())
    assert truoc <= kq <= sau

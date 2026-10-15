"""Mã chứng từ nội bộ sinh từ sequence (spec 04 mục 7)."""

import re

import pytest
from sqlalchemy import text

from app.core.ma_chung_tu import ma_lenh_thu_hoi, ma_nhan_vien, ma_phieu
from app.core.thoi_gian import hom_nay_vn

YY = f"{hom_nay_vn().year % 100:02d}"


async def test_ma_nhan_vien_dinh_dang_va_tang_dan(db):
    a = await ma_nhan_vien(db)
    b = await ma_nhan_vien(db)
    assert re.fullmatch(r"NV\d{4}", a)
    assert int(b[2:]) == int(a[2:]) + 1


@pytest.mark.parametrize(
    ("loai", "tien_to"),
    [
        ("phieu_nhap", "PN"),
        ("phieu_kiem_ke", "KK"),
        ("phieu_dieu_chinh", "DC"),
        ("phieu_huy", "PH"),
        ("phieu_xuat_tra", "XT"),
    ],
)
async def test_ma_phieu_dinh_dang_theo_loai(db, loai, tien_to):
    a = await ma_phieu(db, loai)
    b = await ma_phieu(db, loai)
    assert re.fullmatch(rf"{tien_to}{YY}\d{{6}}", a), a
    assert int(b[4:]) == int(a[4:]) + 1


async def test_ma_phieu_moi_loai_co_sequence_rieng(db):
    nhap = int((await ma_phieu(db, "phieu_nhap"))[4:])
    huy_1 = int((await ma_phieu(db, "phieu_huy"))[4:])
    huy_2 = int((await ma_phieu(db, "phieu_huy"))[4:])
    nhap_2 = int((await ma_phieu(db, "phieu_nhap"))[4:])
    assert huy_2 == huy_1 + 1
    assert nhap_2 == nhap + 1  # lấy mã phiếu hủy không làm nhảy số của phiếu nhập


async def test_ma_phieu_loai_la_bi_tu_choi(db):
    with pytest.raises(ValueError, match="phieu_la"):
        await ma_phieu(db, "phieu_la")


async def test_ma_lenh_thu_hoi(db):
    a = await ma_lenh_thu_hoi(db)
    assert re.fullmatch(rf"TH{YY}\d{{4}}", a), a


async def test_ma_dai_hon_so_chu_so_quy_dinh_van_hop_le(db):
    """Số lớn hơn độ rộng định dạng thì mã dài ra thay vì cắt/lỗi (vẫn duy nhất)."""
    truoc = (await db.execute(text("SELECT last_value, is_called FROM seq_nhan_vien"))).one()
    try:
        await db.execute(text("SELECT setval('seq_nhan_vien', 9999)"))
        assert await ma_nhan_vien(db) == "NV10000"
    finally:  # sequence không rollback theo transaction, trả lại để không ảnh hưởng test khác
        await db.execute(text("SELECT setval('seq_nhan_vien', :v, :c)"), {"v": truoc[0], "c": truoc[1]})

"""core/nhat_ky.py: ghi nhật ký hệ thống và che dữ liệu nhạy cảm (CLAUDE.md quy tắc 7)."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.nhat_ky import DA_CHE, che_du_lieu_nhay_cam, ghi_nhat_ky
from app.models.he_thong import NhatKyHeThong
from tests.factories import tao_nhan_vien


async def test_ghi_nhat_ky_luu_day_du_cac_truong(db):
    nv = await tao_nhan_vien(db)
    dong = await ghi_nhat_ky(
        db,
        nhan_vien_id=nv.id,
        hanh_dong="sua",
        bang="san_pham",
        ban_ghi_id=42,
        gia_tri_cu={"ten": "A"},
        gia_tri_moi={"ten": "B"},
        ip="10.0.0.1",
    )
    luu = (await db.execute(select(NhatKyHeThong).where(NhatKyHeThong.id == dong.id))).scalar_one()
    assert (luu.nhan_vien_id, luu.hanh_dong, luu.bang, luu.ban_ghi_id, luu.ip) == (
        nv.id,
        "sua",
        "san_pham",
        "42",
        "10.0.0.1",
    )
    assert luu.gia_tri_cu == {"ten": "A"} and luu.gia_tri_moi == {"ten": "B"}
    assert luu.created_at is not None


async def test_ban_ghi_id_la_chuoi_va_cho_phep_thieu(db):
    dong = await ghi_nhat_ky(db, nhan_vien_id=None, hanh_dong="dang_nhap_that_bai", bang="nhan_vien")
    assert dong.ban_ghi_id is None and dong.nhan_vien_id is None
    assert dong.gia_tri_cu is None and dong.gia_tri_moi is None


async def test_gia_tri_khong_phai_json_van_ghi_duoc(db):
    dong = await ghi_nhat_ky(
        db,
        nhan_vien_id=None,
        hanh_dong="sua",
        bang="lo_thuoc",
        gia_tri_moi={"gia": Decimal("12500"), "han": date(2027, 1, 31)},
    )
    assert dong.gia_tri_moi == {"gia": "12500", "han": "2027-01-31"}  # Decimal ra chuỗi, không qua float


@pytest.mark.parametrize(
    "khoa",
    [
        "mat_khau",
        "mat_khau_moi",
        "MAT_KHAU_CU",
        "password",
        "otp",
        "ma_otp",
        "access_token",
        "refresh_token_hash",
        "ma_hash",
        "client_secret",
        "benh_nen",
        "di_ung",
        "ho_so_suc_khoe",
        "KHOA_MA_HOA",
    ],
)
def test_khoa_nhay_cam_bi_che_gia_tri(khoa):
    assert che_du_lieu_nhay_cam({khoa: "gia-tri-bi-mat", "ho_ten": "A"}) == {khoa: DA_CHE, "ho_ten": "A"}


def test_che_ca_khi_long_nhau_trong_dict_va_list():
    vao = {"thay_doi": [{"mat_khau_moi": "x", "ten": "A"}, {"sau": {"otp": "123456"}}], "ten": "B"}
    ra = che_du_lieu_nhay_cam(vao)
    assert ra == {"thay_doi": [{"mat_khau_moi": DA_CHE, "ten": "A"}, {"sau": {"otp": DA_CHE}}], "ten": "B"}
    assert vao["thay_doi"][0]["mat_khau_moi"] == "x"  # không sửa dữ liệu của người gọi


def test_khong_che_khoa_vo_hai_chua_doan_tuong_tu():
    # "hoten", "ten_san_pham", "lien_ket" không chứa đoạn nhạy cảm nào.
    du_lieu = {"hoten": "A", "ten_san_pham": "B", "lien_ket": "/don-hang/1", "so_luong": 3}
    assert che_du_lieu_nhay_cam(du_lieu) == du_lieu


async def test_ghi_nhat_ky_che_truoc_khi_luu(db):
    dong = await ghi_nhat_ky(
        db,
        nhan_vien_id=None,
        hanh_dong="doi_mat_khau",
        bang="nhan_vien",
        gia_tri_cu={"mat_khau_hash": "$argon2id$...", "ho_ten": "A"},
        gia_tri_moi={"mat_khau_hash": "$argon2id$moi", "ho_ten": "A"},
    )
    luu = (await db.execute(select(NhatKyHeThong).where(NhatKyHeThong.id == dong.id))).scalar_one()
    assert luu.gia_tri_cu == {"mat_khau_hash": DA_CHE, "ho_ten": "A"}
    assert "argon2" not in str(luu.gia_tri_cu) + str(luu.gia_tri_moi)

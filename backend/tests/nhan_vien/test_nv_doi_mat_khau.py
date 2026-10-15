"""NV01: đổi mật khẩu (POST /api/v1/noi-bo/auth/doi-mat-khau) và bắt đổi mật khẩu lần đầu."""

import json

import pytest

from app.core.nhat_ky import DA_CHE
from tests.factories import MAT_KHAU_TEST, tao_khach, tao_nhan_vien
from tests.nhan_vien.dung_chung import (
    EMAIL,
    URL_DOI_MAT_KHAU,
    URL_TOI,
    bearer,
    cookie_refresh,
    dang_nhap,
    doi_mat_khau,
    lam_moi,
    nhat_ky,
    so_phien_con_hieu_luc,
)
from tests.tai_khoan.dung_chung import cookie_refresh as cookie_khach

MAT_KHAU_MOI = "Mat-khau-moi-2"


async def dang_nhap_lay_token(client, email=EMAIL):
    phan_hoi = await dang_nhap(client, email)
    assert phan_hoi.status_code == 200
    return phan_hoi.json()["access_token"], cookie_refresh(phan_hoi)


async def test_luong_day_du_lan_dau_dang_nhap_bat_doi_mat_khau_roi_vao_duoc(client, db):
    nv = await tao_nhan_vien(db, "ADMIN", email=EMAIL, phai_doi_mat_khau=True)
    token, refresh_cu = await dang_nhap_lay_token(client)
    may_khac = cookie_refresh(await dang_nhap(client))
    assert (await client.get("/api/v1/noi-bo/thong-bao", headers=bearer(token))).status_code == 403

    phan_hoi = await doi_mat_khau(client, token, MAT_KHAU_TEST, MAT_KHAU_MOI)
    assert phan_hoi.status_code == 200
    than = phan_hoi.json()
    assert than["nhan_vien"]["phai_doi_mat_khau"] is False and than["nhan_vien"]["vai_tro"]["ma"] == "ADMIN"
    refresh_moi = cookie_refresh(phan_hoi)
    assert refresh_moi and refresh_moi not in (refresh_cu, may_khac) and refresh_moi not in phan_hoi.text

    await db.refresh(nv)
    assert nv.phai_doi_mat_khau is False and MAT_KHAU_MOI not in nv.mat_khau_hash
    # Mọi phiên cũ (cả máy khác) bị thu hồi; chỉ còn phiên mới của thiết bị vừa đổi.
    assert await so_phien_con_hieu_luc(db, nv.id) == 1
    assert (await lam_moi(client, refresh_cu)).status_code == 401
    # Token mới dùng được ngay mọi route, mật khẩu mới đăng nhập được, mật khẩu cũ thì không.
    assert (await client.get("/api/v1/noi-bo/thong-bao", headers=bearer(than["access_token"]))).status_code == 200
    assert (await dang_nhap(client, EMAIL, MAT_KHAU_MOI)).status_code == 200
    assert (await dang_nhap(client, EMAIL, MAT_KHAU_TEST)).status_code == 401


async def test_doi_mat_khau_khong_dong_den_phien_cua_nguoi_khac(client, db):
    nv = await tao_nhan_vien(db, email=EMAIL)
    nguoi_khac = await tao_nhan_vien(db, email="nguoi.khac@example.com")
    khach = await tao_khach(db, so_dien_thoai="0912345678")
    token, _ = await dang_nhap_lay_token(client)
    phien_nguoi_khac = cookie_refresh(await dang_nhap(client, nguoi_khac.email))
    phien_khach = cookie_khach(
        await client.post(
            "/api/v1/auth/dang-nhap", json={"ten_dang_nhap": khach.so_dien_thoai, "mat_khau": MAT_KHAU_TEST}
        )
    )

    assert (await doi_mat_khau(client, token, MAT_KHAU_TEST, MAT_KHAU_MOI)).status_code == 200
    assert await so_phien_con_hieu_luc(db, nguoi_khac.id) == 1
    assert (await lam_moi(client, phien_nguoi_khac)).status_code == 200
    assert nv.id != nguoi_khac.id and phien_khach


async def test_mat_khau_cu_sai_tra_422_va_duoc_dem(client, db):
    nv = await tao_nhan_vien(db, email=EMAIL)
    token, _ = await dang_nhap_lay_token(client)
    phan_hoi = await doi_mat_khau(client, token, "Sai-mat-khau-1", MAT_KHAU_MOI)
    assert phan_hoi.status_code == 422 and phan_hoi.json()["ma_loi"] == "MAT_KHAU_CU_SAI"
    assert cookie_refresh(phan_hoi) is None
    await db.refresh(nv)
    assert nv.so_lan_dang_nhap_sai == 1  # lưu dù trả lỗi
    assert (await dang_nhap(client, EMAIL, MAT_KHAU_TEST)).status_code == 200  # mật khẩu chưa đổi
    assert await nhat_ky(db, nv.id, "doi_mat_khau") == []


async def test_doan_mat_khau_cu_bang_phien_bi_danh_cap_bi_khoa_tam_va_mat_het_phien(client, db):
    """Kẻ cầm access token đánh cắp không thể dò mật khẩu hiện tại: 5 lần sai khóa tài khoản và thu hồi mọi phiên."""
    nv = await tao_nhan_vien(db, email=EMAIL)
    token, refresh = await dang_nhap_lay_token(client)
    for _ in range(4):
        assert (await doi_mat_khau(client, token, "Sai-mat-khau-1", MAT_KHAU_MOI)).status_code == 422
    phan_hoi = await doi_mat_khau(client, token, "Sai-mat-khau-1", MAT_KHAU_MOI)  # lần 5
    assert phan_hoi.status_code == 403 and phan_hoi.json()["ma_loi"] == "TAI_KHOAN_BI_KHOA"
    assert phan_hoi.json()["chi_tiet"] == {"thu_lai_sau_giay": 15 * 60}
    assert await so_phien_con_hieu_luc(db, nv.id) == 0
    assert (await lam_moi(client, refresh)).status_code == 401
    assert len(await nhat_ky(db, nv.id, "khoa_tam_doi_mat_khau")) == 1

    # Đang khóa: mật khẩu cũ ĐÚNG cũng không đổi được.
    dung = await doi_mat_khau(client, token, MAT_KHAU_TEST, MAT_KHAU_MOI)
    assert dung.status_code == 403
    assert len(await nhat_ky(db, nv.id, "khoa_tam_doi_mat_khau")) == 1  # không ghi lại mỗi lần thử


@pytest.mark.parametrize(
    "mat_khau_moi",
    ["ngan1", "chi-co-chu-cai", "12345678901", "", "a" * 129 + "1"],
    ids=["ngan", "thieu_so", "thieu_chu", "rong", "dai"],
)
async def test_mat_khau_moi_yeu_bi_tu_choi_va_khong_bi_dem_la_lan_sai(client, db, mat_khau_moi):
    nv = await tao_nhan_vien(db, email=EMAIL)
    token, _ = await dang_nhap_lay_token(client)
    phan_hoi = await doi_mat_khau(client, token, "Sai-mat-khau-1", mat_khau_moi)  # cả mật khẩu cũ lẫn mới đều sai
    assert phan_hoi.status_code == 400 and phan_hoi.json()["chi_tiet"][0]["truong"] == "mat_khau_moi"
    await db.refresh(nv)
    assert nv.so_lan_dang_nhap_sai == 0  # kiểm tra định dạng đứng trước, không bị đếm


async def test_mat_khau_moi_phai_khac_mat_khau_cu(client, db):
    await tao_nhan_vien(db, email=EMAIL)
    token, refresh = await dang_nhap_lay_token(client)
    phan_hoi = await doi_mat_khau(client, token, MAT_KHAU_TEST, MAT_KHAU_TEST)
    assert phan_hoi.status_code == 400 and phan_hoi.json()["chi_tiet"][0]["truong"] == "mat_khau_moi"
    assert (await lam_moi(client, refresh)).status_code == 200  # không có gì thay đổi


async def test_thieu_truong_tra_400(client, db):
    await tao_nhan_vien(db, email=EMAIL)
    token, _ = await dang_nhap_lay_token(client)
    phan_hoi = await client.post(URL_DOI_MAT_KHAU, json={"mat_khau_moi": MAT_KHAU_MOI}, headers=bearer(token))
    assert phan_hoi.status_code == 400 and phan_hoi.json()["chi_tiet"][0]["truong"] == "mat_khau_cu"


async def test_phai_dang_nhap_noi_bo(client, db):
    khach = await tao_khach(db)
    from app.core.bao_mat import tao_access_token

    thieu = await client.post(URL_DOI_MAT_KHAU, json={"mat_khau_cu": "x", "mat_khau_moi": MAT_KHAU_MOI})
    assert thieu.status_code == 401
    token_khach = tao_access_token(khach.id, "khach")
    assert (await doi_mat_khau(client, token_khach, MAT_KHAU_TEST, MAT_KHAU_MOI)).status_code == 401


async def test_tai_khoan_bi_khoa_khong_doi_duoc_mat_khau(client, db):
    from app.models.enums import TrangThaiTaiKhoan

    nv = await tao_nhan_vien(db, email=EMAIL)
    token, _ = await dang_nhap_lay_token(client)
    nv.trang_thai = TrangThaiTaiKhoan.bi_khoa
    await db.flush()
    phan_hoi = await doi_mat_khau(client, token, MAT_KHAU_TEST, MAT_KHAU_MOI)
    assert phan_hoi.status_code == 403 and phan_hoi.json()["ma_loi"] == "TAI_KHOAN_BI_KHOA"


async def test_nhat_ky_doi_mat_khau_khong_chua_mat_khau_hay_hash(client, db):
    nv = await tao_nhan_vien(db, email=EMAIL)
    token, _ = await dang_nhap_lay_token(client)
    await doi_mat_khau(client, token, MAT_KHAU_TEST, MAT_KHAU_MOI)
    (dong,) = await nhat_ky(db, nv.id, "doi_mat_khau")
    noi_dung = json.dumps([dong.gia_tri_cu, dong.gia_tri_moi, dong.bang, dong.ban_ghi_id])
    assert MAT_KHAU_MOI not in noi_dung and MAT_KHAU_TEST not in noi_dung and "argon2" not in noi_dung
    assert dong.gia_tri_cu is None and dong.gia_tri_moi is None and DA_CHE not in noi_dung


async def test_sau_khi_doi_mat_khau_cho_phep_doc_ho_so_va_cac_route_khac(client, db):
    await tao_nhan_vien(db, email=EMAIL, phai_doi_mat_khau=True)
    token, _ = await dang_nhap_lay_token(client)
    phan_hoi = await doi_mat_khau(client, token, MAT_KHAU_TEST, MAT_KHAU_MOI)
    token_moi = phan_hoi.json()["access_token"]
    toi = await client.get(URL_TOI, headers=bearer(token_moi))
    assert toi.status_code == 200 and toi.json()["phai_doi_mat_khau"] is False

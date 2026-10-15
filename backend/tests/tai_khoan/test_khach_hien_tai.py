"""Dependency `khach_hien_tai` / `khach_tuy_chon` và `GET /api/v1/toi` (CLAUDE.md quy tắc 3)."""

import re
from datetime import timedelta

import jwt
import pytest
from fastapi import Depends

from app.core.bao_mat import tao_access_token
from app.core.config import settings
from app.core.phan_quyen import khach_tuy_chon
from app.core.thoi_gian import bay_gio_utc
from app.models.enums import TrangThaiTaiKhoan
from app.models.khach_hang import KhachHang
from tests.factories import tao_khach, tao_nhan_vien

URL = "/api/v1/toi"


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def goi(client, token=None, tieu_de=None):
    return await client.get(URL, headers=tieu_de if tieu_de is not None else bearer(token))


def la_loi(phan_hoi, status, ma_loi):
    return phan_hoi.status_code == status and phan_hoi.json()["ma_loi"] == ma_loi


async def test_ho_so_cua_toi_tra_dung_khach_trong_token_va_khong_lo_truong_nhay_cam(client, db):
    khach = await tao_khach(db)
    nguoi_khac = await tao_khach(db)
    phan_hoi = await goi(client, tao_access_token(khach.id, "khach"))
    assert phan_hoi.status_code == 200
    assert phan_hoi.json() == {
        "id": khach.id,
        "ho_ten": khach.ho_ten,
        "so_dien_thoai": khach.so_dien_thoai,
        "email": khach.email,
    }
    assert nguoi_khac.so_dien_thoai not in phan_hoi.text
    assert "mat_khau" not in phan_hoi.text and "hash" not in phan_hoi.text


async def test_id_khach_chi_den_tu_token_khong_nhan_tu_client(client, db):
    khach = await tao_khach(db)
    nguoi_khac = await tao_khach(db)
    phan_hoi = await client.get(
        URL, headers=bearer(tao_access_token(khach.id, "khach")), params={"khach_hang_id": nguoi_khac.id}
    )
    assert phan_hoi.json()["id"] == khach.id


@pytest.mark.parametrize(
    "tieu_de", [{}, {"Authorization": ""}, {"Authorization": "Bearer"}, {"Authorization": "Bearer "}]
)
async def test_khong_co_token_tra_401(client, tieu_de):
    assert la_loi(await goi(client, tieu_de=tieu_de), 401, "CHUA_DANG_NHAP")


@pytest.mark.parametrize("gia_tri", ["Bearer abc.def.ghi", "Basic dXNlcjpwYXNz", "abc", "Token xyz"])
async def test_token_vo_nghia_hoac_sai_kieu_tra_401(client, gia_tri):
    assert la_loi(await goi(client, tieu_de={"Authorization": gia_tri}), 401, "CHUA_DANG_NHAP")


async def test_token_het_han_tra_token_het_han_de_client_lam_moi(client, db):
    khach = await tao_khach(db)
    assert la_loi(await goi(client, tao_access_token(khach.id, "khach", het_han_phut=-1)), 401, "TOKEN_HET_HAN")


async def test_token_noi_bo_khong_dung_duoc_cho_api_khach(client, db):
    nhan_vien = await tao_nhan_vien(db)
    assert la_loi(await goi(client, tao_access_token(nhan_vien.id, "noi_bo")), 401, "CHUA_DANG_NHAP")


async def test_token_khong_phai_do_he_thong_ky_bi_tu_choi(client, db):
    khach = await tao_khach(db)
    claim = {"sub": str(khach.id), "aud": "khach", "exp": bay_gio_utc() + timedelta(minutes=5)}
    gia_khoa = jwt.encode(claim, "khoa-cua-ke-tan-cong-" + "x" * 40, algorithm="HS256")
    khong_ky = jwt.encode(claim, None, algorithm="none")
    for token in (gia_khoa, khong_ky):
        assert la_loi(await goi(client, token), 401, "CHUA_DANG_NHAP")


@pytest.mark.parametrize("sub", ["abc", "", "1.5", "-"])
async def test_sub_khong_phai_so_nguyen_tra_401_khong_phai_500(client, sub):
    claim = {"sub": sub, "aud": "khach", "exp": bay_gio_utc() + timedelta(minutes=5)}
    token = jwt.encode(claim, settings.JWT_SECRET.get_secret_value(), algorithm="HS256")
    assert la_loi(await goi(client, token), 401, "CHUA_DANG_NHAP")


async def test_token_cua_tai_khoan_khong_ton_tai_hoac_da_xoa_tra_401(client, db):
    da_xoa = await tao_khach(db, deleted_at=bay_gio_utc())
    assert la_loi(await goi(client, tao_access_token(da_xoa.id, "khach")), 401, "CHUA_DANG_NHAP")
    assert la_loi(await goi(client, tao_access_token(2_000_000_000, "khach")), 401, "CHUA_DANG_NHAP")


async def test_khoa_tai_khoan_co_hieu_luc_ngay_du_access_token_con_han(client, db):
    khach = await tao_khach(db)
    token = tao_access_token(khach.id, "khach")
    assert (await goi(client, token)).status_code == 200
    khach.trang_thai = TrangThaiTaiKhoan.bi_khoa
    await db.flush()
    assert la_loi(await goi(client, token), 403, "TAI_KHOAN_BI_KHOA")


async def test_khoa_tam_chua_het_han_bi_chan_con_het_han_thi_qua(client, db):
    khach = await tao_khach(db, khoa_den=bay_gio_utc() + timedelta(minutes=10))
    token = tao_access_token(khach.id, "khach")
    assert la_loi(await goi(client, token), 403, "TAI_KHOAN_BI_KHOA")
    khach.khoa_den = bay_gio_utc() - timedelta(seconds=1)
    await db.flush()
    assert (await goi(client, token)).status_code == 200


async def test_moi_route_cua_khach_deu_doi_dang_nhap(app, client):
    """Chặn quên `Depends(khach_hien_tai)` ở route `/toi/*` thêm về sau: không token thì không route nào được qua."""
    cac_route = [
        (phuong_thuc.upper(), duong_dan)
        for duong_dan, thao_tac in app.openapi()["paths"].items()
        if duong_dan == URL or duong_dan.startswith(URL + "/")
        for phuong_thuc in thao_tac
        if phuong_thuc in {"get", "post", "put", "patch", "delete"}
    ]
    assert ("GET", URL) in cac_route
    for phuong_thuc, duong_dan in cac_route:
        phan_hoi = await client.request(phuong_thuc, re.sub(r"\{[^}]+\}", "1", duong_dan))
        assert la_loi(phan_hoi, 401, "CHUA_DANG_NHAP"), (phuong_thuc, duong_dan)


# --- khach_tuy_chon: route công khai biết khách nếu có ---------------------------------------------------------------


@pytest.fixture
def app_co_route_tuy_chon(app):
    @app.get("/api/v1/_thu/ai-do")
    async def ai_do(khach: KhachHang | None = Depends(khach_tuy_chon)):
        return {"khach_id": khach.id if khach else None}

    return app


async def test_khach_tuy_chon_coi_token_vo_nghia_la_khach_vang_lai(app_co_route_tuy_chon, client, db):
    khach = await tao_khach(db)
    khoa = await tao_khach(db, trang_thai=TrangThaiTaiKhoan.bi_khoa)
    nhan_vien = await tao_nhan_vien(db)
    ket_qua = {}
    for ten, tieu_de in {
        "khong_token": {},
        "token_rac": bearer("abc.def.ghi"),
        "dung": bearer(tao_access_token(khach.id, "khach")),
        "bi_khoa": bearer(tao_access_token(khoa.id, "khach")),
        "noi_bo": bearer(tao_access_token(nhan_vien.id, "noi_bo")),
    }.items():
        phan_hoi = await client.get("/api/v1/_thu/ai-do", headers=tieu_de)
        assert phan_hoi.status_code == 200, ten
        ket_qua[ten] = phan_hoi.json()["khach_id"]
    assert ket_qua == {"khong_token": None, "token_rac": None, "dung": khach.id, "bi_khoa": None, "noi_bo": None}


async def test_khach_tuy_chon_bao_token_het_han_de_client_lam_moi(app_co_route_tuy_chon, client, db):
    khach = await tao_khach(db)
    phan_hoi = await client.get(
        "/api/v1/_thu/ai-do", headers=bearer(tao_access_token(khach.id, "khach", het_han_phut=-1))
    )
    assert la_loi(phan_hoi, 401, "TOKEN_HET_HAN")

"""Hàm dùng chung cho test xác thực và hồ sơ nhân viên (T1.3)."""

from sqlalchemy import select

from app.models.he_thong import NhatKyHeThong, PhienDangNhap
from tests.factories import MAT_KHAU_TEST
from tests.tai_khoan import dung_chung as chung

TEN_COOKIE = "refresh_token_noi_bo"
URL_DANG_NHAP = "/api/v1/noi-bo/auth/dang-nhap"
URL_LAM_MOI = "/api/v1/noi-bo/auth/lam-moi"
URL_DANG_XUAT = "/api/v1/noi-bo/auth/dang-xuat"
URL_DOI_MAT_KHAU = "/api/v1/noi-bo/auth/doi-mat-khau"
URL_TOI = "/api/v1/noi-bo/toi"
EMAIL = "duoc.si.thu@example.com"


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def dang_nhap(client, email=EMAIL, mat_khau=MAT_KHAU_TEST):
    return await client.post(URL_DANG_NHAP, json={"email": email, "mat_khau": mat_khau})


def cookie_refresh(phan_hoi) -> str | None:
    return chung.cookie_refresh(phan_hoi, TEN_COOKIE)


def dong_set_cookie(phan_hoi) -> str:
    return chung.dong_set_cookie(phan_hoi, TEN_COOKIE)


async def lam_moi(client, refresh_token: str | None):
    return await chung._goi_voi_cookie(client, URL_LAM_MOI, refresh_token, TEN_COOKIE)


async def dang_xuat(client, refresh_token: str | None):
    return await chung._goi_voi_cookie(client, URL_DANG_XUAT, refresh_token, TEN_COOKIE)


async def doi_mat_khau(client, token: str, mat_khau_cu: str, mat_khau_moi: str):
    return await client.post(
        URL_DOI_MAT_KHAU, json={"mat_khau_cu": mat_khau_cu, "mat_khau_moi": mat_khau_moi}, headers=bearer(token)
    )


async def cac_phien(db, nhan_vien_id: int) -> list[PhienDangNhap]:
    return list((await db.execute(select(PhienDangNhap).where(PhienDangNhap.nhan_vien_id == nhan_vien_id))).scalars())


async def so_phien_con_hieu_luc(db, nhan_vien_id: int) -> int:
    return len([p for p in await cac_phien(db, nhan_vien_id) if p.thu_hoi_luc is None])


async def nhat_ky(db, nhan_vien_id: int, hanh_dong: str | None = None) -> list[NhatKyHeThong]:
    truy_van = select(NhatKyHeThong).where(NhatKyHeThong.nhan_vien_id == nhan_vien_id).order_by(NhatKyHeThong.id)
    if hanh_dong:
        truy_van = truy_van.where(NhatKyHeThong.hanh_dong == hanh_dong)
    return list((await db.execute(truy_van)).scalars())

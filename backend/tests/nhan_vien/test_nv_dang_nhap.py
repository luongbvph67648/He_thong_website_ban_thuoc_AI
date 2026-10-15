"""NV01: đăng nhập nhân viên (POST /api/v1/noi-bo/auth/dang-nhap)."""

import hashlib
import json
from datetime import timedelta

import httpx
import pytest

from app.core.bao_mat import giai_ma_access_token
from app.models.enums import TrangThaiTaiKhoan
from app.modules.tai_khoan import dang_nhap as dich_vu_dang_nhap
from app.modules.tai_khoan import phien_http
from tests.factories import MAT_KHAU_TEST, tao_khach, tao_nhan_vien
from tests.nhan_vien.dung_chung import (
    EMAIL,
    URL_TOI,
    bearer,
    cac_phien,
    cookie_refresh,
    dang_nhap,
    dong_set_cookie,
    nhat_ky,
)


async def tao(db, vai_tro="PHARMACIST", **truong):
    return await tao_nhan_vien(db, vai_tro, email=EMAIL, **truong)


async def test_dang_nhap_thanh_cong_tra_token_ho_so_quyen_va_cookie_rieng(client, db):
    nv = await tao(db)
    phan_hoi = await dang_nhap(client)

    assert phan_hoi.status_code == 200
    than = phan_hoi.json()
    assert set(than) == {"access_token", "token_type", "het_han_giay", "nhan_vien"}
    assert than["token_type"] == "bearer" and than["het_han_giay"] == 15 * 60
    ho_so = than["nhan_vien"]
    assert ho_so["id"] == nv.id and ho_so["email"] == EMAIL and ho_so["ma_nhan_vien"] == nv.ma_nhan_vien
    assert ho_so["vai_tro"]["ma"] == "PHARMACIST" and ho_so["phai_doi_mat_khau"] is False
    assert ho_so["quyen"]["order.confirm"] == "day_du" and ho_so["quyen"]["stock.view"] == "chi_xem"
    assert "order.pick" not in ho_so["quyen"]  # quyền của kho
    assert '"mat_khau"' not in phan_hoi.text and "hash" not in phan_hoi.text and "argon2" not in phan_hoi.text

    claim = giai_ma_access_token(than["access_token"], "noi_bo")  # aud nội bộ, không phải khách
    assert claim["sub"] == str(nv.id)
    with pytest.raises(Exception, match="[Aa]udience"):
        giai_ma_access_token(than["access_token"], "khach")

    refresh = cookie_refresh(phan_hoi)
    assert refresh and refresh not in phan_hoi.text
    cookie = dong_set_cookie(phan_hoi)
    for thuoc_tinh in ("HttpOnly", "Secure", "SameSite=lax", "Path=/api/v1/noi-bo/auth", f"Max-Age={14 * 24 * 3600}"):
        assert thuoc_tinh in cookie, cookie

    (phien,) = await cac_phien(db, nv.id)
    assert phien.refresh_token_hash == hashlib.sha256(refresh.encode()).hexdigest()
    assert phien.khach_hang_id is None and phien.thu_hoi_luc is None and phien.ip == "127.0.0.1"


@pytest.mark.parametrize("email", [EMAIL, EMAIL.upper(), f"  {EMAIL}  ", "Duoc.Si.Thu@Example.com"])
async def test_email_khong_phan_biet_hoa_thuong_va_khoang_trang(client, db, email):
    nv = await tao(db)
    phan_hoi = await dang_nhap(client, email)
    assert phan_hoi.status_code == 200 and phan_hoi.json()["nhan_vien"]["id"] == nv.id


async def test_access_token_dang_nhap_goi_duoc_noi_bo_toi(client, db):
    nv = await tao(db, "WAREHOUSE")
    token = (await dang_nhap(client)).json()["access_token"]
    phan_hoi = await client.get(URL_TOI, headers=bearer(token))
    assert phan_hoi.status_code == 200 and phan_hoi.json()["id"] == nv.id


async def test_sai_thong_tin_cung_phan_hoi_du_tai_khoan_co_hay_khong(client, db):
    await tao(db)
    khach = await tao_khach(db, so_dien_thoai="0912345678", email="khach@example.com")
    cac_thu = [
        (EMAIL, "Sai-mat-khau-1"),  # có tài khoản, sai mật khẩu
        ("khong-co@example.com", MAT_KHAU_TEST),  # không có tài khoản
        (khach.email, MAT_KHAU_TEST),  # email của KHÁCH không phải của nhân viên
        ("0912345678", MAT_KHAU_TEST),  # đăng nhập nội bộ chỉ bằng email
    ]
    phan_hoi = [await dang_nhap(client, email, mat_khau) for email, mat_khau in cac_thu]
    assert {(p.status_code, json.dumps(p.json(), sort_keys=True)) for p in phan_hoi} == {
        (
            401,
            json.dumps(
                {"ma_loi": "SAI_THONG_TIN_DANG_NHAP", "thong_diep": "Email hoặc mật khẩu không đúng", "chi_tiet": None},
                sort_keys=True,
            ),
        )
    }
    assert all(cookie_refresh(p) is None for p in phan_hoi)


async def test_moi_lan_thu_deu_ton_dung_mot_lan_kiem_tra_mat_khau(client, db, monkeypatch):
    await tao(db)
    so_lan = []
    goc = dich_vu_dang_nhap.kiem_tra_mat_khau_async

    async def theo_doi(mat_khau, ma_bam):
        so_lan.append(1)
        return await goc(mat_khau, ma_bam)

    monkeypatch.setattr(dich_vu_dang_nhap, "kiem_tra_mat_khau_async", theo_doi)
    for email in (EMAIL, "khong-co@example.com"):
        so_lan.clear()
        await dang_nhap(client, email, "Sai-mat-khau-1")
        assert len(so_lan) == 1, email


async def test_khach_khong_dang_nhap_duoc_o_cua_noi_bo_va_nguoc_lai(client, db):
    await tao(db)
    khach = await tao_khach(db, so_dien_thoai="0912345678", email="khach@example.com")
    assert (await dang_nhap(client, khach.email)).status_code == 401
    phan_hoi = await client.post("/api/v1/auth/dang-nhap", json={"ten_dang_nhap": EMAIL, "mat_khau": MAT_KHAU_TEST})
    assert phan_hoi.status_code == 401  # email nhân viên không đăng nhập được ở cửa của khách


async def test_dang_nhap_sai_duoc_dem_va_luu_du_tra_loi(client, db):
    nv = await tao(db)
    await dang_nhap(client, mat_khau="Sai-mat-khau-1")
    await dang_nhap(client, mat_khau="Sai-mat-khau-2")
    await db.refresh(nv)
    assert nv.so_lan_dang_nhap_sai == 2 and nv.khoa_den is None


async def test_khoa_tam_sau_5_lan_sai_ghi_nhat_ky_mot_lan_va_tu_mo_sau_15_phut(client, db, thoi_gian):
    nv = await tao(db)
    for _ in range(4):
        assert (await dang_nhap(client, mat_khau="Sai-mat-khau-1")).status_code == 401
    phan_hoi = await dang_nhap(client, mat_khau="Sai-mat-khau-1")  # lần thứ 5
    assert phan_hoi.status_code == 403 and phan_hoi.json()["ma_loi"] == "TAI_KHOAN_BI_KHOA"
    assert phan_hoi.json()["chi_tiet"] == {"thu_lai_sau_giay": 15 * 60}
    await db.refresh(nv)
    assert nv.khoa_den == thoi_gian.bay_gio + timedelta(minutes=15)

    thoi_gian.tien(minutes=10)
    phan_hoi = await dang_nhap(client)  # đang khóa: mật khẩu đúng cũng bị từ chối
    assert phan_hoi.status_code == 403 and cookie_refresh(phan_hoi) is None
    assert await cac_phien(db, nv.id) == []
    await dang_nhap(client, mat_khau="Sai-mat-khau-1")  # thử thêm khi đang khóa
    assert len(await nhat_ky(db, nv.id, "khoa_tam_dang_nhap")) == 1  # chỉ ghi đúng lúc bị khóa

    thoi_gian.tien(minutes=5, seconds=1)
    assert (await dang_nhap(client)).status_code == 200
    await db.refresh(nv)
    assert nv.khoa_den is None and nv.so_lan_dang_nhap_sai == 0


async def test_tai_khoan_bi_admin_khoa_chi_lo_ra_khi_dung_mat_khau(client, db):
    nv = await tao(db, trang_thai=TrangThaiTaiKhoan.bi_khoa)
    dung = await dang_nhap(client)
    assert dung.status_code == 403 and dung.json()["ma_loi"] == "TAI_KHOAN_BI_KHOA"
    assert cookie_refresh(dung) is None and await cac_phien(db, nv.id) == []
    sai = await dang_nhap(client, mat_khau="Sai-mat-khau-1")
    assert sai.status_code == 401 and sai.json()["ma_loi"] == "SAI_THONG_TIN_DANG_NHAP"


async def test_nhan_vien_da_xoa_mem_nhu_khong_ton_tai(client, db, thoi_gian):
    await tao(db, deleted_at=thoi_gian.bay_gio)
    assert (await dang_nhap(client)).status_code == 401


async def test_dang_nhap_thanh_cong_ghi_nhat_ky_khong_lo_bi_mat(client, db):
    nv = await tao(db)
    await dang_nhap(client)
    (dong,) = await nhat_ky(db, nv.id, "dang_nhap")
    assert (dong.bang, dong.ban_ghi_id, dong.ip) == ("nhan_vien", str(nv.id), "127.0.0.1")
    assert dong.gia_tri_cu is None and dong.gia_tri_moi is None


async def test_dang_nhap_that_bai_khong_ghi_nhat_ky_dang_nhap(client, db):
    nv = await tao(db)
    await dang_nhap(client, mat_khau="Sai-mat-khau-1")
    assert await nhat_ky(db, nv.id, "dang_nhap") == []


async def test_phai_doi_mat_khau_van_dang_nhap_duoc_va_duoc_bao_trong_phan_hoi(client, db):
    await tao(db, "ADMIN", phai_doi_mat_khau=True)
    phan_hoi = await dang_nhap(client)
    assert phan_hoi.status_code == 200 and phan_hoi.json()["nhan_vien"]["phai_doi_mat_khau"] is True
    token = phan_hoi.json()["access_token"]
    assert (await client.get(URL_TOI, headers=bearer(token))).status_code == 200  # hồ sơ vẫn đọc được
    chan = await client.get("/api/v1/noi-bo/thong-bao", headers=bearer(token))
    assert chan.status_code == 403 and chan.json()["ma_loi"] == "PHAI_DOI_MAT_KHAU"


@pytest.mark.parametrize("thieu", ["email", "mat_khau"])
async def test_thieu_truong_tra_400(client, thieu):
    than = {"email": EMAIL, "mat_khau": "x"}
    del than[thieu]
    phan_hoi = await client.post("/api/v1/noi-bo/auth/dang-nhap", json=than)
    assert phan_hoi.status_code == 400 and phan_hoi.json()["chi_tiet"][0]["truong"] == thieu


async def test_gioi_han_theo_ip_chan_do_mat_khau_va_tach_rieng_voi_cua_khach(client, db, monkeypatch, app):
    monkeypatch.setattr(phien_http, "DANG_NHAP_TOI_DA_MOI_IP", 3)
    await tao(db)
    khach = await tao_khach(db, so_dien_thoai="0912345678")
    for _ in range(3):
        assert (await dang_nhap(client, mat_khau="Sai-mat-khau-1")).status_code == 401
    phan_hoi = await dang_nhap(client)  # đúng mật khẩu cũng bị chặn vì IP đã thử quá nhiều
    assert phan_hoi.status_code == 429 and phan_hoi.json()["ma_loi"] == "QUA_GIOI_HAN"
    assert 0 < int(phan_hoi.headers["Retry-After"]) <= 601 and cookie_refresh(phan_hoi) is None

    # Cửa của khách dùng bộ đếm riêng: kẻ thử mật khẩu nhân viên không khóa được khách cùng IP.
    cua_khach = await client.post(
        "/api/v1/auth/dang-nhap", json={"ten_dang_nhap": khach.so_dien_thoai, "mat_khau": MAT_KHAU_TEST}
    )
    assert cua_khach.status_code == 200

    transport = httpx.ASGITransport(app=app, client=("10.9.8.7", 4444))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as khac:
        assert (await dang_nhap(khac)).status_code == 200

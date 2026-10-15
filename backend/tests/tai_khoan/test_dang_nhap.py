"""KVL10: đăng nhập khách (POST /api/v1/auth/dang-nhap)."""

import hashlib
import json
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import select, update

from app.core.bao_mat import giai_ma_access_token
from app.models.enums import TrangThaiTaiKhoan
from app.models.he_thong import CauHinh, PhienDangNhap
from app.modules.tai_khoan import dang_nhap as dich_vu_dang_nhap
from app.modules.tai_khoan import router_cong_khai
from tests.factories import MAT_KHAU_TEST, tao_khach
from tests.tai_khoan.dung_chung import SDT, cookie_refresh, dang_nhap, dong_set_cookie


async def cac_phien(db, khach_id):
    return list((await db.execute(select(PhienDangNhap).where(PhienDangNhap.khach_hang_id == khach_id))).scalars())


async def test_dang_nhap_thanh_cong_tra_access_token_va_dat_cookie_refresh(client, db):
    khach = await tao_khach(db, so_dien_thoai=SDT)
    phan_hoi = await dang_nhap(client)

    assert phan_hoi.status_code == 200
    than = phan_hoi.json()
    assert set(than) == {"access_token", "token_type", "het_han_giay", "khach_hang"}
    assert than["token_type"] == "bearer" and than["het_han_giay"] == 15 * 60
    assert than["khach_hang"] == {"id": khach.id, "ho_ten": khach.ho_ten, "so_dien_thoai": SDT, "email": khach.email}
    claim = giai_ma_access_token(than["access_token"], "khach")
    assert claim["sub"] == str(khach.id)

    refresh = cookie_refresh(phan_hoi)
    assert refresh and len(refresh) >= 43  # 32 byte ngẫu nhiên = 256 bit
    assert refresh not in phan_hoi.text  # refresh token chỉ đi trong cookie, không nằm trong JSON
    cookie = dong_set_cookie(phan_hoi)
    for thuoc_tinh in ("HttpOnly", "Secure", "SameSite=lax", "Path=/api/v1/auth", f"Max-Age={14 * 24 * 3600}"):
        assert thuoc_tinh in cookie, cookie

    (phien,) = await cac_phien(db, khach.id)
    assert phien.refresh_token_hash == hashlib.sha256(refresh.encode()).hexdigest()
    assert refresh not in phien.refresh_token_hash and phien.thu_hoi_luc is None
    assert phien.nhan_vien_id is None and phien.ip == "127.0.0.1" and phien.thiet_bi.startswith("python-httpx")


async def test_access_token_cua_dang_nhap_goi_duoc_api_khach(client, db):
    khach = await tao_khach(db, so_dien_thoai=SDT)
    token = (await dang_nhap(client)).json()["access_token"]
    phan_hoi = await client.get("/api/v1/toi", headers={"Authorization": f"Bearer {token}"})
    assert phan_hoi.status_code == 200 and phan_hoi.json()["id"] == khach.id


@pytest.mark.parametrize(
    "ten", [SDT, "+84 912 345 678", "0912.345.678", "Khach.Test@Example.COM", "  khach.test@example.com  "]
)
async def test_dang_nhap_bang_so_dien_thoai_hoac_email_khong_phan_biet_dinh_dang(client, db, ten):
    khach = await tao_khach(db, so_dien_thoai=SDT, email="khach.test@example.com")
    phan_hoi = await dang_nhap(client, ten)
    assert phan_hoi.status_code == 200 and phan_hoi.json()["khach_hang"]["id"] == khach.id


async def test_mat_khau_phan_biet_hoa_thuong(client, db):
    await tao_khach(db, so_dien_thoai=SDT)
    assert (await dang_nhap(client, SDT, MAT_KHAU_TEST.upper())).status_code == 401


async def test_sai_thong_tin_cung_phan_hoi_du_tai_khoan_co_hay_khong(client, db):
    """Chống dò tài khoản: sai mật khẩu, số chưa đăng ký, email lạ, định dạng vô nghĩa đều cho phản hồi y hệt."""
    await tao_khach(db, so_dien_thoai=SDT, email="co@example.com")
    cac_thu = [
        (SDT, "Sai-mat-khau-1"),  # có tài khoản, sai mật khẩu
        ("0987654321", MAT_KHAU_TEST),  # số chưa đăng ký
        ("khong-co@example.com", MAT_KHAU_TEST),
        ("abc", MAT_KHAU_TEST),  # không phải số điện thoại cũng không phải email
    ]
    phan_hoi = [await dang_nhap(client, ten, mat_khau) for ten, mat_khau in cac_thu]
    assert {(p.status_code, json.dumps(p.json(), sort_keys=True)) for p in phan_hoi} == {
        (
            401,
            json.dumps(
                {
                    "ma_loi": "SAI_THONG_TIN_DANG_NHAP",
                    "thong_diep": "Số điện thoại/email hoặc mật khẩu không đúng",
                    "chi_tiet": None,
                },
                sort_keys=True,
            ),
        )
    }
    assert all(cookie_refresh(p) is None for p in phan_hoi)


async def test_moi_lan_thu_deu_ton_dung_mot_lan_kiem_tra_mat_khau(client, db, monkeypatch):
    """Số lạ không được trả lời nhanh hơn số có thật (chống dò bằng thời gian): đường nào cũng băm một lần."""
    await tao_khach(db, so_dien_thoai=SDT, email="co@example.com")
    so_lan = []
    goc = dich_vu_dang_nhap.kiem_tra_mat_khau_async

    async def theo_doi(mat_khau, ma_bam):
        so_lan.append(1)
        return await goc(mat_khau, ma_bam)

    monkeypatch.setattr(dich_vu_dang_nhap, "kiem_tra_mat_khau_async", theo_doi)
    for ten in (SDT, "0987654321", "khong-co@example.com", "co@example.com"):
        so_lan.clear()
        await dang_nhap(client, ten, "Sai-mat-khau-1")
        assert len(so_lan) == 1, ten


async def test_dang_nhap_sai_duoc_dem_va_luu_du_tra_loi(client, db):
    """Bộ đếm phải ở lại DB dù request trả 401 (route TRẢ VỀ lỗi, không raise)."""
    khach = await tao_khach(db, so_dien_thoai=SDT)
    await dang_nhap(client, SDT, "Sai-mat-khau-1")
    await dang_nhap(client, SDT, "Sai-mat-khau-2")
    await db.refresh(khach)
    assert khach.so_lan_dang_nhap_sai == 2 and khach.khoa_den is None


async def test_dang_nhap_dung_xoa_bo_dem_sai(client, db):
    khach = await tao_khach(db, so_dien_thoai=SDT)
    await dang_nhap(client, SDT, "Sai-mat-khau-1")
    assert (await dang_nhap(client)).status_code == 200
    await db.refresh(khach)
    assert khach.so_lan_dang_nhap_sai == 0


async def test_khoa_tam_sau_5_lan_sai_va_tu_mo_sau_15_phut(client, db, thoi_gian):
    khach = await tao_khach(db, so_dien_thoai=SDT)
    for _ in range(4):
        assert (await dang_nhap(client, SDT, "Sai-mat-khau-1")).status_code == 401
    phan_hoi = await dang_nhap(client, SDT, "Sai-mat-khau-1")  # lần thứ 5
    assert phan_hoi.status_code == 403 and phan_hoi.json()["ma_loi"] == "TAI_KHOAN_BI_KHOA"
    assert phan_hoi.json()["chi_tiet"] == {"thu_lai_sau_giay": 15 * 60}
    await db.refresh(khach)
    assert khach.khoa_den == thoi_gian.bay_gio + timedelta(minutes=15)

    # Đang khóa: mật khẩu ĐÚNG cũng bị từ chối, không tạo phiên, không cộng thêm lần sai.
    thoi_gian.tien(minutes=10)
    phan_hoi = await dang_nhap(client)
    assert phan_hoi.status_code == 403 and phan_hoi.json()["ma_loi"] == "TAI_KHOAN_BI_KHOA"
    assert 0 < phan_hoi.json()["chi_tiet"]["thu_lai_sau_giay"] <= 5 * 60 + 1
    assert await cac_phien(db, khach.id) == []

    thoi_gian.tien(minutes=4, seconds=59)
    assert (await dang_nhap(client)).status_code == 403
    thoi_gian.tien(seconds=2)  # đủ 15 phút
    assert (await dang_nhap(client)).status_code == 200
    await db.refresh(khach)
    assert khach.khoa_den is None and khach.so_lan_dang_nhap_sai == 0


async def test_nhap_sai_khi_dang_khoa_khong_keo_dai_thoi_gian_khoa(client, db, thoi_gian):
    """Kẻ phá không thể khóa người dùng vĩnh viễn bằng cách gửi sai liên tục."""
    khach = await tao_khach(db, so_dien_thoai=SDT)
    for _ in range(5):
        await dang_nhap(client, SDT, "Sai-mat-khau-1")
    await db.refresh(khach)
    han_khoa = khach.khoa_den
    thoi_gian.tien(minutes=5)
    for _ in range(3):
        assert (await dang_nhap(client, SDT, "Sai-mat-khau-1")).status_code == 403
    await db.refresh(khach)
    assert khach.khoa_den == han_khoa and khach.so_lan_dang_nhap_sai == 0


async def test_so_lan_sai_va_thoi_gian_khoa_doc_tu_cau_hinh(client, db, thoi_gian):
    await db.execute(update(CauHinh).where(CauHinh.khoa == "so_lan_dang_nhap_sai_toi_da").values(gia_tri=2))
    await db.execute(update(CauHinh).where(CauHinh.khoa == "thoi_gian_khoa_dang_nhap_phut").values(gia_tri=30))
    await tao_khach(db, so_dien_thoai=SDT)
    assert (await dang_nhap(client, SDT, "Sai-mat-khau-1")).status_code == 401
    phan_hoi = await dang_nhap(client, SDT, "Sai-mat-khau-1")
    assert phan_hoi.status_code == 403 and phan_hoi.json()["chi_tiet"] == {"thu_lai_sau_giay": 30 * 60}


async def test_tai_khoan_bi_admin_khoa_chi_lo_ra_khi_dung_mat_khau(client, db):
    khach = await tao_khach(db, so_dien_thoai=SDT, trang_thai=TrangThaiTaiKhoan.bi_khoa)
    dung = await dang_nhap(client)
    assert dung.status_code == 403 and dung.json()["ma_loi"] == "TAI_KHOAN_BI_KHOA"
    assert cookie_refresh(dung) is None and await cac_phien(db, khach.id) == []
    sai = await dang_nhap(client, SDT, "Sai-mat-khau-1")  # người lạ không biết tài khoản này tồn tại
    assert sai.status_code == 401 and sai.json()["ma_loi"] == "SAI_THONG_TIN_DANG_NHAP"


async def test_tai_khoan_da_xoa_mem_nhu_khong_ton_tai(client, db, thoi_gian):
    await tao_khach(db, so_dien_thoai=SDT, deleted_at=thoi_gian.bay_gio)
    phan_hoi = await dang_nhap(client)
    assert phan_hoi.status_code == 401 and phan_hoi.json()["ma_loi"] == "SAI_THONG_TIN_DANG_NHAP"


@pytest.mark.parametrize("thieu", ["ten_dang_nhap", "mat_khau"])
async def test_thieu_truong_tra_400(client, thieu):
    than = {"ten_dang_nhap": SDT, "mat_khau": "x"}
    del than[thieu]
    phan_hoi = await client.post("/api/v1/auth/dang-nhap", json=than)
    assert phan_hoi.status_code == 400 and phan_hoi.json()["chi_tiet"][0]["truong"] == thieu


async def test_gioi_han_theo_ip_chan_do_mat_khau_dien_rong(client, db, monkeypatch, app):
    monkeypatch.setattr(router_cong_khai, "DANG_NHAP_TOI_DA_MOI_IP", 3)
    await tao_khach(db, so_dien_thoai=SDT)
    for _ in range(3):
        assert (await dang_nhap(client, SDT, "Sai-mat-khau-1")).status_code == 401
    phan_hoi = await dang_nhap(client)  # đúng mật khẩu cũng bị chặn vì IP đã thử quá nhiều
    assert phan_hoi.status_code == 429 and phan_hoi.json()["ma_loi"] == "QUA_GIOI_HAN"
    giay = int(phan_hoi.headers["Retry-After"])
    assert 0 < giay <= 601 and phan_hoi.json()["chi_tiet"] == {"thu_lai_sau_giay": giay}
    assert cookie_refresh(phan_hoi) is None

    # IP khác không bị ảnh hưởng.
    transport = httpx.ASGITransport(app=app, client=("10.9.8.7", 4444))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as khac:
        assert (await dang_nhap(khac)).status_code == 200

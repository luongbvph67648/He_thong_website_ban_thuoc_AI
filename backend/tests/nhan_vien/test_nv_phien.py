"""NV01: làm mới, đăng xuất, cách ly phiên khách và phiên nhân viên."""

import asyncio
import hashlib

from sqlalchemy import select

from app.models.enums import TrangThaiTaiKhoan
from app.models.he_thong import PhienDangNhap
from app.modules.tai_khoan import phien
from app.modules.tai_khoan.phien import KetQuaLamMoi
from tests.factories import MAT_KHAU_TEST, tao_khach, tao_nhan_vien
from tests.nhan_vien.dung_chung import (
    EMAIL,
    URL_LAM_MOI,
    URL_TOI,
    bearer,
    cookie_refresh,
    dang_nhap,
    dang_xuat,
    dong_set_cookie,
    lam_moi,
    so_phien_con_hieu_luc,
)
from tests.tai_khoan import dung_chung as khach


async def dang_nhap_lay_refresh(client, email=EMAIL) -> str:
    phan_hoi = await dang_nhap(client, email)
    assert phan_hoi.status_code == 200, phan_hoi.text
    return cookie_refresh(phan_hoi)


async def dong_phien(db, token: str) -> PhienDangNhap:
    bam = hashlib.sha256(token.encode()).hexdigest()
    return (await db.execute(select(PhienDangNhap).where(PhienDangNhap.refresh_token_hash == bam))).scalar_one()


async def test_lam_moi_xoay_vong_va_cap_access_token_noi_bo_moi(client, db):
    nv = await tao_nhan_vien(db, "WAREHOUSE", email=EMAIL)
    cu = await dang_nhap_lay_refresh(client)

    phan_hoi = await lam_moi(client, cu)
    assert phan_hoi.status_code == 200
    assert set(phan_hoi.json()) == {"access_token", "token_type", "het_han_giay"}
    moi = cookie_refresh(phan_hoi)
    assert moi and moi != cu and moi not in phan_hoi.text
    for thuoc_tinh in ("HttpOnly", "Secure", "SameSite=lax", "Path=/api/v1/noi-bo/auth"):
        assert thuoc_tinh in dong_set_cookie(phan_hoi)
    assert (await dong_phien(db, cu)).thu_hoi_luc is not None
    assert (await dong_phien(db, moi)).thu_hoi_luc is None and await so_phien_con_hieu_luc(db, nv.id) == 1

    toi = await client.get(URL_TOI, headers=bearer(phan_hoi.json()["access_token"]))
    assert toi.status_code == 200 and toi.json()["id"] == nv.id


async def test_dung_lai_refresh_token_thu_hoi_moi_phien_cua_nhan_vien_do_va_chi_nhan_vien_do(client, db):
    nv = await tao_nhan_vien(db, email=EMAIL)
    nguoi_khac = await tao_nhan_vien(db, email="nguoi.khac@example.com")
    khach_hang = await tao_khach(db, so_dien_thoai="0912345678")
    cu = await dang_nhap_lay_refresh(client)
    moi = cookie_refresh(await lam_moi(client, cu))
    may_khac = await dang_nhap_lay_refresh(client)
    phien_nguoi_khac = await dang_nhap_lay_refresh(client, nguoi_khac.email)
    phien_khach = khach.cookie_refresh(
        await client.post("/api/v1/auth/dang-nhap", json={"ten_dang_nhap": "0912345678", "mat_khau": MAT_KHAU_TEST})
    )

    phan_hoi = await lam_moi(client, cu)
    assert phan_hoi.status_code == 401 and phan_hoi.json()["ma_loi"] == "CHUA_DANG_NHAP"
    assert cookie_refresh(phan_hoi) == "" and "Max-Age=0" in dong_set_cookie(phan_hoi)

    assert await so_phien_con_hieu_luc(db, nv.id) == 0
    assert (await lam_moi(client, moi)).status_code == 401 and (await lam_moi(client, may_khac)).status_code == 401
    assert (await lam_moi(client, phien_nguoi_khac)).status_code == 200  # nhân viên khác không bị ảnh hưởng
    assert (await khach.lam_moi(client, phien_khach)).status_code == 200  # khách cũng không
    assert khach_hang.id  # (tránh cảnh báo biến không dùng)


async def test_cookie_khong_co_hoac_rac_tra_401_va_khong_dong_den_phien_nao(client, db):
    nv = await tao_nhan_vien(db, email=EMAIL)
    await dang_nhap_lay_refresh(client)
    for token in (None, "", "khong-phai-token"):
        phan_hoi = await lam_moi(client, token)
        assert phan_hoi.status_code == 401 and phan_hoi.json()["ma_loi"] == "CHUA_DANG_NHAP", token
    assert await so_phien_con_hieu_luc(db, nv.id) == 1


async def test_refresh_token_het_han_14_ngay(client, db, thoi_gian):
    await tao_nhan_vien(db, email=EMAIL)
    refresh = await dang_nhap_lay_refresh(client)
    thoi_gian.tien(days=14, seconds=1)
    phan_hoi = await lam_moi(client, refresh)
    assert phan_hoi.status_code == 401 and phan_hoi.json()["ma_loi"] == "TOKEN_HET_HAN"
    assert cookie_refresh(phan_hoi) == ""


async def test_bi_khoa_giua_chung_khong_lam_moi_duoc_va_mat_het_phien(client, db):
    nv = await tao_nhan_vien(db, email=EMAIL)
    refresh = await dang_nhap_lay_refresh(client)
    may_khac = await dang_nhap_lay_refresh(client)
    nv.trang_thai = TrangThaiTaiKhoan.bi_khoa
    await db.flush()

    phan_hoi = await lam_moi(client, refresh)
    assert phan_hoi.status_code == 403 and phan_hoi.json()["ma_loi"] == "TAI_KHOAN_BI_KHOA"
    assert cookie_refresh(phan_hoi) == "" and await so_phien_con_hieu_luc(db, nv.id) == 0

    nv.trang_thai = TrangThaiTaiKhoan.hoat_dong  # mở khóa không hồi sinh token cũ
    await db.flush()
    assert (await lam_moi(client, refresh)).status_code == 401
    assert (await lam_moi(client, may_khac)).status_code == 401


async def test_xoa_mem_giua_chung_khong_lam_moi_duoc(client, db, thoi_gian):
    nv = await tao_nhan_vien(db, email=EMAIL)
    refresh = await dang_nhap_lay_refresh(client)
    nv.deleted_at = thoi_gian.bay_gio
    await db.flush()
    phan_hoi = await lam_moi(client, refresh)
    assert phan_hoi.status_code == 403 and await so_phien_con_hieu_luc(db, nv.id) == 0


async def test_phien_khach_va_phien_nhan_vien_khong_dung_chung_duoc(client, db):
    """Refresh token của khách đưa vào cửa nhân viên (và ngược lại) bị từ chối mà không thu hồi nhầm phiên nào."""
    nv = await tao_nhan_vien(db, email=EMAIL)
    khach_hang = await tao_khach(db, so_dien_thoai="0912345678")
    phien_khach = (await phien.tao_phien(db, loai="khach", chu_id=khach_hang.id)).refresh_token
    phien_nv = (await phien.tao_phien(db, loai="noi_bo", chu_id=nv.id)).refresh_token

    # Cùng tên cookie của nhân viên nhưng mang token của khách.
    assert (await lam_moi(client, phien_khach)).status_code == 401
    # Cùng tên cookie của khách nhưng mang token của nhân viên.
    assert (await khach.lam_moi(client, phien_nv)).status_code == 401
    assert (await dong_phien(db, phien_khach)).thu_hoi_luc is None
    assert (await dong_phien(db, phien_nv)).thu_hoi_luc is None
    # Đúng cổng thì dùng bình thường.
    assert (await lam_moi(client, phien_nv)).status_code == 200
    assert (await khach.lam_moi(client, phien_khach)).status_code == 200


async def test_cookie_ten_khac_khong_duoc_chap_nhan_o_cua_nhan_vien(client, db):
    """Cửa nhân viên chỉ đọc cookie `refresh_token_noi_bo`; cookie `refresh_token` của khách bị bỏ qua."""
    nv = await tao_nhan_vien(db, email=EMAIL)
    token = (await phien.tao_phien(db, loai="noi_bo", chu_id=nv.id)).refresh_token
    phan_hoi = await client.post(URL_LAM_MOI, headers=khach.kem_cookie(token))
    assert phan_hoi.status_code == 401
    assert (await dong_phien(db, token)).thu_hoi_luc is None


async def test_hai_lan_lam_moi_dong_thoi_cung_mot_token_chi_mot_ben_thang(db_that):
    from tests.factories import tao_nhan_vien as tao

    async with db_that() as s, s.begin():
        nv_id = (await tao(s)).id
        refresh = (await phien.tao_phien(s, loai="noi_bo", chu_id=nv_id)).refresh_token

    a_da_xoay = asyncio.Event()

    async def ben_a():
        async with db_that() as s, s.begin():
            ket_qua = (await phien.lam_moi_phien(s, refresh_token=refresh, loai="noi_bo")).ket_qua
            a_da_xoay.set()
            await asyncio.sleep(0.4)
            return ket_qua

    async def ben_b():
        await a_da_xoay.wait()
        async with db_that() as s, s.begin():
            return (await phien.lam_moi_phien(s, refresh_token=refresh, loai="noi_bo")).ket_qua

    ket_qua = await asyncio.wait_for(asyncio.gather(ben_a(), ben_b()), timeout=10)
    assert tuple(ket_qua) == (KetQuaLamMoi.OK, KetQuaLamMoi.DA_THU_HOI)
    async with db_that() as s:
        assert await so_phien_con_hieu_luc(s, nv_id) == 0


async def test_dang_xuat_thu_hoi_dung_phien_va_xoa_cookie(client, db):
    nv = await tao_nhan_vien(db, email=EMAIL)
    dien_thoai = await dang_nhap_lay_refresh(client)
    may_tinh = await dang_nhap_lay_refresh(client)
    phan_hoi = await dang_xuat(client, dien_thoai)
    assert phan_hoi.status_code == 204 and phan_hoi.content == b""
    assert cookie_refresh(phan_hoi) == "" and "Max-Age=0" in dong_set_cookie(phan_hoi)
    assert "Path=/api/v1/noi-bo/auth" in dong_set_cookie(phan_hoi)
    assert await so_phien_con_hieu_luc(db, nv.id) == 1
    assert (await lam_moi(client, may_tinh)).status_code == 200  # phiên còn lại không bị đụng tới
    # Dùng lại token đã đăng xuất là dấu hiệu bị lộ: bị coi như dùng lại token đã thu hồi.
    assert (await lam_moi(client, dien_thoai)).status_code == 401


async def test_dang_xuat_khong_co_hoac_sai_cookie_van_204(client, db):
    nv = await tao_nhan_vien(db, email=EMAIL)
    refresh = await dang_nhap_lay_refresh(client)
    for token in (None, "", "khong-phai-token"):
        assert (await dang_xuat(client, token)).status_code == 204
    await dang_xuat(client, refresh)
    assert (await dang_xuat(client, refresh)).status_code == 204
    assert await so_phien_con_hieu_luc(db, nv.id) == 0


async def test_cookie_jar_cua_trinh_duyet_tach_khach_va_nhan_vien(client_https, db):
    """Một trình duyệt đăng nhập cả hai: cookie nhân viên chỉ đi tới /noi-bo/auth, cookie khách chỉ tới /auth."""
    await tao_nhan_vien(db, email=EMAIL)
    await tao_khach(db, so_dien_thoai="0912345678")
    assert (await dang_nhap(client_https)).status_code == 200
    assert (
        await client_https.post(
            "/api/v1/auth/dang-nhap", json={"ten_dang_nhap": "0912345678", "mat_khau": MAT_KHAU_TEST}
        )
    ).status_code == 200

    lm_nv = await client_https.post("/api/v1/noi-bo/auth/lam-moi")
    assert lm_nv.status_code == 200
    cookie_gui = lm_nv.request.headers["cookie"]
    assert "refresh_token_noi_bo=" in cookie_gui and "refresh_token=" not in cookie_gui.replace(
        "refresh_token_noi_bo=", ""
    )

    lm_khach = await client_https.post("/api/v1/auth/lam-moi")
    assert lm_khach.status_code == 200 and "refresh_token_noi_bo" not in lm_khach.request.headers["cookie"]

    api_thuong = await client_https.get(URL_TOI, headers=bearer(lm_nv.json()["access_token"]))
    assert "cookie" not in api_thuong.request.headers  # API thường không nhận refresh token nào

"""KVL10: làm mới và đăng xuất (refresh token xoay vòng, phát hiện dùng lại)."""

import asyncio
import hashlib
from datetime import timedelta

from sqlalchemy import select

from app.models.enums import TrangThaiTaiKhoan
from app.models.he_thong import PhienDangNhap
from app.models.khach_hang import KhachHang
from app.modules.tai_khoan import phien
from app.modules.tai_khoan.phien import KetQuaLamMoi
from tests.factories import tao_khach, tao_nhan_vien
from tests.tai_khoan.dung_chung import (
    SDT,
    cookie_refresh,
    dang_nhap,
    dang_xuat,
    dong_set_cookie,
    lam_moi,
)


def bam(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def dong_phien(db, token: str) -> PhienDangNhap:
    return (await db.execute(select(PhienDangNhap).where(PhienDangNhap.refresh_token_hash == bam(token)))).scalar_one()


async def so_phien_con_hieu_luc(db, khach_id: int) -> int:
    dong = (
        await db.execute(
            select(PhienDangNhap).where(PhienDangNhap.khach_hang_id == khach_id, PhienDangNhap.thu_hoi_luc.is_(None))
        )
    ).scalars()
    return len(list(dong))


async def dang_nhap_lay_refresh(client, ten=SDT) -> str:
    phan_hoi = await dang_nhap(client, ten)
    assert phan_hoi.status_code == 200, phan_hoi.text
    return cookie_refresh(phan_hoi)


# --- Làm mới --------------------------------------------------------------------------------------------------------


async def test_lam_moi_xoay_vong_refresh_token_va_cap_access_token_moi(client, db):
    khach = await tao_khach(db, so_dien_thoai=SDT)
    cu = await dang_nhap_lay_refresh(client)

    phan_hoi = await lam_moi(client, cu)
    assert phan_hoi.status_code == 200
    assert set(phan_hoi.json()) == {"access_token", "token_type", "het_han_giay"}
    moi = cookie_refresh(phan_hoi)
    assert moi and moi != cu and moi not in phan_hoi.text
    for thuoc_tinh in ("HttpOnly", "Secure", "SameSite=lax", "Path=/api/v1/auth"):
        assert thuoc_tinh in dong_set_cookie(phan_hoi)

    assert (await dong_phien(db, cu)).thu_hoi_luc is not None  # token cũ chết ngay
    assert (await dong_phien(db, moi)).thu_hoi_luc is None
    assert await so_phien_con_hieu_luc(db, khach.id) == 1
    goi = await client.get("/api/v1/toi", headers={"Authorization": f"Bearer {phan_hoi.json()['access_token']}"})
    assert goi.status_code == 200 and goi.json()["id"] == khach.id


async def test_dung_lai_refresh_token_da_thu_hoi_thu_hoi_toan_bo_phien(client, db):
    """Token cũ xuất hiện lần nữa nghĩa là đã bị đánh cắp: cả kẻ trộm lẫn chủ thật đều phải đăng nhập lại."""
    khach = await tao_khach(db, so_dien_thoai=SDT)
    nguoi_khac = await tao_khach(db)
    cu = await dang_nhap_lay_refresh(client)
    moi = cookie_refresh(await lam_moi(client, cu))
    may_khac = await dang_nhap_lay_refresh(client)  # phiên thứ hai của cùng khách (máy khác)
    phien_nguoi_khac = cookie_refresh(
        await client.post(
            "/api/v1/auth/dang-nhap", json={"ten_dang_nhap": nguoi_khac.so_dien_thoai, "mat_khau": "Mat-khau-test-1"}
        )
    )
    assert await so_phien_con_hieu_luc(db, khach.id) == 2

    phan_hoi = await lam_moi(client, cu)  # kẻ trộm dùng lại token cũ
    assert phan_hoi.status_code == 401 and phan_hoi.json()["ma_loi"] == "CHUA_DANG_NHAP"
    assert cookie_refresh(phan_hoi) == "" and "Max-Age=0" in dong_set_cookie(phan_hoi)

    assert await so_phien_con_hieu_luc(db, khach.id) == 0  # đã ghi vào DB dù trả 401
    assert (await lam_moi(client, moi)).status_code == 401  # chủ thật cũng bị đẩy ra
    assert (await lam_moi(client, may_khac)).status_code == 401
    assert (await lam_moi(client, phien_nguoi_khac)).status_code == 200  # khách khác không bị ảnh hưởng


async def test_khong_co_cookie_hoac_cookie_rac_tra_401_va_khong_dong_den_phien_nao(client, db):
    khach = await tao_khach(db, so_dien_thoai=SDT)
    hop_le = await dang_nhap_lay_refresh(client)
    for token in (None, "", "khong-phai-token", hop_le[:-1] + ("A" if hop_le[-1] != "A" else "B")):
        phan_hoi = await lam_moi(client, token)
        assert phan_hoi.status_code == 401 and phan_hoi.json()["ma_loi"] == "CHUA_DANG_NHAP", token
    assert await so_phien_con_hieu_luc(db, khach.id) == 1
    assert (await lam_moi(client, hop_le)).status_code == 200


async def test_refresh_token_het_han_14_ngay(client, db, thoi_gian):
    await tao_khach(db, so_dien_thoai=SDT)
    refresh = await dang_nhap_lay_refresh(client)
    thoi_gian.tien(days=14, seconds=-1)
    sat_han = await lam_moi(client, refresh)
    assert sat_han.status_code == 200  # còn một giây vẫn dùng được

    thoi_gian.tien(days=14, seconds=2)  # token mới cũng quá 14 ngày kể từ lúc cấp
    phan_hoi = await lam_moi(client, cookie_refresh(sat_han))
    assert phan_hoi.status_code == 401 and phan_hoi.json()["ma_loi"] == "TOKEN_HET_HAN"
    assert cookie_refresh(phan_hoi) == ""


async def test_moi_lan_lam_moi_cap_lai_du_14_ngay(client, db, thoi_gian):
    """Người dùng thường xuyên quay lại không bị đăng xuất: hạn tính từ lần làm mới gần nhất."""
    await tao_khach(db, so_dien_thoai=SDT)
    refresh = await dang_nhap_lay_refresh(client)
    for _ in range(3):
        thoi_gian.tien(days=13)
        phan_hoi = await lam_moi(client, refresh)
        assert phan_hoi.status_code == 200
        refresh = cookie_refresh(phan_hoi)
    assert (await dong_phien(db, refresh)).het_han == thoi_gian.bay_gio + timedelta(days=14)


async def test_tai_khoan_bi_khoa_giua_chung_khong_lam_moi_duoc_va_mat_het_phien(client, db):
    khach = await tao_khach(db, so_dien_thoai=SDT)
    refresh = await dang_nhap_lay_refresh(client)
    may_khac = await dang_nhap_lay_refresh(client)
    khach.trang_thai = TrangThaiTaiKhoan.bi_khoa
    await db.flush()

    phan_hoi = await lam_moi(client, refresh)
    assert phan_hoi.status_code == 403 and phan_hoi.json()["ma_loi"] == "TAI_KHOAN_BI_KHOA"
    assert cookie_refresh(phan_hoi) == ""
    assert await so_phien_con_hieu_luc(db, khach.id) == 0  # kể cả phiên vừa được xoay vòng

    khach.trang_thai = TrangThaiTaiKhoan.hoat_dong  # mở khóa không "hồi sinh" token cũ
    await db.flush()
    assert (await lam_moi(client, refresh)).status_code == 401
    assert (await lam_moi(client, may_khac)).status_code == 401


async def test_tai_khoan_dang_khoa_tam_khong_lam_moi_duoc(client, db, thoi_gian):
    khach = await tao_khach(db, so_dien_thoai=SDT)
    refresh = await dang_nhap_lay_refresh(client)
    khach.khoa_den = thoi_gian.bay_gio + timedelta(minutes=5)
    await db.flush()
    phan_hoi = await lam_moi(client, refresh)
    assert phan_hoi.status_code == 403 and phan_hoi.json()["ma_loi"] == "TAI_KHOAN_BI_KHOA"
    assert 0 < phan_hoi.json()["chi_tiet"]["thu_lai_sau_giay"] <= 5 * 60 + 1


async def test_ke_la_lam_khoa_tam_khong_duoc_dang_xuat_chu_tai_khoan(client, db, thoi_gian):
    """Người lạ gửi sai mật khẩu 5 lần để khóa tạm: phiên của chủ tài khoản KHÔNG bị xoay vòng, thu hồi hay xóa cookie
    (QĐ-12); hết khóa thì chính các refresh token cũ dùng tiếp được."""
    khach = await tao_khach(db, so_dien_thoai=SDT)
    dien_thoai = await dang_nhap_lay_refresh(client)
    may_tinh = await dang_nhap_lay_refresh(client)
    for _ in range(5):
        await dang_nhap(client, SDT, "Sai-mat-khau-1")  # kẻ lạ

    phan_hoi = await lam_moi(client, dien_thoai)
    assert phan_hoi.status_code == 403 and phan_hoi.json()["ma_loi"] == "TAI_KHOAN_BI_KHOA"
    assert phan_hoi.json()["chi_tiet"]["thu_lai_sau_giay"] > 0
    assert cookie_refresh(phan_hoi) is None  # không ra lệnh xóa cookie
    assert await so_phien_con_hieu_luc(db, khach.id) == 2
    assert (await dong_phien(db, dien_thoai)).thu_hoi_luc is None  # chưa bị xoay vòng

    thoi_gian.tien(minutes=15, seconds=1)
    assert (await lam_moi(client, dien_thoai)).status_code == 200
    assert (await lam_moi(client, may_tinh)).status_code == 200


async def test_dat_lai_mat_khau_khoa_tai_khoan_truoc_roi_lam_moi_dong_thoi_khong_deadlock(db_that):
    """Thứ tự ngược: chủ đã khóa dòng tài khoản (như route đặt lại mật khẩu) thì lần làm mới đến sau phải CHỜ khóa đó
    rồi thấy token đã bị thu hồi. Nếu làm mới chỉ khóa dòng phiên, hai bên giữ khóa chéo nhau và Postgres hủy một
    giao dịch bằng lỗi deadlock (500 cho người dùng)."""
    async with db_that() as s, s.begin():
        khach_id = (await tao_khach(s)).id
        refresh = (await phien.tao_phien(s, loai="khach", chu_id=khach_id)).refresh_token

    chu_giu_khoa = asyncio.Event()

    async def chu_dat_lai_mat_khau():
        async with db_that() as s, s.begin():
            await s.execute(select(KhachHang).where(KhachHang.id == khach_id).with_for_update())
            chu_giu_khoa.set()
            await asyncio.sleep(0.4)  # giữ khóa tài khoản trong lúc bên kia bắt đầu làm mới
            await phien.thu_hoi_tat_ca(s, "khach", khach_id)

    async def ke_lam_moi():
        await chu_giu_khoa.wait()
        async with db_that() as s, s.begin():
            return (await phien.lam_moi_phien(s, refresh_token=refresh, loai="khach")).ket_qua

    _, ket_qua = await asyncio.wait_for(asyncio.gather(chu_dat_lai_mat_khau(), ke_lam_moi()), timeout=15)
    assert ket_qua == KetQuaLamMoi.DA_THU_HOI  # token đã bị chủ thu hồi trước khi kẻ này làm mới được
    async with db_that() as s:
        assert await so_phien_con_hieu_luc(s, khach_id) == 0


async def test_lam_moi_dong_thoi_voi_dat_lai_mat_khau_khong_de_lai_phien_song(db_that):
    """Kẻ cầm token bị đánh cắp làm mới đúng lúc chủ đặt lại mật khẩu: phiên mới của kẻ đó cũng phải bị thu hồi."""
    async with db_that() as s, s.begin():
        khach_id = (await tao_khach(s)).id
        refresh = (await phien.tao_phien(s, loai="khach", chu_id=khach_id)).refresh_token

    da_xoay = asyncio.Event()

    async def ke_cap_token():
        async with db_that() as s, s.begin():
            kq = await phien.lam_moi_phien(s, refresh_token=refresh, loai="khach")
            da_xoay.set()
            await asyncio.sleep(0.4)  # giữ giao dịch mở: bên kia đang chạy đồng thời
            return kq.ket_qua

    async def chu_dat_lai_mat_khau():
        await da_xoay.wait()
        async with db_that() as s, s.begin():
            # Đúng như route đặt lại mật khẩu: khóa dòng khách rồi thu hồi mọi phiên.
            await s.execute(select(KhachHang).where(KhachHang.id == khach_id).with_for_update())
            await phien.thu_hoi_tat_ca(s, "khach", khach_id)

    ket_qua, _ = await asyncio.wait_for(asyncio.gather(ke_cap_token(), chu_dat_lai_mat_khau()), timeout=10)
    assert ket_qua == KetQuaLamMoi.OK
    async with db_that() as s:
        assert await so_phien_con_hieu_luc(s, khach_id) == 0


async def test_refresh_token_cua_nhan_vien_khong_dung_duoc_o_endpoint_khach(client, db):
    nhan_vien = await tao_nhan_vien(db)
    cap = await phien.tao_phien(db, loai="noi_bo", chu_id=nhan_vien.id)
    phan_hoi = await lam_moi(client, cap.refresh_token)
    assert phan_hoi.status_code == 401 and phan_hoi.json()["ma_loi"] == "CHUA_DANG_NHAP"
    assert (await dong_phien(db, cap.refresh_token)).thu_hoi_luc is None  # không "thu hồi nhầm" phiên nhân viên


async def test_hai_lan_lam_moi_dong_thoi_cung_mot_token_chi_mot_ben_thang(db_that):
    """Khóa dòng phiên: kẻ đến sau thấy token đã thu hồi chứ không được xoay vòng thêm lần nữa."""
    async with db_that() as s, s.begin():
        khach_id = (await tao_khach(s)).id
        refresh = (await phien.tao_phien(s, loai="khach", chu_id=khach_id)).refresh_token

    a_da_xoay = asyncio.Event()

    async def ben_a():
        async with db_that() as s, s.begin():
            ket_qua = (await phien.lam_moi_phien(s, refresh_token=refresh, loai="khach")).ket_qua
            a_da_xoay.set()
            await asyncio.sleep(0.4)  # giữ giao dịch mở: b phải chờ khóa, không được đọc bản cũ
            return ket_qua

    async def ben_b():
        await a_da_xoay.wait()
        async with db_that() as s, s.begin():
            return (await phien.lam_moi_phien(s, refresh_token=refresh, loai="khach")).ket_qua

    ket_qua_a, ket_qua_b = await asyncio.wait_for(asyncio.gather(ben_a(), ben_b()), timeout=10)
    assert (ket_qua_a, ket_qua_b) == (KetQuaLamMoi.OK, KetQuaLamMoi.DA_THU_HOI)
    async with db_that() as s:
        assert await so_phien_con_hieu_luc(s, khach_id) == 0  # dùng lại ⇒ thu hồi toàn bộ


# --- Đăng xuất ------------------------------------------------------------------------------------------------------


async def test_dang_xuat_thu_hoi_phien_va_xoa_cookie(client, db):
    await tao_khach(db, so_dien_thoai=SDT)
    refresh = await dang_nhap_lay_refresh(client)
    phan_hoi = await dang_xuat(client, refresh)
    assert phan_hoi.status_code == 204 and phan_hoi.content == b""
    cookie = dong_set_cookie(phan_hoi)
    assert cookie_refresh(phan_hoi) == "" and "Max-Age=0" in cookie and "Path=/api/v1/auth" in cookie
    assert (await dong_phien(db, refresh)).thu_hoi_luc is not None
    assert (await lam_moi(client, refresh)).status_code == 401


async def test_dang_xuat_chi_thu_hoi_dung_phien_dang_dung(client, db):
    khach = await tao_khach(db, so_dien_thoai=SDT)
    dien_thoai = await dang_nhap_lay_refresh(client)
    may_tinh = await dang_nhap_lay_refresh(client)
    await dang_xuat(client, dien_thoai)
    assert await so_phien_con_hieu_luc(db, khach.id) == 1
    assert (await lam_moi(client, may_tinh)).status_code == 200


async def test_dang_xuat_khong_co_hoac_sai_cookie_van_tra_204_va_khong_dong_den_ai(client, db):
    khach = await tao_khach(db, so_dien_thoai=SDT)
    refresh = await dang_nhap_lay_refresh(client)
    for token in (None, "", "khong-phai-token"):
        phan_hoi = await dang_xuat(client, token)
        assert phan_hoi.status_code == 204, token
    await dang_xuat(client, refresh)
    assert (await dang_xuat(client, refresh)).status_code == 204  # gọi lại vẫn ổn
    assert await so_phien_con_hieu_luc(db, khach.id) == 0


# --- Qua cookie jar như trình duyệt ---------------------------------------------------------------------------------


async def test_trinh_duyet_chi_gui_cookie_refresh_toi_duong_dan_auth(client_https, db):
    await tao_khach(db, so_dien_thoai=SDT)
    dang_nhap_ph = await dang_nhap(client_https)
    token_truy_cap = dang_nhap_ph.json()["access_token"]

    lam_moi_ph = await client_https.post("/api/v1/auth/lam-moi")  # không tự gắn gì: cookie jar lo
    assert lam_moi_ph.status_code == 200
    assert "refresh_token=" in lam_moi_ph.request.headers["cookie"]

    toi = await client_https.get("/api/v1/toi", headers={"Authorization": f"Bearer {token_truy_cap}"})
    assert toi.status_code == 200 and "cookie" not in toi.request.headers  # API thường không nhận được refresh token

    assert (await client_https.post("/api/v1/auth/dang-xuat")).status_code == 204
    assert (await client_https.post("/api/v1/auth/lam-moi")).status_code == 401  # cookie đã bị xóa khỏi jar
    assert "cookie" not in (await client_https.post("/api/v1/auth/lam-moi")).request.headers


async def test_cookie_secure_co_the_tat_cho_dev_http(client, db, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "COOKIE_SECURE", False)
    await tao_khach(db, so_dien_thoai=SDT)
    cookie = dong_set_cookie(await dang_nhap(client))
    assert "Secure" not in cookie and "HttpOnly" in cookie

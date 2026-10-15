"""KVL10: lấy lại mật khẩu bằng OTP (POST /api/v1/auth/otp muc_dich=quen_mat_khau, POST /api/v1/auth/dat-lai-mat-khau)."""

import json
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models.enums import TrangThaiTaiKhoan
from app.models.he_thong import PhienDangNhap
from app.models.khach_hang import MaOtp
from app.modules.tai_khoan.otp import bam_otp
from tests.factories import MAT_KHAU_TEST, tao_khach
from tests.tai_khoan.dung_chung import SDT, cookie_refresh, dang_nhap, lam_moi

MAT_KHAU_MOI = "Mat-khau-moi-2"


async def xin_otp(client, so_dien_thoai=SDT, kenh="sms"):
    return await client.post(
        "/api/v1/auth/otp", json={"so_dien_thoai": so_dien_thoai, "muc_dich": "quen_mat_khau", "kenh": kenh}
    )


async def dat_lai(client, so_dien_thoai=SDT, otp="000000", mat_khau_moi=MAT_KHAU_MOI):
    return await client.post(
        "/api/v1/auth/dat-lai-mat-khau",
        json={"so_dien_thoai": so_dien_thoai, "otp": otp, "mat_khau_moi": mat_khau_moi},
    )


def la_loi(phan_hoi, status, ma_loi):
    return phan_hoi.status_code == status and phan_hoi.json()["ma_loi"] == ma_loi


async def test_luong_day_du_qua_sms_doi_mat_khau_xong_dang_nhap_bang_mat_khau_moi(client, db, kenh_tin_nhan):
    khach = await tao_khach(db, so_dien_thoai=SDT)
    cu = khach.mat_khau_hash
    phan_hoi = await xin_otp(client)
    assert phan_hoi.status_code == 200 and phan_hoi.json() == {"da_gui": True, "het_han_giay": 300}
    assert kenh_tin_nhan.sms[-1][0] == SDT and kenh_tin_nhan.email == []

    ket_qua = await dat_lai(client, otp=kenh_tin_nhan.ma_otp_cuoi())
    assert ket_qua.status_code == 200 and ket_qua.json() == {"da_dat_lai": True}

    await db.refresh(khach)
    assert khach.mat_khau_hash != cu and MAT_KHAU_MOI not in khach.mat_khau_hash
    assert (await dang_nhap(client, SDT, MAT_KHAU_MOI)).status_code == 200
    assert la_loi(await dang_nhap(client, SDT, MAT_KHAU_TEST), 401, "SAI_THONG_TIN_DANG_NHAP")


async def test_so_dien_thoai_duoc_chuan_hoa_khi_dat_lai(client, db, kenh_tin_nhan):
    await tao_khach(db, so_dien_thoai=SDT)
    await xin_otp(client, "+84 912 345 678")
    assert kenh_tin_nhan.sms[-1][0] == SDT
    assert (await dat_lai(client, "0912.345.678", kenh_tin_nhan.ma_otp_cuoi())).status_code == 200


async def test_gui_ma_qua_email_khi_tai_khoan_co_email(client, db, kenh_tin_nhan):
    await tao_khach(db, so_dien_thoai=SDT, email="chu.tai.khoan@example.com")
    assert (await xin_otp(client, kenh="email")).status_code == 200
    assert kenh_tin_nhan.sms == []
    ((den, tieu_de, _),) = kenh_tin_nhan.email
    assert den == "chu.tai.khoan@example.com" and "xác thực" in tieu_de
    assert (await dat_lai(client, otp=kenh_tin_nhan.ma_otp_email_cuoi())).status_code == 200


async def test_xin_ma_qua_email_nhung_chua_co_email_thi_gui_sms(client, db, kenh_tin_nhan):
    await tao_khach(db, so_dien_thoai=SDT, email=None)
    assert (await xin_otp(client, kenh="email")).status_code == 200
    assert kenh_tin_nhan.email == [] and len(kenh_tin_nhan.sms) == 1
    assert (await dat_lai(client, otp=kenh_tin_nhan.ma_otp_cuoi())).status_code == 200


async def test_kenh_email_chi_danh_cho_lay_lai_mat_khau(client, kenh_tin_nhan):
    phan_hoi = await client.post(
        "/api/v1/auth/otp", json={"so_dien_thoai": SDT, "muc_dich": "dang_ky", "kenh": "email"}
    )
    assert phan_hoi.status_code == 400 and phan_hoi.json()["ma_loi"] == "DU_LIEU_KHONG_HOP_LE"
    assert kenh_tin_nhan.sms == [] and kenh_tin_nhan.email == []


async def test_kenh_la_bi_tu_choi(client, kenh_tin_nhan):
    phan_hoi = await xin_otp(client, kenh="zalo")
    assert phan_hoi.status_code == 400 and phan_hoi.json()["chi_tiet"][0]["truong"] == "kenh"


async def test_chong_do_tai_khoan_so_chua_dang_ky_nhan_phan_hoi_va_bo_dem_y_het(client, db, kenh_tin_nhan):
    """Số có tài khoản và số chưa có: cùng phản hồi khi xin mã và cùng chuỗi phản hồi khi nhập mã sai."""
    sdt_co, sdt_khong = "0912345678", "0987654321"
    await tao_khach(db, so_dien_thoai=sdt_co)

    xin = [await xin_otp(client, sdt) for sdt in (sdt_co, sdt_khong)]
    assert xin[0].status_code == xin[1].status_code == 200 and xin[0].json() == xin[1].json()
    ma_that = kenh_tin_nhan.sms[0][1]
    thong_bao = dict(kenh_tin_nhan.sms)
    assert any(ch.isdigit() for ch in ma_that)
    assert "chua co tai khoan" in thong_bao[sdt_khong] and not any(c.isdigit() for c in thong_bao[sdt_khong][-30:])

    cac_lan_thu = []
    for sdt in (sdt_co, sdt_khong):
        chuoi = []
        for _ in range(6):  # 5 lần sai, lần thứ 6 hết lượt
            p = await dat_lai(client, sdt, "000000")
            chuoi.append((p.status_code, json.dumps(p.json(), sort_keys=True)))
        cac_lan_thu.append(chuoi)
    assert cac_lan_thu[0] == cac_lan_thu[1]
    assert json.loads(cac_lan_thu[0][0][1])["chi_tiet"] == {"so_lan_con_lai": 4}
    assert json.loads(cac_lan_thu[0][5][1])["chi_tiet"] == {"so_lan_con_lai": 0}


async def test_het_luot_thu_thi_ma_dung_cung_khong_con_tac_dung(client, db, kenh_tin_nhan):
    khach = await tao_khach(db, so_dien_thoai=SDT)
    await xin_otp(client)
    ma = kenh_tin_nhan.ma_otp_cuoi()
    sai = "000000" if ma != "000000" else "111111"
    for _ in range(5):
        await dat_lai(client, otp=sai)
    phan_hoi = await dat_lai(client, otp=ma)
    assert la_loi(phan_hoi, 422, "OTP_SAI") and phan_hoi.json()["chi_tiet"] == {"so_lan_con_lai": 0}
    await db.refresh(khach)
    assert (await dang_nhap(client, SDT, MAT_KHAU_TEST)).status_code == 200  # mật khẩu vẫn như cũ


async def test_otp_chi_dung_mot_lan(client, db, kenh_tin_nhan):
    await tao_khach(db, so_dien_thoai=SDT)
    await xin_otp(client)
    ma = kenh_tin_nhan.ma_otp_cuoi()
    assert (await dat_lai(client, otp=ma)).status_code == 200
    assert la_loi(await dat_lai(client, otp=ma, mat_khau_moi="Ke-trom-dung-lai-3"), 422, "OTP_SAI")
    assert (await dang_nhap(client, SDT, MAT_KHAU_MOI)).status_code == 200


async def test_xin_ma_moi_vo_hieu_ma_cu(client, db, kenh_tin_nhan):
    await tao_khach(db, so_dien_thoai=SDT)
    await xin_otp(client)
    ma_cu = kenh_tin_nhan.ma_otp_cuoi()
    await xin_otp(client)
    ma_moi = kenh_tin_nhan.ma_otp_cuoi()
    if ma_cu != ma_moi:
        assert la_loi(await dat_lai(client, otp=ma_cu), 422, "OTP_SAI")
    assert (await dat_lai(client, otp=ma_moi)).status_code == 200


async def test_otp_het_han_sau_5_phut(client, db, kenh_tin_nhan, thoi_gian):
    await tao_khach(db, so_dien_thoai=SDT)
    await xin_otp(client)
    ma = kenh_tin_nhan.ma_otp_cuoi()
    thoi_gian.tien(minutes=5, seconds=1)
    assert la_loi(await dat_lai(client, otp=ma), 422, "OTP_HET_HAN")
    assert (await dang_nhap(client, SDT, MAT_KHAU_TEST)).status_code == 200


async def test_otp_dang_ky_khong_dung_duoc_de_dat_lai_mat_khau(client, db, thoi_gian):
    """OTP gắn với mục đích: mã đăng ký của số này không đổi được mật khẩu."""
    await tao_khach(db, so_dien_thoai=SDT)
    db.add(
        MaOtp(
            dich_den=SDT,
            muc_dich="dang_ky",
            ma_hash=bam_otp(SDT, "dang_ky", "123456"),
            het_han=thoi_gian.bay_gio + timedelta(minutes=5),
        )
    )
    await db.flush()
    assert la_loi(await dat_lai(client, otp="123456"), 422, "OTP_SAI")


@pytest.mark.parametrize("mat_khau", ["ngan1", "chi-co-chu-cai", "12345678901", "", "a" * 129 + "1"])
async def test_mat_khau_moi_yeu_bi_tu_choi_va_khong_tieu_ma_otp(client, db, kenh_tin_nhan, mat_khau):
    await tao_khach(db, so_dien_thoai=SDT)
    await xin_otp(client)
    ma = kenh_tin_nhan.ma_otp_cuoi()
    phan_hoi = await dat_lai(client, otp=ma, mat_khau_moi=mat_khau)
    assert phan_hoi.status_code == 400 and phan_hoi.json()["chi_tiet"][0]["truong"] == "mat_khau_moi"
    assert (await dat_lai(client, otp=ma)).status_code == 200  # mã vẫn dùng được cho mật khẩu hợp lệ


@pytest.mark.parametrize("otp", ["12345", "1234567", "abcdef", "12 456", ""])
async def test_otp_sai_dinh_dang_tra_400(client, otp):
    phan_hoi = await dat_lai(client, otp=otp)
    assert phan_hoi.status_code == 400 and phan_hoi.json()["chi_tiet"][0]["truong"] == "otp"


async def test_dat_lai_mo_khoa_tam_va_xoa_bo_dem_sai(client, db, kenh_tin_nhan, thoi_gian):
    khach = await tao_khach(
        db, so_dien_thoai=SDT, so_lan_dang_nhap_sai=3, khoa_den=thoi_gian.bay_gio + timedelta(minutes=10)
    )
    assert la_loi(await dang_nhap(client, SDT, MAT_KHAU_TEST), 403, "TAI_KHOAN_BI_KHOA")
    await xin_otp(client)
    assert (await dat_lai(client, otp=kenh_tin_nhan.ma_otp_cuoi())).status_code == 200
    await db.refresh(khach)
    assert khach.khoa_den is None and khach.so_lan_dang_nhap_sai == 0
    assert (await dang_nhap(client, SDT, MAT_KHAU_MOI)).status_code == 200


async def test_dat_lai_thu_hoi_moi_phien_dang_nhap_cua_khach_do_va_chi_khach_do(client, db, kenh_tin_nhan):
    khach = await tao_khach(db, so_dien_thoai=SDT)
    nguoi_khac = await tao_khach(db)
    phien_cu = [cookie_refresh(await dang_nhap(client)) for _ in range(2)]
    phien_khac = cookie_refresh(await dang_nhap(client, nguoi_khac.so_dien_thoai))

    await xin_otp(client)
    assert (await dat_lai(client, otp=kenh_tin_nhan.ma_otp_cuoi())).status_code == 200

    for token in phien_cu:
        assert (await lam_moi(client, token)).status_code == 401
    dong = (await db.execute(select(PhienDangNhap).where(PhienDangNhap.khach_hang_id == khach.id))).scalars().all()
    assert dong and all(d.thu_hoi_luc is not None for d in dong)
    assert (await lam_moi(client, phien_khac)).status_code == 200


async def test_dat_lai_khong_mo_khoa_tai_khoan_bi_admin_khoa(client, db, kenh_tin_nhan):
    await tao_khach(db, so_dien_thoai=SDT, trang_thai=TrangThaiTaiKhoan.bi_khoa)
    await xin_otp(client)
    assert (await dat_lai(client, otp=kenh_tin_nhan.ma_otp_cuoi())).status_code == 200
    assert la_loi(await dang_nhap(client, SDT, MAT_KHAU_MOI), 403, "TAI_KHOAN_BI_KHOA")


async def test_tai_khoan_da_xoa_mem_coi_nhu_chua_dang_ky(client, db, kenh_tin_nhan, thoi_gian):
    await tao_khach(db, so_dien_thoai=SDT, deleted_at=thoi_gian.bay_gio)
    assert (await xin_otp(client)).status_code == 200
    assert "chua co tai khoan" in kenh_tin_nhan.sms[-1][1]
    assert la_loi(await dat_lai(client, otp="123456"), 422, "OTP_SAI")


async def test_gioi_han_so_lan_xin_ma_ap_dung_rieng_cho_lay_lai_mat_khau(client, db, kenh_tin_nhan):
    await tao_khach(db, so_dien_thoai=SDT)
    for _ in range(5):
        assert (await xin_otp(client)).status_code == 200
    phan_hoi = await xin_otp(client)
    assert la_loi(phan_hoi, 429, "QUA_GIOI_HAN") and int(phan_hoi.headers["Retry-After"]) > 0


async def test_log_khong_chua_otp_hay_mat_khau(client, db, kenh_tin_nhan, bat_log):
    await tao_khach(db, so_dien_thoai=SDT)
    await xin_otp(client)
    ma = kenh_tin_nhan.ma_otp_cuoi()
    await dat_lai(client, otp=ma, mat_khau_moi=MAT_KHAU_MOI)
    await dang_nhap(client, SDT, MAT_KHAU_MOI)
    log = json.dumps(bat_log())
    assert MAT_KHAU_MOI not in log and MAT_KHAU_TEST not in log
    assert f'"{ma}"' not in log and f"OTP {ma}" not in log

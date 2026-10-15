"""KVL09: gửi OTP đăng ký (POST /api/v1/auth/otp)."""

from datetime import timedelta

import httpx
import pytest
from sqlalchemy import select, text

from app.core.bao_mat import bam_mat_khau
from app.models.khach_hang import MaOtp
from app.modules.tai_khoan.otp import bam_otp
from app.tich_hop.tin_nhan import LoiGuiTinNhan
from tests.factories import tao_khach

SDT = "0912345678"


async def xin_otp(client, so_dien_thoai=SDT, muc_dich="dang_ky"):
    return await client.post("/api/v1/auth/otp", json={"so_dien_thoai": so_dien_thoai, "muc_dich": muc_dich})


async def cac_otp(db, dich_den=SDT):
    return list((await db.execute(select(MaOtp).where(MaOtp.dich_den == dich_den).order_by(MaOtp.id))).scalars())


async def test_gui_otp_thanh_cong_luu_hash_het_han_5_phut_va_gui_sms(client, db, kenh_tin_nhan, thoi_gian):
    phan_hoi = await xin_otp(client)
    assert phan_hoi.status_code == 200
    assert phan_hoi.json() == {"da_gui": True, "het_han_giay": 300}

    (sdt, noi_dung) = kenh_tin_nhan.sms[0]
    ma = kenh_tin_nhan.ma_otp_cuoi()
    assert sdt == SDT and len(ma) == 6 and ma.isdigit()
    assert "5 phut" in noi_dung

    (otp,) = await cac_otp(db)
    assert otp.muc_dich == "dang_ky" and otp.so_lan_thu == 0 and otp.da_dung is False
    assert otp.het_han == thoi_gian.bay_gio + timedelta(minutes=5)
    assert otp.ma_hash == bam_otp(SDT, "dang_ky", ma)
    assert ma not in otp.ma_hash and ma not in str(otp.__dict__.values())  # không lưu mã thô


async def test_hash_otp_co_khoa_bi_mat_va_gan_voi_so_dien_thoai_va_muc_dich(monkeypatch):
    from pydantic import SecretStr

    from app.core.config import settings

    goc = bam_otp(SDT, "dang_ky", "123456")
    assert bam_otp(SDT, "dang_ky", "123456") == goc  # xác định
    assert bam_otp("0987654321", "dang_ky", "123456") != goc  # OTP của số này không dùng cho số khác
    assert bam_otp(SDT, "quen_mat_khau", "123456") != goc  # cũng không dùng cho mục đích khác
    monkeypatch.setattr(settings, "JWT_SECRET", SecretStr("khoa-khac-" + "z" * 40))
    assert bam_otp(SDT, "dang_ky", "123456") != goc  # hash có khóa: lộ DB không đủ để dò 10^6 mã


async def test_so_dien_thoai_duoc_chuan_hoa_truoc_khi_luu_va_gui(client, db, kenh_tin_nhan):
    assert (await xin_otp(client, "+84 912 345 678")).status_code == 200
    assert kenh_tin_nhan.sms[0][0] == SDT
    assert len(await cac_otp(db)) == 1


@pytest.mark.parametrize("sdt", ["", "123", "0212345678", "abc", "0912345678x"])
async def test_so_dien_thoai_sai_tra_400_dung_truong(client, kenh_tin_nhan, sdt):
    phan_hoi = await xin_otp(client, sdt)
    assert phan_hoi.status_code == 400 and phan_hoi.json()["ma_loi"] == "DU_LIEU_KHONG_HOP_LE"
    assert phan_hoi.json()["chi_tiet"][0]["truong"] == "so_dien_thoai"
    assert "Số điện thoại" in phan_hoi.json()["chi_tiet"][0]["loi"]
    assert kenh_tin_nhan.sms == []


@pytest.mark.parametrize("muc_dich", ["quen_mat_khau", "don_thuoc_khach", "khac", ""])
async def test_t1_1_chi_ho_tro_muc_dich_dang_ky(client, kenh_tin_nhan, muc_dich):
    phan_hoi = await xin_otp(client, muc_dich=muc_dich)
    assert phan_hoi.status_code == 400 and phan_hoi.json()["chi_tiet"][0]["truong"] == "muc_dich"
    assert kenh_tin_nhan.sms == []


async def test_gui_lai_vo_hieu_otp_cu(client, db, kenh_tin_nhan):
    await xin_otp(client)
    ma_cu = kenh_tin_nhan.ma_otp_cuoi()
    await xin_otp(client)
    ma_moi = kenh_tin_nhan.ma_otp_cuoi()
    cu, moi = await cac_otp(db)
    assert cu.da_dung is True and moi.da_dung is False  # chỉ mã mới nhất còn hiệu lực
    assert cu.ma_hash == bam_otp(SDT, "dang_ky", ma_cu) and moi.ma_hash == bam_otp(SDT, "dang_ky", ma_moi)


async def test_phan_hoi_giong_het_du_so_dien_thoai_da_dang_ky_hay_chua(client, db, kenh_tin_nhan):
    """Chống dò tài khoản (spec 06 mục 3): cùng status, cùng thân phản hồi."""
    chua_co = await xin_otp(client, "0911111111")
    await tao_khach(db, so_dien_thoai="0922222222")
    da_co = await xin_otp(client, "0922222222")
    assert (da_co.status_code, da_co.json()) == (chua_co.status_code, chua_co.json())
    assert da_co.headers["content-type"] == chua_co.headers["content-type"]


async def test_so_da_dang_ky_nhan_tin_bao_da_co_tai_khoan_va_khong_co_ma_dung_duoc(client, db, kenh_tin_nhan):
    await tao_khach(db, so_dien_thoai="0922222222")
    await xin_otp(client, "0922222222")
    (sdt, noi_dung) = kenh_tin_nhan.sms[0]
    assert sdt == "0922222222" and "da co tai khoan" in noi_dung and not any(c.isdigit() for c in noi_dung)
    (dong,) = await cac_otp(db, "0922222222")
    # Dòng giữ chỗ giống hệt OTP thật (chưa dùng, hết hạn sau 5 phút, đếm lần thử) nhưng không mã nào khớp được,
    # để hành vi quan sát từ ngoài không lộ số đã đăng ký hay chưa.
    assert dong.da_dung is False and dong.so_lan_thu == 0
    for ma in ("000000", "123456", "999999"):
        assert dong.ma_hash != bam_otp("0922222222", "dang_ky", ma)


async def test_loi_nha_cung_cap_tra_502_va_khong_de_lai_otp_hay_tinh_vao_gioi_han(client, db, kenh_tin_nhan):
    kenh_tin_nhan.loi = LoiGuiTinNhan("nhà cung cấp lỗi")
    phan_hoi = await xin_otp(client)
    assert phan_hoi.status_code == 502 and phan_hoi.json()["ma_loi"] == "LOI_DOI_TAC"
    assert "nhà cung cấp lỗi" not in phan_hoi.text  # không lộ chi tiết nội bộ
    assert await cac_otp(db) == []  # rollback: không có OTP nào không ai nhận được


# --- Giới hạn tần suất ------------------------------------------------------------------------------------------------


async def test_gioi_han_theo_so_dien_thoai_5_lan_moi_gio_roi_cho_het_cua_so(client, db, kenh_tin_nhan, thoi_gian):
    for _ in range(5):
        assert (await xin_otp(client)).status_code == 200
        thoi_gian.tien(minutes=1)
    phan_hoi = await xin_otp(client)
    assert phan_hoi.status_code == 429 and phan_hoi.json()["ma_loi"] == "QUA_GIOI_HAN"
    assert int(phan_hoi.headers["Retry-After"]) == 55 * 60  # lượt đầu cách đây 5 phút, hết hạn sau 55 phút nữa
    assert len(kenh_tin_nhan.sms) == 5  # lượt bị chặn không gửi SMS

    assert (await xin_otp(client, "0987654321")).status_code == 200  # số khác không bị ảnh hưởng

    thoi_gian.tien(minutes=55, seconds=1)
    assert (await xin_otp(client)).status_code == 200  # hết cửa sổ thì gửi lại được


async def test_gioi_han_doc_tu_cau_hinh_va_ap_dung_ngay(client, db, kenh_tin_nhan):
    await db.execute(
        text(
            "UPDATE cau_hinh SET gia_tri = '{\"moi_sdt_moi_gio\": 2, \"moi_ip_moi_gio\": 20}' WHERE khoa = 'gioi_han_otp'"
        )
    )
    assert [(await xin_otp(client)).status_code for _ in range(3)] == [200, 200, 429]


async def test_so_da_dang_ky_cung_bi_tinh_gioi_han_de_khong_bi_dung_lam_may_gui_sms(client, db, kenh_tin_nhan):
    await tao_khach(db, so_dien_thoai="0922222222")
    ket_qua = [(await xin_otp(client, "0922222222")).status_code for _ in range(6)]
    assert ket_qua == [200] * 5 + [429]
    assert len(kenh_tin_nhan.sms) == 5


async def test_gioi_han_theo_ip_chan_nhieu_so_khac_nhau_tu_cung_may(app, client, db, kenh_tin_nhan):
    await db.execute(
        text(
            "UPDATE cau_hinh SET gia_tri = '{\"moi_sdt_moi_gio\": 5, \"moi_ip_moi_gio\": 3}' WHERE khoa = 'gioi_han_otp'"
        )
    )
    so = [f"09123456{n:02d}" for n in range(10, 15)]
    trang_thai = [(await xin_otp(client, s)).status_code for s in so[:4]]
    assert trang_thai == [200, 200, 200, 429]
    phan_hoi = await xin_otp(client, so[4])
    assert phan_hoi.status_code == 429 and int(phan_hoi.headers["Retry-After"]) > 0

    may_khac = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=("10.9.9.9", 5000)), base_url="http://test"
    )
    async with may_khac:
        assert (await xin_otp(may_khac, so[4])).status_code == 200  # IP khác không bị chặn


async def test_nhieu_lan_thu_voi_so_dien_thoai_sai_dinh_dang_khong_ton_luot_gioi_han(client):
    for _ in range(30):
        assert (await xin_otp(client, "abc")).status_code == 400
    assert (await xin_otp(client)).status_code == 200


def test_bam_mat_khau_khong_dung_cho_otp():
    """Hash OTP là HMAC nhanh có khóa, không phải Argon2 (mã 6 số chỉ sống 5 phút; Argon2 chỉ làm chậm server)."""
    assert not bam_otp(SDT, "dang_ky", "123456").startswith("$argon2")
    assert bam_mat_khau("123456").startswith("$argon2")

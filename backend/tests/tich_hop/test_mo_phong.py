"""Máy chủ mô phỏng VNPay, MoMo, GHN (chế độ `mo_phong`, spec 08 mục 4b, QĐ-56).

Adapter thật chạy nguyên vẹn; chỉ địa chỉ đối tác là máy chủ mô phỏng trong ứng dụng. Test đi từ đầu đến cuối: tạo giao
dịch, khách thao tác trên trang đối tác, IPN server-to-server, ReturnUrl có chữ ký, hoàn tiền qua API đối tác, vận đơn.
"""

import re
from decimal import Decimal
from urllib.parse import parse_qsl, urlsplit

import pytest
from sqlalchemy import select

from app.core import idempotency
from app.core.config import Settings, settings
from app.models.ban_hang import DonHang, ThanhToan, VanDon
from app.tich_hop import cau_hinh
from app.tich_hop.thanh_toan import momo as momo_adapter
from app.tich_hop.thanh_toan import vnpay as vnpay_adapter
from app.tich_hop.thanh_toan.momo import CongMomo
from app.tich_hop.thanh_toan.vnpay import CongVnpay, ky_chuoi_gach_doc
from tests.ban_hang.test_dat_hang import DON
from tests.thanh_toan.test_thanh_toan import dat_online, lay_gd, tao_gd

MP = "/api/v1/mo-phong"


@pytest.fixture
def mo_phong(monkeypatch):
    """Phải đứng TRƯỚC `app`/`dang_nhap_*` trong danh sách tham số để route mô phỏng được gắn."""
    idempotency.quen_het()
    monkeypatch.setattr(settings, "THANH_TOAN_CHE_DO", "mo_phong")
    monkeypatch.setattr(settings, "VAN_CHUYEN_CHE_DO", "mo_phong")
    for ten in (
        "VNPAY_TMN_CODE",
        "VNPAY_URL",
        "VNPAY_RETURN_URL",
        "VNPAY_API_URL",
        "MOMO_PARTNER_CODE",
        "MOMO_ACCESS_KEY",
    ):
        monkeypatch.setattr(settings, ten, "")
    for ten in ("MOMO_ENDPOINT", "MOMO_REFUND_ENDPOINT", "MOMO_RETURN_URL", "MOMO_IPN_URL", "GHN_URL", "GHN_SHOP_ID"):
        monkeypatch.setattr(settings, ten, "")
    for ten in ("VNPAY_HASH_SECRET", "MOMO_SECRET_KEY", "GHN_TOKEN", "GHN_WEBHOOK_TOKEN"):
        monkeypatch.setattr(settings, ten, type(settings.JWT_SECRET)(""))


def _query_vnpay(url: str) -> str:
    return urlsplit(url).query


async def _vnpay_di_den_trang_mo_phong(client, url: str):
    """Trình duyệt mở URL thanh toán: máy chủ VNPay mô phỏng kiểm chữ ký rồi chuyển sang trang mô phỏng."""
    r = await client.get(urlsplit(url).path + "?" + _query_vnpay(url), follow_redirects=False)
    return r


async def _thanh_toan_vnpay(client, url: str, ket_qua: str = "thanh_cong"):
    return await client.post(f"{MP}/vnpay/thanh-toan", json={"query": _query_vnpay(url), "ket_qua": ket_qua})


# --- VNPay ---


async def test_vnpay_mo_phong_luong_day_du_ipn_server_to_server_va_return_url_co_chu_ky(
    mo_phong, dang_nhap_khach, client, db
):
    c = dang_nhap_khach
    _, o = await dat_online(c, db, "vnpay")
    url = (await tao_gd(c, o["ma_don"])).json()["url_thanh_toan"]
    assert url.startswith(f"{settings.FRONTEND_URL}/api/v1/mo-phong/vnpay/vpcpay.html?")
    r = await _vnpay_di_den_trang_mo_phong(client, url)
    assert r.status_code == 307 and "/thanh-toan-gia?cong=vnpay&vnp_Amount=" in r.headers["location"]

    tt = (await client.get(f"{MP}/vnpay/giao-dich?{_query_vnpay(url)}")).json()
    assert (tt["cong"], tt["ma_don"], tt["so_tien"], tt["trang_thai"]) == (
        "vnpay",
        o["ma_don"],
        int(Decimal(o["tong_tien"])),
        "khoi_tao",
    )
    assert tt["het_han_luc"] and tt["noi_dung"].startswith("Thanh toan don hang")

    kq = (await _thanh_toan_vnpay(client, url)).json()
    assert kq["thanh_cong"] is True and kq["ma_phan_hoi"] == "00"  # RspCode cửa hàng trả cho IPN
    tham_so = dict(parse_qsl(urlsplit(kq["redirect_url"]).query))
    assert kq["redirect_url"].startswith(cau_hinh.vnpay_return_url())
    assert tham_so["vnp_ResponseCode"] == "00" and tham_so["vnp_TransactionStatus"] == "00"
    assert tham_so["vnp_SecureHash"] == vnpay_adapter.ky(
        tham_so, cau_hinh.vnpay_hash_secret()
    )  # ReturnUrl có chữ ký thật

    don = await db.scalar(select(DonHang).where(DonHang.ma_don == o["ma_don"]))
    gd = await lay_gd(db, o["ma_don"])
    await db.refresh(don)
    await db.refresh(gd)
    assert (don.trang_thai, don.trang_thai_tt, gd.trang_thai) == ("cho_xac_nhan", "da_thanh_toan", "thanh_cong")
    assert gd.ma_giao_dich_cong == tham_so["vnp_TransactionNo"] and gd.du_lieu_ipn["vnp_PayDate"]
    # Khách thanh toán lại cùng giao dịch: cổng mô phỏng báo đã xử lý, không đổi gì
    sau = (await client.get(f"{MP}/vnpay/giao-dich?{_query_vnpay(url)}")).json()
    assert sau["trang_thai"] == "thanh_cong"


async def test_vnpay_mo_phong_tu_choi_url_sai_chu_ky_hoac_bi_sua_so_tien(mo_phong, dang_nhap_khach, client, db):
    c = dang_nhap_khach
    _, o = await dat_online(c, db, "vnpay")
    url = (await tao_gd(c, o["ma_don"])).json()["url_thanh_toan"]
    q = _query_vnpay(url)
    sua = re.sub(r"vnp_Amount=\d+", "vnp_Amount=100", q)  # khách sửa số tiền trên URL
    r = await client.get(f"{urlsplit(url).path}?{sua}", follow_redirects=False)
    assert r.status_code == 400 and "70" in r.text and "Sai chữ ký" in r.text
    assert (await client.get(f"{MP}/vnpay/giao-dich?{sua}")).status_code == 400
    assert (
        await client.post(f"{MP}/vnpay/thanh-toan", json={"query": sua, "ket_qua": "thanh_cong"})
    ).status_code == 400
    gd = await lay_gd(db, o["ma_don"])
    assert gd.trang_thai == "khoi_tao"  # không có IPN nào được gửi


@pytest.mark.parametrize(
    ("ket_qua", "ma_vnp"),
    [("khach_huy", "24"), ("khong_du_so_du", "51"), ("het_han", "11"), ("sai_otp", "13"), ("the_chua_dang_ky", "09")],
)
async def test_vnpay_mo_phong_that_bai_thi_don_van_cho_thanh_toan_va_thanh_toan_lai_duoc(
    mo_phong, dang_nhap_khach, client, db, ket_qua, ma_vnp
):
    c = dang_nhap_khach
    _, o = await dat_online(c, db, "vnpay")
    url = (await tao_gd(c, o["ma_don"])).json()["url_thanh_toan"]
    kq = (await _thanh_toan_vnpay(client, url, ket_qua)).json()
    assert kq["thanh_cong"] is False
    assert dict(parse_qsl(urlsplit(kq["redirect_url"]).query))["vnp_ResponseCode"] == ma_vnp
    gd = await lay_gd(db, o["ma_don"])
    await db.refresh(gd)
    assert gd.trang_thai == "that_bai"
    assert (await c.get(f"{DON}/{o['ma_don']}")).json()["trang_thai"] == "cho_thanh_toan"
    moi = await tao_gd(c, o["ma_don"])  # thanh toán lại: giao dịch mới vì giao dịch cũ đã thất bại
    assert moi.status_code == 200 and moi.json()["url_thanh_toan"] != url


async def _tra_vnpay_va_huy_don(c, client, db, dang_nhap_admin):
    _, o = await dat_online(c, db, "vnpay")
    url = (await tao_gd(c, o["ma_don"])).json()["url_thanh_toan"]
    assert (await _thanh_toan_vnpay(client, url)).json()["thanh_cong"] is True
    assert (await c.post(f"{DON}/{o['ma_don']}/huy", json={})).status_code == 200
    hoan = (await db.execute(select(ThanhToan).where(ThanhToan.loai == "hoan_tien"))).scalars().one()
    return o, hoan


async def test_vnpay_mo_phong_hoan_tien_qua_api_doi_tac_ky_dung_va_chi_hoan_mot_lan(
    mo_phong, dang_nhap_khach, dang_nhap_admin, client, db
):
    o, hoan = await _tra_vnpay_va_huy_don(dang_nhap_khach, client, db, dang_nhap_admin)
    assert hoan.trang_thai == "khoi_tao"
    r = await dang_nhap_admin.post(f"/api/v1/noi-bo/hoan-tien/{hoan.id}/xac-nhan")
    assert r.status_code == 200, r.text
    await db.refresh(hoan)
    don = await db.scalar(select(DonHang).where(DonHang.ma_don == o["ma_don"]))
    await db.refresh(don)
    assert hoan.trang_thai == "thanh_cong" and re.fullmatch(r"HOAN-\d{8}", hoan.ma_giao_dich_cong)
    assert don.trang_thai_tt == "da_hoan_tien"
    # Gọi lại API hoàn của VNPay với cùng vnp_RequestId: cùng mã giao dịch hoàn (cổng không hoàn hai lần)
    goc = await lay_gd(db, o["ma_don"])
    lan2 = await CongVnpay().hoan_tien(goc, hoan.so_tien, "gọi lại", ma_yeu_cau=f"HT{hoan.id}")
    assert lan2.ma_giao_dich_cong == hoan.ma_giao_dich_cong


async def test_vnpay_mo_phong_hoan_tien_sai_se_bi_doi_tac_tu_choi(
    mo_phong, dang_nhap_khach, dang_nhap_admin, client, db
):
    c = dang_nhap_khach
    _, o = await dat_online(c, db, "vnpay")
    url = (await tao_gd(c, o["ma_don"])).json()["url_thanh_toan"]
    await _thanh_toan_vnpay(client, url)
    goc = await lay_gd(db, o["ma_don"])
    await db.refresh(goc)
    # Hoàn vượt số đã trả: mã 93
    qua = await CongVnpay().hoan_tien(goc, goc.so_tien + 1000, "x", ma_yeu_cau="HTA")
    assert qua.thanh_cong is False and qua.thong_diep.startswith("93")
    # Giao dịch không tồn tại trên cổng (mã giao dịch gốc lạ): mã 91
    goc.ma_giao_dich_cong = "99999999"
    la = await CongVnpay().hoan_tien(goc, goc.so_tien, "x", ma_yeu_cau="HTB")
    assert la.thanh_cong is False and la.thong_diep.startswith("91")


async def test_vnpay_mo_phong_api_hoan_tien_kiem_chu_ky_cua_cua_hang(mo_phong, client):
    yeu_cau = {
        "vnp_RequestId": "R1",
        "vnp_Version": "2.1.0",
        "vnp_Command": "refund",
        "vnp_TmnCode": cau_hinh.vnpay_tmn_code(),
    }
    yeu_cau["vnp_SecureHash"] = "sai"
    r = await client.post(f"{MP}/vnpay/merchant_webapi/api/transaction", json=yeu_cau)
    assert r.json()["vnp_ResponseCode"] == "97"
    # Phản hồi của VNPay luôn có chữ ký để cửa hàng kiểm
    phan_hoi = r.json()
    assert phan_hoi["vnp_SecureHash"] == ky_chuoi_gach_doc(
        phan_hoi, vnpay_adapter.TRUONG_PHAN_HOI_HOAN, cau_hinh.vnpay_hash_secret()
    )


# --- MoMo ---


async def _tao_momo(c, db):
    _, o = await dat_online(c, db, "momo")
    r = await tao_gd(c, o["ma_don"])
    assert r.status_code == 200, r.text
    return o, r.json()["url_thanh_toan"]


async def test_momo_mo_phong_tao_giao_dich_ky_dung_ipn_204_va_redirect_url_co_chu_ky(
    mo_phong, dang_nhap_khach, client, db
):
    c = dang_nhap_khach
    o, pay_url = await _tao_momo(c, db)
    assert pay_url.startswith(f"{settings.FRONTEND_URL}/thanh-toan-gia?cong=momo&token=")
    token = dict(parse_qsl(urlsplit(pay_url).query))["token"]
    tt = (await client.get(f"{MP}/momo/giao-dich", params={"token": token})).json()
    assert (tt["cong"], tt["ma_don"], tt["trang_thai"]) == ("momo", o["ma_don"], "khoi_tao")
    kq = (await client.post(f"{MP}/momo/thanh-toan", json={"token": token, "ket_qua": "thanh_cong"})).json()
    assert kq["thanh_cong"] is True and kq["ma_phan_hoi"] == "204"  # MoMo yêu cầu cửa hàng trả HTTP 204 cho IPN
    tham_so = dict(parse_qsl(urlsplit(kq["redirect_url"]).query))
    assert tham_so["resultCode"] == "0" and tham_so["orderId"].startswith(o["ma_don"])
    day_du = {**tham_so, "accessKey": cau_hinh.momo_access_key()}
    assert tham_so["signature"] == momo_adapter.ky(day_du, momo_adapter.TRUONG_IPN, cau_hinh.momo_secret_key())
    don = await db.scalar(select(DonHang).where(DonHang.ma_don == o["ma_don"]))
    await db.refresh(don)
    assert (don.trang_thai, don.trang_thai_tt) == ("cho_xac_nhan", "da_thanh_toan")


async def test_momo_mo_phong_khach_tu_choi_thi_giao_dich_that_bai(mo_phong, dang_nhap_khach, client, db):
    c = dang_nhap_khach
    o, pay_url = await _tao_momo(c, db)
    token = dict(parse_qsl(urlsplit(pay_url).query))["token"]
    kq = (await client.post(f"{MP}/momo/thanh-toan", json={"token": token, "ket_qua": "tu_choi"})).json()
    assert kq["thanh_cong"] is False and dict(parse_qsl(urlsplit(kq["redirect_url"]).query))["resultCode"] == "1006"
    assert (await lay_gd(db, o["ma_don"])).trang_thai == "that_bai"
    assert (
        await client.post(f"{MP}/momo/thanh-toan", json={"token": token + "x", "ket_qua": "thanh_cong"})
    ).status_code == 400


async def test_momo_mo_phong_tao_giao_dich_sai_chu_ky_hoac_so_tien_ngoai_gioi_han(mo_phong, client):
    yc = {
        "partnerCode": cau_hinh.momo_partner_code(), "orderId": "A-1", "requestId": "r", "amount": 500, "orderInfo": "x",
        "redirectUrl": "http://x", "ipnUrl": "http://x", "requestType": "captureWallet", "extraData": "",
    }  # fmt: skip
    ky = momo_adapter.ky(
        {**yc, "accessKey": cau_hinh.momo_access_key()}, momo_adapter.TRUONG_TAO, cau_hinh.momo_secret_key()
    )
    r = await client.post(f"{MP}/momo/v2/gateway/api/create", json={**yc, "signature": ky})
    assert r.json()["resultCode"] == 22  # dưới 1.000 ₫
    r = await client.post(f"{MP}/momo/v2/gateway/api/create", json={**yc, "amount": 5000, "signature": ky})
    assert r.json()["resultCode"] == 13  # sai chữ ký (đã đổi số tiền sau khi ký)


async def test_momo_mo_phong_hoan_tien_qua_api_refund(mo_phong, dang_nhap_khach, dang_nhap_admin, client, db):
    c = dang_nhap_khach
    o, pay_url = await _tao_momo(c, db)
    token = dict(parse_qsl(urlsplit(pay_url).query))["token"]
    await client.post(f"{MP}/momo/thanh-toan", json={"token": token, "ket_qua": "thanh_cong"})
    assert (await c.post(f"{DON}/{o['ma_don']}/huy", json={})).status_code == 200
    hoan = (await db.execute(select(ThanhToan).where(ThanhToan.loai == "hoan_tien"))).scalars().one()
    r = await dang_nhap_admin.post(f"/api/v1/noi-bo/hoan-tien/{hoan.id}/xac-nhan")
    assert r.status_code == 200, r.text
    await db.refresh(hoan)
    assert hoan.trang_thai == "thanh_cong" and hoan.ma_giao_dich_cong.startswith("HOAN-")
    goc = await lay_gd(db, o["ma_don"])
    qua = await CongMomo().hoan_tien(goc, goc.so_tien, "x", ma_yeu_cau="HTX")  # đã hoàn hết, hoàn nữa bị từ chối
    assert qua.thanh_cong is False and qua.thong_diep.startswith("22")


# --- GHN ---


async def _don_cho_lay_hang(khach, duoc_si, kho, db):
    from tests.ban_hang.test_soan_hang import don_dang_soan

    _, o, don = await don_dang_soan(khach, duoc_si, kho, db)
    assert (await kho.post(f"/api/v1/noi-bo/soan-hang/{don.id}/dong-goi")).status_code == 200
    return o, don


async def test_ghn_mo_phong_tao_van_don_dung_giao_thuc_va_phat_webhook_doi_trang_thai(
    mo_phong, dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, client, db
):
    o, don = await _don_cho_lay_hang(dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, db)
    (vd,) = (await db.execute(select(VanDon).where(VanDon.don_hang_id == don.id))).scalars().all()
    assert vd.don_vi_van_chuyen == "GHN" and re.fullmatch(r"[A-Z2-9]{8}", vd.ma_van_don) and vd.phi > 0
    r = await client.post(f"{MP}/ghn/phat-su-kien", json={"order_code": vd.ma_van_don, "status": "picked"})
    assert (
        r.status_code == 200 and r.json()["ma_phan_hoi"] == 200 and r.json()["than"]["ClientOrderCode"] == o["ma_don"]
    )
    await db.refresh(don)
    assert don.trang_thai == "dang_giao"
    await client.post(f"{MP}/ghn/phat-su-kien", json={"order_code": vd.ma_van_don, "status": "delivered"})
    await db.refresh(don)
    assert don.trang_thai == "da_giao"


async def test_ghn_mo_phong_huy_don_cho_lay_hang_huy_van_don_tai_ghn(
    mo_phong, dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, db
):
    o, don = await _don_cho_lay_hang(dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, db)
    r = await dang_nhap_duoc_si.post(f"/api/v1/noi-bo/don-hang/{don.id}/huy", json={"ly_do": "Khách đổi ý"})
    assert r.status_code == 200, r.text
    (vd,) = (await db.execute(select(VanDon).where(VanDon.don_hang_id == don.id))).scalars().all()
    assert vd.trang_thai_doi_tac == "cancel"


async def test_ghn_mo_phong_van_don_da_lay_hang_thi_ghn_tu_choi_huy_va_don_khong_bi_huy(
    mo_phong, dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, client, db
):
    o, don = await _don_cho_lay_hang(dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, db)
    (vd,) = (await db.execute(select(VanDon).where(VanDon.don_hang_id == don.id))).scalars().all()
    vd.trang_thai_doi_tac = "picked"  # GHN đã lấy hàng nhưng webhook về cửa hàng chưa tới: đơn còn ở "chờ lấy hàng"
    await db.flush()
    r = await dang_nhap_duoc_si.post(f"/api/v1/noi-bo/don-hang/{don.id}/huy", json={"ly_do": "Khách đổi ý"})
    assert (r.status_code, r.json().get("ma_loi")) == (502, "LOI_DOI_TAC"), r.text
    await db.refresh(don)
    assert don.trang_thai == "cho_lay_hang"


async def test_ghn_mo_phong_tieu_de_xac_thuc_va_kiem_tra_du_lieu(mo_phong, client):
    tieu_de = {"Token": cau_hinh.ghn_token(), "ShopId": cau_hinh.ghn_shop_id()}
    fee = "/api/v1/mo-phong/ghn/shiip/public-api/v2/shipping-order/fee"
    assert (await client.post(fee, json={"weight": 500, "to_ward_code": "1"})).status_code == 401  # thiếu Token
    ok = await client.post(fee, json={"weight": 1500, "to_ward_code": "1"}, headers=tieu_de)
    assert ok.json()["data"]["total"] == 30_000  # 25.000 cho kg đầu + 5.000 cho kg thứ hai
    tao = "/api/v1/mo-phong/ghn/shiip/public-api/v2/shipping-order/create"
    r = await client.post(tao, json={"payment_type_id": 2, "required_note": "SAI"}, headers=tieu_de)
    assert r.status_code == 400 and "required_note" in r.json()["message"]


async def test_webhook_ghn_cua_cua_hang_tu_choi_sai_token(mo_phong, client):
    r = await client.post(
        "/api/v1/webhook/ghn", json={"OrderCode": "ABCDEFGH", "Status": "picked"}, headers={"Token": "sai"}
    )
    assert r.status_code in (401, 403)


# --- cấu hình ---


def test_production_tu_choi_che_do_mo_phong():
    from pydantic import SecretStr

    cb = dict(
        _env_file=None, MOI_TRUONG="production", JWT_SECRET=SecretStr("k" * 40), KHOA_MA_HOA=SecretStr("f" * 44),
        COOKIE_SECURE=True, VNPAY_HASH_SECRET=SecretStr("a"), MOMO_SECRET_KEY=SecretStr("b"),
        GHN_WEBHOOK_TOKEN=SecretStr("t"), TIN_NHAN_CHE_DO="that", AI_GIA_LAP=False,
    )  # fmt: skip
    loi = Settings(**cb, THANH_TOAN_CHE_DO="mo_phong", VAN_CHUYEN_CHE_DO="mo_phong").kiem_tra_san_xuat()
    assert any("THANH_TOAN_CHE_DO=mo_phong" in x for x in loi) and any("VAN_CHUYEN_CHE_DO=mo_phong" in x for x in loi)


def test_che_do_sandbox_khong_bao_gio_roi_ve_khoa_mo_phong(monkeypatch):
    monkeypatch.setattr(settings, "THANH_TOAN_CHE_DO", "sandbox")
    monkeypatch.setattr(settings, "VNPAY_TMN_CODE", "")
    assert cau_hinh.vnpay_tmn_code() == ""  # thiếu cấu hình là lỗi cấu hình, không âm thầm dùng khóa mô phỏng
    monkeypatch.setattr(settings, "THANH_TOAN_CHE_DO", "mo_phong")
    assert cau_hinh.vnpay_tmn_code() == "MOPHONG1"

"""KTV03, HT04, HT03: thanh toán online, IPN (VNPay, MoMo, cổng giả) và hủy đơn quá hạn."""

import asyncio
import uuid
from datetime import timedelta
from decimal import Decimal
from urllib.parse import parse_qsl, urlsplit

import httpx
import pytest
from sqlalchemy import func, select

from app.core import idempotency
from app.core.config import settings
from app.core.thoi_gian import bay_gio_utc
from app.models.ban_hang import DonHang, LichSuTrangThai, ThanhToan
from app.models.khach_hang import DiaChi
from app.models.kho import LoThuoc
from app.modules.ban_hang.het_han import huy_don_qua_han
from app.tich_hop.thanh_toan import vnpay
from app.tich_hop.thanh_toan.gia import dung_ipn
from app.tich_hop.thanh_toan.momo import TRUONG_IPN
from app.tich_hop.thanh_toan.momo import ky as ky_momo
from tests.ban_hang.test_dat_hang import DON, dia_chi, khoa, sp_ban, them, thân
from tests.conftest import tao_access_token
from tests.factories import tao_khach, tao_nhan_vien
from tests.khuyen_mai.test_khuyen_mai import tao_km

VNPAY_IPN = "/api/v1/webhook/vnpay-ipn"
MOMO_IPN = "/api/v1/webhook/momo-ipn"
GIA_IPN = "/api/v1/webhook/gia-ipn"
GIA_GD = "/api/v1/webhook/gia-giao-dich"


@pytest.fixture(autouse=True)
def _cau_hinh(monkeypatch):
    idempotency.quen_het()
    monkeypatch.setattr(settings, "THANH_TOAN_CHE_DO", "sandbox")
    monkeypatch.setattr(settings, "VNPAY_TMN_CODE", "TMNTEST")
    monkeypatch.setattr(settings, "VNPAY_HASH_SECRET", type(settings.JWT_SECRET)("khoa-vnpay-test"))
    monkeypatch.setattr(settings, "VNPAY_URL", "https://sandbox.vnpay.test/pay")
    monkeypatch.setattr(settings, "VNPAY_RETURN_URL", "http://localhost:5173/thanh-toan/ket-qua")
    monkeypatch.setattr(settings, "MOMO_ACCESS_KEY", "accesskey")
    monkeypatch.setattr(settings, "MOMO_SECRET_KEY", type(settings.JWT_SECRET)("khoa-momo-test"))
    monkeypatch.setattr(settings, "MOMO_PARTNER_CODE", "MOMOTEST")


async def _client_cua(app, khach):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tao_access_token(khach.id, 'khach')}"},
    )


@pytest.fixture
def cong_gia(monkeypatch):
    """Phải đứng TRƯỚC `app`/`dang_nhap_khach` trong danh sách tham số để route cổng giả được gắn."""
    monkeypatch.setattr(settings, "THANH_TOAN_CHE_DO", "gia")


def che_do(monkeypatch, gia_tri: str):
    monkeypatch.setattr(settings, "THANH_TOAN_CHE_DO", gia_tri)


async def dat_online(c, db, cong="vnpay", ma_giam_gia=None, so_luong=10):
    kh = c.tai_khoan
    sp = await sp_ban(db)
    d = await db.scalar(select(DiaChi).where(DiaChi.khach_hang_id == kh.id)) or await dia_chi(db, kh)
    await them(c, sp, "viên", so_luong)
    r = await c.post(
        DON, json=thân(d, phuong_thuc_tt=cong, **({"ma_giam_gia": ma_giam_gia} if ma_giam_gia else {})), headers=khoa()
    )
    assert r.status_code == 201, r.text
    return sp, r.json()


async def tao_gd(c, ma_don, key=None):
    return await c.post(f"{DON}/{ma_don}/thanh-toan", headers={"Idempotency-Key": key or str(uuid.uuid4())})


async def lay_gd(db, ma_don) -> ThanhToan:
    return (
        await db.execute(
            select(ThanhToan).join(DonHang).where(DonHang.ma_don == ma_don, ThanhToan.loai == "thanh_toan")
            .order_by(ThanhToan.id.desc())
        )
    ).scalars().first()  # fmt: skip


def ipn_vnpay(ref, so_tien, ok=True, ma_gd="14000001", **ghi_de):
    tham_so = {
        "vnp_TmnCode": "TMNTEST", "vnp_Amount": str(int(so_tien) * 100), "vnp_TxnRef": ref,
        "vnp_TransactionNo": ma_gd, "vnp_ResponseCode": "00" if ok else "24",
        "vnp_TransactionStatus": "00" if ok else "02", "vnp_PayDate": "20261016100000", **ghi_de,
    }  # fmt: skip
    tham_so["vnp_SecureHash"] = vnpay.ky(tham_so, "khoa-vnpay-test")
    return tham_so


def ipn_momo(ref, so_tien, ok=True, trans_id=777001):
    tham_so = {
        "partnerCode": "MOMOTEST", "orderId": ref, "requestId": "r1", "amount": int(so_tien), "orderInfo": "x",
        "orderType": "momo_wallet", "transId": trans_id, "resultCode": 0 if ok else 1006, "message": "ok",
        "payType": "qr", "responseTime": 1700000000, "extraData": "",
    }  # fmt: skip
    tham_so["signature"] = ky_momo({**tham_so, "accessKey": "accesskey"}, TRUONG_IPN, "khoa-momo-test")
    return tham_so


# --- Tạo giao dịch (KTV03) ---


async def test_tao_giao_dich_vnpay_url_ky_dung_va_idempotent(dang_nhap_khach, db):
    c = dang_nhap_khach
    _, o = await dat_online(c, db)
    k = str(uuid.uuid4())
    r1 = await tao_gd(c, o["ma_don"], k)
    assert r1.status_code == 200, r1.text
    url = r1.json()["url_thanh_toan"]
    tham_so = dict(parse_qsl(urlsplit(url).query))
    gd = await lay_gd(db, o["ma_don"])
    assert url.startswith("https://sandbox.vnpay.test/pay?")
    assert tham_so["vnp_TxnRef"] == f"{o['ma_don']}-{gd.id}"
    assert tham_so["vnp_Amount"] == str(int(Decimal(o["tong_tien"])) * 100)
    assert tham_so["vnp_SecureHash"] == vnpay.ky(tham_so, "khoa-vnpay-test")
    assert (gd.trang_thai, gd.cong_thanh_toan, gd.so_tien) == ("khoi_tao", "vnpay", Decimal(o["tong_tien"]))
    r2 = await tao_gd(c, o["ma_don"], k)  # cùng khóa: URL cũ, không giao dịch mới
    assert r2.json() == r1.json()
    assert await db.scalar(select(func.count()).select_from(ThanhToan)) == 1
    r3 = await tao_gd(c, o["ma_don"])  # khóa mới: thanh toán lại
    assert r3.json()["url_thanh_toan"] != url and await db.scalar(select(func.count()).select_from(ThanhToan)) == 2


async def test_tao_giao_dich_dieu_kien_va_quyen(dang_nhap_khach, db, client):
    c = dang_nhap_khach
    _, o = await dat_online(c, db)
    assert (await c.post(f"{DON}/{o['ma_don']}/thanh-toan")).status_code == 400  # thiếu Idempotency-Key
    assert (await tao_gd(c, "DHKHONGCO1")).status_code == 404
    assert (await client.post(f"{DON}/{o['ma_don']}/thanh-toan")).status_code == 401
    don = await db.scalar(select(DonHang).where(DonHang.ma_don == o["ma_don"]))
    don.han_thanh_toan = bay_gio_utc() - timedelta(minutes=1)
    await db.flush()
    r = await tao_gd(c, o["ma_don"])
    assert (r.status_code, r.json()["ma_loi"]) == (409, "CHUYEN_TRANG_THAI_KHONG_HOP_LE")


async def test_don_cod_va_don_cua_nguoi_khac_khong_thanh_toan_duoc(dang_nhap_khach, app, db):
    c = dang_nhap_khach
    khac = await _client_cua(app, await tao_khach(db))
    sp = await sp_ban(db)
    d = await dia_chi(db, c.tai_khoan)
    await them(c, sp, "viên", 3)
    cod = (await c.post(DON, json=thân(d), headers=khoa())).json()
    assert (await tao_gd(c, cod["ma_don"])).status_code == 409
    _, online = await dat_online(c, db)
    assert (await tao_gd(khac, online["ma_don"])).status_code == 404


# --- IPN VNPay ---


async def test_ipn_vnpay_thanh_cong_chuyen_cho_xac_nhan_va_dung_dinh_dang(dang_nhap_khach, client, db):
    c = dang_nhap_khach
    _, o = await dat_online(c, db)
    await tao_gd(c, o["ma_don"])
    gd = await lay_gd(db, o["ma_don"])
    ref = f"{o['ma_don']}-{gd.id}"
    r = await client.get(VNPAY_IPN, params=ipn_vnpay(ref, Decimal(o["tong_tien"])))
    assert (r.status_code, r.json()) == (200, {"RspCode": "00", "Message": "Confirm Success"})
    await db.refresh(gd)
    don = await db.scalar(select(DonHang).where(DonHang.ma_don == o["ma_don"]))
    await db.refresh(don)
    assert (gd.trang_thai, gd.ma_giao_dich_cong) == ("thanh_cong", "14000001")
    assert "vnp_SecureHash" not in gd.du_lieu_ipn
    assert (don.trang_thai, don.trang_thai_tt) == ("cho_xac_nhan", "da_thanh_toan")
    ls = (
        (
            await db.execute(
                select(LichSuTrangThai).where(LichSuTrangThai.don_hang_id == don.id).order_by(LichSuTrangThai.id)
            )
        )
        .scalars()
        .all()
    )
    assert [(x.tu_trang_thai, x.den_trang_thai, x.nguon) for x in ls][-1] == ("cho_thanh_toan", "cho_xac_nhan", "ipn_thanh_toan")  # fmt: skip
    assert (await c.get(f"{DON}/{o['ma_don']}")).json()["trang_thai_tt"] == "da_thanh_toan"


async def test_ipn_gui_hai_lan_chi_xu_ly_mot_lan(dang_nhap_khach, client, db):
    c = dang_nhap_khach
    _, o = await dat_online(c, db)
    await tao_gd(c, o["ma_don"])
    gd = await lay_gd(db, o["ma_don"])
    tham_so = ipn_vnpay(f"{o['ma_don']}-{gd.id}", Decimal(o["tong_tien"]))
    r1, r2 = await client.get(VNPAY_IPN, params=tham_so), await client.get(VNPAY_IPN, params=tham_so)
    assert (r1.json()["RspCode"], r2.json()["RspCode"]) == ("00", "02")
    don = await db.scalar(select(DonHang).where(DonHang.ma_don == o["ma_don"]))
    n = await db.scalar(select(func.count()).select_from(LichSuTrangThai).where(LichSuTrangThai.don_hang_id == don.id, LichSuTrangThai.den_trang_thai == "cho_xac_nhan"))  # fmt: skip
    assert n == 1 and await db.scalar(select(func.count()).select_from(ThanhToan)) == 1


async def test_ipn_sai_chu_ky_bi_tu_choi_va_khong_ghi_gi(dang_nhap_khach, client, db):
    c = dang_nhap_khach
    _, o = await dat_online(c, db)
    await tao_gd(c, o["ma_don"])
    gd = await lay_gd(db, o["ma_don"])
    tham_so = ipn_vnpay(f"{o['ma_don']}-{gd.id}", Decimal(o["tong_tien"]))
    tham_so["vnp_Amount"] = "100"  # đổi dữ liệu sau khi ký
    r = await client.get(VNPAY_IPN, params=tham_so)
    assert r.json()["RspCode"] == "97"
    await db.refresh(gd)
    assert (gd.trang_thai, gd.du_lieu_ipn, gd.ma_giao_dich_cong) == ("khoi_tao", None, None)
    assert (await client.get(VNPAY_IPN)).json()["RspCode"] == "97"  # không tham số


async def test_ipn_sai_so_tien_va_khong_thay_giao_dich(dang_nhap_khach, client, db):
    c = dang_nhap_khach
    _, o = await dat_online(c, db)
    await tao_gd(c, o["ma_don"])
    gd = await lay_gd(db, o["ma_don"])
    ref = f"{o['ma_don']}-{gd.id}"
    assert (await client.get(VNPAY_IPN, params=ipn_vnpay(ref, 1000))).json()["RspCode"] == "04"
    assert (await client.get(VNPAY_IPN, params=ipn_vnpay("DHKHONGCO-1", 1000))).json()["RspCode"] == "01"
    assert (await client.get(VNPAY_IPN, params=ipn_vnpay("khong-co-so", 1000))).json()["RspCode"] == "01"
    assert (await client.get(VNPAY_IPN, params=ipn_vnpay(f"DHKHAC0000-{gd.id}", Decimal(o["tong_tien"])))).json()["RspCode"] == "01"  # fmt: skip
    await db.refresh(gd)
    assert gd.trang_thai == "khoi_tao"


async def test_ipn_that_bai_don_giu_cho_thanh_toan_va_cho_thanh_toan_lai(dang_nhap_khach, client, db):
    c = dang_nhap_khach
    _, o = await dat_online(c, db)
    await tao_gd(c, o["ma_don"])
    gd = await lay_gd(db, o["ma_don"])
    r = await client.get(VNPAY_IPN, params=ipn_vnpay(f"{o['ma_don']}-{gd.id}", Decimal(o["tong_tien"]), ok=False))
    assert r.json()["RspCode"] == "00"
    await db.refresh(gd)
    assert (gd.trang_thai, gd.ma_giao_dich_cong) == ("that_bai", None)
    don = (await c.get(f"{DON}/{o['ma_don']}")).json()
    assert (don["trang_thai"], don["trang_thai_tt"]) == ("cho_thanh_toan", "chua_thanh_toan")
    r2 = await tao_gd(c, o["ma_don"])  # thanh toán lại bằng giao dịch mới
    assert r2.status_code == 200
    gd2 = await lay_gd(db, o["ma_don"])
    assert gd2.id != gd.id
    assert (await client.get(VNPAY_IPN, params=ipn_vnpay(f"{o['ma_don']}-{gd2.id}", Decimal(o["tong_tien"]), ma_gd="14000002"))).json()["RspCode"] == "00"  # fmt: skip
    assert (await c.get(f"{DON}/{o['ma_don']}")).json()["trang_thai"] == "cho_xac_nhan"


async def test_ipn_trung_ma_giao_dich_cong_khong_xu_ly_lan_hai(dang_nhap_khach, client, db):
    """Hai giao dịch khác nhau nhưng cùng mã giao dịch của cổng (replay sang giao dịch khác): chỉ lần đầu được tính."""
    c = dang_nhap_khach
    _, o1 = await dat_online(c, db)
    _, o2 = await dat_online(c, db)
    await tao_gd(c, o1["ma_don"])
    await tao_gd(c, o2["ma_don"])
    g1, g2 = await lay_gd(db, o1["ma_don"]), await lay_gd(db, o2["ma_don"])
    r1 = await client.get(
        VNPAY_IPN, params=ipn_vnpay(f"{o1['ma_don']}-{g1.id}", Decimal(o1["tong_tien"]), ma_gd="SAME1")
    )
    r2 = await client.get(
        VNPAY_IPN, params=ipn_vnpay(f"{o2['ma_don']}-{g2.id}", Decimal(o2["tong_tien"]), ma_gd="SAME1")
    )
    assert (r1.json()["RspCode"], r2.json()["RspCode"]) == ("00", "02")
    await db.refresh(g2)
    assert g2.trang_thai == "khoi_tao"


# --- IPN đến muộn: hoàn tiền chờ xác nhận ---


async def test_ipn_den_sau_khi_don_bi_huy_qua_han_tao_hoan_tien_cho_xac_nhan(dang_nhap_khach, client, db):
    c = dang_nhap_khach
    sp, o = await dat_online(c, db)
    await tao_gd(c, o["ma_don"])
    gd = await lay_gd(db, o["ma_don"])
    don = await db.scalar(select(DonHang).where(DonHang.ma_don == o["ma_don"]))
    don.han_thanh_toan = bay_gio_utc() - timedelta(minutes=1)
    await db.flush()
    assert (await huy_don_qua_han(db)).da_huy == [o["ma_don"]]
    r = await client.get(VNPAY_IPN, params=ipn_vnpay(f"{o['ma_don']}-{gd.id}", Decimal(o["tong_tien"])))
    assert r.json()["RspCode"] == "00"  # cổng nhận "đã xác nhận" để không gọi lại
    await db.refresh(don)
    await db.refresh(gd)
    assert (don.trang_thai, don.trang_thai_tt, gd.trang_thai) == ("da_huy", "cho_hoan_tien", "thanh_cong")
    hoan = (await db.execute(select(ThanhToan).where(ThanhToan.loai == "hoan_tien"))).scalars().all()
    assert len(hoan) == 1
    assert (hoan[0].trang_thai, hoan[0].thanh_toan_goc_id, hoan[0].so_tien, hoan[0].don_hang_id) == (
        "khoi_tao", gd.id, Decimal(o["tong_tien"]), don.id,
    )  # fmt: skip
    assert (
        await db.scalar(select(func.sum(LoThuoc.so_luong_giu)).where(LoThuoc.san_pham_id == sp.id)) == 0
    )  # không giữ lại hàng


async def test_ipn_cua_don_duoc_si_tao_chuyen_da_xac_nhan(dang_nhap_khach, client, db):
    c = dang_nhap_khach
    _, o = await dat_online(c, db)
    don = await db.scalar(select(DonHang).where(DonHang.ma_don == o["ma_don"]))
    don.nhan_vien_tao_id = (await tao_nhan_vien(db)).id
    await db.flush()
    await tao_gd(c, o["ma_don"])
    gd = await lay_gd(db, o["ma_don"])
    await client.get(VNPAY_IPN, params=ipn_vnpay(f"{o['ma_don']}-{gd.id}", Decimal(o["tong_tien"])))
    await db.refresh(don)
    assert (don.trang_thai, don.trang_thai_tt) == ("da_xac_nhan", "da_thanh_toan")


# --- IPN MoMo ---


async def test_ipn_momo_thanh_cong_204_va_chong_trung(dang_nhap_khach, client, db, monkeypatch):
    c = dang_nhap_khach
    _, o = await dat_online(c, db, cong="momo")
    gd = ThanhToan(don_hang_id=(await db.scalar(select(DonHang.id).where(DonHang.ma_don == o["ma_don"]))), cong_thanh_toan="momo", so_tien=Decimal(o["tong_tien"]))  # fmt: skip
    db.add(gd)
    await db.flush()  # bỏ qua bước gọi mạng của MoMo (test không gọi dịch vụ thật)
    tham_so = ipn_momo(f"{o['ma_don']}-{gd.id}", Decimal(o["tong_tien"]))
    r1 = await client.post(MOMO_IPN, json=tham_so)
    r2 = await client.post(MOMO_IPN, json=tham_so)
    assert (r1.status_code, r1.content, r2.status_code) == (204, b"", 204)
    await db.refresh(gd)
    assert (gd.trang_thai, gd.ma_giao_dich_cong) == ("thanh_cong", "777001")
    assert (await c.get(f"{DON}/{o['ma_don']}")).json()["trang_thai"] == "cho_xac_nhan"


async def test_ipn_momo_sai_chu_ky_va_sai_dinh_dang(client, db):
    tham_so = ipn_momo("DH00000000-1", 1000)
    tham_so["amount"] = 1
    assert (await client.post(MOMO_IPN, json=tham_so)).status_code == 400
    assert (await client.post(MOMO_IPN, content=b"khong phai json")).status_code == 400
    assert (await client.post(MOMO_IPN, json=[1, 2])).status_code == 400


# --- Cổng giả ---


async def test_cong_gia_bam_thanh_cong_di_qua_cung_ham_xu_ly(cong_gia, dang_nhap_khach, client, db):
    c = dang_nhap_khach
    _, o = await dat_online(c, db)
    r = await tao_gd(c, o["ma_don"])
    gd = await lay_gd(db, o["ma_don"])
    assert (
        r.json()["url_thanh_toan"]
        == f"{settings.FRONTEND_URL.rstrip('/')}/thanh-toan-gia?giao_dich={o['ma_don']}-{gd.id}"
    )
    for ok, mong_doi in ((True, ("00", "cho_xac_nhan")),):
        kq = await client.post(GIA_IPN, json={"giao_dich": f"{o['ma_don']}-{gd.id}", "thanh_cong": ok})
        assert (kq.json()["RspCode"], (await c.get(f"{DON}/{o['ma_don']}")).json()["trang_thai"]) == mong_doi
    assert (await client.post(GIA_IPN, json={"giao_dich": f"{o['ma_don']}-{gd.id}", "thanh_cong": True})).json()["RspCode"] == "02"  # fmt: skip


async def test_cong_gia_tra_thong_tin_giao_dich_de_dung_trang_thanh_toan(cong_gia, dang_nhap_khach, client, db):
    c = dang_nhap_khach
    _, o = await dat_online(c, db, cong="momo")
    await tao_gd(c, o["ma_don"])
    gd = await lay_gd(db, o["ma_don"])
    ref = f"{o['ma_don']}-{gd.id}"
    r = await client.get(GIA_GD, params={"giao_dich": ref})
    assert r.status_code == 200
    ra = r.json()
    assert (ra["ma_don"], ra["cong"], ra["trang_thai"], ra["giao_dich"]) == (o["ma_don"], "momo", "khoi_tao", ref)
    assert ra["so_tien"] == int(gd.so_tien) and ra["het_han_luc"] is not None
    await client.post(GIA_IPN, json={"giao_dich": ref, "thanh_cong": True})
    assert (await client.get(GIA_GD, params={"giao_dich": ref})).json()["trang_thai"] == "thanh_cong"
    # Mã sai, id không có, mã đơn không khớp id: cùng một câu trả lời 404
    for rac in ("rac", "DH1-999999", f"DHKHONGKHOP-{gd.id}", f"{o['ma_don']}-0{gd.id}x"):
        assert (await client.get(GIA_GD, params={"giao_dich": rac})).status_code == 404


async def test_cong_gia_bam_that_bai_va_giao_dich_khong_co(cong_gia, dang_nhap_khach, client, db):
    c = dang_nhap_khach
    _, o = await dat_online(c, db, cong="momo")
    await tao_gd(c, o["ma_don"])
    gd = await lay_gd(db, o["ma_don"])
    kq = await client.post(GIA_IPN, json={"giao_dich": f"{o['ma_don']}-{gd.id}", "thanh_cong": False})
    assert kq.json()["RspCode"] == "00"
    await db.refresh(gd)
    assert gd.trang_thai == "that_bai"
    assert (await client.post(GIA_IPN, json={"giao_dich": "DH1-999999", "thanh_cong": True})).json()["RspCode"] == "01"
    assert (await client.post(GIA_IPN, json={"giao_dich": "rac", "thanh_cong": True})).json()["RspCode"] == "01"


def test_ipn_gia_bi_giam_chu_ky_thi_tu_choi():
    from app.tich_hop.thanh_toan.gia import CongGia

    ipn = dung_ipn("DH1-1", Decimal(5000), True)
    assert CongGia().xac_thuc_ipn(ipn).chu_ky_hop_le
    assert not CongGia().xac_thuc_ipn({**ipn, "so_tien": "1"}).chu_ky_hop_le


def test_route_gia_chi_co_khi_che_do_gia(monkeypatch):
    from app.main import create_app

    def co_route(ung_dung):
        return "/api/v1/webhook/gia-ipn" in ung_dung.openapi()["paths"]

    che_do(monkeypatch, "gia")
    assert co_route(create_app())
    che_do(monkeypatch, "sandbox")
    assert not co_route(create_app())


def test_lay_cong_theo_che_do(monkeypatch):
    from app.tich_hop.thanh_toan import lay_cong
    from app.tich_hop.thanh_toan.gia import CongGia
    from app.tich_hop.thanh_toan.momo import CongMomo
    from app.tich_hop.thanh_toan.vnpay import CongVnpay

    che_do(monkeypatch, "gia")
    assert isinstance(lay_cong("vnpay"), CongGia) and isinstance(lay_cong("momo"), CongGia)
    che_do(monkeypatch, "sandbox")
    assert isinstance(lay_cong("vnpay"), CongVnpay) and isinstance(lay_cong("momo"), CongMomo)
    with pytest.raises(ValueError):
        lay_cong("cod")


# --- HT03 ---


async def test_ht03_huy_don_qua_han_nha_hang_tra_luot_ma_va_giu_don_chua_qua_han(dang_nhap_khach, db):
    c = dang_nhap_khach
    _, ma = await tao_km(db, ma="HT03MA")
    sp, qua_han = await dat_online(c, db, ma_giam_gia="HT03MA")
    _, con_han = await dat_online(c, db, so_luong=5)
    await db.refresh(ma)
    assert ma.so_luot_da_dung == 1
    assert await db.scalar(select(func.sum(LoThuoc.so_luong_giu)).where(LoThuoc.san_pham_id == sp.id)) == 10
    don = await db.scalar(select(DonHang).where(DonHang.ma_don == qua_han["ma_don"]))
    don.han_thanh_toan = bay_gio_utc() - timedelta(seconds=1)
    await db.flush()
    kq = await huy_don_qua_han(db)
    assert kq.da_huy == [qua_han["ma_don"]]
    await db.refresh(don)
    await db.refresh(ma)
    assert (don.trang_thai, don.ly_do_huy) == ("da_huy", "Quá hạn thanh toán")
    assert await db.scalar(select(func.sum(LoThuoc.so_luong_giu)).where(LoThuoc.san_pham_id == sp.id)) == 0
    assert ma.so_luot_da_dung == 0
    assert (await c.get(f"{DON}/{con_han['ma_don']}")).json()["trang_thai"] == "cho_thanh_toan"
    assert (await huy_don_qua_han(db)).da_huy == []  # chạy lại không làm gì


async def test_ht03_huy_don_cho_khach_xac_nhan_qua_han(db):
    from tests.factories import tao_don, tao_khach

    kh = await tao_khach(db)
    nv = await tao_nhan_vien(db)
    qua = await tao_don(db, kh, trang_thai="cho_khach_xac_nhan", nhan_vien_tao_id=nv.id, han_xac_nhan=bay_gio_utc() - timedelta(minutes=5))  # fmt: skip
    con = await tao_don(db, kh, trang_thai="cho_khach_xac_nhan", nhan_vien_tao_id=nv.id, han_xac_nhan=bay_gio_utc() + timedelta(hours=1))  # fmt: skip
    kq = await huy_don_qua_han(db)
    assert kq.da_huy == [qua.ma_don]
    await db.refresh(qua)
    await db.refresh(con)
    assert (qua.trang_thai, con.trang_thai) == ("da_huy", "cho_khach_xac_nhan")


async def test_ht03_don_vua_nhan_ipn_thanh_cong_khong_bi_huy(dang_nhap_khach, client, db):
    c = dang_nhap_khach
    _, o = await dat_online(c, db)
    await tao_gd(c, o["ma_don"])
    gd = await lay_gd(db, o["ma_don"])
    await client.get(VNPAY_IPN, params=ipn_vnpay(f"{o['ma_don']}-{gd.id}", Decimal(o["tong_tien"])))
    don = await db.scalar(select(DonHang).where(DonHang.ma_don == o["ma_don"]))
    don.han_thanh_toan = bay_gio_utc() - timedelta(minutes=1)  # đã sang cho_xac_nhan nên không thuộc diện hủy
    await db.flush()
    assert (await huy_don_qua_han(db)).da_huy == []
    await db.refresh(don)
    assert don.trang_thai == "cho_xac_nhan"


async def test_ht03_chay_qua_chay_job_va_lich(engine_test):
    from app.jobs.__main__ import LICH_PHUT, tao_scheduler

    assert [t for t, *_ in LICH_PHUT] == ["ht03_huy_qua_han", "ht08_tu_hoan_tat", "ai06_doc_don_thuoc"]
    ids = {j.id for j in tao_scheduler().get_jobs()}
    assert "ht03_huy_qua_han" in ids


async def test_hai_ipn_dong_thoi_chi_xu_ly_mot_lan(db_that):
    from app.models.enums import PhuongThucThanhToan
    from app.modules.thanh_toan.dich_vu import KetQuaXuLy, xu_ly_ipn
    from app.tich_hop.thanh_toan import lay_cong
    from tests.factories import tao_don, tao_khach

    async with db_that() as s, s.begin():
        kh = await tao_khach(s)
        don = await tao_don(s, kh, trang_thai="cho_thanh_toan", phuong_thuc_tt="vnpay", han_thanh_toan=bay_gio_utc() + timedelta(minutes=10))  # fmt: skip
        gd = ThanhToan(don_hang_id=don.id, cong_thanh_toan="vnpay", so_tien=don.tong_tien)
        s.add(gd)
        await s.flush()
        ref, tong, don_id = f"{don.ma_don}-{gd.id}", don.tong_tien, don.id
    tham_so = ipn_vnpay(ref, tong)

    async def goi():
        async with db_that() as s, s.begin():
            kq = lay_cong(PhuongThucThanhToan.vnpay).xac_thuc_ipn(tham_so)
            return await xu_ly_ipn(s, PhuongThucThanhToan.vnpay, kq)

    kq = await asyncio.gather(goi(), goi())
    assert sorted(kq) == sorted([KetQuaXuLy.thanh_cong, KetQuaXuLy.da_xu_ly])
    async with db_that() as s:
        n = await s.scalar(select(func.count()).select_from(LichSuTrangThai).where(LichSuTrangThai.don_hang_id == don_id, LichSuTrangThai.den_trang_thai == "cho_xac_nhan"))  # fmt: skip
        assert n == 1 and await s.scalar(select(func.count()).select_from(ThanhToan)) == 1

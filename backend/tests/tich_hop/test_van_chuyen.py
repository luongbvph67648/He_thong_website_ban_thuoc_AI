"""Adapter vận chuyển (spec 08 mục 5): ánh xạ trạng thái đối tác, xác thực webhook GHN, tạo vận đơn."""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.models.enums import TrangThaiDon as TT
from app.tich_hop.van_chuyen import WebhookKhongHopLe, lay_don_vi_van_chuyen
from app.tich_hop.van_chuyen.anh_xa import duong_di, trang_thai_muc_tieu
from app.tich_hop.van_chuyen.ghn import VanChuyenGhn
from app.tich_hop.van_chuyen.gia import VanChuyenGia


@pytest.mark.parametrize(
    ("tt", "hien_tai", "mong_doi"),
    [
        ("picked", TT.cho_lay_hang, TT.dang_giao),
        ("sorting", TT.dang_giao, TT.dang_giao),
        ("delivered", TT.dang_giao, TT.da_giao),
        ("delivery_fail", TT.dang_giao, TT.giao_that_bai),
        ("waiting_to_return", TT.dang_giao, TT.giao_that_bai),
        ("delivering", TT.giao_that_bai, TT.dang_giao),  # giao lại
        ("storing", TT.giao_that_bai, None),  # trung chuyển sau khi thất bại: chưa phải giao lại
        ("returned", TT.giao_that_bai, TT.hoan_ve_kho),
        ("cancel", TT.cho_lay_hang, None),
        ("ready_to_pick", TT.cho_lay_hang, None),
        ("khong_biet", TT.dang_giao, None),
        (" DELIVERED ", TT.dang_giao, TT.da_giao),
    ],
)
def test_trang_thai_muc_tieu(tt, hien_tai, mong_doi):
    assert trang_thai_muc_tieu(tt, hien_tai) == mong_doi


def test_duong_di_bu_su_kien_mat_va_bo_su_kien_cu():
    assert duong_di(TT.cho_lay_hang, TT.da_giao) == [TT.dang_giao, TT.da_giao]
    assert duong_di(TT.cho_lay_hang, TT.hoan_ve_kho) == [TT.dang_giao, TT.giao_that_bai, TT.hoan_ve_kho]
    assert duong_di(TT.dang_giao, TT.dang_giao) == []
    assert duong_di(TT.da_giao, TT.dang_giao) == []  # sự kiện cũ đến sau
    assert duong_di(TT.da_huy, TT.dang_giao) == []
    assert duong_di(TT.hoan_ve_kho, TT.da_giao) == []


def test_webhook_ghn_kiem_token(monkeypatch):
    monkeypatch.setattr(settings, "GHN_WEBHOOK_TOKEN", type(settings.JWT_SECRET)("token-bi-mat"))
    ghn = VanChuyenGhn()
    body = {"OrderCode": "GHN123", "Status": "picked"}
    sk = ghn.xac_thuc_webhook({"Token": "token-bi-mat"}, body)
    assert (sk.ma_van_don, sk.trang_thai_doi_tac) == ("GHN123", "picked")
    for sai in ({}, {"Token": "sai"}, {"Token": ""}):
        with pytest.raises(WebhookKhongHopLe):
            ghn.xac_thuc_webhook(sai, body)
    with pytest.raises(WebhookKhongHopLe):
        ghn.xac_thuc_webhook({"Token": "token-bi-mat"}, {"Status": "picked"})


def test_webhook_ghn_chua_cau_hinh_token_thi_tu_choi_het(monkeypatch):
    monkeypatch.setattr(settings, "GHN_WEBHOOK_TOKEN", type(settings.JWT_SECRET)(""))
    with pytest.raises(WebhookKhongHopLe):
        VanChuyenGhn().xac_thuc_webhook({"Token": ""}, {"OrderCode": "A", "Status": "picked"})


async def test_ghn_tao_van_don_gui_dung_truong_va_doc_ma(monkeypatch):
    da_goi = {}

    async def gia_goi(self, duong_dan, thanh):
        da_goi.update(duong_dan=duong_dan, thanh=thanh)
        return {"order_code": "GHNABC", "total_fee": 28000}

    monkeypatch.setattr(VanChuyenGhn, "_goi", gia_goi)
    don = SimpleNamespace(
        ma_don="DH1", ten_nguoi_nhan="An", sdt_nguoi_nhan="0912345678", dia_chi_giao="12 Lê Lợi", ma_phuong_xa="0001",
        phuong_thuc_tt="cod", tong_tien=Decimal("45000.00"),
        chi_tiet=[SimpleNamespace(ten_san_pham="Paracetamol", so_luong=2)],
    )  # fmt: skip
    kq = await VanChuyenGhn().tao_van_don(don, "giao_hang", 500)
    assert (kq.ma_van_don, kq.phi) == ("GHNABC", Decimal(28000))
    assert da_goi["thanh"]["cod_amount"] == 45000 and da_goi["thanh"]["client_order_code"] == "DH1"
    assert da_goi["thanh"]["items"] == [{"name": "Paracetamol", "quantity": 2}]
    don.phuong_thuc_tt = "vnpay"
    await VanChuyenGhn().tao_van_don(don, "giao_hang", 500)
    assert da_goi["thanh"]["cod_amount"] == 0  # đã thanh toán online thì không thu hộ


def test_chon_adapter_theo_che_do(monkeypatch):
    monkeypatch.setattr(settings, "VAN_CHUYEN_CHE_DO", "gia")
    assert isinstance(lay_don_vi_van_chuyen(), VanChuyenGia)
    monkeypatch.setattr(settings, "VAN_CHUYEN_CHE_DO", "ghn")
    assert isinstance(lay_don_vi_van_chuyen(), VanChuyenGhn)


async def test_van_chuyen_gia_ma_van_don_khac_nhau_va_webhook_gia():
    gia = VanChuyenGia()
    don = SimpleNamespace(id=7)
    a, b = await gia.tao_van_don(don, "giao_hang", 500), await gia.tao_van_don(don, "giao_hang", 500)
    assert a.ma_van_don.startswith("GIA7") and a.ma_van_don != b.ma_van_don
    sk = gia.xac_thuc_webhook({}, {"ma_van_don": a.ma_van_don, "trang_thai_doi_tac": "picked"})
    assert sk.trang_thai_doi_tac == "picked"
    with pytest.raises(WebhookKhongHopLe):
        gia.xac_thuc_webhook({}, {"ma_van_don": a.ma_van_don})

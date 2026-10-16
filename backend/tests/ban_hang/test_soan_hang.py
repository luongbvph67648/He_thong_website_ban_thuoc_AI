"""KHO03, KHO04, HT05, KTV05: soạn hàng (FEFO, đổi lô), đóng gói, vận đơn, webhook vận chuyển, COD."""

from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.core.thoi_gian import hom_nay_vn
from app.models.ban_hang import DonHang, PhanBoLo, ThanhToan, VanDon
from app.models.kho import BienDongKho, LoThuoc
from app.modules.ban_hang import soan_hang
from app.tich_hop.van_chuyen.gia import VanChuyenGia
from tests.ban_hang.test_dat_hang import DON, khoa, sp_ban, them, thân
from tests.ban_hang.test_xu_ly_don import dat_cod, don_cua
from tests.factories import tao_lo

SH = "/api/v1/noi-bo/soan-hang"
NB = "/api/v1/noi-bo/don-hang"
GIA_VC = "/api/v1/webhook/gia-van-chuyen"
GHN = "/api/v1/webhook/ghn"


async def don_da_xac_nhan(khach, duoc_si, db, so_luong=3):
    sp, o = await dat_cod(khach, db, so_luong=so_luong)
    don = await don_cua(db, o["ma_don"])
    assert (await duoc_si.post(f"{NB}/{don.id}/xac-nhan")).status_code == 200
    return sp, o, don


async def don_dang_soan(khach, duoc_si, kho, db, so_luong=3):
    sp, o, don = await don_da_xac_nhan(khach, duoc_si, db, so_luong)
    assert (await kho.post(f"{SH}/{don.id}/bat-dau")).status_code == 200, "bắt đầu soạn"
    return sp, o, don


async def van_don_cua(db, don_id):
    return (await db.execute(select(VanDon).where(VanDon.don_hang_id == don_id).order_by(VanDon.id))).scalars().all()


async def su_kien(client, ma_van_don, trang_thai):
    return await client.post(GIA_VC, json={"ma_van_don": ma_van_don, "trang_thai_doi_tac": trang_thai})


# --- KHO03: xem phiếu, gợi ý FEFO, đổi lô ---


async def test_phieu_soan_chi_kho_xem_va_chi_don_tu_da_xac_nhan(
    dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, dang_nhap_admin, db
):
    sp, o = await dat_cod(dang_nhap_khach, db)
    don = await don_cua(db, o["ma_don"])
    assert (await dang_nhap_kho.get(f"{SH}/{don.id}")).status_code == 404  # còn chờ xác nhận
    await dang_nhap_duoc_si.post(f"{NB}/{don.id}/xac-nhan")
    for c in (dang_nhap_duoc_si, dang_nhap_admin):
        assert (await c.get(f"{SH}/{don.id}")).status_code == 403
    r = await dang_nhap_kho.get(f"{SH}/{don.id}")
    assert r.status_code == 200, r.text
    ct = r.json()
    (dong,) = ct["dong"]
    assert (ct["trang_thai"], ct["che_do_van_chuyen_gia"]) == ("da_xac_nhan", True)
    assert dong["so_luong"] == 3 and len(dong["phan_bo"]) == 1
    assert dong["phan_bo"][0]["trang_thai"] == "dang_giu" and dong["goi_y"]
    assert (await dang_nhap_kho.get(f"{SH}/99999999")).status_code == 404


async def test_doi_lo_bat_buoc_ly_do_va_chuyen_giu_sang_lo_moi(dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, db):
    sp, o, don = await don_da_xac_nhan(dang_nhap_khach, dang_nhap_duoc_si, db, 3)
    lo_moi = await tao_lo(db, sp, so_luong=50, han_su_dung=hom_nay_vn() + timedelta(days=700))
    pb = (await db.execute(select(PhanBoLo).where(PhanBoLo.trang_thai == "dang_giu"))).scalars().one()
    lo_cu_id = pb.lo_id
    base = {"phan_bo_lo_id": pb.id, "lo_id": lo_moi.id}
    for sai in ({**base, "ly_do": ""}, {**base, "ly_do": "   "}, base):
        r = await dang_nhap_kho.post(f"{SH}/{don.id}/doi-lo", json=sai)
        assert r.status_code == 400, r.text
    assert (await dang_nhap_duoc_si.post(f"{SH}/{don.id}/doi-lo", json={**base, "ly_do": "x"})).status_code == 403
    r = await dang_nhap_kho.post(f"{SH}/{don.id}/doi-lo", json={**base, "ly_do": "Khách muốn hạn dài"})
    assert r.status_code == 200, r.text
    await db.refresh(pb)
    assert pb.trang_thai == "da_nha"
    moi = (await db.execute(select(PhanBoLo).where(PhanBoLo.trang_thai == "dang_giu"))).scalars().one()
    assert (moi.lo_id, moi.so_luong_co_so, moi.ly_do_doi_lo) == (lo_moi.id, 3, "Khách muốn hạn dài")
    lo_cu = await db.get(LoThuoc, lo_cu_id, populate_existing=True)
    await db.refresh(lo_moi)
    assert (lo_cu.so_luong_giu, lo_moi.so_luong_giu) == (0, 3)
    phan_bo = r.json()["dong"][0]["phan_bo"]
    assert [p["so_lo"] for p in phan_bo] == [lo_moi.so_lo] and phan_bo[0]["ly_do_doi_lo"]


async def test_doi_lo_chan_lo_sai_san_pham_het_han_thieu_hang_va_cung_lo(
    dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, db
):
    sp, o, don = await don_da_xac_nhan(dang_nhap_khach, dang_nhap_duoc_si, db, 3)
    pb = (await db.execute(select(PhanBoLo).where(PhanBoLo.trang_thai == "dang_giu"))).scalars().one()

    async def doi(lo_id):
        return await dang_nhap_kho.post(
            f"{SH}/{don.id}/doi-lo", json={"phan_bo_lo_id": pb.id, "lo_id": lo_id, "ly_do": "thử"}
        )

    lo_khac_sp = await tao_lo(db, None, so_luong=50)
    lo_het_han = await tao_lo(db, sp, so_luong=50, han_su_dung=hom_nay_vn() - timedelta(days=1), trang_thai="dang_ban")
    lo_it = await tao_lo(db, sp, so_luong=2, han_su_dung=hom_nay_vn() + timedelta(days=500))
    assert (await doi(lo_khac_sp.id)).status_code == 400
    assert (await doi(lo_het_han.id)).status_code == 400
    r = await doi(lo_it.id)
    assert (r.status_code, r.json()["ma_loi"]) == (409, "HET_HANG")
    assert (await doi(pb.lo_id)).status_code == 400  # cùng lô
    assert (await doi(99999999)).status_code == 404
    assert (await db.scalar(select(func.count()).select_from(PhanBoLo).where(PhanBoLo.trang_thai == "dang_giu"))) == 1


async def test_bat_dau_soan_chot_lo_tru_ton_ghi_the_kho_va_khong_doi_lo_nua(
    dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, db
):
    sp, o, don = await don_da_xac_nhan(dang_nhap_khach, dang_nhap_duoc_si, db, 3)
    ton_truoc = await db.scalar(select(func.sum(LoThuoc.so_luong_ton)).where(LoThuoc.san_pham_id == sp.id))
    assert (await dang_nhap_duoc_si.post(f"{SH}/{don.id}/bat-dau")).status_code == 403
    r = await dang_nhap_kho.post(f"{SH}/{don.id}/bat-dau")
    assert r.status_code == 200 and r.json()["trang_thai"] == "dang_soan_hang"
    assert r.json()["dong"][0]["phan_bo"][0]["trang_thai"] == "da_xuat" and r.json()["dong"][0]["goi_y"] == []
    ton_sau = await db.scalar(
        select(func.sum(LoThuoc.so_luong_ton))
        .where(LoThuoc.san_pham_id == sp.id)
        .execution_options(populate_existing=True)
    )
    assert ton_sau == ton_truoc - 3
    the = (await db.execute(select(BienDongKho).where(BienDongKho.chung_tu_loai == "don_hang"))).scalars().all()
    assert [(t.loai, t.so_luong) for t in the] == [("xuat_ban", -3)]
    again = await dang_nhap_kho.post(f"{SH}/{don.id}/bat-dau")  # bấm hai lần chỉ trừ một lần
    assert (again.status_code, again.json()["ma_loi"]) == (409, "CHUYEN_TRANG_THAI_KHONG_HOP_LE")
    pb = (await db.execute(select(PhanBoLo).where(PhanBoLo.trang_thai == "da_xuat"))).scalars().one()
    r2 = await dang_nhap_kho.post(
        f"{SH}/{don.id}/doi-lo", json={"phan_bo_lo_id": pb.id, "lo_id": pb.lo_id + 1, "ly_do": "x"}
    )
    assert r2.status_code == 409


async def test_bat_dau_soan_chan_khi_lo_giu_het_han(dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, db):
    sp, o, don = await don_da_xac_nhan(dang_nhap_khach, dang_nhap_duoc_si, db, 3)
    lo = await db.get(LoThuoc, (await db.scalar(select(PhanBoLo.lo_id).where(PhanBoLo.trang_thai == "dang_giu"))))
    lo.han_su_dung = hom_nay_vn() - timedelta(days=1)
    await db.flush()
    r = await dang_nhap_kho.post(f"{SH}/{don.id}/bat-dau")
    assert (r.status_code, r.json()["ma_loi"]) == (409, "CHUYEN_TRANG_THAI_KHONG_HOP_LE")
    assert (await don_cua(db, o["ma_don"])).trang_thai == "da_xac_nhan"


# --- KHO04: đóng gói, vận đơn ---


async def test_dong_goi_giao_tan_noi_tao_van_don_va_cho_lay_hang(dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, db):
    sp, o, don = await don_dang_soan(dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, db)
    assert (await dang_nhap_duoc_si.post(f"{SH}/{don.id}/dong-goi")).status_code == 403
    r = await dang_nhap_kho.post(f"{SH}/{don.id}/dong-goi")
    assert r.status_code == 200, r.text
    (vd,) = await van_don_cua(db, don.id)
    assert vd.ma_van_don.startswith("GIA") and vd.loai == "giao_hang" and vd.don_vi_van_chuyen == "GIA" and vd.phi > 0
    assert r.json()["trang_thai"] == "cho_lay_hang" and r.json()["van_don"][0]["ma_van_don"] == vd.ma_van_don
    again = await dang_nhap_kho.post(f"{SH}/{don.id}/dong-goi")
    assert again.status_code == 409 and len(await van_don_cua(db, don.id)) == 1


async def test_dong_goi_don_nhan_tai_nha_thuoc_khong_tao_van_don(dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, db):
    c = dang_nhap_khach
    sp = await sp_ban(db)
    await them(c, sp, "viên", 2)
    o = (await c.post(DON, json=thân(None), headers=khoa())).json()
    don = await don_cua(db, o["ma_don"])
    await dang_nhap_duoc_si.post(f"{NB}/{don.id}/xac-nhan")
    await dang_nhap_kho.post(f"{SH}/{don.id}/bat-dau")
    r = await dang_nhap_kho.post(f"{SH}/{don.id}/dong-goi")
    assert r.status_code == 200 and r.json()["trang_thai"] == "cho_lay_hang"
    assert await van_don_cua(db, don.id) == []


async def test_dong_goi_loi_doi_tac_giu_nguyen_don(dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, db, monkeypatch):
    sp, o, don = await don_dang_soan(dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, db)

    async def hong(self, don, loai, kl):
        raise RuntimeError("GHN sập")

    monkeypatch.setattr(VanChuyenGia, "tao_van_don", hong)
    r = await dang_nhap_kho.post(f"{SH}/{don.id}/dong-goi")
    assert (r.status_code, r.json()["ma_loi"]) == (502, "LOI_DOI_TAC")
    assert (await don_cua(db, o["ma_don"])).trang_thai == "dang_soan_hang" and await van_don_cua(db, don.id) == []


async def test_dong_goi_huy_van_don_neu_chuyen_trang_thai_loi(
    dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, db, monkeypatch
):
    sp, o, don = await don_dang_soan(dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, db)
    da_huy = []

    async def ghi_nho(self, ma):
        da_huy.append(ma)

    async def hong(*a, **k):
        raise RuntimeError("lỗi ghi")

    monkeypatch.setattr(VanChuyenGia, "huy_van_don", ghi_nho)
    monkeypatch.setattr(soan_hang, "chuyen_trang_thai", hong)
    with pytest.raises(RuntimeError):
        await soan_hang.dong_goi(db, dang_nhap_kho.tai_khoan, don.id)
    assert len(da_huy) == 1 and da_huy[0].startswith("GIA")


# --- HT05: webhook vận chuyển ---


async def den_cho_lay_hang(khach, duoc_si, kho, db, so_luong=3):
    sp, o, don = await don_dang_soan(khach, duoc_si, kho, db, so_luong)
    assert (await kho.post(f"{SH}/{don.id}/dong-goi")).status_code == 200
    (vd,) = await van_don_cua(db, don.id)
    return sp, o, don, vd


async def test_webhook_giao_thanh_cong_cod_ghi_thanh_toan_mot_lan(
    dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, client, db
):
    sp, o, don, vd = await den_cho_lay_hang(dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, db)
    assert (await su_kien(client, vd.ma_van_don, "picked")).status_code == 200
    assert (await don_cua(db, o["ma_don"])).trang_thai == "dang_giao"
    assert (await su_kien(client, vd.ma_van_don, "sorting")).status_code == 200  # trạng thái trung gian: không đổi đơn
    assert (await don_cua(db, o["ma_don"])).trang_thai == "dang_giao"
    for _ in range(2):  # GHN gửi lặp
        assert (await su_kien(client, vd.ma_van_don, "delivered")).status_code == 200
    d = await don_cua(db, o["ma_don"])
    assert (d.trang_thai, d.trang_thai_tt) == ("da_giao", "da_thanh_toan")
    tt = (await db.execute(select(ThanhToan).where(ThanhToan.don_hang_id == d.id))).scalars().all()
    assert [(t.loai, t.cong_thanh_toan, t.trang_thai, t.so_tien) for t in tt] == [
        ("thanh_toan", "cod", "thanh_cong", d.tong_tien)
    ]
    await db.refresh(vd)
    assert vd.trang_thai_doi_tac == "delivered" and vd.du_lieu_webhook["ma_van_don"] == vd.ma_van_don
    assert (await su_kien(client, vd.ma_van_don, "picked")).status_code == 200  # sự kiện cũ đến sau: bỏ qua
    assert (await don_cua(db, o["ma_don"])).trang_thai == "da_giao"


async def test_webhook_mat_su_kien_picked_van_ve_dung_trang_thai(
    dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, client, db
):
    sp, o, don, vd = await den_cho_lay_hang(dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, db)
    await su_kien(client, vd.ma_van_don, "delivered")
    assert (await don_cua(db, o["ma_don"])).trang_thai == "da_giao"
    ls = (await db.execute(select(DonHang).where(DonHang.id == don.id))).scalar_one()
    assert ls.trang_thai == "da_giao"


async def test_webhook_giao_that_bai_giao_lai_roi_hoan_hang(
    dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, client, db
):
    sp, o, don, vd = await den_cho_lay_hang(dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, db)
    for tt, mong in [
        ("picked", "dang_giao"),
        ("delivery_fail", "giao_that_bai"),
        ("storing", "giao_that_bai"),
        ("delivering", "dang_giao"),
        ("delivery_fail", "giao_that_bai"),
        ("returned", "hoan_ve_kho"),
    ]:
        assert (await su_kien(client, vd.ma_van_don, tt)).status_code == 200
        assert (await don_cua(db, o["ma_don"])).trang_thai == mong, tt
    d = await don_cua(db, o["ma_don"])
    assert d.trang_thai_tt == "chua_thanh_toan"  # chưa thu tiền COD


async def test_webhook_ma_khong_co_va_than_sai(client, db):
    assert (await su_kien(client, "KHONGCO", "picked")).status_code == 200
    assert (await client.post(GIA_VC, json={"ma_van_don": "A"})).status_code == 400
    assert (await client.post(GIA_VC, content=b"khong phai json")).status_code == 400


async def test_webhook_ghn_can_token(dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, client, db, monkeypatch):
    monkeypatch.setattr(settings, "GHN_WEBHOOK_TOKEN", type(settings.JWT_SECRET)("tok-ghn"))
    sp, o, don, vd = await den_cho_lay_hang(dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, db)
    body = {"OrderCode": vd.ma_van_don, "Status": "picked"}
    for headers in ({}, {"Token": "sai"}):
        assert (await client.post(GHN, json=body, headers=headers)).status_code == 401
    assert (await don_cua(db, o["ma_don"])).trang_thai == "cho_lay_hang"
    assert (await client.post(GHN, json=body, headers={"Token": "tok-ghn"})).status_code == 200
    assert (await don_cua(db, o["ma_don"])).trang_thai == "dang_giao"


def test_route_webhook_gia_chi_co_khi_che_do_gia(monkeypatch):
    from app.main import create_app

    def co_route():
        return GIA_VC in create_app().openapi()["paths"]

    monkeypatch.setattr(settings, "VAN_CHUYEN_CHE_DO", "gia")
    assert co_route()
    monkeypatch.setattr(settings, "VAN_CHUYEN_CHE_DO", "ghn")
    assert not co_route()


# --- KTV05: khách theo dõi ---


async def test_khach_thay_dong_thoi_gian_va_ma_van_don(dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, client, db):
    c = dang_nhap_khach
    sp, o, don, vd = await den_cho_lay_hang(c, dang_nhap_duoc_si, dang_nhap_kho, db)
    await su_kien(client, vd.ma_van_don, "picked")
    ct = (await c.get(f"{DON}/{o['ma_don']}")).json()
    assert [m["den_trang_thai"] for m in ct["lich_su"]] == [
        "cho_xac_nhan", "da_xac_nhan", "dang_soan_hang", "cho_lay_hang", "dang_giao",
    ]  # fmt: skip
    assert [v["ma_van_don"] for v in ct["van_don"]] == [vd.ma_van_don]
    assert "nguoi_thuc_hien" not in ct["lich_su"][0]
    noi_bo = (await dang_nhap_duoc_si.get(f"{NB}/{don.id}")).json()
    assert (
        noi_bo["van_don"][0]["ma_van_don"] == vd.ma_van_don and noi_bo["lich_su"][-1]["nguoi_thuc_hien"] == "Hệ thống"
    )

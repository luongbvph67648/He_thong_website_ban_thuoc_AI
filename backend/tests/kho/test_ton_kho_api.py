"""KHO05, KHO06: /noi-bo/ton-kho và /noi-bo/canh-bao-kho."""

from datetime import timedelta

from app.core.thoi_gian import hom_nay_vn
from tests.factories import tao_lo, tao_san_pham

TON = "/api/v1/noi-bo/ton-kho"
CB = "/api/v1/noi-bo/canh-bao-kho"


def ngay(n):
    return hom_nay_vn() + timedelta(days=n)


async def du_lieu(db):
    sp = await tao_san_pham(db, ten="Paracetamol 500", ton_toi_thieu=100)
    await tao_lo(db, sp, so_luong=30, han_su_dung=ngay(300), gia_nhap=700)
    await tao_lo(db, sp, so_luong=20, han_su_dung=ngay(40), trang_thai="can_han")
    await tao_lo(db, sp, so_luong=7, han_su_dung=ngay(-1), trang_thai="het_han")
    return sp


async def test_ton_theo_san_pham_kha_dung_chi_tinh_lo_dang_ban_con_han(dang_nhap_kho, db):
    sp = await du_lieu(db)
    r = (await dang_nhap_kho.get(TON, params={"q": "paracetamol"})).json()
    d = r["du_lieu"][0]
    assert d["san_pham_id"] == sp.id and d["ton_kha_dung"] == 30 and d["tong_ton"] == 57 and d["so_lo"] == 3
    assert d["thap"] is True
    assert (await dang_nhap_kho.get(TON, params={"chi_thap": "true"})).json()["tong"] >= 1


async def test_chi_tiet_lo_kho_thay_gia_nhap_duoc_si_khong(clients_theo_vai_tro, db):
    sp = await du_lieu(db)
    kho = (await clients_theo_vai_tro["WAREHOUSE"].get(f"{TON}/{sp.id}/lo")).json()
    assert [lo["trang_thai"] for lo in kho] == ["het_han", "can_han", "dang_ban"]  # hạn gần trước
    assert kho[2]["gia_nhap"] == "700.00" and kho[2]["so_luong_ton"] == 30
    ds = clients_theo_vai_tro["PHARMACIST"]
    lo_ds = (await ds.get(f"{TON}/{sp.id}/lo")).json()
    assert lo_ds[2]["kha_dung"] == 30
    for truong in ("gia_nhap", "so_luong_ton", "so_luong_giu", "so_luong_biet_tru"):
        assert all(lo[truong] is None for lo in lo_ds), truong
    ton_ds = (await ds.get(TON, params={"q": "paracetamol"})).json()["du_lieu"][0]
    assert ton_ds["ton_kha_dung"] == 30 and ton_ds["tong_ton"] is None and ton_ds["tong_biet_tru"] is None


async def test_san_pham_khong_ton_tai_la_404_va_admin_xem_duoc(clients_theo_vai_tro, db):
    sp = await du_lieu(db)
    assert (await clients_theo_vai_tro["WAREHOUSE"].get(f"{TON}/999999999/lo")).status_code == 404
    admin = clients_theo_vai_tro["ADMIN"]
    assert (await admin.get(f"{TON}/{sp.id}/lo")).json()[2]["gia_nhap"] == "700.00"


async def test_canh_bao_kho_ba_nhom_va_phan_quyen(clients_theo_vai_tro, db):
    sp = await du_lieu(db)
    r = (await clients_theo_vai_tro["WAREHOUSE"].get(CB)).json()
    assert [x["san_pham_id"] for x in r["ton_thap"]["du_lieu"]] == [sp.id] and r["ton_thap"]["du_lieu"][0][
        "ton_kha_dung"
    ] == 30
    assert [x["so_lo"] for x in r["can_han"]["du_lieu"]] and r["can_han"]["tong"] >= 1
    assert r["het_han"]["du_lieu"][0]["so_luong_ton"] == 7
    assert (await clients_theo_vai_tro["ADMIN"].get(CB)).status_code == 200
    assert (await clients_theo_vai_tro["PHARMACIST"].get(CB)).status_code == 403
    assert (await clients_theo_vai_tro["PHARMACIST"].get(TON)).status_code == 200

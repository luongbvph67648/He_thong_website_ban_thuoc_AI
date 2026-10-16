"""KHO02: /api/v1/noi-bo/phieu-nhap. Mọi test kết thúc bằng kiểm tra bất biến tồn kho (conftest)."""

from datetime import timedelta

from sqlalchemy import select

from app.core.thoi_gian import hom_nay_vn
from app.models.kho import BienDongKho, LoThuoc
from tests.factories import tao_san_pham

GOC = "/api/v1/noi-bo/phieu-nhap"
HOP = [
    {"ten_don_vi": "viên", "he_so": 1, "gia_ban": 1000, "la_mac_dinh": True},
    {"ten_don_vi": "hộp", "he_so": 100, "gia_ban": 90000},
]


def ngay(n):
    return (hom_nay_vn() + timedelta(days=n)).isoformat()


async def ncc(c):
    r = await c.post("/api/v1/noi-bo/nha-cung-cap", json={"ten": "NCC"})
    return r.json()["id"]


async def san_pham(db):
    sp = await tao_san_pham(db, don_vi=HOP)
    return sp, sp.don_vi_theo_ten["hộp"].id, sp.don_vi_theo_ten["viên"].id


def dong(sp, dv, **ghi_de):
    return {
        "san_pham_id": sp.id,
        "don_vi_id": dv,
        "so_lo": "lo01",
        "han_su_dung": ngay(400),
        "so_luong": 2,
        "gia_nhap": 60000,
        **ghi_de,
    }


async def lap(c, n, dong_, **ghi_de):
    return await c.post(GOC, json={"nha_cung_cap_id": n, "dong": dong_, **ghi_de})


async def test_nhap_lo_moi_quy_doi_gia_von_the_kho_va_nhat_ky(dang_nhap_kho, db):
    sp, hop, _ = await san_pham(db)
    r = await lap(dang_nhap_kho, await ncc(dang_nhap_kho), [dong(sp, hop)], so_hoa_don_ncc="HD1")
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["ma_phieu"].startswith("PN") and p["tong_tien"] == "120000.00" and p["canh_bao"] == []
    d = p["dong"][0]
    assert (d["so_luong"], d["so_luong_co_so"], d["so_lo"], d["thanh_tien"]) == (2, 200, "LO01", "120000.00")
    lo = (await db.execute(select(LoThuoc).where(LoThuoc.id == d["lo_id"]))).scalar_one()
    assert (lo.so_luong_ton, lo.gia_nhap, lo.trang_thai.value) == (200, 600, "dang_ban")
    the = (await db.execute(select(BienDongKho).where(BienDongKho.lo_id == lo.id))).scalars().all()
    assert [(t.loai.value, t.so_luong, t.ton_sau, t.chung_tu_loai, t.chung_tu_id) for t in the] == [
        ("nhap_kho", 200, 200, "phieu_nhap", p["id"])
    ]
    assert (await dang_nhap_kho.get(f"{GOC}/{p['id']}")).json()["dong"][0]["lo_id"] == lo.id


async def test_cong_vao_lo_cu_tinh_binh_quan_gia_quyen(dang_nhap_kho, db):
    sp, hop, vien = await san_pham(db)
    n = await ncc(dang_nhap_kho)
    await lap(dang_nhap_kho, n, [dong(sp, hop)])  # 200 viên, giá 600
    r = await lap(dang_nhap_kho, n, [dong(sp, vien, gia_nhap=1000, so_luong=100)])  # +100 viên giá 1000
    assert r.status_code == 201, r.text
    lo = (await db.execute(select(LoThuoc).where(LoThuoc.id == r.json()["dong"][0]["lo_id"]))).scalar_one()
    assert (lo.so_luong_ton, lo.gia_nhap) == (300, 733)  # (200*600 + 100*1000)/300 = 733,33


async def test_hai_dong_cung_lo_trong_mot_phieu_cung_cong_vao_mot_lo(dang_nhap_kho, db):
    sp, hop, _ = await san_pham(db)
    r = await lap(dang_nhap_kho, await ncc(dang_nhap_kho), [dong(sp, hop), dong(sp, hop, so_luong=1, gia_nhap=80000)])
    assert r.status_code == 201
    ids = {d["lo_id"] for d in r.json()["dong"]}
    assert len(ids) == 1
    lo = (await db.execute(select(LoThuoc).where(LoThuoc.id == ids.pop()))).scalar_one()
    assert (lo.so_luong_ton, lo.gia_nhap) == (300, 667)  # (200*600 + 100*800)/300


async def test_han_ngan_can_xac_nhan_roi_moi_ghi(dang_nhap_kho, db):
    sp, hop, _ = await san_pham(db)
    n = await ncc(dang_nhap_kho)
    r = await lap(dang_nhap_kho, n, [dong(sp, hop, han_su_dung=ngay(60))])
    assert r.status_code == 409 and r.json()["ma_loi"] == "CAN_XAC_NHAN_CANH_BAO"
    assert r.json()["chi_tiet"]["canh_bao"][0]["dong"] == 0
    assert (await db.execute(select(LoThuoc).where(LoThuoc.san_pham_id == sp.id))).first() is None
    r = await lap(dang_nhap_kho, n, [dong(sp, hop, han_su_dung=ngay(60))], xac_nhan_canh_bao=True)
    assert r.status_code == 201 and r.json()["canh_bao"][0]["loai"] == "han_su_dung_ngan"
    lo = (await db.execute(select(LoThuoc).where(LoThuoc.san_pham_id == sp.id))).scalar_one()
    assert lo.trang_thai.value == "can_han"  # 60 ngày < ngưỡng cận hạn 90


async def test_cung_so_lo_khac_han_la_409_ca_trong_phieu_va_voi_lo_co_san(dang_nhap_kho, db):
    sp, hop, _ = await san_pham(db)
    n = await ncc(dang_nhap_kho)
    r = await lap(dang_nhap_kho, n, [dong(sp, hop), dong(sp, hop, han_su_dung=ngay(500))])
    assert (
        r.status_code == 409
        and r.json()["ma_loi"] == "TRUNG_DU_LIEU"
        and r.json()["chi_tiet"]["truong"] == "dong.1.so_lo"
    )
    assert (await lap(dang_nhap_kho, n, [dong(sp, hop)])).status_code == 201
    r = await lap(dang_nhap_kho, n, [dong(sp, hop, han_su_dung=ngay(500))])
    assert r.status_code == 409 and r.json()["ma_loi"] == "TRUNG_DU_LIEU"


async def test_lo_khoa_thu_hoi_khong_nhap_them_duoc(dang_nhap_kho, db):
    sp, hop, _ = await san_pham(db)
    n = await ncc(dang_nhap_kho)
    r = await lap(dang_nhap_kho, n, [dong(sp, hop)])
    lo = (await db.execute(select(LoThuoc).where(LoThuoc.id == r.json()["dong"][0]["lo_id"]))).scalar_one()
    for tt in ("khoa", "thu_hoi"):
        lo.trang_thai = tt
        await db.flush()
        r = await lap(dang_nhap_kho, n, [dong(sp, hop)])
        assert r.status_code == 409 and r.json()["ma_loi"] == "LO_KHONG_NHAP_DUOC", tt


async def test_du_lieu_sai_la_400_va_khong_ghi_gi(dang_nhap_kho, db):
    sp, hop, _ = await san_pham(db)
    khac, hop_khac, _ = await san_pham(db)
    n = await ncc(dang_nhap_kho)
    sai = [
        dict(han_su_dung=ngay(0)),
        dict(han_su_dung=ngay(366 * 16)),
        dict(ngay_san_xuat=ngay(1)),
        dict(ngay_san_xuat=ngay(500)),
        dict(so_luong=0),
        dict(so_luong=1_000_001),
        dict(gia_nhap=-1),
        dict(gia_nhap="1.5"),
        dict(don_vi_id=hop_khac),
        dict(san_pham_id=999_999_999),
    ]
    for ghi_de in sai:
        r = await lap(dang_nhap_kho, n, [dong(sp, hop, **ghi_de)])
        assert r.status_code == 400, (ghi_de, r.text)
    assert (await lap(dang_nhap_kho, 999_999, [dong(sp, hop)])).status_code == 400
    assert (await lap(dang_nhap_kho, n, [])).status_code == 400
    assert (await db.execute(select(LoThuoc).where(LoThuoc.san_pham_id == sp.id))).first() is None


async def test_ncc_da_ngung_va_san_pham_da_xoa_bi_tu_choi(dang_nhap_kho, db):
    from app.core.thoi_gian import bay_gio_utc

    sp, hop, _ = await san_pham(db)
    c = dang_nhap_kho
    r = await c.post("/api/v1/noi-bo/nha-cung-cap", json={"ten": "Ngừng"})
    await c.delete(f"/api/v1/noi-bo/nha-cung-cap/{r.json()['id']}", params={"phien_ban": r.json()["phien_ban"]})
    assert (await lap(c, r.json()["id"], [dong(sp, hop)])).status_code == 400
    sp.deleted_at = bay_gio_utc()
    await db.flush()
    assert (await lap(c, await ncc(c), [dong(sp, hop)])).status_code == 400


async def test_phieu_khong_sua_khong_xoa_va_phan_quyen(clients_theo_vai_tro, db):
    sp, hop, _ = await san_pham(db)
    kho, admin, ds = (clients_theo_vai_tro[k] for k in ("WAREHOUSE", "ADMIN", "PHARMACIST"))
    p = (await lap(kho, await ncc(kho), [dong(sp, hop)])).json()
    assert (await kho.patch(f"{GOC}/{p['id']}", json={})).status_code == 405
    assert (await kho.delete(f"{GOC}/{p['id']}")).status_code == 405
    assert (await kho.put(f"{GOC}/{p['id']}", json={})).status_code == 405
    assert (await admin.get(f"{GOC}/{p['id']}")).status_code == 200
    assert (await lap(admin, p["nha_cung_cap"]["id"], [dong(sp, hop)])).status_code == 403
    assert (await ds.get(GOC)).status_code == 403


async def test_danh_sach_loc_theo_ma_ncc_va_ngay(dang_nhap_kho, db):
    sp, hop, _ = await san_pham(db)
    c = dang_nhap_kho
    n1, n2 = await ncc(c), await ncc(c)
    p1 = (await lap(c, n1, [dong(sp, hop)], so_hoa_don_ncc="HD-AAA")).json()
    await lap(c, n2, [dong(sp, hop)])
    assert (await c.get(GOC)).json()["tong"] == 2
    assert [x["id"] for x in (await c.get(GOC, params={"nha_cung_cap_id": n1})).json()["du_lieu"]] == [p1["id"]]
    assert (await c.get(GOC, params={"q": "hd-aaa"})).json()["tong"] == 1
    hom_nay = hom_nay_vn().isoformat()
    assert (await c.get(GOC, params={"tu_ngay": hom_nay, "den_ngay": hom_nay})).json()["tong"] == 2
    assert (await c.get(GOC, params={"den_ngay": ngay(-1)})).json()["tong"] == 0


async def test_tra_cuu_san_pham_theo_ten_sku_va_ma_vach(dang_nhap_kho, db):
    sp, hop, _ = await san_pham(db)
    sp.ten = "Panadol Extra"
    sp.don_vi_theo_ten["hộp"].ma_vach = "8934567890123"
    await db.flush()
    c = dang_nhap_kho
    for q in ("panadol", "PANADOL EXTRA".lower(), sp.sku.lower(), "8934567890123"):
        r = (await c.get(f"{GOC}/tra-cuu-san-pham", params={"q": q})).json()
        assert [x["id"] for x in r] == [sp.id], q
    r = (await c.get(f"{GOC}/tra-cuu-san-pham", params={"q": "8934567890123"})).json()[0]
    assert {d["ten_don_vi"] for d in r["don_vi"]} == {"viên", "hộp"} and r["don_vi_mac_dinh_id"] is not None
    assert (await c.get(f"{GOC}/tra-cuu-san-pham", params={"q": "  "})).json() == []

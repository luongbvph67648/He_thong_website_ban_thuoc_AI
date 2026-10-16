"""KVL07: giỏ hàng. Thuốc kê đơn bị chặn ở service; giới hạn tính theo đơn vị cơ sở."""

from decimal import Decimal

from sqlalchemy import select

from app.core.bao_mat import tao_access_token
from app.models.ai import LuatMuaKem
from app.models.ban_hang import CtGioHang
from tests.factories import tao_khach, tao_lo, tao_san_pham

GIO = "/api/v1/toi/gio-hang"
VIEN, HOP = (
    {"ten_don_vi": "viên", "he_so": 1, "gia_ban": 1000, "la_mac_dinh": True},
    {
        "ten_don_vi": "hộp",
        "he_so": 10,
        "gia_ban": 9500,
        "la_mac_dinh": False,
    },
)


async def sp_thuong(db, **kw):
    sp = await tao_san_pham(db, don_vi=[VIEN, HOP], **kw)
    await tao_lo(db, sp, so_luong=500)
    return sp


def dong(sp, don_vi="viên", so_luong=1):
    return {"san_pham_id": sp.id, "don_vi_id": sp.don_vi_theo_ten[don_vi].id, "so_luong": so_luong}


async def test_them_cong_don_va_tinh_tien_theo_don_vi(dang_nhap_khach, db):
    sp = await sp_thuong(db)
    c = dang_nhap_khach
    assert (await c.post(f"{GIO}/dong", json=dong(sp, "viên", 3))).status_code == 200
    r = (await c.post(f"{GIO}/dong", json=dong(sp, "viên", 2))).json()  # cộng dồn vào cùng dòng
    assert len(r["dong"]) == 1 and r["dong"][0]["so_luong"] == 5 and r["dong"][0]["thanh_tien"] == "5000.00"
    r = (await c.post(f"{GIO}/dong", json=dong(sp, "hộp", 2))).json()
    assert len(r["dong"]) == 2 and r["tam_tinh"] == "24000.00" and r["tong_so_luong"] == 7
    assert r["dong"][0]["ton_kha_dung_don_vi"] == 500 and r["dong"][1]["ton_kha_dung_don_vi"] == 50
    assert (await c.get(GIO)).json() == r


async def test_thuoc_ke_don_bi_chan_o_moi_duong_vao(dang_nhap_khach, db):
    rx = await tao_san_pham(db, loai="thuoc_ke_don")
    ok = await sp_thuong(db)
    c = dang_nhap_khach
    r = await c.post(f"{GIO}/dong", json=dong(rx))
    assert r.status_code == 422 and r.json()["ma_loi"] == "THUOC_KE_DON_KHONG_VAO_GIO"
    g = (await c.put(f"{GIO}/gop", json={"dong": [dong(rx), dong(ok)]})).json()
    assert [b["ly_do"] for b in g["bo_qua"]] == ["thuoc_ke_don"] and len(g["gio_hang"]["dong"]) == 1
    assert (await db.scalar(select(CtGioHang.id).where(CtGioHang.san_pham_id == rx.id))) is None
    v = (await c.post("/api/v1/gio-hang/xem", json={"dong": [dong(rx)]})).json()
    assert v["dong"][0]["mua_duoc"] is False and v["dong"][0]["ly_do"] == "thuoc_ke_don" and v["tam_tinh"] == "0.00"


async def test_don_vi_khong_ban_online_va_khong_thuoc_san_pham(dang_nhap_khach, db):
    sp = await tao_san_pham(db, don_vi=[VIEN, {**HOP, "ban_online": False}])
    khac = await sp_thuong(db)
    c = dang_nhap_khach
    r = await c.post(f"{GIO}/dong", json=dong(sp, "hộp"))
    assert r.status_code == 400 and r.json()["chi_tiet"][0]["truong"] == "don_vi_id"
    sai = {"san_pham_id": sp.id, "don_vi_id": khac.don_vi_theo_ten["viên"].id, "so_luong": 1}
    assert (await c.post(f"{GIO}/dong", json=sai)).status_code == 400


async def test_san_pham_an_hoac_ngung_kinh_doanh_la_404(dang_nhap_khach, db):
    sp = await sp_thuong(db, trang_thai="ngung_kinh_doanh")
    assert (await dang_nhap_khach.post(f"{GIO}/dong", json=dong(sp))).status_code == 404


async def test_gioi_han_moi_don_tinh_theo_don_vi_co_so_tren_ca_san_pham(dang_nhap_khach, db):
    sp = await sp_thuong(db, so_luong_toi_da_moi_don=25)
    c = dang_nhap_khach
    assert (await c.post(f"{GIO}/dong", json=dong(sp, "hộp", 2))).status_code == 200  # 20 viên
    r = await c.post(f"{GIO}/dong", json=dong(sp, "viên", 6))  # 26 > 25 dù khác đơn vị
    assert r.status_code == 422 and r.json()["ma_loi"] == "VUOT_SO_LUONG_TOI_DA"
    assert r.json()["chi_tiet"] == {"san_pham_id": sp.id, "toi_da": 25}
    assert (await c.post(f"{GIO}/dong", json=dong(sp, "viên", 5))).status_code == 200  # đúng 25


async def test_gop_cong_don_cat_theo_gioi_han_va_khong_loi_ca_lan(dang_nhap_khach, db):
    sp = await sp_thuong(db, so_luong_toi_da_moi_don=25)
    c = dang_nhap_khach
    await c.post(f"{GIO}/dong", json=dong(sp, "viên", 10))
    g = (await c.put(f"{GIO}/gop", json={"dong": [dong(sp, "viên", 100), dong(sp, "hộp", 5)]})).json()
    # viên: 10 + 100 cắt về 25; hộp: không còn chỗ (25 viên đã đủ) nên bị bỏ qua
    assert [(d["so_luong"]) for d in g["gio_hang"]["dong"]] == [25]
    assert g["bo_qua"] == [{"san_pham_id": sp.id, "don_vi_id": sp.don_vi_theo_ten["hộp"].id, "ly_do": "vuot_toi_da"}]
    g2 = (await c.put(f"{GIO}/gop", json={"dong": [dong(sp, "viên", 3)]})).json()
    assert g2["bo_qua"][0]["ly_do"] == "vuot_toi_da" and g2["gio_hang"]["dong"][0]["so_luong"] == 25


async def test_sua_so_luong_doi_don_vi_gop_dong_va_xoa(dang_nhap_khach, db):
    sp = await sp_thuong(db)
    c = dang_nhap_khach
    await c.post(f"{GIO}/dong", json=dong(sp, "viên", 3))
    r = (await c.post(f"{GIO}/dong", json=dong(sp, "hộp", 2))).json()
    d_vien, d_hop = r["dong"][0]["dong_id"], r["dong"][1]["dong_id"]
    r = (await c.put(f"{GIO}/dong/{d_vien}", json={"so_luong": 7})).json()
    assert r["dong"][0]["so_luong"] == 7
    r = (await c.put(f"{GIO}/dong/{d_vien}", json={"don_vi_id": sp.don_vi_theo_ten["hộp"].id})).json()
    assert len(r["dong"]) == 1 and r["dong"][0]["so_luong"] == 9 and r["dong"][0]["dong_id"] == d_hop
    assert (await c.delete(f"{GIO}/dong/{d_hop}")).json()["dong"] == []
    assert (await c.delete(f"{GIO}/dong/{d_hop}")).status_code == 404
    await c.post(f"{GIO}/dong", json=dong(sp))
    assert (await c.delete(GIO)).status_code == 204 and (await c.get(GIO)).json()["dong"] == []


async def test_khach_khong_dung_duoc_dong_cua_khach_khac(client, dang_nhap_khach, db):
    sp = await sp_thuong(db)
    d = (await dang_nhap_khach.post(f"{GIO}/dong", json=dong(sp))).json()["dong"][0]["dong_id"]
    khac = await tao_khach(db)
    h = {"Authorization": f"Bearer {tao_access_token(khac.id, 'khach')}"}
    assert (await client.put(f"{GIO}/dong/{d}", json={"so_luong": 9}, headers=h)).status_code == 404
    assert (await client.delete(f"{GIO}/dong/{d}", headers=h)).status_code == 404
    assert (await client.get(GIO, headers=h)).json()["dong"] == []
    assert (await client.get(GIO)).status_code == 401


async def test_dong_da_luu_het_hop_le_khi_san_pham_doi_loai(dang_nhap_khach, db):
    sp = await sp_thuong(db)
    c = dang_nhap_khach
    await c.post(f"{GIO}/dong", json=dong(sp, "viên", 2))
    sp.loai_san_pham = "thuoc_ke_don"
    await db.flush()
    r = (await c.get(GIO)).json()
    assert r["dong"][0]["mua_duoc"] is False and r["dong"][0]["ly_do"] == "thuoc_ke_don"
    assert r["tam_tinh"] == "0.00" and r["tong_so_luong"] == 0


async def test_xem_gio_vang_lai_lam_tron_dong_va_khong_luu(client, db):
    sp = await tao_san_pham(db, don_vi=[{**VIEN, "gia_ban": Decimal("333.50")}])
    r = (await client.post("/api/v1/gio-hang/xem", json={"dong": [dong(sp, "viên", 3)]})).json()
    assert r["dong"][0]["thanh_tien"] == "1001.00" and r["dong"][0]["dong_id"] is None  # 1000.5 làm tròn half-up
    assert (await client.post("/api/v1/gio-hang/xem", json={"dong": [dong(sp)] * 101})).status_code == 400
    assert (await db.scalar(select(CtGioHang.id).limit(1))) is None


async def test_mua_kem_xep_hang_loai_thuoc_ke_don_va_rong_thi_an(client, db):
    a, b, c, rx = (
        await sp_thuong(db),
        await sp_thuong(db),
        await sp_thuong(db),
        await tao_san_pham(db, loai="thuoc_ke_don"),
    )
    assert (await client.get("/api/v1/gio-hang/mua-kem", params={"san_pham_id": a.id})).json() == []
    for dich, lift in ((b, 1.5), (c, 3.0), (rx, 9.0), (a, 5.0)):
        db.add(LuatMuaKem(san_pham_a_id=a.id, san_pham_b_id=dich.id, support=0.1, confidence=0.5, lift=lift))
    await db.flush()
    r = (await client.get("/api/v1/gio-hang/mua-kem", params={"san_pham_id": a.id})).json()
    assert [x["id"] for x in r] == [c.id, b.id]  # không thuốc kê đơn, không chính sản phẩm trong giỏ
    r2 = (await client.get("/api/v1/gio-hang/mua-kem", params=[("san_pham_id", a.id), ("san_pham_id", c.id)])).json()
    assert [x["id"] for x in r2] == [b.id]
    assert (await client.get("/api/v1/gio-hang/mua-kem")).json() == []

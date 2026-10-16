"""KHO07, KHO08: kiểm kê và phiếu điều chỉnh tồn (chưa đổi tồn cho đến khi Admin duyệt ở T3.4)."""

from sqlalchemy import func, select

from app.models.kho import PhieuDieuChinh
from tests.factories import tao_danh_muc, tao_lo, tao_san_pham

KK = "/api/v1/noi-bo/kiem-ke"
DC = "/api/v1/noi-bo/dieu-chinh"


async def tao_kk(c, **than):
    r = await c.post(KK, json=than)
    assert r.status_code == 201, r.text
    return r.json()


async def chot_voi(c, kk, thuc_te: dict[int, int]):
    r = await c.put(
        f"{KK}/{kk['id']}/so-luong", json={"dong": [{"lo_id": k, "so_luong_thuc_te": v} for k, v in thuc_te.items()]}
    )
    assert r.status_code == 200, r.text
    return await c.post(f"{KK}/{kk['id']}/chot")


async def test_chup_ton_so_sach_cua_lo_con_ton_va_bo_qua_lo_het_hang(dang_nhap_kho, db):
    sp = await tao_san_pham(db)
    lo1 = await tao_lo(db, sp, so_luong=10)
    await tao_lo(db, sp, so_luong=0)
    kk = await tao_kk(dang_nhap_kho)
    d = [x for x in kk["dong"] if x["lo_id"] == lo1.id]
    assert kk["ma_phieu"].startswith("KK") and kk["trang_thai"] == "dang_kiem" and kk["danh_muc"] is None
    assert d[0]["so_luong_so_sach"] == 10 and d[0]["so_luong_thuc_te"] is None and d[0]["chenh_lech"] is None
    assert all(x["so_luong_so_sach"] > 0 for x in kk["dong"])


async def test_kiem_ke_theo_danh_muc_gom_danh_muc_con(dang_nhap_kho, db):
    goc = await tao_danh_muc(db)
    con = await tao_danh_muc(db, cha=goc)
    sp_con = await tao_san_pham(db, danh_muc_id=con.id)
    sp_khac = await tao_san_pham(db)
    lo_con = await tao_lo(db, sp_con, so_luong=3)
    lo_khac = await tao_lo(db, sp_khac, so_luong=3)
    kk = await tao_kk(dang_nhap_kho, danh_muc_id=goc.id)
    ids = {x["lo_id"] for x in kk["dong"]}
    assert lo_con.id in ids and lo_khac.id not in ids and kk["danh_muc"]["id"] == goc.id
    assert (await dang_nhap_kho.post(KK, json={"danh_muc_id": 999999})).status_code == 400


async def test_nhap_thuc_te_tinh_chenh_lech_chot_khong_doi_ton(dang_nhap_kho, db):
    sp = await tao_san_pham(db)
    lo1, lo2 = await tao_lo(db, sp, so_luong=10), await tao_lo(db, sp, so_luong=5)
    kk = await tao_kk(dang_nhap_kho, danh_muc_id=sp.danh_muc_id)
    r = await dang_nhap_kho.post(f"{KK}/{kk['id']}/chot")
    assert r.status_code == 400 and r.json()["chi_tiet"]["so_dong_chua_nhap"] == 2
    r = await chot_voi(dang_nhap_kho, kk, {lo1.id: 8, lo2.id: 5})
    assert r.status_code == 200
    ct = r.json()
    assert ct["trang_thai"] == "da_chot" and ct["chot_luc"] and ct["so_dong_lech"] == 1
    assert {x["lo_id"]: x["chenh_lech"] for x in ct["dong"]} == {lo1.id: -2, lo2.id: 0}
    await db.refresh(lo1)
    assert lo1.so_luong_ton == 10  # chốt kiểm kê không đổi tồn


async def test_phieu_da_chot_khong_nhap_xoa_chot_lai(dang_nhap_kho, db):
    sp = await tao_san_pham(db)
    lo = await tao_lo(db, sp, so_luong=4)
    kk = await tao_kk(dang_nhap_kho, danh_muc_id=sp.danh_muc_id)
    await chot_voi(dang_nhap_kho, kk, {lo.id: 4})
    for r in (
        await dang_nhap_kho.put(f"{KK}/{kk['id']}/so-luong", json={"dong": [{"lo_id": lo.id, "so_luong_thuc_te": 1}]}),
        await dang_nhap_kho.post(f"{KK}/{kk['id']}/chot"),
        await dang_nhap_kho.delete(f"{KK}/{kk['id']}"),
    ):
        assert r.status_code == 409 and r.json()["ma_loi"] == "CHUYEN_TRANG_THAI_KHONG_HOP_LE"


async def test_nhap_so_luong_sai_la_400(dang_nhap_kho, db):
    sp = await tao_san_pham(db)
    lo, lo_ngoai = await tao_lo(db, sp, so_luong=4), await tao_lo(db, so_luong=4)
    kk = await tao_kk(dang_nhap_kho, danh_muc_id=sp.danh_muc_id)
    url = f"{KK}/{kk['id']}/so-luong"
    for dong in (
        [{"lo_id": lo_ngoai.id, "so_luong_thuc_te": 1}],
        [{"lo_id": lo.id, "so_luong_thuc_te": -1}],
        [{"lo_id": lo.id, "so_luong_thuc_te": 1.5}],
        [{"lo_id": lo.id, "so_luong_thuc_te": 1}, {"lo_id": lo.id, "so_luong_thuc_te": 2}],
        [],
    ):
        assert (await dang_nhap_kho.put(url, json={"dong": dong})).status_code == 400, dong


async def test_xoa_phieu_dang_kiem(dang_nhap_kho, db):
    sp = await tao_san_pham(db)
    await tao_lo(db, sp, so_luong=4)
    kk = await tao_kk(dang_nhap_kho, danh_muc_id=sp.danh_muc_id)
    assert (await dang_nhap_kho.delete(f"{KK}/{kk['id']}")).status_code == 204
    assert (await dang_nhap_kho.get(f"{KK}/{kk['id']}")).status_code == 404


async def test_dieu_chinh_tu_kiem_ke_chi_dong_lech_cho_duyet_va_ton_khong_doi(dang_nhap_kho, db):
    sp = await tao_san_pham(db)
    lo1, lo2 = await tao_lo(db, sp, so_luong=10), await tao_lo(db, sp, so_luong=5)
    kk = await tao_kk(dang_nhap_kho, danh_muc_id=sp.danh_muc_id)
    assert (
        await dang_nhap_kho.post(DC, json={"ly_do": "x", "phieu_kiem_ke_id": kk["id"]})
    ).status_code == 409  # chưa chốt
    await chot_voi(dang_nhap_kho, kk, {lo1.id: 12, lo2.id: 5})
    r = await dang_nhap_kho.post(DC, json={"ly_do": "  Kiểm kê quý 3 ", "phieu_kiem_ke_id": kk["id"]})
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["ma_phieu"].startswith("DC") and p["trang_thai_duyet"] == "cho_duyet" and p["ly_do"] == "Kiểm kê quý 3"
    assert [(d["lo_id"], d["so_luong_thay_doi"], d["so_luong_ton_hien_tai"]) for d in p["dong"]] == [(lo1.id, 2, 10)]
    assert p["ma_phieu_kiem_ke"] == kk["ma_phieu"]
    await db.refresh(lo1)
    assert lo1.so_luong_ton == 10
    r2 = await dang_nhap_kho.post(DC, json={"ly_do": "lại", "phieu_kiem_ke_id": kk["id"]})
    assert r2.status_code == 409 and r2.json()["ma_loi"] == "TRUNG_DU_LIEU"
    # bị từ chối thì lập lại được
    pd = (await db.execute(select(PhieuDieuChinh).where(PhieuDieuChinh.id == p["id"]))).scalar_one()
    pd.trang_thai_duyet = "tu_choi"
    await db.flush()
    assert (await dang_nhap_kho.post(DC, json={"ly_do": "lại", "phieu_kiem_ke_id": kk["id"]})).status_code == 201
    assert (await dang_nhap_kho.delete(f"{KK}/{kk['id']}")).status_code == 409  # đã có phiếu điều chỉnh


async def test_dieu_chinh_khong_co_dong_lech_la_400(dang_nhap_kho, db):
    sp = await tao_san_pham(db)
    lo = await tao_lo(db, sp, so_luong=3)
    kk = await tao_kk(dang_nhap_kho, danh_muc_id=sp.danh_muc_id)
    await chot_voi(dang_nhap_kho, kk, {lo.id: 3})
    r = await dang_nhap_kho.post(DC, json={"ly_do": "x", "phieu_kiem_ke_id": kk["id"]})
    assert r.status_code == 400
    assert (await db.scalar(select(func.count()).select_from(PhieuDieuChinh))) == 0


async def test_dieu_chinh_lap_tay_va_dau_vao_sai(dang_nhap_kho, db):
    lo = await tao_lo(db, so_luong=5)
    r = await dang_nhap_kho.post(
        DC, json={"ly_do": "Nhập nhầm số lượng", "dong": [{"lo_id": lo.id, "so_luong_thay_doi": -3}]}
    )
    assert r.status_code == 201 and r.json()["phieu_kiem_ke_id"] is None
    await db.refresh(lo)
    assert lo.so_luong_ton == 5
    for than in (
        {"ly_do": "x"},
        {"ly_do": "x", "phieu_kiem_ke_id": 1, "dong": [{"lo_id": lo.id, "so_luong_thay_doi": 1}]},
        {"ly_do": "  ", "dong": [{"lo_id": lo.id, "so_luong_thay_doi": 1}]},
        {"ly_do": "x", "dong": [{"lo_id": lo.id, "so_luong_thay_doi": 0}]},
        {"ly_do": "x", "dong": [{"lo_id": 999999, "so_luong_thay_doi": 1}]},
        {"ly_do": "x", "dong": [{"lo_id": lo.id, "so_luong_thay_doi": 1}, {"lo_id": lo.id, "so_luong_thay_doi": 2}]},
    ):
        assert (await dang_nhap_kho.post(DC, json=than)).status_code == 400, than
    lst = (await dang_nhap_kho.get(DC)).json()
    assert lst["tong"] == 1 and lst["du_lieu"][0]["so_dong"] == 1


async def test_phan_quyen_kiem_ke_va_dieu_chinh(clients_theo_vai_tro, db):
    sp = await tao_san_pham(db)
    await tao_lo(db, sp, so_luong=2)
    kho, admin, ds = (clients_theo_vai_tro[k] for k in ("WAREHOUSE", "ADMIN", "PHARMACIST"))
    kk = await tao_kk(kho, danh_muc_id=sp.danh_muc_id)
    assert (await admin.get(f"{KK}/{kk['id']}")).status_code == 200  # Admin xem
    assert (await admin.post(KK, json={})).status_code == 403
    assert (await admin.post(f"{KK}/{kk['id']}/chot")).status_code == 403
    assert (await ds.get(KK)).status_code == 403
    assert (await admin.get(DC)).status_code == 403 and (await ds.get(DC)).status_code == 403

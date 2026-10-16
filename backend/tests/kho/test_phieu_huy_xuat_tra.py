"""KHO09, KHO11, AD12: phiếu hủy, phiếu xuất trả NCC, phiếu điều chỉnh và luồng duyệt (spec 06 mục 3.18)."""

import pytest
from sqlalchemy import select

from app.models.enums import KhuTon, LoaiBienDong, TrangThaiDuyet
from app.models.khach_hang import ThongBao
from app.models.kho import BienDongKho, CtPhieuHuy, NhaCungCap, PhieuDieuChinh, PhieuHuy
from tests.factories import tao_lo

HUY = "/api/v1/noi-bo/phieu-huy"
XT = "/api/v1/noi-bo/xuat-tra"
DC = "/api/v1/noi-bo/dieu-chinh"
DUYET = "/api/v1/noi-bo/duyet-phieu"


async def tao_ncc(db) -> NhaCungCap:
    ncc = NhaCungCap(ten="NCC thử nghiệm")
    db.add(ncc)
    await db.flush()
    return ncc


async def lap_huy(c, lo_id, so_luong, tu_khu="kho_ban", ly_do="het_han"):
    return await c.post(HUY, json={"ly_do": ly_do, "dong": [{"lo_id": lo_id, "tu_khu": tu_khu, "so_luong": so_luong}]})


async def lap_xt(c, ncc_id, lo_id, so_luong, tu_khu="kho_ban", **them):
    dong = {"lo_id": lo_id, "tu_khu": tu_khu, "so_luong": so_luong, **them}
    return await c.post(XT, json={"nha_cung_cap_id": ncc_id, "ly_do": "Cận hạn", "dong": [dong]})


async def lo_co_biet_tru(db, ton=10, biet_tru=4):
    lo = await tao_lo(db, so_luong=ton)
    lo.so_luong_biet_tru = biet_tru  # bất biến 3 chấp nhận biệt trữ có thẻ kho; dựng thẻ kho tương ứng bên dưới
    db.add(
        BienDongKho(
            lo_id=lo.id,
            loai=LoaiBienDong.nhan_tra_ve,
            khu=KhuTon.biet_tru,
            so_luong=biet_tru,
            ton_sau=biet_tru,
            chung_tu_loai="yeu_cau_doi_tra",
            chung_tu_id=0,
        )
    )
    await db.flush()
    return lo


# --- Lập phiếu -------------------------------------------------------------------------------------------------------


async def test_lap_phieu_huy_cho_duyet_ton_chua_doi(dang_nhap_kho, db):
    lo = await tao_lo(db, so_luong=10)
    r = await lap_huy(dang_nhap_kho, lo.id, 4)
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["ma_phieu"].startswith("PH") and p["trang_thai_duyet"] == "cho_duyet" and p["nguoi_duyet"] is None
    assert p["dong"][0]["so_luong"] == 4 and p["dong"][0]["tu_khu"] == "kho_ban"
    await db.refresh(lo)
    assert lo.so_luong_ton == 10  # chỉ trừ khi duyệt


@pytest.mark.khong_kiem_bat_bien  # giả lập hàng đang giữ không có phân bổ
async def test_lap_phieu_khong_vuot_ton_khu_da_chon(dang_nhap_kho, db):
    lo = await lo_co_biet_tru(db, ton=10, biet_tru=4)
    lo.so_luong_giu = 3
    await db.flush()
    r = await lap_huy(dang_nhap_kho, lo.id, 8)  # khả dụng khu bán = 10 - 3 = 7
    assert r.status_code == 409 and r.json()["ma_loi"] == "HET_HANG" and r.json()["chi_tiet"]["con_lai"] == 7
    assert (await lap_huy(dang_nhap_kho, lo.id, 5, tu_khu="biet_tru")).json()["ma_loi"] == "HET_HANG"
    assert (await lap_huy(dang_nhap_kho, lo.id, 4, tu_khu="biet_tru")).status_code == 201
    assert (await lap_huy(dang_nhap_kho, lo.id, 7)).status_code == 201


async def test_lap_phieu_dau_vao_sai_la_400(dang_nhap_kho, db):
    lo = await tao_lo(db, so_luong=5)
    d = {"lo_id": lo.id, "tu_khu": "kho_ban", "so_luong": 1}
    for than in (
        {"ly_do": "het_han", "dong": []},
        {"ly_do": "khong_co", "dong": [d]},
        {"ly_do": "het_han", "dong": [{**d, "so_luong": 0}]},
        {"ly_do": "het_han", "dong": [{**d, "so_luong": -1}]},
        {"ly_do": "het_han", "dong": [{**d, "lo_id": 999999}]},
        {"ly_do": "het_han", "dong": [d, d]},  # trùng (lô, khu)
        {"ly_do": "het_han", "dong": [{**d, "tu_khu": "khac"}]},
    ):
        assert (await dang_nhap_kho.post(HUY, json=than)).status_code == 400, than


async def test_lap_phieu_xuat_tra_mac_dinh_don_gia_theo_gia_nhap(dang_nhap_kho, db):
    lo = await tao_lo(db, so_luong=10, gia_nhap=1500)
    ncc = await tao_ncc(db)
    r = await lap_xt(dang_nhap_kho, ncc.id, lo.id, 3)
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["ma_phieu"].startswith("XT") and p["trang_thai_duyet"] == "cho_duyet" and p["nha_cung_cap"]["id"] == ncc.id
    assert float(p["dong"][0]["don_gia"]) == 1500
    p2 = (await lap_xt(dang_nhap_kho, ncc.id, lo.id, 1, don_gia=1200)).json()
    assert float(p2["dong"][0]["don_gia"]) == 1200
    assert (await lap_xt(dang_nhap_kho, 999999, lo.id, 1)).status_code == 400
    ncc.deleted_at = ncc.created_at
    await db.flush()
    assert (await lap_xt(dang_nhap_kho, ncc.id, lo.id, 1)).status_code == 400


async def test_danh_sach_va_chi_tiet_phieu_cua_kho(dang_nhap_kho, db):
    lo = await tao_lo(db, so_luong=5)
    p = (await lap_huy(dang_nhap_kho, lo.id, 1)).json()
    ds = (await dang_nhap_kho.get(HUY, params={"trang_thai_duyet": "cho_duyet"})).json()
    assert ds["tong"] == 1 and ds["du_lieu"][0]["id"] == p["id"]
    assert (await dang_nhap_kho.get(f"{HUY}/{p['id']}")).json()["dong"][0]["so_lo"] == lo.so_lo
    assert (await dang_nhap_kho.get(f"{HUY}/999999")).status_code == 404


# --- Duyệt -----------------------------------------------------------------------------------------------------------


async def test_duyet_phieu_huy_tru_ton_dung_va_ghi_the_kho(dang_nhap_kho, dang_nhap_admin, db):
    lo = await lo_co_biet_tru(db, ton=10, biet_tru=4)
    r = await dang_nhap_kho.post(
        HUY,
        json={
            "ly_do": "hu_hong",
            "dong": [
                {"lo_id": lo.id, "tu_khu": "kho_ban", "so_luong": 3},
                {"lo_id": lo.id, "tu_khu": "biet_tru", "so_luong": 4},
            ],
        },
    )
    p = r.json()
    r = await dang_nhap_admin.post(f"{DUYET}/huy/{p['id']}/duyet")
    assert r.status_code == 200, r.text
    assert r.json()["trang_thai_duyet"] == "da_duyet" and r.json()["nguoi_duyet"]["id"] == dang_nhap_admin.tai_khoan.id
    await db.refresh(lo)
    assert (lo.so_luong_ton, lo.so_luong_biet_tru) == (7, 0)
    the = (
        (
            await db.execute(
                select(BienDongKho).where(BienDongKho.chung_tu_loai == "phieu_huy", BienDongKho.chung_tu_id == p["id"])
            )
        )
        .scalars()
        .all()
    )
    assert {(t.khu, t.so_luong, t.ton_sau, t.loai) for t in the} == {
        (KhuTon.kho_ban, -3, 7, LoaiBienDong.huy_hang),
        (KhuTon.biet_tru, -4, 0, LoaiBienDong.huy_hang),
    }
    assert all(t.nhan_vien_id == dang_nhap_admin.tai_khoan.id for t in the)


async def test_duyet_xuat_tra_tru_ton_va_the_kho_xuat_tra_ncc(dang_nhap_kho, dang_nhap_admin, db):
    lo = await tao_lo(db, so_luong=10)
    ncc = await tao_ncc(db)
    p = (await lap_xt(dang_nhap_kho, ncc.id, lo.id, 6)).json()
    assert (await dang_nhap_admin.post(f"{DUYET}/xuat-tra/{p['id']}/duyet")).status_code == 200
    await db.refresh(lo)
    assert lo.so_luong_ton == 4
    the = (await db.execute(select(BienDongKho).where(BienDongKho.chung_tu_loai == "phieu_xuat_tra"))).scalars().one()
    assert (the.loai, the.so_luong, the.ton_sau) == (LoaiBienDong.xuat_tra_ncc, -6, 4)


async def test_duyet_dieu_chinh_doi_ton_theo_so_luong_thay_doi(dang_nhap_kho, dang_nhap_admin, db):
    lo1, lo2 = await tao_lo(db, so_luong=10), await tao_lo(db, so_luong=5)
    p = (
        await dang_nhap_kho.post(
            DC,
            json={
                "ly_do": "Kiểm lại",
                "dong": [{"lo_id": lo1.id, "so_luong_thay_doi": -2}, {"lo_id": lo2.id, "so_luong_thay_doi": 3}],
            },
        )
    ).json()
    r = await dang_nhap_admin.post(f"{DUYET}/dieu-chinh/{p['id']}/duyet")
    assert r.status_code == 200 and r.json()["trang_thai_duyet"] == "da_duyet", r.text
    await db.refresh(lo1)
    await db.refresh(lo2)
    assert (lo1.so_luong_ton, lo2.so_luong_ton) == (8, 8)
    loai = {
        t.loai
        for t in (
            await db.execute(select(BienDongKho).where(BienDongKho.chung_tu_loai == "phieu_dieu_chinh"))
        ).scalars()
    }
    assert loai == {LoaiBienDong.dieu_chinh}


@pytest.mark.parametrize("loai", ["huy", "xuat-tra", "dieu-chinh"])
async def test_tu_duyet_bi_chan_khong_doi_ton(loai, dang_nhap_admin, db):
    """Phiếu do chính người duyệt lập (vd vai trò bị đổi sau đó) vẫn không được tự duyệt hay tự từ chối."""
    admin = dang_nhap_admin
    lo = await tao_lo(db, so_luong=10)
    nguoi = admin.tai_khoan.id
    if loai == "huy":
        p = PhieuHuy(ma_phieu="PHTD1", ly_do="khac", nguoi_lap_id=nguoi)
        db.add(p)
        await db.flush()
        db.add(CtPhieuHuy(phieu_huy_id=p.id, lo_id=lo.id, tu_khu=KhuTon.kho_ban, so_luong=2))
    elif loai == "dieu-chinh":
        from app.models.kho import CtPhieuDieuChinh

        p = PhieuDieuChinh(ma_phieu="DCTD1", ly_do="x", nguoi_lap_id=nguoi)
        db.add(p)
        await db.flush()
        db.add(CtPhieuDieuChinh(phieu_dieu_chinh_id=p.id, lo_id=lo.id, so_luong_thay_doi=-2))
    else:
        from app.models.kho import CtPhieuXuatTra, PhieuXuatTra

        ncc = await tao_ncc(db)
        p = PhieuXuatTra(ma_phieu="XTTD1", nha_cung_cap_id=ncc.id, ly_do="x", nhan_vien_id=nguoi)
        db.add(p)
        await db.flush()
        db.add(CtPhieuXuatTra(phieu_xuat_tra_id=p.id, lo_id=lo.id, tu_khu=KhuTon.kho_ban, so_luong=2))
    await db.flush()
    for hanh_dong, than in (("duyet", None), ("tu-choi", {"ly_do": "không đạt"})):
        r = await admin.post(f"{DUYET}/{loai}/{p.id}/{hanh_dong}", json=than)
        assert r.status_code == 403 and r.json()["ma_loi"] == "TU_DUYET_KHONG_DUOC", (hanh_dong, r.text)
    await db.refresh(lo)
    await db.refresh(p)
    assert lo.so_luong_ton == 10 and p.trang_thai_duyet == TrangThaiDuyet.cho_duyet


async def test_tu_choi_bat_buoc_ly_do_va_khong_doi_ton(dang_nhap_kho, dang_nhap_admin, db):
    lo = await tao_lo(db, so_luong=10)
    p = (await lap_huy(dang_nhap_kho, lo.id, 5)).json()
    url = f"{DUYET}/huy/{p['id']}/tu-choi"
    for than in ({}, {"ly_do": ""}, {"ly_do": "   "}, {"ly_do": "x" * 1001}):
        assert (await dang_nhap_admin.post(url, json=than)).status_code == 400, than
    assert (await dang_nhap_admin.post(url)).status_code == 400
    r = await dang_nhap_admin.post(url, json={"ly_do": "Còn dùng được"})
    assert r.status_code == 200, r.text
    ct = r.json()
    assert ct["trang_thai_duyet"] == "tu_choi" and ct["ly_do_tu_choi"] == "Còn dùng được" and ct["duyet_luc"]
    await db.refresh(lo)
    assert lo.so_luong_ton == 10
    assert (await db.execute(select(BienDongKho).where(BienDongKho.chung_tu_loai == "phieu_huy"))).first() is None


async def test_khong_duyet_hai_lan_va_khong_duyet_phieu_da_tu_choi(dang_nhap_kho, dang_nhap_admin, db):
    lo = await tao_lo(db, so_luong=10)
    p = (await lap_huy(dang_nhap_kho, lo.id, 4)).json()
    assert (await dang_nhap_admin.post(f"{DUYET}/huy/{p['id']}/duyet")).status_code == 200
    for hanh_dong, than in (("duyet", None), ("tu-choi", {"ly_do": "x"})):
        r = await dang_nhap_admin.post(f"{DUYET}/huy/{p['id']}/{hanh_dong}", json=than)
        assert r.status_code == 409 and r.json()["ma_loi"] == "CHUYEN_TRANG_THAI_KHONG_HOP_LE"
    await db.refresh(lo)
    assert lo.so_luong_ton == 6  # chỉ trừ một lần
    q = (await lap_huy(dang_nhap_kho, lo.id, 1)).json()
    assert (await dang_nhap_admin.post(f"{DUYET}/huy/{q['id']}/tu-choi", json={"ly_do": "x"})).status_code == 200
    assert (await dang_nhap_admin.post(f"{DUYET}/huy/{q['id']}/duyet")).status_code == 409


async def test_kiem_tra_lai_so_luong_luc_duyet_va_hoan_tac_ca_phieu(dang_nhap_kho, dang_nhap_admin, db):
    lo1, lo2 = await tao_lo(db, so_luong=10), await tao_lo(db, so_luong=10)
    r = await dang_nhap_kho.post(
        HUY,
        json={
            "ly_do": "het_han",
            "dong": [
                {"lo_id": lo1.id, "tu_khu": "kho_ban", "so_luong": 5},
                {"lo_id": lo2.id, "tu_khu": "kho_ban", "so_luong": 8},
            ],
        },
    )
    p = r.json()
    lo2.so_luong_ton = 6  # sau khi lập, lô 2 đã bán bớt (giả lập)
    lo2.so_luong_giu = 0
    db.add(
        BienDongKho(
            lo_id=lo2.id,
            loai=LoaiBienDong.xuat_ban,
            khu=KhuTon.kho_ban,
            so_luong=-4,
            ton_sau=6,
            chung_tu_loai="don_hang",
            chung_tu_id=0,
        )
    )
    await db.flush()
    r = await dang_nhap_admin.post(f"{DUYET}/huy/{p['id']}/duyet")
    assert r.status_code == 409 and r.json()["ma_loi"] == "HET_HANG"
    await db.refresh(lo1)
    await db.refresh(lo2)
    assert (lo1.so_luong_ton, lo2.so_luong_ton) == (10, 6)  # lô 1 cũng không bị trừ
    assert (await dang_nhap_admin.get(f"{DUYET}/huy/{p['id']}")).json()["trang_thai_duyet"] == "cho_duyet"


@pytest.mark.khong_kiem_bat_bien  # giả lập hàng đang giữ không có phân bổ
async def test_khong_duoc_huy_hang_dang_giu_cho_don(dang_nhap_kho, dang_nhap_admin, db):
    lo = await tao_lo(db, so_luong=10)
    p = (await lap_huy(dang_nhap_kho, lo.id, 8)).json()
    lo.so_luong_giu = 5  # đơn mới giữ hàng sau khi lập phiếu: khả dụng còn 5
    await db.flush()
    r = await dang_nhap_admin.post(f"{DUYET}/huy/{p['id']}/duyet")
    assert r.status_code == 409 and r.json()["ma_loi"] == "HET_HANG" and r.json()["chi_tiet"]["con_lai"] == 5


async def test_duyet_gui_thong_bao_cho_nguoi_lap(dang_nhap_kho, dang_nhap_admin, db):
    lo = await tao_lo(db, so_luong=10)
    p1 = (await lap_huy(dang_nhap_kho, lo.id, 1)).json()
    p2 = (await lap_huy(dang_nhap_kho, lo.id, 1)).json()
    await dang_nhap_admin.post(f"{DUYET}/huy/{p1['id']}/duyet")
    await dang_nhap_admin.post(f"{DUYET}/huy/{p2['id']}/tu-choi", json={"ly_do": "Không hợp lệ"})
    tb = (await db.execute(select(ThongBao).where(ThongBao.nhan_vien_id == dang_nhap_kho.tai_khoan.id))).scalars().all()
    assert {t.loai for t in tb} == {"phieu_kho_da_duyet", "phieu_kho_tu_choi"}
    assert all(t.lien_ket == "/nhan-vien/phieu-huy" for t in tb)


async def test_danh_sach_cho_duyet_gop_ba_loai(dang_nhap_kho, dang_nhap_admin, db):
    lo = await tao_lo(db, so_luong=20)
    ncc = await tao_ncc(db)
    h = (await lap_huy(dang_nhap_kho, lo.id, 1)).json()
    x = (await lap_xt(dang_nhap_kho, ncc.id, lo.id, 1)).json()
    d = (await dang_nhap_kho.post(DC, json={"ly_do": "x", "dong": [{"lo_id": lo.id, "so_luong_thay_doi": 1}]})).json()
    await dang_nhap_admin.post(f"{DUYET}/huy/{h['id']}/tu-choi", json={"ly_do": "x"})
    ds = (await dang_nhap_admin.get(DUYET, params={"trang_thai_duyet": "cho_duyet"})).json()
    assert ds["tong"] == 2
    assert {(i["loai"], i["id"]) for i in ds["du_lieu"]} == {("xuat-tra", x["id"]), ("dieu-chinh", d["id"])}
    assert ds["du_lieu"][0]["nguoi_lap"]["id"] == dang_nhap_kho.tai_khoan.id and ds["du_lieu"][0]["so_dong"] == 1
    tat_ca = (await dang_nhap_admin.get(DUYET)).json()
    assert tat_ca["tong"] == 3
    chi_huy = (await dang_nhap_admin.get(DUYET, params={"loai": "huy"})).json()
    assert [i["id"] for i in chi_huy["du_lieu"]] == [h["id"]]
    assert (await dang_nhap_admin.get(DUYET, params={"loai": "khac"})).status_code == 400


async def test_chi_tiet_phieu_cho_admin_theo_loai(dang_nhap_kho, dang_nhap_admin, db):
    lo = await tao_lo(db, so_luong=5)
    ncc = await tao_ncc(db)
    x = (await lap_xt(dang_nhap_kho, ncc.id, lo.id, 2)).json()
    ct = (await dang_nhap_admin.get(f"{DUYET}/xuat-tra/{x['id']}")).json()
    assert ct["ma_phieu"] == x["ma_phieu"] and ct["nha_cung_cap"]["ten"] == ncc.ten
    assert (await dang_nhap_admin.get(f"{DUYET}/xuat-tra/999999")).status_code == 404
    assert (await dang_nhap_admin.get(f"{DUYET}/loai-la/1")).status_code == 400


async def test_phan_quyen_phieu_huy_xuat_tra_va_duyet(clients_theo_vai_tro, db):
    lo = await tao_lo(db, so_luong=5)
    kho, admin, ds = (clients_theo_vai_tro[k] for k in ("WAREHOUSE", "ADMIN", "PHARMACIST"))
    ncc = await tao_ncc(db)
    p = (await lap_huy(kho, lo.id, 1)).json()
    # Admin và dược sĩ không lập phiếu; kho không duyệt.
    for c in (admin, ds):
        assert (await lap_huy(c, lo.id, 1)).status_code == 403
        assert (await lap_xt(c, ncc.id, lo.id, 1)).status_code == 403
        assert (await c.get(HUY)).status_code == 403 and (await c.get(XT)).status_code == 403
    for c in (kho, ds):
        assert (await c.get(DUYET)).status_code == 403
        assert (await c.post(f"{DUYET}/huy/{p['id']}/duyet")).status_code == 403
        assert (await c.post(f"{DUYET}/huy/{p['id']}/tu-choi", json={"ly_do": "x"})).status_code == 403

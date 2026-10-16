"""AD06 (quản lý khuyến mãi, sinh mã) và KTV04 (kiểm tra, dùng, trả lượt mã giảm giá)."""

from datetime import timedelta
from decimal import Decimal
from itertools import count

import pytest

from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc
from app.models.ban_hang import KhuyenMai, KhuyenMaiPhamVi, MaGiamGia
from app.modules.ban_hang import trang_thai as mt
from app.modules.khuyen_mai import ap_dung
from app.modules.khuyen_mai.ap_dung import DongGio, MaLyDo
from tests.factories import tao_danh_muc, tao_don, tao_khach, tao_lo, tao_nhan_vien, tao_san_pham

KM = "/api/v1/noi-bo/khuyen-mai"
KIEM_TRA = "/api/v1/toi/ma-giam-gia/kiem-tra"
GIO = "/api/v1/toi/gio-hang"
_dem = count(1)


def noi_dung(**kw):
    bay_gio = bay_gio_utc()
    return {
        "ten": "Khuyến mãi thử",
        "loai_giam": "phan_tram",
        "gia_tri": "10",
        "don_toi_thieu": "0",
        "bat_dau": (bay_gio - timedelta(days=1)).isoformat(),
        "ket_thuc": (bay_gio + timedelta(days=30)).isoformat(),
        "luot_moi_khach": 1,
        "pham_vi": "toan_bo",
        **kw,
    }


async def tao_km(db, ma="GIAM10", **kw):
    bay_gio = bay_gio_utc()
    gia_tri = {
        "ten": "KM",
        "loai_giam": "phan_tram",
        "gia_tri": Decimal(10),
        "don_toi_thieu": Decimal(0),
        "bat_dau": bay_gio - timedelta(days=1),
        "ket_thuc": bay_gio + timedelta(days=30),
        "luot_moi_khach": 1,
        "pham_vi": "toan_bo",
        "dang_hoat_dong": True,
        **kw,
    }
    km = KhuyenMai(**gia_tri)
    db.add(km)
    await db.flush()
    m = MaGiamGia(khuyen_mai_id=km.id, ma=f"{ma}{next(_dem)}" if ma is None else ma)
    db.add(m)
    await db.flush()
    return km, m


def dong_gio(sp, thanh_tien, khoa=0, danh_muc=None, ke_don=False):
    return DongGio(khoa, sp.id, frozenset({danh_muc or sp.danh_muc_id}), ke_don, Decimal(thanh_tien))


# --- AD06: CRUD ---


async def test_admin_tao_sua_xoa_khuyen_mai_va_sinh_ma(dang_nhap_admin, db):
    c = dang_nhap_admin
    r = await c.post(KM, json=noi_dung(gia_tri="15", giam_toi_da="50000", tong_luot=100))
    assert r.status_code == 201
    d = r.json()
    assert d["trang_thai"] == "dang_hieu_luc" and d["giam_toi_da"] == "50000.00" and d["so_ma"] == 0
    ma = (await c.post(f"{KM}/{d['id']}/ma", json={"so_luong": 3})).json()
    assert len(ma) == 3 and all(len(m["ma"]) == 8 and m["ma"] == m["ma"].upper() for m in ma)
    rieng = (await c.post(f"{KM}/{d['id']}/ma", json={"ma": "freeship-01"})).json()
    assert rieng[0]["ma"] == "FREESHIP-01"
    r = await c.post(f"{KM}/{d['id']}/ma", json={"ma": "FREESHIP-01"})
    assert r.status_code == 409 and r.json()["ma_loi"] == "TRUNG_DU_LIEU"
    ct = (await c.get(f"{KM}/{d['id']}")).json()
    assert ct["so_ma"] == 4 and len(ct["ma_giam_gia"]) == 4
    sua = {k: v for k, v in noi_dung(ten="Đã sửa", gia_tri="20").items()} | {"phien_ban": ct["phien_ban"]}
    r = await c.put(f"{KM}/{d['id']}", json=sua)
    assert r.status_code == 200 and r.json()["ten"] == "Đã sửa" and r.json()["gia_tri"] == "20.00"
    r = await c.put(f"{KM}/{d['id']}", json=sua)  # phiên bản cũ
    assert r.status_code == 409 and r.json()["ma_loi"] == "DU_LIEU_DA_THAY_DOI"
    assert (await c.delete(f"{KM}/{d['id']}/ma/{rieng[0]['id']}")).status_code == 204
    assert (await c.delete(f"{KM}/{d['id']}")).status_code == 204
    assert (await c.get(f"{KM}/{d['id']}")).status_code == 404


@pytest.mark.parametrize(
    ("thay", "truong"),
    [
        ({"gia_tri": "101"}, "gia_tri"),
        ({"gia_tri": "0"}, "gia_tri"),
        ({"loai_giam": "so_tien", "gia_tri": "1000.5"}, "gia_tri"),
        ({"loai_giam": "so_tien", "gia_tri": "1000", "giam_toi_da": "500"}, "giam_toi_da"),
        ({"ket_thuc": "2000-01-02T00:00:00+00:00", "bat_dau": "2000-01-03T00:00:00+00:00"}, "ket_thuc"),
        ({"pham_vi": "danh_muc"}, "danh_muc_ids"),
        ({"pham_vi": "san_pham", "danh_muc_ids": [1]}, "san_pham_ids"),
        ({"pham_vi": "toan_bo", "san_pham_ids": [1]}, "pham_vi"),
        ({"luot_moi_khach": 0}, "luot_moi_khach"),
        ({"tong_luot": 0}, "tong_luot"),
    ],
)
async def test_du_lieu_khuyen_mai_sai_la_400(dang_nhap_admin, thay, truong):
    r = await dang_nhap_admin.post(KM, json=noi_dung(**thay))
    assert r.status_code == 400 and r.json()["ma_loi"] == "DU_LIEU_KHONG_HOP_LE"


async def test_pham_vi_san_pham_khong_nhan_thuoc_ke_don_va_id_la(dang_nhap_admin, db):
    rx, thuong = await tao_san_pham(db, loai="thuoc_ke_don"), await tao_san_pham(db)
    c = dang_nhap_admin
    r = await c.post(KM, json=noi_dung(pham_vi="san_pham", san_pham_ids=[thuong.id, rx.id]))
    assert r.status_code == 400 and "kê đơn" in r.json()["chi_tiet"][0]["loi"]
    assert (await c.post(KM, json=noi_dung(pham_vi="san_pham", san_pham_ids=[999_999_9]))).status_code == 400
    ok = await c.post(KM, json=noi_dung(pham_vi="san_pham", san_pham_ids=[thuong.id]))
    assert ok.status_code == 201 and ok.json()["san_pham"][0]["id"] == thuong.id
    dm = await tao_danh_muc(db)
    ok = await c.post(KM, json=noi_dung(pham_vi="danh_muc", danh_muc_ids=[dm.id]))
    assert ok.status_code == 201 and ok.json()["danh_muc"][0]["ten"] == dm.ten
    assert (await c.post(KM, json=noi_dung(pham_vi="danh_muc", danh_muc_ids=[999_999_9]))).status_code == 400


async def test_khong_xoa_khuyen_mai_hoac_ma_da_dung(dang_nhap_admin, db):
    km, ma = await tao_km(db, "DADUNG")
    ma.so_luot_da_dung = 1
    await db.flush()
    r = await dang_nhap_admin.delete(f"{KM}/{km.id}")
    assert r.status_code == 409 and r.json()["ma_loi"] == "DU_LIEU_DANG_DUOC_SU_DUNG"
    assert (await dang_nhap_admin.delete(f"{KM}/{km.id}/ma/{ma.id}")).status_code == 409


async def test_loc_danh_sach_theo_trang_thai(dang_nhap_admin, db):
    bay_gio = bay_gio_utc()
    await tao_km(
        db, "A1", ten="Sắp diễn ra ZZ", bat_dau=bay_gio + timedelta(days=1), ket_thuc=bay_gio + timedelta(days=2)
    )
    await tao_km(db, "A2", ten="Hết hạn ZZ", bat_dau=bay_gio - timedelta(days=9), ket_thuc=bay_gio - timedelta(days=1))
    await tao_km(db, "A3", ten="Đã tắt ZZ", dang_hoat_dong=False)
    for trang_thai, ten in (("sap_dien_ra", "Sắp"), ("het_han", "Hết"), ("da_tat", "Đã tắt")):
        r = (await dang_nhap_admin.get(KM, params={"trang_thai": trang_thai, "q": "ZZ"})).json()
        assert [x["ten"] for x in r["du_lieu"]] == [
            f"{ten} diễn ra ZZ" if ten == "Sắp" else f"{ten} hạn ZZ" if ten == "Hết" else "Đã tắt ZZ"
        ]


async def test_duoc_si_va_kho_khong_quan_ly_khuyen_mai(clients_theo_vai_tro):
    for vai in ("PHARMACIST", "WAREHOUSE"):
        assert (await clients_theo_vai_tro[vai].get(KM)).status_code == 403
        assert (await clients_theo_vai_tro[vai].post(KM, json=noi_dung())).status_code == 403


# --- KTV04: kiểm tra mã theo giỏ ---


async def gio_co(c, db, gia=1000, so_luong=1, **kw):
    sp = await tao_san_pham(db, don_vi=[{"ten_don_vi": "viên", "he_so": 1, "gia_ban": gia, "la_mac_dinh": True}], **kw)
    await tao_lo(db, sp, so_luong=500)
    r = await c.post(
        f"{GIO}/dong", json={"san_pham_id": sp.id, "don_vi_id": sp.don_vi_theo_ten["viên"].id, "so_luong": so_luong}
    )
    assert r.status_code == 200
    return sp


async def test_kiem_tra_ma_tra_so_tien_giam_theo_gio(dang_nhap_khach, db):
    await gio_co(dang_nhap_khach, db, gia=20_000, so_luong=3)  # 60.000
    await tao_km(db, "SALE10", giam_toi_da=Decimal(5000))
    r = (await dang_nhap_khach.post(KIEM_TRA, json={"ma": " sale10 "})).json()
    assert r["hop_le"] is True and r["ma"] == "SALE10" and r["co_so_giam"] == "60000.00"
    assert r["giam"] == "5000.00" and r["ma_ly_do"] is None and r["khuyen_mai"]["ten"] == "KM"


@pytest.mark.parametrize(
    ("kw", "ly_do"),
    [
        ({"dang_hoat_dong": False}, "da_tat"),
        ({"bat_dau": bay_gio_utc() + timedelta(days=1), "ket_thuc": bay_gio_utc() + timedelta(days=2)}, "chua_bat_dau"),
        ({"bat_dau": bay_gio_utc() - timedelta(days=2), "ket_thuc": bay_gio_utc() - timedelta(days=1)}, "het_han"),
        ({"don_toi_thieu": Decimal(500_000)}, "duoi_don_toi_thieu"),
    ],
)
async def test_kiem_tra_ma_khong_ap_dung_duoc_co_ly_do(dang_nhap_khach, db, kw, ly_do):
    await gio_co(dang_nhap_khach, db, gia=10_000)
    await tao_km(db, f"MA{ly_do.upper()}", **kw)
    r = (await dang_nhap_khach.post(KIEM_TRA, json={"ma": f"MA{ly_do.upper()}"})).json()
    assert r["hop_le"] is False and r["ma_ly_do"] == ly_do and r["ly_do"] and r["giam"] == "0.00"


async def test_ma_khong_ton_tai_va_gio_rong_va_het_luot_tong(dang_nhap_khach, db):
    c = dang_nhap_khach
    assert (await c.post(KIEM_TRA, json={"ma": "KHONGCO"})).json()["ma_ly_do"] == "khong_ton_tai"
    await tao_km(db, "GIOTRONG")
    assert (await c.post(KIEM_TRA, json={"ma": "GIOTRONG"})).json()["ma_ly_do"] == "khong_co_san_pham"
    await gio_co(c, db)
    km, ma = await tao_km(db, "HETLUOT", tong_luot=2)
    ma.so_luot_da_dung = 1
    db.add(MaGiamGia(khuyen_mai_id=km.id, ma="HETLUOT2", so_luot_da_dung=1))  # tổng theo khuyến mãi = 2
    await db.flush()
    assert (await c.post(KIEM_TRA, json={"ma": "HETLUOT"})).json()["ma_ly_do"] == "het_luot"


async def test_thuoc_ke_don_khong_duoc_giam_va_pham_vi_danh_muc_gom_danh_muc_con(dang_nhap_khach, db):
    c = dang_nhap_khach
    cha = await tao_danh_muc(db)
    con = await tao_danh_muc(db, cha=cha)
    sp = await tao_san_pham(
        db, danh_muc_id=con.id, don_vi=[{"ten_don_vi": "viên", "he_so": 1, "gia_ban": 10_000, "la_mac_dinh": True}]
    )
    await tao_lo(db, sp, so_luong=50)
    other = await gio_co(c, db, gia=30_000)  # sản phẩm ngoài phạm vi
    await c.post(f"{GIO}/dong", json={"san_pham_id": sp.id, "don_vi_id": sp.don_vi_theo_ten["viên"].id, "so_luong": 2})
    km, _ = await tao_km(db, "DANHMUC", pham_vi="danh_muc")
    db.add(
        KhuyenMaiPhamVi(khuyen_mai_id=km.id, danh_muc_id=cha.id)
    )  # phạm vi là danh mục CHA, sản phẩm nằm ở danh mục con
    await db.flush()
    r = (await c.post(KIEM_TRA, json={"ma": "DANHMUC"})).json()
    assert r["hop_le"] and r["co_so_giam"] == "20000.00" and r["giam"] == "2000.00" and other.id
    # pham_vi toàn bộ mà giỏ chỉ có hàng ngoài phạm vi sản phẩm -> không có sản phẩm hợp lệ
    km2, _ = await tao_km(db, "SANPHAM", pham_vi="san_pham")
    db.add(KhuyenMaiPhamVi(khuyen_mai_id=km2.id, san_pham_id=(await tao_san_pham(db)).id))
    await db.flush()
    assert (await c.post(KIEM_TRA, json={"ma": "SANPHAM"})).json()["ma_ly_do"] == "khong_co_san_pham"


async def test_ke_don_bi_loai_khoi_co_so_giam_o_tang_thuat_toan(db):
    khach = await tao_khach(db)
    rx, thuong = await tao_san_pham(db, loai="thuoc_ke_don"), await tao_san_pham(db)
    await tao_km(db, "TOANBO")
    dong = [dong_gio(rx, 90_000, 0, ke_don=True), dong_gio(thuong, 10_000, 1)]
    kq = await ap_dung.kiem_tra_ma(db, khach.id, "toanbo", dong)
    assert kq.hop_le and kq.co_so_giam == 10_000 and kq.giam == 1000 and kq.phan_bo == {0: 0, 1: 1000}
    chi_ke_don = await ap_dung.kiem_tra_ma(db, khach.id, "TOANBO", [dong_gio(rx, 90_000, 0, ke_don=True)])
    assert chi_ke_don.ma_ly_do == MaLyDo.khong_co_san_pham


async def test_gioi_han_thu_ma_theo_khach(dang_nhap_khach):
    for _ in range(30):
        assert (await dang_nhap_khach.post(KIEM_TRA, json={"ma": "DOMA"})).status_code == 200
    r = await dang_nhap_khach.post(KIEM_TRA, json={"ma": "DOMA"})
    assert r.status_code == 429 and r.json()["ma_loi"] == "QUA_GIOI_HAN"


async def test_kiem_tra_ma_can_dang_nhap(client):
    assert (await client.post(KIEM_TRA, json={"ma": "X"})).status_code == 401


# --- Dùng mã và trả lượt ---


async def test_dung_ma_tang_luot_het_luot_moi_khach_va_don_huy_tra_luot(db):
    khach = await tao_khach(db)
    sp = await tao_san_pham(db)
    km, ma = await tao_km(db, "DUNGMA", luot_moi_khach=1)
    kq = await ap_dung.dung_ma(db, khach.id, "dungma", [dong_gio(sp, 10_000)])
    assert kq.giam == 1000
    await db.refresh(ma)
    assert ma.so_luot_da_dung == 1
    don = await tao_don(db, khach, trang_thai="cho_xac_nhan", ma_giam_gia_id=ma.id)  # đơn đã dùng mã
    with pytest.raises(LoiNghiepVu) as e:  # lượt thứ hai của cùng khách
        await ap_dung.dung_ma(db, khach.id, "DUNGMA", [dong_gio(sp, 10_000)])
    assert e.value.ma_loi == "MA_GIAM_GIA_KHONG_HOP_LE" and e.value.chi_tiet == {"ma_ly_do": "het_luot_khach"}
    khach_khac = await tao_khach(db)
    await ap_dung.dung_ma(db, khach_khac.id, "DUNGMA", [dong_gio(sp, 10_000)])  # khách khác vẫn dùng được
    await db.refresh(ma)
    assert ma.so_luot_da_dung == 2
    # hủy đơn: trả lượt (hook của máy trạng thái), khách dùng lại được
    ds = mt.TacNhan.duoc_si((await tao_nhan_vien(db, "PHARMACIST")).id)
    await mt.chuyen_trang_thai(db, don, mt.TT.da_huy, ds, "nguoi_dung", "Khách hủy")
    await db.refresh(ma)
    assert ma.so_luot_da_dung == 1
    await ap_dung.dung_ma(db, khach.id, "DUNGMA", [dong_gio(sp, 10_000)])
    assert km.id


async def test_dung_ma_khong_hop_le_khong_tang_luot_va_don_khong_ma_khong_tra_luot(db):
    khach = await tao_khach(db)
    sp = await tao_san_pham(db)
    _, ma = await tao_km(db, "DUOIMIN", don_toi_thieu=Decimal(99_999))
    with pytest.raises(LoiNghiepVu) as e:
        await ap_dung.dung_ma(db, khach.id, "DUOIMIN", [dong_gio(sp, 1000)])
    assert e.value.chi_tiet == {"ma_ly_do": "duoi_don_toi_thieu"}
    await db.refresh(ma)
    assert ma.so_luot_da_dung == 0
    don = await tao_don(db, khach, trang_thai="cho_xac_nhan")
    ds = mt.TacNhan.duoc_si((await tao_nhan_vien(db, "PHARMACIST")).id)
    await mt.chuyen_trang_thai(db, don, mt.TT.da_huy, ds, "nguoi_dung", "x")  # không có mã: không lỗi
    await db.refresh(ma)
    assert ma.so_luot_da_dung == 0


def test_moi_dong_chuyen_sang_da_huy_deu_co_hook_tra_luot():
    for so in (9, 12, 14, 15, 19, 21, 27):
        assert ap_dung.tra_luot_khi_huy in mt.HOOK_THEO_DONG[so], so

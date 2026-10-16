"""KVL01, KVL02: danh sách sản phẩm công khai, giá theo đơn vị bán online, còn hàng, lọc, sắp xếp, trang chủ."""

from datetime import timedelta

from app.core.thoi_gian import bay_gio_utc, hom_nay_vn
from app.models.san_pham import ThuongHieu
from tests.cua_hang.mau_cua_hang import GOC, dat_ban_chay, sp_ban_duoc, ten_the
from tests.factories import tao_danh_muc, tao_lo

DON_VI_3_BAC = [
    {"ten_don_vi": "viên", "he_so": 1, "gia_ban": 1000},
    {"ten_don_vi": "vỉ", "he_so": 10, "gia_ban": 9000, "la_mac_dinh": True},
    {"ten_don_vi": "hộp", "he_so": 100, "gia_ban": 80000, "ban_online": False},
]

# --- Thẻ sản phẩm: giá và còn hàng --------------------------------------------------------------------------------------


async def test_the_san_pham_co_du_truong_gia_la_don_vi_online_mac_dinh(client, db):
    th = ThuongHieu(ten="Sanofi")
    db.add(th)
    await db.flush()
    sp = await sp_ban_duoc(db, "Paracetamol", don_vi=DON_VI_3_BAC, thuong_hieu_id=th.id, quy_cach="Hộp 10 vỉ")
    phan_hoi = await client.get(f"{GOC}/san-pham")
    assert phan_hoi.status_code == 200, phan_hoi.text
    trang = phan_hoi.json()
    assert (trang["tong"], trang["trang"], trang["kich_thuoc"]) == (1, 1, 20)
    the = trang["du_lieu"][0]
    assert the == {
        "id": sp.id,
        "ten": "Paracetamol",
        "slug": sp.slug,
        "loai_san_pham": "thuoc_khong_ke_don",
        "can_tu_van": False,
        "thuong_hieu": "Sanofi",
        "quy_cach": "Hộp 10 vỉ",
        "anh_chinh_url": None,
        "gia": "9000.00",
        "ten_don_vi_gia": "vỉ",
        "con_hang": True,
    }


async def test_gia_the_khong_co_mac_dinh_thi_don_vi_online_nho_nhat_khong_online_thi_null(client, db):
    await sp_ban_duoc(
        db,
        "KhongMacDinh",
        don_vi=[
            {"ten_don_vi": "hộp", "he_so": 100, "gia_ban": 80000},
            {"ten_don_vi": "vỉ", "he_so": 10, "gia_ban": 9000},
            {"ten_don_vi": "viên", "he_so": 1, "gia_ban": 1000, "ban_online": False},
        ],
    )
    await sp_ban_duoc(
        db, "ChiTaiQuay", don_vi=[{"ten_don_vi": "viên", "he_so": 1, "gia_ban": 500, "ban_online": False}]
    )
    the = {t["ten"]: t for t in (await client.get(f"{GOC}/san-pham")).json()["du_lieu"]}
    assert (the["KhongMacDinh"]["gia"], the["KhongMacDinh"]["ten_don_vi_gia"]) == ("9000.00", "vỉ")
    assert the["ChiTaiQuay"]["gia"] is None and the["ChiTaiQuay"]["ten_don_vi_gia"] is None


async def test_con_hang_la_ton_kha_dung_cua_lo_dang_ban_con_han(client, db):
    hom_nay = hom_nay_vn()
    await sp_ban_duoc(db, "Hết", ton=0)
    du = await sp_ban_duoc(db, "Đủ", ton=0)
    await tao_lo(db, du, so_luong=5)
    giu_het = await sp_ban_duoc(db, "GiữHết", ton=0)
    await tao_lo(db, giu_het, so_luong_ton=5, so_luong_giu=5)  # 5 - 5 = 0 khả dụng
    can_han = await sp_ban_duoc(db, "CậnHạn", ton=0)
    await tao_lo(db, can_han, so_luong=9, han_su_dung=hom_nay + timedelta(days=30))  # cận hạn chỉ bán tại quầy
    qua_han = await sp_ban_duoc(db, "QuáHạn", ton=0)
    # còn nhãn dang_ban nhưng hạn đã qua (job HT01 chưa chạy): vẫn không tính
    await tao_lo(db, qua_han, so_luong_ton=9, han_su_dung=hom_nay, trang_thai="dang_ban")
    biet_tru = await sp_ban_duoc(db, "BiệtTrữ", ton=0)
    await tao_lo(db, biet_tru, so_luong_ton=0, so_luong_biet_tru=9)
    khoa = await sp_ban_duoc(db, "Khóa", ton=0)
    await tao_lo(db, khoa, so_luong=9, trang_thai="khoa")
    con = {t["ten"]: t["con_hang"] for t in (await client.get(f"{GOC}/san-pham")).json()["du_lieu"]}
    assert con == {
        "Hết": False,
        "Đủ": True,
        "GiữHết": False,
        "CậnHạn": False,
        "QuáHạn": False,
        "BiệtTrữ": False,
        "Khóa": False,
    }
    assert ten_the(await client.get(f"{GOC}/san-pham", params={"con_hang": "true"})) == ["Đủ"]
    assert (await client.get(f"{GOC}/san-pham", params={"con_hang": "true"})).json()["tong"] == 1


async def test_thuoc_ke_don_co_trong_danh_sach_kem_can_tu_van(client, db):
    await sp_ban_duoc(db, "Kháng sinh", loai="thuoc_ke_don")
    the = (await client.get(f"{GOC}/san-pham")).json()["du_lieu"][0]
    assert the["can_tu_van"] is True and the["loai_san_pham"] == "thuoc_ke_don"


# --- Lọc ---------------------------------------------------------------------------------------------------------------


async def test_loc_danh_muc_gom_ca_danh_muc_con(client, db):
    goc = await tao_danh_muc(db, "Thuốc")
    con = await tao_danh_muc(db, "Giảm đau", cha=goc)
    khac = await tao_danh_muc(db, "Chăm sóc")
    await sp_ban_duoc(db, "ỞGốc", danh_muc_id=goc.id)
    await sp_ban_duoc(db, "ỞCon", danh_muc_id=con.id)
    await sp_ban_duoc(db, "ỞKhác", danh_muc_id=khac.id)
    assert sorted(ten_the(await client.get(f"{GOC}/san-pham", params={"danh_muc": goc.slug}))) == ["ỞCon", "ỞGốc"]
    assert ten_the(await client.get(f"{GOC}/san-pham", params={"danh_muc": con.slug})) == ["ỞCon"]
    assert len(ten_the(await client.get(f"{GOC}/san-pham"))) == 3


async def test_loc_theo_loai_thuong_hieu_doi_tuong_khong_phan_biet_dau_va_hoa_thuong(client, db):
    a, b = ThuongHieu(ten="A"), ThuongHieu(ten="B")
    db.add_all([a, b])
    await db.flush()
    await sp_ban_duoc(db, "P1", thuong_hieu_id=a.id, doi_tuong_su_dung="Trẻ em từ 2 tuổi")
    await sp_ban_duoc(db, "P2", thuong_hieu_id=b.id, doi_tuong_su_dung="Người lớn", loai="thuc_pham_chuc_nang")
    await sp_ban_duoc(db, "P3", doi_tuong_su_dung="100% người lớn")
    layp = lambda **tham_so: client.get(f"{GOC}/san-pham", params=tham_so)  # noqa: E731
    assert ten_the(await layp(loai="thuc_pham_chuc_nang")) == ["P2"]
    assert ten_the(await layp(thuong_hieu_id=[a.id])) == ["P1"]
    assert sorted(ten_the(await layp(thuong_hieu_id=[a.id, b.id]))) == ["P1", "P2"]
    assert ten_the(await layp(doi_tuong="TRE EM")) == ["P1"]  # không dấu, hoa thường
    assert sorted(ten_the(await layp(doi_tuong="nguoi lon"))) == ["P2", "P3"]
    assert ten_the(await layp(doi_tuong="100%")) == ["P3"]  # % là ký tự thường, không là ký tự thay thế
    assert ten_the(await layp(doi_tuong="%")) == ["P3"]
    assert ten_the(await layp(doi_tuong="_")) == []
    assert ten_the(await layp(loai="thuc_pham_chuc_nang", thuong_hieu_id=[a.id])) == []  # các lọc kết hợp bằng AND


async def test_loc_khoang_gia_theo_gia_the_va_bo_san_pham_khong_co_gia(client, db):
    for ten, gia in (("R100", 100), ("R200", 200), ("R300", 300)):
        await sp_ban_duoc(db, ten, don_vi=[{"ten_don_vi": "viên", "he_so": 1, "gia_ban": gia, "la_mac_dinh": True}])
    await sp_ban_duoc(db, "TạiQuầy", don_vi=[{"ten_don_vi": "viên", "he_so": 1, "gia_ban": 150, "ban_online": False}])
    layp = lambda **tham_so: client.get(f"{GOC}/san-pham", params=tham_so)  # noqa: E731
    assert sorted(ten_the(await layp(gia_tu=200))) == ["R200", "R300"]
    assert sorted(ten_the(await layp(gia_den=200))) == ["R100", "R200"]
    assert ten_the(await layp(gia_tu=200, gia_den=200)) == ["R200"]  # biên gồm cả hai đầu
    assert len(ten_the(await layp())) == 4  # không lọc giá thì sản phẩm không có giá vẫn hiện
    loi = await layp(gia_tu=300, gia_den=100)
    assert loi.status_code == 400 and loi.json()["ma_loi"] == "DU_LIEU_KHONG_HOP_LE"
    for sai in ({"gia_tu": -1}, {"gia_tu": "1.5"}, {"gia_den": "abc"}, {"gia_tu": 10**13}):
        assert (await layp(**sai)).status_code == 400, sai


async def test_tham_so_sai_la_400_khong_phai_500(client, db):
    await sp_ban_duoc(db, "X")
    layp = lambda **tham_so: client.get(f"{GOC}/san-pham", params=tham_so)  # noqa: E731
    for sai in (
        {"sap_xep": "gia"},
        {"sap_xep": "-moi"},
        {"loai": "khong_co"},
        {"con_hang": "có"},
        {"doi_tuong": "a\x00b"},
        {"trang": 0},
        {"kich_thuoc": 101},
        {"thuong_hieu_id": "x"},
    ):
        phan_hoi = await layp(**sai)
        assert phan_hoi.status_code == 400 and phan_hoi.json()["ma_loi"] == "DU_LIEU_KHONG_HOP_LE", sai
    assert (await layp(thuong_hieu_id=[2**40])).status_code == 400  # ngoài miền Integer: lỗi rõ, không bỏ lọc ngầm
    assert (await layp(thuong_hieu_id=[0])).status_code == 400
    assert (await layp(thuong_hieu_id=list(range(1, 22)))).status_code == 400  # tối đa 20 thương hiệu


# --- Sắp xếp -----------------------------------------------------------------------------------------------------------


async def test_sap_xep_moi_gia_ten_on_dinh_giua_cac_trang(client, db):
    cu = await sp_ban_duoc(db, "Bình", don_vi=[{"ten_don_vi": "v", "he_so": 1, "gia_ban": 300, "la_mac_dinh": True}])
    cu.created_at = bay_gio_utc() - timedelta(days=2)
    giua = await sp_ban_duoc(db, "an", don_vi=[{"ten_don_vi": "v", "he_so": 1, "gia_ban": 100, "la_mac_dinh": True}])
    giua.created_at = bay_gio_utc() - timedelta(days=1)
    await sp_ban_duoc(db, "Cúc", don_vi=[{"ten_don_vi": "v", "he_so": 1, "gia_ban": 200, "la_mac_dinh": True}])
    khong_gia = await sp_ban_duoc(
        db, "Zzz", don_vi=[{"ten_don_vi": "v", "he_so": 1, "gia_ban": 1, "ban_online": False}]
    )
    khong_gia.created_at = bay_gio_utc() - timedelta(days=3)
    await db.flush()
    layp = lambda sap_xep: client.get(f"{GOC}/san-pham", params={"sap_xep": sap_xep})  # noqa: E731
    assert ten_the(await layp("moi")) == ["Cúc", "an", "Bình", "Zzz"]
    assert ten_the(await client.get(f"{GOC}/san-pham")) == ["Cúc", "an", "Bình", "Zzz"]  # mặc định là mới nhất
    assert ten_the(await layp("gia_tang")) == ["an", "Cúc", "Bình", "Zzz"]  # không có giá xếp cuối
    assert ten_the(await layp("gia_giam")) == ["Bình", "Cúc", "an", "Zzz"]  # không có giá vẫn xếp cuối khi giảm dần
    assert ten_the(await layp("ten")) == ["an", "Bình", "Cúc", "Zzz"]  # không phân biệt hoa thường
    hai_trang = []
    for trang in (1, 2):
        phan_hoi = await client.get(f"{GOC}/san-pham", params={"sap_xep": "ten", "kich_thuoc": 2, "trang": trang})
        hai_trang += ten_the(phan_hoi)
        assert phan_hoi.json()["tong"] == 4
    assert hai_trang == ["an", "Bình", "Cúc", "Zzz"]


async def test_sap_xep_ban_chay_dem_dong_don_30_ngay_khong_tinh_don_huy_va_don_cu(client, db):
    nhieu = await sp_ban_duoc(db, "Nhiều")
    it = await sp_ban_duoc(db, "Ít")
    huy = await sp_ban_duoc(db, "ChỉĐơnHủy")
    cu = await sp_ban_duoc(db, "ChỉĐơnCũ")
    chua_ban = await sp_ban_duoc(db, "ChưaBán")
    await dat_ban_chay(db, nhieu, 3)
    await dat_ban_chay(db, it, 1, tuoi_ngay=29)
    await dat_ban_chay(db, huy, 5, trang_thai="da_huy")
    await dat_ban_chay(db, cu, 5, tuoi_ngay=31)
    phan_hoi = await client.get(f"{GOC}/san-pham", params={"sap_xep": "ban_chay"})
    ten = ten_the(phan_hoi)
    assert ten[:2] == ["Nhiều", "Ít"]
    assert sorted(ten[2:]) == sorted(["ChỉĐơnHủy", "ChỉĐơnCũ", "ChưaBán"])  # còn lại hòa 0: theo id tăng dần
    assert ten[2:] == [x.ten for x in sorted((huy, cu, chua_ban), key=lambda sp: sp.id)]


# --- Trang chủ ---------------------------------------------------------------------------------------------------------


async def test_trang_chu_noi_bat_va_ban_chay_loai_thuoc_ke_don_ngay_o_truy_van(client, db):
    await sp_ban_duoc(db, "Nổi bật thường", la_noi_bat=True)
    await sp_ban_duoc(db, "Kê đơn nổi bật", loai="thuoc_ke_don", la_noi_bat=True)  # DB không cấm; service AD04 mới cấm
    await sp_ban_duoc(db, "Không nổi bật")
    ban_chay_thuong = await sp_ban_duoc(db, "Bán chạy thường")
    ban_chay_ke_don = await sp_ban_duoc(db, "Bán chạy kê đơn", loai="thuoc_ke_don")
    await dat_ban_chay(db, ban_chay_thuong, 2)
    await dat_ban_chay(db, ban_chay_ke_don, 9)
    trang_chu = (await client.get(f"{GOC}/trang-chu")).json()
    assert [t["ten"] for t in trang_chu["noi_bat"]] == ["Nổi bật thường"]
    assert [t["ten"] for t in trang_chu["ban_chay"]] == ["Bán chạy thường"]  # kê đơn bán chạy nhất vẫn không hiện
    assert {t["can_tu_van"] for t in trang_chu["noi_bat"] + trang_chu["ban_chay"]} == {False}


async def test_trang_chu_toi_da_12_moi_khu_va_noi_bat_moi_nhat_truoc(client, db):
    for i in range(14):
        sp = await sp_ban_duoc(db, f"NB{i:02d}", la_noi_bat=True)
        sp.created_at = bay_gio_utc() - timedelta(hours=14 - i)
    await db.flush()
    noi_bat = (await client.get(f"{GOC}/trang-chu")).json()["noi_bat"]
    assert [t["ten"] for t in noi_bat] == [f"NB{i:02d}" for i in range(13, 1, -1)]


async def test_trang_chu_trong_van_tra_cau_truc_day_du(client, db):
    assert (await client.get(f"{GOC}/trang-chu")).json() == {
        "banner_chinh": [],
        "banner_phu": [],
        "noi_bat": [],
        "ban_chay": [],
    }


# --- Bộ lọc ------------------------------------------------------------------------------------------------------------


async def test_bo_loc_liet_ke_thuong_hieu_doi_tuong_va_khoang_gia_trong_pham_vi_danh_muc(client, db):
    goc = await tao_danh_muc(db, "Thuốc")
    khac = await tao_danh_muc(db, "Khác")
    a, b = ThuongHieu(ten="Beta"), ThuongHieu(ten="alpha")
    db.add_all([a, b])
    await db.flush()
    mot_don_vi = lambda gia: [{"ten_don_vi": "v", "he_so": 1, "gia_ban": gia, "la_mac_dinh": True}]  # noqa: E731
    await sp_ban_duoc(
        db, "P1", danh_muc_id=goc.id, thuong_hieu_id=a.id, doi_tuong_su_dung="Trẻ em", don_vi=mot_don_vi(500)
    )
    await sp_ban_duoc(
        db, "P2", danh_muc_id=goc.id, thuong_hieu_id=b.id, doi_tuong_su_dung="Người lớn", don_vi=mot_don_vi(900)
    )
    await sp_ban_duoc(
        db, "P3", danh_muc_id=goc.id, thuong_hieu_id=b.id, doi_tuong_su_dung="Người lớn", don_vi=mot_don_vi(700)
    )
    await sp_ban_duoc(db, "P4", danh_muc_id=khac.id, doi_tuong_su_dung="Mọi người", don_vi=mot_don_vi(50))
    ngoai = await sp_ban_duoc(
        db, "Ẩn", danh_muc_id=goc.id, trang_thai="ngung_kinh_doanh", doi_tuong_su_dung="Ẩn", don_vi=mot_don_vi(1)
    )
    phan_hoi = await client.get(f"{GOC}/bo-loc-san-pham", params={"danh_muc": goc.slug})
    assert phan_hoi.status_code == 200, phan_hoi.text
    assert phan_hoi.json() == {
        "thuong_hieu": [{"id": b.id, "ten": "alpha"}, {"id": a.id, "ten": "Beta"}],
        "doi_tuong": ["Người lớn", "Trẻ em"],
        "gia_thap_nhat": "500.00",
        "gia_cao_nhat": "900.00",
    }
    toan = (await client.get(f"{GOC}/bo-loc-san-pham")).json()
    assert toan["gia_thap_nhat"] == "50.00" and "Mọi người" in toan["doi_tuong"] and "Ẩn" not in toan["doi_tuong"]
    assert (await client.get(f"{GOC}/bo-loc-san-pham", params={"danh_muc": "khong-co"})).status_code == 404
    assert ngoai.id


async def test_danh_sach_san_pham_la_cong_khai_khong_can_dang_nhap_va_khong_lo_truong_noi_bo(client, db):
    sp = await sp_ban_duoc(db, "Công khai", ton_toi_thieu=5, so_luong_toi_da_moi_don=3, so_dang_ky="VD-1")
    the = (await client.get(f"{GOC}/san-pham")).json()["du_lieu"][0]
    for noi_bo in ("sku", "ton_toi_thieu", "so_luong_toi_da_moi_don", "trang_thai", "deleted_at", "so_dang_ky"):
        assert noi_bo not in the
    assert sp.id == the["id"]

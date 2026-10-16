"""KVL03: chi tiết sản phẩm công khai: đơn vị và giá, nội dung chuyên môn đã duyệt, đánh giá, lịch sử xem, tương tự."""

import json
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.core.thoi_gian import bay_gio_utc
from app.models.ai import LichSuXem
from app.models.enums import TrangThaiNoiDung
from app.models.san_pham import AnhSanPham, HoatChat, NhaSanXuat, ThanhPhan, ThongTinChuyenMon, ThuongHieu
from app.modules.cua_hang.chi_tiet import ma_phien_hop_le, ten_rut_gon
from tests.cua_hang.mau_cua_hang import GOC, sp_ban_duoc, tao_danh_gia
from tests.factories import tao_danh_muc, tao_khach, tao_nhan_vien

DON_VI = [
    {"ten_don_vi": "viên", "he_so": 1, "gia_ban": 1000},
    {"ten_don_vi": "vỉ", "he_so": 10, "gia_ban": 9000, "la_mac_dinh": True},
    {"ten_don_vi": "hộp", "he_so": 100, "gia_ban": 80000},
    {"ten_don_vi": "thùng", "he_so": 1000, "gia_ban": 700000, "ban_online": False},
]


async def lay(client, sp, **kwargs):
    return await client.get(f"{GOC}/san-pham/{sp.slug}", **kwargs)


# --- Nội dung cơ bản ---------------------------------------------------------------------------------------------------


async def test_chi_tiet_day_du_don_vi_online_theo_he_so_gia_va_con_hang_theo_tung_don_vi(client, db):
    th, nsx = ThuongHieu(ten="Sanofi"), NhaSanXuat(ten="Hậu Giang", quoc_gia="VN")
    hc = HoatChat(ten="Paracetamol")
    db.add_all([th, nsx, hc])
    await db.flush()
    goc = await tao_danh_muc(db, "Thuốc")
    con = await tao_danh_muc(db, "Giảm đau", cha=goc)
    sp = await sp_ban_duoc(
        db,
        "Paracetamol 500",
        ton=50,  # 50 viên: đủ viên và vỉ (10), thiếu hộp (100)
        don_vi=DON_VI,
        danh_muc_id=con.id,
        thuong_hieu_id=th.id,
        nha_san_xuat_id=nsx.id,
        so_dang_ky="VD-1",
        dang_bao_che="Viên nén",
        quy_cach="Hộp 10 vỉ",
        doi_tuong_su_dung="Người lớn",
    )
    db.add_all(
        [
            ThanhPhan(san_pham_id=sp.id, hoat_chat_id=hc.id, ham_luong="500mg"),
            AnhSanPham(san_pham_id=sp.id, url="/api/v1/tep/san-pham/b.jpg", thu_tu=2),
            AnhSanPham(san_pham_id=sp.id, url="/api/v1/tep/san-pham/a.jpg", thu_tu=1, la_anh_chinh=True),
        ]
    )
    await db.flush()
    phan_hoi = await lay(client, sp)
    assert phan_hoi.status_code == 200, phan_hoi.text
    d = phan_hoi.json()
    assert d["ten"] == "Paracetamol 500" and d["sku"] == sp.sku and d["loai_san_pham"] == "thuoc_khong_ke_don"
    assert d["can_tu_van"] is False and d["luu_y_khong_phai_thuoc"] is False and d["chi_ban_tai_quay"] is False
    assert d["thuong_hieu"] == {"id": th.id, "ten": "Sanofi"} and d["nha_san_xuat"] == "Hậu Giang"
    assert (d["so_dang_ky"], d["dang_bao_che"], d["quy_cach"], d["doi_tuong_su_dung"]) == (
        "VD-1",
        "Viên nén",
        "Hộp 10 vỉ",
        "Người lớn",
    )
    assert [m["ten"] for m in d["duong_dan_danh_muc"]] == ["Thuốc", "Giảm đau"]
    assert [(u["ten_don_vi"], u["he_so"], u["gia_ban"], u["la_mac_dinh"], u["con_hang"]) for u in d["don_vi"]] == [
        ("viên", 1, "1000.00", False, True),
        ("vỉ", 10, "9000.00", True, True),
        ("hộp", 100, "80000.00", False, False),  # thùng không bán online nên không có; hộp cần 100 mà chỉ có 50
    ]
    assert [a["url"] for a in d["anh"]] == ["/api/v1/tep/san-pham/a.jpg", "/api/v1/tep/san-pham/b.jpg"]
    assert d["anh"][0]["la_anh_chinh"] is True
    assert d["thanh_phan"] == [{"hoat_chat_id": hc.id, "ten": "Paracetamol", "ham_luong": "500mg"}]
    assert d["con_hang"] is True and d["noi_dung_chuyen_mon"] is None
    assert d["danh_gia"] == {"so_luong": 0, "tong_sao": 0, "phan_bo": [0, 0, 0, 0, 0], "moi_nhat": []}
    assert d["tuong_tu"] == []


async def test_het_hang_va_chi_ban_tai_quay(client, db):
    het = await sp_ban_duoc(db, "Hết", ton=0)
    assert (await lay(client, het)).json()["con_hang"] is False
    quay = await sp_ban_duoc(db, "Quầy", don_vi=[{"ten_don_vi": "viên", "he_so": 1, "gia_ban": 1, "ban_online": False}])
    d = (await lay(client, quay)).json()
    assert d["chi_ban_tai_quay"] is True and d["don_vi"] == []


async def test_thuoc_ke_don_can_tu_van_thuc_pham_chuc_nang_co_luu_y(client, db):
    ke_don = (await lay(client, await sp_ban_duoc(db, loai="thuoc_ke_don"))).json()
    assert ke_don["can_tu_van"] is True and ke_don["luu_y_khong_phai_thuoc"] is False
    tpcn = (await lay(client, await sp_ban_duoc(db, loai="thuc_pham_chuc_nang"))).json()
    assert tpcn["can_tu_van"] is False and tpcn["luu_y_khong_phai_thuoc"] is True


async def test_slug_khong_co_la_404_sai_dinh_dang_la_400(client, db):
    assert (await client.get(f"{GOC}/san-pham/khong-co-san-pham")).status_code == 404
    assert (await client.get(f"{GOC}/san-pham/Sai Dinh Dang")).status_code == 400
    assert (await client.get(f"{GOC}/san-pham/{'a' * 301}")).status_code == 400


# --- Nội dung chuyên môn -----------------------------------------------------------------------------------------------


def ban(sp, phien_ban, trang_thai, nguoi, **noi_dung):
    return ThongTinChuyenMon(
        san_pham_id=sp.id,
        phien_ban=phien_ban,
        trang_thai=trang_thai,
        nguoi_soan_id=nguoi.id,
        duoc_si_duyet_id=nguoi.id if trang_thai == TrangThaiNoiDung.da_duyet else None,
        ngay_duyet=bay_gio_utc() if trang_thai == TrangThaiNoiDung.da_duyet else None,
        **noi_dung,
    )


async def test_chi_hien_ban_da_duyet_khong_lo_ban_nhap_hay_nguoi_soan_nguoi_duyet(client, db):
    sp = await sp_ban_duoc(db)
    ds = await tao_nhan_vien(db, "PHARMACIST", ho_ten="Dược Sĩ Bí Mật", email="bi-mat@nhathuoc.example")
    db.add_all(
        [
            ban(sp, 1, TrangThaiNoiDung.luu_tru, ds, chi_dinh="Bản cũ đã lưu trữ"),
            ban(
                sp, 2, TrangThaiNoiDung.da_duyet, ds, chi_dinh="Giảm đau", chong_chi_dinh="Quá mẫn", bao_quan="Nơi khô"
            ),
            ban(sp, 3, TrangThaiNoiDung.nhap, ds, chi_dinh="BẢN NHÁP CHƯA DUYỆT"),
        ]
    )
    await db.flush()
    phan_hoi = await lay(client, sp)
    nd = phan_hoi.json()["noi_dung_chuyen_mon"]
    assert (nd["phien_ban"], nd["chi_dinh"], nd["chong_chi_dinh"], nd["bao_quan"]) == (
        2,
        "Giảm đau",
        "Quá mẫn",
        "Nơi khô",
    )
    assert nd["tac_dung_phu"] is None and nd["file_hdsd_url"] is None and nd["ngay_duyet"]
    mo_ta = phan_hoi.text
    for lo in ("BẢN NHÁP", "Bản cũ", "Bí Mật", "bi-mat@", "nguoi_soan", "duoc_si_duyet"):
        assert lo not in mo_ta, lo


async def test_noi_dung_chuyen_mon_cua_thuoc_ke_don_van_hien_de_khach_xem_thong_tin(client, db):
    sp = await sp_ban_duoc(db, loai="thuoc_ke_don")
    ds = await tao_nhan_vien(db, "PHARMACIST")
    db.add(ban(sp, 1, TrangThaiNoiDung.da_duyet, ds, chi_dinh="Nhiễm khuẩn"))
    await db.flush()
    d = (await lay(client, sp)).json()
    assert d["can_tu_van"] is True and d["noi_dung_chuyen_mon"]["chi_dinh"] == "Nhiễm khuẩn"


# --- Đánh giá -----------------------------------------------------------------------------------------------------------


async def test_tong_hop_danh_gia_chi_tinh_dang_hien_ten_rut_gon_moi_nhat_truoc(client, db):
    sp = await sp_ban_duoc(db)
    ten = ["Nguyễn Văn An", "Trần Thị Bình", "Lê Cường", "Phạm D", "Hoàng E"]
    sao = [5, 4, 4, 1, 2]
    khach = [await tao_khach(db, ho_ten=t) for t in ten]
    for i, (k, s) in enumerate(zip(khach, sao, strict=True)):
        dg = await tao_danh_gia(db, sp, k, s, noi_dung=f"ý kiến {i}", phan_hoi="Cảm ơn" if i == 0 else None)
        dg.created_at = bay_gio_utc() - timedelta(hours=10 - i)
    an = await tao_danh_gia(db, sp, await tao_khach(db), 1, noi_dung="đã bị ẩn", dang_hien=False)
    assert an.id
    await db.flush()
    dg = (await lay(client, sp)).json()["danh_gia"]
    assert dg["so_luong"] == 5 and dg["tong_sao"] == 16 and dg["phan_bo"] == [1, 1, 0, 2, 1]
    assert [x["noi_dung"] for x in dg["moi_nhat"]] == [f"ý kiến {i}" for i in (4, 3, 2, 1, 0)]
    assert [x["ten_hien_thi"] for x in dg["moi_nhat"]] == ["Hoàng E.", "Phạm D.", "Lê C.", "Trần B.", "Nguyễn A."]
    assert dg["moi_nhat"][-1]["phan_hoi"] == "Cảm ơn"
    mo_ta = json.dumps(dg, ensure_ascii=False)
    assert "đã bị ẩn" not in mo_ta and "Văn" not in mo_ta and "khach_hang_id" not in mo_ta


async def test_chi_hien_10_danh_gia_moi_nhat_nhung_thong_ke_tinh_het(client, db):
    sp = await sp_ban_duoc(db)
    for i in range(12):
        dg = await tao_danh_gia(db, sp, await tao_khach(db), 5)
        dg.created_at = bay_gio_utc() - timedelta(minutes=12 - i)
    await db.flush()
    dg = (await lay(client, sp)).json()["danh_gia"]
    assert dg["so_luong"] == 12 and len(dg["moi_nhat"]) == 10


@pytest.mark.parametrize(
    ("ho_ten", "ket_qua"),
    [
        ("Nguyễn Văn An", "Nguyễn A."),
        ("An", "An"),
        ("  Trần   thị  bình ", "Trần B."),
        ("", "Khách hàng"),
        ("   ", "Khách hàng"),
    ],
)
def test_ten_rut_gon(ho_ten, ket_qua):
    assert ten_rut_gon(ho_ten) == ket_qua


# --- Sản phẩm tương tự -------------------------------------------------------------------------------------------------


async def test_tuong_tu_cung_danh_muc_hoac_chung_hoat_chat_chung_nhieu_truoc_loai_ke_don_va_chinh_no(client, db):
    h1, h2 = HoatChat(ten="HC1"), HoatChat(ten="HC2")
    db.add_all([h1, h2])
    await db.flush()
    dm = await tao_danh_muc(db, "Cùng")
    goc = await sp_ban_duoc(db, "Gốc", danh_muc_id=dm.id)
    db.add_all([ThanhPhan(san_pham_id=goc.id, hoat_chat_id=h.id) for h in (h1, h2)])
    chung_hai = await sp_ban_duoc(db, "ChungHai")  # khác danh mục, chung 2 hoạt chất
    db.add_all([ThanhPhan(san_pham_id=chung_hai.id, hoat_chat_id=h.id) for h in (h1, h2)])
    chung_mot = await sp_ban_duoc(db, "ChungMột")
    db.add(ThanhPhan(san_pham_id=chung_mot.id, hoat_chat_id=h1.id))
    await sp_ban_duoc(db, "CùngDanhMục", danh_muc_id=dm.id)
    ke_don = await sp_ban_duoc(db, "KêĐơnChung", loai="thuoc_ke_don", danh_muc_id=dm.id)
    db.add(ThanhPhan(san_pham_id=ke_don.id, hoat_chat_id=h1.id))
    await sp_ban_duoc(db, "Ngừng", danh_muc_id=dm.id, trang_thai="ngung_kinh_doanh")
    await sp_ban_duoc(db, "KhôngLiênQuan")
    await db.flush()
    tuong_tu = (await lay(client, goc)).json()["tuong_tu"]
    assert [t["ten"] for t in tuong_tu] == ["ChungHai", "ChungMột", "CùngDanhMục"]
    assert set(tuong_tu[0]) >= {"id", "ten", "slug", "gia", "con_hang", "can_tu_van"}


async def test_xem_thuoc_ke_don_cung_khong_goi_y_thuoc_ke_don_khac(client, db):
    dm = await tao_danh_muc(db, "Cùng")
    a = await sp_ban_duoc(db, "A", loai="thuoc_ke_don", danh_muc_id=dm.id)
    await sp_ban_duoc(db, "B", loai="thuoc_ke_don", danh_muc_id=dm.id)
    thuong = await sp_ban_duoc(db, "Thường", danh_muc_id=dm.id)
    assert [t["ten"] for t in (await lay(client, a)).json()["tuong_tu"]] == ["Thường"]
    assert thuong.id


async def test_toi_da_8_san_pham_tuong_tu(client, db):
    dm = await tao_danh_muc(db, "Cùng")
    goc = await sp_ban_duoc(db, "Gốc", danh_muc_id=dm.id)
    for i in range(10):
        await sp_ban_duoc(db, f"T{i}", danh_muc_id=dm.id)
    assert len((await lay(client, goc)).json()["tuong_tu"]) == 8


# --- Lịch sử xem -------------------------------------------------------------------------------------------------------


async def so_lich_su(db, **loc) -> list[LichSuXem]:
    return list((await db.execute(select(LichSuXem).filter_by(**loc).order_by(LichSuXem.id))).scalars())


async def test_khach_thanh_vien_ghi_lich_su_theo_token_khong_tin_client(dang_nhap_khach, db):
    sp = await sp_ban_duoc(db)
    phan_hoi = await lay(
        dang_nhap_khach, sp, params={"nguon": "tim_kiem"}, headers={"X-Ma-Phien": "phien-cua-nguoi-khac"}
    )
    assert phan_hoi.status_code == 200
    dong = await so_lich_su(db, san_pham_id=sp.id)
    assert len(dong) == 1
    assert dong[0].khach_hang_id == dang_nhap_khach.tai_khoan.id and dong[0].ma_phien is None  # mã phiên bị bỏ qua
    assert dong[0].nguon == "tim_kiem"


async def test_khach_vang_lai_ghi_theo_ma_phien_va_khong_ma_phien_thi_khong_ghi(client, db):
    sp = await sp_ban_duoc(db)
    assert (await lay(client, sp)).status_code == 200
    assert await so_lich_su(db, san_pham_id=sp.id) == []
    assert (await lay(client, sp, headers={"X-Ma-Phien": "abcdEFGH_12-34"})).status_code == 200
    dong = await so_lich_su(db, san_pham_id=sp.id)
    assert len(dong) == 1 and dong[0].ma_phien == "abcdEFGH_12-34" and dong[0].khach_hang_id is None
    assert dong[0].nguon is None


@pytest.mark.parametrize("sai", ["ngan", "a" * 65, "co dau cach 12345", "tiếng-việt-123456", "a;b=c-1234567"])
async def test_ma_phien_sai_dinh_dang_bi_bo_qua_khong_gay_loi(client, db, sai):
    sp = await sp_ban_duoc(db)
    phan_hoi = await lay(client, sp, headers={"X-Ma-Phien": sai.encode("utf-8")})
    assert phan_hoi.status_code == 200
    assert await so_lich_su(db, san_pham_id=sp.id) == []


def test_ma_phien_hop_le():
    assert ma_phien_hop_le("abcdefgh") == "abcdefgh" and ma_phien_hop_le("a" * 64) == "a" * 64
    assert ma_phien_hop_le(None) is None and ma_phien_hop_le("abcdefg") is None and ma_phien_hop_le("a" * 65) is None
    assert ma_phien_hop_le("abcdefgh\n") is None  # `$` thường chấp nhận "\n" cuối: phải dùng fullmatch


async def test_xem_lai_trong_30_phut_chi_giu_mot_dong_sau_30_phut_ghi_them(client, db):
    sp = await sp_ban_duoc(db)
    khac = await sp_ban_duoc(db)
    dau = {"X-Ma-Phien": "phien-so-mot"}
    for _ in range(3):
        await lay(client, sp, headers=dau)
    await lay(client, khac, headers=dau)  # sản phẩm khác: dòng riêng
    await lay(client, sp, headers={"X-Ma-Phien": "phien-so-hai"})  # người khác: dòng riêng
    assert len(await so_lich_su(db, san_pham_id=sp.id)) == 2 and len(await so_lich_su(db, san_pham_id=khac.id)) == 1
    for dong in await so_lich_su(db, san_pham_id=sp.id, ma_phien="phien-so-mot"):
        dong.created_at = bay_gio_utc() - timedelta(minutes=31)
    await db.flush()
    await lay(client, sp, headers=dau)
    assert len(await so_lich_su(db, san_pham_id=sp.id, ma_phien="phien-so-mot")) == 2


async def test_nguon_sai_la_400_va_san_pham_khong_hien_thi_khong_ghi_lich_su(client, db):
    sp = await sp_ban_duoc(db)
    dau = {"X-Ma-Phien": "phien-so-mot"}
    assert (await lay(client, sp, params={"nguon": "khong_co"}, headers=dau)).status_code == 400
    an = await sp_ban_duoc(db, trang_thai="ngung_kinh_doanh")
    assert (await lay(client, an, headers=dau)).status_code == 404
    assert (await db.scalar(select(func.count()).select_from(LichSuXem))) == 0


async def test_token_khach_het_han_tra_401_de_client_lam_moi_con_token_vo_nghia_la_khach_vang_lai(client, db):
    sp = await sp_ban_duoc(db)
    phan_hoi = await lay(client, sp, headers={"Authorization": "Bearer khong-phai-jwt"})
    assert phan_hoi.status_code == 200  # token vô nghĩa = khách vãng lai, không phải lỗi

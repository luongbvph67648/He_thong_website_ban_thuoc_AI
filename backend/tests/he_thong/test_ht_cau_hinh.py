"""AD08: Admin xem và sửa cấu hình hệ thống (/api/v1/noi-bo/cau-hinh)."""

import asyncio

import pytest
from app.modules.he_thong import cau_hinh_service
from sqlalchemy import func, select

from app.core import phan_quyen
from app.core.cau_hinh import doc_cau_hinh
from app.core.cau_hinh_khoa import KHOA_CAU_HINH, dau_van_tay
from app.core.loi import LoiNghiepVu
from app.models.he_thong import CauHinh, NhanVien, NhatKyHeThong, Quyen, VaiTro, VaiTroQuyen
from tests.factories import tao_nhan_vien
from tests.nhan_vien.dung_chung import nhat_ky

GOC = "/api/v1/noi-bo/cau-hinh"


def la_loi(phan_hoi, status, ma_loi):
    return phan_hoi.status_code == status and phan_hoi.json()["ma_loi"] == ma_loi


async def gia_tri_trong_db(db, khoa):
    return (await db.execute(select(CauHinh.gia_tri).where(CauHinh.khoa == khoa))).scalar_one_or_none()


async def dat(admin, khoa, gia_tri, phien_ban=None):
    """PUT như giao diện: gửi kèm `phien_ban` vừa đọc, trừ khi test chủ động truyền bản khác."""
    if phien_ban is None:
        muc = next(m for m in (await admin.get(GOC)).json() if m["khoa"] == khoa)
        phien_ban = muc["phien_ban"]
    return await admin.put(f"{GOC}/{khoa}", json={"gia_tri": gia_tri, "phien_ban": phien_ban})


# --- Đọc -------------------------------------------------------------------------------------------------------------


async def test_danh_sach_gom_dung_cac_khoa_ad08_theo_nhom_va_khong_co_khoa_ai(dang_nhap_admin):
    phan_hoi = await dang_nhap_admin.get(GOC)
    assert phan_hoi.status_code == 200
    ds = phan_hoi.json()
    assert [m["khoa"] for m in ds] == list(KHOA_CAU_HINH)  # đúng thứ tự hiển thị của bảng khóa
    assert not [m for m in ds if m["khoa"].startswith("ai_")]
    nhom = [m["nhom"] for m in ds]
    assert nhom == sorted(nhom, key=nhom.index) and len(set(nhom)) < len(nhom)  # cùng nhóm đứng liền nhau
    assert all(
        {"khoa", "nhom", "nhan", "mo_ta", "kieu", "don_vi", "toi_thieu", "toi_da", "truong", "gia_tri", "phien_ban"}
        <= set(m)
        for m in ds
    )


async def test_gia_tri_la_gia_tri_seed_va_phien_ban_la_dau_van_tay_noi_dung(dang_nhap_admin, db):
    theo_khoa = {m["khoa"]: m for m in (await dang_nhap_admin.get(GOC)).json()}
    assert theo_khoa["nguong_can_han_ngay"]["gia_tri"] == 90 and theo_khoa["nguong_can_han_ngay"]["kieu"] == "so"
    assert theo_khoa["nguong_can_han_ngay"]["toi_thieu"] == 1 and theo_khoa["nguong_can_han_ngay"]["toi_da"] == 730
    assert theo_khoa["nguong_can_han_ngay"]["don_vi"] == "ngày" and theo_khoa["nguong_can_han_ngay"]["mo_ta"]
    assert theo_khoa["phi_ship_mac_dinh"]["kieu"] == "tien" and theo_khoa["phi_ship_mac_dinh"]["gia_tri"] == 30000
    otp = theo_khoa["gioi_han_otp"]
    assert otp["kieu"] == "nhom_so" and otp["gia_tri"] == {"moi_sdt_moi_gio": 5, "moi_ip_moi_gio": 20}
    assert [t["ten"] for t in otp["truong"]] == ["moi_sdt_moi_gio", "moi_ip_moi_gio"] and otp["truong"][0][
        "toi_da"
    ] == 20
    assert theo_khoa["gio_lam_viec_duoc_si"]["kieu"] == "gio_lam_viec"
    for m in theo_khoa.values():
        assert m["phien_ban"] == dau_van_tay(m["gia_tri"])
        assert m["nhan_vien_cap_nhat"] is None  # seed không do nhân viên nào đặt


async def test_khoa_chua_co_trong_bang_van_duoc_liet_ke_voi_gia_tri_null_va_dat_duoc(dang_nhap_admin, db):
    await db.execute(CauHinh.__table__.delete().where(CauHinh.khoa == "thoi_han_doi_tra_ngay"))
    muc = next(m for m in (await dang_nhap_admin.get(GOC)).json() if m["khoa"] == "thoi_han_doi_tra_ngay")
    assert muc["gia_tri"] is None and muc["mo_ta"] is None and muc["phien_ban"] == dau_van_tay(None)
    phan_hoi = await dat(dang_nhap_admin, "thoi_han_doi_tra_ngay", 10)
    assert phan_hoi.status_code == 200 and phan_hoi.json()["gia_tri"] == 10
    assert await gia_tri_trong_db(db, "thoi_han_doi_tra_ngay") == 10


# --- Sửa -------------------------------------------------------------------------------------------------------------


async def test_sua_ghi_nguoi_cap_nhat_thoi_gian_nhat_ky_va_co_hieu_luc_ngay(dang_nhap_admin, db):
    truoc = next(m for m in (await dang_nhap_admin.get(GOC)).json() if m["khoa"] == "so_lan_dang_nhap_sai_toi_da")
    phan_hoi = await dat(dang_nhap_admin, "so_lan_dang_nhap_sai_toi_da", 3)
    assert phan_hoi.status_code == 200
    than = phan_hoi.json()
    assert than["gia_tri"] == 3 and than["phien_ban"] == dau_van_tay(3) != truoc["phien_ban"]
    admin = dang_nhap_admin.tai_khoan
    assert than["nhan_vien_cap_nhat"] == {"id": admin.id, "ma_nhan_vien": admin.ma_nhan_vien, "ho_ten": admin.ho_ten}
    assert than["updated_at"] and than["updated_at"] != truoc["updated_at"]
    assert await doc_cau_hinh(db, "so_lan_dang_nhap_sai_toi_da", 5) == 3  # nơi dùng đọc mỗi lần: hiệu lực ngay
    (dong,) = await nhat_ky(db, admin.id, "sua")
    assert (dong.bang, dong.ban_ghi_id) == ("cau_hinh", "so_lan_dang_nhap_sai_toi_da")
    assert (dong.gia_tri_cu, dong.gia_tri_moi) == (5, 3)
    ds = {m["khoa"]: m for m in (await dang_nhap_admin.get(GOC)).json()}
    assert ds["so_lan_dang_nhap_sai_toi_da"]["nhan_vien_cap_nhat"]["id"] == admin.id


async def test_sua_nhom_so_va_gio_lam_viec_luu_dung_cau_truc_da_chuan_hoa(dang_nhap_admin, db):
    assert (await dat(dang_nhap_admin, "gioi_han_otp", {"moi_sdt_moi_gio": 3, "moi_ip_moi_gio": 50})).status_code == 200
    assert await gia_tri_trong_db(db, "gioi_han_otp") == {"moi_sdt_moi_gio": 3, "moi_ip_moi_gio": 50}
    gio = {"bat_dau": "07:30", "ket_thuc": "22:00", "ngay_trong_tuan": [6, 1, 3]}
    phan_hoi = await dat(dang_nhap_admin, "gio_lam_viec_duoc_si", gio)
    assert phan_hoi.status_code == 200 and phan_hoi.json()["gia_tri"]["ngay_trong_tuan"] == [1, 3, 6]
    assert (await gia_tri_trong_db(db, "gio_lam_viec_duoc_si"))["ngay_trong_tuan"] == [1, 3, 6]


async def test_dat_dung_gia_tri_hien_tai_thi_khong_ghi_gi(dang_nhap_admin, db):
    phan_hoi = await dat(dang_nhap_admin, "nguong_can_han_ngay", 90)
    assert phan_hoi.status_code == 200 and phan_hoi.json()["nhan_vien_cap_nhat"] is None
    assert await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "sua") == []


@pytest.mark.parametrize(
    ("khoa", "sai"),
    [
        ("nguong_can_han_ngay", 0),
        ("nguong_can_han_ngay", 731),
        ("nguong_can_han_ngay", True),
        ("nguong_can_han_ngay", 90.5),
        ("nguong_can_han_ngay", "90"),
        ("nguong_can_han_ngay", None),
        ("nguong_can_han_ngay", 10**30),
        ("so_lan_dang_nhap_sai_toi_da", 1),  # dưới 3: ai cũng khóa tạm được tài khoản người khác
        ("thoi_han_thanh_toan_phut", -15),
        ("phi_ship_mac_dinh", 30000.5),
        ("mien_phi_ship_tu", 100_000_001),
        ("gioi_han_otp", {"moi_sdt_moi_gio": 0, "moi_ip_moi_gio": 20}),
        ("gioi_han_otp", {"moi_sdt_moi_gio": 5}),
        ("gioi_han_ai", [1, 2, 3]),
        ("gio_lam_viec_duoc_si", {"bat_dau": "21:00", "ket_thuc": "08:00", "ngay_trong_tuan": [1]}),
        ("gio_lam_viec_duoc_si", {"bat_dau": "08:00", "ket_thuc": "21:00", "ngay_trong_tuan": []}),
    ],
)
async def test_gia_tri_sai_bi_tu_choi_400_khong_doi_gi_va_khong_ghi_nhat_ky(dang_nhap_admin, db, khoa, sai):
    truoc = await gia_tri_trong_db(db, khoa)
    phan_hoi = await dat(dang_nhap_admin, khoa, sai)
    assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE")
    assert phan_hoi.json()["chi_tiet"] and all(c["truong"].startswith("gia_tri") for c in phan_hoi.json()["chi_tiet"])
    assert await gia_tri_trong_db(db, khoa) == truoc
    assert await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "sua") == []


@pytest.mark.parametrize(
    "khoa", ["ai_module", "ai_dau_hieu_nguy_hiem", "ai_nguong_chuyen_duoc_si", "ai_loi_nhac_bo_sung", "khong_co"]
)
async def test_khoa_cua_ad09_hoac_khong_co_la_404_va_khong_doi_gi(dang_nhap_admin, db, khoa):
    truoc = await gia_tri_trong_db(db, khoa)
    phan_hoi = await dang_nhap_admin.put(f"{GOC}/{khoa}", json={"gia_tri": 1, "phien_ban": "0" * 16})
    assert la_loi(phan_hoi, 404, "KHONG_TIM_THAY")
    assert await gia_tri_trong_db(db, khoa) == truoc


@pytest.mark.parametrize("khoa", ["NGUONG_CAN_HAN", "a" * 81, "nguong can han", "a;b"])
async def test_khoa_sai_dinh_dang_la_400(dang_nhap_admin, khoa):
    phan_hoi = await dang_nhap_admin.put(f"{GOC}/{khoa}", json={"gia_tri": 1, "phien_ban": "0" * 16})
    assert phan_hoi.status_code in (400, 404) and phan_hoi.status_code != 500


@pytest.mark.parametrize(
    "than",
    [
        {"gia_tri": 5},
        {"phien_ban": "0" * 16},
        {"gia_tri": 5, "phien_ban": "xyz"},
        {"gia_tri": 5, "phien_ban": "G" * 16},
        {},
    ],
)
async def test_thieu_hoac_sai_phien_ban_la_400(dang_nhap_admin, than):
    assert la_loi(await dang_nhap_admin.put(f"{GOC}/nguong_can_han_ngay", json=than), 400, "DU_LIEU_KHONG_HOP_LE")


async def test_trang_cu_khong_the_ghi_de_gia_tri_vua_duoc_admin_khac_doi(dang_nhap_admin, db):
    ban_cu = next(m for m in (await dang_nhap_admin.get(GOC)).json() if m["khoa"] == "nguong_can_han_ngay")["phien_ban"]
    assert (await dat(dang_nhap_admin, "nguong_can_han_ngay", 60)).status_code == 200  # Admin B
    phan_hoi = await dat(dang_nhap_admin, "nguong_can_han_ngay", 100, phien_ban=ban_cu)  # Admin A, trang cũ
    assert la_loi(phan_hoi, 409, "DU_LIEU_DA_THAY_DOI")
    assert await gia_tri_trong_db(db, "nguong_can_han_ngay") == 60
    assert len(await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "sua")) == 1


async def test_hai_admin_sua_cung_khoa_cung_luc_dung_mot_ben_thanh_cong_ben_kia_nhan_409(db_that):
    async with db_that() as s, s.begin():
        admin_id = (await tao_nhan_vien(s, "ADMIN")).id
        phien_ban = dau_van_tay(90)

    async def sua(gia_tri):
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, admin_id)
            await cau_hinh_service.cap_nhat(s, actor, "nguong_can_han_ngay", gia_tri, phien_ban, ip="127.0.0.1")
            await asyncio.sleep(0.3)  # giữ giao dịch mở để bên kia phải chờ khóa dòng

    ket_qua = await asyncio.wait_for(asyncio.gather(sua(60), sua(120), return_exceptions=True), timeout=20)
    that_bai = [k for k in ket_qua if k is not None]
    assert (
        len(that_bai) == 1 and isinstance(that_bai[0], LoiNghiepVu) and that_bai[0].ma_loi == "DU_LIEU_DA_THAY_DOI"
    ), ket_qua
    async with db_that() as s:
        cuoi = (await s.execute(select(CauHinh.gia_tri).where(CauHinh.khoa == "nguong_can_han_ngay"))).scalar_one()
        so_nhat_ky = (
            await s.execute(select(func.count()).select_from(NhatKyHeThong).where(NhatKyHeThong.bang == "cau_hinh"))
        ).scalar_one()
    assert cuoi == (60 if ket_qua[0] is None else 120) and so_nhat_ky == 1


# --- Phân quyền ------------------------------------------------------------------------------------------------------


async def test_chi_admin_dung_duoc_va_token_khach_bi_tu_choi(clients_theo_vai_tro, dang_nhap_khach, client):
    for vai_tro in ("PHARMACIST", "WAREHOUSE"):
        c = clients_theo_vai_tro[vai_tro]
        assert la_loi(await c.get(GOC), 403, "KHONG_CO_QUYEN")
        assert la_loi(
            await c.put(f"{GOC}/nguong_can_han_ngay", json={"gia_tri": 60, "phien_ban": "0" * 16}),
            403,
            "KHONG_CO_QUYEN",
        )
    assert (await client.get(GOC)).status_code == 401
    assert (await dang_nhap_khach.get(GOC)).status_code == 401


async def test_config_manage_cap_ngoai_ad18_van_khong_cho_phep_ghi(clients_theo_vai_tro, dang_nhap_admin, db):
    """Lớp phòng thủ thứ hai (QĐ-13): dược sĩ giữ `config.manage` do cấu hình sai vẫn không sửa được cấu hình."""
    duoc_si = clients_theo_vai_tro["PHARMACIST"]
    quyen_id = (await db.execute(select(Quyen.id).where(Quyen.ma == "config.manage"))).scalar_one()
    vai_tro_id = (await db.execute(select(VaiTro.id).where(VaiTro.ma == "PHARMACIST"))).scalar_one()
    db.add(VaiTroQuyen(vai_tro_id=vai_tro_id, quyen_id=quyen_id, gioi_han=None))
    await db.flush()
    phan_quyen.xoa_cache_quyen()
    so_nhat_ky = (await db.execute(select(func.count()).select_from(NhatKyHeThong))).scalar_one()
    phien_ban = dau_van_tay(90)
    assert la_loi(
        await duoc_si.put(f"{GOC}/nguong_can_han_ngay", json={"gia_tri": 1, "phien_ban": phien_ban}),
        403,
        "KHONG_CO_QUYEN",
    )
    assert await gia_tri_trong_db(db, "nguong_can_han_ngay") == 90
    assert (await db.execute(select(func.count()).select_from(NhatKyHeThong))).scalar_one() == so_nhat_ky

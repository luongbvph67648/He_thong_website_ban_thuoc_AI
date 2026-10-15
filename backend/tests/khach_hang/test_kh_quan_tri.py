"""AD02: Admin quản lý khách hàng (/api/v1/noi-bo/khach-hang): danh sách, chi tiết, lịch sử mua, khóa/mở khóa."""

import asyncio
import json
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.core import phan_quyen
from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc
from app.models.enums import TrangThaiTaiKhoan
from app.models.he_thong import NhanVien, NhatKyHeThong, PhienDangNhap, Quyen, VaiTro, VaiTroQuyen
from app.models.khach_hang import DiUng, HoSoSucKhoe, KhachHang
from app.models.san_pham import HoatChat
from app.modules.tai_khoan import phien, quan_tri_khach
from app.modules.tai_khoan.phien import KetQuaLamMoi
from tests.factories import tao_don, tao_khach, tao_nhan_vien
from tests.nhan_vien.dung_chung import nhat_ky
from tests.tai_khoan import dung_chung as khach_chung

GOC = "/api/v1/noi-bo/khach-hang"

# Giá trị nhạy cảm gieo vào hồ sơ sức khỏe: không được xuất hiện ở BẤT KỲ phản hồi nào của AD02 (spec 03 mục 5.1).
BENH_NEN = "Tiểu đường tuýp hai, suy thận mạn"
GHI_CHU_DI_UNG = "Sốc phản vệ lần hai"
KHOA_CAM = {"ho_so_suc_khoe", "di_ung", "benh_nen", "nam_sinh", "dang_mang_thai", "dang_cho_con_bu", "hoat_chat_id"}


def la_loi(phan_hoi, status, ma_loi):
    return phan_hoi.status_code == status and phan_hoi.json()["ma_loi"] == ma_loi


def moi_khoa(du_lieu):
    """Mọi tên khóa JSON ở mọi mức lồng nhau."""
    if isinstance(du_lieu, dict):
        for k, v in du_lieu.items():
            yield k
            yield from moi_khoa(v)
    elif isinstance(du_lieu, list):
        for v in du_lieu:
            yield from moi_khoa(v)


def khong_lo_du_lieu_nhay_cam(phan_hoi):
    """Không chứa khóa sức khỏe/mật khẩu và không chứa giá trị đã gieo, dù ở dạng nào (kể cả bị đặt tên khác)."""
    khoa = set(moi_khoa(phan_hoi.json()))
    assert not (khoa & KHOA_CAM), khoa & KHOA_CAM
    assert not [k for k in khoa if "mat_khau" in k or "hash" in k], khoa
    van_ban = json.dumps(phan_hoi.json(), ensure_ascii=False)
    for gia_tri in (BENH_NEN, GHI_CHU_DI_UNG, "Amoxicillin"):
        assert gia_tri not in van_ban


async def gieo_ho_so_suc_khoe(db, khach: KhachHang) -> None:
    hoat_chat = HoatChat(ten="Amoxicillin")
    db.add(hoat_chat)
    await db.flush()
    db.add(
        HoSoSucKhoe(
            khach_hang_id=khach.id,
            nam_sinh=1980,
            benh_nen=BENH_NEN,
            dang_mang_thai=True,
            dang_cho_con_bu=False,
            dong_y_su_dung=True,
            dong_y_luc=bay_gio_utc(),
        )
    )
    db.add(DiUng(khach_hang_id=khach.id, hoat_chat_id=hoat_chat.id, ghi_chu=GHI_CHU_DI_UNG))
    await db.flush()


async def so_phien_khach(db, khach_id: int) -> tuple[int, int]:
    """(tổng phiên, phiên còn hiệu lực)."""
    phien_khach = list(
        (await db.execute(select(PhienDangNhap).where(PhienDangNhap.khach_hang_id == khach_id))).scalars()
    )
    return len(phien_khach), len([p for p in phien_khach if p.thu_hoi_luc is None])


# --- Danh sách -------------------------------------------------------------------------------------------------------


async def test_danh_sach_dung_hinh_dang_va_khong_lo_bi_mat(dang_nhap_admin, db):
    khach = await tao_khach(db, ho_ten="Lê Minh Anh", email="minhanh@example.com", so_dien_thoai="0901234567")
    await gieo_ho_so_suc_khoe(db, khach)
    phan_hoi = await dang_nhap_admin.get(GOC)
    assert phan_hoi.status_code == 200
    than = phan_hoi.json()
    assert set(than) == {"du_lieu", "tong", "trang", "kich_thuoc"} and than["tong"] == 1
    assert set(than["du_lieu"][0]) == {"id", "ho_ten", "email", "so_dien_thoai", "trang_thai", "khoa_den", "created_at"}
    assert than["du_lieu"][0]["so_dien_thoai"] == "0901234567" and than["du_lieu"][0]["trang_thai"] == "hoat_dong"
    khong_lo_du_lieu_nhay_cam(phan_hoi)


async def test_danh_sach_khong_co_khach_da_xoa_va_moi_nhat_truoc(dang_nhap_admin, db):
    cu = await tao_khach(db, ho_ten="Khách Cũ")
    da_xoa = await tao_khach(db, ho_ten="Khách Đã Xóa")
    da_xoa.deleted_at = bay_gio_utc()
    moi = await tao_khach(db, ho_ten="Khách Mới")
    cu.created_at = bay_gio_utc().replace(year=2020)
    await db.flush()
    ten = [d["ho_ten"] for d in (await dang_nhap_admin.get(GOC)).json()["du_lieu"]]
    assert ten == [moi.ho_ten, cu.ho_ten]
    assert (await dang_nhap_admin.get(f"{GOC}/{da_xoa.id}")).status_code == 404


@pytest.mark.parametrize(
    ("q", "mong_doi"),
    [
        ("nguyen", {"Nguyễn Văn An"}),  # không phân biệt dấu
        ("NGUYỄN văn", {"Nguyễn Văn An"}),  # không phân biệt hoa thường
        ("tran", {"Trần Thị Bình"}),
        ("binh@MAIL", {"Trần Thị Bình"}),  # email, không phân biệt hoa thường
        ("0901", {"Nguyễn Văn An", "Lê Cường"}),  # một phần số điện thoại
        ("0902 345 678", {"Trần Thị Bình"}),  # có khoảng trắng
        ("+84 902-345-678", {"Trần Thị Bình"}),  # mã quốc gia như người dùng gõ
        ("84901234567", {"Nguyễn Văn An"}),
        ("100%", set()),  # % và _ là ký tự thường, không phải ký tự thay thế
        ("_", set()),
        ("khong.co.ai", set()),
    ],
)
async def test_tim_theo_ten_email_so_dien_thoai(dang_nhap_admin, db, q, mong_doi):
    await tao_khach(db, ho_ten="Nguyễn Văn An", email="an@example.com", so_dien_thoai="0901234567")
    await tao_khach(db, ho_ten="Trần Thị Bình", email="binh@mail.vn", so_dien_thoai="0902345678")
    await tao_khach(db, ho_ten="Lê Cường", email=None, so_dien_thoai="0901999888")
    phan_hoi = await dang_nhap_admin.get(GOC, params={"q": q})
    assert phan_hoi.status_code == 200
    assert {d["ho_ten"] for d in phan_hoi.json()["du_lieu"]} == mong_doi


async def test_loc_theo_trang_thai_va_phan_trang(dang_nhap_admin, db):
    for i in range(5):
        await tao_khach(db, ho_ten=f"Khách {i}")
    khoa = await tao_khach(db, ho_ten="Khách Bị Khóa", trang_thai=TrangThaiTaiKhoan.bi_khoa)
    bi_khoa = (await dang_nhap_admin.get(GOC, params={"trang_thai": "bi_khoa"})).json()
    assert [d["id"] for d in bi_khoa["du_lieu"]] == [khoa.id] and bi_khoa["tong"] == 1
    trang = (await dang_nhap_admin.get(GOC, params={"kich_thuoc": 4, "trang": 2})).json()
    assert trang["tong"] == 6 and len(trang["du_lieu"]) == 2 and trang["trang"] == 2
    assert (await dang_nhap_admin.get(GOC, params={"trang_thai": "khong_co"})).status_code == 400


async def test_sap_xep_theo_ten_khong_dau_va_truong_la_bi_chan(dang_nhap_admin, db):
    for ten in ("Đức Anh", "An Nam", "Ân Bình", "Cường"):
        await tao_khach(db, ho_ten=ten)
    tang = [d["ho_ten"] for d in (await dang_nhap_admin.get(GOC, params={"sap_xep": "ho_ten"})).json()["du_lieu"]]
    assert tang[-2:] == ["Cường", "Đức Anh"] and set(tang[:2]) == {"An Nam", "Ân Bình"}
    giam = [d["ho_ten"] for d in (await dang_nhap_admin.get(GOC, params={"sap_xep": "-ho_ten"})).json()["du_lieu"]]
    assert giam == list(reversed(tang))
    for sai in ("mat_khau_hash", "-mat_khau_hash", "id;drop"):
        assert la_loi(await dang_nhap_admin.get(GOC, params={"sap_xep": sai}), 400, "DU_LIEU_KHONG_HOP_LE")


# --- Chi tiết và lịch sử mua -------------------------------------------------------------------------------------------


async def test_chi_tiet_co_thong_tin_lien_he_so_don_va_khong_lo_bi_mat(dang_nhap_admin, db):
    khach = await tao_khach(db, ho_ten="Phạm Thu Hà", gioi_tinh="nu", so_dien_thoai="0933444555")
    await gieo_ho_so_suc_khoe(db, khach)
    await tao_don(db, khach)
    await tao_don(db, khach, trang_thai="da_giao")
    phan_hoi = await dang_nhap_admin.get(f"{GOC}/{khach.id}")
    assert phan_hoi.status_code == 200
    than = phan_hoi.json()
    assert than["id"] == khach.id and than["ho_ten"] == "Phạm Thu Hà" and than["so_dien_thoai"] == "0933444555"
    assert than["gioi_tinh"] == "nu" and than["so_don_hang"] == 2 and than["dong_y_chinh_sach_luc"]
    assert set(than) == {
        "id", "ho_ten", "email", "so_dien_thoai", "gioi_tinh", "trang_thai", "khoa_den",
        "dong_y_chinh_sach_luc", "created_at", "updated_at", "so_don_hang",
    }  # fmt: skip
    khong_lo_du_lieu_nhay_cam(phan_hoi)


@pytest.mark.parametrize(
    ("khach_id", "ma_trang_thai", "ma_loi"),
    [
        (2_000_000_000, 404, "KHONG_TIM_THAY"),
        (2_147_483_648, 400, "DU_LIEU_KHONG_HOP_LE"),
        (0, 400, "DU_LIEU_KHONG_HOP_LE"),
        (-5, 400, "DU_LIEU_KHONG_HOP_LE"),
    ],
)
async def test_khach_khong_co_hoac_id_vo_ly(dang_nhap_admin, khach_id, ma_trang_thai, ma_loi):
    for duong_dan in (f"{GOC}/{khach_id}", f"{GOC}/{khach_id}/don-hang"):
        assert la_loi(await dang_nhap_admin.get(duong_dan), ma_trang_thai, ma_loi)


async def test_lich_su_mua_chi_gom_don_cua_khach_do_moi_nhat_truoc_va_khong_lo_chi_tiet_giao_hang(dang_nhap_admin, db):
    khach = await tao_khach(db)
    khac = await tao_khach(db)
    await gieo_ho_so_suc_khoe(db, khach)
    d1 = await tao_don(db, khach, ten_nguoi_nhan="Người Nhận Bí Mật", dia_chi_giao="12 Phố Riêng Tư", ghi_chu="ghi chú")
    d2 = await tao_don(db, khach, trang_thai="da_giao", phi_van_chuyen=Decimal("30000"))
    await tao_don(db, khac)  # đơn người khác
    await tao_don(db, None)  # đơn khách lẻ tại quầy
    d1.created_at = bay_gio_utc().replace(year=2021)
    await db.flush()
    phan_hoi = await dang_nhap_admin.get(f"{GOC}/{khach.id}/don-hang")
    assert phan_hoi.status_code == 200
    than = phan_hoi.json()
    assert [d["ma_don"] for d in than["du_lieu"]] == [d2.ma_don, d1.ma_don] and than["tong"] == 2
    dong = than["du_lieu"][0]
    assert set(dong) == {"id", "ma_don", "kenh_ban", "trang_thai", "trang_thai_tt", "tong_tien", "created_at"}
    assert dong["trang_thai"] == "da_giao" and dong["tong_tien"] == f"{d2.tong_tien:.2f}"  # tiền là chuỗi số
    van_ban = json.dumps(than, ensure_ascii=False)
    assert "Người Nhận Bí Mật" not in van_ban and "12 Phố Riêng Tư" not in van_ban and "token" not in van_ban
    khong_lo_du_lieu_nhay_cam(phan_hoi)
    trang = (await dang_nhap_admin.get(f"{GOC}/{khach.id}/don-hang", params={"kich_thuoc": 1, "trang": 2})).json()
    assert [d["ma_don"] for d in trang["du_lieu"]] == [d1.ma_don] and trang["tong"] == 2


async def test_khach_chua_co_don_thi_lich_su_rong(dang_nhap_admin, db):
    khach = await tao_khach(db)
    assert (await dang_nhap_admin.get(f"{GOC}/{khach.id}/don-hang")).json()["du_lieu"] == []
    assert (await dang_nhap_admin.get(f"{GOC}/{khach.id}")).json()["so_don_hang"] == 0


# --- Khóa và mở khóa ---------------------------------------------------------------------------------------------------


async def test_khoa_dat_bi_khoa_thu_hoi_moi_phien_va_ghi_nhat_ky_co_ly_do(dang_nhap_admin, db):
    khach = await tao_khach(db)
    await phien.tao_phien(db, loai="khach", chu_id=khach.id)
    await phien.tao_phien(db, loai="khach", chu_id=khach.id)
    assert await so_phien_khach(db, khach.id) == (2, 2)
    phan_hoi = await dang_nhap_admin.post(f"{GOC}/{khach.id}/khoa", json={"ly_do": "Hủy đơn liên tục, quấy rối"})
    assert phan_hoi.status_code == 200 and phan_hoi.json()["trang_thai"] == "bi_khoa"
    khong_lo_du_lieu_nhay_cam(phan_hoi)
    assert await so_phien_khach(db, khach.id) == (2, 0)
    (dong,) = await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "khoa")
    assert (dong.bang, dong.ban_ghi_id) == ("khach_hang", str(khach.id))
    assert dong.gia_tri_moi == {"ly_do": "Hủy đơn liên tục, quấy rối"}
    assert "0901" not in json.dumps(dong.gia_tri_moi)  # nhật ký không chứa số điện thoại đầy đủ


async def test_khoa_khong_can_than_yeu_cau_va_goi_lai_van_thanh_cong(dang_nhap_admin, db):
    khach = await tao_khach(db)
    assert (await dang_nhap_admin.post(f"{GOC}/{khach.id}/khoa")).status_code == 200  # không có thân
    assert (await dang_nhap_admin.post(f"{GOC}/{khach.id}/khoa", json={})).status_code == 200  # gọi lại
    assert len(await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "khoa")) == 1  # lần hai không ghi thêm


@pytest.mark.parametrize("ly_do", ["x" * 301, 123, {"a": 1}])
async def test_ly_do_khoa_qua_dai_hoac_sai_kieu_tra_400(dang_nhap_admin, db, ly_do):
    khach = await tao_khach(db)
    assert la_loi(
        await dang_nhap_admin.post(f"{GOC}/{khach.id}/khoa", json={"ly_do": ly_do}), 400, "DU_LIEU_KHONG_HOP_LE"
    )
    await db.refresh(khach)
    assert khach.trang_thai == TrangThaiTaiKhoan.hoat_dong


async def test_khach_bi_khoa_mat_quyen_ngay_ca_voi_token_dang_dung(dang_nhap_admin, app, db, client):
    """Khóa có hiệu lực ngay (không đợi access token hết hạn), làm mới và đăng nhập đều bị từ chối."""
    khach = await tao_khach(db, so_dien_thoai="0912345678")
    dang_nhap = await khach_chung.dang_nhap(client)
    assert dang_nhap.status_code == 200
    token = dang_nhap.json()["access_token"]
    refresh = khach_chung.cookie_refresh(dang_nhap)
    tieu_de = {"Authorization": f"Bearer {token}"}
    assert (await client.get("/api/v1/toi", headers=tieu_de)).status_code == 200

    assert (await dang_nhap_admin.post(f"{GOC}/{khach.id}/khoa")).status_code == 200
    assert la_loi(await client.get("/api/v1/toi", headers=tieu_de), 403, "TAI_KHOAN_BI_KHOA")
    assert la_loi(await khach_chung.lam_moi(client, refresh), 401, "CHUA_DANG_NHAP")  # phiên đã thu hồi
    assert la_loi(await khach_chung.dang_nhap(client), 403, "TAI_KHOAN_BI_KHOA")  # mật khẩu đúng
    sai = await khach_chung.dang_nhap(client, mat_khau="Sai-mat-khau-1")
    assert la_loi(
        sai, 401, "SAI_THONG_TIN_DANG_NHAP"
    )  # sai mật khẩu vẫn như tài khoản bình thường (không lộ trạng thái)


async def test_mo_khoa_xoa_khoa_tam_bo_dem_sai_va_cho_dang_nhap_lai(dang_nhap_admin, db, client):
    khach = await tao_khach(
        db,
        so_dien_thoai="0912345678",
        trang_thai=TrangThaiTaiKhoan.bi_khoa,
        so_lan_dang_nhap_sai=5,
        khoa_den=bay_gio_utc().replace(year=2099),
    )
    assert la_loi(await khach_chung.dang_nhap(client), 403, "TAI_KHOAN_BI_KHOA")
    phan_hoi = await dang_nhap_admin.post(f"{GOC}/{khach.id}/mo-khoa")
    assert phan_hoi.status_code == 200
    assert phan_hoi.json()["trang_thai"] == "hoat_dong" and phan_hoi.json()["khoa_den"] is None
    await db.refresh(khach)
    assert khach.so_lan_dang_nhap_sai == 0
    assert (await khach_chung.dang_nhap(client)).status_code == 200
    (dong,) = await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "mo_khoa")
    assert (dong.bang, dong.ban_ghi_id) == ("khach_hang", str(khach.id))
    assert (await dang_nhap_admin.post(f"{GOC}/{khach.id}/mo-khoa")).status_code == 200  # đã mở: gọi lại vẫn 200
    assert len(await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "mo_khoa")) == 1


async def test_khoa_mo_khoa_khach_da_xoa_hoac_khong_co_la_404(dang_nhap_admin, db):
    da_xoa = await tao_khach(db)
    da_xoa.deleted_at = bay_gio_utc()
    await db.flush()
    for id_ in (da_xoa.id, 2_000_000_000):
        for hau_to in ("khoa", "mo-khoa"):
            assert la_loi(await dang_nhap_admin.post(f"{GOC}/{id_}/{hau_to}"), 404, "KHONG_TIM_THAY")


async def test_khoa_khach_khong_dung_den_nhan_vien_cung_id(dang_nhap_admin, db):
    """Id nhân viên và id khách nằm ở hai bảng khác nhau: thao tác theo id khách không bao giờ chạm tài khoản nhân viên."""
    khach = await tao_khach(db)
    nv = await tao_nhan_vien(db, "WAREHOUSE")
    await phien.tao_phien(db, loai="noi_bo", chu_id=nv.id)
    await dang_nhap_admin.post(f"{GOC}/{khach.id}/khoa")
    await db.refresh(nv)
    assert nv.trang_thai == TrangThaiTaiKhoan.hoat_dong
    con_hieu_luc = (
        await db.execute(
            select(func.count())
            .select_from(PhienDangNhap)
            .where(PhienDangNhap.nhan_vien_id == nv.id, PhienDangNhap.thu_hoi_luc.is_(None))
        )
    ).scalar_one()
    assert con_hieu_luc == 1


# --- Phân quyền ---------------------------------------------------------------------------------------------------------


async def test_chi_admin_dung_duoc_va_token_khach_bi_tu_choi(clients_theo_vai_tro, dang_nhap_khach, client):
    for vai_tro in ("PHARMACIST", "WAREHOUSE"):
        c = clients_theo_vai_tro[vai_tro]
        assert la_loi(await c.get(GOC), 403, "KHONG_CO_QUYEN")
        assert la_loi(await c.post(f"{GOC}/1/khoa"), 403, "KHONG_CO_QUYEN")
    assert (await client.get(GOC)).status_code == 401
    assert (await dang_nhap_khach.get(GOC)).status_code == 401  # token khách không dùng được ở khu nội bộ


@pytest.mark.parametrize("hau_to", ["khoa", "mo-khoa"])
async def test_quyen_customer_manage_cap_ngoai_ad18_van_khong_cho_phep_thao_tac_ghi(clients_theo_vai_tro, db, hau_to):
    """Lớp phòng thủ thứ hai (QĐ-13): dù cấu hình sai khiến dược sĩ giữ `customer.manage` (gán thẳng vào DB), khóa và mở
    khóa khách vẫn đòi người thực hiện là ADMIN."""
    duoc_si = clients_theo_vai_tro["PHARMACIST"]
    quyen_id = (await db.execute(select(Quyen.id).where(Quyen.ma == "customer.manage"))).scalar_one()
    vai_tro_id = (await db.execute(select(VaiTro.id).where(VaiTro.ma == "PHARMACIST"))).scalar_one()
    db.add(VaiTroQuyen(vai_tro_id=vai_tro_id, quyen_id=quyen_id, gioi_han=None))
    await db.flush()
    phan_quyen.xoa_cache_quyen()
    khach = await tao_khach(db)
    so_nhat_ky = (await db.execute(select(func.count()).select_from(NhatKyHeThong))).scalar_one()
    assert la_loi(await duoc_si.post(f"{GOC}/{khach.id}/{hau_to}"), 403, "KHONG_CO_QUYEN")
    await db.refresh(khach)
    assert khach.trang_thai == TrangThaiTaiKhoan.hoat_dong
    assert (await db.execute(select(func.count()).select_from(NhatKyHeThong))).scalar_one() == so_nhat_ky


# --- Đồng thời ---------------------------------------------------------------------------------------------------------


async def test_khoa_khach_va_lam_moi_phien_dong_thoi_khong_deadlock_va_khong_de_lai_phien_song(db_that):
    """Cùng thứ tự khóa với đăng nhập/làm mới/đặt lại mật khẩu: dòng khách trước, dòng phiên sau (QĐ-12). Làm mới đang
    xoay vòng token (đã khóa dòng khách) thì Admin khóa phải CHỜ rồi thu hồi cả phiên mới; nếu ngược thứ tự, hai bên
    giữ khóa chéo nhau và Postgres hủy một giao dịch bằng deadlock."""
    async with db_that() as s, s.begin():
        khach_id = (await tao_khach(s)).id
        admin = await tao_nhan_vien(s, "ADMIN")
        refresh = (await phien.tao_phien(s, loai="khach", chu_id=khach_id)).refresh_token
        admin_id = admin.id

    dang_xoay = asyncio.Event()

    async def ke_lam_moi():
        async with db_that() as s, s.begin():
            kq = await phien.lam_moi_phien(s, refresh_token=refresh, loai="khach")
            dang_xoay.set()
            await asyncio.sleep(0.4)  # giữ giao dịch mở: Admin đang chạy đồng thời
            return kq.ket_qua

    async def admin_khoa():
        await dang_xoay.wait()
        async with db_that() as s, s.begin():
            actor = await s.get(type(admin), admin_id)
            await quan_tri_khach.khoa(s, actor, khach_id, ly_do=None, ip="127.0.0.1")

    ket_qua, _ = await asyncio.wait_for(asyncio.gather(ke_lam_moi(), admin_khoa()), timeout=15)
    assert ket_qua == KetQuaLamMoi.OK  # bên làm mới đến trước nên xoay vòng được
    async with db_that() as s:
        assert await so_phien_khach(s, khach_id) == (2, 0)  # phiên mới cấp cũng bị thu hồi: không còn phiên sống
        khach = await s.get(KhachHang, khach_id)
        assert khach.trang_thai == TrangThaiTaiKhoan.bi_khoa


async def test_khoa_goi_thang_service_voi_nguoi_thuc_hien_khong_phai_admin_bi_tu_choi(db):
    duoc_si = await tao_nhan_vien(db, "PHARMACIST")
    khach = await tao_khach(db)
    with pytest.raises(LoiNghiepVu) as loi:
        await quan_tri_khach.khoa(db, duoc_si, khach.id, ly_do=None, ip="127.0.0.1")
    assert loi.value.ma_loi == "KHONG_CO_QUYEN"


async def test_hai_admin_khoa_cung_mot_khach_cung_luc_chi_ghi_mot_nhat_ky(db_that):
    """Khóa dòng khách (`FOR UPDATE`) làm hai Admin tuần tự: bên đến sau thấy khách đã khóa và không ghi nhật ký thêm.
    Nếu không khóa dòng, cả hai cùng thấy "chưa khóa" và cùng ghi."""
    async with db_that() as s, s.begin():
        khach_id = (await tao_khach(s)).id
        admin_a = (await tao_nhan_vien(s, "ADMIN")).id
        admin_b = (await tao_nhan_vien(s, "ADMIN")).id

    async def khoa(admin_id, cho: float):
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, admin_id)
            await quan_tri_khach.khoa(s, actor, khach_id, ly_do=None, ip="127.0.0.1")
            await asyncio.sleep(cho)  # giữ giao dịch mở để bên kia phải chờ khóa dòng

    await asyncio.wait_for(asyncio.gather(khoa(admin_a, 0.4), khoa(admin_b, 0.0)), timeout=15)
    async with db_that() as s:
        so_nhat_ky = (
            await s.execute(select(func.count()).select_from(NhatKyHeThong).where(NhatKyHeThong.hanh_dong == "khoa"))
        ).scalar_one()
        assert so_nhat_ky == 1

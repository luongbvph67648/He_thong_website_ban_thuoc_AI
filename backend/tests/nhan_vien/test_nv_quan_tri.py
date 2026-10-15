"""AD01: quản lý tài khoản nhân viên (/api/v1/noi-bo/nhan-vien)."""

import asyncio
import json

import pytest
from sqlalchemy import select

from app.core.bao_mat import mat_khau_du_manh
from app.models.enums import TrangThaiTaiKhoan
from app.models.he_thong import NhanVien, PhienDangNhap
from app.modules.nhan_vien import quan_tri
from app.modules.tai_khoan import phien
from tests.factories import MAT_KHAU_TEST, tao_khach, tao_nhan_vien
from tests.nhan_vien.dung_chung import (
    cookie_refresh,
    dang_nhap,
    lam_moi,
    nhat_ky,
    so_phien_con_hieu_luc,
)

GOC = "/api/v1/noi-bo/nhan-vien"


def la_loi(phan_hoi, status, ma_loi):
    return phan_hoi.status_code == status and phan_hoi.json()["ma_loi"] == ma_loi


async def tao_qua_api(client, **tuy_chon):
    than = {"ho_ten": "Trần Văn Mới", "email": "moi@example.com", "vai_tro": "WAREHOUSE", **tuy_chon}
    return await client.post(GOC, json=than)


# --- Tạo ------------------------------------------------------------------------------------------------------------


async def test_tao_nhan_vien_sinh_mat_khau_tam_mot_lan_va_bat_doi_mat_khau(dang_nhap_admin, client, db):
    phan_hoi = await tao_qua_api(dang_nhap_admin, so_dien_thoai="+84 912 345 678", email="  Moi@Example.COM ")
    assert phan_hoi.status_code == 201
    than = phan_hoi.json()
    assert than["ma_nhan_vien"].startswith("NV") and than["email"] == "moi@example.com"
    assert than["vai_tro"]["ma"] == "WAREHOUSE" and than["trang_thai"] == "hoat_dong"
    assert than["phai_doi_mat_khau"] is True and than["so_dien_thoai"] == "0912345678"
    tam = than["mat_khau_tam"]
    assert mat_khau_du_manh(tam) and len(tam) >= 12
    assert "mat_khau_hash" not in than

    nv = (await db.execute(select(NhanVien).where(NhanVien.id == than["id"]))).scalar_one()
    assert tam not in nv.mat_khau_hash and nv.phai_doi_mat_khau is True
    # Nhân viên mới đăng nhập được bằng mật khẩu tạm và bị bắt đổi mật khẩu.
    dn = await dang_nhap(client, "moi@example.com", tam)
    assert dn.status_code == 200 and dn.json()["nhan_vien"]["phai_doi_mat_khau"] is True
    # Mật khẩu tạm không xuất hiện ở lần đọc sau.
    doc = await dang_nhap_admin.get(f"{GOC}/{than['id']}")
    assert "mat_khau_tam" not in doc.json() and tam not in doc.text


async def test_mat_khau_tam_khong_vao_nhat_ky_va_moi_lan_khac_nhau(dang_nhap_admin, db):
    a = (await tao_qua_api(dang_nhap_admin, email="a@example.com")).json()
    b = (await tao_qua_api(dang_nhap_admin, email="b@example.com")).json()
    assert a["mat_khau_tam"] != b["mat_khau_tam"]
    cac_dong = await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "tao")
    assert len(cac_dong) == 2
    toan_bo = json.dumps([[d.gia_tri_cu, d.gia_tri_moi, d.ban_ghi_id] for d in cac_dong])
    assert a["mat_khau_tam"] not in toan_bo and b["mat_khau_tam"] not in toan_bo and "argon2" not in toan_bo
    assert cac_dong[0].gia_tri_moi["vai_tro"] == "WAREHOUSE" and cac_dong[0].ban_ghi_id == str(a["id"])


async def test_tao_trung_email_ke_ca_khac_hoa_thuong_va_tai_khoan_da_xoa(dang_nhap_admin, db):
    await tao_nhan_vien(db, email="co.san@example.com")
    da_xoa = await tao_nhan_vien(db, email="da.xoa@example.com")
    da_xoa.deleted_at = da_xoa.created_at
    await db.flush()
    for email in ("co.san@example.com", "CO.SAN@example.com", "da.xoa@example.com"):
        phan_hoi = await tao_qua_api(dang_nhap_admin, email=email)
        assert la_loi(phan_hoi, 409, "TRUNG_DU_LIEU") and phan_hoi.json()["chi_tiet"] == {"truong": "email"}, email


async def test_tao_trung_email_da_luu_co_chu_hoa_van_bi_chan(dang_nhap_admin, db):
    """Ràng buộc unique của DB phân biệt hoa thường; kiểm tra bằng `lower()` mới bắt được email cũ lưu có chữ hoa
    (ví dụ Admin đầu tiên do seed tạo)."""
    await tao_nhan_vien(db, email="Mixed.Case@Example.com")
    phan_hoi = await tao_qua_api(dang_nhap_admin, email="mixed.case@example.com")
    assert la_loi(phan_hoi, 409, "TRUNG_DU_LIEU") and phan_hoi.json()["chi_tiet"] == {"truong": "email"}


@pytest.mark.parametrize(
    ("than", "truong"),
    [
        ({"ho_ten": ""}, "ho_ten"),
        ({"email": "khong-phai-email"}, "email"),
        ({"email": ""}, "email"),
        ({"so_dien_thoai": "0212345678"}, "so_dien_thoai"),
        ({"vai_tro": ""}, "vai_tro"),
    ],
)
async def test_tao_du_lieu_sai_tra_400(dang_nhap_admin, than, truong):
    phan_hoi = await tao_qua_api(dang_nhap_admin, **than)
    assert phan_hoi.status_code == 400 and phan_hoi.json()["chi_tiet"][0]["truong"] == truong


async def test_tao_vai_tro_khong_ton_tai_tra_400(dang_nhap_admin):
    phan_hoi = await tao_qua_api(dang_nhap_admin, vai_tro="SUPERUSER")
    assert phan_hoi.status_code == 400 and phan_hoi.json()["chi_tiet"] == [
        {"truong": "vai_tro", "loi": "Vai trò không tồn tại"}
    ]


async def test_tao_that_bai_khong_de_lai_nhat_ky_hay_tai_khoan(dang_nhap_admin, db):
    await tao_qua_api(dang_nhap_admin, vai_tro="SUPERUSER")
    assert await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "tao") == []


# --- Danh sách, chi tiết ---------------------------------------------------------------------------------------------


async def test_danh_sach_loc_tim_kiem_va_phan_trang(dang_nhap_admin, db):
    await tao_nhan_vien(db, "PHARMACIST", ho_ten="Nguyễn Thị Hòa", email="hoa@example.com")
    await tao_nhan_vien(db, "WAREHOUSE", ho_ten="Lê Văn Kho", email="kho.le@example.com")
    khoa = await tao_nhan_vien(
        db, "WAREHOUSE", ho_ten="Phạm Bị Khóa", email="khoa@example.com", trang_thai=TrangThaiTaiKhoan.bi_khoa
    )
    da_xoa = await tao_nhan_vien(db, "PHARMACIST", ho_ten="Đã Xóa Mềm", email="xoa@example.com")
    da_xoa.deleted_at = da_xoa.created_at
    await db.flush()

    def ten(phan_hoi):
        return {d["ho_ten"] for d in phan_hoi.json()["du_lieu"]}

    tat_ca = await dang_nhap_admin.get(GOC, params={"kich_thuoc": 100})
    assert tat_ca.status_code == 200 and "Đã Xóa Mềm" not in ten(tat_ca)
    assert {"Nguyễn Thị Hòa", "Lê Văn Kho", "Phạm Bị Khóa"} <= ten(tat_ca)
    assert ten(await dang_nhap_admin.get(GOC, params={"q": "thi hoa"})) == {"Nguyễn Thị Hòa"}  # không phân biệt dấu
    assert ten(await dang_nhap_admin.get(GOC, params={"q": "NGUYỄN"})) == {"Nguyễn Thị Hòa"}
    assert ten(await dang_nhap_admin.get(GOC, params={"q": "kho.le@"})) == {"Lê Văn Kho"}  # theo email
    ma_nv = khoa.ma_nhan_vien
    assert ten(await dang_nhap_admin.get(GOC, params={"q": ma_nv.lower()})) == {"Phạm Bị Khóa"}  # theo mã
    kho = await dang_nhap_admin.get(GOC, params={"vai_tro": "WAREHOUSE", "trang_thai": "bi_khoa"})
    assert ten(kho) == {"Phạm Bị Khóa"}
    assert (await dang_nhap_admin.get(GOC, params={"kich_thuoc": 2, "trang": 2})).json()["trang"] == 2


async def test_tim_kiem_ky_tu_dac_biet_khong_bi_hieu_la_ky_tu_thay_the(dang_nhap_admin, db):
    await tao_nhan_vien(db, ho_ten="Một Hai Ba", email="mot.hai.ba@example.com")
    for q in ("%", "_", "\\", "a%b"):
        phan_hoi = await dang_nhap_admin.get(GOC, params={"q": q})
        assert phan_hoi.status_code == 200 and phan_hoi.json()["tong"] == 0, q


async def test_danh_sach_va_chi_tiet_khong_lo_bi_mat(dang_nhap_admin, db):
    nv = await tao_nhan_vien(db, so_dien_thoai="0912345678")
    doc = await dang_nhap_admin.get(f"{GOC}/{nv.id}")
    assert doc.status_code == 200 and doc.json()["email"] == nv.email
    assert set(doc.json()) == {
        "id", "ma_nhan_vien", "ho_ten", "email", "so_dien_thoai", "vai_tro", "trang_thai",
        "phai_doi_mat_khau", "khoa_den", "created_at", "updated_at",
    }  # fmt: skip
    ds = await dang_nhap_admin.get(GOC)
    assert "hash" not in ds.text and "argon2" not in ds.text and "mat_khau_tam" not in ds.text


@pytest.mark.parametrize(
    ("nhan_vien_id", "ma_trang_thai", "ma_loi"),
    [
        (2_000_000_000, 404, "KHONG_TIM_THAY"),  # trong khoảng int32 nhưng không có
        (2_147_483_647, 404, "KHONG_TIM_THAY"),
        (2_147_483_648, 400, "DU_LIEU_KHONG_HOP_LE"),  # vượt int32: asyncpg sẽ ném lỗi nếu lọt tới DB
        (0, 400, "DU_LIEU_KHONG_HOP_LE"),
        (-1, 400, "DU_LIEU_KHONG_HOP_LE"),
        (99999999999999999999, 400, "DU_LIEU_KHONG_HOP_LE"),
    ],
)
async def test_chi_tiet_khong_co_hoac_id_vo_ly(dang_nhap_admin, nhan_vien_id, ma_trang_thai, ma_loi):
    assert la_loi(await dang_nhap_admin.get(f"{GOC}/{nhan_vien_id}"), ma_trang_thai, ma_loi)


async def test_nhan_vien_da_xoa_mem_la_404(dang_nhap_admin, db):
    nv = await tao_nhan_vien(db)
    nv.deleted_at = nv.created_at
    await db.flush()
    assert la_loi(await dang_nhap_admin.get(f"{GOC}/{nv.id}"), 404, "KHONG_TIM_THAY")


# --- Sửa, gán vai trò ----------------------------------------------------------------------------------------------


async def test_sua_thong_tin_ghi_nhat_ky_cu_moi_va_che_so_dien_thoai(dang_nhap_admin, db):
    nv = await tao_nhan_vien(db, ho_ten="Tên Cũ", email="cu@example.com")
    phan_hoi = await dang_nhap_admin.patch(
        f"{GOC}/{nv.id}", json={"ho_ten": "Tên Mới", "email": "Moi.Hon@example.com", "so_dien_thoai": "0912345678"}
    )
    assert phan_hoi.status_code == 200
    assert (phan_hoi.json()["ho_ten"], phan_hoi.json()["email"]) == ("Tên Mới", "moi.hon@example.com")
    (dong,) = await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "sua")
    assert dong.ban_ghi_id == str(nv.id) and dong.gia_tri_cu["ho_ten"] == "Tên Cũ"
    assert dong.gia_tri_moi["so_dien_thoai"] == "091***678" and "0912345678" not in json.dumps(dong.gia_tri_moi)


async def test_sua_khong_doi_gi_thi_khong_ghi_nhat_ky_va_khong_thu_hoi_phien(dang_nhap_admin, db):
    nv = await tao_nhan_vien(db)
    await phien.tao_phien(db, loai="noi_bo", chu_id=nv.id)
    phan_hoi = await dang_nhap_admin.patch(f"{GOC}/{nv.id}", json={"ho_ten": nv.ho_ten, "vai_tro": "PHARMACIST"})
    assert phan_hoi.status_code == 200
    assert await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "sua") == []
    assert await so_phien_con_hieu_luc(db, nv.id) == 1


async def test_doi_vai_tro_co_hieu_luc_ngay_va_thu_hoi_moi_phien(dang_nhap_admin, client, db):
    nv = await tao_nhan_vien(db, "PHARMACIST", email="duoc@example.com")
    refresh = cookie_refresh(await dang_nhap(client, "duoc@example.com"))
    assert (await dang_nhap_admin.patch(f"{GOC}/{nv.id}", json={"vai_tro": "WAREHOUSE"})).json()["vai_tro"][
        "ma"
    ] == "WAREHOUSE"
    assert await so_phien_con_hieu_luc(db, nv.id) == 0
    assert (await lam_moi(client, refresh)).status_code == 401
    # Đăng nhập lại thấy quyền của vai trò mới.
    quyen = (await dang_nhap(client, "duoc@example.com")).json()["nhan_vien"]["quyen"]
    assert "order.pick" in quyen and "order.confirm" not in quyen


@pytest.mark.parametrize(
    "than", [{"ho_ten": None}, {"email": None}, {"vai_tro": None}, {"trang_thai": "hoat_dong"}, {"mat_khau_hash": "x"}]
)
async def test_sua_truong_khong_hop_le_hoac_khong_duoc_sua_tra_400(dang_nhap_admin, db, than):
    nv = await tao_nhan_vien(db)
    assert (await dang_nhap_admin.patch(f"{GOC}/{nv.id}", json=than)).status_code == 400


async def test_sua_email_trung_tra_409(dang_nhap_admin, db):
    nv = await tao_nhan_vien(db)
    khac = await tao_nhan_vien(db, email="da.co@example.com")
    phan_hoi = await dang_nhap_admin.patch(f"{GOC}/{nv.id}", json={"email": khac.email})
    assert la_loi(phan_hoi, 409, "TRUNG_DU_LIEU")


async def test_sua_vai_tro_khong_ton_tai_tra_400(dang_nhap_admin, db):
    nv = await tao_nhan_vien(db)
    phan_hoi = await dang_nhap_admin.patch(f"{GOC}/{nv.id}", json={"vai_tro": "SUPERUSER"})
    assert phan_hoi.status_code == 400 and phan_hoi.json()["chi_tiet"][0]["truong"] == "vai_tro"


async def test_sua_nhan_vien_khong_ton_tai_404(dang_nhap_admin):
    assert la_loi(await dang_nhap_admin.patch(f"{GOC}/2000000000", json={"ho_ten": "X"}), 404, "KHONG_TIM_THAY")


# --- Khóa, mở khóa --------------------------------------------------------------------------------------------------


async def test_khoa_thu_hoi_moi_phien_va_chan_dang_nhap_lan_lam_moi(dang_nhap_admin, client, db):
    nv = await tao_nhan_vien(db, email="khoa.toi@example.com")
    dn = await dang_nhap(client, "khoa.toi@example.com")
    refresh, token = cookie_refresh(dn), dn.json()["access_token"]
    may_khac = cookie_refresh(await dang_nhap(client, "khoa.toi@example.com"))

    phan_hoi = await dang_nhap_admin.post(f"{GOC}/{nv.id}/khoa")
    assert phan_hoi.status_code == 200 and phan_hoi.json()["trang_thai"] == "bi_khoa"
    assert await so_phien_con_hieu_luc(db, nv.id) == 0
    assert (await lam_moi(client, refresh)).status_code == 401 and (await lam_moi(client, may_khac)).status_code == 401
    assert la_loi(await dang_nhap(client, "khoa.toi@example.com"), 403, "TAI_KHOAN_BI_KHOA")
    # Access token đã cấp bị chặn ngay vì trạng thái đọc từ DB mỗi request.
    toi = await client.get("/api/v1/noi-bo/toi", headers={"Authorization": f"Bearer {token}"})
    assert la_loi(toi, 403, "TAI_KHOAN_BI_KHOA")
    assert len(await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "khoa")) == 1


async def test_khoa_hai_lan_van_thanh_cong_va_chi_ghi_nhat_ky_mot_lan(dang_nhap_admin, db):
    nv = await tao_nhan_vien(db)
    for _ in range(2):
        assert (await dang_nhap_admin.post(f"{GOC}/{nv.id}/khoa")).status_code == 200
    assert len(await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "khoa")) == 1


async def test_mo_khoa_xoa_ca_khoa_admin_va_khoa_tam(dang_nhap_admin, client, db, thoi_gian):
    nv = await tao_nhan_vien(db, email="mo.khoa@example.com", trang_thai=TrangThaiTaiKhoan.bi_khoa)
    assert la_loi(await dang_nhap(client, "mo.khoa@example.com"), 403, "TAI_KHOAN_BI_KHOA")
    assert (await dang_nhap_admin.post(f"{GOC}/{nv.id}/mo-khoa")).json()["trang_thai"] == "hoat_dong"
    assert (await dang_nhap(client, "mo.khoa@example.com")).status_code == 200

    for _ in range(5):  # khóa tạm do đoán mật khẩu
        await dang_nhap(client, "mo.khoa@example.com", "Sai-mat-khau-1")
    assert la_loi(await dang_nhap(client, "mo.khoa@example.com"), 403, "TAI_KHOAN_BI_KHOA")
    phan_hoi = await dang_nhap_admin.post(f"{GOC}/{nv.id}/mo-khoa")
    assert phan_hoi.status_code == 200 and phan_hoi.json()["khoa_den"] is None
    assert (await dang_nhap(client, "mo.khoa@example.com")).status_code == 200
    assert len(await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "mo_khoa")) == 2


async def test_mo_khoa_tai_khoan_dang_binh_thuong_khong_ghi_nhat_ky(dang_nhap_admin, db):
    nv = await tao_nhan_vien(db)
    assert (await dang_nhap_admin.post(f"{GOC}/{nv.id}/mo-khoa")).status_code == 200
    assert await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "mo_khoa") == []


# --- Đặt lại mật khẩu -----------------------------------------------------------------------------------------------


async def test_dat_lai_mat_khau_sinh_mat_khau_tam_bat_doi_xoa_khoa_tam_va_thu_hoi_phien(dang_nhap_admin, client, db):
    nv = await tao_nhan_vien(db, email="quen@example.com", phai_doi_mat_khau=False, so_lan_dang_nhap_sai=3)
    refresh = cookie_refresh(await dang_nhap(client, "quen@example.com"))
    phan_hoi = await dang_nhap_admin.post(f"{GOC}/{nv.id}/dat-lai-mat-khau")
    assert phan_hoi.status_code == 200
    tam = phan_hoi.json()["mat_khau_tam"]
    assert mat_khau_du_manh(tam) and phan_hoi.json()["phai_doi_mat_khau"] is True
    await db.refresh(nv)
    assert nv.so_lan_dang_nhap_sai == 0 and nv.khoa_den is None and tam not in nv.mat_khau_hash

    assert (await lam_moi(client, refresh)).status_code == 401  # mọi phiên cũ bị thu hồi
    assert (await dang_nhap(client, "quen@example.com", MAT_KHAU_TEST)).status_code == 401  # mật khẩu cũ chết
    dn = await dang_nhap(client, "quen@example.com", tam)
    assert dn.status_code == 200 and dn.json()["nhan_vien"]["phai_doi_mat_khau"] is True
    (dong,) = await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "dat_lai_mat_khau")
    assert tam not in json.dumps([dong.gia_tri_cu, dong.gia_tri_moi])


async def test_dat_lai_mat_khau_khong_mo_khoa_cua_admin(dang_nhap_admin, client, db):
    nv = await tao_nhan_vien(db, email="bi.khoa@example.com", trang_thai=TrangThaiTaiKhoan.bi_khoa)
    tam = (await dang_nhap_admin.post(f"{GOC}/{nv.id}/dat-lai-mat-khau")).json()["mat_khau_tam"]
    assert la_loi(await dang_nhap(client, "bi.khoa@example.com", tam), 403, "TAI_KHOAN_BI_KHOA")


# --- Xóa mềm ---------------------------------------------------------------------------------------------------------


async def test_xoa_mem_khong_xoa_cung_thu_hoi_phien_va_an_khoi_danh_sach(dang_nhap_admin, client, db):
    nv = await tao_nhan_vien(db, email="se.xoa@example.com")
    refresh = cookie_refresh(await dang_nhap(client, "se.xoa@example.com"))
    phan_hoi = await dang_nhap_admin.delete(f"{GOC}/{nv.id}")
    assert phan_hoi.status_code == 204 and phan_hoi.content == b""
    await db.refresh(nv)
    assert nv.deleted_at is not None  # vẫn còn dòng
    assert await so_phien_con_hieu_luc(db, nv.id) == 0 and (await lam_moi(client, refresh)).status_code == 401
    assert (await dang_nhap(client, "se.xoa@example.com")).status_code == 401
    assert la_loi(await dang_nhap_admin.get(f"{GOC}/{nv.id}"), 404, "KHONG_TIM_THAY")
    assert nv.ma_nhan_vien not in (await dang_nhap_admin.get(GOC, params={"kich_thuoc": 100})).text
    assert la_loi(await dang_nhap_admin.delete(f"{GOC}/{nv.id}"), 404, "KHONG_TIM_THAY")
    assert len(await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "xoa")) == 1


# --- Tự thao tác trên chính mình ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("phuong_thuc", "hau_to", "than"),
    [
        ("POST", "/khoa", None),
        ("POST", "/dat-lai-mat-khau", None),
        ("DELETE", "", None),
        ("PATCH", "", {"vai_tro": "WAREHOUSE"}),
    ],
)
async def test_admin_khong_tu_khoa_xoa_doi_vai_tro_hay_dat_lai_mat_khau_cua_chinh_minh(
    dang_nhap_admin, db, phuong_thuc, hau_to, than
):
    chinh_minh = dang_nhap_admin.tai_khoan
    # Có Admin khác nên không phải vì PHAI_CON_ADMIN mà vì là chính mình.
    await tao_nhan_vien(db, "ADMIN")
    phan_hoi = await dang_nhap_admin.request(
        phuong_thuc, f"{GOC}/{chinh_minh.id}{hau_to}", **({"json": than} if than else {})
    )
    assert la_loi(phan_hoi, 403, "TU_THAY_DOI_KHONG_DUOC")
    await db.refresh(chinh_minh, ["trang_thai", "deleted_at", "phai_doi_mat_khau", "vai_tro_id"])
    assert chinh_minh.trang_thai == TrangThaiTaiKhoan.hoat_dong and chinh_minh.deleted_at is None
    assert (await dang_nhap_admin.get(GOC)).status_code == 200  # vẫn là Admin, vẫn dùng được


async def test_admin_van_sua_duoc_ho_ten_va_so_dien_thoai_cua_chinh_minh_va_gui_lai_dung_vai_tro(dang_nhap_admin):
    chinh_minh = dang_nhap_admin.tai_khoan
    phan_hoi = await dang_nhap_admin.patch(
        f"{GOC}/{chinh_minh.id}", json={"ho_ten": "Admin Đổi Tên", "vai_tro": "ADMIN"}
    )
    assert phan_hoi.status_code == 200 and phan_hoi.json()["ho_ten"] == "Admin Đổi Tên"


# --- Luôn còn ít nhất một Admin hoạt động ----------------------------------------------------------------------------


async def test_admin_cuoi_cung_khong_bi_khoa_xoa_hay_ha_vai_tro_boi_nguoi_khac(db, app, clients_theo_vai_tro):
    """Người khác (có `staff.manage`, không phải Admin này) cũng không thể làm hệ thống mất Admin hoạt động cuối cùng."""
    from app.models.he_thong import Quyen, VaiTro, VaiTroQuyen

    # Cấp `staff.manage` cho dược sĩ để có người không phải Admin quản lý nhân viên (AD18 cho phép).
    quyen_id = (await db.execute(select(Quyen.id).where(Quyen.ma == "staff.manage"))).scalar_one()
    vai_tro_id = (await db.execute(select(VaiTro.id).where(VaiTro.ma == "PHARMACIST"))).scalar_one()
    db.add(VaiTroQuyen(vai_tro_id=vai_tro_id, quyen_id=quyen_id))
    await db.flush()
    from app.core.phan_quyen import xoa_cache_quyen

    xoa_cache_quyen()
    duoc_si = clients_theo_vai_tro["PHARMACIST"]
    admin_duy_nhat = (
        (
            await db.execute(
                select(NhanVien)
                .join(VaiTro, VaiTro.id == NhanVien.vai_tro_id)
                .where(
                    VaiTro.ma == "ADMIN",
                    NhanVien.trang_thai == TrangThaiTaiKhoan.hoat_dong,
                    NhanVien.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(admin_duy_nhat) == 1  # chỉ có Admin do fixture tạo (DB test không seed Admin)
    id_admin = admin_duy_nhat[0].id

    for phuong_thuc, hau_to, than in (
        ("POST", "/khoa", None),
        ("DELETE", "", None),
        ("PATCH", "", {"vai_tro": "WAREHOUSE"}),
    ):
        phan_hoi = await duoc_si.request(phuong_thuc, f"{GOC}/{id_admin}{hau_to}", **({"json": than} if than else {}))
        assert la_loi(phan_hoi, 409, "PHAI_CON_ADMIN"), (phuong_thuc, hau_to)
    await db.refresh(admin_duy_nhat[0])
    assert admin_duy_nhat[0].trang_thai == TrangThaiTaiKhoan.hoat_dong and admin_duy_nhat[0].deleted_at is None


async def test_co_admin_khac_hoat_dong_thi_khoa_duoc_va_admin_bi_khoa_khong_tinh_la_hoat_dong(dang_nhap_admin, db):
    b = await tao_nhan_vien(db, "ADMIN")
    c = await tao_nhan_vien(db, "ADMIN")
    assert (await dang_nhap_admin.post(f"{GOC}/{b.id}/khoa")).status_code == 200  # còn actor và c
    assert (await dang_nhap_admin.post(f"{GOC}/{c.id}/khoa")).status_code == 200  # còn actor
    # b, c bị khóa nên không tính; actor là Admin hoạt động duy nhất, người khác không khóa/xóa được actor qua api của actor.
    d = await tao_nhan_vien(db, "ADMIN")
    assert (await dang_nhap_admin.post(f"{GOC}/{d.id}/khoa")).status_code == 200


async def test_admin_khoa_nhau_dong_thoi_chi_mot_ben_thanh_cong(db_that):
    """Hai Admin cùng khóa nhau: nếu không khóa dòng thì cả hai cùng thấy "còn Admin kia" và cùng thành công, hệ thống
    không còn Admin hoạt động nào. Khóa dòng mọi Admin theo id tăng dần làm hai bên tuần tự."""
    async with db_that() as s, s.begin():
        a_id = (await tao_nhan_vien(s, "ADMIN")).id
        b_id = (await tao_nhan_vien(s, "ADMIN")).id

    da_vao = asyncio.Event()

    async def khoa_nhau(nguoi_khoa_id: int, nguoi_bi_khoa_id: int, cho_nhau: bool):
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, nguoi_khoa_id)
            if cho_nhau:
                await da_vao.wait()
            else:
                da_vao.set()
            try:
                await quan_tri.khoa(s, actor, nguoi_bi_khoa_id, ip="127.0.0.1")
                await asyncio.sleep(0.3)  # giữ giao dịch mở để bên kia phải chờ
                return "ok"
            except Exception as loi:  # LoiNghiepVu: giao dịch này bị rollback khi thoát khỏi `begin()`
                return getattr(loi, "ma_loi", repr(loi))

    ket_qua = await asyncio.wait_for(
        asyncio.gather(khoa_nhau(a_id, b_id, False), khoa_nhau(b_id, a_id, True)), timeout=20
    )
    assert sorted(ket_qua) == ["PHAI_CON_ADMIN", "ok"], ket_qua
    async with db_that() as s:
        con = (
            (
                await s.execute(
                    select(NhanVien).where(
                        NhanVien.id.in_([a_id, b_id]), NhanVien.trang_thai == TrangThaiTaiKhoan.hoat_dong
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(con) == 1  # đúng một Admin còn hoạt động


async def test_hai_admin_tao_cung_email_cung_luc_chi_mot_thanh_cong(db_that):
    async with db_that() as s, s.begin():
        admin_id = (await tao_nhan_vien(s, "ADMIN")).id
    from app.modules.nhan_vien.schemas_quan_tri import NhanVienTao

    async def tao():
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, admin_id)
            try:
                await quan_tri.tao(
                    s, actor, NhanVienTao(ho_ten="X", email="trung@example.com", vai_tro="WAREHOUSE"), ip="127.0.0.1"
                )
                await asyncio.sleep(0.2)
                return "ok"
            except Exception as loi:
                return getattr(loi, "ma_loi", repr(loi))

    ket_qua = await asyncio.wait_for(asyncio.gather(tao(), tao()), timeout=20)
    assert sorted(ket_qua) == ["TRUNG_DU_LIEU", "ok"], ket_qua


# --- Quyền ----------------------------------------------------------------------------------------------------------


async def test_chi_nguoi_co_staff_manage_moi_dung_duoc(clients_theo_vai_tro, client):
    nv = None
    for vai_tro in ("PHARMACIST", "WAREHOUSE"):
        c = clients_theo_vai_tro[vai_tro]
        assert la_loi(await c.get(GOC), 403, "KHONG_CO_QUYEN")
        assert la_loi(await tao_qua_api(c), 403, "KHONG_CO_QUYEN")
    assert (await clients_theo_vai_tro["ADMIN"].get(GOC)).status_code == 200
    assert (await client.get(GOC)).status_code == 401
    assert nv is None


async def test_khach_khong_goi_duoc(client, db):
    from app.core.bao_mat import tao_access_token

    khach = await tao_khach(db)
    phan_hoi = await client.get(GOC, headers={"Authorization": f"Bearer {tao_access_token(khach.id, 'khach')}"})
    assert la_loi(phan_hoi, 401, "CHUA_DANG_NHAP")


async def test_phien_dang_nhap_cua_nhan_vien_khac_khong_bi_dung_toi(dang_nhap_admin, db):
    nv = await tao_nhan_vien(db)
    khac = await tao_nhan_vien(db)
    await phien.tao_phien(db, loai="noi_bo", chu_id=khac.id)
    await dang_nhap_admin.post(f"{GOC}/{nv.id}/khoa")
    dong = (await db.execute(select(PhienDangNhap).where(PhienDangNhap.nhan_vien_id == khac.id))).scalars().all()
    assert len(dong) == 1 and dong[0].thu_hoi_luc is None


# --- Sắp xếp `sap_xep` (spec 06 mục 5) -------------------------------------------------------------------------------


async def _ten_theo(dang_nhap_admin, sap_xep: str | None) -> list[str]:
    tham_so = {"q": "Sapxep", "kich_thuoc": 100}
    if sap_xep is not None:
        tham_so["sap_xep"] = sap_xep
    phan_hoi = await dang_nhap_admin.get(GOC, params=tham_so)
    assert phan_hoi.status_code == 200, phan_hoi.text
    return [d["ho_ten"] for d in phan_hoi.json()["du_lieu"]]


async def test_sap_xep_theo_ten_khong_phan_biet_dau_va_hoa_thuong(dang_nhap_admin, db):
    for ten in ("Sapxep Đức", "Sapxep an", "Sapxep Ân", "Sapxep Bình"):
        await tao_nhan_vien(db, ho_ten=ten)
    tang = await _ten_theo(dang_nhap_admin, "ho_ten")
    # Không dấu, không phân biệt hoa thường: "an" và "Ân" đứng cùng nhau trước "Bình", rồi "Đức" (d).
    assert tang[:2] in (["Sapxep an", "Sapxep Ân"], ["Sapxep Ân", "Sapxep an"])
    assert tang[2:] == ["Sapxep Bình", "Sapxep Đức"]
    assert await _ten_theo(dang_nhap_admin, "-ho_ten") == list(reversed(tang))


async def test_sap_xep_mac_dinh_la_moi_tao_truoc_va_theo_ma(dang_nhap_admin, db):
    a = await tao_nhan_vien(db, ho_ten="Sapxep Một")
    b = await tao_nhan_vien(db, ho_ten="Sapxep Hai")
    mac_dinh = await _ten_theo(dang_nhap_admin, None)
    assert mac_dinh == await _ten_theo(dang_nhap_admin, "-created_at")
    assert mac_dinh.index(b.ho_ten) < mac_dinh.index(a.ho_ten)
    assert await _ten_theo(dang_nhap_admin, "ma_nhan_vien") == [a.ho_ten, b.ho_ten]


@pytest.mark.parametrize(
    "sap_xep", ["mat_khau_hash", "-mat_khau_hash", "phai_doi_mat_khau", "ho_ten;select", "-", "ho_ten,-id"]
)
async def test_sap_xep_truong_ngoai_danh_sach_la_400(dang_nhap_admin, sap_xep):
    phan_hoi = await dang_nhap_admin.get(GOC, params={"sap_xep": sap_xep})
    assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE")
    assert "mat_khau" not in phan_hoi.text.replace("mat_khau_hash", "")  # không lộ gì về cột bí mật

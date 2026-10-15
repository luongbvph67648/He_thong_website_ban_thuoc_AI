"""NV02: hồ sơ cá nhân (GET/PATCH /api/v1/noi-bo/toi)."""

import json

import pytest
import yaml

from app.core.bao_mat import tao_access_token
from app.core.danh_muc_quyen import QUYEN_YAML
from tests.factories import tao_khach, tao_nhan_vien
from tests.nhan_vien.dung_chung import URL_TOI, bearer, nhat_ky


def quyen_theo_yaml(vai_tro: str) -> dict[str, str]:
    du_lieu = yaml.safe_load(QUYEN_YAML.read_text(encoding="utf-8"))
    return {q["ma"]: q["vai_tro"][vai_tro] for q in du_lieu["quyen"] if vai_tro in q["vai_tro"]}


async def test_ho_so_cua_toi_duoc_si(dang_nhap_duoc_si):
    phan_hoi = await dang_nhap_duoc_si.get(URL_TOI)
    nv = dang_nhap_duoc_si.tai_khoan
    assert phan_hoi.status_code == 200
    than = phan_hoi.json()
    assert set(than) == {
        "id",
        "ma_nhan_vien",
        "ho_ten",
        "email",
        "so_dien_thoai",
        "vai_tro",
        "phai_doi_mat_khau",
        "quyen",
    }
    assert (than["id"], than["email"], than["ma_nhan_vien"]) == (nv.id, nv.email, nv.ma_nhan_vien)
    assert than["vai_tro"] == {"ma": "PHARMACIST", "ten": "Dược sĩ bán hàng"}
    assert "mat_khau" not in than and "mat_khau_hash" not in phan_hoi.text and "argon2" not in phan_hoi.text


async def test_quyen_tra_ve_khop_tung_dong_voi_quyen_yaml_cua_ca_ba_vai_tro(
    dang_nhap_duoc_si, dang_nhap_kho, dang_nhap_admin
):
    for client, vai_tro in (
        (dang_nhap_duoc_si, "PHARMACIST"),
        (dang_nhap_kho, "WAREHOUSE"),
        (dang_nhap_admin, "ADMIN"),
    ):
        than = (await client.get(URL_TOI)).json()
        assert than["vai_tro"]["ma"] == vai_tro
        assert than["quyen"] == quyen_theo_yaml(vai_tro), vai_tro


async def test_quyen_chi_xem_va_day_du_duoc_phan_biet(dang_nhap_kho):
    quyen = (await dang_nhap_kho.get(URL_TOI)).json()["quyen"]
    assert quyen["order.pick"] == "day_du" and quyen["order.view"] == "chi_xem"
    assert "order.confirm" not in quyen and "staff.manage" not in quyen


async def test_phai_dang_nhap_noi_bo(client, db):
    khach = await tao_khach(db)
    assert (await client.get(URL_TOI)).status_code == 401
    assert (await client.get(URL_TOI, headers=bearer(tao_access_token(khach.id, "khach")))).status_code == 401


async def test_cap_nhat_ho_ten_va_so_dien_thoai_duoc_chuan_hoa(dang_nhap_kho, db):
    phan_hoi = await dang_nhap_kho.patch(
        URL_TOI, json={"ho_ten": "  Nguyễn Văn Kho  ", "so_dien_thoai": "+84 912 345 678"}
    )
    assert phan_hoi.status_code == 200
    assert phan_hoi.json()["ho_ten"] == "Nguyễn Văn Kho" and phan_hoi.json()["so_dien_thoai"] == "0912345678"
    await db.refresh(dang_nhap_kho.tai_khoan)
    nv = dang_nhap_kho.tai_khoan
    assert (nv.ho_ten, nv.so_dien_thoai) == ("Nguyễn Văn Kho", "0912345678") and nv.updated_at is not None
    assert (await dang_nhap_kho.get(URL_TOI)).json()["ho_ten"] == "Nguyễn Văn Kho"


async def test_chi_doi_truong_duoc_gui(dang_nhap_kho, db):
    nv = dang_nhap_kho.tai_khoan
    nv.so_dien_thoai = "0987654321"
    await db.flush()
    ten_cu = nv.ho_ten
    phan_hoi = await dang_nhap_kho.patch(URL_TOI, json={"ho_ten": "Tên Mới"})
    assert phan_hoi.json()["so_dien_thoai"] == "0987654321"  # không gửi thì giữ nguyên
    phan_hoi = await dang_nhap_kho.patch(URL_TOI, json={"so_dien_thoai": "0911111111"})
    assert phan_hoi.json()["ho_ten"] == "Tên Mới" and ten_cu != "Tên Mới"


@pytest.mark.parametrize("gia_tri", [None, "", "   "])
async def test_xoa_so_dien_thoai(dang_nhap_kho, db, gia_tri):
    dang_nhap_kho.tai_khoan.so_dien_thoai = "0987654321"
    await db.flush()
    phan_hoi = await dang_nhap_kho.patch(URL_TOI, json={"so_dien_thoai": gia_tri})
    assert phan_hoi.status_code == 200 and phan_hoi.json()["so_dien_thoai"] is None


@pytest.mark.parametrize(
    ("than", "truong"),
    [
        ({"ho_ten": ""}, "ho_ten"),
        ({"ho_ten": "   "}, "ho_ten"),
        ({"ho_ten": None}, "ho_ten"),
        ({"ho_ten": "A" * 151}, "ho_ten"),
        ({"so_dien_thoai": "0212345678"}, "so_dien_thoai"),
        ({"so_dien_thoai": "abc"}, "so_dien_thoai"),
        ({"email": "moi@example.com"}, "email"),
        ({"vai_tro_id": 3}, "vai_tro_id"),
        ({"phai_doi_mat_khau": False}, "phai_doi_mat_khau"),
        ({"trang_thai": "hoat_dong"}, "trang_thai"),
    ],
)
async def test_du_lieu_sai_hoac_truong_khong_duoc_sua_bi_tu_choi(dang_nhap_kho, than, truong):
    """Email do Admin quản lý; vai trò, trạng thái, cờ đổi mật khẩu không bao giờ tự sửa được qua hồ sơ."""
    phan_hoi = await dang_nhap_kho.patch(URL_TOI, json=than)
    assert phan_hoi.status_code == 400 and phan_hoi.json()["chi_tiet"][0]["truong"] == truong


async def test_khong_tu_nang_vai_tro_qua_ho_so(dang_nhap_kho, db):
    await dang_nhap_kho.patch(URL_TOI, json={"vai_tro_id": 1})
    await db.refresh(dang_nhap_kho.tai_khoan)
    assert (await dang_nhap_kho.get(URL_TOI)).json()["vai_tro"]["ma"] == "WAREHOUSE"


async def test_nhat_ky_ghi_gia_tri_cu_moi_va_che_so_dien_thoai(dang_nhap_kho, db):
    nv = dang_nhap_kho.tai_khoan
    ten_cu = nv.ho_ten
    await dang_nhap_kho.patch(URL_TOI, json={"ho_ten": "Tên Mới", "so_dien_thoai": "0912345678"})
    (dong,) = await nhat_ky(db, nv.id, "sua")
    assert (dong.bang, dong.ban_ghi_id) == ("nhan_vien", str(nv.id))
    assert dong.gia_tri_cu == {"ho_ten": ten_cu, "so_dien_thoai": None}
    assert dong.gia_tri_moi == {"ho_ten": "Tên Mới", "so_dien_thoai": "091***678"}
    assert "0912345678" not in json.dumps([dong.gia_tri_cu, dong.gia_tri_moi])


async def test_khong_thay_doi_gi_thi_khong_ghi_nhat_ky(dang_nhap_kho, db):
    nv = dang_nhap_kho.tai_khoan
    await dang_nhap_kho.patch(URL_TOI, json={"ho_ten": nv.ho_ten})
    await dang_nhap_kho.patch(URL_TOI, json={})
    assert await nhat_ky(db, nv.id, "sua") == []


async def test_chi_sua_duoc_ho_so_cua_chinh_minh(dang_nhap_kho, db):
    nguoi_khac = await tao_nhan_vien(db, "ADMIN")
    ten_cu = nguoi_khac.ho_ten
    await dang_nhap_kho.patch(URL_TOI, json={"ho_ten": "Kẻ lạ"})
    await db.refresh(nguoi_khac)
    assert nguoi_khac.ho_ten == ten_cu


async def test_dang_bi_bat_doi_mat_khau_xem_duoc_nhung_khong_sua_duoc(client, db):
    nv = await tao_nhan_vien(db, phai_doi_mat_khau=True)
    tieu_de = bearer(tao_access_token(nv.id, "noi_bo"))
    xem = await client.get(URL_TOI, headers=tieu_de)
    assert xem.status_code == 200 and xem.json()["phai_doi_mat_khau"] is True
    sua = await client.patch(URL_TOI, json={"ho_ten": "Tên Mới"}, headers=tieu_de)
    assert sua.status_code == 403 and sua.json()["ma_loi"] == "PHAI_DOI_MAT_KHAU"

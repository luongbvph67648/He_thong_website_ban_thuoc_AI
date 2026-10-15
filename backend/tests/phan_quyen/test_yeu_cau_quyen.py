"""core/phan_quyen.py: `nhan_vien_hien_tai` và `yeu_cau_quyen` (spec 03 mục 8)."""

from datetime import timedelta
from typing import Annotated

import pytest
from fastapi import Depends
from sqlalchemy import select, update

from app.core import phan_quyen
from app.core.bao_mat import tao_access_token
from app.core.danh_muc_quyen import QUYEN_YAML, ma_quyen_hop_le
from app.core.phan_quyen import nhan_vien_hien_tai, xoa_cache_quyen, yeu_cau_quyen
from app.core.thoi_gian import bay_gio_utc
from app.models.enums import TrangThaiTaiKhoan
from app.models.he_thong import NhanVien, Quyen, VaiTro, VaiTroQuyen
from tests.factories import tao_khach, tao_nhan_vien

GOC = "/api/v1/noi-bo/_thu"


@pytest.fixture
def app_thu(app):
    """Ứng dụng thật kèm vài route thử đủ kiểu khai báo quyền."""

    @app.get(f"{GOC}/xem-don")
    async def xem_don(nv: Annotated[NhanVien, Depends(yeu_cau_quyen("order.view", "xem"))]):
        return {"id": nv.id, "vai_tro": nv.vai_tro.ma}

    @app.post(f"{GOC}/xac-nhan")
    async def xac_nhan(nv: Annotated[NhanVien, Depends(yeu_cau_quyen("order.confirm"))]):
        return {"id": nv.id}

    @app.post(f"{GOC}/ghi-nhan-khai-bao-nham-xem")
    async def ghi_nham(nv: Annotated[NhanVien, Depends(yeu_cau_quyen("order.view", "xem"))]):
        return {"id": nv.id}

    @app.get(f"{GOC}/cho-phep-chua-doi-mk")
    async def cho_phep(
        nv: Annotated[NhanVien, Depends(yeu_cau_quyen("profile.self", "xem", ke_ca_chua_doi_mat_khau=True))],
    ):
        return {"id": nv.id}

    @app.get(f"{GOC}/chi-can-dang-nhap")
    async def chi_can_dang_nhap(nv: Annotated[NhanVien, Depends(nhan_vien_hien_tai)]):
        return {"id": nv.id}

    return app


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def la_loi(phan_hoi, status, ma_loi):
    return phan_hoi.status_code == status and phan_hoi.json()["ma_loi"] == ma_loi


# --- Xác thực -------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("tieu_de", [{}, {"Authorization": "Bearer"}, {"Authorization": "Bearer abc.def.ghi"}])
async def test_khong_co_token_hoac_token_rac_tra_401(app_thu, client, tieu_de):
    assert la_loi(await client.get(f"{GOC}/xem-don", headers=tieu_de), 401, "CHUA_DANG_NHAP")


async def test_token_khach_khong_dung_duoc_o_route_noi_bo(app_thu, client, db):
    khach = await tao_khach(db)
    phan_hoi = await client.get(f"{GOC}/xem-don", headers=bearer(tao_access_token(khach.id, "khach")))
    assert la_loi(phan_hoi, 401, "CHUA_DANG_NHAP")


async def test_token_het_han_tra_token_het_han(app_thu, client, db):
    nv = await tao_nhan_vien(db, phai_doi_mat_khau=False)
    token = tao_access_token(nv.id, "noi_bo", het_han_phut=-1)
    assert la_loi(await client.get(f"{GOC}/xem-don", headers=bearer(token)), 401, "TOKEN_HET_HAN")


async def test_token_cua_tai_khoan_khong_ton_tai_hoac_da_xoa_tra_401(app_thu, client, db):
    da_xoa = await tao_nhan_vien(db, phai_doi_mat_khau=False, deleted_at=bay_gio_utc())
    for nhan_vien_id in (da_xoa.id, 2_000_000_000):
        phan_hoi = await client.get(f"{GOC}/xem-don", headers=bearer(tao_access_token(nhan_vien_id, "noi_bo")))
        assert la_loi(phan_hoi, 401, "CHUA_DANG_NHAP")


# --- Trạng thái tài khoản kiểm tra ở mỗi request ----------------------------------------------------------------------


async def test_khoa_tai_khoan_co_hieu_luc_ngay_du_token_con_han(app_thu, dang_nhap_duoc_si, db):
    assert (await dang_nhap_duoc_si.get(f"{GOC}/xem-don")).status_code == 200
    dang_nhap_duoc_si.tai_khoan.trang_thai = TrangThaiTaiKhoan.bi_khoa
    await db.flush()
    assert la_loi(await dang_nhap_duoc_si.get(f"{GOC}/xem-don"), 403, "TAI_KHOAN_BI_KHOA")


async def test_khoa_tam_chua_het_han_bi_chan_het_han_thi_qua(app_thu, dang_nhap_kho, db):
    nv = dang_nhap_kho.tai_khoan
    nv.khoa_den = bay_gio_utc() + timedelta(minutes=10)
    await db.flush()
    assert la_loi(await dang_nhap_kho.get(f"{GOC}/xem-don"), 403, "TAI_KHOAN_BI_KHOA")
    nv.khoa_den = bay_gio_utc() - timedelta(seconds=1)
    await db.flush()
    assert (await dang_nhap_kho.get(f"{GOC}/xem-don")).status_code == 200


async def test_xoa_mem_nhan_vien_co_hieu_luc_ngay(app_thu, dang_nhap_admin, db):
    assert (await dang_nhap_admin.get(f"{GOC}/xem-don")).status_code == 200
    dang_nhap_admin.tai_khoan.deleted_at = bay_gio_utc()
    await db.flush()
    assert la_loi(await dang_nhap_admin.get(f"{GOC}/xem-don"), 401, "CHUA_DANG_NHAP")


async def test_vai_tro_doi_co_hieu_luc_ngay_vi_vai_tro_doc_tu_db(app_thu, dang_nhap_duoc_si, db):
    """Vai trò không nằm trong token: đổi vai trò của nhân viên thì request kế tiếp đã theo vai trò mới."""
    assert (await dang_nhap_duoc_si.post(f"{GOC}/xac-nhan")).status_code == 200
    kho_id = (await db.execute(select(VaiTro.id).where(VaiTro.ma == "WAREHOUSE"))).scalar_one()
    dang_nhap_duoc_si.tai_khoan.vai_tro_id = kho_id
    await db.flush()
    assert la_loi(await dang_nhap_duoc_si.post(f"{GOC}/xac-nhan"), 403, "KHONG_CO_QUYEN")


# --- Bắt đổi mật khẩu -----------------------------------------------------------------------------------------------


async def test_phai_doi_mat_khau_chan_moi_route_tru_route_duoc_mien(app_thu, client, db):
    nv = await tao_nhan_vien(db, "PHARMACIST", phai_doi_mat_khau=True)
    tieu_de = bearer(tao_access_token(nv.id, "noi_bo"))
    for phuong_thuc, duong_dan in (("GET", "xem-don"), ("POST", "xac-nhan"), ("GET", "chi-can-dang-nhap")):
        phan_hoi = await client.request(phuong_thuc, f"{GOC}/{duong_dan}", headers=tieu_de)
        assert la_loi(phan_hoi, 403, "PHAI_DOI_MAT_KHAU"), duong_dan
    assert (await client.get(f"{GOC}/cho-phep-chua-doi-mk", headers=tieu_de)).status_code == 200


async def test_phai_doi_mat_khau_van_phai_con_hoat_dong(app_thu, client, db):
    nv = await tao_nhan_vien(db, phai_doi_mat_khau=True, trang_thai=TrangThaiTaiKhoan.bi_khoa)
    phan_hoi = await client.get(f"{GOC}/cho-phep-chua-doi-mk", headers=bearer(tao_access_token(nv.id, "noi_bo")))
    assert la_loi(phan_hoi, 403, "TAI_KHOAN_BI_KHOA")


# --- Ma trận quyền ---------------------------------------------------------------------------------------------------


async def test_yeu_cau_quyen_theo_vai_tro(app_thu, dang_nhap_duoc_si, dang_nhap_kho, dang_nhap_admin):
    """order.view: dược sĩ đầy đủ, kho và Admin chỉ xem. order.confirm: chỉ dược sĩ."""
    ket_qua = {
        ten: (
            (await c.get(f"{GOC}/xem-don")).status_code,
            (await c.post(f"{GOC}/xac-nhan")).status_code,
        )
        for ten, c in (("duoc_si", dang_nhap_duoc_si), ("kho", dang_nhap_kho), ("admin", dang_nhap_admin))
    }
    assert ket_qua == {"duoc_si": (200, 200), "kho": (200, 403), "admin": (200, 403)}


async def test_khong_co_quyen_tra_403_dung_ma(app_thu, dang_nhap_kho):
    phan_hoi = await dang_nhap_kho.post(f"{GOC}/xac-nhan")
    assert la_loi(phan_hoi, 403, "KHONG_CO_QUYEN")


async def test_thao_tac_ghi_luon_can_muc_day_du_ke_ca_khi_khai_bao_nham_muc_xem(
    app_thu, dang_nhap_duoc_si, dang_nhap_kho, dang_nhap_admin
):
    """`order.view` mức xem cho phép kho/Admin GET, nhưng POST (ghi) phải bị chặn dù route khai báo `muc="xem"`."""
    assert (await dang_nhap_duoc_si.post(f"{GOC}/ghi-nhan-khai-bao-nham-xem")).status_code == 200
    assert la_loi(await dang_nhap_kho.post(f"{GOC}/ghi-nhan-khai-bao-nham-xem"), 403, "KHONG_CO_QUYEN")
    assert la_loi(await dang_nhap_admin.post(f"{GOC}/ghi-nhan-khai-bao-nham-xem"), 403, "KHONG_CO_QUYEN")


async def test_dependency_tra_ve_nhan_vien_voi_vai_tro_da_nap(app_thu, dang_nhap_kho):
    phan_hoi = await dang_nhap_kho.get(f"{GOC}/xem-don")
    assert phan_hoi.json() == {"id": dang_nhap_kho.tai_khoan.id, "vai_tro": "WAREHOUSE"}


async def test_gioi_han_la_duoc_coi_la_chi_xem(app_thu, dang_nhap_duoc_si, db):
    """`gioi_han` khác NULL (kể cả giá trị lạ) không bao giờ nâng thành đầy đủ: đặc quyền tối thiểu."""
    await db.execute(
        update(VaiTroQuyen)
        .where(VaiTroQuyen.quyen_id == select(Quyen.id).where(Quyen.ma == "order.confirm").scalar_subquery())
        .values(gioi_han="gia-tri-la")
    )
    assert la_loi(await dang_nhap_duoc_si.post(f"{GOC}/xac-nhan"), 403, "KHONG_CO_QUYEN")


# --- Cache quyền 60 giây ---------------------------------------------------------------------------------------------


async def _bo_quyen_xac_nhan_cua_duoc_si(db):
    await db.execute(
        select(VaiTroQuyen).limit(0)  # chỉ để rõ ý; xóa thật bằng DELETE bên dưới
    )
    quyen_id = (await db.execute(select(Quyen.id).where(Quyen.ma == "order.confirm"))).scalar_one()
    vai_tro_id = (await db.execute(select(VaiTro.id).where(VaiTro.ma == "PHARMACIST"))).scalar_one()
    await db.execute(
        VaiTroQuyen.__table__.delete().where(VaiTroQuyen.vai_tro_id == vai_tro_id, VaiTroQuyen.quyen_id == quyen_id)
    )


async def test_quyen_duoc_cache_toi_da_60_giay(app_thu, dang_nhap_duoc_si, db, monkeypatch):
    dong_ho = [1000.0]
    monkeypatch.setattr(phan_quyen.time, "monotonic", lambda: dong_ho[0])
    assert (await dang_nhap_duoc_si.post(f"{GOC}/xac-nhan")).status_code == 200  # nạp cache

    await _bo_quyen_xac_nhan_cua_duoc_si(db)
    dong_ho[0] += 59
    assert (await dang_nhap_duoc_si.post(f"{GOC}/xac-nhan")).status_code == 200  # còn trong 60 giây: dùng bản cache
    dong_ho[0] += 2  # 61 giây từ lúc nạp
    assert la_loi(await dang_nhap_duoc_si.post(f"{GOC}/xac-nhan"), 403, "KHONG_CO_QUYEN")


async def test_xoa_cache_quyen_co_hieu_luc_ngay(app_thu, dang_nhap_duoc_si, db):
    assert (await dang_nhap_duoc_si.post(f"{GOC}/xac-nhan")).status_code == 200
    await _bo_quyen_xac_nhan_cua_duoc_si(db)
    assert (await dang_nhap_duoc_si.post(f"{GOC}/xac-nhan")).status_code == 200  # cache
    xoa_cache_quyen()
    assert la_loi(await dang_nhap_duoc_si.post(f"{GOC}/xac-nhan"), 403, "KHONG_CO_QUYEN")


async def test_cache_khong_che_trang_thai_tai_khoan(app_thu, dang_nhap_duoc_si, db):
    """Quyền cache nhưng trạng thái tài khoản vẫn đọc mỗi request."""
    assert (await dang_nhap_duoc_si.post(f"{GOC}/xac-nhan")).status_code == 200
    dang_nhap_duoc_si.tai_khoan.trang_thai = TrangThaiTaiKhoan.bi_khoa
    await db.flush()
    assert la_loi(await dang_nhap_duoc_si.post(f"{GOC}/xac-nhan"), 403, "TAI_KHOAN_BI_KHOA")


# --- Khai báo ---------------------------------------------------------------------------------------------------------


def test_ma_quyen_khong_co_trong_yaml_loi_ngay_khi_dung_route():
    with pytest.raises(ValueError, match="quyen.yaml"):
        yeu_cau_quyen("order.khong_ton_tai")


def test_muc_khong_hop_le_loi_ngay_khi_dung_route():
    with pytest.raises(ValueError, match="muc"):
        yeu_cau_quyen("order.view", "ghi")  # type: ignore[arg-type]


def test_dependency_ghi_lai_khai_bao_de_test_registry_doi_chieu():
    dep = yeu_cau_quyen("stock.import", "xem")
    assert (dep.ma_quyen, dep.muc, dep.ke_ca_chua_doi_mat_khau) == ("stock.import", "xem", False)  # type: ignore[attr-defined]


def test_quyen_yaml_co_mat_va_du_51_ma_quyen():
    """Nếu file vắng thì việc kiểm tra mã lúc khai báo bị bỏ qua âm thầm; test này bảo đảm trong repo nó luôn bật."""
    assert QUYEN_YAML.is_file()
    ma = ma_quyen_hop_le()
    assert ma is not None and len(ma) == 51 and "profile.self" in ma

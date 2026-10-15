"""NV02: thông báo của nhân viên (/api/v1/noi-bo/thong-bao)."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.thoi_gian import bay_gio_utc
from app.models.khach_hang import ThongBao
from app.modules.thong_bao import service
from tests.factories import tao_khach, tao_nhan_vien

GOC = "/api/v1/noi-bo/thong-bao"


async def tao(db, nhan_vien, tieu_de="Đơn mới", **truong):
    gia_tri = {"loai": "don_hang", "lien_ket": "/nhan-vien/don-hang/1", **truong}
    return await service.gui_cho_nhan_vien(db, nhan_vien.id, tieu_de=tieu_de, **gia_tri)


async def test_chi_thay_thong_bao_cua_chinh_minh_moi_nhat_truoc(dang_nhap_duoc_si, db):
    nv = dang_nhap_duoc_si.tai_khoan
    khac = await tao_nhan_vien(db, "PHARMACIST")
    khach = await tao_khach(db)
    cu = await tao(db, nv, "Cũ")
    moi = await tao(db, nv, "Mới")
    await tao(db, khac, "Của người khác")
    db.add(ThongBao(khach_hang_id=khach.id, loai="don_hang", tieu_de="Của khách"))
    cu.created_at = bay_gio_utc() - timedelta(hours=1)
    await db.flush()

    phan_hoi = await dang_nhap_duoc_si.get(GOC)
    assert phan_hoi.status_code == 200
    than = phan_hoi.json()
    assert [t["tieu_de"] for t in than["du_lieu"]] == ["Mới", "Cũ"] and than["tong"] == 2
    assert (than["trang"], than["kich_thuoc"]) == (1, 20)
    assert set(than["du_lieu"][0]) == {"id", "loai", "tieu_de", "noi_dung", "lien_ket", "da_doc", "created_at"}
    assert than["du_lieu"][0]["id"] == moi.id and than["du_lieu"][0]["da_doc"] is False


async def test_phan_trang_va_loc_theo_da_doc(dang_nhap_kho, db):
    nv = dang_nhap_kho.tai_khoan
    cac = [await tao(db, nv, f"TB {i}") for i in range(5)]
    cac[0].da_doc = cac[1].da_doc = True
    await db.flush()

    trang_1 = (await dang_nhap_kho.get(GOC, params={"kich_thuoc": 2, "trang": 1})).json()
    trang_3 = (await dang_nhap_kho.get(GOC, params={"kich_thuoc": 2, "trang": 3})).json()
    assert (trang_1["tong"], len(trang_1["du_lieu"]), len(trang_3["du_lieu"])) == (5, 2, 1)
    chua_doc = (await dang_nhap_kho.get(GOC, params={"da_doc": "false"})).json()
    da_doc = (await dang_nhap_kho.get(GOC, params={"da_doc": "true"})).json()
    assert (chua_doc["tong"], da_doc["tong"]) == (3, 2)
    assert all(not t["da_doc"] for t in chua_doc["du_lieu"]) and all(t["da_doc"] for t in da_doc["du_lieu"])


async def test_so_chua_doc_dem_dung_chu_so_huu(dang_nhap_admin, db):
    nv = dang_nhap_admin.tai_khoan
    khac = await tao_nhan_vien(db, "ADMIN")
    for _ in range(3):
        await tao(db, nv)
    da_doc = await tao(db, nv)
    da_doc.da_doc = True
    await tao(db, khac)
    await db.flush()
    assert (await dang_nhap_admin.get(f"{GOC}/so-chua-doc")).json() == {"so_chua_doc": 3}


async def test_danh_dau_da_doc_mot_thong_bao_va_goi_lai_van_thanh_cong(dang_nhap_duoc_si, db):
    tb = await tao(db, dang_nhap_duoc_si.tai_khoan)
    for _ in range(2):
        phan_hoi = await dang_nhap_duoc_si.post(f"{GOC}/{tb.id}/da-doc")
        assert phan_hoi.status_code == 200 and phan_hoi.json()["da_doc"] is True
    await db.refresh(tb)
    assert tb.da_doc is True


async def test_thong_bao_cua_nguoi_khac_hoac_cua_khach_hoac_khong_co_deu_404(dang_nhap_duoc_si, db):
    khac = await tao_nhan_vien(db, "PHARMACIST")
    khach = await tao_khach(db)
    cua_nguoi_khac = await tao(db, khac)
    cua_khach = ThongBao(khach_hang_id=khach.id, loai="don_hang", tieu_de="Của khách")
    db.add(cua_khach)
    await db.flush()
    for tb_id in (cua_nguoi_khac.id, cua_khach.id, 2_000_000_000):
        phan_hoi = await dang_nhap_duoc_si.post(f"{GOC}/{tb_id}/da-doc")
        assert phan_hoi.status_code == 404 and phan_hoi.json()["ma_loi"] == "KHONG_TIM_THAY", tb_id
    await db.refresh(cua_nguoi_khac)
    assert cua_nguoi_khac.da_doc is False  # không bị đánh dấu hộ


async def test_danh_dau_tat_ca_chi_dung_thong_bao_chua_doc_cua_minh(dang_nhap_kho, db):
    nv = dang_nhap_kho.tai_khoan
    khac = await tao_nhan_vien(db, "WAREHOUSE")
    cua_minh = [await tao(db, nv) for _ in range(3)]
    cua_minh[0].da_doc = True
    cua_khac = await tao(db, khac)
    await db.flush()

    phan_hoi = await dang_nhap_kho.post(f"{GOC}/da-doc-tat-ca")
    assert phan_hoi.status_code == 200 and phan_hoi.json() == {"da_cap_nhat": 2}
    assert (await dang_nhap_kho.get(f"{GOC}/so-chua-doc")).json() == {"so_chua_doc": 0}
    await db.refresh(cua_khac)
    assert cua_khac.da_doc is False
    assert (await dang_nhap_kho.post(f"{GOC}/da-doc-tat-ca")).json() == {"da_cap_nhat": 0}


async def test_ca_ba_vai_tro_deu_dung_duoc(dang_nhap_duoc_si, dang_nhap_kho, dang_nhap_admin):
    for client in (dang_nhap_duoc_si, dang_nhap_kho, dang_nhap_admin):
        assert (await client.get(GOC)).status_code == 200
        assert (await client.get(f"{GOC}/so-chua-doc")).status_code == 200
        assert (await client.post(f"{GOC}/da-doc-tat-ca")).status_code == 200


@pytest.mark.parametrize(
    ("phuong_thuc", "duong_dan"),
    [("GET", GOC), ("GET", f"{GOC}/so-chua-doc"), ("POST", f"{GOC}/da-doc-tat-ca"), ("POST", f"{GOC}/1/da-doc")],
)
async def test_phai_dang_nhap_noi_bo(client, phuong_thuc, duong_dan):
    phan_hoi = await client.request(phuong_thuc, duong_dan)
    assert phan_hoi.status_code == 401 and phan_hoi.json()["ma_loi"] == "CHUA_DANG_NHAP"


async def test_gui_thong_bao_luu_day_du_truong_va_mac_dinh_chua_doc(db):
    nv = await tao_nhan_vien(db)
    tb = await service.gui_cho_nhan_vien(
        db, nv.id, loai="kho", tieu_de="Lô sắp hết hạn", noi_dung="Lô A1 còn 30 ngày", lien_ket="/nhan-vien/canh-bao"
    )
    luu = (await db.execute(select(ThongBao).where(ThongBao.id == tb.id))).scalar_one()
    assert (luu.nhan_vien_id, luu.khach_hang_id, luu.loai, luu.da_doc) == (nv.id, None, "kho", False)
    assert luu.created_at is not None and luu.lien_ket == "/nhan-vien/canh-bao"


@pytest.mark.parametrize(
    "lien_ket",
    ["https://trang-lua-dao.example", "//trang-lua-dao.example", "javascript:alert(1)", "don-hang/1", "/\\x.example"],
)
async def test_lien_ket_ngoai_ung_dung_bi_tu_choi(db, lien_ket):
    nv = await tao_nhan_vien(db)
    with pytest.raises(ValueError, match="lien_ket"):
        await service.gui_cho_nhan_vien(db, nv.id, loai="kho", tieu_de="X", lien_ket=lien_ket)

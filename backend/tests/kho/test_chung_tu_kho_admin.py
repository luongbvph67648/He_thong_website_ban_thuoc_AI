"""AD16: Admin chỉ xem đơn hàng, chứng từ kho, nội dung chuyên môn (T6.7)."""

import pytest

from tests.factories import tao_lo, tao_san_pham

CT = "/api/v1/noi-bo/chung-tu-kho"
DON_VI = [{"ten_don_vi": "hộp", "he_so": 1, "gia_ban": 10000, "la_mac_dinh": True}]


async def _lap_phieu_huy(kho, lo):
    r = await kho.post(
        "/api/v1/noi-bo/phieu-huy",
        json={"ly_do": "het_han", "dong": [{"lo_id": lo.id, "tu_khu": "kho_ban", "so_luong": 1}]},
    )
    assert r.status_code == 201, r.text
    return r.json()


async def test_gop_chung_tu_cac_loai_phan_trang_va_loc(dang_nhap_kho, dang_nhap_admin, db):
    sp = await tao_san_pham(db, "thuoc_khong_ke_don", don_vi=DON_VI)
    lo = await tao_lo(db, sp, so_luong=10)
    huy = await _lap_phieu_huy(dang_nhap_kho, lo)
    kk = await dang_nhap_kho.post("/api/v1/noi-bo/kiem-ke", json={})
    assert kk.status_code == 201, kk.text
    d = (await dang_nhap_admin.get(CT)).json()
    loai = {x["loai"] for x in d["du_lieu"]}
    assert {"phieu_huy", "kiem_ke"} <= loai and d["tong"] >= 2
    h = next(x for x in d["du_lieu"] if x["loai"] == "phieu_huy")
    assert (
        h["ma_phieu"] == huy["ma_phieu"]
        and h["trang_thai"] == "cho_duyet"
        and h["nguoi_lap"]
        and h["nguoi_duyet"] is None
    )
    chi_huy = (await dang_nhap_admin.get(CT, params={"loai": "phieu_huy"})).json()
    assert {x["loai"] for x in chi_huy["du_lieu"]} == {"phieu_huy"}
    trang = (await dang_nhap_admin.get(CT, params={"kich_thuoc": 1, "trang": 2})).json()
    assert len(trang["du_lieu"]) == 1 and trang["tong"] == d["tong"]
    assert (await dang_nhap_admin.get(CT, params={"loai": "la"})).status_code == 400


@pytest.mark.parametrize("vai_tro", ["WAREHOUSE", "PHARMACIST"])
async def test_vai_tro_khac_khong_xem_man_gop(vai_tro, clients_theo_vai_tro):
    assert (await clients_theo_vai_tro[vai_tro].get(CT)).status_code == 403


async def test_admin_khong_ghi_duoc_o_cac_man_chi_xem(clients_theo_vai_tro, dang_nhap_kho, db):
    """Mỗi loại: Admin gọi API ghi bị 403 (chứng từ kho, nội dung chuyên môn, đơn hàng, thuốc kê đơn)."""
    ad = clients_theo_vai_tro["ADMIN"]
    sp = await tao_san_pham(db, "thuoc_khong_ke_don", don_vi=DON_VI)
    lo = await tao_lo(db, sp, so_luong=5)
    cac_cuoc_goi = [
        ("POST", "/api/v1/noi-bo/phieu-nhap", {}),
        (
            "POST",
            "/api/v1/noi-bo/phieu-huy",
            {"ly_do": "het_han", "dong": [{"lo_id": lo.id, "tu_khu": "kho_ban", "so_luong": 1}]},
        ),
        ("POST", "/api/v1/noi-bo/kiem-ke", {}),
        ("POST", "/api/v1/noi-bo/dieu-chinh", {}),
        ("POST", f"/api/v1/noi-bo/chuyen-mon/san-pham/{sp.id}", {}),
        ("POST", "/api/v1/noi-bo/tuong-tac", {}),
        ("POST", "/api/v1/noi-bo/don-hang/1/xac-nhan", None),
        ("POST", "/api/v1/noi-bo/don-hang/1/huy", {"ly_do": "thử"}),
    ]
    for phuong_thuc, duong, body in cac_cuoc_goi:
        r = await ad.request(phuong_thuc, duong, json=body)
        assert r.status_code == 403, (duong, r.status_code, r.text)
    # các màn xem dùng lại API nội bộ ở mức chi_xem
    for duong in (
        "/api/v1/noi-bo/don-hang",
        "/api/v1/noi-bo/chuyen-mon",
        "/api/v1/noi-bo/phieu-nhap",
        "/api/v1/noi-bo/kiem-ke",
    ):
        assert (await ad.get(duong)).status_code == 200, duong

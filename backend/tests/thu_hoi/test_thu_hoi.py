"""AD13, KHO12, DS13: thu hồi lô (T6.6)."""

from sqlalchemy import select

from app.models.ban_hang import CtDonHang, PhanBoLo
from app.models.khach_hang import ThongBao
from app.models.kho import CtLenhThuHoi, LenhThuHoi, LoThuoc
from app.modules.kho import ton_kho
from app.modules.kho.ton_kho import ChungTu, YeuCauGiu
from tests.factories import tao_don, tao_khach, tao_lo, tao_san_pham

TH = "/api/v1/noi-bo/thu-hoi"
DON_VI = [{"ten_don_vi": "hộp", "he_so": 1, "gia_ban": 10000, "la_mac_dinh": True}]


async def _da_ban(db, khach, sp, lo, so_luong=2):
    """Đơn đã giao dùng đúng lô `lo`: giữ rồi xuất kho."""
    don = await tao_don(db, khach, "da_giao", [{"san_pham": sp, "so_luong": so_luong}])
    ct = (await db.execute(select(CtDonHang).where(CtDonHang.don_hang_id == don.id))).scalars().one()
    pb = await ton_kho.giu_hang_nhieu(db, [YeuCauGiu(ct.id, sp.id, so_luong)])
    ds = [p for v in pb.values() for p in v]
    assert {p.lo_id for p in ds} == {lo.id}
    await ton_kho.xuat_theo_phan_bo(db, ds, ChungTu("don_hang", don.id, None))
    return don


async def test_tao_lenh_khoa_lo_lap_dong_truy_vet_va_bao_khach(dang_nhap_khach, dang_nhap_admin, kenh_tin_nhan, db):
    khach = dang_nhap_khach.tai_khoan
    sp = await tao_san_pham(db, "thuoc_khong_ke_don", don_vi=DON_VI)
    lo = await tao_lo(db, sp, so_luong=50)
    lo_khac = await tao_lo(db, sp, so_luong=30)
    don = await _da_ban(db, khach, sp, lo, 3)
    don_khac = await tao_don(db, await tao_khach(db), "cho_xac_nhan", [{"san_pham": sp, "so_luong": 1}])
    r = await dang_nhap_admin.post(TH, json={"san_pham_id": sp.id, "lo_id": lo.id, "can_cu": "CV 123/QLD"})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["ma_lenh"].startswith("TH") and d["trang_thai"] == "dang_thu_hoi" and d["so_khach"] == 1
    assert [x["lo_id"] for x in d["lo"]] == [lo.id] and d["lo"][0]["so_luong_da_ban"] == 3
    assert (await db.get(LoThuoc, lo.id, populate_existing=True)).trang_thai == "thu_hoi"
    assert (await db.get(LoThuoc, lo_khac.id, populate_existing=True)).trang_thai != "thu_hoi"
    ct = (await db.execute(select(CtLenhThuHoi))).scalars().one()
    assert (ct.don_hang_id, ct.khach_hang_id, ct.so_luong_da_ban, ct.ket_qua_lien_he) == (
        don.id,
        khach.id,
        3,
        "chua_lien_he",
    )
    tb = (
        (await db.execute(select(ThongBao).where(ThongBao.khach_hang_id == khach.id, ThongBao.loai == "thu_hoi")))
        .scalars()
        .one()
    )
    assert don.ma_don in tb.tieu_de and sp.ten in (tb.noi_dung or "") and sp.ten not in tb.tieu_de
    assert all(sp.ten not in t for _, t in kenh_tin_nhan.sms)  # SMS không nêu tên thuốc
    assert don_khac is not None


async def test_go_khoi_don_chua_xuat_phan_bo_lai_sang_lo_khac(dang_nhap_admin, db):
    sp = await tao_san_pham(db, "thuoc_khong_ke_don", don_vi=DON_VI)
    lo = await tao_lo(db, sp, so_luong=50)
    lo_khac = await tao_lo(db, sp, so_luong=30)
    lo_khac.han_su_dung = lo.han_su_dung.replace(year=lo.han_su_dung.year + 1)
    khach = await tao_khach(db)
    don = await tao_don(db, khach, "da_xac_nhan", [{"san_pham": sp, "so_luong": 4}])
    ct = (await db.execute(select(PhanBoLo))).first()  # chưa có phân bổ vì factory không giữ hàng
    assert ct is None
    dong = (await db.execute(select(CtDonHang).where(CtDonHang.don_hang_id == don.id))).scalars().one()
    await ton_kho.giu_hang_nhieu(db, [YeuCauGiu(dong.id, sp.id, 4)])
    r = await dang_nhap_admin.post(TH, json={"san_pham_id": sp.id, "lo_id": lo.id, "can_cu": "Nghi vấn chất lượng"})
    assert r.status_code == 201, r.text
    assert r.json()["don_thieu_hang"] == []
    pb = (await db.execute(select(PhanBoLo).where(PhanBoLo.ct_don_hang_id == dong.id))).scalars().all()
    giu = [p for p in pb if p.trang_thai == "dang_giu"]
    assert [p.lo_id for p in giu] == [lo_khac.id] and sum(p.so_luong_co_so for p in giu) == 4
    assert (await db.get(LoThuoc, lo.id, populate_existing=True)).so_luong_giu == 0


async def test_thu_hoi_moi_lo_cua_san_pham_va_khong_tao_lenh_trung(dang_nhap_admin, db):
    sp = await tao_san_pham(db, "thuoc_khong_ke_don", don_vi=DON_VI)
    l1 = await tao_lo(db, sp, so_luong=10)
    l2 = await tao_lo(db, sp, so_luong=10)
    r = await dang_nhap_admin.post(TH, json={"san_pham_id": sp.id, "can_cu": "Đình chỉ số đăng ký"})
    assert r.status_code == 201 and {x["lo_id"] for x in r.json()["lo"]} == {l1.id, l2.id}
    for lo in (l1, l2):
        assert (await db.get(LoThuoc, lo.id, populate_existing=True)).trang_thai == "thu_hoi"
    lai = await dang_nhap_admin.post(TH, json={"san_pham_id": sp.id, "lo_id": l1.id, "can_cu": "Lại"})
    assert lai.status_code == 409
    sai = await dang_nhap_admin.post(TH, json={"san_pham_id": sp.id, "lo_id": 999999, "can_cu": "Sai lô"})
    assert sai.status_code == 400
    la = await dang_nhap_admin.post(TH, json={"san_pham_id": 999999, "can_cu": "Sản phẩm lạ"})
    assert la.status_code == 400


async def test_duoc_si_lien_he_khach_va_dong_lenh(
    dang_nhap_khach, dang_nhap_admin, dang_nhap_duoc_si, dang_nhap_kho, db
):
    sp = await tao_san_pham(db, "thuoc_khong_ke_don", don_vi=DON_VI)
    lo = await tao_lo(db, sp, so_luong=20)
    don = await _da_ban(db, dang_nhap_khach.tai_khoan, sp, lo, 2)
    lenh_id = (await dang_nhap_admin.post(TH, json={"san_pham_id": sp.id, "lo_id": lo.id, "can_cu": "CV 9"})).json()[
        "id"
    ]
    # kho thấy lô cần gom
    kho = (await dang_nhap_kho.get(f"{TH}/thuc-hien/{lenh_id}")).json()
    assert kho["ton_con_lai"] == 18 and kho["lo"][0]["so_luong_ton"] == 18
    assert [x["id"] for x in (await dang_nhap_kho.get(f"{TH}/thuc-hien")).json()["du_lieu"]] == [lenh_id]
    # chưa đóng được: còn khách chưa liên hệ và còn hàng
    chua = await dang_nhap_admin.post(f"{TH}/{lenh_id}/dong")
    assert chua.status_code == 409 and chua.json()["chi_tiet"] == {"khach_chua_lien_he": 1, "ton_con_lai": 18}
    khach = (await dang_nhap_duoc_si.get(f"{TH}/lien-he/{lenh_id}/khach")).json()
    assert khach[0]["ma_don"] == don.ma_don and khach[0]["ten_khach"] and khach[0]["ket_qua_lien_he"] == "chua_lien_he"
    ct_id = khach[0]["id"]
    sai = await dang_nhap_duoc_si.put(
        f"{TH}/lien-he/khach/{ct_id}", json={"ket_qua_lien_he": "da_thu_ve", "so_luong_da_thu_ve": 5}
    )
    assert sai.status_code == 400
    ok = await dang_nhap_duoc_si.put(
        f"{TH}/lien-he/khach/{ct_id}",
        json={"ket_qua_lien_he": "da_thu_ve", "so_luong_da_thu_ve": 2, "ghi_chu": "Đã nhận lại"},
    )
    assert ok.status_code == 200 and ok.json()["so_luong_da_thu_ve"] == 2
    # kho hủy toàn bộ hàng còn lại qua phiếu hủy được Admin duyệt
    lo_db = await db.get(LoThuoc, lo.id, populate_existing=True)
    phieu = await dang_nhap_kho.post(
        "/api/v1/noi-bo/phieu-huy",
        json={"ly_do": "thu_hoi", "dong": [{"lo_id": lo.id, "tu_khu": "kho_ban", "so_luong": lo_db.so_luong_ton}]},
    )
    assert phieu.status_code == 201, phieu.text
    assert (await dang_nhap_admin.post(f"/api/v1/noi-bo/duyet-phieu/huy/{phieu.json()['id']}/duyet")).status_code == 200
    dong = await dang_nhap_admin.post(f"{TH}/{lenh_id}/dong")
    assert dong.status_code == 200, dong.text
    assert dong.json()["trang_thai"] == "hoan_tat" and dong.json()["dong_luc"]
    lenh = await db.get(LenhThuHoi, lenh_id, populate_existing=True)
    assert lenh.trang_thai == "hoan_tat"
    assert (await dang_nhap_duoc_si.get(f"{TH}/lien-he/{lenh_id}/khach")).status_code == 404  # chỉ lệnh đang mở
    assert (await dang_nhap_admin.post(f"{TH}/{lenh_id}/dong")).status_code == 409


async def test_phieu_xuat_tra_gan_lenh_thu_hoi(dang_nhap_admin, dang_nhap_kho, db):
    from tests.kho.test_phieu_huy_xuat_tra import tao_ncc

    sp = await tao_san_pham(db, "thuoc_khong_ke_don", don_vi=DON_VI)
    lo = await tao_lo(db, sp, so_luong=10)
    khac = await tao_lo(db, await tao_san_pham(db, "thuoc_khong_ke_don", don_vi=DON_VI), so_luong=10)
    ncc = await tao_ncc(db)
    lenh_id = (await dang_nhap_admin.post(TH, json={"san_pham_id": sp.id, "lo_id": lo.id, "can_cu": "CV 1"})).json()[
        "id"
    ]
    dong = [{"lo_id": lo.id, "tu_khu": "kho_ban", "so_luong": 10}]
    ok = await dang_nhap_kho.post(
        "/api/v1/noi-bo/xuat-tra",
        json={"nha_cung_cap_id": ncc.id, "ly_do": "Thu hồi", "lenh_thu_hoi_id": lenh_id, "dong": dong},
    )
    assert ok.status_code == 201, ok.text
    lo_khac = await dang_nhap_kho.post(
        "/api/v1/noi-bo/xuat-tra",
        json={
            "nha_cung_cap_id": ncc.id,
            "ly_do": "Sai lô",
            "lenh_thu_hoi_id": lenh_id,
            "dong": [{"lo_id": khac.id, "tu_khu": "kho_ban", "so_luong": 1}],
        },
    )
    assert lo_khac.status_code == 400
    assert (await dang_nhap_admin.post(f"{TH}/{lenh_id}/dong")).status_code == 409


async def test_phan_quyen_thu_hoi(dang_nhap_khach, clients_theo_vai_tro, db):
    sp = await tao_san_pham(db, "thuoc_khong_ke_don", don_vi=DON_VI)
    await tao_lo(db, sp, so_luong=5)
    kho, ds, ad = (clients_theo_vai_tro[k] for k in ("WAREHOUSE", "PHARMACIST", "ADMIN"))
    body = {"san_pham_id": sp.id, "can_cu": "CV 55"}
    assert (await kho.post(TH, json=body)).status_code in (401, 403)
    assert (await ds.post(TH, json=body)).status_code in (401, 403)
    r = await ad.post(TH, json=body)
    assert r.status_code == 201, r.text
    lenh_id = r.json()["id"]
    assert (await kho.get(f"{TH}/{lenh_id}")).status_code in (401, 403)
    assert (await ds.get(f"{TH}/thuc-hien")).status_code in (401, 403)
    assert (await kho.get(f"{TH}/lien-he/{lenh_id}/khach")).status_code in (401, 403)
    assert (await ad.get(f"{TH}/lien-he/{lenh_id}/khach")).status_code == 200  # Admin được xem (chi_xem)
    assert (await ad.get(f"{TH}/thuc-hien")).status_code == 200  # Admin xem phía kho
    assert (await dang_nhap_khach.get(TH)).status_code in (401, 403)

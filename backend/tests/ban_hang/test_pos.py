"""DS08: bán tại quầy POS (T5.4): tìm/quét mã, lô cận hạn, FEFO, thu tiền, thuốc kê đơn, cảnh báo, hóa đơn."""

import uuid
from datetime import timedelta

from sqlalchemy import select

from app.core.thoi_gian import hom_nay_vn
from app.models.ban_hang import DonHang, PhanBoLo, ThanhToan, YeuCauDonThuoc
from app.models.he_thong import NhanVien
from app.models.kho import BienDongKho, LoThuoc
from app.models.san_pham import HoatChat, ThanhPhan, TuongTacHoatChat
from tests.factories import tao_khach, tao_lo, tao_nhan_vien, tao_san_pham

POS = "/api/v1/noi-bo/pos"
PNG = b"\x89PNG\r\n\x1a\n" + b"anh-don-quay" * 20
DON_VI = [
    {"ten_don_vi": "viên", "he_so": 1, "gia_ban": 1000, "la_mac_dinh": False, "ma_vach": None},
    {"ten_don_vi": "hộp", "he_so": 10, "gia_ban": 9000, "la_mac_dinh": True, "ma_vach": "8934001234567"},
]


def _dong(sp, don_vi="viên", so_luong=1):
    return {"san_pham_id": sp.id, "don_vi_id": sp.don_vi_theo_ten[don_vi].id, "so_luong": so_luong}


def _ban(dong, **kw):
    return {"dong": dong, "phuong_thuc_thu": "tien_mat", "tien_khach_dua": "100000", **kw}


async def _sp(db, loai="thuoc_khong_ke_don", ton=100, **kw):
    sp = await tao_san_pham(db, loai, don_vi=DON_VI, **kw)
    await tao_lo(db, sp, so_luong=ton)
    return sp


async def _gui(c, body, khoa=None):
    return await c.post(f"{POS}/don", json=body, headers={"Idempotency-Key": khoa or str(uuid.uuid4())})


async def _yc_quay(c, **kw):
    r = await c.post(
        f"{POS}/don-thuoc",
        data={"ho_ten": "Lê Văn C", "tuoi_hoac_nam_sinh": "45", **kw},
        files=[("anh", ("d.png", PNG, "image/png"))],
    )
    assert r.status_code == 201, r.text
    return r.json()


async def test_chi_duoc_si_dung_pos(clients_theo_vai_tro):
    for vai_tro in ("WAREHOUSE", "ADMIN"):
        c = clients_theo_vai_tro[vai_tro]
        assert (await c.get(f"{POS}/san-pham", params={"q": "a"})).status_code == 403
        assert (await _gui(c, _ban([]))).status_code == 403


async def test_tim_theo_ten_ma_vach_va_ton_gom_lo_can_han(dang_nhap_duoc_si, db):
    sp = await tao_san_pham(db, "thuoc_ke_don", don_vi=DON_VI, ten="Zithromax-pos-xyz")
    await tao_lo(db, sp, so_luong=30)
    await tao_lo(db, sp, so_luong=5, han_su_dung=hom_nay_vn() + timedelta(days=30))  # cận hạn
    await tao_lo(db, sp, so_luong=7, han_su_dung=hom_nay_vn() - timedelta(days=1), trang_thai="het_han")
    r = await dang_nhap_duoc_si.get(f"{POS}/san-pham", params={"q": "zithromax pos"[:9]})
    d = r.json()
    assert [x["id"] for x in d] == [sp.id] and d[0]["ton_quay"] == 35 and d[0]["co_lo_can_han"] is True
    assert d[0]["loai_san_pham"] == "thuoc_ke_don" and d[0]["don_vi_khop_ma_vach"] is None
    quet = (await dang_nhap_duoc_si.get(f"{POS}/san-pham", params={"q": "8934001234567"})).json()
    assert [x["id"] for x in quet] == [sp.id] and quet[0]["don_vi_khop_ma_vach"] == sp.don_vi_theo_ten["hộp"].id
    assert (await dang_nhap_duoc_si.get(f"{POS}/san-pham", params={"q": ""})).json() == []


async def test_ban_le_theo_vien_tien_mat_xuat_kho_ngay(dang_nhap_duoc_si, db):
    sp = await _sp(db, ton=50)
    r = await _gui(dang_nhap_duoc_si, _ban([_dong(sp, "viên", 3), _dong(sp, "hộp", 1)], tien_khach_dua="20000"))
    assert r.status_code == 201, r.text
    hd = r.json()["hoa_don"]
    assert hd["tong_tien"] == "12000.00" and hd["tien_khach_dua"] == "20000.00" and hd["tien_thua"] == "8000.00"
    assert hd["phuong_thuc_thu"] == "tien_mat" and hd["co_thuoc_ke_don"] is False and hd["ma_don"].startswith("DH")
    assert {(x["ten_don_vi"], x["so_luong"]) for x in hd["dong"]} == {("viên", 3), ("hộp", 1)}
    don = (await db.execute(select(DonHang).where(DonHang.id == r.json()["don_id"]))).scalars().one()
    assert don.trang_thai == "hoan_tat" and don.kenh_ban == "tai_quay" and don.trang_thai_tt == "da_thanh_toan"
    assert don.nhan_vien_tao_id == dang_nhap_duoc_si.tai_khoan.id and don.khach_hang_id is None
    lo = (await db.execute(select(LoThuoc).where(LoThuoc.san_pham_id == sp.id))).scalars().one()
    assert lo.so_luong_ton == 37 and lo.so_luong_giu == 0  # 3 viên + 1 hộp (10 viên)
    the = (await db.execute(select(BienDongKho).where(BienDongKho.chung_tu_id == don.id))).scalars().all()
    assert [(t.loai, t.so_luong) for t in the] == [("xuat_ban", -13)] or sum(t.so_luong for t in the) == -13
    tt = (await db.execute(select(ThanhToan).where(ThanhToan.don_hang_id == don.id))).scalars().one()
    assert (tt.trang_thai, tt.cong_thanh_toan, tt.so_tien, tt.nhan_vien_xu_ly_id) == (
        "thanh_cong", "tien_mat", 12000, dang_nhap_duoc_si.tai_khoan.id
    )  # fmt: skip
    pb = (await db.execute(select(PhanBoLo))).scalars().all()
    assert pb and all(p.trang_thai == "da_xuat" for p in pb)


async def test_dung_duoc_lo_can_han_va_fefo(dang_nhap_duoc_si, db):
    sp = await tao_san_pham(db, "thuoc_khong_ke_don", don_vi=DON_VI)
    can_han = await tao_lo(db, sp, so_luong=4, han_su_dung=hom_nay_vn() + timedelta(days=30))
    dang_ban = await tao_lo(db, sp, so_luong=20, han_su_dung=hom_nay_vn() + timedelta(days=400))
    r = await _gui(dang_nhap_duoc_si, _ban([_dong(sp, "viên", 6)]))
    assert r.status_code == 201, r.text
    await db.refresh(can_han)
    await db.refresh(dang_ban)
    assert (can_han.so_luong_ton, dang_ban.so_luong_ton) == (0, 18)  # hết lô gần hạn trước (FEFO), rồi sang lô sau


async def test_tien_mat_phai_du_chuyen_khoan_khong_nhan_tien_khach_dua(dang_nhap_duoc_si, db):
    sp = await _sp(db)
    thieu = await _gui(dang_nhap_duoc_si, _ban([_dong(sp, "hộp", 1)], tien_khach_dua="8999"))
    assert thieu.status_code == 400 and thieu.json()["chi_tiet"][0]["truong"] == "tien_khach_dua"
    khong_co = await _gui(dang_nhap_duoc_si, {"dong": [_dong(sp)], "phuong_thuc_thu": "tien_mat"})
    assert khong_co.status_code == 400
    sai = await _gui(
        dang_nhap_duoc_si, {"dong": [_dong(sp)], "phuong_thuc_thu": "chuyen_khoan", "tien_khach_dua": "5000"}
    )
    assert sai.status_code == 400
    ok = await _gui(dang_nhap_duoc_si, {"dong": [_dong(sp, "hộp", 2)], "phuong_thuc_thu": "chuyen_khoan"})
    assert ok.status_code == 201 and ok.json()["hoa_don"]["tien_thua"] is None
    cong = (await db.execute(select(ThanhToan.cong_thanh_toan))).scalars().all()
    assert cong == ["chuyen_khoan"]
    assert (await db.execute(select(DonHang).where(DonHang.trang_thai_tt == "da_thanh_toan"))).scalars().one()


async def test_cong_thanh_toan_khac_bi_chan(dang_nhap_duoc_si, db):
    sp = await _sp(db)
    for pt in ("cod", "vnpay"):
        assert (await _gui(dang_nhap_duoc_si, {"dong": [_dong(sp)], "phuong_thuc_thu": pt})).status_code == 400


async def test_het_hang_hoan_tac_khong_tao_don(dang_nhap_duoc_si, db):
    sp = await _sp(db, ton=2)
    r = await _gui(dang_nhap_duoc_si, _ban([_dong(sp, "viên", 3)]))
    assert r.status_code == 409 and r.json()["ma_loi"] == "HET_HANG"
    assert (await db.execute(select(DonHang))).first() is None


async def test_idempotency_khong_ban_hai_lan(dang_nhap_duoc_si, db):
    sp = await _sp(db, ton=20)
    khoa = str(uuid.uuid4())
    a = await _gui(dang_nhap_duoc_si, _ban([_dong(sp, "viên", 5)]), khoa)
    b = await _gui(dang_nhap_duoc_si, _ban([_dong(sp, "viên", 5)]), khoa)
    assert a.status_code == b.status_code == 201 and a.json() == b.json()
    lo = (await db.execute(select(LoThuoc).where(LoThuoc.san_pham_id == sp.id))).scalars().one()
    assert lo.so_luong_ton == 15
    assert (await dang_nhap_duoc_si.post(f"{POS}/don", json=_ban([_dong(sp)]))).status_code == 400  # thiếu khóa


async def test_thuoc_ke_don_can_yeu_cau_tai_quay(dang_nhap_duoc_si, db):
    rx = await _sp(db, "thuoc_ke_don", ton=30)
    thieu = await _gui(dang_nhap_duoc_si, _ban([_dong(rx)]))
    assert thieu.status_code == 400 and thieu.json()["chi_tiet"][0]["truong"] == "yeu_cau_don_thuoc_id"
    yc = await _yc_quay(dang_nhap_duoc_si)
    d = await db.get(YeuCauDonThuoc, yc["id"])
    assert (d.kenh, d.trang_thai, d.duoc_si_id, d.da_su_dung, d.khach_hang_id) == (
        "tai_quay", "da_tao_don", dang_nhap_duoc_si.tai_khoan.id, False, None
    )  # fmt: skip
    assert d.anh_don_thuoc[0].startswith("don-thuoc/") and d.hash_anh
    r = await _gui(dang_nhap_duoc_si, _ban([_dong(rx, "viên", 2)], yeu_cau_don_thuoc_id=yc["id"]))
    assert r.status_code == 201, r.text
    assert r.json()["hoa_don"]["co_thuoc_ke_don"] is True
    await db.refresh(d)
    assert d.da_su_dung is True
    don = (await db.execute(select(DonHang))).scalars().one()
    assert don.yeu_cau_don_thuoc_id == d.id and don.giam_gia == 0
    # Dùng lại yêu cầu cho đơn khác bị chặn.
    lai = await _gui(dang_nhap_duoc_si, _ban([_dong(rx)], yeu_cau_don_thuoc_id=yc["id"]))
    assert lai.status_code == 409


async def test_yeu_cau_cua_nguoi_khac_hoac_khong_phai_quay_bi_chan(dang_nhap_duoc_si, app, db):

    rx = await _sp(db, "thuoc_ke_don")
    khac = await tao_nhan_vien(db)
    cua_khac = YeuCauDonThuoc(
        ma_yeu_cau="YCKHAC001", kenh="tai_quay", ho_ten="X", so_dien_thoai="", anh_don_thuoc=[], trang_thai="da_tao_don",
        duoc_si_id=khac.id, hash_anh="a" * 64,
    )  # fmt: skip
    online = YeuCauDonThuoc(
        ma_yeu_cau="YCONLINE01", kenh="online", ho_ten="X", so_dien_thoai="0900000000", anh_don_thuoc=[],
        trang_thai="da_tao_don", duoc_si_id=dang_nhap_duoc_si.tai_khoan.id, hash_anh="b" * 64,
    )  # fmt: skip
    db.add_all([cua_khac, online])
    await db.flush()
    for yc in (cua_khac, online):
        r = await _gui(dang_nhap_duoc_si, _ban([_dong(rx)], yeu_cau_don_thuoc_id=yc.id))
        assert r.status_code == 404
    otc = await _sp(db)
    yc = await _yc_quay(dang_nhap_duoc_si)
    r = await _gui(dang_nhap_duoc_si, _ban([_dong(otc)], yeu_cau_don_thuoc_id=yc["id"]))
    assert r.status_code == 400


async def test_anh_trung_don_da_dung_can_xac_nhan(dang_nhap_duoc_si, db):
    rx = await _sp(db, "thuoc_ke_don", ton=50)
    a = await _yc_quay(dang_nhap_duoc_si)
    assert (await _gui(dang_nhap_duoc_si, _ban([_dong(rx)], yeu_cau_don_thuoc_id=a["id"]))).status_code == 201
    b = await _yc_quay(dang_nhap_duoc_si)
    assert b["trung_anh"] == [a["ma_yeu_cau"]]
    r = await _gui(dang_nhap_duoc_si, _ban([_dong(rx)], yeu_cau_don_thuoc_id=b["id"]))
    assert r.status_code == 409 and r.json()["ma_loi"] == "CAN_XAC_NHAN_CANH_BAO"
    r = await _gui(dang_nhap_duoc_si, _ban([_dong(rx)], yeu_cau_don_thuoc_id=b["id"], xac_nhan_trung_anh=True))
    assert r.status_code == 201


async def test_lap_yeu_cau_quay_kiem_tra_anh(dang_nhap_duoc_si):
    r = await dang_nhap_duoc_si.post(
        f"{POS}/don-thuoc", data={"ho_ten": "A"}, files=[("anh", ("x.png", b"khong-phai-anh" * 5, "image/png"))]
    )
    assert r.status_code == 400 and r.json()["ma_loi"] == "DU_LIEU_KHONG_HOP_LE"
    r = await dang_nhap_duoc_si.post(
        f"{POS}/don-thuoc", data={"ho_ten": ""}, files=[("anh", ("x.png", PNG, "image/png"))]
    )
    assert r.status_code == 400


async def test_canh_bao_tuong_tac_nang_can_xac_nhan_moi_ban(dang_nhap_duoc_si, db):
    a = HoatChat(ten=f"HcA-{uuid.uuid4().hex[:6]}")
    b = HoatChat(ten=f"HcB-{uuid.uuid4().hex[:6]}")
    db.add_all([a, b])
    await db.flush()
    sp_a, sp_b = await _sp(db), await _sp(db)
    db.add_all([ThanhPhan(san_pham_id=sp_a.id, hoat_chat_id=a.id), ThanhPhan(san_pham_id=sp_b.id, hoat_chat_id=b.id)])
    x, y = sorted((a.id, b.id))
    db.add(TuongTacHoatChat(hoat_chat_a_id=x, hoat_chat_b_id=y, muc_do="chong_chi_dinh", khuyen_cao="Không dùng chung"))
    await db.flush()
    dong = [_dong(sp_a), _dong(sp_b)]
    cb = (await dang_nhap_duoc_si.post(f"{POS}/canh-bao", json={"dong": dong})).json()
    assert cb["can_xac_nhan"] is True and cb["tuong_tac"][0]["muc_do"] == "chong_chi_dinh"
    r = await _gui(dang_nhap_duoc_si, _ban(dong))
    assert r.status_code == 409 and r.json()["ma_loi"] == "CAN_XAC_NHAN_CANH_BAO"
    assert (await db.execute(select(DonHang))).first() is None
    r = await _gui(dang_nhap_duoc_si, _ban(dong, xac_nhan_canh_bao=True))
    assert r.status_code == 201


async def test_gan_khach_theo_sdt_va_canh_bao_di_ung_khong_lo_ho_so(dang_nhap_duoc_si, db):
    from app.models.khach_hang import DiUng

    khach = await tao_khach(db)
    amox = HoatChat(ten=f"Amox-{uuid.uuid4().hex[:6]}")
    db.add(amox)
    await db.flush()
    sp = await _sp(db)
    db.add_all(
        [
            ThanhPhan(san_pham_id=sp.id, hoat_chat_id=amox.id),
            DiUng(khach_hang_id=khach.id, hoat_chat_id=amox.id, ghi_chu="BI-MAT-12"),
        ]
    )
    await db.flush()
    cb = await dang_nhap_duoc_si.post(f"{POS}/canh-bao", json={"dong": [_dong(sp)], "sdt_khach": khach.so_dien_thoai})
    assert cb.json()["di_ung"][0]["ten_hoat_chat"] == amox.ten and "BI-MAT-12" not in cb.text
    r = await _gui(dang_nhap_duoc_si, _ban([_dong(sp)], sdt_khach=khach.so_dien_thoai))
    assert r.status_code == 409  # dị ứng: phải xác nhận
    r = await _gui(dang_nhap_duoc_si, _ban([_dong(sp)], sdt_khach=khach.so_dien_thoai, xac_nhan_canh_bao=True))
    assert r.status_code == 201 and r.json()["hoa_don"]["khach"] == khach.ho_ten
    don = (await db.execute(select(DonHang))).scalars().one()
    assert don.khach_hang_id == khach.id
    chua = await _gui(dang_nhap_duoc_si, _ban([_dong(sp)], sdt_khach="0999999999"))
    assert chua.status_code == 404


async def test_hoa_don_in_lai(dang_nhap_duoc_si, clients_theo_vai_tro, db):
    sp = await _sp(db)
    don_id = (await _gui(dang_nhap_duoc_si, _ban([_dong(sp, "viên", 2)], tien_khach_dua="5000"))).json()["don_id"]
    hd = (await dang_nhap_duoc_si.get(f"{POS}/don/{don_id}/hoa-don")).json()
    assert hd["tong_tien"] == "2000.00" and hd["tien_khach_dua"] is None and hd["nhan_vien"]
    assert (await clients_theo_vai_tro["WAREHOUSE"].get(f"{POS}/don/{don_id}/hoa-don")).status_code == 403
    online = (await db.execute(select(NhanVien))).first()  # chỉ để chắc có dữ liệu
    assert online is not None
    assert (await dang_nhap_duoc_si.get(f"{POS}/don/999999/hoa-don")).status_code == 404

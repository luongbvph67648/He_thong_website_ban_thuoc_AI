"""KHO10: kho nhận hàng khách trả về và kiểm hàng hoàn về kho (T6.2)."""

from sqlalchemy import select

from app.models.ban_hang import CtYeuCauDoiTra, PhanBoLo, ThanhToan, YeuCauDoiTra
from app.models.kho import BienDongKho, LoThuoc
from app.modules.kho import ton_kho
from app.modules.kho.ton_kho import ChungTu, YeuCauGiu
from tests.doi_tra.test_doi_tra import _don_da_giao, _gui

KHO = "/api/v1/noi-bo/nhan-hang"


async def _xuat_hang(db, don, ct, sp):
    """Giữ rồi xuất kho cho dòng đơn, như khi đơn đã qua dòng 16."""
    pb = await ton_kho.giu_hang_nhieu(db, [YeuCauGiu(ct.id, sp.id, ct.so_luong * ct.he_so)])
    ds = [p for v in pb.values() for p in v]
    await ton_kho.xuat_theo_phan_bo(db, ds, ChungTu("don_hang", don.id, None))
    return ds


async def _yeu_cau_da_duyet(dang_nhap_khach, dang_nhap_duoc_si, db, so_luong=3, tra=2):
    don, ct, sp = await _don_da_giao(db, dang_nhap_khach.tai_khoan, so_luong=so_luong)
    pb = await _xuat_hang(db, don, ct, sp)
    ma = (await _gui(dang_nhap_khach, don.ma_don, ct, tra)).json()["ma_yeu_cau"]
    yc = (await db.execute(select(YeuCauDoiTra).where(YeuCauDoiTra.ma_yeu_cau == ma))).scalars().one()
    r = await dang_nhap_duoc_si.post(f"/api/v1/noi-bo/doi-tra/{yc.id}/duyet", json={"huong_xu_ly": "hoan_tien"})
    assert r.status_code == 200, r.text
    return don, ct, sp, yc, pb


async def test_kho_nhan_hang_tra_vao_biet_tru(dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, db):
    don, ct, sp, yc, pb = await _yeu_cau_da_duyet(dang_nhap_khach, dang_nhap_duoc_si, db)
    ds = (await dang_nhap_kho.get(f"{KHO}/doi-tra")).json()
    assert [d["id"] for d in ds] == [yc.id]
    assert "ten_khach" not in ds[0]  # kho không cần thông tin khách
    lo_id = ds[0]["dong"][0]["lo"][0]["lo_id"]
    r = await dang_nhap_kho.post(
        f"{KHO}/doi-tra/{yc.id}",
        json={
            "dong": [{"ct_don_hang_id": ct.id, "lo_id": lo_id, "so_luong_nhan": 2}],
            "ket_qua_kiem_hang": "Đúng mô tả, vỏ vỡ",
        },
    )
    assert r.status_code == 200, r.text
    await db.refresh(yc)
    assert yc.trang_thai == "kho_da_nhan" and yc.ket_qua_kiem_hang == "Đúng mô tả, vỏ vỡ"
    assert yc.nhan_vien_kho_id is not None
    ct_yc = (await db.execute(select(CtYeuCauDoiTra).where(CtYeuCauDoiTra.yeu_cau_id == yc.id))).scalars().one()
    assert (ct_yc.lo_id, ct_yc.so_luong_nhan) == (lo_id, 2)
    lo = await db.get(LoThuoc, lo_id, populate_existing=True)
    assert lo.so_luong_biet_tru == 2
    the = (
        (await db.execute(select(BienDongKho).where(BienDongKho.lo_id == lo_id, BienDongKho.loai == "nhan_tra_ve")))
        .scalars()
        .one()
    )
    assert (the.so_luong, the.khu, the.chung_tu_loai, the.chung_tu_id) == (2, "biet_tru", "yeu_cau_doi_tra", yc.id)
    assert (await dang_nhap_kho.get(f"{KHO}/doi-tra")).json() == []
    again = await dang_nhap_kho.post(
        f"{KHO}/doi-tra/{yc.id}",
        json={"dong": [{"ct_don_hang_id": ct.id, "lo_id": lo_id, "so_luong_nhan": 2}], "ket_qua_kiem_hang": "lần hai"},
    )
    assert again.status_code == 409 and lo.so_luong_biet_tru == 2


async def test_kiem_hang_tra_kiem_tra_dau_vao(dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, db):
    don, ct, sp, yc, pb = await _yeu_cau_da_duyet(dang_nhap_khach, dang_nhap_duoc_si, db)
    lo_id = pb[0].lo_id
    muc = {"ket_qua_kiem_hang": "ok"}
    cac_sai = [
        {"dong": [{"ct_don_hang_id": ct.id, "lo_id": lo_id, "so_luong_nhan": 3}], **muc},  # nhiều hơn khách trả
        {"dong": [{"ct_don_hang_id": ct.id, "so_luong_nhan": 1}], **muc},  # thiếu lô
        {"dong": [{"ct_don_hang_id": ct.id, "lo_id": 999999, "so_luong_nhan": 1}], **muc},  # lô không thuộc dòng
        {"dong": [{"ct_don_hang_id": ct.id + 999, "lo_id": lo_id, "so_luong_nhan": 1}], **muc},  # dòng lạ
        {"dong": [], **muc},
        {"dong": [{"ct_don_hang_id": ct.id, "lo_id": lo_id, "so_luong_nhan": 1}], "ket_qua_kiem_hang": ""},
    ]
    for body in cac_sai:
        assert (await dang_nhap_kho.post(f"{KHO}/doi-tra/{yc.id}", json=body)).status_code in (400, 422), body
    lo = await db.get(LoThuoc, lo_id, populate_existing=True)
    assert lo.so_luong_biet_tru == 0


async def test_kho_khong_nhan_duoc_hang_thi_khong_hoan_tien(dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, db):
    _, ct, _, yc, _ = await _yeu_cau_da_duyet(dang_nhap_khach, dang_nhap_duoc_si, db)
    r = await dang_nhap_kho.post(
        f"{KHO}/doi-tra/{yc.id}",
        json={"dong": [{"ct_don_hang_id": ct.id, "so_luong_nhan": 0}], "ket_qua_kiem_hang": "Không có hàng trong kiện"},
    )
    assert r.status_code == 200
    assert (await dang_nhap_duoc_si.post(f"/api/v1/noi-bo/doi-tra/{yc.id}/hoan-tien")).status_code == 409
    assert (
        await dang_nhap_duoc_si.post(f"/api/v1/noi-bo/doi-tra/{yc.id}/tu-choi", json={"ly_do": "Kho không nhận"})
    ).status_code == 200


async def test_hoan_tien_theo_so_thuc_nhan(dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, db):
    don, ct, sp, yc, pb = await _yeu_cau_da_duyet(dang_nhap_khach, dang_nhap_duoc_si, db, so_luong=3, tra=2)
    r = await dang_nhap_kho.post(
        f"{KHO}/doi-tra/{yc.id}",
        json={
            "dong": [{"ct_don_hang_id": ct.id, "lo_id": pb[0].lo_id, "so_luong_nhan": 1}],
            "ket_qua_kiem_hang": "Chỉ có 1",
        },
    )
    assert r.status_code == 200
    d = (await dang_nhap_duoc_si.post(f"/api/v1/noi-bo/doi-tra/{yc.id}/hoan-tien")).json()
    assert d["so_tien_hoan"] == "10000.00"
    hoan = (await db.execute(select(ThanhToan).where(ThanhToan.yeu_cau_doi_tra_id == yc.id))).scalars().one()
    assert hoan.so_tien == 10000


async def test_chi_nhan_vien_kho_nhan_hang_tra(dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_admin, db):
    _, ct, _, yc, pb = await _yeu_cau_da_duyet(dang_nhap_khach, dang_nhap_duoc_si, db)
    body = {"dong": [{"ct_don_hang_id": ct.id, "lo_id": pb[0].lo_id, "so_luong_nhan": 1}], "ket_qua_kiem_hang": "ok"}
    for c in (dang_nhap_duoc_si, dang_nhap_admin, dang_nhap_khach):
        r = await c.post(f"{KHO}/doi-tra/{yc.id}", json=body)
        assert r.status_code in (401, 403)
    await db.refresh(yc)
    assert yc.trang_thai == "da_duyet"


async def _hoan_ve(dang_nhap_khach, db, tt="da_thanh_toan", cong="vnpay"):
    don, ct, sp = await _don_da_giao(db, dang_nhap_khach.tai_khoan, so_luong=2, tt=tt, cong=cong)
    pb = await _xuat_hang(db, don, ct, sp)
    don.trang_thai = "hoan_ve_kho"
    await db.flush()
    return don, ct, pb


async def test_hang_hoan_nguyen_niem_phong_hoan_nhap_dung_lo(dang_nhap_khach, dang_nhap_kho, db):
    don, ct, pb = await _hoan_ve(dang_nhap_khach, db)
    ds = (await dang_nhap_kho.get(f"{KHO}/hoan-ve")).json()
    assert [d["ma_don"] for d in ds] == [don.ma_don] and ds[0]["da_thanh_toan"] is True
    ton_truoc = (await db.get(LoThuoc, pb[0].lo_id, populate_existing=True)).so_luong_ton
    r = await dang_nhap_kho.post(
        f"{KHO}/hoan-ve/{don.id}", json={"dong": [{"ct_don_hang_id": ct.id, "tinh_trang": "nguyen_niem_phong"}]}
    )
    assert r.status_code == 200, r.text
    kq = r.json()
    assert kq["trang_thai"] == "da_huy" and kq["cho_hoan_tien"] is True and kq["so_luong_hoan_nhap"] == 2
    lo = await db.get(LoThuoc, pb[0].lo_id, populate_existing=True)
    assert lo.so_luong_ton == ton_truoc + 2 and lo.so_luong_biet_tru == 0
    p = await db.get(PhanBoLo, pb[0].id, populate_existing=True)
    assert p.trang_thai == "da_hoan_nhap"
    hoan = (
        (await db.execute(select(ThanhToan).where(ThanhToan.don_hang_id == don.id, ThanhToan.loai == "hoan_tien")))
        .scalars()
        .one()
    )
    assert hoan.trang_thai == "khoi_tao" and hoan.so_tien == don.tong_tien
    assert (await dang_nhap_kho.get(f"{KHO}/hoan-ve")).json() == []


async def test_hang_hoan_hu_hong_vao_biet_tru_va_don_cod_chua_thu_khong_hoan(dang_nhap_khach, dang_nhap_kho, db):
    don, ct, pb = await _hoan_ve(dang_nhap_khach, db, tt="chua_thanh_toan")
    ton_truoc = (await db.get(LoThuoc, pb[0].lo_id, populate_existing=True)).so_luong_ton
    r = await dang_nhap_kho.post(
        f"{KHO}/hoan-ve/{don.id}", json={"dong": [{"ct_don_hang_id": ct.id, "tinh_trang": "hu_hong"}]}
    )
    assert r.status_code == 200, r.text
    assert r.json()["cho_hoan_tien"] is False and r.json()["so_luong_biet_tru"] == 2
    lo = await db.get(LoThuoc, pb[0].lo_id, populate_existing=True)
    assert lo.so_luong_ton == ton_truoc and lo.so_luong_biet_tru == 2
    assert (
        await dang_nhap_kho.post(
            f"{KHO}/hoan-ve/{don.id}", json={"dong": [{"ct_don_hang_id": ct.id, "tinh_trang": "hu_hong"}]}
        )
    ).status_code == 409


async def test_kiem_hoan_ve_dau_vao_sai(dang_nhap_khach, dang_nhap_kho, dang_nhap_duoc_si, db):
    don, ct, _ = await _hoan_ve(dang_nhap_khach, db)
    url = f"{KHO}/hoan-ve/{don.id}"
    assert (
        await dang_nhap_kho.post(url, json={"dong": [{"ct_don_hang_id": ct.id, "tinh_trang": "la"}]})
    ).status_code == 400
    assert (
        await dang_nhap_kho.post(url, json={"dong": [{"ct_don_hang_id": ct.id + 99, "tinh_trang": "hu_hong"}]})
    ).status_code == 400
    assert (
        await dang_nhap_duoc_si.post(url, json={"dong": [{"ct_don_hang_id": ct.id, "tinh_trang": "hu_hong"}]})
    ).status_code in (401, 403)
    assert (
        await dang_nhap_kho.post(
            f"{KHO}/hoan-ve/999999", json={"dong": [{"ct_don_hang_id": 1, "tinh_trang": "hu_hong"}]}
        )
    ).status_code == 404
    await db.refresh(don)
    assert don.trang_thai == "hoan_ve_kho"


async def test_kho_khong_xem_yeu_cau_chua_duyet_va_khong_nhan_qua_so_da_xuat_cua_lo(
    dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, db
):
    don, ct, sp = await _don_da_giao(db, dang_nhap_khach.tai_khoan, so_luong=3)
    pb = await _xuat_hang(db, don, ct, sp)
    ma = (await _gui(dang_nhap_khach, don.ma_don, ct, 2)).json()["ma_yeu_cau"]
    yc = (await db.execute(select(YeuCauDoiTra).where(YeuCauDoiTra.ma_yeu_cau == ma))).scalars().one()
    body = {"dong": [{"ct_don_hang_id": ct.id, "so_luong_nhan": 0}], "ket_qua_kiem_hang": "chưa duyệt"}
    assert (await dang_nhap_kho.post(f"{KHO}/doi-tra/{yc.id}", json=body)).status_code == 409  # còn chờ duyệt
    await dang_nhap_duoc_si.post(f"/api/v1/noi-bo/doi-tra/{yc.id}/duyet", json={"huong_xu_ly": "hoan_tien"})
    # Đơn có hai lô: nhận nhiều hơn số đã xuất của lô được chọn là sai
    ct.he_so = 1
    pb[0].so_luong_co_so = 1
    await db.flush()
    r = await dang_nhap_kho.post(
        f"{KHO}/doi-tra/{yc.id}",
        json={"dong": [{"ct_don_hang_id": ct.id, "lo_id": pb[0].lo_id, "so_luong_nhan": 2}], "ket_qua_kiem_hang": "ok"},
    )
    assert r.status_code == 400


async def test_doi_tra_don_thay_the_bi_chan_va_huy_don_thay_the_khong_loi(dang_nhap_khach, dang_nhap_duoc_si, db):
    from app.models.ban_hang import DonHang
    from app.modules.ban_hang.trang_thai import NGUON_NGUOI_DUNG, TacNhan, chuyen_trang_thai

    don, ct, _ = await _don_da_giao(db, dang_nhap_khach.tai_khoan)
    don.don_hang_goc_id = don.id  # giả lập đơn thay thế: trỏ về một đơn gốc, tổng 0
    await db.flush()
    r = await _gui(dang_nhap_khach, don.ma_don, ct, 1)
    assert r.status_code == 409
    # Hủy đơn 0đ đã "thanh toán" không tạo giao dịch hoàn bằng 0 (CHECK so_tien > 0)
    don.tong_tien, don.trang_thai, don.trang_thai_tt, don.phuong_thuc_tt = 0, "da_xac_nhan", "da_thanh_toan", "cod"
    don.tam_tinh = don.giam_gia = don.phi_van_chuyen = 0
    await db.flush()
    await chuyen_trang_thai(
        db,
        await db.get(DonHang, don.id),
        "da_huy",
        TacNhan.duoc_si(dang_nhap_duoc_si.tai_khoan.id),
        NGUON_NGUOI_DUNG,
        "Hủy thử",
    )
    assert (
        await db.execute(select(ThanhToan).where(ThanhToan.don_hang_id == don.id, ThanhToan.loai == "hoan_tien"))
    ).first() is None

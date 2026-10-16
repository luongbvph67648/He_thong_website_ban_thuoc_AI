"""KTV09, DS09: yêu cầu đổi trả, duyệt, hoàn tiền, hàng thay thế (T6.1)."""

import json
from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core import luu_tru
from app.core.thoi_gian import bay_gio_utc
from app.models.ban_hang import CtDonHang, CtYeuCauDoiTra, DonHang, ThanhToan, VanDon, YeuCauDoiTra
from app.models.khach_hang import ThongBao
from app.models.kho import LoThuoc
from tests.conftest import _dang_nhap
from tests.factories import tao_khach, tao_lo, tao_san_pham

DON_VI = [{"ten_don_vi": "hộp", "he_so": 1, "gia_ban": 10000, "la_mac_dinh": True}]
PNG = b"\x89PNG\r\n\x1a\n" + b"bang-chung" * 20
MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64


async def _don_da_giao(db, khach, so_luong=3, phi=15000, tt="da_thanh_toan", cong="cod", **kw):
    sp = await tao_san_pham(db, "thuoc_khong_ke_don", don_vi=DON_VI)
    await tao_lo(db, sp, so_luong=100)
    from tests.factories import tao_don

    don = await tao_don(
        db, khach, "da_giao", [{"san_pham": sp, "so_luong": so_luong}], phi_van_chuyen=phi, trang_thai_tt=tt,
        hinh_thuc_nhan="giao_tan_noi", ten_nguoi_nhan="A", sdt_nguoi_nhan="0912345678", dia_chi_giao="1 Phố A", **kw,
    )  # fmt: skip
    if tt == "da_thanh_toan":
        db.add(
            ThanhToan(
                don_hang_id=don.id,
                loai="thanh_toan",
                cong_thanh_toan=cong,
                so_tien=don.tong_tien,
                trang_thai="thanh_cong",
            )
        )
    await db.flush()
    ct = (await db.execute(select(CtDonHang).where(CtDonHang.don_hang_id == don.id))).scalars().one()
    return don, ct, sp


async def _gui(c, ma_don, ct, so_luong=1, tep=None, ly_do="hu_hong", **kw):
    tep = tep if tep is not None else [("tep", ("a.png", PNG, "image/png"))]
    return await c.post(
        f"/api/v1/toi/don-hang/{ma_don}/doi-tra",
        data={"dong": json.dumps([{"ct_don_hang_id": ct.id, "so_luong": so_luong}]), "ly_do": ly_do, **kw},
        files=tep or None,
    )


async def test_khach_gui_yeu_cau_voi_anh_va_video(dang_nhap_khach, db):
    don, ct, _ = await _don_da_giao(db, dang_nhap_khach.tai_khoan)
    r = await _gui(
        dang_nhap_khach,
        don.ma_don,
        ct,
        2,
        tep=[("tep", ("a.png", PNG, "image/png")), ("tep", ("v.mp4", MP4, "video/mp4"))],
        mo_ta="vỡ vỉ",
    )
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["trang_thai"] == "cho_duyet" and d["ma_yeu_cau"].startswith("DT") and d["ma_don"] == don.ma_don
    assert [(x["so_luong_tra"], x["so_luong_mua"]) for x in d["dong"]] == [(2, 3)] and d["dong"][0][
        "thanh_tien"
    ] == "20000.00"
    assert len(d["anh"]) == 2 and d["can_nhap_tai_khoan_hoan"] is False and d["ma_van_don"] is None
    yc = (await db.execute(select(YeuCauDoiTra))).scalars().one()
    assert yc.khach_hang_id == dang_nhap_khach.tai_khoan.id and yc.mo_ta == "vỡ vỉ" and len(yc.anh) == 2
    assert yc.anh[0].startswith("doi-tra/") and yc.anh[1].endswith(".mp4")
    assert await luu_tru.luu_tru().doc(yc.anh[1], "rieng_tu") == MP4
    anh = await dang_nhap_khach.get(d["anh"][1], headers={"Authorization": ""})
    assert anh.status_code == 200 and anh.headers["content-type"] == "video/mp4"


async def test_chi_doi_tra_don_da_giao_trong_han(dang_nhap_khach, db):
    khach = dang_nhap_khach.tai_khoan
    don, ct, _ = await _don_da_giao(db, khach)
    don.trang_thai = "dang_giao"
    await db.flush()
    r = await _gui(dang_nhap_khach, don.ma_don, ct)
    assert r.status_code == 409 and r.json()["ma_loi"] == "CHUYEN_TRANG_THAI_KHONG_HOP_LE"
    cu, ct2, _ = await _don_da_giao(db, khach, created_at=bay_gio_utc() - timedelta(days=30))
    r = await _gui(dang_nhap_khach, cu.ma_don, ct2)
    assert r.status_code == 422 and r.json()["ma_loi"] == "QUA_THOI_HAN_DOI_TRA"


async def test_so_luong_tra_khong_vuot_da_mua_cong_don_cac_yeu_cau(dang_nhap_khach, db):
    don, ct, _ = await _don_da_giao(db, dang_nhap_khach.tai_khoan, so_luong=3)
    assert (await _gui(dang_nhap_khach, don.ma_don, ct, 4)).status_code == 422
    a = await _gui(dang_nhap_khach, don.ma_don, ct, 2)
    assert a.status_code == 201
    r = await _gui(dang_nhap_khach, don.ma_don, ct, 2)
    assert r.status_code == 422 and r.json()["ma_loi"] == "HOAN_VUOT_SO_DA_TRA" and r.json()["chi_tiet"]["con_lai"] == 1
    assert (await _gui(dang_nhap_khach, don.ma_don, ct, 1)).status_code == 201
    # Yêu cầu bị từ chối trả lại số lượng.
    yc = (
        (await db.execute(select(YeuCauDoiTra).where(YeuCauDoiTra.ma_yeu_cau == a.json()["ma_yeu_cau"])))
        .scalars()
        .one()
    )
    yc.trang_thai = "tu_choi"
    await db.flush()
    assert (await _gui(dang_nhap_khach, don.ma_don, ct, 2)).status_code == 201


async def test_don_nguoi_khac_dong_la_va_tep_sai(dang_nhap_khach, app, db):
    don, ct, _ = await _don_da_giao(db, dang_nhap_khach.tai_khoan)
    khac_don, khac_ct, _ = await _don_da_giao(db, dang_nhap_khach.tai_khoan)
    r = await dang_nhap_khach.post(
        f"/api/v1/toi/don-hang/{don.ma_don}/doi-tra",
        data={"dong": json.dumps([{"ct_don_hang_id": khac_ct.id, "so_luong": 1}]), "ly_do": "hu_hong"},
        files=[("tep", ("a.png", PNG, "image/png"))],
    )
    assert r.status_code == 400
    assert (
        await _gui(dang_nhap_khach, don.ma_don, ct, tep=[("tep", ("x.png", b"khong-phai-anh" * 4, "image/png"))])
    ).status_code == 400
    assert (
        await _gui(dang_nhap_khach, don.ma_don, ct, tep=[("tep", ("a.png", PNG, "image/png"))] * 9)
    ).status_code == 400
    assert (await _gui(dang_nhap_khach, don.ma_don, ct, ly_do="khong-co")).status_code == 400
    bad = await dang_nhap_khach.post(
        f"/api/v1/toi/don-hang/{don.ma_don}/doi-tra",
        data={"dong": "khong-phai-json", "ly_do": "hu_hong"},
        files=[("tep", ("a.png", PNG, "image/png"))],
    )
    assert bad.status_code == 400
    async for khac in _dang_nhap(app, await tao_khach(db), "khach"):
        assert (await _gui(khac, don.ma_don, ct)).status_code == 404
    ok = await _gui(dang_nhap_khach, don.ma_don, ct)
    async for khac in _dang_nhap(app, await tao_khach(db), "khach"):
        assert (await khac.get("/api/v1/toi/doi-tra")).json() == []
        assert (await khac.get(f"/api/v1/toi/doi-tra/{ok.json()['ma_yeu_cau']}")).status_code == 404


async def _xin(dang_nhap_khach, db, **kw):
    don, ct, sp = await _don_da_giao(db, dang_nhap_khach.tai_khoan, **kw)
    return don, ct, sp


async def test_duoc_si_duyet_hoan_tien_tao_van_don_va_tinh_tien(dang_nhap_khach, dang_nhap_duoc_si, db):
    don, ct, _ = await _xin(dang_nhap_khach, db, so_luong=3, phi=15000)
    ma = (await _gui(dang_nhap_khach, don.ma_don, ct, 1)).json()["ma_yeu_cau"]
    yc = (await db.execute(select(YeuCauDoiTra).where(YeuCauDoiTra.ma_yeu_cau == ma))).scalars().one()
    r = await dang_nhap_duoc_si.post(f"/api/v1/noi-bo/doi-tra/{yc.id}/duyet", json={"huong_xu_ly": "hoan_tien"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["trang_thai"] == "da_duyet" and d["so_tien_hoan"] == "10000.00" and d["ma_van_don"].startswith("GIA")
    vd = (await db.execute(select(VanDon).where(VanDon.yeu_cau_doi_tra_id == yc.id))).scalars().one()
    assert vd.loai == "tra_hang" and vd.don_hang_id == don.id
    tb = (
        (await db.execute(select(ThongBao).where(ThongBao.khach_hang_id == dang_nhap_khach.tai_khoan.id)))
        .scalars()
        .all()
    )
    assert tb and tb[-1].loai == "doi_tra" and d["ma_van_don"] in (tb[-1].noi_dung or "")
    kh = (await dang_nhap_khach.get(f"/api/v1/toi/doi-tra/{ma}")).json()
    assert kh["ma_van_don"] == d["ma_van_don"] and kh["trang_thai"] == "da_duyet"
    assert (
        await dang_nhap_duoc_si.post(f"/api/v1/noi-bo/doi-tra/{yc.id}/duyet", json={"huong_xu_ly": "hoan_tien"})
    ).status_code == 409


async def test_tra_toan_bo_don_hoan_them_phi_van_chuyen(dang_nhap_khach, dang_nhap_duoc_si, db):
    don, ct, _ = await _xin(dang_nhap_khach, db, so_luong=2, phi=15000)
    ma = (await _gui(dang_nhap_khach, don.ma_don, ct, 2)).json()["ma_yeu_cau"]
    yc = (await db.execute(select(YeuCauDoiTra).where(YeuCauDoiTra.ma_yeu_cau == ma))).scalars().one()
    d = (
        await dang_nhap_duoc_si.post(f"/api/v1/noi-bo/doi-tra/{yc.id}/duyet", json={"huong_xu_ly": "hoan_tien"})
    ).json()
    assert d["so_tien_hoan"] == "35000.00"  # 2 x 10.000 + phí ship 15.000
    assert d["tong_da_thanh_toan"] == "35000.00"


async def test_lam_tron_tung_dong_khi_tra_mot_phan(dang_nhap_khach, dang_nhap_duoc_si, db):
    don, ct, _ = await _xin(dang_nhap_khach, db, so_luong=3, phi=0)
    ct.giam_gia_phan_bo = Decimal("20000")  # 3 hộp còn 10.000 sau giảm giá: 1/3 -> 3.333
    ct.thanh_tien = Decimal("10000")
    await db.flush()
    ma = (await _gui(dang_nhap_khach, don.ma_don, ct, 1)).json()["ma_yeu_cau"]
    yc = (await db.execute(select(YeuCauDoiTra).where(YeuCauDoiTra.ma_yeu_cau == ma))).scalars().one()
    d = (
        await dang_nhap_duoc_si.post(f"/api/v1/noi-bo/doi-tra/{yc.id}/duyet", json={"huong_xu_ly": "gui_hang_thay_the"})
    ).json()
    assert d["so_tien_hoan"] == "0.00"
    yc2 = (await _gui(dang_nhap_khach, don.ma_don, ct, 1)).json()["ma_yeu_cau"]
    y2 = (await db.execute(select(YeuCauDoiTra).where(YeuCauDoiTra.ma_yeu_cau == yc2))).scalars().one()
    don.giam_gia, don.tong_tien = Decimal("20000"), Decimal("10000")
    await db.flush()
    d2 = (
        await dang_nhap_duoc_si.post(f"/api/v1/noi-bo/doi-tra/{y2.id}/duyet", json={"huong_xu_ly": "hoan_tien"})
    ).json()
    assert d2["so_tien_hoan"] == "3333.00"


async def test_chua_thanh_toan_khong_chon_hoan_tien(dang_nhap_khach, dang_nhap_duoc_si, db):
    don, ct, _ = await _xin(dang_nhap_khach, db, tt="chua_thanh_toan")
    ma = (await _gui(dang_nhap_khach, don.ma_don, ct)).json()["ma_yeu_cau"]
    yc = (await db.execute(select(YeuCauDoiTra).where(YeuCauDoiTra.ma_yeu_cau == ma))).scalars().one()
    r = await dang_nhap_duoc_si.post(f"/api/v1/noi-bo/doi-tra/{yc.id}/duyet", json={"huong_xu_ly": "hoan_tien"})
    assert r.status_code == 400
    assert (
        await dang_nhap_duoc_si.post(f"/api/v1/noi-bo/doi-tra/{yc.id}/duyet", json={"huong_xu_ly": "gui_hang_thay_the"})
    ).status_code == 200


async def test_tu_choi_can_ly_do_va_kiem_hang(dang_nhap_khach, dang_nhap_duoc_si, db):
    don, ct, _ = await _xin(dang_nhap_khach, db)
    ma = (await _gui(dang_nhap_khach, don.ma_don, ct)).json()["ma_yeu_cau"]
    yc = (await db.execute(select(YeuCauDoiTra).where(YeuCauDoiTra.ma_yeu_cau == ma))).scalars().one()
    url = f"/api/v1/noi-bo/doi-tra/{yc.id}/tu-choi"
    assert (await dang_nhap_duoc_si.post(url, json={"ly_do": ""})).status_code == 400
    r = await dang_nhap_duoc_si.post(url, json={"ly_do": "Không đúng mô tả"})
    assert (
        r.status_code == 200 and r.json()["trang_thai"] == "tu_choi" and r.json()["ly_do_tu_choi"] == "Không đúng mô tả"
    )
    assert (await dang_nhap_duoc_si.post(url, json={"ly_do": "Lại từ chối"})).status_code == 409
    # Từ chối sau khi kho nhận phải có kết quả kiểm của kho.
    don2, ct2, _ = await _xin(dang_nhap_khach, db)
    ma2 = (await _gui(dang_nhap_khach, don2.ma_don, ct2)).json()["ma_yeu_cau"]
    y2 = (await db.execute(select(YeuCauDoiTra).where(YeuCauDoiTra.ma_yeu_cau == ma2))).scalars().one()
    y2.trang_thai = "kho_da_nhan"
    await db.flush()
    assert (
        await dang_nhap_duoc_si.post(f"/api/v1/noi-bo/doi-tra/{y2.id}/tu-choi", json={"ly_do": "Hàng đã dùng"})
    ).status_code == 400
    y2.ket_qua_kiem_hang = "Hộp đã bóc, thiếu 2 viên"
    await db.flush()
    assert (
        await dang_nhap_duoc_si.post(f"/api/v1/noi-bo/doi-tra/{y2.id}/tu-choi", json={"ly_do": "Hàng đã dùng"})
    ).status_code == 200


async def _kho_da_nhan(db, ma, huong):
    yc = (await db.execute(select(YeuCauDoiTra).where(YeuCauDoiTra.ma_yeu_cau == ma))).scalars().one()
    yc.trang_thai, yc.huong_xu_ly = "kho_da_nhan", huong
    for r in (await db.execute(select(CtYeuCauDoiTra).where(CtYeuCauDoiTra.yeu_cau_id == yc.id))).scalars():
        r.so_luong_nhan = r.so_luong  # kho nhận đủ (T6.2 làm bước này thật)
    await db.flush()
    return yc


async def test_tao_hoan_tien_va_khach_nhap_tai_khoan(dang_nhap_khach, dang_nhap_duoc_si, db):
    khach = dang_nhap_khach.tai_khoan
    don, ct, _ = await _xin(dang_nhap_khach, db, so_luong=3, phi=0)
    ma = (await _gui(dang_nhap_khach, don.ma_don, ct, 1)).json()["ma_yeu_cau"]
    yc = await _kho_da_nhan(db, ma, "hoan_tien")
    tk = {"ngan_hang": "Vietcombank", "so_tai_khoan": "0123456789", "chu_tai_khoan": "NGUYEN VAN A"}
    # Chưa có giao dịch hoàn thì khách chưa nhập được.
    assert (await dang_nhap_khach.put(f"/api/v1/toi/doi-tra/{ma}/tai-khoan-nhan-hoan", json=tk)).status_code == 409
    r = await dang_nhap_duoc_si.post(f"/api/v1/noi-bo/doi-tra/{yc.id}/hoan-tien")
    assert r.status_code == 200, r.text
    assert r.json()["da_co_giao_dich_hoan"] is True and r.json()["can_nhap_tai_khoan_hoan"] is True
    hoan = (await db.execute(select(ThanhToan).where(ThanhToan.yeu_cau_doi_tra_id == yc.id))).scalars().one()
    goc = (
        (await db.execute(select(ThanhToan).where(ThanhToan.loai == "thanh_toan", ThanhToan.don_hang_id == don.id)))
        .scalars()
        .one()
    )
    assert (hoan.loai, hoan.trang_thai, hoan.so_tien, hoan.thanh_toan_goc_id) == (
        "hoan_tien",
        "khoi_tao",
        10000,
        goc.id,
    )
    await db.refresh(don)
    assert don.trang_thai_tt == "cho_hoan_tien"
    assert (await dang_nhap_duoc_si.post(f"/api/v1/noi-bo/doi-tra/{yc.id}/hoan-tien")).status_code == 409
    sai = await dang_nhap_khach.put(
        f"/api/v1/toi/doi-tra/{ma}/tai-khoan-nhan-hoan", json={**tk, "so_tai_khoan": "12 34"}
    )
    assert sai.status_code == 400
    ok = await dang_nhap_khach.put(f"/api/v1/toi/doi-tra/{ma}/tai-khoan-nhan-hoan", json=tk)
    assert ok.status_code == 200 and ok.json()["da_nhap_tai_khoan_hoan"] is True
    await db.refresh(hoan)
    assert hoan.thong_tin_nhan_hoan == tk
    # Phản hồi khách và dược sĩ không lộ số tài khoản.
    assert "0123456789" not in ok.text
    assert "0123456789" not in (await dang_nhap_duoc_si.get(f"/api/v1/noi-bo/doi-tra/{yc.id}")).text
    assert khach.id == yc.khach_hang_id


async def test_don_online_khong_can_tai_khoan_nhan_hoan(dang_nhap_khach, dang_nhap_duoc_si, db):
    don, ct, _ = await _xin(dang_nhap_khach, db, cong="vnpay", phuong_thuc_tt="vnpay")
    ma = (await _gui(dang_nhap_khach, don.ma_don, ct)).json()["ma_yeu_cau"]
    yc = await _kho_da_nhan(db, ma, "hoan_tien")
    r = await dang_nhap_duoc_si.post(f"/api/v1/noi-bo/doi-tra/{yc.id}/hoan-tien")
    assert r.status_code == 200 and r.json()["can_nhap_tai_khoan_hoan"] is False
    tk = {"ngan_hang": "VCB", "so_tai_khoan": "0123456789", "chu_tai_khoan": "A"}
    assert (await dang_nhap_khach.put(f"/api/v1/toi/doi-tra/{ma}/tai-khoan-nhan-hoan", json=tk)).status_code == 409


async def test_tong_hoan_khong_vuot_da_thanh_toan(dang_nhap_khach, dang_nhap_duoc_si, db):
    don, ct, _ = await _xin(dang_nhap_khach, db, so_luong=3, phi=0)
    ma = (await _gui(dang_nhap_khach, don.ma_don, ct, 1)).json()["ma_yeu_cau"]
    yc = await _kho_da_nhan(db, ma, "hoan_tien")
    db.add(
        ThanhToan(don_hang_id=don.id, loai="hoan_tien", cong_thanh_toan="cod", so_tien=25000, trang_thai="thanh_cong")
    )
    await db.flush()
    r = await dang_nhap_duoc_si.post(f"/api/v1/noi-bo/doi-tra/{yc.id}/hoan-tien")
    assert r.status_code == 422 and r.json()["ma_loi"] == "HOAN_VUOT_SO_DA_TRA"


async def test_gui_hang_thay_the_tao_don_0d(dang_nhap_khach, dang_nhap_duoc_si, db):
    don, ct, sp = await _xin(dang_nhap_khach, db, so_luong=3)
    ma = (await _gui(dang_nhap_khach, don.ma_don, ct, 2)).json()["ma_yeu_cau"]
    yc = await _kho_da_nhan(db, ma, "gui_hang_thay_the")
    r = await dang_nhap_duoc_si.post(f"/api/v1/noi-bo/doi-tra/{yc.id}/thay-the")
    assert r.status_code == 200, r.text
    assert r.json()["trang_thai"] == "hoan_tat"
    moi = (await db.execute(select(DonHang).where(DonHang.don_hang_goc_id == don.id))).scalars().one()
    assert (moi.trang_thai, moi.tong_tien, moi.tam_tinh, moi.khach_hang_id) == ("da_xac_nhan", 0, 0, don.khach_hang_id)
    assert moi.dia_chi_giao == don.dia_chi_giao and moi.nhan_vien_tao_id == dang_nhap_duoc_si.tai_khoan.id
    ct_moi = (await db.execute(select(CtDonHang).where(CtDonHang.don_hang_id == moi.id))).scalars().one()
    assert (ct_moi.so_luong, ct_moi.don_gia, ct_moi.thanh_tien) == (2, 0, 0)
    lo = (await db.execute(select(LoThuoc).where(LoThuoc.san_pham_id == sp.id))).scalars().one()
    assert lo.so_luong_giu == 2
    assert (await dang_nhap_duoc_si.post(f"/api/v1/noi-bo/doi-tra/{yc.id}/thay-the")).status_code == 409


async def test_thay_the_het_hang_hoan_tac(dang_nhap_khach, dang_nhap_duoc_si, db):
    don, ct, sp = await _xin(dang_nhap_khach, db, so_luong=3)
    lo = (await db.execute(select(LoThuoc).where(LoThuoc.san_pham_id == sp.id))).scalars().one()
    lo.so_luong_ton = 1
    await db.flush()
    ma = (await _gui(dang_nhap_khach, don.ma_don, ct, 2)).json()["ma_yeu_cau"]
    yc = await _kho_da_nhan(db, ma, "gui_hang_thay_the")
    r = await dang_nhap_duoc_si.post(f"/api/v1/noi-bo/doi-tra/{yc.id}/thay-the")
    assert r.status_code == 409 and r.json()["ma_loi"] == "HET_HANG"
    await db.refresh(yc)
    assert yc.trang_thai == "kho_da_nhan"
    assert (await db.execute(select(DonHang).where(DonHang.don_hang_goc_id == don.id))).first() is None


async def test_chi_duoc_si_xu_ly_doi_tra(clients_theo_vai_tro, dang_nhap_khach, db):
    don, ct, _ = await _xin(dang_nhap_khach, db)
    await _gui(dang_nhap_khach, don.ma_don, ct)
    yc = (await db.execute(select(YeuCauDoiTra))).scalars().one()
    for vai_tro in ("WAREHOUSE", "ADMIN"):
        c = clients_theo_vai_tro[vai_tro]
        assert (await c.get("/api/v1/noi-bo/doi-tra")).status_code == 403
        assert (
            await c.post(f"/api/v1/noi-bo/doi-tra/{yc.id}/duyet", json={"huong_xu_ly": "hoan_tien"})
        ).status_code == 403


async def test_hang_cho_loc_va_ht08_khong_hoan_tat_khi_con_yeu_cau(dang_nhap_khach, dang_nhap_duoc_si, db):
    from app.jobs.cong_viec import ht08_tu_hoan_tat

    don, ct, _ = await _xin(dang_nhap_khach, db)
    await _gui(dang_nhap_khach, don.ma_don, ct)
    ds = (await dang_nhap_duoc_si.get("/api/v1/noi-bo/doi-tra")).json()
    assert len(ds) == 1 and ds[0]["ma_don"] == don.ma_don and ds[0]["ten_khach"]
    assert (await dang_nhap_duoc_si.get("/api/v1/noi-bo/doi-tra", params={"trang_thai": "tu_choi"})).json() == []
    kq = await ht08_tu_hoan_tat(db)
    assert don.ma_don not in kq.hoan_tat
    assert pytest is not None and CtYeuCauDoiTra is not None

"""AD17: Admin xác nhận hoàn tiền (T6.3)."""

from decimal import Decimal

from sqlalchemy import select

from app.core import luu_tru
from app.models.ban_hang import CtYeuCauDoiTra, ThanhToan, YeuCauDoiTra
from app.models.khach_hang import ThongBao
from tests.doi_tra.test_doi_tra import PNG, _don_da_giao
from tests.doi_tra.test_doi_tra import _gui as gui_doi_tra

HT = "/api/v1/noi-bo/hoan-tien"


async def _goc_va_hoan(db, khach, cong="vnpay", tt="da_thanh_toan", **kw):
    don, ct, sp = await _don_da_giao(db, khach, so_luong=2, tt="chua_thanh_toan", **kw)
    goc = ThanhToan(
        don_hang_id=don.id, loai="thanh_toan", cong_thanh_toan=cong, so_tien=don.tong_tien, trang_thai="thanh_cong",
        ma_giao_dich_cong=f"TX{don.id}",
    )  # fmt: skip
    db.add(goc)
    don.trang_thai_tt = "cho_hoan_tien"
    await db.flush()
    hoan = ThanhToan(
        don_hang_id=don.id, loai="hoan_tien", cong_thanh_toan=cong, so_tien=don.tong_tien, trang_thai="khoi_tao",
        thanh_toan_goc_id=goc.id, ghi_chu="Hoàn tiền do hủy đơn",
    )  # fmt: skip
    db.add(hoan)
    await db.flush()
    return don, ct, goc, hoan


async def test_danh_sach_hoan_tien_cho_xu_ly(dang_nhap_khach, dang_nhap_admin, db):
    don, _, _, hoan = await _goc_va_hoan(db, dang_nhap_khach.tai_khoan)
    ds = (await dang_nhap_admin.get(HT)).json()
    assert [d["id"] for d in ds] == [hoan.id]
    d = ds[0]
    assert d["ma_don"] == don.ma_don and d["nguon"] == "huy_don" and d["tu_dong_qua_cong"] is True
    assert Decimal(d["so_tien"]) == don.tong_tien and d["trang_thai"] == "khoi_tao" and d["thieu_tai_khoan"] is False
    assert (await dang_nhap_admin.get(HT, params={"trang_thai": "thanh_cong"})).json() == []


async def test_hoan_qua_cong_vnpay_cap_nhat_don_va_bao_khach(dang_nhap_khach, dang_nhap_admin, db):
    khach = dang_nhap_khach.tai_khoan
    don, _, _, hoan = await _goc_va_hoan(db, khach)
    r = await dang_nhap_admin.post(f"{HT}/{hoan.id}/xac-nhan")
    assert r.status_code == 200, r.text
    assert r.json()["trang_thai"] == "thanh_cong"
    await db.refresh(hoan)
    await db.refresh(don)
    assert hoan.trang_thai == "thanh_cong" and hoan.ma_giao_dich_cong.startswith("GIA-HOAN-")
    assert hoan.nhan_vien_xu_ly_id == dang_nhap_admin.tai_khoan.id
    assert don.trang_thai_tt == "da_hoan_tien"
    tb = (await db.execute(select(ThongBao).where(ThongBao.khach_hang_id == khach.id))).scalars().all()
    assert tb and tb[-1].loai == "hoan_tien"
    again = await dang_nhap_admin.post(f"{HT}/{hoan.id}/xac-nhan")
    assert again.status_code == 409


async def test_hoan_mot_phan_va_con_giao_dich_khac_cho(dang_nhap_khach, dang_nhap_admin, db):
    don, _, goc, hoan = await _goc_va_hoan(db, dang_nhap_khach.tai_khoan)
    hoan.so_tien = Decimal("10000")
    hai = ThanhToan(
        don_hang_id=don.id, loai="hoan_tien", cong_thanh_toan="vnpay", so_tien=Decimal("5000"), trang_thai="khoi_tao",
        thanh_toan_goc_id=goc.id,
    )  # fmt: skip
    db.add(hai)
    await db.flush()
    assert (await dang_nhap_admin.post(f"{HT}/{hoan.id}/xac-nhan")).status_code == 200
    await db.refresh(don)
    assert don.trang_thai_tt == "cho_hoan_tien"  # còn một giao dịch hoàn đang chờ
    assert (await dang_nhap_admin.post(f"{HT}/{hai.id}/xac-nhan")).status_code == 200
    await db.refresh(don)
    assert don.trang_thai_tt == "hoan_tien_mot_phan"  # 15.000 / 20.000 + phí ship


async def test_hoan_thu_cong_can_chung_tu_va_an_danh_tai_khoan(dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_admin, db):
    khach = dang_nhap_khach.tai_khoan
    don, ct, goc, _ = await _goc_va_hoan(db, khach, cong="cod")
    # giao dịch hoàn do hủy ban đầu của _goc_va_hoan không thuộc yêu cầu: đóng nó để chỉ còn hoàn đổi trả
    for t in (await db.execute(select(ThanhToan).where(ThanhToan.loai == "hoan_tien"))).scalars():
        t.trang_thai = "that_bai"
    don.trang_thai_tt = "da_thanh_toan"
    await db.flush()
    ma = (await gui_doi_tra(dang_nhap_khach, don.ma_don, ct, 1)).json()["ma_yeu_cau"]
    yc = (await db.execute(select(YeuCauDoiTra).where(YeuCauDoiTra.ma_yeu_cau == ma))).scalars().one()
    await dang_nhap_duoc_si.post(f"/api/v1/noi-bo/doi-tra/{yc.id}/duyet", json={"huong_xu_ly": "hoan_tien"})
    for r in (await db.execute(select(CtYeuCauDoiTra).where(CtYeuCauDoiTra.yeu_cau_id == yc.id))).scalars():
        r.so_luong_nhan = r.so_luong
    yc.trang_thai = "kho_da_nhan"
    await db.flush()
    assert (await dang_nhap_duoc_si.post(f"/api/v1/noi-bo/doi-tra/{yc.id}/hoan-tien")).status_code == 200
    hoan = (await db.execute(select(ThanhToan).where(ThanhToan.yeu_cau_doi_tra_id == yc.id))).scalars().one()
    ds = (await dang_nhap_admin.get(HT)).json()
    assert ds[0]["nguon"] == "doi_tra" and ds[0]["tu_dong_qua_cong"] is False and ds[0]["thieu_tai_khoan"] is True
    # Thiếu tài khoản và thiếu chứng từ đều chưa xác nhận được
    r = await dang_nhap_admin.post(f"{HT}/{hoan.id}/xac-nhan")
    assert r.status_code == 400 and r.json()["chi_tiet"][0]["truong"] == "chung_tu"
    chung_tu = {"chung_tu": ("ct.png", PNG, "image/png")}
    assert (await dang_nhap_admin.post(f"{HT}/{hoan.id}/xac-nhan", files=chung_tu)).status_code == 409
    tk = {"ngan_hang": "Vietcombank", "so_tai_khoan": "0123456789", "chu_tai_khoan": "NGUYEN VAN A"}
    assert (await dang_nhap_khach.put(f"/api/v1/toi/doi-tra/{ma}/tai-khoan-nhan-hoan", json=tk)).status_code == 200
    ds = (await dang_nhap_admin.get(HT)).json()
    assert ds[0]["thong_tin_nhan_hoan"]["so_tai_khoan"] == "0123456789"
    # Chứng từ sai kiểu bị từ chối
    xau = await dang_nhap_admin.post(
        f"{HT}/{hoan.id}/xac-nhan", files={"chung_tu": ("x.png", b"khong-phai-anh" * 4, "image/png")}
    )
    assert xau.status_code == 400
    r = await dang_nhap_admin.post(f"{HT}/{hoan.id}/xac-nhan", files=chung_tu)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["trang_thai"] == "thanh_cong" and d["chung_tu"]
    assert d["thong_tin_nhan_hoan"] == {"ngan_hang": "Vietcombank", "so_tai_khoan": "****6789", "da_an_danh": True}
    await db.refresh(hoan)
    await db.refresh(yc)
    await db.refresh(don)
    assert "NGUYEN" not in str(hoan.thong_tin_nhan_hoan) and "0123456789" not in str(hoan.thong_tin_nhan_hoan)
    assert await luu_tru.luu_tru().doc(hoan.chung_tu_url, "rieng_tu") == PNG
    assert yc.trang_thai == "hoan_tat"
    assert don.trang_thai_tt == "hoan_tien_mot_phan"


async def test_nguoi_duyet_doi_tra_khong_tu_xac_nhan_hoan(dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_admin, db):
    khach = dang_nhap_khach.tai_khoan
    don, ct, goc, _ = await _goc_va_hoan(db, khach)
    for t in (await db.execute(select(ThanhToan).where(ThanhToan.loai == "hoan_tien"))).scalars():
        t.trang_thai = "that_bai"
    don.trang_thai_tt = "da_thanh_toan"
    await db.flush()
    ma = (await gui_doi_tra(dang_nhap_khach, don.ma_don, ct, 1)).json()["ma_yeu_cau"]
    yc = (await db.execute(select(YeuCauDoiTra).where(YeuCauDoiTra.ma_yeu_cau == ma))).scalars().one()
    await dang_nhap_duoc_si.post(f"/api/v1/noi-bo/doi-tra/{yc.id}/duyet", json={"huong_xu_ly": "hoan_tien"})
    for r in (await db.execute(select(CtYeuCauDoiTra).where(CtYeuCauDoiTra.yeu_cau_id == yc.id))).scalars():
        r.so_luong_nhan = r.so_luong
    yc.trang_thai = "kho_da_nhan"
    await db.flush()
    await dang_nhap_duoc_si.post(f"/api/v1/noi-bo/doi-tra/{yc.id}/hoan-tien")
    hoan = (await db.execute(select(ThanhToan).where(ThanhToan.yeu_cau_doi_tra_id == yc.id))).scalars().one()
    yc.duoc_si_id = dang_nhap_admin.tai_khoan.id  # giả lập một người kiêm cả hai vai trò
    await db.flush()
    r = await dang_nhap_admin.post(f"{HT}/{hoan.id}/xac-nhan")
    assert r.status_code == 403 and r.json()["ma_loi"] == "TU_DUYET_KHONG_DUOC"
    await db.refresh(hoan)
    assert hoan.trang_thai == "khoi_tao"


async def test_chi_admin_xac_nhan_hoan_tien(dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, db):
    _, _, _, hoan = await _goc_va_hoan(db, dang_nhap_khach.tai_khoan)
    for c in (dang_nhap_duoc_si, dang_nhap_kho, dang_nhap_khach):
        assert (await c.get(HT)).status_code in (401, 403)
        assert (await c.post(f"{HT}/{hoan.id}/xac-nhan")).status_code in (401, 403)
    assert (await dang_nhap_khach.get(HT)).status_code in (401, 403)

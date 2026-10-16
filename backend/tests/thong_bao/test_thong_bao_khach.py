"""KTV13, KTV14, HT07: thông báo của khách và nhắc mua lại (T6.5)."""

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core.thoi_gian import bay_gio_utc, hom_nay_vn
from app.models.ban_hang import LichSuTrangThai
from app.models.khach_hang import ThongBao
from app.modules.ban_hang.trang_thai import TacNhan, chuyen_trang_thai
from app.modules.thong_bao.nhac_mua_lai import nhac_mua_lai
from app.modules.thong_bao.service import gui_cho_khach
from tests.conftest import _dang_nhap
from tests.doi_tra.test_doi_tra import _don_da_giao
from tests.factories import tao_khach

TB = "/api/v1/toi/thong-bao"


async def test_chi_thay_thong_bao_cua_minh_va_danh_dau_da_doc(dang_nhap_khach, app, db):
    khach = dang_nhap_khach.tai_khoan
    a = await gui_cho_khach(db, khach.id, loai="don_hang", tieu_de="Đơn A", lien_ket="/tai-khoan/don-hang/A")
    await gui_cho_khach(db, khach.id, loai="hoi_dap", tieu_de="Trả lời")
    async for khac in _dang_nhap(app, await tao_khach(db), "khach"):
        await gui_cho_khach(db, khac.tai_khoan.id, loai="don_hang", tieu_de="Của người khác")
        assert (await khac.post(f"{TB}/{a.id}/da-doc")).status_code == 404
        assert (await khac.get(f"{TB}/so-chua-doc")).json()["so_chua_doc"] == 1
    assert (await dang_nhap_khach.get(f"{TB}/so-chua-doc")).json()["so_chua_doc"] == 2
    ds = (await dang_nhap_khach.get(TB)).json()
    assert ds["tong"] == 2 and {d["tieu_de"] for d in ds["du_lieu"]} == {"Đơn A", "Trả lời"}
    assert (await dang_nhap_khach.post(f"{TB}/{a.id}/da-doc")).json()["da_doc"] is True
    assert (await dang_nhap_khach.get(TB, params={"da_doc": "false"})).json()["tong"] == 1
    assert (await dang_nhap_khach.post(f"{TB}/da-doc-tat-ca")).json()["da_cap_nhat"] == 1
    assert (await dang_nhap_khach.get(f"{TB}/so-chua-doc")).json()["so_chua_doc"] == 0


async def test_can_dang_nhap(client):
    assert (await client.get(TB)).status_code == 401


async def test_gui_email_sms_theo_loai(db, kenh_tin_nhan):
    khach = await tao_khach(db, email="a@example.com")
    await gui_cho_khach(
        db,
        khach.id,
        loai="don_thuoc",
        tieu_de="Đơn thuốc đã duyệt",
        noi_dung="<b>x</b>",
        lien_ket="/tai-khoan/don-thuoc",
    )
    assert [t for _, t in kenh_tin_nhan.sms] == ["Nha thuoc AI: Don thuoc da duyet"]
    den, tieu_de, html = kenh_tin_nhan.email[0]
    assert den == "a@example.com" and "&lt;b&gt;x&lt;/b&gt;" in html and "/tai-khoan/don-thuoc" in html
    await gui_cho_khach(db, khach.id, loai="hoi_dap", tieu_de="Chỉ trong ứng dụng")
    assert len(kenh_tin_nhan.sms) == 1 and len(kenh_tin_nhan.email) == 1
    kenh_tin_nhan.loi = RuntimeError("nhà cung cấp lỗi")
    tb = await gui_cho_khach(db, khach.id, loai="don_thuoc", tieu_de="Vẫn lưu được")
    assert tb.id is not None  # lỗi gửi ngoài không làm hỏng nghiệp vụ


async def test_doi_trang_thai_don_bao_khach_nhung_khong_bao_viec_khach_tu_lam(db):
    khach = await tao_khach(db)
    don, _, _ = await _don_da_giao(db, khach, tt="chua_thanh_toan")
    don.trang_thai = "dang_giao"
    await db.flush()
    await chuyen_trang_thai(db, don, "da_giao", TacNhan.he_thong(), "webhook_van_chuyen")
    tb = (await db.execute(select(ThongBao).where(ThongBao.khach_hang_id == khach.id))).scalars().all()
    assert [t.tieu_de for t in tb] == [f"Đơn {don.ma_don} đã giao thành công"]
    assert tb[0].loai == "don_hang" and tb[0].lien_ket == f"/tai-khoan/don-hang/{don.ma_don}"


async def _san_pham_dinh_ky(db, khach, ngay_truoc, so_luong=2, so_ngay="10"):
    don, ct, sp = await _don_da_giao(db, khach, so_luong=so_luong)
    sp.dung_dinh_ky, sp.so_ngay_dung_moi_don_vi = True, Decimal(so_ngay)
    luc = bay_gio_utc() - timedelta(days=ngay_truoc)
    db.add(LichSuTrangThai(don_hang_id=don.id, tu_trang_thai="dang_giao", den_trang_thai="da_giao", created_at=luc))
    await db.flush()
    return don, ct, sp


async def test_nhac_mua_lai_truoc_3_ngay_va_khong_nhac_trung(db):
    khach = await tao_khach(db)
    # 2 hộp x 10 ngày = 20 ngày; giao 17 ngày trước -> còn 3 ngày: nhắc
    _, ct, sp = await _san_pham_dinh_ky(db, khach, 17)
    kq = await nhac_mua_lai(db)
    assert kq.da_nhac == 1
    tb = (
        (await db.execute(select(ThongBao).where(ThongBao.khach_hang_id == khach.id, ThongBao.loai == "nhac_mua_lai")))
        .scalars()
        .one()
    )
    assert sp.ten in tb.tieu_de and tb.lien_ket == f"/san-pham/{sp.slug}?nhac={ct.id}"
    assert (await nhac_mua_lai(db)).da_nhac == 0  # chạy lại không nhắc trùng


async def test_nhac_mua_lai_khong_nhac_som_hoac_qua_tre_hoac_san_pham_khong_dinh_ky(db):
    khach = await tao_khach(db)
    await _san_pham_dinh_ky(db, khach, 5)  # còn 15 ngày
    await _san_pham_dinh_ky(db, khach, 80)  # hết từ 60 ngày trước: quá 30 ngày
    don, _, _ = await _don_da_giao(db, khach)  # không dùng định kỳ
    db.add(LichSuTrangThai(don_hang_id=don.id, tu_trang_thai="dang_giao", den_trang_thai="da_giao"))
    await db.flush()
    assert (await nhac_mua_lai(db)).da_nhac == 0
    assert (await nhac_mua_lai(db, hom_nay_vn() + timedelta(days=13))).da_nhac == 1  # tới hạn nhắc của đơn thứ nhất


async def test_nhac_mua_lai_bo_qua_thuoc_ke_don(db):
    khach = await tao_khach(db)
    _, _, sp = await _san_pham_dinh_ky(db, khach, 17)
    sp.loai_san_pham = "thuoc_ke_don"
    await db.flush()
    assert (await nhac_mua_lai(db)).da_nhac == 0

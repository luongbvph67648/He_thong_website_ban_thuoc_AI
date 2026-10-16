"""HT08: tự hoàn tất đơn đã giao hết hạn đổi trả; hủy đơn nhận tại quầy quá hạn (dòng 29 và 21)."""

from datetime import timedelta

from sqlalchemy import select

from app.core.thoi_gian import bay_gio_utc
from app.models.ban_hang import LichSuTrangThai, YeuCauDoiTra
from app.modules.ban_hang.tu_hoan_tat import tu_hoan_tat_don
from tests.factories import tao_don, tao_khach


async def _don(db, kh, trang_thai, so_ngay, **kw):
    """Đơn ở `trang_thai` từ `so_ngay` ngày trước (mốc nằm ở lịch sử trạng thái)."""
    don = await tao_don(db, kh, trang_thai=trang_thai, **kw)
    db.add(LichSuTrangThai(don_hang_id=don.id, den_trang_thai=trang_thai, nguon="he_thong", created_at=bay_gio_utc() - timedelta(days=so_ngay)))  # fmt: skip
    await db.flush()
    return don


async def test_da_giao_het_han_doi_tra_thanh_hoan_tat_con_han_thi_giu(db):
    kh = await tao_khach(db)
    het, con = await _don(db, kh, "da_giao", 8), await _don(db, kh, "da_giao", 6)  # mặc định 7 ngày
    kq = await tu_hoan_tat_don(db)
    assert kq.hoan_tat == [het.ma_don]
    await db.refresh(het)
    await db.refresh(con)
    assert (het.trang_thai, con.trang_thai) == ("hoan_tat", "da_giao")
    lich_su = (await db.scalars(select(LichSuTrangThai).where(LichSuTrangThai.don_hang_id == het.id).order_by(LichSuTrangThai.id.desc()))).first()  # fmt: skip
    assert (lich_su.den_trang_thai, lich_su.nguon) == ("hoan_tat", "he_thong")
    assert (await tu_hoan_tat_don(db)).hoan_tat == []  # chạy lại không làm gì


async def test_con_yeu_cau_doi_tra_mo_thi_khong_hoan_tat_dong_roi_thi_hoan_tat(db):
    kh = await tao_khach(db)
    mo, dong = await _don(db, kh, "da_giao", 30), await _don(db, kh, "da_giao", 30)
    for i, (don, tt) in enumerate(((mo, "da_duyet"), (dong, "tu_choi"))):
        db.add(YeuCauDoiTra(ma_yeu_cau=f"DT{i}{don.id}", don_hang_id=don.id, khach_hang_id=kh.id, ly_do="hu_hong", trang_thai=tt))  # fmt: skip
    await db.flush()
    assert (await tu_hoan_tat_don(db)).hoan_tat == [dong.ma_don]
    await db.refresh(mo)
    assert mo.trang_thai == "da_giao"


async def test_don_nhan_tai_quay_qua_han_bi_huy_don_giao_tan_noi_cho_lay_hang_thi_khong(db):
    kh = await tao_khach(db)
    qua = await _don(db, kh, "cho_lay_hang", 4, hinh_thuc_nhan="nhan_tai_nha_thuoc")  # mặc định 3 ngày
    con = await _don(db, kh, "cho_lay_hang", 2, hinh_thuc_nhan="nhan_tai_nha_thuoc")
    kq = await tu_hoan_tat_don(db)
    assert kq.da_huy_qua_han_quay == [qua.ma_don]
    await db.refresh(qua)
    await db.refresh(con)
    assert (qua.trang_thai, qua.ly_do_huy) == ("da_huy", "Quá hạn nhận hàng tại nhà thuốc")
    assert con.trang_thai == "cho_lay_hang"


async def test_doi_cau_hinh_thoi_han_co_hieu_luc_ngay(db):
    from app.models.he_thong import CauHinh

    kh = await tao_khach(db)
    don = await _don(db, kh, "da_giao", 2)
    assert (await tu_hoan_tat_don(db)).hoan_tat == []
    row = await db.get(CauHinh, "thoi_han_doi_tra_ngay")
    if row is None:
        db.add(CauHinh(khoa="thoi_han_doi_tra_ngay", gia_tri=1))
    else:
        row.gia_tri = 1
    await db.flush()
    assert (await tu_hoan_tat_don(db)).hoan_tat == [don.ma_don]


# --- KTV08: mua lại ---

MUA_LAI = "/api/v1/toi/don-hang/{}/mua-lai"


async def test_mua_lai_dua_dong_con_ban_vao_gio_bo_qua_thuoc_ke_don_va_dong_khong_ban(dang_nhap_khach, db):
    from tests.factories import tao_san_pham

    c = dang_nhap_khach
    con_ban = await tao_san_pham(db)
    ke_don = await tao_san_pham(db, "thuoc_ke_don")
    ngung = await tao_san_pham(db, trang_thai="ngung_kinh_doanh")
    don = await tao_don(
        db,
        c.tai_khoan,
        trang_thai="hoan_tat",
        dong=[
            {"san_pham": con_ban, "so_luong": 3},
            {"san_pham": ke_don, "so_luong": 1},
            {"san_pham": ngung, "so_luong": 2},
        ],
    )
    r = await c.post(MUA_LAI.format(don.ma_don))
    assert r.status_code == 200, r.text
    j = r.json()
    assert [(d["san_pham"]["id"], d["so_luong"]) for d in j["gio_hang"]["dong"]] == [(con_ban.id, 3)]
    assert {(b["san_pham_id"], b["ly_do"]) for b in j["bo_qua"]} == {(ke_don.id, "thuoc_ke_don"), (ngung.id, "khong_hien_thi")}  # fmt: skip
    r = await c.post(MUA_LAI.format(don.ma_don))  # mua lại lần nữa thì cộng dồn
    assert r.json()["gio_hang"]["dong"][0]["so_luong"] == 6


async def test_mua_lai_don_cua_nguoi_khac_hoac_khong_co_la_404(dang_nhap_khach, db):
    nguoi_khac = await tao_khach(db)
    don = await tao_don(db, nguoi_khac, trang_thai="hoan_tat")
    for ma in (don.ma_don, "DH_KHONG_CO"):
        r = await dang_nhap_khach.post(MUA_LAI.format(ma))
        assert (r.status_code, r.json()["ma_loi"]) == (404, "KHONG_TIM_THAY")


async def test_mua_lai_phai_dang_nhap(client):
    assert (await client.post(MUA_LAI.format("DH1"))).status_code == 401

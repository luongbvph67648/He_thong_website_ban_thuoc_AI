"""DS01, DS02, DS03, KTV06: danh sách/chi tiết đơn nội bộ, xác nhận, hủy đơn, hoàn tiền khi hủy đơn đã thanh toán."""

from decimal import Decimal

from sqlalchemy import func, select

from app.models.ban_hang import CtDonHang, DonHang, LichSuTrangThai, PhanBoLo, ThanhToan
from app.models.khach_hang import DiaChi
from app.models.kho import LoThuoc
from app.modules.ban_hang.trang_thai import NGUON_NGUOI_DUNG, TacNhan, chuyen_trang_thai
from tests.ban_hang.test_dat_hang import DON, dia_chi, khoa, sp_ban, them, thân
from tests.factories import tao_khach, tao_nhan_vien
from tests.khuyen_mai.test_khuyen_mai import tao_km
from tests.thanh_toan.test_thanh_toan import (  # noqa: F401  (_cau_hinh là fixture autouse của file này)
    _cau_hinh,
    dat_online,
    ipn_vnpay,
    lay_gd,
    tao_gd,
)

NB = "/api/v1/noi-bo/don-hang"


async def dat_cod(c, db, so_luong=3, **kw):
    sp = await sp_ban(db)
    d = await db.scalar(select(DiaChi).where(DiaChi.khach_hang_id == c.tai_khoan.id)) or await dia_chi(db, c.tai_khoan)
    await them(c, sp, "viên", so_luong)
    r = await c.post(DON, json=thân(d, **kw), headers=khoa())
    assert r.status_code == 201, r.text
    return sp, r.json()


async def don_cua(db, ma) -> DonHang:
    don = await db.scalar(select(DonHang).where(DonHang.ma_don == ma))
    await db.refresh(don)
    return don


async def tra_tien(client_khach, db, ma_don_online, tong):
    """Khách trả tiền thành công qua IPN VNPay → đơn sang `cho_xac_nhan`, `da_thanh_toan`."""
    await tao_gd(client_khach, ma_don_online)
    gd = await lay_gd(db, ma_don_online)
    r = await client_khach.get("/api/v1/webhook/vnpay-ipn", params=ipn_vnpay(f"{ma_don_online}-{gd.id}", Decimal(tong)))
    assert r.json()["RspCode"] == "00", r.text


# --- KTV06: khách hủy ---


async def test_khach_huy_don_nha_giu_tra_luot_ma(dang_nhap_khach, db):
    c = dang_nhap_khach
    _, ma = await tao_km(db, ma="HUY10")
    sp, o = await dat_cod(c, db, ma_giam_gia="HUY10")
    await db.refresh(ma)
    assert ma.so_luot_da_dung == 1
    r = await c.post(f"{DON}/{o['ma_don']}/huy", json={"ly_do": "Đặt nhầm"})
    assert r.status_code == 200, r.text
    assert r.json()["trang_thai"] == "da_huy"
    don = await don_cua(db, o["ma_don"])
    assert don.ly_do_huy == "Đặt nhầm"
    await db.refresh(ma)
    assert ma.so_luot_da_dung == 0
    assert (
        await db.scalar(select(func.coalesce(func.sum(LoThuoc.so_luong_giu), 0)).where(LoThuoc.san_pham_id == sp.id))
        == 0
    )
    # đã hủy rồi thì không hủy lại được (và không trả lượt lần hai)
    r2 = await c.post(f"{DON}/{o['ma_don']}/huy", json={})
    assert (r2.status_code, r2.json()["ma_loi"]) == (409, "CHUYEN_TRANG_THAI_KHONG_HOP_LE")
    await db.refresh(ma)
    assert ma.so_luot_da_dung == 0


async def test_khach_khong_huy_don_nguoi_khac_va_khong_huy_khi_dang_soan(dang_nhap_khach, app, db):
    from tests.thanh_toan.test_thanh_toan import _client_cua

    c = dang_nhap_khach
    _, o = await dat_cod(c, db)
    khac = await _client_cua(app, await tao_khach(db))
    assert (await khac.post(f"{DON}/{o['ma_don']}/huy", json={})).status_code == 404
    assert (await c.post(f"{DON}/DHKHONGCO1/huy", json={})).status_code == 404
    don = await don_cua(db, o["ma_don"])
    assert don.trang_thai == "cho_xac_nhan"
    kho = await tao_nhan_vien(db, "WAREHOUSE")
    await chuyen_trang_thai(db, don, "da_xac_nhan", TacNhan.duoc_si((await tao_nhan_vien(db)).id), NGUON_NGUOI_DUNG)
    await chuyen_trang_thai(db, don, "dang_soan_hang", TacNhan.kho(kho.id), NGUON_NGUOI_DUNG)
    r = await c.post(f"{DON}/{o['ma_don']}/huy", json={})
    assert (r.status_code, r.json()["ma_loi"]) == (403, "KHONG_CO_QUYEN")  # dòng hủy này không dành cho khách
    assert (await don_cua(db, o["ma_don"])).trang_thai == "dang_soan_hang"


async def test_khach_huy_don_da_thanh_toan_tao_hoan_tien_cho_admin(dang_nhap_khach, db):
    c = dang_nhap_khach
    _, o = await dat_online(c, db)
    await tra_tien(c, db, o["ma_don"], o["tong_tien"])
    don = await don_cua(db, o["ma_don"])
    assert (don.trang_thai, don.trang_thai_tt) == ("cho_xac_nhan", "da_thanh_toan")
    r = await c.post(f"{DON}/{o['ma_don']}/huy", json={"ly_do": "Không cần nữa"})
    assert r.status_code == 200, r.text
    don = await don_cua(db, o["ma_don"])
    assert (don.trang_thai, don.trang_thai_tt) == ("da_huy", "cho_hoan_tien")
    goc = await lay_gd(db, o["ma_don"])
    hoan = (await db.execute(select(ThanhToan).where(ThanhToan.loai == "hoan_tien"))).scalars().one()
    assert (hoan.don_hang_id, hoan.trang_thai, hoan.thanh_toan_goc_id) == (don.id, "khoi_tao", goc.id)
    assert (hoan.so_tien, hoan.cong_thanh_toan) == (goc.so_tien, "vnpay")


async def test_huy_don_chua_thanh_toan_khong_tao_hoan_tien(dang_nhap_khach, db):
    c = dang_nhap_khach
    _, o = await dat_online(c, db)  # cho_thanh_toan
    assert (await c.post(f"{DON}/{o['ma_don']}/huy", json={})).status_code == 200
    don = await don_cua(db, o["ma_don"])
    assert (don.trang_thai, don.trang_thai_tt) == ("da_huy", "chua_thanh_toan")
    assert await db.scalar(select(func.count()).select_from(ThanhToan).where(ThanhToan.loai == "hoan_tien")) == 0


async def test_khach_xem_danh_sach_don_cua_minh_co_dong_thoi_gian(dang_nhap_khach, app, db):
    from tests.thanh_toan.test_thanh_toan import _client_cua

    c = dang_nhap_khach
    _, a = await dat_cod(c, db)
    _, b = await dat_cod(c, db)
    khac = await _client_cua(app, await tao_khach(db))
    ds = (await c.get(DON)).json()
    assert [d["ma_don"] for d in ds["du_lieu"]] == [b["ma_don"], a["ma_don"]]  # mới nhất trước
    assert (await khac.get(DON)).json()["tong"] == 0
    loc = (await c.get(DON, params={"trang_thai": "da_huy"})).json()
    assert loc["tong"] == 0
    ct = (await c.get(f"{DON}/{a['ma_don']}")).json()
    assert [(m["tu_trang_thai"], m["den_trang_thai"]) for m in ct["lich_su"]] == [(None, "cho_xac_nhan")]
    assert "nhan_vien_id" not in ct["lich_su"][0]


# --- DS02, DS03: dược sĩ ---


async def test_duoc_si_xac_nhan_don(dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, dang_nhap_admin, db):
    _, o = await dat_cod(dang_nhap_khach, db)
    don = await don_cua(db, o["ma_don"])
    for c in (dang_nhap_kho, dang_nhap_admin):
        assert (await c.post(f"{NB}/{don.id}/xac-nhan")).status_code == 403
    r = await dang_nhap_duoc_si.post(f"{NB}/{don.id}/xac-nhan")
    assert r.status_code == 200, r.text
    assert r.json()["trang_thai"] == "da_xac_nhan"
    don = await don_cua(db, o["ma_don"])
    assert don.nhan_vien_xac_nhan_id == dang_nhap_duoc_si.tai_khoan.id
    again = await dang_nhap_duoc_si.post(f"{NB}/{don.id}/xac-nhan")
    assert (again.status_code, again.json()["ma_loi"]) == (409, "CHUYEN_TRANG_THAI_KHONG_HOP_LE")
    assert (await dang_nhap_duoc_si.post(f"{NB}/99999999/xac-nhan")).status_code == 404


async def test_duoc_si_huy_bat_buoc_ly_do_va_nha_giu(dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, db):
    sp, o = await dat_cod(dang_nhap_khach, db)
    don = await don_cua(db, o["ma_don"])
    assert (await dang_nhap_kho.post(f"{NB}/{don.id}/huy", json={"ly_do": "x"})).status_code == 403
    for thân_sai in ({}, {"ly_do": "   "}):
        r = await dang_nhap_duoc_si.post(f"{NB}/{don.id}/huy", json=thân_sai)
        assert r.status_code == 400, r.text
    assert (await don_cua(db, o["ma_don"])).trang_thai == "cho_xac_nhan"
    r = await dang_nhap_duoc_si.post(f"{NB}/{don.id}/huy", json={"ly_do": "Hết hàng thực tế"})
    assert r.status_code == 200, r.text
    don = await don_cua(db, o["ma_don"])
    assert (don.trang_thai, don.ly_do_huy) == ("da_huy", "Hết hàng thực tế")
    ls = (
        (
            await db.execute(
                select(LichSuTrangThai).where(LichSuTrangThai.don_hang_id == don.id).order_by(LichSuTrangThai.id)
            )
        )
        .scalars()
        .all()
    )
    assert ls[-1].nhan_vien_id == dang_nhap_duoc_si.tai_khoan.id and ls[-1].ghi_chu == "Hết hàng thực tế"
    assert (
        await db.scalar(select(func.coalesce(func.sum(LoThuoc.so_luong_giu), 0)).where(LoThuoc.san_pham_id == sp.id))
        == 0
    )


async def test_duoc_si_huy_don_dang_soan_hoan_nhap_dung_lo_va_hoan_tien(dang_nhap_khach, dang_nhap_duoc_si, db):
    c = dang_nhap_khach
    sp, o = await dat_online(c, db, so_luong=4)
    await tra_tien(c, db, o["ma_don"], o["tong_tien"])
    don = await don_cua(db, o["ma_don"])
    ton_truoc = await db.scalar(select(func.sum(LoThuoc.so_luong_ton)).where(LoThuoc.san_pham_id == sp.id))
    kho = await tao_nhan_vien(db, "WAREHOUSE")
    ds = TacNhan.duoc_si(dang_nhap_duoc_si.tai_khoan.id)
    await chuyen_trang_thai(db, don, "da_xac_nhan", ds, NGUON_NGUOI_DUNG)
    await chuyen_trang_thai(db, don, "dang_soan_hang", TacNhan.kho(kho.id), NGUON_NGUOI_DUNG)
    assert await db.scalar(select(func.sum(LoThuoc.so_luong_ton)).where(LoThuoc.san_pham_id == sp.id)) == ton_truoc - 4
    r = await dang_nhap_duoc_si.post(f"{NB}/{don.id}/huy", json={"ly_do": "Khách yêu cầu qua điện thoại"})
    assert r.status_code == 200, r.text
    assert await db.scalar(select(func.sum(LoThuoc.so_luong_ton)).where(LoThuoc.san_pham_id == sp.id)) == ton_truoc
    trang_thai_pb = (
        (
            await db.execute(
                select(PhanBoLo.trang_thai)
                .join(CtDonHang, CtDonHang.id == PhanBoLo.ct_don_hang_id)
                .where(CtDonHang.don_hang_id == don.id)
            )
        )
        .scalars()
        .all()
    )
    assert trang_thai_pb and set(trang_thai_pb) == {"da_hoan_nhap"}
    don = await don_cua(db, o["ma_don"])
    assert (don.trang_thai, don.trang_thai_tt) == ("da_huy", "cho_hoan_tien")
    assert await db.scalar(select(func.count()).select_from(ThanhToan).where(ThanhToan.loai == "hoan_tien")) == 1


# --- DS01: danh sách và chi tiết nội bộ ---


async def test_danh_sach_loc_theo_trang_thai_ngay_phuong_thuc_kenh(dang_nhap_khach, dang_nhap_duoc_si, db):
    from datetime import timedelta

    c = dang_nhap_khach
    _, a = await dat_cod(c, db)
    _, b = await dat_online(c, db)
    ps = dang_nhap_duoc_si
    ds = (await ps.get(NB)).json()
    assert {d["ma_don"] for d in ds["du_lieu"]} == {a["ma_don"], b["ma_don"]}
    r = (await ps.get(NB, params={"trang_thai": "cho_thanh_toan"})).json()
    assert [d["ma_don"] for d in r["du_lieu"]] == [b["ma_don"]]
    r = (await ps.get(NB, params={"phuong_thuc_tt": "cod"})).json()
    assert [d["ma_don"] for d in r["du_lieu"]] == [a["ma_don"]]
    assert (await ps.get(NB, params={"kenh_ban": "tai_quay"})).json()["tong"] == 0
    assert (await ps.get(NB, params={"kenh_ban": "online"})).json()["tong"] == 2
    don_a = await don_cua(db, a["ma_don"])
    hom_qua = (don_a.created_at - timedelta(days=2)).date().isoformat()
    ngay = don_a.created_at.date().isoformat()
    assert (await ps.get(NB, params={"tu_ngay": ngay, "den_ngay": ngay})).json()["tong"] == 2
    assert (await ps.get(NB, params={"den_ngay": hom_qua})).json()["tong"] == 0
    tim = (await ps.get(NB, params={"q": a["ma_don"]})).json()
    assert [d["ma_don"] for d in tim["du_lieu"]] == [a["ma_don"]]
    assert (await ps.get(NB, params={"trang_thai": "khong_co"})).status_code == 400


async def test_chi_tiet_don_noi_bo_co_dong_thoi_gian(dang_nhap_khach, dang_nhap_duoc_si, db):
    _, o = await dat_cod(dang_nhap_khach, db)
    don = await don_cua(db, o["ma_don"])
    await dang_nhap_duoc_si.post(f"{NB}/{don.id}/xac-nhan")
    ct = (await dang_nhap_duoc_si.get(f"{NB}/{don.id}")).json()
    assert ct["ma_don"] == o["ma_don"] and len(ct["dong"]) == 1
    assert [(m["tu_trang_thai"], m["den_trang_thai"]) for m in ct["lich_su"]] == [
        (None, "cho_xac_nhan"),
        ("cho_xac_nhan", "da_xac_nhan"),
    ]
    assert ct["lich_su"][1]["nguoi_thuc_hien"] == dang_nhap_duoc_si.tai_khoan.ho_ten
    assert ct["lich_su"][0]["nguoi_thuc_hien"] is not None  # khách đặt
    assert "giao_dich" in ct
    assert (await dang_nhap_duoc_si.get(f"{NB}/99999999")).status_code == 404


async def test_kho_chi_thay_don_tu_da_xac_nhan_tro_di(
    dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, dang_nhap_admin, db
):
    c = dang_nhap_khach
    _, a = await dat_cod(c, db)
    _, b = await dat_cod(c, db)
    _, huy_som = await dat_cod(c, db)
    await c.post(f"{DON}/{huy_som['ma_don']}/huy", json={})
    don_a = await don_cua(db, a["ma_don"])
    await dang_nhap_duoc_si.post(f"{NB}/{don_a.id}/xac-nhan")
    don_b = await don_cua(db, b["ma_don"])
    ds_kho = (await dang_nhap_kho.get(NB)).json()
    assert [d["ma_don"] for d in ds_kho["du_lieu"]] == [a["ma_don"]]  # chờ xác nhận và hủy trước xác nhận: ẩn
    assert (await dang_nhap_kho.get(f"{NB}/{don_b.id}")).status_code == 404
    ct = (await dang_nhap_kho.get(f"{NB}/{don_a.id}")).json()
    assert ct["ten_nguoi_nhan"] and ct["sdt_nguoi_nhan"] and ct["dia_chi_giao"]
    assert ct["giao_dich"] == [] and ct["khach_hang_id"] is None  # kho không thấy tiền và hồ sơ khách
    assert (await dang_nhap_admin.get(NB)).json()["tong"] == 3  # Admin xem tất cả
    assert (await dang_nhap_admin.get(f"{NB}/{don_b.id}")).status_code == 200


async def test_noi_bo_can_dang_nhap(client):
    assert (await client.get(NB)).status_code == 401

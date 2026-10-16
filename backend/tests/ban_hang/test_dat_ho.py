"""DS07 (tạo đơn hộ khách qua điện thoại) và DS15 (giao đơn nhận tại quầy)."""

import uuid
from decimal import Decimal

from sqlalchemy import func, select

from app.models.ban_hang import CtDonHang, DonHang, ThanhToan
from app.models.kho import LoThuoc
from tests.ban_hang.test_dat_hang import DON, khoa, sp_ban, them, thân
from tests.ban_hang.test_soan_hang import SH
from tests.ban_hang.test_xu_ly_don import NB, don_cua
from tests.factories import tao_khach, tao_san_pham
from tests.thanh_toan.test_thanh_toan import _cau_hinh, ipn_vnpay, lay_gd, tao_gd  # noqa: F401

HO = "/api/v1/noi-bo/don-ho"
QUAY = "/api/v1/noi-bo/giao-tai-quay"
DIA_CHI = {"dia_chi_chi_tiet": "12 Lê Lợi", "ma_tinh": "201", "ma_phuong_xa": "2010101"}


def khoa_moi() -> dict:
    return {"Idempotency-Key": str(uuid.uuid4())}


def than_ho(sp, so_luong=2, don_vi="viên", **kw) -> dict:
    return {
        "ten_nguoi_nhan": "Trần Bình",
        "sdt_nguoi_nhan": "0987654321",
        "hinh_thuc_nhan": "nhan_tai_nha_thuoc",
        "phuong_thuc_tt": "cod",
        "dong": [{"san_pham_id": sp.id, "don_vi_id": sp.don_vi_theo_ten[don_vi].id, "so_luong": so_luong}],
        **kw,
    }


async def giu_cua(db, sp) -> int:
    return await db.scalar(select(func.coalesce(func.sum(LoThuoc.so_luong_giu), 0)).where(LoThuoc.san_pham_id == sp.id))


# --- DS07 ---


async def test_cod_cua_khach_co_tai_khoan_vao_thang_da_xac_nhan_va_giu_hang(dang_nhap_duoc_si, db):
    khach = await tao_khach(db)
    sp = await sp_ban(db)
    r = await dang_nhap_duoc_si.post(
        HO,
        json=than_ho(sp, 3, sdt_khach=khach.so_dien_thoai, hinh_thuc_nhan="giao_tan_noi", dia_chi=DIA_CHI),
        headers=khoa_moi(),
    )
    assert r.status_code == 201, r.text
    ra = r.json()
    assert ra["lien_ket_thanh_toan"] is None
    assert ra["don"]["trang_thai"] == "da_xac_nhan"
    assert ra["don"]["dia_chi_giao"].startswith("12 Lê Lợi")
    don = await don_cua(db, ra["don"]["ma_don"])
    assert (don.kenh_ban, don.khach_hang_id) == ("dien_thoai", khach.id)
    assert don.nhan_vien_tao_id == dang_nhap_duoc_si.tai_khoan.id
    assert await giu_cua(db, sp) == 3
    assert [x["den_trang_thai"] for x in ra["don"]["lich_su"]] == ["da_xac_nhan"]


async def test_khach_chua_co_tai_khoan_chi_dung_cod(dang_nhap_duoc_si, db):
    sp = await sp_ban(db)
    r = await dang_nhap_duoc_si.post(HO, json=than_ho(sp), headers=khoa_moi())
    assert r.status_code == 201, r.text
    assert (await don_cua(db, r.json()["don"]["ma_don"])).khach_hang_id is None
    r = await dang_nhap_duoc_si.post(HO, json=than_ho(sp, phuong_thuc_tt="vnpay"), headers=khoa_moi())
    assert (r.status_code, r.json()["ma_loi"]) == (400, "DU_LIEU_KHONG_HOP_LE")
    r = await dang_nhap_duoc_si.post(HO, json=than_ho(sp, sdt_khach="0911111111"), headers=khoa_moi())
    assert (r.status_code, r.json()["ma_loi"]) == (404, "KHONG_TIM_THAY")
    r = await dang_nhap_duoc_si.post(HO, json=than_ho(sp, ma_giam_gia="ABC"), headers=khoa_moi())
    assert r.status_code == 400  # mã giảm giá cần khách có tài khoản


async def test_online_vao_cho_thanh_toan_roi_ipn_chuyen_da_xac_nhan(dang_nhap_duoc_si, app, db):
    from tests.thanh_toan.test_thanh_toan import _client_cua

    khach = await tao_khach(db)
    sp = await sp_ban(db)
    r = await dang_nhap_duoc_si.post(
        HO, json=than_ho(sp, sdt_khach=khach.so_dien_thoai, phuong_thuc_tt="vnpay"), headers=khoa_moi()
    )
    assert r.status_code == 201, r.text
    ra = r.json()
    assert ra["don"]["trang_thai"] == "cho_thanh_toan" and ra["don"]["han_thanh_toan"]
    assert ra["lien_ket_thanh_toan"] == f"/thanh-toan/ket-qua?ma={ra['don']['ma_don']}"
    assert await giu_cua(db, sp) == 2
    ck = await _client_cua(app, khach)  # khách mở link và thanh toán như đơn tự đặt
    await tao_gd(ck, ra["don"]["ma_don"])
    gd = await lay_gd(db, ra["don"]["ma_don"])
    tong = Decimal(ra["don"]["tong_tien"])
    r2 = await ck.get("/api/v1/webhook/vnpay-ipn", params=ipn_vnpay(f"{ra['don']['ma_don']}-{gd.id}", tong))
    assert r2.json()["RspCode"] == "00", r2.text
    don = await don_cua(db, ra["don"]["ma_don"])
    assert (don.trang_thai, don.trang_thai_tt) == ("da_xac_nhan", "da_thanh_toan")  # dòng 11: đơn do dược sĩ tạo


async def test_thuoc_ke_don_bi_chan_o_service_va_khong_tao_don(dang_nhap_duoc_si, db):
    ke_don = await tao_san_pham(db, loai="thuoc_ke_don")
    r = await dang_nhap_duoc_si.post(HO, json=than_ho(ke_don), headers=khoa_moi())
    assert r.status_code >= 400
    assert r.json()["ma_loi"] == "THUOC_KE_DON_KHONG_VAO_GIO"
    assert await db.scalar(select(func.count()).select_from(CtDonHang).where(CtDonHang.san_pham_id == ke_don.id)) == 0


async def test_het_hang_hoan_tac_ca_don(dang_nhap_duoc_si, db):
    sp = await sp_ban(db, ton=2)
    nhieu = await sp_ban(db)
    body = than_ho(sp, 5)
    body["dong"].append({"san_pham_id": nhieu.id, "don_vi_id": nhieu.don_vi_theo_ten["viên"].id, "so_luong": 1})
    r = await dang_nhap_duoc_si.post(HO, json=body, headers=khoa_moi())
    assert (r.status_code, r.json()["ma_loi"]) == (409, "HET_HANG")
    assert await giu_cua(db, nhieu) == 0
    assert await db.scalar(select(func.count()).select_from(DonHang).where(DonHang.ten_nguoi_nhan == "Trần Bình")) == 0


async def test_khoa_idempotency_tao_mot_don_giu_hang_mot_lan(dang_nhap_duoc_si, db):
    sp = await sp_ban(db)
    k = khoa_moi()
    r1 = await dang_nhap_duoc_si.post(HO, json=than_ho(sp, 2), headers=k)
    r2 = await dang_nhap_duoc_si.post(HO, json=than_ho(sp, 2), headers=k)
    assert r1.status_code == r2.status_code == 201
    assert r1.json()["don"]["ma_don"] == r2.json()["don"]["ma_don"]
    assert await giu_cua(db, sp) == 2
    assert (await dang_nhap_duoc_si.post(HO, json=than_ho(sp, 2))).status_code == 400  # thiếu Idempotency-Key


async def test_dia_chi_giao_hop_le(dang_nhap_duoc_si, db):
    sp = await sp_ban(db)
    giao = than_ho(sp, hinh_thuc_nhan="giao_tan_noi")
    r = await dang_nhap_duoc_si.post(HO, json=giao, headers=khoa_moi())
    assert r.status_code == 400  # giao tận nơi phải có địa chỉ
    r = await dang_nhap_duoc_si.post(HO, json={**giao, "dia_chi": {**DIA_CHI, "ma_tinh": "ZZ"}}, headers=khoa_moi())
    assert r.status_code == 400  # mã tỉnh không có trong danh mục
    r = await dang_nhap_duoc_si.post(HO, json=than_ho(sp, dia_chi=DIA_CHI), headers=khoa_moi())
    assert r.status_code == 400  # nhận tại nhà thuốc không có địa chỉ giao
    assert await giu_cua(db, sp) == 0


async def test_tim_khach_theo_sdt_va_phan_quyen(dang_nhap_duoc_si, dang_nhap_kho, dang_nhap_admin, db):
    khach = await tao_khach(db)
    r = await dang_nhap_duoc_si.get(f"{HO}/khach", params={"sdt": khach.so_dien_thoai})
    assert r.status_code == 200, r.text
    assert r.json()["ho_ten"] == khach.ho_ten and r.json()["dia_chi"] == []
    assert "email" not in r.json()
    assert (await dang_nhap_duoc_si.get(f"{HO}/khach", params={"sdt": "0911111111"})).status_code == 404
    assert (await dang_nhap_duoc_si.get(f"{HO}/khach", params={"sdt": "abc"})).status_code == 400
    sp = await sp_ban(db)
    for c in (dang_nhap_kho, dang_nhap_admin):  # chỉ dược sĩ lập đơn hộ
        assert (await c.get(f"{HO}/khach", params={"sdt": khach.so_dien_thoai})).status_code == 403
        assert (await c.post(HO, json=than_ho(sp), headers=khoa_moi())).status_code == 403


# --- DS15 ---


async def den_cho_lay_hang_tai_quay(duoc_si, kho, db, **kw):
    sp = await sp_ban(db)
    r = await duoc_si.post(HO, json=than_ho(sp, **kw), headers=khoa_moi())
    assert r.status_code == 201, r.text
    don = await don_cua(db, r.json()["don"]["ma_don"])
    assert (await kho.post(f"{SH}/{don.id}/bat-dau")).status_code == 200
    assert (await kho.post(f"{SH}/{don.id}/dong-goi")).status_code == 200
    return sp, don


async def test_giao_tai_quay_thu_tien_roi_da_giao(dang_nhap_duoc_si, dang_nhap_kho, db):
    _, don = await den_cho_lay_hang_tai_quay(dang_nhap_duoc_si, dang_nhap_kho, db)
    assert (await don_cua(db, don.ma_don)).trang_thai == "cho_lay_hang"
    for q in (don.ma_don.lower(), "0987654321"):  # tìm theo mã đơn hoặc SĐT
        r = await dang_nhap_duoc_si.get(QUAY, params={"q": q})
        assert r.status_code == 200 and [x["ma_don"] for x in r.json()] == [don.ma_don], r.text
    r = await dang_nhap_duoc_si.post(f"{QUAY}/{don.id}", json={})
    assert (r.status_code, r.json()["ma_loi"]) == (400, "DU_LIEU_KHONG_HOP_LE")  # chưa trả tiền thì phải chọn cách thu
    assert (await don_cua(db, don.ma_don)).trang_thai == "cho_lay_hang"
    r = await dang_nhap_duoc_si.post(f"{QUAY}/{don.id}", json={"phuong_thuc_thu": "tien_mat"})
    assert r.status_code == 200, r.text
    d = await don_cua(db, don.ma_don)
    assert (d.trang_thai, d.trang_thai_tt) == ("da_giao", "da_thanh_toan")
    (tt,) = (await db.execute(select(ThanhToan).where(ThanhToan.don_hang_id == d.id))).scalars().all()
    assert (tt.cong_thanh_toan, tt.trang_thai, tt.so_tien) == ("tien_mat", "thanh_cong", d.tong_tien)
    assert tt.nhan_vien_xu_ly_id == dang_nhap_duoc_si.tai_khoan.id
    r = await dang_nhap_duoc_si.post(f"{QUAY}/{don.id}", json={"phuong_thuc_thu": "tien_mat"})
    assert (r.status_code, r.json()["ma_loi"]) == (409, "CHUYEN_TRANG_THAI_KHONG_HOP_LE")  # không thu hai lần
    assert (await dang_nhap_duoc_si.get(QUAY, params={"q": don.ma_don})).json() == []  # đã giao khỏi danh sách tìm


async def test_giao_tai_quay_don_da_thanh_toan_khong_thu_them(dang_nhap_duoc_si, dang_nhap_kho, db):
    _, don = await den_cho_lay_hang_tai_quay(dang_nhap_duoc_si, dang_nhap_kho, db)
    don.trang_thai_tt = "da_thanh_toan"  # như đã chuyển khoản trước
    await db.flush()
    r = await dang_nhap_duoc_si.post(f"{QUAY}/{don.id}", json={})
    assert r.status_code == 200, r.text
    assert (await don_cua(db, don.ma_don)).trang_thai == "da_giao"
    assert (await db.scalar(select(func.count()).select_from(ThanhToan).where(ThanhToan.don_hang_id == don.id))) == 0


async def test_giao_tai_quay_chi_don_nhan_tai_nha_thuoc_o_cho_lay_hang_va_chi_duoc_si(
    dang_nhap_duoc_si, dang_nhap_kho, dang_nhap_admin, db
):
    sp = await sp_ban(db)
    giao = await dang_nhap_duoc_si.post(
        HO, json=than_ho(sp, hinh_thuc_nhan="giao_tan_noi", dia_chi=DIA_CHI), headers=khoa_moi()
    )
    don_giao = await don_cua(db, giao.json()["don"]["ma_don"])
    r = await dang_nhap_duoc_si.post(f"{QUAY}/{don_giao.id}", json={"phuong_thuc_thu": "tien_mat"})
    assert r.status_code == 404  # đơn giao tận nơi không đi luồng này
    quay = await dang_nhap_duoc_si.post(HO, json=than_ho(sp), headers=khoa_moi())
    don_quay = await don_cua(db, quay.json()["don"]["ma_don"])  # mới ở "Đã xác nhận"
    assert (await dang_nhap_duoc_si.get(QUAY, params={"q": don_quay.ma_don})).json() == []
    r = await dang_nhap_duoc_si.post(f"{QUAY}/{don_quay.id}", json={"phuong_thuc_thu": "tien_mat"})
    assert (r.status_code, r.json()["ma_loi"]) == (409, "CHUYEN_TRANG_THAI_KHONG_HOP_LE")
    for c in (dang_nhap_kho, dang_nhap_admin):
        assert (await c.get(QUAY, params={"q": "x"})).status_code == 403
        assert (await c.post(f"{QUAY}/{don_quay.id}", json={})).status_code == 403
    assert (await dang_nhap_duoc_si.get(QUAY, params={"q": " "})).status_code == 400


async def test_don_online_nhan_tai_nha_thuoc_cung_giao_duoc_o_quay(
    dang_nhap_khach, dang_nhap_duoc_si, dang_nhap_kho, db
):
    c = dang_nhap_khach
    sp = await sp_ban(db)
    await them(c, sp, "viên", 2)
    o = (await c.post(DON, json=thân(None), headers=khoa())).json()
    don = await don_cua(db, o["ma_don"])
    await dang_nhap_duoc_si.post(f"{NB}/{don.id}/xac-nhan")
    await dang_nhap_kho.post(f"{SH}/{don.id}/bat-dau")
    await dang_nhap_kho.post(f"{SH}/{don.id}/dong-goi")
    r = await dang_nhap_duoc_si.get(QUAY, params={"q": c.tai_khoan.so_dien_thoai})
    assert [x["ma_don"] for x in r.json()] == [don.ma_don]
    assert (
        await dang_nhap_duoc_si.post(f"{QUAY}/{don.id}", json={"phuong_thuc_thu": "chuyen_khoan"})
    ).status_code == 200
    assert (await don_cua(db, don.ma_don)).trang_thai == "da_giao"

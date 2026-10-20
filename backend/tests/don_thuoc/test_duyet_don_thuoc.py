"""DS04, DS05: hàng chờ, khóa, màn duyệt, cảnh báo, tạo đơn từ đơn thuốc (T5.3)."""

import re
import uuid
from datetime import timedelta

from sqlalchemy import select

from app.core.thoi_gian import bay_gio_utc
from app.jobs.cong_viec import ht08_tu_hoan_tat
from app.models.ban_hang import DonHang, YeuCauDonThuoc
from app.models.he_thong import NhatKyHeThong
from app.models.khach_hang import DiUng, HoSoSucKhoe, ThongBao
from app.models.san_pham import HoatChat, ThanhPhan, TuongTacHoatChat
from tests.conftest import _dang_nhap
from tests.factories import tao_khach, tao_lo, tao_nhan_vien, tao_san_pham

BASE = "/api/v1/noi-bo/don-thuoc"
CHECKLIST = {
    "thong_tin_nguoi_benh": True,
    "thong_tin_bac_si": True,
    "ngay_ke_trong_hieu_luc": True,
    "don_chua_su_dung": True,
    "da_kiem_tra_tuong_tac": True,
}
HASH = "h" * 64


async def _yc(db, khach=None, trang_thai="cho_duyet", duoc_si=None, **kw):
    yc = YeuCauDonThuoc(
        ma_yeu_cau="YC" + uuid.uuid4().hex[:8].upper(), khach_hang_id=None if khach is None else khach.id,
        ho_ten="Nguyễn Văn A", so_dien_thoai="0912345678", anh_don_thuoc=["don-thuoc/" + uuid.uuid4().hex + ".png"],
        trang_thai=trang_thai, duoc_si_id=None if duoc_si is None else duoc_si.id,
        khoa_luc=bay_gio_utc() if duoc_si is not None else None, hash_anh=uuid.uuid4().hex, **kw,
    )  # fmt: skip
    db.add(yc)
    await db.flush()
    return yc


async def _thuoc(db, loai="thuoc_ke_don", ton=100, **kw):
    sp = await tao_san_pham(db, loai, **kw)
    await tao_lo(db, sp, so_luong=ton)
    return sp


def _dong(sp, so_luong=2):
    return {"san_pham_id": sp.id, "don_vi_id": sp.don_vi_theo_ten["viên"].id, "so_luong": so_luong}


def _tao(dong, **kw):
    return {"dong": dong, "checklist": CHECKLIST, **kw}


async def _hoat_chat(db, ten):
    h = HoatChat(ten=f"{ten}-{uuid.uuid4().hex[:6]}")
    db.add(h)
    await db.flush()
    return h


async def test_hang_cho_chi_hien_cho_duyet_va_khoa_cua_minh(dang_nhap_duoc_si, db):
    ds = dang_nhap_duoc_si.tai_khoan
    khac = await tao_nhan_vien(db)
    a, b, c, d = (
        await _yc(db),
        await _yc(db, trang_thai="dang_tu_van", duoc_si=ds),
        await _yc(db, trang_thai="dang_tu_van", duoc_si=khac),
        await _yc(db, trang_thai="da_tao_don"),
    )
    r = await dang_nhap_duoc_si.get(BASE)
    assert r.status_code == 200
    ma = {x["ma_yeu_cau"]: x for x in r.json()}
    assert set(ma) == {a.ma_yeu_cau, b.ma_yeu_cau}
    assert ma[b.ma_yeu_cau]["khoa_boi_toi"] is True and ma[a.ma_yeu_cau]["khoa_boi_toi"] is False
    assert c.ma_yeu_cau not in ma and d.ma_yeu_cau not in ma


async def test_chi_duoc_si_vao_duoc(clients_theo_vai_tro, db):
    yc = await _yc(db)
    for vai_tro in ("WAREHOUSE", "ADMIN"):
        c = clients_theo_vai_tro[vai_tro]
        for r in (await c.get(BASE), await c.get(f"{BASE}/{yc.id}"), await c.post(f"{BASE}/{yc.id}/nhan")):
            assert r.status_code == 403


async def test_nhan_xu_ly_khoa_va_nguoi_khac_bi_chan(dang_nhap_duoc_si, app, db):
    yc = await _yc(db)
    r = await dang_nhap_duoc_si.post(f"{BASE}/{yc.id}/nhan")
    assert r.status_code == 200 and r.json()["trang_thai"] == "dang_tu_van" and r.json()["het_khoa_luc"]
    assert (await dang_nhap_duoc_si.post(f"{BASE}/{yc.id}/nhan")).status_code == 200  # gia hạn
    async for khac in _dang_nhap(app, await tao_nhan_vien(db), "noi_bo"):
        r = await khac.post(f"{BASE}/{yc.id}/nhan")
        assert r.status_code == 409 and r.json()["ma_loi"] == "DA_CO_NGUOI_XU_LY"
        assert (await khac.get(f"{BASE}/{yc.id}")).status_code == 403  # không xem được yêu cầu khóa cho người khác
        assert (await khac.post(f"{BASE}/{yc.id}/tu-choi", json={"ly_do": "không hợp lệ"})).status_code == 403
        assert (await khac.post(f"{BASE}/{yc.id}/nha")).status_code == 403
    assert (await dang_nhap_duoc_si.post(f"{BASE}/{yc.id}/nha")).status_code == 204
    await db.refresh(yc)
    assert yc.trang_thai == "cho_duyet" and yc.duoc_si_id is None and yc.khoa_luc is None


async def test_chua_nhan_thi_khong_xem_duoc(dang_nhap_duoc_si, db):
    yc = await _yc(db)
    assert (await dang_nhap_duoc_si.get(f"{BASE}/{yc.id}")).status_code == 403
    assert (await dang_nhap_duoc_si.get(f"{BASE}/999999")).status_code == 404


async def test_man_duyet_url_anh_ky_va_ho_so_qua_cong(dang_nhap_duoc_si, db):
    ds = dang_nhap_duoc_si.tai_khoan
    khach = await tao_khach(db)
    amox = await _hoat_chat(db, "Amoxicillin")
    db.add(HoSoSucKhoe(khach_hang_id=khach.id, dong_y_su_dung=True, nam_sinh=1980))
    db.add(DiUng(khach_hang_id=khach.id, hoat_chat_id=amox.id))
    yc = await _yc(db, khach, "dang_tu_van", ds)
    r = await dang_nhap_duoc_si.get(f"{BASE}/{yc.id}")
    d = r.json()
    assert d["anh"][0].startswith("/api/v1/tep-rieng/don-thuoc/") and "ky=" in d["anh"][0]
    assert d["ho_so_suc_khoe"]["nam_sinh"] == 1980 and d["ho_so_suc_khoe"]["di_ung"][0]["ten_hoat_chat"].startswith(
        "Amox"
    )
    nhat_ky = (await db.execute(select(NhatKyHeThong).where(NhatKyHeThong.hanh_dong == "doc_suc_khoe"))).scalars().all()
    assert len(nhat_ky) == 1 and nhat_ky[0].nhan_vien_id == ds.id


async def test_khach_chua_dong_y_hoac_vang_lai_khong_co_ho_so(dang_nhap_duoc_si, db):
    ds = dang_nhap_duoc_si.tai_khoan
    chua = await tao_khach(db)
    db.add(HoSoSucKhoe(khach_hang_id=chua.id, dong_y_su_dung=False, nam_sinh=1980))
    a, b = await _yc(db, chua, "dang_tu_van", ds), await _yc(db, None, "dang_tu_van", ds)
    for yc in (a, b):
        assert (await dang_nhap_duoc_si.get(f"{BASE}/{yc.id}")).json()["ho_so_suc_khoe"] is None
    assert (await db.execute(select(NhatKyHeThong).where(NhatKyHeThong.hanh_dong == "doc_suc_khoe"))).first() is None


async def test_canh_bao_trung_anh(dang_nhap_duoc_si, db):
    ds = dang_nhap_duoc_si.tai_khoan
    cu = await _yc(db, trang_thai="da_tao_don", da_su_dung=True)
    yc = await _yc(db, None, "dang_tu_van", ds)
    yc.hash_anh = cu.hash_anh = HASH
    await db.flush()
    d = (await dang_nhap_duoc_si.get(f"{BASE}/{yc.id}")).json()
    assert [(t["ma_yeu_cau"], t["da_su_dung"]) for t in d["trung_anh"]] == [(cu.ma_yeu_cau, True)]
    sp = await _thuoc(db)
    r = await dang_nhap_duoc_si.post(f"{BASE}/{yc.id}/tao-don", json=_tao([_dong(sp)]))
    assert r.status_code == 409 and r.json()["ma_loi"] == "CAN_XAC_NHAN_CANH_BAO"
    r = await dang_nhap_duoc_si.post(f"{BASE}/{yc.id}/tao-don", json=_tao([_dong(sp)], xac_nhan_trung_anh=True))
    assert r.status_code == 201, r.text


async def test_tu_choi_can_ly_do_va_bao_khach(dang_nhap_duoc_si, kenh_tin_nhan, db):
    ds = dang_nhap_duoc_si.tai_khoan
    khach = await tao_khach(db)
    thanh_vien, vang_lai = await _yc(db, khach, "dang_tu_van", ds), await _yc(db, None, "dang_tu_van", ds)
    assert (await dang_nhap_duoc_si.post(f"{BASE}/{vang_lai.id}/tu-choi", json={"ly_do": ""})).status_code == 400
    assert (await dang_nhap_duoc_si.post(f"{BASE}/{vang_lai.id}/tu-choi", json={})).status_code == 400
    r = await dang_nhap_duoc_si.post(f"{BASE}/{vang_lai.id}/tu-choi", json={"ly_do": "Đơn mờ, không đọc được"})
    assert r.status_code == 204
    await db.refresh(vang_lai)
    assert vang_lai.trang_thai == "tu_choi" and vang_lai.ly_do_tu_choi == "Đơn mờ, không đọc được"
    assert kenh_tin_nhan.sms and vang_lai.ma_yeu_cau in kenh_tin_nhan.sms[-1][1]
    await dang_nhap_duoc_si.post(f"{BASE}/{thanh_vien.id}/tu-choi", json={"ly_do": "Hết hiệu lực"})
    tb = (await db.execute(select(ThongBao).where(ThongBao.khach_hang_id == khach.id))).scalars().one()
    assert tb.loai == "don_thuoc" and tb.lien_ket == "/tai-khoan/don-thuoc"


async def test_tim_san_pham_co_ke_don_va_ton(dang_nhap_duoc_si, db):
    ds = dang_nhap_duoc_si.tai_khoan
    yc = await _yc(db, None, "dang_tu_van", ds)
    sp = await _thuoc(db, ten="Augmentin-xyz 625", ton=40)
    hc = await _hoat_chat(db, "Amoxicillin")
    db.add(ThanhPhan(san_pham_id=sp.id, hoat_chat_id=hc.id))
    await db.flush()
    r = await dang_nhap_duoc_si.get(f"{BASE}/{yc.id}/san-pham", params={"q": "augmentin xyz"[:9]})
    d = r.json()
    assert [x["id"] for x in d] == [sp.id] and d[0]["loai_san_pham"] == "thuoc_ke_don" and d[0]["ton_kha_dung"] == 40
    assert d[0]["hoat_chat"] == [hc.ten] and d[0]["don_vi"][0]["ten_don_vi"] == "viên"
    assert (await dang_nhap_duoc_si.get(f"{BASE}/{yc.id}/san-pham", params={"q": hc.ten[:6]})).json()[0]["id"] == sp.id
    assert (await dang_nhap_duoc_si.get(f"{BASE}/{yc.id}/san-pham", params={"q": ""})).json() == []


async def test_tao_don_vang_lai_giu_hang_gui_link(dang_nhap_duoc_si, kenh_tin_nhan, db):
    from app.models.kho import LoThuoc

    ds = dang_nhap_duoc_si.tai_khoan
    yc = await _yc(db, None, "dang_tu_van", ds)
    ke_don, otc = await _thuoc(db, ton=50), await _thuoc(db, "thuoc_khong_ke_don", ton=50)
    r = await dang_nhap_duoc_si.post(f"{BASE}/{yc.id}/tao-don", json=_tao([_dong(ke_don, 3), _dong(otc, 1)]))
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["don"]["trang_thai"] == "cho_khach_xac_nhan" and d["don"]["han_xac_nhan"]
    assert d["lien_ket_xac_nhan"] is None  # link chỉ tới khách qua SMS: dược sĩ cầm link thì xác nhận thay khách được
    lien_ket = re.search(r"https?://\S+/xac-nhan-don/\S+", kenh_tin_nhan.sms[-1][1]).group(0)
    assert kenh_tin_nhan.sms[-1][0] == yc.so_dien_thoai
    don = (await db.execute(select(DonHang).where(DonHang.ma_don == d["don"]["ma_don"]))).scalars().one()
    assert don.khach_hang_id is None and don.nhan_vien_tao_id == ds.id and don.yeu_cau_don_thuoc_id == yc.id
    assert don.token_truy_cap_hash and lien_ket.rsplit("/", 1)[1] not in don.token_truy_cap_hash
    assert don.giam_gia == 0 and don.phuong_thuc_tt is None
    lo = (await db.execute(select(LoThuoc).where(LoThuoc.san_pham_id == ke_don.id))).scalars().one()
    assert lo.so_luong_giu == 3 and lo.so_luong_ton == 50
    await db.refresh(yc)
    assert yc.trang_thai == "da_tao_don" and yc.da_su_dung is False and yc.checklist["da_kiem_tra_tuong_tac"] is True
    # Không tạo được đơn thứ hai từ cùng yêu cầu.
    assert (await dang_nhap_duoc_si.post(f"{BASE}/{yc.id}/tao-don", json=_tao([_dong(otc)]))).status_code == 403


async def test_tao_don_thanh_vien_khong_sms_co_thong_bao(dang_nhap_duoc_si, kenh_tin_nhan, db):
    ds = dang_nhap_duoc_si.tai_khoan
    khach = await tao_khach(db)
    yc = await _yc(db, khach, "dang_tu_van", ds)
    sp = await _thuoc(db)
    r = await dang_nhap_duoc_si.post(f"{BASE}/{yc.id}/tao-don", json=_tao([_dong(sp)]))
    assert r.status_code == 201 and r.json()["lien_ket_xac_nhan"] is None
    assert kenh_tin_nhan.sms == []
    don = (await db.execute(select(DonHang))).scalars().one()
    assert don.khach_hang_id == khach.id and don.token_truy_cap_hash is None
    tb = (await db.execute(select(ThongBao).where(ThongBao.khach_hang_id == khach.id))).scalars().one()
    assert tb.lien_ket == f"/tai-khoan/don-hang/{don.ma_don}"


async def test_checklist_thieu_thi_khong_tao_don(dang_nhap_duoc_si, db):
    yc = await _yc(db, None, "dang_tu_van", dang_nhap_duoc_si.tai_khoan)
    sp = await _thuoc(db)
    r = await dang_nhap_duoc_si.post(
        f"{BASE}/{yc.id}/tao-don", json={"dong": [_dong(sp)], "checklist": {**CHECKLIST, "thong_tin_bac_si": False}}
    )
    assert r.status_code == 400 and r.json()["chi_tiet"][0]["truong"] == "checklist.thong_tin_bac_si"
    assert (await db.execute(select(DonHang))).first() is None


async def test_het_hang_hoan_tac_ca_don(dang_nhap_duoc_si, db):
    yc = await _yc(db, None, "dang_tu_van", dang_nhap_duoc_si.tai_khoan)
    sp = await _thuoc(db, ton=1)
    r = await dang_nhap_duoc_si.post(f"{BASE}/{yc.id}/tao-don", json=_tao([_dong(sp, 5)]))
    assert r.status_code == 409 and r.json()["ma_loi"] == "HET_HANG"
    await db.refresh(yc)
    assert yc.trang_thai == "dang_tu_van"


async def test_canh_bao_tuong_tac_nghiem_trong_bat_buoc_ghi_chu(dang_nhap_duoc_si, dang_nhap_admin, dang_nhap_kho, db):
    ds = dang_nhap_duoc_si.tai_khoan
    yc = await _yc(db, None, "dang_tu_van", ds)
    a, b = await _hoat_chat(db, "HoatChatA"), await _hoat_chat(db, "HoatChatB")
    sp_a, sp_b = await _thuoc(db), await _thuoc(db)
    db.add_all([ThanhPhan(san_pham_id=sp_a.id, hoat_chat_id=a.id), ThanhPhan(san_pham_id=sp_b.id, hoat_chat_id=b.id)])
    x, y = sorted((a.id, b.id))
    db.add(TuongTacHoatChat(hoat_chat_a_id=x, hoat_chat_b_id=y, muc_do="nghiem_trong", khuyen_cao="Tránh dùng chung"))
    await db.flush()
    dong = [_dong(sp_a), _dong(sp_b)]
    cb = (await dang_nhap_duoc_si.post(f"{BASE}/{yc.id}/canh-bao", json={"dong": dong})).json()
    assert cb["can_ghi_chu_tu_van"] is True and cb["tuong_tac"][0]["muc_do"] == "nghiem_trong"
    r = await dang_nhap_duoc_si.post(f"{BASE}/{yc.id}/tao-don", json=_tao(dong))
    assert r.status_code == 400 and r.json()["chi_tiet"][0]["truong"] == "ghi_chu_tu_van"
    r = await dang_nhap_duoc_si.post(f"{BASE}/{yc.id}/tao-don", json=_tao(dong, ghi_chu_tu_van="Uống cách nhau 4 giờ"))
    assert r.status_code == 201
    assert r.json()["don"]["ghi_chu"] == "Uống cách nhau 4 giờ"
    # Ghi chú tư vấn có thể nêu dị ứng: dược sĩ thấy, Admin và kho thì không (quy tắc 7)
    don = await db.scalar(select(DonHang).where(DonHang.ma_don == r.json()["don"]["ma_don"]))
    ct = await dang_nhap_duoc_si.get(f"/api/v1/noi-bo/don-hang/{don.id}")
    assert ct.json()["ghi_chu"] == "Uống cách nhau 4 giờ"
    don.trang_thai, don.phuong_thuc_tt = "da_xac_nhan", "cod"  # kho chỉ thấy đơn từ "Đã xác nhận" trở đi
    await db.flush()
    for client_noi_bo, duong in ((dang_nhap_admin, "don-hang"), (dang_nhap_kho, "soan-hang")):
        r2 = await client_noi_bo.get(f"/api/v1/noi-bo/{duong}/{don.id}")
        assert r2.status_code == 200 and r2.json()["ghi_chu"] is None and "Uống cách nhau" not in r2.text


async def test_canh_bao_di_ung_khong_lo_ho_so(dang_nhap_duoc_si, db):
    ds = dang_nhap_duoc_si.tai_khoan
    khach = await tao_khach(db)
    amox = await _hoat_chat(db, "Amoxicillin")
    db.add(DiUng(khach_hang_id=khach.id, hoat_chat_id=amox.id, ghi_chu="GHICHU-BI-MAT"))
    sp = await _thuoc(db)
    db.add(ThanhPhan(san_pham_id=sp.id, hoat_chat_id=amox.id))
    yc = await _yc(db, khach, "dang_tu_van", ds)
    await db.flush()
    r = await dang_nhap_duoc_si.post(f"{BASE}/{yc.id}/canh-bao", json={"dong": [_dong(sp)]})
    assert r.status_code == 200 and "GHICHU-BI-MAT" not in r.text
    cb = r.json()
    assert cb["di_ung"][0]["ten_hoat_chat"].startswith("Amoxicillin") and cb["can_ghi_chu_tu_van"] is True


async def test_ke_don_van_bi_chan_o_gio_hang_va_don_ho(dang_nhap_khach, db):
    """Mở đường riêng cho DS05 không làm lộ đường giỏ hàng."""
    sp = await _thuoc(db)
    r = await dang_nhap_khach.post(
        "/api/v1/toi/gio-hang/dong",
        json={"san_pham_id": sp.id, "don_vi_id": sp.don_vi_theo_ten["viên"].id, "so_luong": 1},
    )
    assert r.status_code == 422 and r.json()["ma_loi"] == "THUOC_KE_DON_KHONG_VAO_GIO"


async def test_ht08_nha_khoa_qua_han(db):
    ds = await tao_nhan_vien(db)
    cu = await _yc(db, None, "dang_tu_van", ds)
    cu.khoa_luc = bay_gio_utc() - timedelta(minutes=31)
    moi = await _yc(db, None, "dang_tu_van", ds)
    xong = await _yc(db, None, "da_tao_don", ds)
    xong.khoa_luc = bay_gio_utc() - timedelta(hours=5)
    await db.flush()
    kq = await ht08_tu_hoan_tat(db)
    assert kq.nha_khoa_don_thuoc == [cu.ma_yeu_cau]
    for y in (cu, moi, xong):
        await db.refresh(y)
    assert (cu.trang_thai, cu.duoc_si_id, cu.khoa_luc) == ("cho_duyet", None, None)
    assert moi.trang_thai == "dang_tu_van" and moi.duoc_si_id == ds.id
    assert xong.trang_thai == "da_tao_don"

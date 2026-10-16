"""KTV02: đặt hàng từ giỏ, giữ hàng FEFO, mã giảm giá, phí ship, idempotency và tranh chấp đơn vị cuối cùng."""

import asyncio
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.core import idempotency
from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc, hom_nay_vn
from app.models.ban_hang import CtGioHang, DonHang, GioHang, LichSuTrangThai, MaGiamGia, PhanBoLo
from app.models.khach_hang import DiaChi
from app.models.kho import LoThuoc
from app.modules.ban_hang import dat_hang
from app.modules.ban_hang.schemas import DatHangVao
from app.modules.gio_hang.dich_vu import them_dong
from app.modules.gio_hang.schemas import DongVao
from app.tich_hop import van_chuyen
from tests.bat_bien.kiem_tra import kiem_tra_bat_bien
from tests.factories import tao_khach, tao_lo, tao_san_pham
from tests.khuyen_mai.test_khuyen_mai import tao_km

DON = "/api/v1/toi/don-hang"
GIO = "/api/v1/toi/gio-hang"
VIEN, HOP = (
    {"ten_don_vi": "viên", "he_so": 1, "gia_ban": 1000, "la_mac_dinh": True},
    {"ten_don_vi": "hộp", "he_so": 10, "gia_ban": 9500, "la_mac_dinh": False},
)


@pytest.fixture(autouse=True)
def _xoa_idempotency():
    idempotency.quen_het()


def khoa() -> dict:
    return {"Idempotency-Key": str(uuid.uuid4())}


async def sp_ban(db, ton=100, **kw):
    sp = await tao_san_pham(db, don_vi=[VIEN, HOP], **kw)
    if ton:
        await tao_lo(db, sp, so_luong=ton)
    return sp


async def them(c, sp, don_vi="viên", so_luong=1):
    r = await c.post(
        f"{GIO}/dong", json={"san_pham_id": sp.id, "don_vi_id": sp.don_vi_theo_ten[don_vi].id, "so_luong": so_luong}
    )
    assert r.status_code == 200, r.text


async def dia_chi(db, khach) -> DiaChi:
    d = DiaChi(
        khach_hang_id=khach.id, ten_nguoi_nhan="Nguyễn An", so_dien_thoai="0912345678", dia_chi_chi_tiet="12 Lê Lợi",
        ma_tinh="01", ten_tinh="Hà Nội", ma_phuong_xa="0001", ten_phuong_xa="Phường A", la_mac_dinh=True,
    )  # fmt: skip
    db.add(d)
    await db.flush()
    return d


def thân(d: DiaChi | None = None, **kw) -> dict:
    return {
        "hinh_thuc_nhan": "giao_tan_noi" if d else "nhan_tai_nha_thuoc",
        "phuong_thuc_tt": "cod",
        **({"dia_chi_id": d.id} if d else {}),
        **kw,
    }


async def so_giu(db, sp) -> int:
    return await db.scalar(select(func.coalesce(func.sum(LoThuoc.so_luong_giu), 0)).where(LoThuoc.san_pham_id == sp.id))


async def test_dat_cod_tao_don_chup_gia_va_giu_hang(dang_nhap_khach, db):
    c, kh = dang_nhap_khach, dang_nhap_khach.tai_khoan
    sp = await sp_ban(db)
    d = await dia_chi(db, kh)
    await them(c, sp, "viên", 3)
    await them(c, sp, "hộp", 1)
    r = await c.post(DON, json=thân(d), headers=khoa())
    assert r.status_code == 201, r.text
    o = r.json()
    assert len(o["ma_don"]) == 10 and o["ma_don"].startswith("DH")
    assert (o["trang_thai"], o["trang_thai_tt"], o["han_thanh_toan"]) == ("cho_xac_nhan", "chua_thanh_toan", None)
    assert (o["tam_tinh"], o["giam_gia"], o["phi_van_chuyen"], o["tong_tien"]) == (
        "12500.00",
        "0.00",
        "25000.00",
        "37500.00",
    )
    assert o["dia_chi_giao"] == "12 Lê Lợi, Phường A, Hà Nội" and o["ten_nguoi_nhan"] == "Nguyễn An"
    assert {x["ten_don_vi"] for x in o["dong"]} == {"viên", "hộp"}
    assert await so_giu(db, sp) == 13  # 3 viên + 1 hộp = 13 đơn vị cơ sở
    ls = (await db.execute(select(LichSuTrangThai))).scalars().all()
    assert [(x.tu_trang_thai, x.den_trang_thai.value) for x in ls] == [(None, "cho_xac_nhan")]
    assert (await c.get(GIO)).json()["dong"] == []  # giỏ đã được dùng hết
    assert (await c.get(f"{DON}/{o['ma_don']}")).json() == o
    assert await kiem_tra_bat_bien(db) == []


@pytest.mark.parametrize("pt", ["vnpay", "momo"])
async def test_thanh_toan_online_cho_thanh_toan_kem_han(dang_nhap_khach, db, pt):
    c = dang_nhap_khach
    sp = await sp_ban(db)
    await them(c, sp)
    r = await c.post(DON, json=thân(phuong_thuc_tt=pt), headers=khoa())
    o = r.json()
    assert (o["trang_thai"], o["phuong_thuc_tt"]) == ("cho_thanh_toan", pt)
    from datetime import datetime

    han = datetime.fromisoformat(o["han_thanh_toan"])
    assert timedelta(minutes=14) < han - bay_gio_utc() <= timedelta(minutes=15)


async def test_nhan_tai_nha_thuoc_khong_ton_phi_ship_va_mien_phi_tu_nguong(dang_nhap_khach, db):
    c, kh = dang_nhap_khach, dang_nhap_khach.tai_khoan
    sp = await sp_ban(db, ton=1000)
    d = await dia_chi(db, kh)
    await them(c, sp, "viên", 5)
    o = (await c.post(DON, json=thân(), headers=khoa())).json()
    assert o["phi_van_chuyen"] == "0.00" and o["dia_chi_giao"] is None and o["tong_tien"] == "5000.00"
    await them(c, sp, "viên", 300)  # đúng 300.000 ₫: miễn phí ship từ ngưỡng (>=)
    o = (await c.post(DON, json=thân(d), headers=khoa())).json()
    assert (o["tam_tinh"], o["phi_van_chuyen"], o["tong_tien"]) == ("300000.00", "0.00", "300000.00")
    await them(c, sp, "viên", 299)
    o = (await c.post(DON, json=thân(d), headers=khoa())).json()
    assert o["phi_van_chuyen"] == "50000.00"  # 299.000 < 300.000; ~6 kg nên phí giả 50.000


async def test_adapter_van_chuyen_loi_dung_phi_mac_dinh(dang_nhap_khach, db, monkeypatch):
    class Hong:
        async def tinh_phi(self, *a):
            raise RuntimeError("GHN sập")

    monkeypatch.setattr(dat_hang, "lay_don_vi_van_chuyen", lambda: Hong())
    c, kh = dang_nhap_khach, dang_nhap_khach.tai_khoan
    sp = await sp_ban(db)
    d = await dia_chi(db, kh)
    await them(c, sp)
    o = (await c.post(DON, json=thân(d), headers=khoa())).json()
    assert o["phi_van_chuyen"] == "30000.00"


async def test_fefo_tach_lo_va_bo_qua_lo_can_han_hoac_het_han(dang_nhap_khach, db):
    c = dang_nhap_khach
    sp = await tao_san_pham(db, don_vi=[VIEN])
    hn = hom_nay_vn()
    muon = await tao_lo(db, sp, so_luong=10, han_su_dung=hn + timedelta(days=400))
    som = await tao_lo(db, sp, so_luong=4, han_su_dung=hn + timedelta(days=200))
    can_han = await tao_lo(db, sp, so_luong=50, han_su_dung=hn + timedelta(days=30))  # cận hạn: không bán online
    het_han = await tao_lo(db, sp, so_luong=50, han_su_dung=hn - timedelta(days=1), trang_thai="dang_ban")
    await them(c, sp, "viên", 7)
    assert (await c.post(DON, json=thân(), headers=khoa())).status_code == 201
    pb = (await db.execute(select(PhanBoLo).order_by(PhanBoLo.id))).scalars().all()
    assert [(p.lo_id, p.so_luong_co_so, p.trang_thai.value) for p in pb] == [
        (som.id, 4, "dang_giu"),
        (muon.id, 3, "dang_giu"),
    ]
    await db.refresh(can_han)
    await db.refresh(het_han)
    assert can_han.so_luong_giu == 0 and het_han.so_luong_giu == 0
    assert await kiem_tra_bat_bien(db) == []


async def test_chi_con_lo_can_han_thi_het_hang(dang_nhap_khach, db):
    c = dang_nhap_khach
    sp = await tao_san_pham(db, don_vi=[VIEN])
    await tao_lo(db, sp, so_luong=50, han_su_dung=hom_nay_vn() + timedelta(days=30))
    await them(c, sp, "viên", 1)
    r = await c.post(DON, json=thân(), headers=khoa())
    assert r.status_code == 409 and r.json()["ma_loi"] == "HET_HANG" and r.json()["chi_tiet"]["con_lai"] == 0


async def test_het_hang_hoan_tac_ca_don_ma_giam_gia_va_giu_hang(dang_nhap_khach, db):
    c = dang_nhap_khach
    du, thieu = await sp_ban(db, ton=50), await sp_ban(db, ton=2)
    _, ma = await tao_km(db, ma="HETHANG1")
    await them(c, du, "viên", 5)
    await them(c, thieu, "viên", 3)  # giữ được dòng 1 rồi mới thiếu ở dòng 2
    r = await c.post(DON, json=thân(ma_giam_gia="HETHANG1"), headers=khoa())
    assert (r.status_code, r.json()["ma_loi"], r.json()["chi_tiet"]["con_lai"]) == (409, "HET_HANG", 2)
    assert await db.scalar(select(func.count()).select_from(DonHang)) == 0
    assert await so_giu(db, du) == 0 and await so_giu(db, thieu) == 0
    await db.refresh(ma)
    assert ma.so_luot_da_dung == 0
    assert len((await c.get(GIO)).json()["dong"]) == 2  # giỏ còn nguyên để khách sửa


async def test_ma_giam_gia_phan_bo_vao_dong_va_tang_luot(dang_nhap_khach, db):
    c = dang_nhap_khach
    a, b = await sp_ban(db), await sp_ban(db)
    km, ma = await tao_km(db, ma="GIAM10X", gia_tri=Decimal(10))
    await them(c, a, "viên", 7)  # 7.000
    await them(c, b, "viên", 3)  # 3.000 -> giảm 10% của 10.000 = 1.000
    o = (await c.post(DON, json=thân(ma_giam_gia="giam10x"), headers=khoa())).json()
    assert (o["tam_tinh"], o["giam_gia"], o["tong_tien"], o["ma_giam_gia"]) == (
        "10000.00",
        "1000.00",
        "9000.00",
        "GIAM10X",
    )
    assert sum(Decimal(x["giam_gia_phan_bo"]) for x in o["dong"]) == Decimal(1000)
    assert sorted(x["giam_gia_phan_bo"] for x in o["dong"]) == ["300.00", "700.00"]
    await db.refresh(ma)
    assert ma.so_luot_da_dung == 1
    # hết lượt/khách (luot_moi_khach = 1, đơn trước chưa hủy): đặt lần hai bị từ chối và không đổi gì
    await them(c, a, "viên", 1)
    r = await c.post(DON, json=thân(ma_giam_gia="GIAM10X"), headers=khoa())
    assert r.status_code == 422 and r.json()["ma_loi"] == "MA_GIAM_GIA_KHONG_HOP_LE"
    assert r.json()["chi_tiet"]["ma_ly_do"] == "het_luot_khach"
    assert await db.scalar(select(func.count()).select_from(DonHang)) == 1
    await db.refresh(ma)
    assert ma.so_luot_da_dung == 1


async def test_gia_da_thay_doi_tra_gio_tinh_lai_va_khong_tao_gi(dang_nhap_khach, db):
    c = dang_nhap_khach
    sp = await sp_ban(db)
    await them(c, sp, "viên", 4)
    r = await c.post(DON, json=thân(tong_tien_ky_vong="3000"), headers=khoa())
    assert (r.status_code, r.json()["ma_loi"]) == (409, "GIA_DA_THAY_DOI")
    ct = r.json()["chi_tiet"]
    assert (ct["tam_tinh"], ct["tong_tien"], ct["dong"][0]["thanh_tien"]) == ("4000.00", "4000.00", "4000.00")
    assert await db.scalar(select(func.count()).select_from(DonHang)) == 0 and await so_giu(db, sp) == 0
    r = await c.post(DON, json=thân(tong_tien_ky_vong="4000"), headers=khoa())  # đúng tổng thì đặt được
    assert r.status_code == 201


async def test_idempotency_cung_khoa_tra_don_cu_khac_noi_dung_409(dang_nhap_khach, db):
    c = dang_nhap_khach
    sp = await sp_ban(db)
    await them(c, sp, "viên", 2)
    h = khoa()
    r1 = await c.post(DON, json=thân(), headers=h)
    r2 = await c.post(DON, json=thân(), headers=h)
    assert r1.status_code == r2.status_code == 201 and r1.json() == r2.json()
    assert await db.scalar(select(func.count()).select_from(DonHang)) == 1 and await so_giu(db, sp) == 2
    r3 = await c.post(DON, json=thân(phuong_thuc_tt="momo"), headers=h)
    assert (r3.status_code, r3.json()["ma_loi"]) == (409, "TRUNG_DU_LIEU")
    r4 = await c.post(DON, json=thân(), headers=khoa())  # khóa mới + giỏ trống
    assert (r4.status_code, r4.json()["ma_loi"]) == (400, "DU_LIEU_KHONG_HOP_LE")


@pytest.mark.parametrize("h", [{}, {"Idempotency-Key": "khong-phai-uuid"}])
async def test_thieu_hoac_sai_idempotency_key_la_400(dang_nhap_khach, db, h):
    sp = await sp_ban(db)
    await them(dang_nhap_khach, sp)
    r = await dang_nhap_khach.post(DON, json=thân(), headers=h)
    assert (r.status_code, r.json()["ma_loi"]) == (400, "DU_LIEU_KHONG_HOP_LE")
    assert await db.scalar(select(func.count()).select_from(DonHang)) == 0


async def test_dia_chi_cua_khach_khac_la_404_va_thieu_dia_chi_la_400(dang_nhap_khach, db):
    c = dang_nhap_khach
    sp = await sp_ban(db)
    await them(c, sp)
    nguoi_la = await dia_chi(db, await tao_khach(db))
    r = await c.post(DON, json=thân(nguoi_la), headers=khoa())
    assert (r.status_code, r.json()["ma_loi"]) == (404, "KHONG_TIM_THAY")
    r = await c.post(DON, json={"hinh_thuc_nhan": "giao_tan_noi", "phuong_thuc_tt": "cod"}, headers=khoa())
    assert (r.status_code, r.json()["chi_tiet"][0]["truong"]) == (400, "dia_chi_id")
    assert await db.scalar(select(func.count()).select_from(DonHang)) == 0


async def test_khong_nhan_phuong_thuc_tai_quay_va_truong_la(dang_nhap_khach, db):
    sp = await sp_ban(db)
    await them(dang_nhap_khach, sp)
    for body in ({**thân(), "phuong_thuc_tt": "tien_mat"}, {**thân(), "khach_hang_id": 1}):
        r = await dang_nhap_khach.post(DON, json=body, headers=khoa())
        assert r.status_code == 400, body


async def test_thuoc_ke_don_trong_gio_bi_chan_o_service_ke_ca_khi_lot_vao_gio(dang_nhap_khach, db):
    c, kh = dang_nhap_khach, dang_nhap_khach.tai_khoan
    ke_don = await sp_ban(db, loai="thuoc_ke_don")
    gio = GioHang(khach_hang_id=kh.id)
    db.add(gio)
    await db.flush()
    db.add(
        CtGioHang(gio_hang_id=gio.id, san_pham_id=ke_don.id, don_vi_id=ke_don.don_vi_theo_ten["viên"].id, so_luong=1)
    )
    await db.flush()  # chèn thẳng, qua mặt API giỏ
    r = await c.post(DON, json=thân(), headers=khoa())
    assert (r.status_code, r.json()["ma_loi"]) == (422, "THUOC_KE_DON_KHONG_VAO_GIO")
    assert await db.scalar(select(func.count()).select_from(DonHang)) == 0 and await so_giu(db, ke_don) == 0


async def test_vuot_so_luong_toi_da_theo_don_vi_co_so(dang_nhap_khach, db):
    c = dang_nhap_khach
    sp = await sp_ban(db, so_luong_toi_da_moi_don=12)
    await them(c, sp, "hộp", 1)  # 10 viên
    await them(c, sp, "viên", 2)  # 12: vừa đủ
    assert (await c.post(DON, json=thân(), headers=khoa())).status_code == 201
    await them(c, sp, "hộp", 1)
    await them(c, sp, "viên", 2)
    await db.execute(
        CtGioHang.__table__.update().values(so_luong=CtGioHang.so_luong + 1).where(CtGioHang.san_pham_id == sp.id)
    )  # nâng vượt qua mặt API giỏ
    r = await c.post(DON, json=thân(), headers=khoa())
    assert (r.status_code, r.json()["ma_loi"]) == (422, "VUOT_SO_LUONG_TOI_DA")


async def test_don_hang_cua_nguoi_khac_la_404_qua_service(db):
    a, b = await tao_khach(db), await tao_khach(db)
    sp = await sp_ban(db)
    await them_dong(db, a, DongVao(san_pham_id=sp.id, don_vi_id=sp.don_vi_theo_ten["viên"].id, so_luong=1))
    ra = await dat_hang.dat_hang(db, a, DatHangVao(**thân()), str(uuid.uuid4()))
    assert (await dat_hang.don_cua_khach(db, a, ra.ma_don)).ma_don == ra.ma_don
    with pytest.raises(LoiNghiepVu) as e:
        await dat_hang.don_cua_khach(db, b, ra.ma_don)
    assert e.value.ma_loi == "KHONG_TIM_THAY"


async def test_hai_khach_cung_dat_don_vi_cuoi_dung_mot_don_thanh_cong(db_that):
    async with db_that() as s, s.begin():
        sp = await tao_san_pham(s, don_vi=[VIEN])
        await tao_lo(s, sp, so_luong=1)
        khach = [await tao_khach(s), await tao_khach(s)]
        for k in khach:
            await them_dong(s, k, DongVao(san_pham_id=sp.id, don_vi_id=sp.don_vi_theo_ten["viên"].id, so_luong=1))
        sp_id = sp.id
        khach_ids = [k.id for k in khach]

    async def dat(khach_id):
        async with db_that() as s, s.begin():
            from app.models.khach_hang import KhachHang

            k = await s.get(KhachHang, khach_id)
            return await dat_hang.dat_hang(s, k, DatHangVao(**thân()), str(uuid.uuid4()))

    kq = await asyncio.gather(*[dat(i) for i in khach_ids], return_exceptions=True)
    thanh_cong = [x for x in kq if not isinstance(x, Exception)]
    loi = [x for x in kq if isinstance(x, LoiNghiepVu)]
    assert len(thanh_cong) == 1 and len(loi) == 1 and loi[0].ma_loi == "HET_HANG"
    async with db_that() as s:
        lo = (await s.execute(select(LoThuoc).where(LoThuoc.san_pham_id == sp_id))).scalar_one()
        assert (lo.so_luong_ton, lo.so_luong_giu) == (1, 1)  # tồn không âm, đúng một lượt giữ
        assert await s.scalar(select(func.count()).select_from(DonHang)) == 1
        assert await kiem_tra_bat_bien(s) == []


async def test_hai_lan_dat_dong_thoi_cua_mot_khach_chi_tao_mot_don(db_that):
    async with db_that() as s, s.begin():
        sp = await tao_san_pham(s, don_vi=[VIEN])
        await tao_lo(s, sp, so_luong=50)
        k = await tao_khach(s)
        await them_dong(s, k, DongVao(san_pham_id=sp.id, don_vi_id=sp.don_vi_theo_ten["viên"].id, so_luong=2))
        khach_id = k.id
    khoa_chung = str(uuid.uuid4())

    async def dat():
        async with db_that() as s, s.begin():
            from app.models.khach_hang import KhachHang

            return await dat_hang.dat_hang(s, await s.get(KhachHang, khach_id), DatHangVao(**thân()), khoa_chung)

    kq = await asyncio.gather(dat(), dat(), return_exceptions=True)
    assert all(not isinstance(x, Exception) for x in kq) and kq[0].ma_don == kq[1].ma_don
    async with db_that() as s:
        assert await s.scalar(select(func.count()).select_from(DonHang)) == 1
        assert await s.scalar(select(func.sum(LoThuoc.so_luong_giu))) == 2
        assert await s.scalar(select(func.count()).select_from(MaGiamGia)) == 0


def test_phi_ship_gia_theo_khoi_luong():
    from app.tich_hop.van_chuyen.gia import VanChuyenGia

    dc = van_chuyen.DiaChiGiao(ma_tinh="01", ma_phuong_xa="0001", dia_chi_chi_tiet="x")
    phi = lambda g: asyncio.run(VanChuyenGia().tinh_phi(dc, g, Decimal(0)))  # noqa: E731
    assert [phi(200), phi(1000), phi(1001), phi(500_000)] == [25000, 25000, 30000, 100000]


async def test_xem_truoc_tinh_phi_va_giam_ma_ma_khong_ghi_gi(dang_nhap_khach, db):
    c, kh = dang_nhap_khach, dang_nhap_khach.tai_khoan
    sp = await sp_ban(db)
    d = await dia_chi(db, kh)
    _, ma = await tao_km(db, ma="XEMTRUOC1", gia_tri=Decimal(10))
    await them(c, sp, "viên", 10)
    r = await c.post(f"{DON}/xem-truoc", json=thân(d, ma_giam_gia="xemtruoc1"))  # không cần Idempotency-Key
    assert r.status_code == 200, r.text
    assert r.json() == {
        "tam_tinh": "10000.00",
        "giam_gia": "1000.00",
        "phi_van_chuyen": "25000.00",
        "tong_tien": "34000.00",
        "ma_giam_gia": "XEMTRUOC1",
    }
    r = await c.post(f"{DON}/xem-truoc", json=thân())
    assert r.json()["phi_van_chuyen"] == "0.00" and r.json()["tong_tien"] == "10000.00"
    await db.refresh(ma)
    assert ma.so_luot_da_dung == 0 and await so_giu(db, sp) == 0
    assert await db.scalar(select(func.count()).select_from(DonHang)) == 0
    r = await c.post(f"{DON}/xem-truoc", json=thân(ma_giam_gia="KHONGCO"))
    assert (r.status_code, r.json()["ma_loi"]) == (422, "MA_GIAM_GIA_KHONG_HOP_LE")

"""T7.9: AI09 dự báo nhu cầu (mô hình thuần, job hằng tuần) và KHO14 xem đề xuất nhập hàng."""

import uuid
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.thoi_gian import VN_TZ, hom_nay_vn
from app.jobs.__main__ import LICH_TUAN
from app.jobs.cong_viec import ai09_du_bao_nhu_cau
from app.models.ai import DeXuatNhapHang
from app.models.ban_hang import CtDonHang, PhanBoLo
from app.models.he_thong import CauHinh
from app.modules.du_bao import mo_hinh
from app.modules.du_bao.dich_vu import chay_du_bao, chuoi_day_du, chuoi_xuat_theo_tuan, dau_tuan
from tests.factories import tao_don, tao_khach, tao_lo, tao_san_pham

BASE = "/api/v1/noi-bo/de-xuat-nhap"


# --- mô hình thuần ---


def test_trung_binh_truot_trong_so_4_3_2_1():
    assert mo_hinh.trung_binh_truot([10, 20, 30, 40], 2) == [30.0, 30.0]
    assert mo_hinh.trung_binh_truot([99, 10, 20, 30, 40], 1) == [30.0]  # chỉ 4 tuần cuối
    assert mo_hinh.trung_binh_truot([5], 1) == [5.0]
    assert mo_hinh.trung_binh_truot([2, 4], 1)[0] == pytest.approx((2 * 3 + 4 * 4) / 7)
    assert mo_hinh.trung_binh_truot([], 3) == [0.0, 0.0, 0.0]


def test_tong_30_ngay_bon_tuan_va_hai_phan_bay_tuan_lam_tron_len():
    assert mo_hinh.tong_30_ngay([7.0] * 5) == 30  # 28 + 2/7 * 7, không bị nhiễu số thực đẩy lên 31
    assert mo_hinh.tong_30_ngay([1.0] * 5) == 5  # 4.2857 -> 5
    assert mo_hinh.tong_30_ngay([0.0] * 5) == 0
    assert mo_hinh.tong_30_ngay([10.0, 10.0, 10.0, 10.0]) == 40  # thiếu tuần thứ 5 coi như 0


def test_du_bao_tuan_chon_mo_hinh_theo_do_dai_chuoi():
    ten_ngan = mo_hinh.du_bao_tuan([5.0] * 11)[1]
    ten_dai = mo_hinh.du_bao_tuan([5.0] * 12)[1]
    assert (ten_ngan, ten_dai) == (mo_hinh.MO_HINH_TRUNG_BINH_TRUOT, mo_hinh.MO_HINH_HOLT_WINTERS)


def test_holt_winters_bat_xu_huong_va_khong_am():
    tang, ten = mo_hinh.du_bao_tuan([10.0 + 2 * i for i in range(14)])
    assert (
        ten == mo_hinh.MO_HINH_HOLT_WINTERS and tang[0] > 30 and tang[4] > tang[0]
    )  # đang tăng nên dự báo vượt tuần cuối
    giam, _ = mo_hinh.du_bao_tuan([max(0.0, 60.0 - 6 * i) for i in range(14)])
    assert all(x >= 0 for x in giam)  # xu hướng giảm sâu không cho nhu cầu âm
    phang, _ = mo_hinh.du_bao_tuan([5.0] * 14)
    assert all(x == pytest.approx(5.0, abs=0.5) for x in phang)


def test_holt_winters_loi_thi_quay_ve_trung_binh_truot(monkeypatch):
    monkeypatch.setattr(mo_hinh, "_holt_winters", lambda chuoi, so_tuan: None)
    du_bao, ten = mo_hinh.du_bao_tuan([float(i) for i in range(20)])
    assert ten == mo_hinh.MO_HINH_TRUNG_BINH_TRUOT and du_bao == mo_hinh.trung_binh_truot(
        [float(i) for i in range(20)], 5
    )


def test_mape_4_tuan():
    assert mo_hinh.mape_4_tuan([10, 20, 30, 40]) is None  # chưa có tuần huấn luyện trước 4 tuần đánh giá
    assert mo_hinh.mape_4_tuan([10.0] * 8) == 0.0
    assert mo_hinh.mape_4_tuan([10, 10, 10, 10, 20, 20, 20, 20]) == 25.0  # (50 + 30 + 15 + 5) / 4 %
    # chỉ tuần cuối tính (thực tế 10, dự báo (5*1)/10 = 0.5); 3 tuần thực tế 0 bị bỏ
    assert mo_hinh.mape_4_tuan([5, 5, 5, 5, 0, 0, 0, 10]) == pytest.approx(95.0, abs=0.001)
    assert mo_hinh.mape_4_tuan([5, 5, 5, 5, 0, 0, 0, 0]) is None
    assert mo_hinh.mape_4_tuan([0.0] * 3 + [1.0] + [1000.0] * 4) <= mo_hinh.MAPE_TOI_DA


def test_de_xuat_nhap():
    assert mo_hinh.de_xuat_nhap(100, 20, 50) == 70
    assert mo_hinh.de_xuat_nhap(10, 0, 50) == 0
    assert mo_hinh.de_xuat_nhap(0, 20, 5) == 15


def test_lich_tuan_co_ai09_thu_hai():
    assert ("ai09_du_bao_nhu_cau", "mon") in [(t, thu) for t, _, thu, *_ in LICH_TUAN]


# --- dữ liệu ---


def tuan_truoc(k: int):
    """Đầu tuần hiện tại lùi `k` tuần."""
    return dau_tuan(hom_nay_vn()) - timedelta(weeks=k)


def luc_xuat(k: int) -> datetime:
    """Thứ Tư 10:00 giờ VN của tuần cách đây `k` tuần, ở UTC."""
    return datetime.combine(tuan_truoc(k) + timedelta(days=2), time(10), tzinfo=VN_TZ).astimezone(UTC)


async def xuat(db, sp, lo, theo_tuan: dict[int, int], trang_thai="da_xuat"):
    """`theo_tuan`: {số tuần trước: số lượng cơ sở đã xuất}."""
    khach = await tao_khach(db)
    for k, so in theo_tuan.items():
        don = await tao_don(db, khach, "hoan_tat", dong=[{"san_pham": sp, "so_luong": 1}])
        ct_id = await db.scalar(select(CtDonHang.id).where(CtDonHang.don_hang_id == don.id))
        db.add(
            PhanBoLo(
                ct_don_hang_id=ct_id, lo_id=lo.id, so_luong_co_so=so, gia_von=Decimal(1000),
                trang_thai=trang_thai, updated_at=luc_xuat(k),
            )
        )  # fmt: skip
    await db.flush()


async def san_pham_co_ban(db, ten, theo_tuan, *, ton=0, toi_thieu=0, **kw):
    sp = await tao_san_pham(db, ten=f"{ten}-{uuid.uuid4().hex[:5]}", ton_toi_thieu=toi_thieu, **kw)
    lo = await tao_lo(db, sp, so_luong=ton)
    await xuat(db, sp, lo, theo_tuan)
    return sp, lo


async def de_xuat_cua(db, sp):
    return (await db.execute(select(DeXuatNhapHang).where(DeXuatNhapHang.san_pham_id == sp.id))).scalar_one_or_none()


async def tat_du_bao(db):
    gia_tri = dict.fromkeys(("tim_kiem", "chat", "tra_anh", "doc_don_thuoc", "goi_y"), True) | {"du_bao": False}
    cu = await db.get(CauHinh, "ai_module")
    if cu is None:
        db.add(CauHinh(khoa="ai_module", gia_tri=gia_tri))
    else:
        cu.gia_tri = gia_tri
    await db.flush()


# --- chuỗi theo tuần ---


async def test_chuoi_theo_tuan_gom_theo_tuan_vn_loai_tuan_hien_tai_va_trang_thai_khac(db):
    sp, lo = await san_pham_co_ban(db, "A", {1: 5, 3: 7})
    await xuat(db, sp, lo, {2: 100}, trang_thai="da_hoan_nhap")  # đã hoàn nhập: không phải nhu cầu thực
    await xuat(db, sp, lo, {0: 50})  # tuần đang diễn ra chưa đủ
    await xuat(db, sp, lo, {60: 9})  # quá 52 tuần
    await xuat(db, sp, lo, {1: 3})  # cùng tuần với 5 -> cộng dồn
    den = dau_tuan(hom_nay_vn())
    theo = (await chuoi_xuat_theo_tuan(db, den, [sp.id]))[sp.id]
    assert theo == {tuan_truoc(1): 8, tuan_truoc(3): 7}
    assert chuoi_day_du(theo, den) == [7.0, 0.0, 8.0]  # tuần 3 trước, 2 trước (0), 1 trước
    assert chuoi_day_du({}, den) == []


async def test_gom_tuan_theo_gio_viet_nam_khong_theo_utc(db):
    """Chủ nhật 23:30 giờ VN là 16:30 UTC cùng ngày; Thứ Hai 00:30 giờ VN vẫn là Chủ nhật 17:30 UTC: phải sang tuần sau."""
    sp, lo = await san_pham_co_ban(db, "B", {})
    khach = await tao_khach(db)
    chu_nhat = tuan_truoc(1) + timedelta(days=6)
    for gio_vn, so in (
        (datetime.combine(chu_nhat, time(23, 30), tzinfo=VN_TZ), 4),
        (datetime.combine(chu_nhat + timedelta(days=1), time(0, 30), tzinfo=VN_TZ), 6),
    ):
        don = await tao_don(db, khach, "hoan_tat", dong=[{"san_pham": sp, "so_luong": 1}])
        ct_id = await db.scalar(select(CtDonHang.id).where(CtDonHang.don_hang_id == don.id))
        db.add(
            PhanBoLo(
                ct_don_hang_id=ct_id,
                lo_id=lo.id,
                so_luong_co_so=so,
                gia_von=Decimal(1),
                trang_thai="da_xuat",
                updated_at=gio_vn.astimezone(UTC),
            )
        )
    await db.flush()
    theo = (await chuoi_xuat_theo_tuan(db, dau_tuan(hom_nay_vn()), [sp.id]))[sp.id]
    assert theo == {tuan_truoc(1): 4, tuan_truoc(0): 6} or theo == {tuan_truoc(1): 4}  # tuần 0 bị loại vì chưa đủ


# --- job ---


async def test_job_chon_mo_hinh_theo_do_dai_lich_su_va_tinh_de_xuat(db):
    dai, _ = await san_pham_co_ban(
        db, "Dài", {k: 20 + 2 * (14 - k) for k in range(1, 15)}, ton=30, toi_thieu=10
    )  # 14 tuần, đang tăng
    ngan, _ = await san_pham_co_ban(db, "Ngắn", {1: 10, 2: 20, 3: 30, 4: 40}, ton=5, toi_thieu=0)  # 4 tuần
    ky = dau_tuan(hom_nay_vn())
    kq = await ai09_du_bao_nhu_cau(db)
    assert kq.bo_qua is False and kq.ky_bat_dau == ky and kq.so_san_pham >= 2
    d_dai, d_ngan = await de_xuat_cua(db, dai), await de_xuat_cua(db, ngan)
    assert (d_dai.mo_hinh, d_ngan.mo_hinh) == ("holt_winters", "trung_binh_truot")
    assert d_dai.ky_bat_dau == ky and d_dai.ky_ket_thuc == ky + timedelta(days=29)
    # Ngắn: tuần cũ→mới 40,30,20,10, trọng số 1-2-3-4 = (40+60+60+40)/10 = 20/tuần -> 30 ngày = 4*20 + 2/7*20 = 85.7 -> 86
    assert d_ngan.so_luong_du_bao == 86 and d_ngan.ton_kha_dung == 5 and d_ngan.so_luong_de_xuat == 81
    assert d_ngan.sai_so_mape is None  # chưa đủ tuần để đánh giá (4 tuần = 4, cần > 4)
    assert d_dai.so_luong_du_bao > 4 * 48 and d_dai.so_luong_de_xuat == max(0, d_dai.so_luong_du_bao + 10 - 30)
    assert d_dai.sai_so_mape is not None and d_dai.sai_so_mape >= 0 and d_dai.da_xu_ly is False


async def test_job_san_pham_chua_ban_nhung_duoi_ton_toi_thieu_van_duoc_de_xuat(db):
    duoi = await tao_san_pham(db, ten=f"Dưới-{uuid.uuid4().hex[:5]}", ton_toi_thieu=20)
    await tao_lo(db, duoi, so_luong=5)
    du = await tao_san_pham(db, ten=f"Đủ-{uuid.uuid4().hex[:5]}", ton_toi_thieu=20)
    await tao_lo(db, du, so_luong=50)
    ngung = await tao_san_pham(db, ten=f"Ngừng-{uuid.uuid4().hex[:5]}", ton_toi_thieu=20, trang_thai="ngung_kinh_doanh")
    await ai09_du_bao_nhu_cau(db)
    d = await de_xuat_cua(db, duoi)
    assert (d.mo_hinh, d.so_luong_du_bao, d.so_luong_de_xuat, d.sai_so_mape) == ("khong_co_lich_su", 0, 15, None)
    assert await de_xuat_cua(db, du) is None and await de_xuat_cua(db, ngung) is None


async def test_job_ton_kha_dung_tru_hang_dang_giu_va_lo_het_han(db):
    sp, lo = await san_pham_co_ban(db, "Tồn", {1: 10}, ton=40, toi_thieu=0)
    lo.so_luong_giu = 15
    await tao_lo(db, sp, so_luong=100, han_su_dung=hom_nay_vn() - timedelta(days=1))  # lô hết hạn: không bán được
    await db.flush()
    await ai09_du_bao_nhu_cau(db)
    assert (await de_xuat_cua(db, sp)).ton_kha_dung == 25


async def test_job_chay_lai_trong_tuan_cap_nhat_va_giu_da_xu_ly(db):
    sp, lo = await san_pham_co_ban(db, "Lặp", {1: 10, 2: 10}, ton=0)
    await ai09_du_bao_nhu_cau(db)
    d = await de_xuat_cua(db, sp)
    d.da_xu_ly = True
    await db.flush()
    await xuat(db, sp, lo, {3: 50})  # có thêm dữ liệu rồi tính lại
    await ai09_du_bao_nhu_cau(db)
    dem = (await db.execute(select(DeXuatNhapHang).where(DeXuatNhapHang.san_pham_id == sp.id))).scalars().all()
    assert len(dem) == 1 and dem[0].id == d.id and dem[0].da_xu_ly is True
    await db.refresh(d)
    assert d.so_luong_du_bao > 0


async def test_job_tat_module_du_bao(db):
    sp, _ = await san_pham_co_ban(db, "Tắt", {1: 10})
    await tat_du_bao(db)
    kq = await chay_du_bao(db)
    assert kq.bo_qua is True and await de_xuat_cua(db, sp) is None


# --- KHO14 ---


async def tao_ky(db):
    """Hai sản phẩm có đề xuất (cần nhập / không cần) cho tuần hiện tại."""
    can, _ = await san_pham_co_ban(db, "Cần nhập", {1: 30, 2: 30, 3: 30}, ton=10, toi_thieu=5)
    khong, _ = await san_pham_co_ban(db, "Không cần", {1: 1}, ton=500)
    await ai09_du_bao_nhu_cau(db)
    return can, khong


async def test_kho_xem_danh_sach_mac_dinh_chi_can_nhap_va_loc(clients_theo_vai_tro, db):
    kho = clients_theo_vai_tro["WAREHOUSE"]
    can, khong = await tao_ky(db)
    r = await kho.get(BASE, params={"q": can.sku})
    assert r.status_code == 200
    d = r.json()["du_lieu"]
    assert [x["san_pham_id"] for x in d] == [can.id]
    x = d[0]
    assert (
        x["sku"] == can.sku
        and x["don_vi_co_so"] == "viên"
        and x["ton_toi_thieu"] == 5
        and x["so_luong_de_xuat"] > 0
        and x["da_xu_ly"] is False
    )
    assert x["mo_hinh"] == "trung_binh_truot" and x["ky_bat_dau"] == dau_tuan(hom_nay_vn()).isoformat()
    tat_ca = (await kho.get(BASE, params={"q": khong.sku, "chi_can_nhap": False})).json()["du_lieu"]
    assert [y["san_pham_id"] for y in tat_ca] == [khong.id] and tat_ca[0]["so_luong_de_xuat"] == 0
    assert (await kho.get(BASE, params={"q": khong.sku})).json()["du_lieu"] == []  # không cần nhập thì ẩn mặc định
    assert (await kho.get(BASE, params={"q": can.sku, "da_xu_ly": True})).json()["du_lieu"] == []


async def test_kho_danh_dau_da_xu_ly_va_bo_danh_dau(clients_theo_vai_tro, db):
    kho = clients_theo_vai_tro["WAREHOUSE"]
    can, _ = await tao_ky(db)
    d = await de_xuat_cua(db, can)
    r = await kho.put(f"{BASE}/{d.id}/da-xu-ly", json={"da_xu_ly": True})
    assert r.status_code == 200 and r.json()["da_xu_ly"] is True
    assert (await kho.get(BASE, params={"q": can.sku, "da_xu_ly": True})).json()["tong"] == 1
    assert (await kho.put(f"{BASE}/{d.id}/da-xu-ly", json={"da_xu_ly": False})).json()["da_xu_ly"] is False
    assert (await kho.put(f"{BASE}/{d.id}/da-xu-ly", json={})).status_code == 400
    assert (await kho.put(f"{BASE}/999999/da-xu-ly", json={"da_xu_ly": True})).status_code == 404


async def test_bieu_do_26_tuan_lich_su_va_5_tuan_du_bao(clients_theo_vai_tro, db):
    kho = clients_theo_vai_tro["WAREHOUSE"]
    can, _ = await tao_ky(db)
    d = await de_xuat_cua(db, can)
    r = await kho.get(f"{BASE}/{d.id}/bieu-do")
    assert r.status_code == 200
    b = r.json()
    ky = dau_tuan(hom_nay_vn())
    assert len(b["lich_su"]) == 26 and len(b["du_bao"]) == 5
    assert (
        b["lich_su"][-1]["tuan_bat_dau"] == (ky - timedelta(weeks=1)).isoformat()
        and b["lich_su"][0]["tuan_bat_dau"] == (ky - timedelta(weeks=26)).isoformat()
    )
    assert [p["so_luong"] for p in b["lich_su"][-3:]] == [30, 30, 30] and b["lich_su"][0]["so_luong"] == 0
    assert b["du_bao"][0]["tuan_bat_dau"] == ky.isoformat() and all(p["so_luong"] == 30 for p in b["du_bao"])
    assert b["mo_hinh"] == "trung_binh_truot" and b["don_vi_co_so"] == "viên"


async def test_cac_ky_va_ky_cu_theo_tham_so(clients_theo_vai_tro, db):
    kho = clients_theo_vai_tro["WAREHOUSE"]
    can, _ = await tao_ky(db)
    ky_cu = dau_tuan(hom_nay_vn()) - timedelta(weeks=1)
    db.add(
        DeXuatNhapHang(
            san_pham_id=can.id,
            ky_bat_dau=ky_cu,
            ky_ket_thuc=ky_cu + timedelta(days=29),
            so_luong_du_bao=1,
            ton_kha_dung=0,
            so_luong_de_xuat=1,
            mo_hinh="trung_binh_truot",
        )
    )
    await db.flush()
    ds = (await kho.get(f"{BASE}/ky")).json()
    assert [k["ky_bat_dau"] for k in ds[:2]] == [dau_tuan(hom_nay_vn()).isoformat(), ky_cu.isoformat()]
    cu = (await kho.get(BASE, params={"ky": ky_cu.isoformat(), "q": can.sku})).json()["du_lieu"]
    assert len(cu) == 1 and cu[0]["so_luong_du_bao"] == 1


async def test_phan_quyen_kho_day_du_admin_chi_xem_duoc_si_khong(clients_theo_vai_tro, db):
    can, _ = await tao_ky(db)
    d = await de_xuat_cua(db, can)
    admin, ds = clients_theo_vai_tro["ADMIN"], clients_theo_vai_tro["PHARMACIST"]
    assert (await admin.get(BASE)).status_code == 200 and (await admin.get(f"{BASE}/{d.id}/bieu-do")).status_code == 200
    assert (await admin.put(f"{BASE}/{d.id}/da-xu-ly", json={"da_xu_ly": True})).status_code == 403
    assert (await ds.get(BASE)).status_code == 403 and (await ds.get(f"{BASE}/ky")).status_code == 403


async def test_tim_kiem_khong_vo_voi_ky_tu_dac_biet(clients_theo_vai_tro, db):
    kho = clients_theo_vai_tro["WAREHOUSE"]
    await tao_ky(db)
    for q in ("\\", "%", "_", "a\\"):
        assert (await kho.get(BASE, params={"q": q})).status_code == 200

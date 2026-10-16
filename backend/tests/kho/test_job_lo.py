"""HT01, HT02, dọn lịch sử và bộ chạy job (advisory lock)."""

from datetime import timedelta

from sqlalchemy import func, select

from app.core.thoi_gian import bay_gio_utc, hom_nay_vn
from app.jobs.chay import chay_job
from app.jobs.cong_viec import don_lich_su, ht01_cap_nhat_lo, ht02_canh_bao_kho
from app.models.ai import LichSuXem
from app.models.ban_hang import CtDonHang, PhanBoLo
from app.models.khach_hang import ThongBao
from app.modules.kho import ton_kho
from app.modules.kho.lo_hang_ngay import cap_nhat_trang_thai_lo
from tests.factories import tao_don, tao_lo, tao_nhan_vien, tao_san_pham


def ngay(n):
    return hom_nay_vn() + timedelta(days=n)


async def test_ht01_chuyen_can_han_het_han_va_ve_dang_ban(db):
    sp = await tao_san_pham(db)
    a = await tao_lo(db, sp, so_luong=5, han_su_dung=ngay(30), trang_thai="dang_ban")  # < 90 ngày → cận hạn
    b = await tao_lo(db, sp, so_luong=5, han_su_dung=ngay(0), trang_thai="can_han")  # hết hạn hôm nay
    c = await tao_lo(db, sp, so_luong=5, han_su_dung=ngay(200), trang_thai="can_han")  # xa hơn ngưỡng → đang bán
    d = await tao_lo(db, sp, so_luong=5, han_su_dung=ngay(-3), trang_thai="khoa")  # Admin khóa: không đụng
    e = await tao_lo(db, sp, so_luong=5, han_su_dung=ngay(-3), trang_thai="thu_hoi")
    f = await tao_lo(db, sp, so_luong=5, han_su_dung=ngay(300), trang_thai="dang_ban")  # không đổi
    kq = await cap_nhat_trang_thai_lo(db)
    assert (kq.sang_can_han, kq.sang_het_han, kq.ve_dang_ban) == (1, 1, 1)
    for lo, mong in ((a, "can_han"), (b, "het_han"), (c, "dang_ban"), (d, "khoa"), (e, "thu_hoi"), (f, "dang_ban")):
        await db.refresh(lo)
        assert lo.trang_thai.value == mong
    again = await cap_nhat_trang_thai_lo(db)
    assert (again.sang_can_han, again.sang_het_han, again.ve_dang_ban) == (0, 0, 0)  # chạy lại không đổi gì


async def test_ht01_go_lo_het_han_khoi_don_chua_xuat_va_phan_bo_lai_fefo(db):
    sp = await tao_san_pham(db)
    lo_cu = await tao_lo(db, sp, so_luong=10, han_su_dung=ngay(60), trang_thai="can_han")
    lo_moi = await tao_lo(db, sp, so_luong=10, han_su_dung=ngay(300))
    don = await tao_don(db, dong=[{"san_pham": sp, "so_luong": 4}])
    ct = (await db.execute(select(CtDonHang).where(CtDonHang.don_hang_id == don.id))).scalar_one()
    await ton_kho.giu_hang(db, ct, 4, cho_phep_can_han=True)  # giữ ở lô hạn gần (cận hạn)
    lo_cu.han_su_dung = ngay(0)  # hết hạn trước giờ job chạy
    await db.flush()
    kq = await cap_nhat_trang_thai_lo(db)
    assert kq.sang_het_han == 1 and kq.phan_bo_lai == 1 and kq.don_thieu_hang == []
    await db.refresh(lo_cu)
    await db.refresh(lo_moi)
    assert (lo_cu.so_luong_giu, lo_moi.so_luong_giu) == (0, 4)
    pb = (await db.execute(select(PhanBoLo).where(PhanBoLo.trang_thai == "dang_giu"))).scalars().all()
    assert [(p.lo_id, p.so_luong_co_so) for p in pb] == [(lo_moi.id, 4)]


async def test_ht01_khong_con_hang_thay_the_thi_bao_don_thieu_hang(db):
    sp = await tao_san_pham(db)
    lo = await tao_lo(db, sp, so_luong=10, han_su_dung=ngay(60), trang_thai="can_han")
    don = await tao_don(db, dong=[{"san_pham": sp, "so_luong": 4}])
    ct = (await db.execute(select(CtDonHang).where(CtDonHang.don_hang_id == don.id))).scalar_one()
    await ton_kho.giu_hang(db, ct, 4, cho_phep_can_han=True)
    lo.han_su_dung = ngay(0)
    await db.flush()
    kq = await cap_nhat_trang_thai_lo(db)
    assert kq.don_thieu_hang == [don.ma_don] and kq.phan_bo_lai == 0
    kho = await tao_nhan_vien(db, "WAREHOUSE")
    await ht01_cap_nhat_lo(db)  # lần hai: không còn lô nào đổi → không thông báo thêm
    assert (await db.scalar(select(func.count()).select_from(ThongBao).where(ThongBao.nhan_vien_id == kho.id))) == 0


async def test_ht02_moi_loai_mot_thong_bao_moi_ngay_cho_nhan_vien_kho(db):
    kho1, kho2 = await tao_nhan_vien(db, "WAREHOUSE"), await tao_nhan_vien(db, "WAREHOUSE")
    ds = await tao_nhan_vien(db, "PHARMACIST")
    sp = await tao_san_pham(db, ton_toi_thieu=100)
    await tao_lo(db, sp, so_luong=5)
    await tao_lo(db, sp, so_luong=5, han_su_dung=ngay(30), trang_thai="can_han")
    await tao_lo(db, sp, so_luong=5, han_su_dung=ngay(-1), trang_thai="het_han")
    assert await ht02_canh_bao_kho(db) == 6  # 3 loại x 2 nhân viên kho
    assert await ht02_canh_bao_kho(db) == 0  # cùng ngày: không gửi trùng
    loai = set((await db.execute(select(ThongBao.loai).where(ThongBao.nhan_vien_id == kho1.id))).scalars())
    assert loai == {"canh_bao_ton_thap", "canh_bao_can_han", "canh_bao_het_han"}
    dem = select(func.count()).select_from(ThongBao)
    assert await db.scalar(dem.where(ThongBao.nhan_vien_id == ds.id)) == 0
    assert await db.scalar(dem.where(ThongBao.nhan_vien_id == kho2.id)) == 3
    # sang ngày mới (lùi mốc thời gian của thông báo cũ) thì gửi lại
    await db.execute(ThongBao.__table__.update().values(created_at=bay_gio_utc() - timedelta(days=2)))
    assert await ht02_canh_bao_kho(db) == 6


async def test_ht02_khong_co_gi_de_canh_bao_thi_khong_gui(db):
    await tao_nhan_vien(db, "WAREHOUSE")
    sp = await tao_san_pham(db, ton_toi_thieu=10)
    await tao_lo(db, sp, so_luong=50)
    assert await ht02_canh_bao_kho(db) == 0


async def test_don_lich_su_chi_xoa_ban_ghi_cu(db):
    sp = await tao_san_pham(db)
    db.add_all(
        [
            LichSuXem(san_pham_id=sp.id, ma_phien="a", created_at=bay_gio_utc() - timedelta(days=100)),
            LichSuXem(san_pham_id=sp.id, ma_phien="b", created_at=bay_gio_utc() - timedelta(days=5)),
        ]
    )
    await db.flush()
    assert await don_lich_su(db) == 1
    assert (await db.scalar(select(func.count()).select_from(LichSuXem))) == 1


async def test_chay_job_chi_mot_noi_chay_tai_mot_thoi_diem(db_that, engine_test):
    import asyncio

    dang_chay = asyncio.Event()
    xong = asyncio.Event()

    async def cham(_db):
        dang_chay.set()
        await xong.wait()
        return "ok"

    async def nhanh(_db):
        return "nhanh"

    viec = asyncio.create_task(chay_job(engine_test, "thu", cham))
    await dang_chay.wait()
    assert await chay_job(engine_test, "thu", nhanh) is None  # trùng khóa: bỏ qua
    assert await chay_job(engine_test, "khac", nhanh) == "nhanh"  # job khác không bị chặn
    xong.set()
    assert await viec == "ok"
    assert await chay_job(engine_test, "thu", nhanh) == "nhanh"  # đã nhả khóa

"""Các hàm đổi tồn còn lại của `ton_kho.py` (spec 04 mục 3): giữ hàng FEFO, nhả, xuất, hoàn nhập, biệt trữ, trừ tồn, điều chỉnh."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc, hom_nay_vn
from app.models.ban_hang import CtDonHang, PhanBoLo
from app.models.enums import KhuTon, LoaiBienDong, TrangThaiPhanBo
from app.models.kho import BienDongKho
from app.models.san_pham import SanPham
from app.modules.kho import ton_kho
from app.modules.kho.ton_kho import ChungTu, YeuCauGiu
from tests.factories import tao_don, tao_lo, tao_nhan_vien, tao_san_pham

CT = ChungTu("don_hang", 1, None)


async def the_kho(db, lo_id) -> list[BienDongKho]:
    return list(
        (await db.execute(select(BienDongKho).where(BienDongKho.lo_id == lo_id).order_by(BienDongKho.id))).scalars()
    )


async def dong_don(db, san_pham, so_luong=1):
    """Dòng đơn (`CtDonHang`) của một đơn mới có đúng một dòng."""
    don = await tao_don(db, dong=[{"san_pham": san_pham, "so_luong": so_luong}])
    return (await db.execute(select(CtDonHang).where(CtDonHang.don_hang_id == don.id))).scalar_one()


def ngay(so_ngay: int):
    return hom_nay_vn() + timedelta(days=so_ngay)


# --- giữ hàng ---------------------------------------------------------------------------------------------------


async def test_giu_hang_chon_lo_het_han_truoc_va_tach_nhieu_lo(db):
    sp = await tao_san_pham(db)
    lo_xa = await tao_lo(db, sp, so_luong=50, han_su_dung=ngay(400))
    lo_gan = await tao_lo(db, sp, so_luong=30, han_su_dung=ngay(200), gia_nhap=777)
    ct = await dong_don(db, sp)

    phan_bo = await ton_kho.giu_hang(db, ct, 45)

    assert [(p.lo_id, p.so_luong_co_so) for p in phan_bo] == [(lo_gan.id, 30), (lo_xa.id, 15)]
    assert all(p.trang_thai == TrangThaiPhanBo.dang_giu and p.ct_don_hang_id == ct.id for p in phan_bo)
    assert phan_bo[0].gia_von == 777  # bản chụp giá nhập của lô lúc giữ
    assert (lo_gan.so_luong_giu, lo_xa.so_luong_giu) == (30, 15)
    assert (lo_gan.so_luong_ton, lo_xa.so_luong_ton) == (30, 50)  # giữ chưa đổi tồn thật
    assert (
        len(await the_kho(db, lo_gan.id)) == 1 and len(await the_kho(db, lo_xa.id)) == 1
    )  # chỉ thẻ nhập, không thẻ giữ


async def test_giu_hang_tinh_ton_kha_dung_tru_phan_dang_giu(db):
    sp = await tao_sanpham_voi_hai_lo(db)
    lo_1, lo_2 = sp[1]
    ct = await dong_don(db, sp[0])
    phan_bo = await ton_kho.giu_hang(db, ct, 12)  # lô 1 khả dụng 10 (đã giữ 0), lấy hết rồi sang lô 2
    assert [(p.lo_id, p.so_luong_co_so) for p in phan_bo] == [(lo_1.id, 10), (lo_2.id, 2)]
    ct2 = await dong_don(db, sp[0])
    phan_bo2 = await ton_kho.giu_hang(db, ct2, 3)  # lô 1 hết khả dụng, lô 2 còn 8
    assert [(p.lo_id, p.so_luong_co_so) for p in phan_bo2] == [(lo_2.id, 3)]


async def tao_sanpham_voi_hai_lo(db):
    sp = await tao_san_pham(db)
    lo_1 = await tao_lo(db, sp, so_luong=10, han_su_dung=ngay(200))
    lo_2 = await tao_lo(db, sp, so_luong=10, han_su_dung=ngay(300))
    return sp, (lo_1, lo_2)


async def test_giu_hang_khong_du_thi_het_hang_va_khong_giu_gi(db):
    sp = await tao_san_pham(db, ten="Thuốc thử")
    lo = await tao_lo(db, sp, so_luong=5)
    ct = await dong_don(db, sp)
    with pytest.raises(LoiNghiepVu) as loi:
        await ton_kho.giu_hang(db, ct, 6)
    assert loi.value.ma_loi == "HET_HANG"
    assert loi.value.chi_tiet == {"san_pham_id": sp.id, "con_lai": 5}
    assert "Thuốc thử" in loi.value.thong_diep
    assert lo.so_luong_giu == 0
    assert (await db.execute(select(PhanBoLo))).first() is None


async def test_giu_hang_online_bo_qua_lo_can_han_nhung_tai_quay_dung_duoc(db):
    sp = await tao_san_pham(db)
    lo_can = await tao_lo(db, sp, so_luong=10, han_su_dung=ngay(30), trang_thai="can_han")
    ct = await dong_don(db, sp)
    with pytest.raises(LoiNghiepVu) as loi:
        await ton_kho.giu_hang(db, ct, 1)  # đơn online chỉ dùng lô Đang bán
    assert loi.value.chi_tiet["con_lai"] == 0
    phan_bo = await ton_kho.giu_hang(db, ct, 4, cho_phep_can_han=True)
    assert [(p.lo_id, p.so_luong_co_so) for p in phan_bo] == [(lo_can.id, 4)]


@pytest.mark.parametrize("trang_thai", ["khoa", "het_han", "thu_hoi"])
async def test_giu_hang_bo_qua_lo_khoa_het_han_thu_hoi(db, trang_thai):
    sp = await tao_san_pham(db)
    await tao_lo(db, sp, so_luong=10, trang_thai=trang_thai)
    ct = await dong_don(db, sp)
    with pytest.raises(LoiNghiepVu) as loi:
        await ton_kho.giu_hang(db, ct, 1, cho_phep_can_han=True)
    assert loi.value.ma_loi == "HET_HANG"


async def test_giu_hang_bo_qua_lo_het_han_su_dung_du_trang_thai_chua_cap_nhat(db):
    """Job HT01 chạy 00:05; trong khoảng đó lô hết hạn hôm nay vẫn nhãn `dang_ban` nhưng không được bán."""
    sp = await tao_san_pham(db)
    await tao_lo(db, sp, so_luong=10, han_su_dung=hom_nay_vn(), trang_thai="dang_ban")
    con_han = await tao_lo(db, sp, so_luong=10, han_su_dung=ngay(1), trang_thai="dang_ban")
    ct = await dong_don(db, sp)
    phan_bo = await ton_kho.giu_hang(db, ct, 3)
    assert [p.lo_id for p in phan_bo] == [con_han.id]


async def test_giu_hang_nhieu_dong_cung_san_pham_khong_giu_trung_phan(db):
    sp = await tao_san_pham(db)
    lo = await tao_lo(db, sp, so_luong=10)
    ct_a, ct_b = await dong_don(db, sp), await dong_don(db, sp)
    ket_qua = await ton_kho.giu_hang_nhieu(db, [YeuCauGiu(ct_a.id, sp.id, 6), YeuCauGiu(ct_b.id, sp.id, 4)])
    assert [p.so_luong_co_so for p in ket_qua[ct_a.id]] == [6] and [p.so_luong_co_so for p in ket_qua[ct_b.id]] == [4]
    assert lo.so_luong_giu == 10
    with pytest.raises(LoiNghiepVu):
        await ton_kho.giu_hang_nhieu(db, [YeuCauGiu(ct_a.id, sp.id, 1)])


async def test_giu_hang_nhieu_dong_that_bai_o_dong_sau_thi_khong_giu_dong_truoc(db):
    sp_a, sp_b = await tao_san_pham(db), await tao_san_pham(db)
    lo_a = await tao_lo(db, sp_a, so_luong=10)
    await tao_lo(db, sp_b, so_luong=1)
    ct_a, ct_b = await dong_don(db, sp_a), await dong_don(db, sp_b)
    with pytest.raises(LoiNghiepVu) as loi:
        await ton_kho.giu_hang_nhieu(db, [YeuCauGiu(ct_a.id, sp_a.id, 5), YeuCauGiu(ct_b.id, sp_b.id, 2)])
    assert loi.value.chi_tiet["san_pham_id"] == sp_b.id
    await db.refresh(lo_a)
    assert (
        lo_a.so_luong_giu == 0
    )  # gọi lại trong transaction của request: lỗi làm rollback; ở đây ta kiểm không để lại phân bổ
    assert (await db.execute(select(PhanBoLo))).first() is None


@pytest.mark.parametrize("so_luong", [0, -1])
async def test_giu_hang_so_luong_phai_duong(db, so_luong):
    sp = await tao_san_pham(db)
    await tao_lo(db, sp, so_luong=5)
    ct = await dong_don(db, sp)
    with pytest.raises(ValueError):
        await ton_kho.giu_hang(db, ct, so_luong)


# --- nhả, xuất, hoàn nhập -----------------------------------------------------------------------------------------


async def giu(db, so_luong_lo=10, so_luong_giu=4):
    sp = await tao_san_pham(db)
    lo = await tao_lo(db, sp, so_luong=so_luong_lo)
    ct = await dong_don(db, sp)
    (phan_bo,) = await ton_kho.giu_hang(db, ct, so_luong_giu)
    return lo, phan_bo


async def test_nha_giu_tra_lai_ton_kha_dung_va_khong_ghi_the_kho(db):
    lo, phan_bo = await giu(db)
    await ton_kho.nha_giu(db, phan_bo)
    assert phan_bo.trang_thai == TrangThaiPhanBo.da_nha
    assert (lo.so_luong_giu, lo.so_luong_ton) == (0, 10)
    assert len(await the_kho(db, lo.id)) == 1


async def test_nha_giu_hai_lan_bi_tu_choi(db):
    lo, phan_bo = await giu(db)
    await ton_kho.nha_giu(db, phan_bo)
    with pytest.raises(LoiNghiepVu) as loi:
        await ton_kho.nha_giu(db, phan_bo)
    assert loi.value.ma_loi == "CHUYEN_TRANG_THAI_KHONG_HOP_LE"
    assert lo.so_luong_giu == 0


async def test_xuat_theo_phan_bo_tru_ton_va_giu_va_ghi_the_kho(db):
    lo, phan_bo = await giu(db)
    nv = await tao_nhan_vien(db, "WAREHOUSE")
    await ton_kho.xuat_theo_phan_bo(db, phan_bo, ChungTu("don_hang", 55, nv.id))
    assert phan_bo.trang_thai == TrangThaiPhanBo.da_xuat
    assert (lo.so_luong_ton, lo.so_luong_giu) == (6, 0)
    the = (await the_kho(db, lo.id))[-1]
    assert (the.loai, the.khu, the.so_luong, the.ton_sau) == (LoaiBienDong.xuat_ban, KhuTon.kho_ban, -4, 6)
    assert (the.chung_tu_loai, the.chung_tu_id, the.nhan_vien_id) == ("don_hang", 55, nv.id)


async def test_xuat_phan_bo_chua_giu_hoac_da_xuat_bi_tu_choi(db):
    lo, phan_bo = await giu(db)
    await ton_kho.nha_giu(db, phan_bo)
    with pytest.raises(LoiNghiepVu):
        await ton_kho.xuat_theo_phan_bo(db, phan_bo, CT)
    lo2, phan_bo2 = await giu(db)
    await ton_kho.xuat_theo_phan_bo(db, phan_bo2, CT)
    with pytest.raises(LoiNghiepVu):
        await ton_kho.xuat_theo_phan_bo(db, phan_bo2, CT)
    assert lo2.so_luong_ton == 6


async def test_hoan_nhap_cong_lai_ton_dung_lo(db):
    lo, phan_bo = await giu(db)
    await ton_kho.xuat_theo_phan_bo(db, phan_bo, CT)
    await ton_kho.hoan_nhap(db, phan_bo, CT)
    assert phan_bo.trang_thai == TrangThaiPhanBo.da_hoan_nhap
    assert (lo.so_luong_ton, lo.so_luong_giu) == (10, 0)
    the = (await the_kho(db, lo.id))[-1]
    assert (the.loai, the.khu, the.so_luong, the.ton_sau) == (LoaiBienDong.hoan_nhap, KhuTon.kho_ban, 4, 10)


async def test_hoan_nhap_phan_bo_chua_xuat_bi_tu_choi(db):
    lo, phan_bo = await giu(db)
    with pytest.raises(LoiNghiepVu) as loi:
        await ton_kho.hoan_nhap(db, phan_bo, CT)
    assert loi.value.ma_loi == "CHUYEN_TRANG_THAI_KHONG_HOP_LE"
    assert lo.so_luong_ton == 10


async def test_hoan_nhap_vao_lo_cua_san_pham_da_xoa_bi_tu_choi(db):
    lo, phan_bo = await giu(db)
    await ton_kho.xuat_theo_phan_bo(db, phan_bo, CT)
    (await db.get(SanPham, lo.san_pham_id)).deleted_at = bay_gio_utc()
    await db.flush()
    with pytest.raises(LoiNghiepVu) as loi:
        await ton_kho.hoan_nhap(db, phan_bo, CT)
    assert loi.value.ma_loi == "KHONG_TIM_THAY"


async def test_xuat_nhieu_phan_bo_ghi_the_kho_cho_tung_lo(db):
    sp = await tao_san_pham(db)
    lo_1 = await tao_lo(db, sp, so_luong=5, han_su_dung=ngay(500))
    lo_2 = await tao_lo(db, sp, so_luong=5, han_su_dung=ngay(100))
    ct = await dong_don(db, sp)
    phan_bo = await ton_kho.giu_hang(db, ct, 8)  # lấy lô 2 (hạn gần) trước, rồi lô 1
    assert [p.lo_id for p in phan_bo] == [lo_2.id, lo_1.id]
    the = await ton_kho.xuat_theo_phan_bo(db, phan_bo, CT)
    assert (lo_1.so_luong_ton, lo_2.so_luong_ton) == (2, 0)
    assert {(t.lo_id, t.so_luong, t.ton_sau) for t in the} == {(lo_2.id, -5, 0), (lo_1.id, -3, 2)}


# --- biệt trữ, trừ tồn, điều chỉnh --------------------------------------------------------------------------------


async def test_vao_biet_tru_cong_khu_biet_tru_khong_dong_den_ton_ban(db):
    lo = await tao_lo(db, so_luong=10)
    bien_dong = await ton_kho.vao_biet_tru(db, lo, 3, ChungTu("yeu_cau_doi_tra", 9, None))
    assert (lo.so_luong_biet_tru, lo.so_luong_ton) == (3, 10)
    assert (bien_dong.loai, bien_dong.khu, bien_dong.so_luong, bien_dong.ton_sau) == (
        LoaiBienDong.nhan_tra_ve,
        KhuTon.biet_tru,
        3,
        3,
    )
    await ton_kho.vao_biet_tru(db, lo, 2, ChungTu("yeu_cau_doi_tra", 10, None))
    assert lo.so_luong_biet_tru == 5 and (await the_kho(db, lo.id))[-1].ton_sau == 5


async def test_tru_ton_kho_ban_cho_huy_va_xuat_tra(db):
    lo = await tao_lo(db, so_luong=10)
    bd = await ton_kho.tru_ton(db, lo, 4, KhuTon.kho_ban, LoaiBienDong.huy_hang, ChungTu("phieu_huy", 3, None))
    assert lo.so_luong_ton == 6
    assert (bd.loai, bd.khu, bd.so_luong, bd.ton_sau) == (LoaiBienDong.huy_hang, KhuTon.kho_ban, -4, 6)
    bd = await ton_kho.tru_ton(db, lo, 1, KhuTon.kho_ban, LoaiBienDong.xuat_tra_ncc, ChungTu("phieu_xuat_tra", 4, None))
    assert (lo.so_luong_ton, bd.loai) == (5, LoaiBienDong.xuat_tra_ncc)


async def test_tru_ton_kho_ban_khong_duoc_lam_ton_kha_dung_am(db):
    sp = await tao_san_pham(db)
    lo = await tao_lo(db, sp, so_luong=10)
    ct = await dong_don(db, sp)
    await ton_kho.giu_hang(db, ct, 7)  # còn khả dụng 3
    with pytest.raises(LoiNghiepVu) as loi:
        await ton_kho.tru_ton(db, lo, 4, KhuTon.kho_ban, LoaiBienDong.huy_hang, CT)
    assert loi.value.ma_loi == "HET_HANG"
    assert loi.value.chi_tiet == {"lo_id": lo.id, "con_lai": 3}
    assert lo.so_luong_ton == 10
    await ton_kho.tru_ton(db, lo, 3, KhuTon.kho_ban, LoaiBienDong.huy_hang, CT)
    assert (lo.so_luong_ton, lo.so_luong_giu) == (7, 7)


async def test_tru_ton_khu_biet_tru(db):
    lo = await tao_lo(db, so_luong=10)
    await ton_kho.vao_biet_tru(db, lo, 5, CT)
    bd = await ton_kho.tru_ton(db, lo, 2, KhuTon.biet_tru, LoaiBienDong.huy_hang, CT)
    assert (lo.so_luong_biet_tru, lo.so_luong_ton) == (3, 10)
    assert (bd.khu, bd.so_luong, bd.ton_sau) == (KhuTon.biet_tru, -2, 3)
    with pytest.raises(LoiNghiepVu) as loi:
        await ton_kho.tru_ton(db, lo, 4, KhuTon.biet_tru, LoaiBienDong.xuat_tra_ncc, CT)
    assert loi.value.ma_loi == "HET_HANG"
    assert lo.so_luong_biet_tru == 3


@pytest.mark.parametrize("loai", [LoaiBienDong.nhap_kho, LoaiBienDong.xuat_ban, LoaiBienDong.dieu_chinh])
async def test_tru_ton_chi_nhan_loai_huy_hoac_xuat_tra(db, loai):
    lo = await tao_lo(db, so_luong=10)
    with pytest.raises(ValueError):
        await ton_kho.tru_ton(db, lo, 1, KhuTon.kho_ban, loai, CT)


async def test_dieu_chinh_tang_giam_va_ghi_the_kho(db):
    lo = await tao_lo(db, so_luong=10)
    bd = await ton_kho.dieu_chinh(db, lo, 5, ChungTu("phieu_dieu_chinh", 2, None))
    assert lo.so_luong_ton == 15 and (bd.loai, bd.so_luong, bd.ton_sau) == (LoaiBienDong.dieu_chinh, 5, 15)
    bd = await ton_kho.dieu_chinh(db, lo, -12, ChungTu("phieu_dieu_chinh", 3, None))
    assert lo.so_luong_ton == 3 and (bd.so_luong, bd.ton_sau) == (-12, 3)


async def test_dieu_chinh_khong_duoc_xuong_duoi_so_dang_giu_hoac_am(db):
    sp = await tao_san_pham(db)
    lo = await tao_lo(db, sp, so_luong=10)
    ct = await dong_don(db, sp)
    await ton_kho.giu_hang(db, ct, 6)
    with pytest.raises(LoiNghiepVu) as loi:
        await ton_kho.dieu_chinh(db, lo, -5, CT)  # còn 5 < đang giữ 6
    assert loi.value.ma_loi == "HET_HANG"
    assert loi.value.chi_tiet == {"lo_id": lo.id, "con_lai": 4}
    assert lo.so_luong_ton == 10
    await ton_kho.dieu_chinh(db, lo, -4, CT)
    assert lo.so_luong_ton == 6


async def test_dieu_chinh_bang_khong_la_loi_va_khong_nhan_float(db):
    lo = await tao_lo(db, so_luong=10)
    with pytest.raises(ValueError):
        await ton_kho.dieu_chinh(db, lo, 0, CT)
    with pytest.raises(TypeError):
        await ton_kho.dieu_chinh(db, lo, 1.5, CT)  # type: ignore[arg-type]


async def test_dieu_chinh_tang_lo_cua_san_pham_da_xoa_bi_tu_choi_con_giam_thi_duoc(db):
    sp = await tao_san_pham(db)
    lo = await tao_lo(db, sp, so_luong=10)
    (await db.get(SanPham, sp.id)).deleted_at = bay_gio_utc()
    await db.flush()
    with pytest.raises(LoiNghiepVu):
        await ton_kho.dieu_chinh(db, lo, 1, CT)
    await ton_kho.dieu_chinh(db, lo, -1, CT)
    assert lo.so_luong_ton == 9


async def test_vao_biet_tru_lo_cua_san_pham_da_xoa_bi_tu_choi(db):
    sp = await tao_san_pham(db)
    lo = await tao_lo(db, sp, so_luong=10)
    (await db.get(SanPham, sp.id)).deleted_at = bay_gio_utc()
    await db.flush()
    with pytest.raises(LoiNghiepVu):
        await ton_kho.vao_biet_tru(db, lo, 1, CT)

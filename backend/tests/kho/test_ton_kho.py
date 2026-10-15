"""Dịch vụ tồn kho `modules/kho/ton_kho.py` (spec 04 mục 3): chỉ phần nhập kho ở T0.5; các hàm còn lại ở T3.1."""

from datetime import date

import pytest
from sqlalchemy import select, text

from app.models.enums import KhuTon, LoaiBienDong
from app.models.kho import BienDongKho, LoThuoc
from app.modules.kho.ton_kho import ChungTu, khoa_cac_lo, nhap_kho
from tests.factories import tao_lo


async def the_kho(db, lo_id) -> list[BienDongKho]:
    ket_qua = await db.execute(select(BienDongKho).where(BienDongKho.lo_id == lo_id).order_by(BienDongKho.id))
    return list(ket_qua.scalars())


async def test_nhap_kho_cong_ton_va_ghi_the_kho(db):
    lo = await tao_lo(db)
    bien_dong = await nhap_kho(db, lo, 100, ChungTu("phieu_nhap", 7, nhan_vien_id=None))
    assert lo.so_luong_ton == 100
    assert (bien_dong.loai, bien_dong.khu) == (LoaiBienDong.nhap_kho, KhuTon.kho_ban)
    assert (bien_dong.so_luong, bien_dong.ton_sau) == (100, 100)
    assert (bien_dong.chung_tu_loai, bien_dong.chung_tu_id) == ("phieu_nhap", 7)
    assert bien_dong.nhan_vien_id is None
    assert [b.id for b in await the_kho(db, lo.id)] == [bien_dong.id]


async def test_nhap_nhieu_lan_ton_sau_la_ton_luy_ke(db):
    lo = await tao_lo(db)
    chung_tu = ChungTu("phieu_nhap", 1, None)
    a = await nhap_kho(db, lo, 40, chung_tu)
    b = await nhap_kho(db, lo, 25, chung_tu)
    assert (a.ton_sau, b.ton_sau) == (40, 65)
    assert lo.so_luong_ton == 65
    assert sum(b.so_luong for b in await the_kho(db, lo.id)) == lo.so_luong_ton  # bất biến 3 (spec 04 mục 3.2)


async def test_nhap_vao_lo_da_co_ton_tinh_tiep_tu_ton_hien_co(db):
    lo = await tao_lo(db, so_luong_ton=10)  # tồn có sẵn nhưng chưa có thẻ kho (dữ liệu dựng tay)
    bien_dong = await nhap_kho(db, lo, 5, ChungTu("phieu_nhap", 1, None))
    assert (bien_dong.so_luong, bien_dong.ton_sau) == (5, 15)


@pytest.mark.parametrize("so_luong", [0, -1])
async def test_so_luong_phai_duong(db, so_luong):
    lo = await tao_lo(db)
    with pytest.raises(ValueError, match="so_luong"):
        await nhap_kho(db, lo, so_luong, ChungTu("phieu_nhap", 1, None))
    assert await the_kho(db, lo.id) == []
    assert lo.so_luong_ton == 0


async def test_so_luong_khong_duoc_la_float_hay_bool(db):
    lo = await tao_lo(db)
    for xau in (1.5, True, "5"):
        with pytest.raises(TypeError):
            await nhap_kho(db, lo, xau, ChungTu("phieu_nhap", 1, None))


async def test_lo_khong_ton_tai_bi_tu_choi(db):
    lo = LoThuoc(id=987654, san_pham_id=1, so_lo="X", han_su_dung=date(2030, 1, 1), gia_nhap=1)  # không có trong DB
    with pytest.raises(LookupError, match="987654"):
        await nhap_kho(db, lo, 1, ChungTu("phieu_nhap", 1, None))


async def test_khoa_cac_lo_tra_theo_id_tang_dan_va_khong_trung(db):
    a, b, c = await tao_lo(db), await tao_lo(db), await tao_lo(db)
    khoa = await khoa_cac_lo(db, [c.id, a.id, b.id, a.id])
    assert [lo.id for lo in khoa] == sorted({a.id, b.id, c.id})


async def test_khoa_cac_lo_thieu_lo_thi_bao_loi(db):
    a = await tao_lo(db)
    with pytest.raises(LookupError, match="424242"):
        await khoa_cac_lo(db, [a.id, 424242])


async def test_khoa_cac_lo_doc_gia_tri_moi_nhat_cua_lo_da_nap(db):
    """Đối tượng đã nạp từ trước phải được làm mới theo dòng vừa khóa (tránh ghi đè bằng số cũ)."""
    lo = await tao_lo(db, so_luong_ton=10)
    await db.execute(text("UPDATE lo_thuoc SET so_luong_ton = 99 WHERE id = :id"), {"id": lo.id})
    assert lo.so_luong_ton == 10  # đối tượng trong bộ nhớ đã cũ
    (khoa,) = await khoa_cac_lo(db, [lo.id])
    assert khoa is lo and lo.so_luong_ton == 99


async def test_nhap_kho_co_the_ghi_the_kho_vao_thoi_diem_cu(db):
    """Nhập dữ liệu cũ (seed, chuyển đổi): thẻ kho mang ngày của chứng từ gốc."""
    from datetime import UTC, datetime

    lo = await tao_lo(db)
    luc = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)
    bien_dong = await nhap_kho(db, lo, 10, ChungTu("phieu_nhap", 1), luc=luc)
    assert bien_dong.created_at == luc


async def test_khoa_cac_lo_phat_ra_order_by_id_va_for_update(db):
    """Thứ tự khóa là điều kiện chống deadlock nên kiểm ngay trong câu SQL (kết quả trả về luôn sắp xếp nên không đủ)."""
    from sqlalchemy import event

    a, b = await tao_lo(db), await tao_lo(db)
    cau_lenh: list[str] = []

    def ghi(conn, cursor, statement, *_):
        cau_lenh.append(statement)

    ket_noi = (await db.connection()).sync_connection
    event.listen(ket_noi, "before_cursor_execute", ghi)
    try:
        await khoa_cac_lo(db, [b.id, a.id])
    finally:
        event.remove(ket_noi, "before_cursor_execute", ghi)
    (truy_van,) = [c for c in cau_lenh if "FROM lo_thuoc" in c]
    assert "ORDER BY lo_thuoc.id" in truy_van and truy_van.rstrip().endswith("FOR UPDATE")

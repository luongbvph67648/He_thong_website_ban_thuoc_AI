"""Tranh chấp khi đổi tồn: giao dịch thứ hai phải chờ khóa lô rồi mới tính trên tồn mới nhất (spec 02 mục 5)."""

import asyncio

from sqlalchemy import select

from app.models.kho import BienDongKho, LoThuoc
from app.modules.kho.ton_kho import ChungTu, nhap_kho
from tests.factories import tao_lo


async def test_nhap_kho_cho_khoa_lo_roi_tinh_tren_ton_moi_nhat(db_that):
    async with db_that() as s, s.begin():
        lo_id = (await tao_lo(s)).id

    async with db_that() as a, db_that() as b:
        await a.begin()
        await b.begin()
        lo_a = await a.get(LoThuoc, lo_id)
        lo_b = await b.get(LoThuoc, lo_id)  # b nạp lô khi tồn còn 0; sau đó bản trong bộ nhớ của b sẽ cũ
        assert lo_b.so_luong_ton == 0

        await nhap_kho(a, lo_a, 30, ChungTu("phieu_nhap", 1, None))  # a đang giữ khóa lô, chưa commit
        viec_b = asyncio.create_task(nhap_kho(b, lo_b, 20, ChungTu("phieu_nhap", 2, None)))
        await asyncio.sleep(0.5)
        assert not viec_b.done(), "b phải chờ khóa của a, không được chạy song song"

        await a.commit()
        bien_dong_b = await asyncio.wait_for(viec_b, timeout=5)
        await b.commit()

    assert bien_dong_b.ton_sau == 50  # tính trên tồn đã commit của a, không phải trên số 0 cũ
    async with db_that() as s:
        lo = await s.get(LoThuoc, lo_id)
        the = list(
            (await s.execute(select(BienDongKho).where(BienDongKho.lo_id == lo_id).order_by(BienDongKho.id))).scalars()
        )
    assert lo.so_luong_ton == 50
    assert [(t.so_luong, t.ton_sau) for t in the] == [(30, 30), (20, 50)]

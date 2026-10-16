"""Tranh chấp khi giữ hàng (spec 10 mục 4): hai giao dịch thật song song trên cùng lô, và khóa lô theo thứ tự ngược nhau."""

import asyncio

import pytest
from sqlalchemy import select

from app.core.loi import LoiNghiepVu
from app.models.ban_hang import CtDonHang, PhanBoLo
from app.models.kho import LoThuoc
from app.modules.kho import ton_kho
from app.modules.kho.ton_kho import YeuCauGiu
from tests.factories import tao_don, tao_lo, tao_san_pham


async def dong_don_moi(s, san_pham, so_luong=1) -> int:
    don = await tao_don(s, dong=[{"san_pham": san_pham, "so_luong": so_luong}])
    return (await s.execute(select(CtDonHang.id).where(CtDonHang.don_hang_id == don.id))).scalar_one()


async def test_lo_con_1_don_vi_hai_don_song_song_dung_1_thanh_cong(db_that):
    async with db_that() as s, s.begin():
        sp = await tao_san_pham(s)
        lo_id = (await tao_lo(s, sp, so_luong=1)).id
        ct_a, ct_b = await dong_don_moi(s, sp), await dong_don_moi(s, sp)
        sp_id = sp.id

    async def dat(ct_id):
        async with db_that() as s:
            try:
                await ton_kho.giu_hang_nhieu(s, [YeuCauGiu(ct_id, sp_id, 1)])
                await s.commit()
                return "ok"
            except LoiNghiepVu as loi:
                await s.rollback()
                return loi.ma_loi

    ket_qua = await asyncio.gather(dat(ct_a), dat(ct_b))
    assert sorted(ket_qua) == ["HET_HANG", "ok"]
    async with db_that() as s:
        lo = await s.get(LoThuoc, lo_id)
        assert (lo.so_luong_ton, lo.so_luong_giu) == (1, 1)
        assert len((await s.execute(select(PhanBoLo))).scalars().all()) == 1


@pytest.mark.parametrize("lan", range(3))
async def test_giu_hang_hai_san_pham_theo_thu_tu_nguoc_nhau_khong_deadlock(db_that, lan):
    async with db_that() as s, s.begin():
        sp_a, sp_b = await tao_san_pham(s), await tao_san_pham(s)
        await tao_lo(s, sp_a, so_luong=100)
        await tao_lo(s, sp_b, so_luong=100)
        ct = [
            await dong_don_moi(s, sp_a),
            await dong_don_moi(s, sp_b),
            await dong_don_moi(s, sp_a),
            await dong_don_moi(s, sp_b),
        ]
        a, b = sp_a.id, sp_b.id

    async def dat(dong):
        async with db_that() as s:
            await ton_kho.giu_hang_nhieu(s, dong)
            await s.commit()

    await asyncio.wait_for(
        asyncio.gather(
            dat([YeuCauGiu(ct[0], a, 3), YeuCauGiu(ct[1], b, 3)]),
            dat([YeuCauGiu(ct[3], b, 4), YeuCauGiu(ct[2], a, 4)]),
        ),
        timeout=15,
    )
    async with db_that() as s:
        tong = sum((await s.execute(select(LoThuoc.so_luong_giu))).scalars().all())
    assert tong == 14

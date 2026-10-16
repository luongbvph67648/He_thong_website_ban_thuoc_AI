"""Chính hàm kiểm tra bất biến phải bắt được từng kiểu sai (nếu không, mọi test kho đang kiểm bằng một cái thước cong)."""

from sqlalchemy import text

from app.models.enums import KhuTon, LoaiBienDong
from app.modules.kho import ton_kho
from app.modules.kho.ton_kho import ChungTu
from tests.bat_bien.kiem_tra import kiem_tra_bat_bien
from tests.factories import tao_lo, tao_san_pham


async def test_du_lieu_dung_khong_co_vi_pham(db):
    sp = await tao_san_pham(db)
    lo = await tao_lo(db, sp, so_luong=10)
    await ton_kho.vao_biet_tru(db, lo, 2, ChungTu("yeu_cau_doi_tra", 1))
    await ton_kho.tru_ton(db, lo, 3, KhuTon.kho_ban, LoaiBienDong.huy_hang, ChungTu("phieu_huy", 1))
    assert await kiem_tra_bat_bien(db) == []


async def test_ton_khong_co_the_kho_bi_bat(db):
    lo = await tao_lo(db, so_luong_ton=5)  # tồn "có sẵn" không thẻ kho
    vi_pham = await kiem_tra_bat_bien(db)
    assert any(f"lô {lo.id}" in v and v.startswith("3") for v in vi_pham)


async def test_giu_khong_co_phan_bo_bi_bat(db):
    lo = await tao_lo(db, so_luong=10)
    await db.execute(text("UPDATE lo_thuoc SET so_luong_giu = 4 WHERE id = :id"), {"id": lo.id})
    vi_pham = await kiem_tra_bat_bien(db)
    assert any(v.startswith("2") and f"lô {lo.id}" in v for v in vi_pham)


async def test_ton_sau_the_cuoi_sai_bi_bat(db):
    lo = await tao_lo(db, so_luong=10)
    await db.execute(text("UPDATE bien_dong_kho SET ton_sau = 99 WHERE lo_id = :id"), {"id": lo.id})
    vi_pham = await kiem_tra_bat_bien(db)
    assert any("ton_sau" in v and f"lô {lo.id}" in v for v in vi_pham)

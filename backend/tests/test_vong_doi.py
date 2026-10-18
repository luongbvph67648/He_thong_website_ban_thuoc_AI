"""Làm nóng mô hình embedding lúc khởi động không được làm sập API."""

import asyncio

from app import main
from app.ai import embedding
from app.core.config import settings


async def test_lam_nong_goi_embed_va_nuot_loi(monkeypatch):
    da_goi = []

    async def hong(ds):
        da_goi.append(list(ds))
        raise OSError("không tải được mô hình")

    monkeypatch.setattr(embedding, "embed", hong)
    await main._lam_nong_embedding()  # không ném lỗi
    assert da_goi == [["khởi động"]]


async def test_vong_doi_chi_lam_nong_khi_dung_mo_hinh_that(monkeypatch):
    dem = []

    async def embed(ds):
        dem.append(1)
        return [[0.0]]

    monkeypatch.setattr(embedding, "embed", embed)
    for gia_lap, mong_doi in ((True, 0), (False, 1)):
        dem.clear()
        monkeypatch.setattr(settings, "EMBEDDING_GIA_LAP", gia_lap)
        async with main._vong_doi(main.FastAPI()):
            await asyncio.sleep(0.05)
        assert len(dem) == mong_doi

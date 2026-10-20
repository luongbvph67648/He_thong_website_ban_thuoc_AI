"""ai/embedding.py nhánh THẬT (BGE-M3 qua sentence-transformers) với mô-đun `sentence_transformers` thay thế.

Không tải được 2,3 GB trọng số trong test, nên chỉ kiểm phần keo của hệ thống: nạp một lần, giới hạn độ dài, gọi `encode`
đúng tham số, kiểm số chiều 1024, và không chạy hai lượt encode cùng lúc trên một mô hình.
"""

import asyncio
import sys
import threading
import time
import types

import numpy as np
import pytest

from app.ai import embedding
from app.core.config import settings


class MoHinhGia:
    so_lan_nap = 0
    dang_chay = 0
    chay_chong_nhau = False

    def __init__(self, ten: str):
        MoHinhGia.so_lan_nap += 1
        self.ten = ten
        self.max_seq_length = 8192
        self.so_chieu = embedding.SO_CHIEU

    def encode(self, ds, normalize_embeddings, batch_size):
        assert normalize_embeddings is True and batch_size == 16
        MoHinhGia.dang_chay += 1
        if MoHinhGia.dang_chay > 1:
            MoHinhGia.chay_chong_nhau = True
        time.sleep(0.05)
        MoHinhGia.dang_chay -= 1
        v = np.zeros((len(ds), self.so_chieu), dtype=np.float32)
        v[:, 0] = 1.0
        return v


@pytest.fixture
def bge(monkeypatch):
    mo_dun = types.ModuleType("sentence_transformers")
    mo_dun.SentenceTransformer = MoHinhGia
    monkeypatch.setitem(sys.modules, "sentence_transformers", mo_dun)
    monkeypatch.setattr(settings, "EMBEDDING_GIA_LAP", False)
    monkeypatch.setattr(settings, "EMBEDDING_MODEL", "BAAI/bge-m3")
    monkeypatch.setattr(embedding, "_model", None)
    MoHinhGia.so_lan_nap, MoHinhGia.dang_chay, MoHinhGia.chay_chong_nhau = 0, 0, False
    return MoHinhGia


async def test_embed_that_nap_mot_lan_gioi_han_do_dai_va_tra_vector_1024(bge):
    v = await embedding.embed(["thuốc hạ sốt", "khẩu trang"])
    assert len(v) == 2 and all(len(x) == embedding.SO_CHIEU for x in v) and isinstance(v[0][0], float)
    await embedding.embed(["thêm một câu"])
    assert bge.so_lan_nap == 1  # nạp một lần mỗi process
    assert embedding._model.max_seq_length == embedding.TOI_DA_TOKEN  # không dùng mặc định 8192 token
    assert embedding.ten_mo_hinh() == "BAAI/bge-m3"


async def test_embed_that_hai_yeu_cau_dong_thoi_khong_encode_chong_nhau(bge):
    await asyncio.gather(*(embedding.embed([f"câu {i}"]) for i in range(6)))
    assert bge.chay_chong_nhau is False and threading.active_count() >= 1


async def test_embed_that_sai_so_chieu_thi_bao_loi_ro(bge, monkeypatch):
    monkeypatch.setattr(
        bge, "__init__", lambda self, ten: (setattr(self, "max_seq_length", 1), setattr(self, "so_chieu", 768))[0]
    )
    with pytest.raises(RuntimeError, match="768 chiều"):
        await embedding.embed(["x"])


async def test_embed_that_thieu_thu_vien_thi_loi_importerror_cho_noi_goi_xu_ly(monkeypatch):
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)  # như chưa cài nhóm ai-local
    monkeypatch.setattr(settings, "EMBEDDING_GIA_LAP", False)
    monkeypatch.setattr(embedding, "_model", None)
    with pytest.raises(ImportError):
        await embedding.embed(["x"])

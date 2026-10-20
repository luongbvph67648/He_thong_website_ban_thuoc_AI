"""Điểm duy nhất tạo vector (spec 07 mục 3): BGE-M3 qua sentence-transformers hoặc bản giả xác định.

Bản giả (`EMBEDDING_GIA_LAP=true`) băm từng từ (đã bỏ dấu, chữ thường) vào 1024 chiều rồi chuẩn hóa: văn bản chung
từ vựng thì gần nhau theo cosine, đủ để test tìm kiếm lai mà không cần mô hình 2.3 GB.
"""

import asyncio
import hashlib
import math
import re
import threading
from collections.abc import Sequence
from typing import Any

from app.core.config import settings
from app.core.slug import bo_dau

SO_CHIEU = 1024
TEN_MO_HINH_GIA = "gia-lap-hash-1024"
_model: Any = None
_khoa_model = threading.Lock()
"""Nạp mô hình một lần và không chạy hai lượt `encode` cùng lúc trên một mô hình (không an toàn đa luồng; `embed` chạy
trong `asyncio.to_thread` nên hai request đồng thời sẽ vào đây cùng lúc)."""
TOI_DA_TOKEN = 512
"""BGE-M3 mặc định nhận 8192 token (chậm và tốn RAM); đoạn tri thức và câu hỏi của hệ thống ngắn hơn nhiều."""
_TU = re.compile(r"[a-z0-9]+")


def ten_mo_hinh() -> str:
    """Giá trị ghi ở `tai_lieu_tri_thuc.mo_hinh_embedding`; đổi giá trị này là tạo lại toàn bộ vector."""
    return TEN_MO_HINH_GIA if settings.EMBEDDING_GIA_LAP else settings.EMBEDDING_MODEL


def vector_gia(van_ban: str) -> list[float]:
    v = [0.0] * SO_CHIEU
    for tu in _TU.findall(bo_dau(van_ban).lower()):
        h = hashlib.sha256(tu.encode()).digest()
        v[int.from_bytes(h[:4], "big") % SO_CHIEU] += 1.0 if h[4] % 2 == 0 else -1.0
    chuan = math.sqrt(sum(x * x for x in v))
    if chuan == 0:  # văn bản rỗng: vector đơn vị cố định để cosine vẫn xác định
        v[0], chuan = 1.0, 1.0
    return [x / chuan for x in v]


def _nap_model() -> Any:
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer  # nhóm phụ thuộc `ai-local`, nạp một lần mỗi process

        mo_hinh = SentenceTransformer(settings.EMBEDDING_MODEL)
        mo_hinh.max_seq_length = TOI_DA_TOKEN
        _model = mo_hinh
    return _model


def _ma_hoa(ds: list[str]) -> list[list[float]]:
    with _khoa_model:
        vector = [list(map(float, v)) for v in _nap_model().encode(ds, normalize_embeddings=True, batch_size=16)]
    if vector and len(vector[0]) != SO_CHIEU:
        # Bảng `tai_lieu_tri_thuc.embedding` là vector(1024): mô hình khác số chiều thì không lưu/so sánh được
        raise RuntimeError(f"Mô hình {settings.EMBEDDING_MODEL} cho {len(vector[0])} chiều, hệ thống cần {SO_CHIEU}")
    return vector


async def embed(ds: Sequence[str]) -> list[list[float]]:
    """Vector 1024 chiều đã chuẩn hóa cho từng văn bản (cosine = tích vô hướng)."""
    if not ds:
        return []
    if settings.EMBEDDING_GIA_LAP:
        return [vector_gia(t) for t in ds]
    return await asyncio.to_thread(_ma_hoa, list(ds))

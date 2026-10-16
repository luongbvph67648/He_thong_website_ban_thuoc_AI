"""Điểm duy nhất tạo vector (spec 07 mục 3): BGE-M3 qua sentence-transformers hoặc bản giả xác định.

Bản giả (`EMBEDDING_GIA_LAP=true`) băm từng từ (đã bỏ dấu, chữ thường) vào 1024 chiều rồi chuẩn hóa: văn bản chung
từ vựng thì gần nhau theo cosine, đủ để test tìm kiếm lai mà không cần mô hình 2.3 GB.
"""

import asyncio
import hashlib
import math
import re
from collections.abc import Sequence
from typing import Any

from app.core.config import settings
from app.core.slug import bo_dau

SO_CHIEU = 1024
TEN_MO_HINH_GIA = "gia-lap-hash-1024"
_model: Any = None
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

        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model


def _ma_hoa(ds: list[str]) -> list[list[float]]:
    return [list(map(float, v)) for v in _nap_model().encode(ds, normalize_embeddings=True, batch_size=16)]


async def embed(ds: Sequence[str]) -> list[list[float]]:
    """Vector 1024 chiều đã chuẩn hóa cho từng văn bản (cosine = tích vô hướng)."""
    if not ds:
        return []
    if settings.EMBEDDING_GIA_LAP:
        return [vector_gia(t) for t in ds]
    return await asyncio.to_thread(_ma_hoa, list(ds))

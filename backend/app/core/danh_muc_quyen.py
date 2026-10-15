"""Danh mục mã quyền hợp lệ, đọc từ `docs/spec/data/quyen.yaml` (nguồn sự thật, spec 03 mục 4)."""

import logging
from functools import cache
from pathlib import Path

import yaml

from app.core.config import BACKEND_DIR

logger = logging.getLogger(__name__)

QUYEN_YAML = BACKEND_DIR.parent / "docs" / "spec" / "data" / "quyen.yaml"


@cache
def ma_quyen_hop_le(duong_dan: Path = QUYEN_YAML) -> frozenset[str] | None:
    """Tập mã quyền trong yaml; `None` nếu không đọc được file (bản đóng gói chưa kèm docs/).

    Khi đó bỏ qua kiểm tra mã lúc dựng route thay vì làm ứng dụng không khởi động được.
    Test luôn khẳng định file có mặt.
    """
    try:
        du_lieu = yaml.safe_load(duong_dan.read_text(encoding="utf-8"))
        return frozenset(q["ma"] for q in du_lieu["quyen"])
    except OSError:
        logger.warning("Không đọc được %s, bỏ qua kiểm tra mã quyền lúc khai báo route", duong_dan)
        return None

"""Hỗ trợ tìm kiếm văn bản cho các danh sách quản trị (AD01, AD02...)."""

import re

_KY_TU_LIKE = re.compile(r"([\\%_])")


def mau_tim_like(q: str) -> str:
    """Mẫu `LIKE '%q%'` an toàn: thoát `\\`, `%`, `_` để người dùng gõ chúng không biến thành ký tự thay thế. Dùng cùng
    `escape="\\\\"` ở điều kiện `.like(...)`."""
    return "%" + _KY_TU_LIKE.sub(r"\\\1", q.strip()) + "%"

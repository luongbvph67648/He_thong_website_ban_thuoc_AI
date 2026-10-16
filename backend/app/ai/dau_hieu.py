"""Phát hiện dấu hiệu nguy hiểm bằng luật (spec 07 mục 1.3): chạy TRƯỚC khi gọi Claude."""

import re

from app.core.slug import bo_dau

_KHOANG_TRANG = re.compile(r"\s+")

MAU_NGUY_HIEM = (
    "Những dấu hiệu bạn nêu có thể nghiêm trọng. Mình dừng tư vấn tại đây để bạn được xử lý kịp thời: "
    "vui lòng đến cơ sở y tế gần nhất ngay, hoặc gọi 115 nếu có nguy cơ đến tính mạng. "
    "Bạn cũng có thể nhờ người thân đi cùng. Dược sĩ của nhà thuốc sẽ hỗ trợ thêm sau khi bạn đã được thăm khám."
)


def chuan_hoa(van_ban: str) -> str:
    """Bỏ dấu, chữ thường, gộp khoảng trắng; ký tự không phải chữ/số thành khoảng trắng."""
    t = re.sub(r"[^a-z0-9]+", " ", bo_dau(van_ban).lower())
    return _KHOANG_TRANG.sub(" ", t).strip()


def tim_dau_hieu(van_ban: str, danh_sach: list[str]) -> str | None:
    """Cụm đầu tiên trong `danh_sach` xuất hiện trong `van_ban` (theo ranh giới từ), hoặc None."""
    noi_dung = f" {chuan_hoa(van_ban)} "
    for cum in danh_sach:
        c = chuan_hoa(cum)
        if c and f" {c} " in noi_dung:
            return cum
    return None

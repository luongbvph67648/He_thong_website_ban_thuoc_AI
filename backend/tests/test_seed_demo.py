"""Seed demo (T8.3): phần thuần không cần dựng cả ứng dụng. Luồng đầy đủ được kiểm bằng `scripts/e2e.sh`."""

import io

from PIL import Image

from app.core.luu_tru import nhan_dang_anh
from app.seed.demo import _ve_anh_san_pham


def test_anh_minh_hoa_la_jpeg_hop_le_va_khac_nhau_theo_ten():
    a, b = _ve_anh_san_pham("Paracetamol 500mg"), _ve_anh_san_pham("Vitamin C 1000mg viên sủi")
    assert nhan_dang_anh(a) == "image/jpeg" and a != b
    assert Image.open(io.BytesIO(a)).size == (600, 600)
    assert _ve_anh_san_pham("Paracetamol 500mg") == a  # cùng tên cho cùng ảnh

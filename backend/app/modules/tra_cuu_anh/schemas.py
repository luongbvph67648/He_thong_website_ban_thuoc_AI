from typing import Literal

from pydantic import BaseModel

from app.ai.doc_anh import HopThuocDoc
from app.modules.cua_hang.schemas import SanPhamThe


class TomTatSanPham(BaseModel):
    chi_dinh: str | None
    chong_chi_dinh: str | None
    than_trong: str | None


class KhopSanPham(BaseModel):
    cach: Literal["so_dang_ky", "ten"]
    san_pham: SanPhamThe
    la_thuoc_ke_don: bool
    tom_tat: TomTatSanPham | None
    """Tóm tắt từ nội dung chuyên môn đã duyệt; thuốc kê đơn không có tóm tắt (chỉ dẫn tới dược sĩ)."""


class TraCuuAnhRa(BaseModel):
    doc_duoc: HopThuocDoc
    khop: KhopSanPham | None
    da_xac_minh: bool
    canh_bao: str | None

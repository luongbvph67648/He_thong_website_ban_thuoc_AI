"""Schema xác nhận hoàn tiền (AD17; spec 06 mục 3.34)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from app.core.tien import TienDoc
from app.models.enums import PhuongThucThanhToan, TrangThaiGiaoDich


class HoanTienRa(BaseModel):
    id: int
    ma_don: str
    ten_khach: str | None
    so_tien: TienDoc
    cong_thanh_toan: PhuongThucThanhToan
    trang_thai: TrangThaiGiaoDich
    nguon: Literal["huy_don", "doi_tra"]
    ma_yeu_cau: str | None
    tong_da_thanh_toan: TienDoc
    tu_dong_qua_cong: bool
    """VNPay/MoMo: Admin bấm xác nhận để gọi API hoàn của cổng; ngược lại chuyển khoản tay kèm chứng từ."""
    thong_tin_nhan_hoan: dict[str, Any] | None
    """Tài khoản khách cung cấp; sau khi hoàn xong chỉ còn dạng che (`****1234`)."""
    thieu_tai_khoan: bool
    """Hoàn do đổi trả, chuyển khoản tay, mà khách chưa nhập tài khoản: chưa xác nhận được."""
    chung_tu: str | None
    """URL ký của chứng từ chuyển khoản (sau khi xác nhận)."""
    ghi_chu: str | None
    created_at: datetime
    xu_ly_luc: datetime | None

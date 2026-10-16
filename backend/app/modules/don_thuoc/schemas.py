"""Schema yêu cầu tư vấn đơn thuốc (KVL08, KTV07; spec 06 mục 3.29)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import TrangThaiYeuCauDonThuoc


class YeuCauDonThuocTao(BaseModel):
    """Phản hồi sau khi gửi: khách vãng lai chỉ biết mã yêu cầu (kết quả gửi qua SMS)."""

    ma_yeu_cau: str
    trang_thai: TrangThaiYeuCauDonThuoc
    created_at: datetime


class YeuCauDonThuocTom(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ma_yeu_cau: str
    trang_thai: TrangThaiYeuCauDonThuoc
    ho_ten: str
    so_anh: int
    ghi_chu: str | None
    ly_do_tu_choi: str | None
    ma_don: str | None
    """Mã đơn hàng đã tạo từ yêu cầu này (khi `da_tao_don`)."""
    created_at: datetime


class YeuCauDonThuocChiTiet(YeuCauDonThuocTom):
    so_dien_thoai: str
    anh: list[str]
    """URL ký có hạn 10 phút, theo thứ tự đã tải lên."""

"""Schema bán tại quầy POS (DS08, spec 06 mục 3.31)."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.kieu_du_lieu import kieu_ten, van_ban_tuy_chon
from app.core.tien import Tien, TienDoc
from app.models.enums import LoaiSanPham, PhuongThucThanhToan
from app.modules.chuyen_mon.canh_bao import CanhBaoDiUng, CanhBaoTuongTac
from app.modules.tai_khoan.schemas import SoDienThoai


class DonViPos(BaseModel):
    id: int
    ten_don_vi: str
    he_so: int
    gia_ban: TienDoc
    ma_vach: str | None


class SanPhamPos(BaseModel):
    id: int
    ten: str
    loai_san_pham: LoaiSanPham
    don_vi_co_so: str
    ton_quay: int
    """Tồn khả dụng tại quầy (đơn vị cơ sở): lô đang bán và cận hạn còn hạn, trừ phần đang giữ cho đơn khác."""
    co_lo_can_han: bool
    hoat_chat: list[str]
    don_vi: list[DonViPos]
    don_vi_khop_ma_vach: int | None = None
    """Có khi tìm bằng mã vạch: đơn vị khớp mã quét."""


class DongPosVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    san_pham_id: Annotated[int, Field(ge=1, le=2_147_483_647)]
    don_vi_id: Annotated[int, Field(ge=1, le=2_147_483_647)]
    so_luong: int = Field(ge=1, le=9999)


class CanhBaoPosVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dong: list[DongPosVao] = Field(min_length=1, max_length=50)
    sdt_khach: SoDienThoai | None = None


class CanhBaoPosRa(BaseModel):
    tuong_tac: list[CanhBaoTuongTac]
    di_ung: list[CanhBaoDiUng]
    can_xac_nhan: bool
    """Có tương tác `nghiem_trong`/`chong_chi_dinh` hoặc dị ứng: phải xác nhận mới bán được."""


class DonPosVao(CanhBaoPosVao):
    yeu_cau_don_thuoc_id: Annotated[int, Field(ge=1, le=2_147_483_647)] | None = None
    phuong_thuc_thu: Literal[PhuongThucThanhToan.tien_mat, PhuongThucThanhToan.chuyen_khoan]
    tien_khach_dua: Tien | None = None
    """Bắt buộc với tiền mặt: phải đủ tổng tiền; thừa bao nhiêu thối bấy nhiêu."""
    xac_nhan_canh_bao: bool = False
    xac_nhan_trung_anh: bool = False


class DongHoaDon(BaseModel):
    ten_san_pham: str
    ten_don_vi: str
    so_luong: int
    don_gia: TienDoc
    thanh_tien: TienDoc


class HoaDonRa(BaseModel):
    """Dữ liệu hóa đơn để in (giao diện dựng HTML in được)."""

    ten_nha_thuoc: str
    ma_don: str
    thoi_diem: datetime
    nhan_vien: str
    khach: str | None
    dong: list[DongHoaDon]
    tam_tinh: TienDoc
    giam_gia: TienDoc
    tong_tien: TienDoc
    phuong_thuc_thu: PhuongThucThanhToan
    tien_khach_dua: TienDoc | None
    tien_thua: TienDoc | None
    """Chỉ có ngay lúc bán; in lại sau đó không có hai số này."""
    co_thuoc_ke_don: bool


class DonPosRa(BaseModel):
    don_id: int
    hoa_don: HoaDonRa


class YeuCauQuayVao(BaseModel):
    ho_ten: kieu_ten(150)
    tuoi_hoac_nam_sinh: van_ban_tuy_chon(20) = None
    so_dien_thoai: SoDienThoai | None = None
    ghi_chu: van_ban_tuy_chon(500, nhieu_dong=True) = None


class YeuCauQuayRa(BaseModel):
    id: int
    ma_yeu_cau: str
    ho_ten: str
    trung_anh: list[str]
    """Mã các yêu cầu đã dùng có cùng ảnh (cảnh báo đơn đã sử dụng)."""

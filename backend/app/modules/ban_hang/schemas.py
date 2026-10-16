"""Schema đặt hàng của khách (KTV02, spec 06 mục 3.22)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.kieu_du_lieu import van_ban_tuy_chon
from app.core.tien import Tien, TienDoc
from app.models.enums import HinhThucNhan, PhuongThucThanhToan, TrangThaiDon, TrangThaiThanhToan


class DatHangVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hinh_thuc_nhan: HinhThucNhan
    phuong_thuc_tt: Literal[PhuongThucThanhToan.cod, PhuongThucThanhToan.vnpay, PhuongThucThanhToan.momo]
    dia_chi_id: int | None = Field(default=None, ge=1, le=2_147_483_647)
    ma_giam_gia: str | None = Field(default=None, max_length=40)
    tong_tien_ky_vong: Tien | None = None
    ghi_chu: van_ban_tuy_chon(500, nhieu_dong=True) = None


class DongDonRa(BaseModel):
    san_pham_id: int
    ten_san_pham: str
    ten_don_vi: str
    so_luong: int
    don_gia: TienDoc
    giam_gia_phan_bo: TienDoc
    thanh_tien: TienDoc


class DonHangRa(BaseModel):
    ma_don: str
    trang_thai: TrangThaiDon
    trang_thai_tt: TrangThaiThanhToan
    phuong_thuc_tt: PhuongThucThanhToan | None
    hinh_thuc_nhan: HinhThucNhan
    tam_tinh: TienDoc
    giam_gia: TienDoc
    phi_van_chuyen: TienDoc
    tong_tien: TienDoc
    han_thanh_toan: datetime | None
    ma_giam_gia: str | None
    ten_nguoi_nhan: str | None
    sdt_nguoi_nhan: str | None
    dia_chi_giao: str | None
    ghi_chu: str | None
    created_at: datetime
    dong: list[DongDonRa]


class XemTruocRa(BaseModel):
    tam_tinh: TienDoc
    giam_gia: TienDoc
    phi_van_chuyen: TienDoc
    tong_tien: TienDoc
    ma_giam_gia: str | None

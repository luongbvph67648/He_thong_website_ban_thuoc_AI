"""Schema nhận hàng trả về và hàng hoàn (KHO10; spec 06 mục 3.33)."""

from datetime import date
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import LyDoDoiTra, TrangThaiDon

ID = Annotated[int, Field(ge=1, le=2_147_483_647)]
VAN_BAN = Annotated[str, Field(min_length=3, max_length=1000, pattern=r"^[^\x00]*$")]


class TinhTrangHang(StrEnum):
    nguyen_niem_phong = "nguyen_niem_phong"
    hu_hong = "hu_hong"


class LoGoiY(BaseModel):
    lo_id: int
    so_lo: str
    han_su_dung: date
    so_luong_da_xuat: int
    """Đơn vị cơ sở đã xuất từ lô này cho dòng đơn."""


class DongKhoRa(BaseModel):
    ct_don_hang_id: int
    ten_san_pham: str
    ten_don_vi: str
    he_so: int
    so_luong: int
    """Số lượng cần trả (đổi trả) hoặc đã đặt (hàng hoàn), tính theo đơn vị của dòng."""
    lo: list[LoGoiY]


class DoiTraKhoRa(BaseModel):
    id: int
    ma_yeu_cau: str
    ma_don: str
    ly_do: LyDoDoiTra
    mo_ta: str | None
    ma_van_don: str | None
    anh: list[str]
    dong: list[DongKhoRa]


class HoanVeKhoRa(BaseModel):
    id: int
    ma_don: str
    trang_thai: TrangThaiDon
    da_thanh_toan: bool
    dong: list[DongKhoRa]


class NhanDongVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ct_don_hang_id: ID
    lo_id: ID | None = None
    so_luong_nhan: int = Field(ge=0, le=9999)
    """Theo đơn vị của dòng đơn; 0 = không nhận được hàng của dòng này (khi đó không cần `lo_id`)."""


class NhanDoiTraVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dong: list[NhanDongVao] = Field(min_length=1, max_length=50)
    ket_qua_kiem_hang: VAN_BAN


class KiemHoanDongVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ct_don_hang_id: ID
    tinh_trang: TinhTrangHang


class KiemHoanVeVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dong: list[KiemHoanDongVao] = Field(min_length=1, max_length=50)
    ghi_chu: Annotated[str | None, Field(max_length=500, pattern=r"^[^\x00]*$")] = None


class KetQuaKiemHoan(BaseModel):
    ma_don: str
    trang_thai: TrangThaiDon
    cho_hoan_tien: bool
    """Đơn đã thanh toán: giao dịch hoàn tiền đã tạo ở trạng thái khởi tạo, chờ Admin xác nhận (AD17)."""
    so_luong_hoan_nhap: int
    so_luong_biet_tru: int

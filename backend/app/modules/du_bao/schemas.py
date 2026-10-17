"""Schema đề xuất nhập hàng (KHO14; spec 06 mục 3.47)."""

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class DeXuatRa(BaseModel):
    id: int
    san_pham_id: int
    sku: str
    ten_san_pham: str
    don_vi_co_so: str
    ky_bat_dau: date
    ky_ket_thuc: date
    so_luong_du_bao: int
    ton_kha_dung: int
    ton_toi_thieu: int
    so_luong_de_xuat: int
    mo_hinh: str | None
    sai_so_mape: Decimal | None
    """Phần trăm (ví dụ 23.5 là 23,5%); `null` khi chưa đủ dữ liệu để đo."""
    da_xu_ly: bool


class DiemTuan(BaseModel):
    tuan_bat_dau: date
    so_luong: int


class BieuDoDeXuat(BaseModel):
    id: int
    ten_san_pham: str
    don_vi_co_so: str
    mo_hinh: str
    lich_su: list[DiemTuan]
    du_bao: list[DiemTuan]


class DaXuLyVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    da_xu_ly: bool


class KyDeXuat(BaseModel):
    ky_bat_dau: date
    ky_ket_thuc: date
    so_san_pham: Annotated[int, Field(ge=0)]

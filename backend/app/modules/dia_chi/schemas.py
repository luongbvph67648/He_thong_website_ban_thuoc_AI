"""Schema sổ địa chỉ (KTV01, spec 06 mục 3.20)."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.core.kieu_du_lieu import kieu_ten
from app.modules.tai_khoan.schemas import SoDienThoai

Ma = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20, pattern=r"^[0-9A-Za-z_-]+$")]


class DiaChiVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ten_nguoi_nhan: kieu_ten(150)
    so_dien_thoai: SoDienThoai
    dia_chi_chi_tiet: Annotated[kieu_ten(300), Field(min_length=5)]
    ma_tinh: Ma
    ma_phuong_xa: Ma


class DiaChiTao(DiaChiVao):
    la_mac_dinh: bool = False


class DiaChiRa(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ten_nguoi_nhan: str
    so_dien_thoai: str
    dia_chi_chi_tiet: str
    ma_tinh: str
    ten_tinh: str | None
    ma_phuong_xa: str
    ten_phuong_xa: str | None
    la_mac_dinh: bool

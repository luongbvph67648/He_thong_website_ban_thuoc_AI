"""Schema đánh giá và hỏi đáp sản phẩm (KTV10, KTV15, DS11; spec 06 mục 3.35)."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

VAN_BAN_DAI = Annotated[str, Field(min_length=1, max_length=2000, pattern=r"^[^\x00]*$")]
CAU_HOI = Annotated[str, Field(min_length=5, max_length=1000, pattern=r"^[^\x00]*$")]
TRA_LOI = Annotated[str, Field(min_length=2, max_length=2000, pattern=r"^[^\x00]*$")]


class DanhGiaCuaToi(BaseModel):
    id: int
    ct_don_hang_id: int
    san_pham_ten: str
    san_pham_slug: str
    so_sao: int
    noi_dung: str | None
    anh: list[str]
    dang_hien: bool
    phan_hoi: str | None
    created_at: datetime


class DongCoTheDanhGia(BaseModel):
    ct_don_hang_id: int
    ma_don: str
    ten_san_pham: str
    san_pham_slug: str | None
    created_at: datetime


class HoiDapCongKhai(BaseModel):
    id: int
    cau_hoi: str
    tra_loi: str | None
    ten_hien_thi: str
    tra_loi_luc: datetime | None
    created_at: datetime


class HoiVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cau_hoi: CAU_HOI


class HoiDapCuaToi(BaseModel):
    id: int
    san_pham_ten: str
    san_pham_slug: str
    cau_hoi: str
    tra_loi: str | None
    tra_loi_luc: datetime | None
    dang_hien: bool
    created_at: datetime


class DanhGiaNoiBo(BaseModel):
    id: int
    san_pham_ten: str
    ten_khach: str
    so_sao: int
    noi_dung: str | None
    anh: list[str]
    dang_hien: bool
    phan_hoi: str | None
    created_at: datetime


class HienThiVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dang_hien: bool


class PhanHoiVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phan_hoi: TRA_LOI


class HoiDapNoiBo(BaseModel):
    id: int
    san_pham_ten: str
    san_pham_slug: str
    ten_khach: str
    cau_hoi: str
    tra_loi: str | None
    tra_loi_luc: datetime | None
    dang_hien: bool
    created_at: datetime


class TraLoiVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tra_loi: TRA_LOI

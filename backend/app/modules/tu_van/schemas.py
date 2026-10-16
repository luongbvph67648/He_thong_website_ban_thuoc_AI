"""Schema chat tư vấn (KVL05; spec 06 mục 9)."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

NOI_DUNG = Annotated[str, Field(min_length=1, max_length=1000, pattern=r"^[^\x00]*$")]


class ChatVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ma_phien: uuid.UUID
    """Do trình duyệt sinh và giữ; bí mật như mã truy cập, đừng chia sẻ."""
    noi_dung: NOI_DUNG


class DanhGiaVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ma_phien: uuid.UUID
    tin_nhan_id: int = Field(ge=1, le=9_223_372_036_854_775_807)
    ket_qua: Literal["huu_ich", "khong_huu_ich"]


class TinNhanRa(BaseModel):
    id: int
    vai_tro: Literal["khach", "ai", "duoc_si", "he_thong"]
    noi_dung: str
    dau_hieu_nguy_hiem: bool
    created_at: datetime


class LichSuRa(BaseModel):
    trang_thai: str
    tin_nhan: list[TinNhanRa]


class GapDuocSiVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ma_phien: uuid.UUID
    so_dien_thoai: Annotated[str | None, Field(max_length=20, pattern=r"^[^\x00]*$")] = None
    """Bắt buộc khi ngoài giờ làm việc và khách chưa có số trong tài khoản."""


class GapDuocSiRa(BaseModel):
    trang_thai: Literal["cho_duoc_si", "cho_goi_lai"]
    trong_gio: bool
    thong_diep: str


class ChatTomTat(BaseModel):
    id: int
    ma_phien: uuid.UUID
    trang_thai: str
    tom_tat: str | None
    ten_khach: str | None
    so_dien_thoai_goi_lai: str | None
    bi_gan_co: bool
    duoc_si_cua_toi: bool
    created_at: datetime


class HoSoTomLuoc(BaseModel):
    nam_sinh: int | None
    dang_mang_thai: bool | None
    dang_cho_con_bu: bool | None
    di_ung: list[str]


class ChatChiTiet(ChatTomTat):
    tin_nhan: list[TinNhanRa]
    ho_so_suc_khoe: HoSoTomLuoc | None
    """Chỉ có khi khách đã đồng ý và dược sĩ đang xử lý chính phiên này (hàm cổng spec 03 mục 5.1)."""


class TinNhanVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    noi_dung: NOI_DUNG

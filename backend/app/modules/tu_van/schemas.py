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

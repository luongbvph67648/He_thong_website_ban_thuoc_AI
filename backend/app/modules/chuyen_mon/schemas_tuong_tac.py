"""Schema API tương tác giữa các hoạt chất (DS10, spec 06 mục 3.12)."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.kieu_du_lieu import van_ban_tuy_chon
from app.models.enums import MucDoTuongTac

IdSql = Annotated[int, Field(ge=1, le=2_147_483_647)]
PhienBan = Annotated[str, Field(pattern=r"^[0-9a-f]{16}$")]

VanBan2000 = van_ban_tuy_chon(2000, nhieu_dong=True)
NguonThamKhao = van_ban_tuy_chon(255)


def _bat_buoc(gia_tri: str | None) -> str:
    if gia_tri is None:
        raise ValueError("Không được để trống")
    return gia_tri


class TuongTacTao(BaseModel):
    """Cặp hoạt chất không có thứ tự: server tự đặt `hoat_chat_a_id < hoat_chat_b_id` (CHECK ở DB)."""

    model_config = ConfigDict(extra="forbid")

    hoat_chat_1_id: IdSql
    hoat_chat_2_id: IdSql
    muc_do: MucDoTuongTac
    co_che: VanBan2000 = None
    khuyen_cao: VanBan2000
    nguon_tham_khao: NguonThamKhao = None

    _khuyen_cao_bat_buoc = field_validator("khuyen_cao")(_bat_buoc)


class TuongTacSua(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phien_ban: PhienBan
    muc_do: MucDoTuongTac
    co_che: VanBan2000 = None
    khuyen_cao: VanBan2000
    nguon_tham_khao: NguonThamKhao = None

    _khuyen_cao_bat_buoc = field_validator("khuyen_cao")(_bat_buoc)


class TuongTacDoc(BaseModel):
    hoat_chat_a_id: int
    ten_hoat_chat_a: str
    hoat_chat_b_id: int
    ten_hoat_chat_b: str
    muc_do: MucDoTuongTac
    co_che: str | None
    khuyen_cao: str
    nguon_tham_khao: str | None
    nguoi_cap_nhat: str | None
    """Họ tên dược sĩ cập nhật gần nhất."""
    updated_at: datetime | None
    phien_ban: str
    """Dấu vân tay nội dung (khóa lạc quan khi sửa, xóa)."""

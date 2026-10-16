"""Schema API duyệt bài viết sức khỏe (DS10). Soạn bài là việc của AD07 (T2.6); ở đây dược sĩ chỉ đọc và duyệt."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import LoaiBaiViet, TrangThaiNoiDung


class BaiVietTomTat(BaseModel):
    id: int
    tieu_de: str
    slug: str
    loai: LoaiBaiViet
    trang_thai: TrangThaiNoiDung
    tac_gia: str
    created_at: datetime
    updated_at: datetime | None


class BaiVietChiTiet(BaiVietTomTat):
    noi_dung: str
    anh_bia_url: str | None
    dua_vao_ai: bool
    duoc_si_duyet: str | None
    ngay_duyet: datetime | None
    phien_ban: str


class DuyetBaiViet(BaseModel):
    """`phien_ban` là giá trị `GET` trả về lúc dược sĩ đọc bài: chỉ duyệt đúng bản đã đọc."""

    model_config = ConfigDict(extra="forbid")

    phien_ban: str = Field(min_length=16, max_length=16, pattern=r"^[0-9a-f]{16}$")

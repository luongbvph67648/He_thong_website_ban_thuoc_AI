"""Schema hồ sơ sức khỏe (KTV11, spec 06 mục 3.28). Dữ liệu nhạy cảm: không bao giờ đưa vào log."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

GhiChu = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255, pattern=r"^[^\x00]*$")]
BenhNen = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000, pattern=r"^[^\x00]*$")]


class DiUngVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hoat_chat_id: Annotated[int, Field(ge=1, le=2_147_483_647)]
    ghi_chu: GhiChu | None = None


class HoSoVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dong_y_su_dung: bool
    nam_sinh: Annotated[int, Field(ge=1900, le=2100)] | None = None
    benh_nen: BenhNen | None = None
    dang_mang_thai: bool | None = None
    dang_cho_con_bu: bool | None = None
    di_ung: Annotated[list[DiUngVao], Field(max_length=100)] = []


class DiUngRa(BaseModel):
    hoat_chat_id: int
    ten_hoat_chat: str
    ghi_chu: str | None


class HoSoRa(BaseModel):
    """`dong_y_su_dung = false` và các trường rỗng khi khách chưa có hồ sơ."""

    dong_y_su_dung: bool = False
    dong_y_luc: str | None = None
    nam_sinh: int | None = None
    benh_nen: str | None = None
    dang_mang_thai: bool | None = None
    dang_cho_con_bu: bool | None = None
    di_ung: list[DiUngRa] = []


class HoatChatChon(BaseModel):
    """Một lựa chọn hoạt chất; chỉ có id và tên (danh mục công khai, không chứa dữ liệu của khách)."""

    id: int
    ten: str

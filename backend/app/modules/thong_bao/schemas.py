"""Schema API thông báo (spec 06)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ThongBaoDoc(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    loai: str
    tieu_de: str
    noi_dung: str | None
    lien_ket: str | None
    da_doc: bool
    created_at: datetime


class SoChuaDoc(BaseModel):
    so_chua_doc: int


class DaDocTatCa(BaseModel):
    da_cap_nhat: int

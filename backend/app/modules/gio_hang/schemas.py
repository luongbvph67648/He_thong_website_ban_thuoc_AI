"""Schema giỏ hàng (KVL07, spec 06 mục 3.20)."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.tien import TienDoc

IdSql = Annotated[int, Field(ge=1, le=2_147_483_647)]
SoLuongDong = Annotated[int, Field(ge=1, le=9999)]
TOI_DA_DONG_VAO = 100
LyDo = Literal["thuoc_ke_don", "khong_hien_thi", "don_vi_khong_hop_le", "vuot_toi_da"]


class DongVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    san_pham_id: IdSql
    don_vi_id: IdSql
    so_luong: SoLuongDong


class DanhSachDongVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dong: Annotated[list[DongVao], Field(max_length=TOI_DA_DONG_VAO)]


class SuaDong(BaseModel):
    model_config = ConfigDict(extra="forbid")

    so_luong: SoLuongDong | None = None
    don_vi_id: IdSql | None = None


class SanPhamTrongGio(BaseModel):
    id: int
    ten: str
    slug: str
    anh_chinh_url: str | None
    can_tu_van: bool


class DonViTrongGio(BaseModel):
    id: int
    ten_don_vi: str
    he_so: int
    gia_ban: TienDoc


class DongGio(BaseModel):
    dong_id: int | None
    san_pham: SanPhamTrongGio
    don_vi: DonViTrongGio | None
    don_vi_co_the_chon: list[DonViTrongGio]
    so_luong: int
    thanh_tien: TienDoc
    toi_da_don_vi: int | None
    ton_kha_dung_don_vi: int
    mua_duoc: bool
    ly_do: LyDo | None


class GioHangRa(BaseModel):
    dong: list[DongGio]
    tam_tinh: TienDoc
    tong_so_luong: int


class DongBoQua(BaseModel):
    san_pham_id: int
    don_vi_id: int
    ly_do: LyDo


class KetQuaGop(BaseModel):
    gio_hang: GioHangRa
    bo_qua: list[DongBoQua]


class MuaKem(BaseModel):
    id: int
    ten: str
    slug: str
    anh_chinh_url: str | None
    don_vi_id: int
    ten_don_vi: str
    gia_ban: TienDoc

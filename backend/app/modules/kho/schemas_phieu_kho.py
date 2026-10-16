"""Schema API phiếu hủy, phiếu xuất trả NCC và duyệt phiếu kho (KHO09, KHO11, AD12, spec 06 mục 3.18)."""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from app.core.kieu_du_lieu import chuan_hoa_van_ban, van_ban_tuy_chon
from app.core.tien import Tien, TienDoc
from app.models.enums import KhuTon, LyDoHuyHang, TrangThaiDuyet
from app.modules.kho.schemas_kiem_ke import TON_TOI_DA
from app.modules.kho.schemas_phieu_nhap import IdDb, NhanVienRut, SanPhamRut

LoaiPhieu = Literal["dieu-chinh", "huy", "xuat-tra"]


def _van_ban_bat_buoc(gia_tri: object) -> object:
    if not isinstance(gia_tri, str):
        return gia_tri
    gon = chuan_hoa_van_ban(gia_tri, 1000, nhieu_dong=True)
    if gon is None:
        raise ValueError("Không được để trống")
    return gon


LyDoBatBuoc = Annotated[str, BeforeValidator(_van_ban_bat_buoc)]


class DongPhieuVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lo_id: IdDb
    tu_khu: KhuTon
    so_luong: Annotated[int, Field(ge=1, le=TON_TOI_DA, strict=True)]


class DongXuatTraVao(DongPhieuVao):
    don_gia: Tien | None = None


def _khong_trung(dong: list[DongPhieuVao]) -> None:
    cap = [(d.lo_id, d.tu_khu) for d in dong]
    if len(cap) != len(set(cap)):
        raise ValueError("Mỗi cặp (lô, khu) chỉ xuất hiện một lần")


class PhieuHuyTao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ly_do: LyDoHuyHang
    mo_ta: van_ban_tuy_chon(2000, nhieu_dong=True) = None
    dong: Annotated[list[DongPhieuVao], Field(min_length=1, max_length=100)]

    @model_validator(mode="after")
    def _kiem_tra(self) -> "PhieuHuyTao":
        _khong_trung(self.dong)
        return self


class PhieuXuatTraTao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nha_cung_cap_id: IdDb
    ly_do: LyDoBatBuoc
    dong: Annotated[list[DongXuatTraVao], Field(min_length=1, max_length=100)]

    @model_validator(mode="after")
    def _kiem_tra(self) -> "PhieuXuatTraTao":
        _khong_trung(self.dong)
        return self


class TuChoi(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ly_do: LyDoBatBuoc


class DongPhieuRa(BaseModel):
    lo_id: int
    san_pham: SanPhamRut
    so_lo: str
    han_su_dung: date
    tu_khu: KhuTon
    so_luong: int


class DongXuatTraRa(DongPhieuRa):
    don_gia: TienDoc | None


class NccRut(BaseModel):
    id: int
    ten: str


class PhieuKhoTomTat(BaseModel):
    id: int
    ma_phieu: str
    ly_do: str
    trang_thai_duyet: TrangThaiDuyet
    nguoi_lap: NhanVienRut
    created_at: datetime
    so_dong: int


class PhieuHuyTomTat(PhieuKhoTomTat):
    pass


class PhieuXuatTraTomTat(PhieuKhoTomTat):
    nha_cung_cap: NccRut


class _ChiTietDuyet(BaseModel):
    nguoi_duyet: NhanVienRut | None
    ly_do_tu_choi: str | None
    duyet_luc: datetime | None


class PhieuHuyChiTiet(PhieuHuyTomTat, _ChiTietDuyet):
    mo_ta: str | None
    dong: list[DongPhieuRa]


class PhieuXuatTraChiTiet(PhieuXuatTraTomTat, _ChiTietDuyet):
    da_xac_nhan: bool
    dong: list[DongXuatTraRa]


class PhieuChoDuyet(BaseModel):
    """Một dòng của danh sách duyệt gộp ba loại phiếu."""

    loai: LoaiPhieu
    id: int
    ma_phieu: str
    ly_do: str
    trang_thai_duyet: TrangThaiDuyet
    nguoi_lap: NhanVienRut
    created_at: datetime
    so_dong: int

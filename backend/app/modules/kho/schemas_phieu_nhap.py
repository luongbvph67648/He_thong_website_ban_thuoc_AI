"""Schema API phiếu nhập kho (KHO02, spec 06 mục 3.15)."""

from datetime import date, datetime
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from app.core.kieu_du_lieu import _gon, van_ban_tuy_chon
from app.core.tien import Tien, TienDoc

IdDb = Annotated[int, Field(ge=1, le=2_147_483_647, strict=True)]
SO_DONG_TOI_DA = 100
SO_LUONG_TOI_DA_MOI_DONG = 1_000_000
SO_LO_TOI_DA = 50


def _so_lo(gia_tri: Any) -> Any:
    """Số lô của nhà sản xuất: gọn khoảng trắng và viết hoa, để `lo01` và `LO01` không thành hai lô."""
    gon = _gon(gia_tri)
    return gon.upper() if isinstance(gon, str) else gon


SoLo = Annotated[str, BeforeValidator(_so_lo), Field(min_length=1, max_length=SO_LO_TOI_DA)]


class DongNhapVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    san_pham_id: IdDb
    don_vi_id: IdDb
    so_lo: SoLo
    ngay_san_xuat: date | None = None
    han_su_dung: date
    so_luong: Annotated[int, Field(ge=1, le=SO_LUONG_TOI_DA_MOI_DONG, strict=True)]
    gia_nhap: Tien


class PhieuNhapTao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nha_cung_cap_id: IdDb
    so_hoa_don_ncc: van_ban_tuy_chon(50) = None
    ghi_chu: van_ban_tuy_chon(2000, nhieu_dong=True) = None
    dong: Annotated[list[DongNhapVao], Field(min_length=1, max_length=SO_DONG_TOI_DA)]
    xac_nhan_canh_bao: bool = False


class NhaCungCapRut(BaseModel):
    id: int
    ten: str


class NhanVienRut(BaseModel):
    id: int
    ma_nhan_vien: str
    ho_ten: str


class SanPhamRut(BaseModel):
    id: int
    sku: str
    ten: str


class DonViRut(BaseModel):
    id: int
    ten_don_vi: str
    he_so: int


class CanhBao(BaseModel):
    dong: int
    loai: str
    han_su_dung: date
    so_ngay_con_lai: int
    toi_thieu: int


class DongNhapRa(BaseModel):
    lo_id: int
    san_pham: SanPhamRut
    so_lo: str
    ngay_san_xuat: date | None
    han_su_dung: date
    don_vi: DonViRut
    so_luong: int
    so_luong_co_so: int
    gia_nhap: TienDoc
    thanh_tien: TienDoc


class PhieuNhapTomTat(BaseModel):
    id: int
    ma_phieu: str
    nha_cung_cap: NhaCungCapRut
    so_hoa_don_ncc: str | None
    nhan_vien: NhanVienRut
    ngay_nhap: datetime
    tong_tien: TienDoc
    so_dong: int


class PhieuNhapChiTiet(PhieuNhapTomTat):
    ghi_chu: str | None
    dong: list[DongNhapRa]
    canh_bao: list[CanhBao] = []


class DonViTraCuu(DonViRut):
    ma_vach: str | None


class SanPhamTraCuu(SanPhamRut):
    don_vi: list[DonViTraCuu]
    don_vi_mac_dinh_id: int | None

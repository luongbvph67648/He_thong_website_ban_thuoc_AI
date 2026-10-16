"""Schema API kiểm kê và phiếu điều chỉnh tồn (KHO07, KHO08, spec 06 mục 3.17)."""

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from app.core.kieu_du_lieu import chuan_hoa_van_ban
from app.models.enums import TrangThaiDuyet, TrangThaiKiemKe
from app.modules.kho.schemas_phieu_nhap import IdDb, NhanVienRut, SanPhamRut

TON_TOI_DA = 2_000_000_000


def _ly_do(gia_tri: object) -> object:
    if not isinstance(gia_tri, str):
        return gia_tri
    gon = chuan_hoa_van_ban(gia_tri, 1000, nhieu_dong=True)
    if gon is None:
        raise ValueError("Không được để trống")
    return gon


LyDo = Annotated[str, BeforeValidator(_ly_do)]


class DanhMucRut(BaseModel):
    id: int
    ten: str


# --- Kiểm kê ---------------------------------------------------------------------------------------------------------


class KiemKeTao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    danh_muc_id: IdDb | None = None


class DongSoLuong(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lo_id: IdDb
    so_luong_thuc_te: Annotated[int, Field(ge=0, le=TON_TOI_DA, strict=True)]


class NhapSoLuong(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dong: Annotated[list[DongSoLuong], Field(min_length=1, max_length=500)]

    @model_validator(mode="after")
    def _khong_trung_lo(self) -> "NhapSoLuong":
        ids = [d.lo_id for d in self.dong]
        if len(ids) != len(set(ids)):
            raise ValueError("Mỗi lô chỉ xuất hiện một lần")
        return self


class KiemKeTomTat(BaseModel):
    id: int
    ma_phieu: str
    danh_muc: DanhMucRut | None
    nhan_vien: NhanVienRut
    trang_thai: TrangThaiKiemKe
    thoi_diem_chup_ton: datetime
    chot_luc: datetime | None
    so_dong: int
    so_dong_lech: int


class DongKiemKe(BaseModel):
    lo_id: int
    san_pham: SanPhamRut
    so_lo: str
    han_su_dung: date
    so_luong_so_sach: int
    so_luong_thuc_te: int | None
    chenh_lech: int | None


class KiemKeChiTiet(KiemKeTomTat):
    dong: list[DongKiemKe]

    """Đúng một trong `phieu_kiem_ke_id` (các dòng lệch của phiếu đã chốt) hoặc `dong` (lập tay)."""


class DongDieuChinhVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lo_id: IdDb
    so_luong_thay_doi: Annotated[int, Field(ge=-TON_TOI_DA, le=TON_TOI_DA, strict=True)]


class DieuChinhTao(BaseModel):
    """Đúng một trong `phieu_kiem_ke_id` (lấy các dòng lệch của phiếu đã chốt) hoặc `dong` (lập tay)."""

    model_config = ConfigDict(extra="forbid")

    ly_do: LyDo
    phieu_kiem_ke_id: IdDb | None = None
    dong: Annotated[list[DongDieuChinhVao], Field(min_length=1, max_length=100)] | None = None

    @model_validator(mode="after")
    def _mot_trong_hai(self) -> "DieuChinhTao":
        if (self.phieu_kiem_ke_id is None) == (self.dong is None):
            raise ValueError("Cần đúng một trong phieu_kiem_ke_id hoặc dong")
        if self.dong is not None:
            ids = [d.lo_id for d in self.dong]
            if len(ids) != len(set(ids)):
                raise ValueError("Mỗi lô chỉ xuất hiện một lần")
            if any(d.so_luong_thay_doi == 0 for d in self.dong):
                raise ValueError("so_luong_thay_doi phải khác 0")
        return self


class DongDieuChinhRa(BaseModel):
    lo_id: int
    san_pham: SanPhamRut
    so_lo: str
    so_luong_thay_doi: int
    so_luong_ton_hien_tai: int


class DieuChinhTomTat(BaseModel):
    id: int
    ma_phieu: str
    phieu_kiem_ke_id: int | None
    ma_phieu_kiem_ke: str | None
    ly_do: str
    trang_thai_duyet: TrangThaiDuyet
    nguoi_lap: NhanVienRut
    created_at: datetime
    so_dong: int


class DieuChinhChiTiet(DieuChinhTomTat):
    nguoi_duyet: NhanVienRut | None
    ly_do_tu_choi: str | None
    duyet_luc: datetime | None
    dong: list[DongDieuChinhRa]

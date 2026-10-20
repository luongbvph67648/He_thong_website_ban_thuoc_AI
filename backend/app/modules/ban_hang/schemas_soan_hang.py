"""Schema soạn hàng và đóng gói (KHO03, KHO04, spec 06 mục 3.25)."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import HinhThucNhan, TrangThaiDon, TrangThaiPhanBo
from app.modules.ban_hang.schemas import VanDonRa


class LoGoiY(BaseModel):
    lo_id: int
    so_lo: str
    han_su_dung: date
    kha_dung: int


class PhanBoRa(BaseModel):
    id: int
    lo_id: int
    so_lo: str
    han_su_dung: date
    so_luong_co_so: int
    trang_thai: TrangThaiPhanBo
    ly_do_doi_lo: str | None


class DongSoanRa(BaseModel):
    ct_don_hang_id: int
    san_pham_id: int
    ten_san_pham: str
    ten_don_vi: str
    he_so: int
    so_luong: int
    ma_vach: str | None
    phan_bo: list[PhanBoRa]
    goi_y: list[LoGoiY]


class SoanHangRa(BaseModel):
    id: int
    ma_don: str
    trang_thai: TrangThaiDon
    hinh_thuc_nhan: HinhThucNhan
    ten_nguoi_nhan: str | None
    sdt_nguoi_nhan: str | None
    dia_chi_giao: str | None
    ghi_chu: str | None
    created_at: datetime
    dong: list[DongSoanRa]
    van_don: list[VanDonRa]
    che_do_van_chuyen_gia: bool
    van_chuyen_mo_phong: bool = False
    """Chạy với GHN mô phỏng (`VAN_CHUYEN_CHE_DO=mo_phong`): kho được phát webhook trạng thái đúng khuôn GHN."""


class DoiLoVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phan_bo_lo_id: int = Field(ge=1, le=2_147_483_647)
    lo_id: int = Field(ge=1, le=2_147_483_647)
    ly_do: str = Field(min_length=1, max_length=500)

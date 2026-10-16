"""Schema API nội dung website (spec 06 mục 3.14): banner và bài viết/chính sách/FAQ của Admin, và phần công khai."""

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.functional_validators import BeforeValidator

from app.core.kieu_du_lieu import DuongDanTuyChon, chuan_hoa_van_ban, kieu_ten, van_ban_tuy_chon
from app.models.enums import LoaiBaiViet, TrangThaiNoiDung

VI_TRI_BANNER = ("trang_chu_chinh", "trang_chu_phu")
ViTriBanner = Literal["trang_chu_chinh", "trang_chu_phu"]
PhienBan = Annotated[str, Field(min_length=16, max_length=16, pattern=r"^[0-9a-f]{16}$")]
TOI_DA_NOI_DUNG = 100_000
TOI_DA_TIEU_DE = 255

TieuDeBanner = van_ban_tuy_chon(200)


def _kiem_tra_noi_dung(gia_tri: object) -> object:
    """Markdown nhiều dòng: bỏ ký tự điều khiển/vô hình (NUL, surrogate lẻ làm CSDL báo 500), giữ xuống dòng và tab."""
    if not isinstance(gia_tri, str):
        return gia_tri
    gon = chuan_hoa_van_ban(gia_tri, TOI_DA_NOI_DUNG, nhieu_dong=True)
    if gon is None:
        raise ValueError("Không được để trống")
    return gon


NoiDungBaiViet = Annotated[str, BeforeValidator(_kiem_tra_noi_dung)]
TieuDeBaiViet = kieu_ten(TOI_DA_TIEU_DE)

MIEN_NAM_BANNER = (2000, 2100)


def _thoi_diem_trong_mien(gia_tri: datetime | None) -> datetime | None:
    """Đổi về UTC (khớp giá trị CSDL trả về, nên dấu vân tay `phien_ban` không phụ thuộc múi giờ client gửi) và chặn
    năm ngoài miền: năm 0001 làm datetime từ asyncpg mất múi giờ, năm 9999 tràn khi ghi."""
    if gia_tri is None:
        return None
    try:
        utc = gia_tri.astimezone(UTC)
    except (OverflowError, ValueError):
        utc = None
    if utc is None or not MIEN_NAM_BANNER[0] <= utc.year <= MIEN_NAM_BANNER[1]:
        raise ValueError(f"Thời điểm phải trong khoảng năm {MIEN_NAM_BANNER[0]} đến {MIEN_NAM_BANNER[1]}")
    return utc


ThoiDiemBanner = Annotated[AwareDatetime | None, AfterValidator(_thoi_diem_trong_mien)]


# --- Banner ---------------------------------------------------------------------------------------


class BannerVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tieu_de: TieuDeBanner = None
    anh_url: DuongDanTuyChon
    lien_ket: DuongDanTuyChon = None
    vi_tri: ViTriBanner
    thu_tu: Annotated[int, Field(ge=0, le=9999, strict=True)] = 0
    bat_dau: ThoiDiemBanner = None
    ket_thuc: ThoiDiemBanner = None
    dang_hien: bool = True

    @field_validator("anh_url")
    @classmethod
    def _anh_bat_buoc(cls, gia_tri: str | None) -> str:
        if gia_tri is None:
            raise ValueError("Cần có ảnh")
        return gia_tri

    @model_validator(mode="after")
    def _khoang_thoi_gian(self) -> "BannerVao":
        if self.bat_dau and self.ket_thuc and self.ket_thuc <= self.bat_dau:
            raise ValueError("Thời điểm kết thúc phải sau thời điểm bắt đầu")
        return self


class BannerSua(BaseModel):
    """Chỉ gửi trường cần đổi (kèm `phien_ban`); `tieu_de`, `lien_ket`, `bat_dau`, `ket_thuc` là `null` thì xóa."""

    model_config = ConfigDict(extra="forbid")

    phien_ban: PhienBan
    tieu_de: TieuDeBanner = None
    anh_url: DuongDanTuyChon = None
    lien_ket: DuongDanTuyChon = None
    vi_tri: ViTriBanner | None = None
    thu_tu: Annotated[int, Field(ge=0, le=9999, strict=True)] | None = None
    bat_dau: ThoiDiemBanner = None
    ket_thuc: ThoiDiemBanner = None
    dang_hien: bool | None = None

    @field_validator("anh_url", "vi_tri", "thu_tu", "dang_hien", mode="before")
    @classmethod
    def _khong_duoc_null(cls, gia_tri: object) -> object:
        if gia_tri is None:
            raise ValueError("Không được để trống")
        return gia_tri


class BannerRa(BaseModel):
    id: int
    tieu_de: str | None
    anh_url: str
    lien_ket: str | None
    vi_tri: str
    thu_tu: int
    bat_dau: datetime | None
    ket_thuc: datetime | None
    dang_hien: bool
    tinh_trang: Literal["dang_hien", "da_tat", "chua_den_gio", "het_han"]
    phien_ban: str


class AnhDaTai(BaseModel):
    url: str


# --- Bài viết, chính sách, FAQ (Admin) ------------------------------------------------------------


class BaiVietVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    loai: LoaiBaiViet
    tieu_de: TieuDeBaiViet
    noi_dung: NoiDungBaiViet
    anh_bia_url: DuongDanTuyChon = None
    dua_vao_ai: bool = False


class BaiVietSua(BaseModel):
    """Không đổi `loai` (đổi loại là cách vòng qua bước dược sĩ duyệt). `anh_bia_url` gửi `null` là bỏ ảnh bìa."""

    model_config = ConfigDict(extra="forbid")

    phien_ban: PhienBan
    tieu_de: TieuDeBaiViet | None = None
    noi_dung: NoiDungBaiViet | None = None
    anh_bia_url: DuongDanTuyChon = None
    dua_vao_ai: bool | None = None

    @field_validator("tieu_de", "noi_dung", "dua_vao_ai", mode="before")
    @classmethod
    def _khong_duoc_null(cls, gia_tri: object) -> object:
        if gia_tri is None:
            raise ValueError("Không được để trống")
        return gia_tri


class ChuyenTrangThai(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phien_ban: PhienBan


class BaiVietTomTatAdmin(BaseModel):
    id: int
    tieu_de: str
    slug: str
    loai: LoaiBaiViet
    trang_thai: TrangThaiNoiDung
    dua_vao_ai: bool
    tac_gia: str
    created_at: datetime
    updated_at: datetime | None
    ngay_duyet: datetime | None


class BaiVietAdmin(BaiVietTomTatAdmin):
    noi_dung: str
    anh_bia_url: str | None
    duoc_si_duyet: str | None
    phien_ban: str


# --- Công khai ------------------------------------------------------------------------------------


class BaiVietCongKhaiTomTat(BaseModel):
    id: int
    tieu_de: str
    slug: str
    loai: LoaiBaiViet
    anh_bia_url: str | None
    tom_tat: str
    ngay_dang: datetime
    noi_dung: str | None = None


class BaiVietCongKhai(BaseModel):
    id: int
    tieu_de: str
    slug: str
    loai: LoaiBaiViet
    anh_bia_url: str | None
    noi_dung: str
    ngay_dang: datetime

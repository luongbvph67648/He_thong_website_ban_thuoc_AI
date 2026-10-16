"""Schema API sản phẩm: thông tin thương mại (AD04, spec 06 mục 3.11).

Chỉ trường thương mại; nội dung chuyên môn (chỉ định, liều dùng...) thuộc DS10 nên mọi body từ chối trường lạ.
Các quy tắc chỉ cần nhìn danh sách (một đơn vị cơ sở, tối đa một mặc định, tên không trùng) nằm ở đây để dùng chung cho
tạo và thay danh sách đơn vị; các quy tắc cần dữ liệu trong DB nằm ở service.
"""

import re
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints, field_validator

from app.core.kieu_du_lieu import kieu_ten, van_ban_tuy_chon
from app.core.slug import bo_dau, tao_slug
from app.core.tien import Tien
from app.models.enums import LoaiSanPham, TrangThaiKinhDoanh

SO_ANH_TOI_DA = 20

IdSql = Annotated[int, Field(ge=1, le=2_147_483_647)]
PhienBan = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{16}$")]
"""Dấu vân tay nội dung của cả sản phẩm (khóa lạc quan)."""

_SKU = re.compile(r"[A-Z0-9][A-Z0-9._-]{0,49}")
_MA_VACH = re.compile(r"[0-9A-Za-z._-]{1,50}")


def _chuan_sku(gia_tri: Any) -> Any:
    if not isinstance(gia_tri, str):
        return gia_tri
    sku = gia_tri.strip().upper()
    if not _SKU.fullmatch(sku):
        raise ValueError("SKU gồm chữ, số, dấu chấm, gạch dưới, gạch ngang, bắt đầu bằng chữ hoặc số, tối đa 50 ký tự")
    return sku


Sku = Annotated[str, BeforeValidator(_chuan_sku)]
TenSanPham = kieu_ten(255)
TenDonVi = kieu_ten(30)
VanBan50 = van_ban_tuy_chon(50)
VanBan100 = van_ban_tuy_chon(100)
VanBan150 = van_ban_tuy_chon(150)


def _ma_vach_tuy_chon(gia_tri: Any) -> Any:
    if gia_tri is None:
        return None
    if not isinstance(gia_tri, str):
        raise ValueError("Phải là chuỗi")
    ma = gia_tri.strip()
    if ma == "":
        return None
    if not _MA_VACH.fullmatch(ma):
        raise ValueError("Mã vạch gồm chữ, số, dấu chấm, gạch dưới, gạch ngang, tối đa 50 ký tự, không có khoảng trắng")
    return ma


MaVach = Annotated[str | None, BeforeValidator(_ma_vach_tuy_chon)]


def _ten_phai_co_chu(ten: str) -> str:
    try:
        tao_slug(ten)
    except ValueError as loi:
        raise ValueError("Tên phải có ít nhất một chữ hoặc số") from loi
    return ten


def khoa_ten_don_vi(ten: str) -> str:
    """Khóa so sánh tên đơn vị: không phân biệt hoa thường và dấu ("Hộp" và "hop" là một)."""
    return bo_dau(ten).lower()


# --- Đơn vị quy đổi và thành phần -------------------------------------------------------------------------------------


class DonViVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: IdSql | None = None
    """Có `id`: sửa đơn vị đang có (phải thuộc sản phẩm này); không có: thêm mới."""
    ten_don_vi: TenDonVi
    he_so: Annotated[int, Field(ge=1, le=1_000_000, strict=True)]
    """Số đơn vị cơ sở trong một đơn vị này; đơn vị cơ sở có `he_so = 1`."""
    gia_ban: Tien
    ban_online: bool = True
    la_mac_dinh: bool = False
    ma_vach: MaVach = None


def kiem_tra_danh_sach_don_vi(don_vi: list[DonViVao]) -> list[DonViVao]:
    """Quy tắc của cả danh sách đơn vị (spec 06 mục 3.11)."""
    if not don_vi:
        raise ValueError("Sản phẩm phải có ít nhất một đơn vị (đơn vị cơ sở)")
    if sum(1 for d in don_vi if d.he_so == 1) != 1:
        raise ValueError("Phải có đúng một đơn vị cơ sở (hệ số 1)")
    if sum(1 for d in don_vi if d.la_mac_dinh) > 1:
        raise ValueError("Chỉ được một đơn vị mặc định")
    khoa = [khoa_ten_don_vi(d.ten_don_vi) for d in don_vi]
    if len(set(khoa)) != len(khoa):
        raise ValueError("Tên đơn vị không được trùng nhau")
    ma_vach = [d.ma_vach for d in don_vi if d.ma_vach]
    if len({m.upper() for m in ma_vach}) != len(ma_vach):
        raise ValueError("Mã vạch không được trùng giữa các đơn vị")
    id_co = [d.id for d in don_vi if d.id is not None]
    if len(set(id_co)) != len(id_co):
        raise ValueError("Một đơn vị xuất hiện hai lần")
    return don_vi


class ThanhPhanVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hoat_chat_id: IdSql
    ham_luong: VanBan50 = None


def kiem_tra_danh_sach_thanh_phan(thanh_phan: list[ThanhPhanVao]) -> list[ThanhPhanVao]:
    ids = [t.hoat_chat_id for t in thanh_phan]
    if len(set(ids)) != len(ids):
        raise ValueError("Mỗi hoạt chất chỉ được xuất hiện một lần")
    return thanh_phan


# --- Sản phẩm ---------------------------------------------------------------------------------------------------------


class SanPhamTao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sku: Sku
    ten: TenSanPham
    loai_san_pham: LoaiSanPham
    danh_muc_id: IdSql
    thuong_hieu_id: IdSql | None = None
    nha_san_xuat_id: IdSql | None = None
    so_dang_ky: VanBan50 = None
    dang_bao_che: VanBan100 = None
    quy_cach: VanBan150 = None
    doi_tuong_su_dung: VanBan150 = None
    ton_toi_thieu: Annotated[int, Field(ge=0, le=1_000_000_000, strict=True)] = 0
    dung_dinh_ky: bool = False
    so_ngay_dung_moi_don_vi: Annotated[Decimal, Field(gt=0, lt=10_000, max_digits=6, decimal_places=2)] | None = None
    so_luong_toi_da_moi_don: Annotated[int, Field(ge=1, le=1_000_000_000, strict=True)] | None = None
    la_noi_bat: bool = False
    trang_thai: TrangThaiKinhDoanh = TrangThaiKinhDoanh.dang_kinh_doanh
    don_vi: list[DonViVao]
    thanh_phan: list[ThanhPhanVao] = []

    _ten_co_chu = field_validator("ten")(_ten_phai_co_chu)
    _kiem_tra_don_vi = field_validator("don_vi")(kiem_tra_danh_sach_don_vi)
    _kiem_tra_thanh_phan = field_validator("thanh_phan")(kiem_tra_danh_sach_thanh_phan)


def vi_pham_cheo(
    dung_dinh_ky: bool, so_ngay: Decimal | None, loai: LoaiSanPham, la_noi_bat: bool
) -> tuple[str, str] | None:
    """Quy tắc giữa các trường: `(trường, lỗi)` nếu vi phạm. Dùng cho tạo và cho sửa (sau khi gộp giá trị cũ và mới)."""
    if dung_dinh_ky and so_ngay is None:
        return "so_ngay_dung_moi_don_vi", "Dùng định kỳ thì phải có số ngày dùng cho mỗi đơn vị"
    if not dung_dinh_ky and so_ngay is not None:
        return "so_ngay_dung_moi_don_vi", "Chỉ sản phẩm dùng định kỳ mới có số ngày dùng cho mỗi đơn vị"
    if la_noi_bat and loai == LoaiSanPham.thuoc_ke_don:
        return "la_noi_bat", "Không đặt thuốc kê đơn làm sản phẩm nổi bật"
    return None


class SanPhamSua(BaseModel):
    """Chỉ gửi trường cần đổi (kèm `phien_ban`). Đơn vị, thành phần, ảnh có route riêng."""

    model_config = ConfigDict(extra="forbid")

    phien_ban: PhienBan
    sku: Sku | None = None
    ten: TenSanPham | None = None
    loai_san_pham: LoaiSanPham | None = None
    danh_muc_id: IdSql | None = None
    thuong_hieu_id: IdSql | None = None
    nha_san_xuat_id: IdSql | None = None
    so_dang_ky: VanBan50 = None
    dang_bao_che: VanBan100 = None
    quy_cach: VanBan150 = None
    doi_tuong_su_dung: VanBan150 = None
    ton_toi_thieu: Annotated[int, Field(ge=0, le=1_000_000_000, strict=True)] | None = None
    dung_dinh_ky: bool | None = None
    so_ngay_dung_moi_don_vi: Annotated[Decimal, Field(gt=0, lt=10_000, max_digits=6, decimal_places=2)] | None = None
    so_luong_toi_da_moi_don: Annotated[int, Field(ge=1, le=1_000_000_000, strict=True)] | None = None
    la_noi_bat: bool | None = None
    trang_thai: TrangThaiKinhDoanh | None = None

    @field_validator(
        "sku",
        "ten",
        "loai_san_pham",
        "danh_muc_id",
        "ton_toi_thieu",
        "dung_dinh_ky",
        "la_noi_bat",
        "trang_thai",
        mode="before",
    )
    @classmethod
    def _khong_duoc_null(cls, gia_tri: object) -> object:
        if gia_tri is None:
            raise ValueError("Không được để trống")
        return gia_tri

    @field_validator("ten")
    @classmethod
    def _ten_co_chu(cls, ten: str | None) -> str | None:
        return None if ten is None else _ten_phai_co_chu(ten)


class ThayDonVi(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phien_ban: PhienBan
    don_vi: list[DonViVao]

    _kiem_tra = field_validator("don_vi")(kiem_tra_danh_sach_don_vi)


class ThayThanhPhan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phien_ban: PhienBan
    thanh_phan: list[ThanhPhanVao]

    _kiem_tra = field_validator("thanh_phan")(kiem_tra_danh_sach_thanh_phan)


class DatThuTuAnh(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phien_ban: PhienBan
    ids: Annotated[list[IdSql], Field(min_length=1, max_length=SO_ANH_TOI_DA)]


class DatAnhChinh(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phien_ban: PhienBan


# --- Đọc --------------------------------------------------------------------------------------------------------------


class DonViDoc(BaseModel):
    id: int
    ten_don_vi: str
    he_so: int
    gia_ban: Tien
    ban_online: bool
    la_mac_dinh: bool
    ma_vach: str | None


class ThanhPhanDoc(BaseModel):
    hoat_chat_id: int
    ten_hoat_chat: str
    ham_luong: str | None


class AnhDoc(BaseModel):
    id: int
    url: str
    thu_tu: int
    la_anh_chinh: bool


class SanPhamTomTat(BaseModel):
    id: int
    sku: str
    ten: str
    slug: str
    loai_san_pham: LoaiSanPham
    danh_muc_id: int
    ten_danh_muc: str
    thuong_hieu_id: int | None
    ten_thuong_hieu: str | None
    trang_thai: TrangThaiKinhDoanh
    la_noi_bat: bool
    don_vi_co_so: str
    gia_mac_dinh: Tien | None
    anh_chinh_url: str | None
    created_at: datetime


class SanPhamChiTiet(BaseModel):
    id: int
    sku: str
    ten: str
    slug: str
    loai_san_pham: LoaiSanPham
    danh_muc_id: int
    ten_danh_muc: str
    thuong_hieu_id: int | None
    ten_thuong_hieu: str | None
    nha_san_xuat_id: int | None
    ten_nha_san_xuat: str | None
    so_dang_ky: str | None
    dang_bao_che: str | None
    quy_cach: str | None
    doi_tuong_su_dung: str | None
    don_vi_co_so: str
    ton_toi_thieu: int
    dung_dinh_ky: bool
    so_ngay_dung_moi_don_vi: Decimal | None
    so_luong_toi_da_moi_don: int | None
    la_noi_bat: bool
    trang_thai: TrangThaiKinhDoanh
    created_at: datetime
    updated_at: datetime | None
    don_vi: list[DonViDoc]
    thanh_phan: list[ThanhPhanDoc]
    anh: list[AnhDoc]
    phien_ban: str

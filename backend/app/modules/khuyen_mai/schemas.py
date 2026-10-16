"""Schema khuyến mãi và mã giảm giá (AD06, KTV04, spec 06 mục 3.21)."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.core.kieu_du_lieu import kieu_ten
from app.core.tien import Tien, TienDoc
from app.models.enums import LoaiGiamGia, PhamViKhuyenMai
from app.modules.khuyen_mai.ap_dung import MaLyDo

TrangThaiHieuLuc = Literal["da_tat", "sap_dien_ra", "dang_hieu_luc", "het_han"]
NAM_TOI_THIEU, NAM_TOI_DA = 2000, 2100
PhienBan = Annotated[str, Field(min_length=1, max_length=64)]


def _trong_mien(gia_tri: datetime) -> datetime:
    if not NAM_TOI_THIEU <= gia_tri.year <= NAM_TOI_DA:
        raise ValueError(f"Thời điểm phải trong khoảng năm {NAM_TOI_THIEU} đến {NAM_TOI_DA}")
    return gia_tri


ThoiDiem = Annotated[AwareDatetime, AfterValidator(_trong_mien)]
MaCode = Annotated[str, Field(min_length=4, max_length=30, pattern=r"^[A-Za-z0-9_-]+$")]


class _KhuyenMaiChung(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ten: kieu_ten(200)
    loai_giam: LoaiGiamGia
    gia_tri: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    giam_toi_da: Tien | None = None
    don_toi_thieu: Tien = Decimal(0)
    bat_dau: ThoiDiem
    ket_thuc: ThoiDiem
    tong_luot: Annotated[int, Field(ge=1, le=10_000_000, strict=True)] | None = None
    luot_moi_khach: Annotated[int, Field(ge=1, le=1000, strict=True)] = 1
    pham_vi: PhamViKhuyenMai = PhamViKhuyenMai.toan_bo
    danh_muc_ids: Annotated[list[Annotated[int, Field(ge=1, le=2_147_483_647)]], Field(max_length=50)] = []  # noqa: B006
    san_pham_ids: Annotated[list[Annotated[int, Field(ge=1, le=2_147_483_647)]], Field(max_length=200)] = []  # noqa: B006
    dang_hoat_dong: bool = True

    @field_validator("danh_muc_ids", "san_pham_ids")
    @classmethod
    def _khong_trung(cls, v: list[int]) -> list[int]:
        if len(set(v)) != len(v):
            raise ValueError("Có phần tử trùng")
        return v

    @model_validator(mode="after")
    def _kiem_tra(self):
        loi: list[tuple[str, str]] = []
        if self.ket_thuc <= self.bat_dau:
            loi.append(("ket_thuc", "Phải sau thời điểm bắt đầu"))
        if self.loai_giam == LoaiGiamGia.phan_tram:
            if self.gia_tri > 100:
                loi.append(("gia_tri", "Phần trăm tối đa là 100"))
        else:
            if self.gia_tri != self.gia_tri.to_integral_value():
                loi.append(("gia_tri", "Số tiền phải là số đồng nguyên"))
            if self.giam_toi_da is not None:
                loi.append(("giam_toi_da", "Chỉ dùng với giảm theo phần trăm"))
        if self.giam_toi_da is not None and self.giam_toi_da <= 0:
            loi.append(("giam_toi_da", "Phải lớn hơn 0"))
        if self.pham_vi == PhamViKhuyenMai.toan_bo and (self.danh_muc_ids or self.san_pham_ids):
            loi.append(("pham_vi", "Phạm vi toàn bộ không kèm danh mục hay sản phẩm"))
        if self.pham_vi == PhamViKhuyenMai.danh_muc and (not self.danh_muc_ids or self.san_pham_ids):
            loi.append(("danh_muc_ids", "Chọn ít nhất một danh mục (và không chọn sản phẩm)"))
        if self.pham_vi == PhamViKhuyenMai.san_pham and (not self.san_pham_ids or self.danh_muc_ids):
            loi.append(("san_pham_ids", "Chọn ít nhất một sản phẩm (và không chọn danh mục)"))
        if loi:
            raise ValueError("; ".join(f"{t}: {m}" for t, m in loi))
        return self


class KhuyenMaiVao(_KhuyenMaiChung):
    pass


class KhuyenMaiSua(_KhuyenMaiChung):
    phien_ban: PhienBan


class MaRa(BaseModel):
    id: int
    ma: str
    so_luot_da_dung: int


class PhamViRa(BaseModel):
    id: int
    ten: str


class KhuyenMaiTomTat(BaseModel):
    id: int
    ten: str
    loai_giam: LoaiGiamGia
    gia_tri: TienDoc
    giam_toi_da: TienDoc | None
    don_toi_thieu: TienDoc
    bat_dau: datetime
    ket_thuc: datetime
    tong_luot: int | None
    luot_moi_khach: int
    pham_vi: PhamViKhuyenMai
    dang_hoat_dong: bool
    trang_thai: TrangThaiHieuLuc
    so_ma: int
    da_dung: int


class KhuyenMaiChiTiet(KhuyenMaiTomTat):
    phien_ban: str
    danh_muc: list[PhamViRa]
    san_pham: list[PhamViRa]
    ma_giam_gia: list[MaRa]


class SinhMa(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ma: MaCode | None = None
    so_luong: Annotated[int, Field(ge=1, le=100, strict=True)] = 1

    @model_validator(mode="after")
    def _mot_trong_hai(self):
        if self.ma is not None and self.so_luong != 1:
            raise ValueError("so_luong: Nhập mã cụ thể thì chỉ tạo một mã")
        return self


class KiemTraMaVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ma: Annotated[str, Field(min_length=1, max_length=30)]


class KhuyenMaiCongKhai(BaseModel):
    ten: str
    loai_giam: LoaiGiamGia
    gia_tri: TienDoc
    giam_toi_da: TienDoc | None
    don_toi_thieu: TienDoc


class KetQuaKiemTraMa(BaseModel):
    hop_le: bool
    ma: str
    khuyen_mai: KhuyenMaiCongKhai | None
    co_so_giam: TienDoc
    giam: TienDoc
    ma_ly_do: MaLyDo | None
    ly_do: str | None

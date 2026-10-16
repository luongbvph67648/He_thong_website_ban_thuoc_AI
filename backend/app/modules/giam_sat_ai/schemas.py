"""Schema đánh giá câu trả lời AI (DS12) và giám sát hội thoại AI (AD11); spec 06 mục 3.46. Mọi nội dung đã ẩn danh."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import LoaiHoiThoai, TrangThaiHoiThoai, VaiTroTinNhan


class DanhGiaTinNhanRa(BaseModel):
    nguon: Literal["khach", "duoc_si"]
    ket_qua: str
    ghi_chu: str | None
    cua_toi: bool
    """Đánh giá do chính người đang xem lập (chỉ có với dược sĩ)."""


class TinNhanAnDanh(BaseModel):
    id: int
    vai_tro: VaiTroTinNhan
    noi_dung: str
    y_dinh: str | None
    dau_hieu_nguy_hiem: bool
    created_at: datetime
    danh_gia: list[DanhGiaTinNhanRa]


class HoiThoaiAnDanhTom(BaseModel):
    id: int
    created_at: datetime
    loai: LoaiHoiThoai
    trang_thai: TrangThaiHoiThoai
    bi_gan_co: bool
    ly_do_gan_co: str | None
    so_tin_nhan: int
    so_khach_bao_sai: int
    so_duoc_si_danh_gia: int
    cau_hoi_dau: str
    tong_token: int
    chi_phi: Annotated[Decimal, Field(description="USD")]


class HoiThoaiAnDanhChiTiet(HoiThoaiAnDanhTom):
    tin_nhan: list[TinNhanAnDanh]


class DanhGiaDuocSiVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ket_qua: Literal["dung", "sai"]
    ghi_chu: Annotated[str | None, Field(max_length=1000, pattern=r"^[^\x00]*$")] = None
    """Bắt buộc (từ 3 ký tự) khi `ket_qua = sai`: nội dung đúng cần có."""


class CauHoiPhoBien(BaseModel):
    y_dinh: str
    so_luong: int


class ThongKeDanhGia(BaseModel):
    khach_huu_ich: int
    khach_khong_huu_ich: int
    duoc_si_dung: int
    duoc_si_sai: int


class ThongKeAi(BaseModel):
    tu_ngay: date
    den_ngay: date
    tong_hoi_thoai: int
    so_chuyen_duoc_si: int
    ty_le_chuyen_duoc_si: Decimal | None
    """0..1, làm tròn 4 chữ số; `null` khi không có hội thoại nào."""
    so_gan_co: int
    tong_token: int
    tong_chi_phi_usd: Decimal
    cau_hoi_pho_bien: list[CauHoiPhoBien]
    danh_gia: ThongKeDanhGia


class TimKiemKhongKetQua(BaseModel):
    tu_khoa: str
    so_lan: int
    lan_cuoi: datetime

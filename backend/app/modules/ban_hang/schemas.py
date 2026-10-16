"""Schema đặt hàng của khách (KTV02, spec 06 mục 3.22)."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from app.core.kieu_du_lieu import chuan_hoa_van_ban, van_ban_tuy_chon
from app.core.tien import Tien, TienDoc
from app.models.enums import (
    HinhThucNhan,
    KenhBan,
    LoaiGiaoDich,
    PhuongThucThanhToan,
    TrangThaiDon,
    TrangThaiGiaoDich,
    TrangThaiThanhToan,
)


class DatHangVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hinh_thuc_nhan: HinhThucNhan
    phuong_thuc_tt: Literal[PhuongThucThanhToan.cod, PhuongThucThanhToan.vnpay, PhuongThucThanhToan.momo]
    dia_chi_id: int | None = Field(default=None, ge=1, le=2_147_483_647)
    ma_giam_gia: str | None = Field(default=None, max_length=40)
    tong_tien_ky_vong: Tien | None = None
    ghi_chu: van_ban_tuy_chon(500, nhieu_dong=True) = None


class DongDonRa(BaseModel):
    san_pham_id: int
    ten_san_pham: str
    ten_don_vi: str
    so_luong: int
    don_gia: TienDoc
    giam_gia_phan_bo: TienDoc
    thanh_tien: TienDoc


class MocTrangThai(BaseModel):
    """Một dòng của dòng thời gian trạng thái đơn, phía khách (không lộ nhân viên nào xử lý)."""

    tu_trang_thai: TrangThaiDon | None
    den_trang_thai: TrangThaiDon
    thoi_diem: datetime
    ghi_chu: str | None


class VanDonRa(BaseModel):
    """Vận đơn giao hàng của đơn (KTV05): mã để khách tra cứu với đơn vị vận chuyển."""

    ma_van_don: str | None
    don_vi_van_chuyen: str
    created_at: datetime


class DonHangRa(BaseModel):
    ma_don: str
    trang_thai: TrangThaiDon
    trang_thai_tt: TrangThaiThanhToan
    phuong_thuc_tt: PhuongThucThanhToan | None
    hinh_thuc_nhan: HinhThucNhan
    tam_tinh: TienDoc
    giam_gia: TienDoc
    phi_van_chuyen: TienDoc
    tong_tien: TienDoc
    han_thanh_toan: datetime | None
    ma_giam_gia: str | None
    ten_nguoi_nhan: str | None
    sdt_nguoi_nhan: str | None
    dia_chi_giao: str | None
    ghi_chu: str | None
    ly_do_huy: str | None = None
    created_at: datetime
    dong: list[DongDonRa]
    lich_su: list[MocTrangThai] = []
    van_don: list[VanDonRa] = []


class XemTruocRa(BaseModel):
    tam_tinh: TienDoc
    giam_gia: TienDoc
    phi_van_chuyen: TienDoc
    tong_tien: TienDoc
    ma_giam_gia: str | None


class HuyVao(BaseModel):
    """Khách hủy đơn: lý do không bắt buộc."""

    model_config = ConfigDict(extra="forbid")

    ly_do: van_ban_tuy_chon(500, nhieu_dong=True) = None


def _ly_do_bat_buoc(gia_tri: object) -> object:
    if not isinstance(gia_tri, str):
        return gia_tri
    gon = chuan_hoa_van_ban(gia_tri, 500, nhieu_dong=True)
    if gon is None:
        raise ValueError("Bắt buộc nhập lý do")
    return gon


class HuyNoiBoVao(BaseModel):
    """Dược sĩ hủy đơn: bắt buộc lý do (DS03)."""

    model_config = ConfigDict(extra="forbid")

    ly_do: Annotated[str, BeforeValidator(_ly_do_bat_buoc)]


class DonTomTat(BaseModel):
    """Một dòng danh sách đơn."""

    ma_don: str
    trang_thai: TrangThaiDon
    trang_thai_tt: TrangThaiThanhToan
    phuong_thuc_tt: PhuongThucThanhToan | None
    tong_tien: TienDoc
    so_san_pham: int
    created_at: datetime


class DonNoiBoTomTat(DonTomTat):
    id: int
    kenh_ban: KenhBan
    ten_nguoi_nhan: str | None
    sdt_nguoi_nhan: str | None


class MocTrangThaiNoiBo(MocTrangThai):
    nguon: str | None
    nguoi_thuc_hien: str | None


class GiaoDichRa(BaseModel):
    id: int
    loai: LoaiGiaoDich
    cong_thanh_toan: PhuongThucThanhToan
    so_tien: TienDoc
    trang_thai: TrangThaiGiaoDich
    created_at: datetime


class DonNoiBoChiTiet(DonHangRa):
    id: int
    kenh_ban: KenhBan
    khach_hang_id: int | None
    lich_su: list[MocTrangThaiNoiBo] = []  # type: ignore[assignment]
    giao_dich: list[GiaoDichRa]

"""Schema phản hồi của cửa hàng công khai (spec 06 mục 3.13). Chỉ đọc nên tiền dùng `TienDoc`."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.core.tien import TienDoc
from app.models.enums import LoaiSanPham


class MucDuongDan(BaseModel):
    ten: str
    slug: str


class DanhMucCongKhai(BaseModel):
    id: int
    ten: str
    slug: str
    anh_url: str | None
    con: list["DanhMucCongKhai"]


class DanhMucChiTiet(BaseModel):
    id: int
    ten: str
    slug: str
    anh_url: str | None
    duong_dan: list[MucDuongDan]
    con: list[DanhMucCongKhai]


class BannerCongKhai(BaseModel):
    id: int
    tieu_de: str | None
    anh_url: str
    lien_ket: str | None
    vi_tri: str


class SanPhamThe(BaseModel):
    id: int
    ten: str
    slug: str
    loai_san_pham: LoaiSanPham
    can_tu_van: bool
    thuong_hieu: str | None
    quy_cach: str | None
    anh_chinh_url: str | None
    gia: TienDoc | None
    ten_don_vi_gia: str | None
    con_hang: bool


class TrangChu(BaseModel):
    banner_chinh: list[BannerCongKhai]
    banner_phu: list[BannerCongKhai]
    noi_bat: list[SanPhamThe]
    ban_chay: list[SanPhamThe]


class ThuongHieuLoc(BaseModel):
    id: int
    ten: str


class BoLocSanPham(BaseModel):
    thuong_hieu: list[ThuongHieuLoc]
    doi_tuong: list[str]
    gia_thap_nhat: TienDoc | None
    gia_cao_nhat: TienDoc | None


class DonViBan(BaseModel):
    id: int
    ten_don_vi: str
    he_so: int
    gia_ban: TienDoc
    la_mac_dinh: bool
    con_hang: bool


class AnhCongKhai(BaseModel):
    url: str
    la_anh_chinh: bool


class ThanhPhanCongKhai(BaseModel):
    hoat_chat_id: int
    ten: str
    ham_luong: str | None


class NoiDungChuyenMonCongKhai(BaseModel):
    """Chỉ nội dung và mốc duyệt; KHÔNG có người soạn hay người duyệt."""

    phien_ban: int
    ngay_duyet: datetime | None
    chi_dinh: str | None
    chong_chi_dinh: str | None
    lieu_dung_tham_khao: str | None
    tac_dung_phu: str | None
    than_trong: str | None
    tuong_tac_thuoc: str | None
    phu_nu_co_thai_cho_con_bu: str | None
    tre_em: str | None
    qua_lieu_xu_tri: str | None
    bao_quan: str | None
    file_hdsd_url: str | None


class DanhGiaCongKhai(BaseModel):
    so_sao: int
    noi_dung: str | None
    ten_hien_thi: str
    phan_hoi: str | None
    anh: list[str] = []
    created_at: datetime


class TongHopDanhGia(BaseModel):
    so_luong: int
    tong_sao: int
    phan_bo: list[int]
    moi_nhat: list[DanhGiaCongKhai]


class TenRut(BaseModel):
    id: int
    ten: str


class SanPhamChiTietCongKhai(BaseModel):
    id: int
    sku: str
    ten: str
    slug: str
    loai_san_pham: LoaiSanPham
    can_tu_van: bool
    luu_y_khong_phai_thuoc: bool
    chi_ban_tai_quay: bool
    thuong_hieu: TenRut | None
    nha_san_xuat: str | None
    so_dang_ky: str | None
    dang_bao_che: str | None
    quy_cach: str | None
    doi_tuong_su_dung: str | None
    duong_dan_danh_muc: list[MucDuongDan]
    don_vi: list[DonViBan]
    anh: list[AnhCongKhai]
    thanh_phan: list[ThanhPhanCongKhai]
    noi_dung_chuyen_mon: NoiDungChuyenMonCongKhai | None
    con_hang: bool
    danh_gia: TongHopDanhGia
    tuong_tu: list[SanPhamThe]


class GoiYTimKiem(BaseModel):
    """Một dòng gợi ý khi gõ: sản phẩm (bấm vào mở thẳng chi tiết) hoặc hoạt chất (bấm vào để tìm)."""

    kieu: Literal["san_pham", "hoat_chat"]
    ten: str
    slug: str | None
    loai_san_pham: LoaiSanPham | None
    can_tu_van: bool

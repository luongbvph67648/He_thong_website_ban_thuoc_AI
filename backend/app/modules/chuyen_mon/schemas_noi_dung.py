"""Schema API nội dung chuyên môn của sản phẩm (DS10, spec 06 mục 3.12).

Mỗi lần sửa là MỘT PHIÊN BẢN MỚI (`thong_tin_chuyen_mon.phien_ban` tăng dần theo sản phẩm, trạng thái `nhap`); chỉ bản
`da_duyet` hiển thị cho khách và được đồng bộ vào kho tri thức AI. Chỉ dược sĩ ghi; Admin chỉ xem.
"""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.core.kieu_du_lieu import DuongDanTuyChon, van_ban_tuy_chon
from app.models.enums import LoaiSanPham, TrangThaiNoiDung

TOI_DA_KY_TU = 20_000
VanBanChuyenMon = van_ban_tuy_chon(TOI_DA_KY_TU, nhieu_dong=True)

TRUONG_VAN_BAN = (
    "chi_dinh",
    "chong_chi_dinh",
    "lieu_dung_tham_khao",
    "tac_dung_phu",
    "than_trong",
    "tuong_tac_thuoc",
    "phu_nu_co_thai_cho_con_bu",
    "tre_em",
    "qua_lieu_xu_tri",
    "bao_quan",
)
"""Các trường nội dung chuyên môn (cột Text của `thong_tin_chuyen_mon`), theo thứ tự hiển thị."""

TRUONG_NOI_DUNG = (*TRUONG_VAN_BAN, "file_hdsd_url")

IdSql = Annotated[int, Field(ge=1, le=2_147_483_647)]


class NoiDungVao(BaseModel):
    """Nội dung của MỘT phiên bản mới. Trường bỏ trống là `null` (không kế thừa từ bản trước): giao diện điền sẵn."""

    model_config = ConfigDict(extra="forbid")

    phien_ban_co_so: Annotated[int, Field(ge=1, le=2_147_483_647)] | None
    """Phiên bản mới nhất mà người soạn đã thấy (`null`: chưa có phiên bản nào). Bắt buộc có mặt (có thể là `null`):
    có người tạo bản mới hơn trong lúc đang soạn thì `409 DU_LIEU_DA_THAY_DOI`, không ngầm bỏ qua bản của họ."""
    chi_dinh: VanBanChuyenMon = None
    chong_chi_dinh: VanBanChuyenMon = None
    lieu_dung_tham_khao: VanBanChuyenMon = None
    tac_dung_phu: VanBanChuyenMon = None
    than_trong: VanBanChuyenMon = None
    tuong_tac_thuoc: VanBanChuyenMon = None
    phu_nu_co_thai_cho_con_bu: VanBanChuyenMon = None
    tre_em: VanBanChuyenMon = None
    qua_lieu_xu_tri: VanBanChuyenMon = None
    bao_quan: VanBanChuyenMon = None
    file_hdsd_url: DuongDanTuyChon = None
    """Tờ hướng dẫn sử dụng gốc: đường dẫn `/...` hoặc `http(s)://...`."""


class NguoiRut(BaseModel):
    """Nhân viên rút gọn (người soạn, người duyệt): không email, không số điện thoại."""

    id: int
    ma_nhan_vien: str
    ho_ten: str


class PhienBanNoiDung(BaseModel):
    id: int
    san_pham_id: int
    phien_ban: int
    trang_thai: TrangThaiNoiDung
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
    nguoi_soan: NguoiRut | None
    duoc_si_duyet: NguoiRut | None
    ngay_duyet: datetime | None
    created_at: datetime


class SanPhamRut(BaseModel):
    id: int
    sku: str
    ten: str
    loai_san_pham: LoaiSanPham


class NoiDungSanPham(BaseModel):
    """Toàn bộ phiên bản của một sản phẩm (mới nhất trước) và phiên bản đang hiển thị."""

    san_pham: SanPhamRut
    phien_ban_hien_thi: int | None
    """`phien_ban` của bản `da_duyet` (duy nhất); `null` nếu chưa có nội dung nào được duyệt."""
    phien_ban: list[PhienBanNoiDung]


class DongNoiDung(BaseModel):
    """Một dòng của danh sách sản phẩm cần biên soạn."""

    san_pham_id: int
    sku: str
    ten: str
    loai_san_pham: LoaiSanPham
    phien_ban_da_duyet: int | None
    ngay_duyet: datetime | None
    phien_ban_nhap_moi_nhat: int | None
    """Bản nháp mới nhất còn chờ duyệt (trạng thái `nhap`), `null` nếu không có."""
    cho_duyet: bool
    """Có bản nháp mới hơn bản đã duyệt (hoặc chưa có bản đã duyệt nào mà đã có bản nháp)."""

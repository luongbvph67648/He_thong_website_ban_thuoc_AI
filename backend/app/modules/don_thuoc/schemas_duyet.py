"""Schema duyệt yêu cầu đơn thuốc và tạo đơn (DS04, DS05; spec 06 mục 3.30)."""

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.kieu_du_lieu import van_ban_tuy_chon
from app.core.tien import TienDoc
from app.models.enums import LoaiSanPham, TrangThaiYeuCauDonThuoc
from app.modules.ban_hang.schemas import DonHangRa
from app.modules.chuyen_mon.canh_bao import CanhBaoDiUng, CanhBaoTuongTac
from app.modules.suc_khoe.schemas import HoSoRa

ID = Annotated[int, Field(ge=1, le=2_147_483_647)]


class HangChoRa(BaseModel):
    id: int
    ma_yeu_cau: str
    ho_ten: str
    so_dien_thoai: str
    trang_thai: TrangThaiYeuCauDonThuoc
    so_anh: int
    la_thanh_vien: bool
    khoa_boi_toi: bool
    khoa_luc: datetime | None
    created_at: datetime


class ThuocTrenDonRa(BaseModel):
    ten_thuoc_tren_don: str
    ham_luong: str | None
    so_luong_ke: str | None
    do_tin_cay_ai: TienDoc | None
    san_pham_id: int | None


class TrungAnhRa(BaseModel):
    ma_yeu_cau: str
    trang_thai: TrangThaiYeuCauDonThuoc
    da_su_dung: bool
    created_at: datetime


class YeuCauDuyetRa(BaseModel):
    id: int
    ma_yeu_cau: str
    ho_ten: str
    so_dien_thoai: str
    ghi_chu: str | None
    trang_thai: TrangThaiYeuCauDonThuoc
    khoa_luc: datetime | None
    het_khoa_luc: datetime | None
    la_thanh_vien: bool
    anh: list[str]
    """URL ký 10 phút (chỉ dược sĩ đang khóa yêu cầu nhận được)."""
    ket_qua_ai: Any | None
    thuoc_tren_don: list[ThuocTrenDonRa]
    checklist: dict[str, Any] | None
    trung_anh: list[TrungAnhRa]
    """Yêu cầu khác có cùng `hash_anh` (đơn có thể đã dùng)."""
    ho_so_suc_khoe: HoSoRa | None
    """Chỉ có khi qua hàm cổng `duoc_doc_ho_so_suc_khoe` (khách đã đồng ý); ngược lại `null`."""


class DonViChon(BaseModel):
    id: int
    ten_don_vi: str
    he_so: int
    gia_ban: TienDoc


class SanPhamChon(BaseModel):
    id: int
    ten: str
    loai_san_pham: LoaiSanPham
    don_vi_co_so: str
    ton_kha_dung: int
    """Theo đơn vị cơ sở."""
    hoat_chat: list[str]
    don_vi: list[DonViChon]


class DongTaoDonVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    san_pham_id: ID
    don_vi_id: ID
    so_luong: int = Field(ge=1, le=9999)


class CanhBaoVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dong: list[DongTaoDonVao] = Field(min_length=1, max_length=50)


class CanhBaoRa(BaseModel):
    tuong_tac: list[CanhBaoTuongTac]
    di_ung: list[CanhBaoDiUng]
    can_ghi_chu_tu_van: bool
    """Có cảnh báo `nghiem_trong` hoặc `chong_chi_dinh` (kể cả dị ứng): bắt buộc nhập ghi chú tư vấn."""


class ChecklistVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thong_tin_nguoi_benh: bool
    thong_tin_bac_si: bool
    ngay_ke_trong_hieu_luc: bool
    don_chua_su_dung: bool
    da_kiem_tra_tuong_tac: bool


class TaoDonVao(CanhBaoVao):
    checklist: ChecklistVao
    ghi_chu_tu_van: van_ban_tuy_chon(500, nhieu_dong=True) = None
    xac_nhan_trung_anh: bool = False
    """Dược sĩ đã xem cảnh báo ảnh trùng đơn đã dùng và vẫn chấp nhận."""


class TuChoiVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ly_do: Annotated[str, Field(min_length=3, max_length=500, pattern=r"^[^\x00]*$")]


class TaoDonRa(BaseModel):
    don: DonHangRa
    lien_ket_xac_nhan: str | None
    """Link có mã truy cập cho khách vãng lai (đã gửi SMS); thành viên xác nhận trong tài khoản (`null`)."""

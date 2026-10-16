"""Schema đổi trả (KTV09, DS09; spec 06 mục 3.32)."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.core.kieu_du_lieu import kieu_ten
from app.core.tien import TienDoc
from app.models.enums import HuongXuLyDoiTra, LyDoDoiTra, TrangThaiDoiTra

ID = Annotated[int, Field(ge=1, le=2_147_483_647)]


class DongTraVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ct_don_hang_id: ID
    so_luong: int = Field(ge=1, le=9999)


class DongTraRa(BaseModel):
    ct_don_hang_id: int
    ten_san_pham: str
    ten_don_vi: str
    so_luong_mua: int
    so_luong_tra: int
    thanh_tien: TienDoc
    so_luong_nhan: int | None
    """Kho thực nhận (đơn vị cơ sở), có sau khi kho nhận hàng."""


class DoiTraTom(BaseModel):
    ma_yeu_cau: str
    ma_don: str
    trang_thai: TrangThaiDoiTra
    ly_do: LyDoDoiTra
    huong_xu_ly: HuongXuLyDoiTra | None
    so_tien_hoan: TienDoc | None
    created_at: datetime


class DoiTraChiTietKhach(DoiTraTom):
    mo_ta: str | None
    ly_do_tu_choi: str | None
    ma_van_don: str | None
    """Mã vận đơn trả hàng gửi cho khách sau khi duyệt."""
    dong: list[DongTraRa]
    anh: list[str]
    """URL ký 10 phút của ảnh/video bằng chứng."""
    can_nhap_tai_khoan_hoan: bool
    """Đơn trả bằng COD/tiền mặt và giao dịch hoàn đã tạo: khách nhập tài khoản nhận hoàn."""
    da_nhap_tai_khoan_hoan: bool


class TaiKhoanNhanHoanVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ngan_hang: kieu_ten(100)
    so_tai_khoan: Annotated[str, Field(min_length=6, max_length=30, pattern=r"^[0-9A-Za-z]+$")]
    chu_tai_khoan: kieu_ten(150)


class DoiTraNoiBoTom(DoiTraTom):
    id: int
    ten_khach: str
    so_dien_thoai_khach: str | None
    duoc_si_duyet_toi: bool


class DoiTraNoiBoChiTiet(DoiTraChiTietKhach):
    id: int
    ten_khach: str
    so_dien_thoai_khach: str | None
    ket_qua_kiem_hang: str | None
    tong_da_thanh_toan: TienDoc
    da_co_giao_dich_hoan: bool


class DuyetVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    huong_xu_ly: HuongXuLyDoiTra


class TuChoiDoiTraVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ly_do: Annotated[str, Field(min_length=3, max_length=500, pattern=r"^[^\x00]*$")]

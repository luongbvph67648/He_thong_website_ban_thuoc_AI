"""Schema thu hồi lô (AD13, KHO12, DS13; spec 06 mục 3.37)."""

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import KetQuaLienHeThuHoi, TrangThaiLo, TrangThaiThuHoi

ID = Annotated[int, Field(ge=1, le=2_147_483_647)]
VAN_BAN = Annotated[str, Field(min_length=1, pattern=r"^[^\x00]*$")]


class LenhTao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    san_pham_id: ID
    lo_id: ID | None = None
    """Bỏ trống = thu hồi mọi lô hiện có của sản phẩm."""
    can_cu: Annotated[str, Field(min_length=3, max_length=255, pattern=r"^[^\x00]*$")]
    muc_do: Annotated[str | None, Field(max_length=50, pattern=r"^[^\x00]*$")] = None


class LoThuHoiRa(BaseModel):
    lo_id: int
    so_lo: str
    han_su_dung: date
    trang_thai: TrangThaiLo
    so_luong_ton: int
    so_luong_biet_tru: int
    so_luong_da_ban: int
    """Đã bán ra ngoài (phân bổ `da_xuat`) của lô này theo lệnh."""


class LenhTomTat(BaseModel):
    id: int
    ma_lenh: str
    san_pham_ten: str
    so_lo: str | None
    """Không có = mọi lô của sản phẩm."""
    can_cu: str
    muc_do: str | None
    trang_thai: TrangThaiThuHoi
    so_khach: int
    so_khach_da_xu_ly: int
    created_at: datetime
    dong_luc: datetime | None


class LenhChiTiet(LenhTomTat):
    lo: list[LoThuHoiRa]
    ton_con_lai: int
    """Tổng `so_luong_ton` và `so_luong_biet_tru` còn ở các lô bị thu hồi; về 0 mới đóng được lệnh."""
    don_thieu_hang: list[str] = []
    """Mã đơn mất hàng giữ lúc khóa lô, kho cần xử lý lại (chỉ có ngay khi tạo lệnh)."""


class KhachThuHoi(BaseModel):
    id: int
    ma_don: str
    ten_khach: str | None
    so_dien_thoai: str | None
    so_luong_da_ban: int
    so_luong_da_thu_ve: int
    ket_qua_lien_he: KetQuaLienHeThuHoi
    ghi_chu: str | None
    cap_nhat_luc: datetime | None


class LienHeVao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ket_qua_lien_he: KetQuaLienHeThuHoi
    so_luong_da_thu_ve: int | None = Field(default=None, ge=0, le=1_000_000)
    ghi_chu: Annotated[str | None, Field(max_length=1000, pattern=r"^[^\x00]*$")] = None

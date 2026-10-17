"""Schema báo cáo tổng hợp (AD14) và báo cáo ca (DS14); spec 06 mục 3.48. Tiền là Decimal, xuất JSON dạng chuỗi."""

from datetime import date, datetime

from pydantic import BaseModel

from app.core.tien import TienDoc
from app.modules.giam_sat_ai.schemas import ThongKeAi


class DoanhThuNgay(BaseModel):
    ngay: date
    so_don: int
    doanh_thu: TienDoc


class SanPhamBanChay(BaseModel):
    san_pham_id: int
    sku: str
    ten: str
    so_luong_co_so: int
    doanh_thu: TienDoc


class GiaTriTonTheoTrangThai(BaseModel):
    trang_thai: str
    so_luong: int
    gia_tri: TienDoc


class LoCanHan(BaseModel):
    lo_id: int
    sku: str
    ten_san_pham: str
    so_lo: str
    han_su_dung: date
    con_ngay: int
    so_luong_ton: int
    gia_tri: TienDoc


class BaoCaoTongHop(BaseModel):
    tu_ngay: date
    den_ngay: date
    so_don_hoan_tat: int
    doanh_thu: TienDoc
    """Tổng tiền khách trả của đơn vào `hoan_tat` trong kỳ (gồm phí vận chuyển, đã trừ giảm giá)."""
    hoan_tien: TienDoc
    """Tiền hoàn đã chi thành công trong kỳ (mọi đơn)."""
    doanh_thu_thuan: TienDoc
    gia_von: TienDoc
    """Giá vốn của hàng đã xuất cho các đơn hoàn tất trong kỳ, theo `phan_bo_lo`."""
    loi_nhuan_gop: TienDoc
    doanh_thu_theo_ngay: list[DoanhThuNgay]
    ban_chay: list[SanPhamBanChay]
    gia_tri_ton_kho: TienDoc
    ton_kho_theo_trang_thai: list[GiaTriTonTheoTrangThai]
    so_lo_can_han: int
    lo_can_han: list[LoCanHan]
    hieu_qua_ai: ThongKeAi


class BaoCaoCa(BaseModel):
    tu: datetime
    den: datetime
    so_don: int
    doanh_thu: TienDoc
    so_don_thuoc_da_duyet: int
    tien_mat_thu_tai_quay: TienDoc
    chuyen_khoan_thu_tai_quay: TienDoc
    so_giao_dich_tien_mat: int

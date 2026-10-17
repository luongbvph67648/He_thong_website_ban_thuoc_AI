"""DS14: báo cáo bán hàng của ca cho CHÍNH dược sĩ đang đăng nhập. Không có giá vốn, lợi nhuận (spec 05).

"Đơn do mình xử lý" = đơn mình tạo (đặt hộ, POS) có `created_at` trong ca, hoặc đơn mình xác nhận (lịch sử `da_xac_nhan`
của mình) trong ca; đơn đã hủy không tính. Tiền thu tại quầy lấy từ `thanh_toan` mình xử lý (`nhan_vien_xu_ly_id`)."""

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.core.phan_quyen import dam_bao_la_duoc_si
from app.core.thoi_gian import VN_TZ
from app.core.tien import lam_tron_vnd
from app.models.ban_hang import DonHang, LichSuTrangThai, ThanhToan, YeuCauDonThuoc
from app.models.enums import LoaiGiaoDich, PhuongThucThanhToan, TrangThaiDon, TrangThaiGiaoDich, TrangThaiYeuCauDonThuoc
from app.models.he_thong import NhanVien
from app.modules.bao_cao.schemas import BaoCaoCa

CA_TOI_DA = timedelta(days=31)


def _chuan(luc: datetime) -> datetime:
    """Thời điểm không kèm múi giờ coi là giờ Việt Nam."""
    return luc.replace(tzinfo=VN_TZ) if luc.tzinfo is None else luc


async def bao_cao_ca(db: AsyncSession, nv: NhanVien, tu: datetime, den: datetime) -> BaoCaoCa:
    await dam_bao_la_duoc_si(db, nv)
    tu, den = _chuan(tu), _chuan(den)
    if tu >= den:
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE",
            "Dữ liệu không hợp lệ",
            chi_tiet=[{"truong": "tu", "loi": "Đầu ca phải trước cuối ca"}],
        )
    if den - tu > CA_TOI_DA:
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE", "Dữ liệu không hợp lệ", chi_tiet=[{"truong": "den", "loi": "Ca tối đa 31 ngày"}]
        )
    da_xac_nhan = exists().where(
        LichSuTrangThai.don_hang_id == DonHang.id,
        LichSuTrangThai.den_trang_thai == TrangThaiDon.da_xac_nhan,
        LichSuTrangThai.nhan_vien_id == nv.id,
        LichSuTrangThai.created_at >= tu,
        LichSuTrangThai.created_at < den,
    )
    do_toi_tao = (DonHang.nhan_vien_tao_id == nv.id) & (DonHang.created_at >= tu) & (DonHang.created_at < den)
    so_don, doanh_thu = (
        await db.execute(
            select(func.count(), func.coalesce(func.sum(DonHang.tong_tien), 0)).where(
                DonHang.trang_thai != TrangThaiDon.da_huy, or_(do_toi_tao, da_xac_nhan)
            )
        )
    ).one()
    don_thuoc = await db.scalar(
        select(func.count()).where(
            YeuCauDonThuoc.duoc_si_id == nv.id,
            YeuCauDonThuoc.trang_thai == TrangThaiYeuCauDonThuoc.da_tao_don,
            func.coalesce(YeuCauDonThuoc.updated_at, YeuCauDonThuoc.created_at) >= tu,
            func.coalesce(YeuCauDonThuoc.updated_at, YeuCauDonThuoc.created_at) < den,
        )
    )

    async def thu(cong: PhuongThucThanhToan) -> tuple[int, Decimal]:
        so, tien = (
            await db.execute(
                select(func.count(), func.coalesce(func.sum(ThanhToan.so_tien), 0)).where(
                    ThanhToan.nhan_vien_xu_ly_id == nv.id,
                    ThanhToan.loai == LoaiGiaoDich.thanh_toan,
                    ThanhToan.trang_thai == TrangThaiGiaoDich.thanh_cong,
                    ThanhToan.cong_thanh_toan == cong,
                    ThanhToan.created_at >= tu,
                    ThanhToan.created_at < den,
                )
            )
        ).one()
        return so, lam_tron_vnd(Decimal(tien))

    so_tm, tien_mat = await thu(PhuongThucThanhToan.tien_mat)
    _, chuyen_khoan = await thu(PhuongThucThanhToan.chuyen_khoan)
    return BaoCaoCa(
        tu=tu,
        den=den,
        so_don=so_don,
        doanh_thu=lam_tron_vnd(Decimal(doanh_thu)),
        so_don_thuoc_da_duyet=don_thuoc or 0,
        tien_mat_thu_tai_quay=tien_mat,
        chuyen_khoan_thu_tai_quay=chuyen_khoan,
        so_giao_dich_tien_mat=so_tm,
    )

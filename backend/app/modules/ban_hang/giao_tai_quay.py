"""Giao đơn nhận tại nhà thuốc (DS15, spec 04 mục 1.1 dòng 20).

Khách đọc mã đơn hoặc SĐT; dược sĩ tìm đơn "Chờ lấy hàng" nhận tại nhà thuốc, thu tiền nếu chưa thanh toán rồi chuyển
"Đã giao" qua máy trạng thái. Thu tiền và đổi trạng thái cùng một transaction.
"""

from collections.abc import Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dien_thoai import chuan_hoa_sdt
from app.core.loi import LoiNghiepVu
from app.models.ban_hang import CtDonHang, DonHang, ThanhToan
from app.models.enums import (
    HinhThucNhan,
    LoaiGiaoDich,
    PhuongThucThanhToan,
    TrangThaiDon,
    TrangThaiGiaoDich,
    TrangThaiThanhToan,
)
from app.models.he_thong import NhanVien
from app.models.khach_hang import KhachHang
from app.modules.ban_hang.dat_hang import khong_hop_le
from app.modules.ban_hang.schemas_dat_ho import DongQuayRa, DonQuayRa
from app.modules.ban_hang.trang_thai import NGUON_NGUOI_DUNG, chuyen_trang_thai, tac_nhan_tu_nhan_vien

TOI_DA_KET_QUA = 20


def _ra(don: DonHang, dong: Sequence[CtDonHang]) -> DonQuayRa:
    return DonQuayRa(
        id=don.id,
        ma_don=don.ma_don,
        ten_nguoi_nhan=don.ten_nguoi_nhan,
        sdt_nguoi_nhan=don.sdt_nguoi_nhan,
        tong_tien=don.tong_tien,
        phuong_thuc_tt=don.phuong_thuc_tt,
        trang_thai_tt=don.trang_thai_tt,
        dong=[DongQuayRa(ten_san_pham=c.ten_san_pham, ten_don_vi=c.ten_don_vi, so_luong=c.so_luong) for c in dong],
    )


async def tim(db: AsyncSession, q: str) -> list[DonQuayRa]:
    """Tìm đơn nhận tại nhà thuốc đang "Chờ lấy hàng" theo mã đơn (đúng mã) hoặc SĐT (người nhận hoặc chủ tài khoản)."""
    q = q.strip()
    if not q:
        raise khong_hop_le("q", "Nhập mã đơn hoặc số điện thoại")
    dieu_kien = [DonHang.ma_don == q.upper()]
    try:
        sdt = chuan_hoa_sdt(q)
    except ValueError:
        pass
    else:
        dieu_kien += [
            DonHang.sdt_nguoi_nhan == sdt,
            DonHang.khach_hang_id.in_(select(KhachHang.id).where(KhachHang.so_dien_thoai == sdt)),
        ]
    ds = (
        (
            await db.execute(
                select(DonHang)
                .where(
                    DonHang.trang_thai == TrangThaiDon.cho_lay_hang,
                    DonHang.hinh_thuc_nhan == HinhThucNhan.nhan_tai_nha_thuoc,
                    or_(*dieu_kien),
                )
                .options(selectinload(DonHang.chi_tiet))
                .order_by(DonHang.created_at.desc(), DonHang.id.desc())
                .limit(TOI_DA_KET_QUA)
            )
        )
        .scalars()
        .all()
    )
    return [_ra(d, d.chi_tiet) for d in ds]


async def giao(db: AsyncSession, nv: NhanVien, don_id: int, phuong_thuc_thu: PhuongThucThanhToan | None) -> DonQuayRa:
    """Bàn giao hàng tại quầy. Đơn chưa thanh toán phải kèm `phuong_thuc_thu` (tiền mặt/chuyển khoản), ghi một giao
    dịch `thanh_toan` thành công; đơn đã thanh toán thì không thu thêm."""
    don = (await db.execute(select(DonHang).where(DonHang.id == don_id))).scalar_one_or_none()
    if don is None or don.hinh_thuc_nhan != HinhThucNhan.nhan_tai_nha_thuoc:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy đơn nhận tại nhà thuốc")
    tac_nhan = await tac_nhan_tu_nhan_vien(db, nv)
    await chuyen_trang_thai(db, don, TrangThaiDon.da_giao, tac_nhan, NGUON_NGUOI_DUNG)  # khóa đơn, kiểm tra dòng 20
    if don.trang_thai_tt == TrangThaiThanhToan.chua_thanh_toan:
        if phuong_thuc_thu is None:
            raise khong_hop_le("phuong_thuc_thu", "Đơn chưa thanh toán: chọn hình thức thu tiền")
        db.add(
            ThanhToan(
                don_hang_id=don.id,
                loai=LoaiGiaoDich.thanh_toan,
                cong_thanh_toan=phuong_thuc_thu,
                so_tien=don.tong_tien,
                trang_thai=TrangThaiGiaoDich.thanh_cong,
                nhan_vien_xu_ly_id=nv.id,
                ghi_chu="Thu tiền khi khách nhận hàng tại quầy",
            )
        )
        don.trang_thai_tt = TrangThaiThanhToan.da_thanh_toan
    dong = (await db.execute(select(CtDonHang).where(CtDonHang.don_hang_id == don.id).order_by(CtDonHang.id))).scalars()
    return _ra(don, list(dong))

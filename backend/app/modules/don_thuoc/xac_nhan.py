"""Khách xác nhận hoặc từ chối đơn từ đơn thuốc (KTV07, dòng 7, 8, 9). Không commit.

Hai đường vào: thành viên đăng nhập (`khach_hang_id` từ token) và khách vãng lai qua link mã truy cập (hash lưu trong
`token_truy_cap_hash`). Token lạ hoặc sai là `404`. Link luôn XEM được trạng thái đơn (trang kết quả thanh toán của
khách vãng lai cần đọc lại sau khi cổng đưa về), còn mọi thao tác kiểm trạng thái của đơn: xác nhận và từ chối chỉ khi
`cho_khach_xac_nhan`, tạo thanh toán chỉ khi `cho_thanh_toan` còn hạn.
"""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.cau_hinh import doc_cau_hinh
from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc
from app.models.ban_hang import DonHang
from app.models.enums import HinhThucNhan, PhuongThucThanhToan, TrangThaiDon
from app.models.khach_hang import DiaChi, KhachHang
from app.modules.ban_hang import dat_hang
from app.modules.ban_hang.schemas import DonHangRa
from app.modules.ban_hang.trang_thai import NGUON_NGUOI_DUNG, TacNhan, chuyen_trang_thai
from app.modules.dia_chi.dich_vu import ten_dia_gioi
from app.modules.don_thuoc.duyet import hash_token
from app.modules.don_thuoc.schemas_xac_nhan import DonXacNhanRa, XacNhanVao
from app.modules.thanh_toan import dich_vu as thanh_toan

TT = TrangThaiDon


def _khong_tim_thay() -> LoiNghiepVu:
    return LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy đơn hàng hoặc liên kết đã hết hiệu lực")


async def _khoa_don(db: AsyncSession, dieu_kien) -> DonHang:
    don = (
        await db.execute(
            select(DonHang)
            .where(dieu_kien, DonHang.yeu_cau_don_thuoc_id.is_not(None))
            .options(selectinload(DonHang.chi_tiet))
            .with_for_update(of=DonHang)
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if don is None:
        raise _khong_tim_thay()
    return don


async def don_theo_token(db: AsyncSession, token: str) -> DonHang:
    if not 20 <= len(token) <= 100:
        raise _khong_tim_thay()
    return await _khoa_don(db, DonHang.token_truy_cap_hash == hash_token(token))


async def don_cua_khach(db: AsyncSession, khach: KhachHang, ma_don: str) -> DonHang:
    return await _khoa_don(db, (DonHang.ma_don == ma_don[:20]) & (DonHang.khach_hang_id == khach.id))


def tac_nhan(khach: KhachHang | None) -> TacNhan:
    return TacNhan.khach_qua_link() if khach is None else TacNhan.khach(khach.id)


async def xem(db: AsyncSession, don: DonHang) -> DonXacNhanRa:
    ra = await dat_hang.don_ra_day_du(db, don)
    bay_gio = bay_gio_utc()
    con_han = don.han_xac_nhan is None or bay_gio <= don.han_xac_nhan
    online = don.phuong_thuc_tt in (PhuongThucThanhToan.vnpay, PhuongThucThanhToan.momo)
    return DonXacNhanRa(
        don=ra,
        co_the_xac_nhan=don.trang_thai == TT.cho_khach_xac_nhan and con_han,
        co_the_thanh_toan=don.trang_thai == TT.cho_thanh_toan
        and online
        and (don.han_thanh_toan is None or bay_gio <= don.han_thanh_toan),
    )


async def _chon_dia_chi(db: AsyncSession, don: DonHang, khach: KhachHang | None, vao: XacNhanVao) -> DiaChi | None:
    if vao.hinh_thuc_nhan == HinhThucNhan.nhan_tai_nha_thuoc:
        if vao.dia_chi is not None or vao.dia_chi_id is not None:
            raise dat_hang.khong_hop_le("dia_chi", "Đơn nhận tại nhà thuốc không có địa chỉ giao")
        return None
    if vao.dia_chi_id is not None:
        if khach is None:
            raise dat_hang.khong_hop_le("dia_chi_id", "Chỉ khách có tài khoản dùng được sổ địa chỉ")
        dc = (
            await db.execute(select(DiaChi).where(DiaChi.id == vao.dia_chi_id, DiaChi.khach_hang_id == khach.id))
        ).scalar_one_or_none()
        if dc is None:
            raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy địa chỉ")
        return dc
    if vao.dia_chi is None or not vao.ten_nguoi_nhan or not vao.sdt_nguoi_nhan:
        raise dat_hang.khong_hop_le("dia_chi", "Cần địa chỉ giao hàng, tên và số điện thoại người nhận")
    ten_tinh, ten_xa = ten_dia_gioi(vao.dia_chi.ma_tinh, vao.dia_chi.ma_phuong_xa)
    return DiaChi(  # chỉ để chụp vào đơn, không lưu vào sổ địa chỉ
        ten_nguoi_nhan=vao.ten_nguoi_nhan,
        so_dien_thoai=vao.sdt_nguoi_nhan,
        dia_chi_chi_tiet=vao.dia_chi.dia_chi_chi_tiet,
        ma_tinh=vao.dia_chi.ma_tinh,
        ten_tinh=ten_tinh,
        ma_phuong_xa=vao.dia_chi.ma_phuong_xa,
        ten_phuong_xa=ten_xa,
    )


async def xac_nhan(db: AsyncSession, don: DonHang, khach: KhachHang | None, vao: XacNhanVao) -> DonXacNhanRa:
    """Dòng 7 (COD -> Đã xác nhận) hoặc 8 (VNPay/MoMo -> Chờ thanh toán). `don` đã khóa. Chốt cách nhận, địa chỉ,
    phí ship (tính lại theo địa chỉ) và phương thức thanh toán rồi mới chuyển trạng thái."""
    if don.trang_thai != TT.cho_khach_xac_nhan:
        raise LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Đơn không còn ở trạng thái chờ xác nhận")
    bay_gio = bay_gio_utc()
    if don.han_xac_nhan is not None and bay_gio > don.han_xac_nhan:
        raise LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Đã quá hạn xác nhận")
    dia_chi = await _chon_dia_chi(db, don, khach, vao)
    so_co_so = sum(c.so_luong * c.he_so for c in don.chi_tiet)
    phi = await dat_hang.tinh_phi_van_chuyen(db, dia_chi, so_co_so, don.tam_tinh, don.giam_gia)
    don.hinh_thuc_nhan = vao.hinh_thuc_nhan
    don.phuong_thuc_tt = vao.phuong_thuc_tt
    don.phi_van_chuyen = phi
    don.tong_tien = don.tam_tinh - don.giam_gia + phi
    if dia_chi is not None:
        dat_hang.ghi_dia_chi_giao(don, dia_chi)
    if vao.ghi_chu:
        don.ghi_chu = f"{don.ghi_chu}\n{vao.ghi_chu}" if don.ghi_chu else vao.ghi_chu
    online = vao.phuong_thuc_tt != PhuongThucThanhToan.cod
    if online:
        phut = int(await doc_cau_hinh(db, "thoi_han_thanh_toan_phut", dat_hang.THOI_HAN_THANH_TOAN_PHUT))
        don.han_thanh_toan = bay_gio + timedelta(minutes=phut)
    await db.flush()
    await chuyen_trang_thai(db, don, TT.cho_thanh_toan if online else TT.da_xac_nhan, tac_nhan(khach), NGUON_NGUOI_DUNG)
    return await xem(db, don)


async def tu_choi(db: AsyncSession, don: DonHang, khach: KhachHang | None) -> DonHangRa:
    """Dòng 9: khách từ chối. Hook nhả hàng và đưa yêu cầu đơn thuốc về `dang_tu_van` để tạo lại đơn."""
    if don.trang_thai != TT.cho_khach_xac_nhan:
        raise LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Đơn không còn ở trạng thái chờ xác nhận")
    await chuyen_trang_thai(db, don, TT.da_huy, tac_nhan(khach), NGUON_NGUOI_DUNG, "Khách từ chối đơn")
    return await dat_hang.don_ra_day_du(db, don)


async def thanh_toan_online(db: AsyncSession, don: DonHang, khach: KhachHang | None, khoa: str, ip: str) -> dict:
    chu = khach.id if khach is not None else -don.id
    return await thanh_toan.tao_thanh_toan_don(db, don, chu, khoa, ip)

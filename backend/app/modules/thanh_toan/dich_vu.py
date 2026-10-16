"""KTV03 (tạo giao dịch thanh toán online) và HT04 (xử lý IPN), spec 06 mục 3.23."""

from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import idempotency
from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc
from app.core.tien import lam_tron_vnd
from app.models.ban_hang import DonHang, ThanhToan
from app.models.enums import LoaiGiaoDich, PhuongThucThanhToan, TrangThaiDon, TrangThaiGiaoDich, TrangThaiThanhToan
from app.modules.ban_hang.trang_thai import NGUON_THANH_TOAN, TacNhan, chuyen_trang_thai
from app.tich_hop.thanh_toan import KetQuaIpn, lay_cong

THAO_TAC = "thanh_toan_online"
CONG_ONLINE = (PhuongThucThanhToan.vnpay, PhuongThucThanhToan.momo)


class KetQuaXuLy(StrEnum):
    thanh_cong = "thanh_cong"
    khong_tim_thay = "khong_tim_thay"
    sai_so_tien = "sai_so_tien"
    da_xu_ly = "da_xu_ly"
    sai_chu_ky = "sai_chu_ky"


async def _khoa_don_cua_khach(db: AsyncSession, khach_hang_id: int, ma_don: str) -> DonHang:
    don = (
        await db.execute(
            select(DonHang)
            .where(DonHang.ma_don == ma_don, DonHang.khach_hang_id == khach_hang_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if don is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy đơn hàng")
    return don


async def tao_thanh_toan(db: AsyncSession, khach_hang_id: int, ma_don: str, khoa: str, ip: str) -> dict:
    """Tạo giao dịch `khoi_tao` cho đơn chờ thanh toán, trả URL của cổng (cùng `Idempotency-Key` thì trả URL cũ)."""
    don = await _khoa_don_cua_khach(db, khach_hang_id, ma_don)  # tuần tự hóa các lần bấm của cùng một đơn
    return await tao_thanh_toan_don(db, don, khach_hang_id, khoa, ip)


async def tao_thanh_toan_don(db: AsyncSession, don: DonHang, chu_idem: int, khoa: str, ip: str) -> dict:
    """Phần dùng chung: `don` đã khóa và đã kiểm quyền. `chu_idem` là khóa chủ sở hữu của `Idempotency-Key` (id khách,
    hoặc `-don.id` cho khách vãng lai vào bằng link mã truy cập)."""
    dau_van_tay = idempotency.dau_van_tay({"ma_don": don.ma_don})
    cu = idempotency.tra_cuu(THAO_TAC, chu_idem, khoa, dau_van_tay)
    if cu is not None and await db.scalar(select(ThanhToan.id).where(ThanhToan.id == cu["giao_dich_id"])):
        return cu["ket_qua"]
    if don.trang_thai != TrangThaiDon.cho_thanh_toan or don.phuong_thuc_tt not in CONG_ONLINE:
        raise LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Đơn hàng không ở trạng thái chờ thanh toán online")
    if don.han_thanh_toan is not None and bay_gio_utc() > don.han_thanh_toan:
        raise LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Đơn hàng đã quá hạn thanh toán")
    assert don.phuong_thuc_tt is not None
    giao_dich = ThanhToan(
        don_hang_id=don.id,
        loai=LoaiGiaoDich.thanh_toan,
        cong_thanh_toan=don.phuong_thuc_tt,
        so_tien=lam_tron_vnd(don.tong_tien),
        trang_thai=TrangThaiGiaoDich.khoi_tao,
    )
    db.add(giao_dich)
    await db.flush()
    url = await lay_cong(don.phuong_thuc_tt).tao_url_thanh_toan(don, giao_dich, ip)
    ra = {"url_thanh_toan": url, "han_thanh_toan": don.han_thanh_toan.isoformat() if don.han_thanh_toan else None}
    idempotency.ghi_nho(THAO_TAC, chu_idem, khoa, dau_van_tay, {"giao_dich_id": giao_dich.id, "ket_qua": ra})
    return ra


async def xu_ly_ipn(db: AsyncSession, cong: PhuongThucThanhToan, ket_qua: KetQuaIpn) -> KetQuaXuLy:
    """HT04. Thứ tự: chữ ký, tìm giao dịch, số tiền, chống trùng, cập nhật (spec 08 mục 2)."""
    if not ket_qua.chu_ky_hop_le:
        return KetQuaXuLy.sai_chu_ky
    ma_don, _, id_text = ket_qua.tham_chieu.rpartition("-")
    if not id_text.isdigit():
        return KetQuaXuLy.khong_tim_thay
    giao_dich = (
        await db.execute(
            select(ThanhToan)
            .where(ThanhToan.id == int(id_text), ThanhToan.loai == LoaiGiaoDich.thanh_toan)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if giao_dich is None or giao_dich.cong_thanh_toan != cong:
        return KetQuaXuLy.khong_tim_thay
    don = (
        await db.execute(
            select(DonHang)
            .where(DonHang.id == giao_dich.don_hang_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    if don.ma_don != ma_don:
        return KetQuaXuLy.khong_tim_thay
    if ket_qua.so_tien is None or lam_tron_vnd(ket_qua.so_tien) != lam_tron_vnd(don.tong_tien):
        return KetQuaXuLy.sai_so_tien
    if giao_dich.trang_thai != TrangThaiGiaoDich.khoi_tao:
        return KetQuaXuLy.da_xu_ly
    if ket_qua.ma_giao_dich_cong and await db.scalar(
        select(ThanhToan.id).where(ThanhToan.ma_giao_dich_cong == ket_qua.ma_giao_dich_cong)
    ):
        return KetQuaXuLy.da_xu_ly

    giao_dich.du_lieu_ipn = ket_qua.du_lieu
    giao_dich.updated_at = bay_gio_utc()
    if not ket_qua.thanh_cong:
        giao_dich.trang_thai = TrangThaiGiaoDich.that_bai
        return KetQuaXuLy.thanh_cong
    giao_dich.trang_thai = TrangThaiGiaoDich.thanh_cong
    giao_dich.ma_giao_dich_cong = ket_qua.ma_giao_dich_cong
    if don.trang_thai == TrangThaiDon.cho_thanh_toan and don.trang_thai_tt != TrangThaiThanhToan.da_thanh_toan:
        den = TrangThaiDon.cho_xac_nhan if don.nhan_vien_tao_id is None else TrangThaiDon.da_xac_nhan
        await chuyen_trang_thai(db, don, den, TacNhan.he_thong(), NGUON_THANH_TOAN, "Thanh toán online thành công")
    else:  # đến muộn (đơn đã hủy quá hạn) hoặc trả tiền hai lần: tiền đã vào nên phải hoàn
        db.add(
            ThanhToan(
                don_hang_id=don.id,
                loai=LoaiGiaoDich.hoan_tien,
                cong_thanh_toan=giao_dich.cong_thanh_toan,
                so_tien=giao_dich.so_tien,
                trang_thai=TrangThaiGiaoDich.khoi_tao,
                thanh_toan_goc_id=giao_dich.id,
                ghi_chu="Thanh toán đến sau khi đơn không còn chờ thanh toán",
            )
        )
        don.trang_thai_tt = TrangThaiThanhToan.cho_hoan_tien
        don.updated_at = bay_gio_utc()
    await db.flush()
    return KetQuaXuLy.thanh_cong

"""Đăng nhập khách (KVL10): kiểm tra mật khẩu, khóa tạm khi sai nhiều lần.

Bộ đếm sai và `khoa_den` phải được lưu dù request trả lỗi, nên service trả kết quả (enum) và route TRẢ VỀ lỗi
bằng `core.loi.tra_loi` (xem `core/loi.py`). Chống dò tài khoản: số/email không tồn tại và mật khẩu sai cho cùng
phản hồi và cùng thời gian (vẫn băm một lần với mã băm giả).
"""

import secrets
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from functools import cache

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bao_mat import bam_mat_khau, kiem_tra_mat_khau_async
from app.core.cau_hinh import doc_cau_hinh
from app.core.dien_thoai import chuan_hoa_sdt
from app.core.thoi_gian import bay_gio_utc
from app.models.enums import TrangThaiTaiKhoan
from app.models.khach_hang import KhachHang

SO_LAN_SAI_MAC_DINH = 5
THOI_GIAN_KHOA_PHUT_MAC_DINH = 15


class KetQuaDangNhap(StrEnum):
    OK = "ok"
    SAI_THONG_TIN = "sai_thong_tin"
    KHOA_TAM = "khoa_tam"  # nhập sai quá nhiều lần, hoặc đang trong thời gian khóa
    TAI_KHOAN_BI_KHOA = "tai_khoan_bi_khoa"  # Admin khóa (đúng mật khẩu mới biết, nên không lộ tài khoản có tồn tại)


@dataclass(frozen=True)
class KetQuaKiemTraDangNhap:
    ket_qua: KetQuaDangNhap
    khach: KhachHang | None = None
    thu_lai_sau_giay: int | None = None


@cache
def _ma_bam_gia() -> str:
    """Mã băm Argon2 của một chuỗi ngẫu nhiên: để đường "không có tài khoản" cũng tốn đúng một lần băm."""
    return bam_mat_khau(secrets.token_urlsafe(16))


def _tim_theo(dinh_danh: str):
    """Điều kiện tìm tài khoản: có `@` là email, ngược lại là số điện thoại; không hợp lệ thì None."""
    dinh_danh = dinh_danh.strip()
    if "@" in dinh_danh:
        return func.lower(KhachHang.email) == dinh_danh.lower()
    try:
        return KhachHang.so_dien_thoai == chuan_hoa_sdt(dinh_danh)
    except ValueError:
        return None


async def kiem_tra_dang_nhap(db: AsyncSession, *, ten_dang_nhap: str, mat_khau: str) -> KetQuaKiemTraDangNhap:
    """Kiểm tra thông tin đăng nhập và cập nhật bộ đếm sai/khóa. Không tạo phiên (route làm khi `OK`)."""
    dieu_kien = _tim_theo(ten_dang_nhap)
    khach = None
    if dieu_kien is not None:
        khach = (
            await db.execute(select(KhachHang).where(dieu_kien, KhachHang.deleted_at.is_(None)).with_for_update())
        ).scalar_one_or_none()
    if khach is None:
        await kiem_tra_mat_khau_async(mat_khau, _ma_bam_gia())  # cân bằng thời gian với đường có tài khoản
        return KetQuaKiemTraDangNhap(KetQuaDangNhap.SAI_THONG_TIN)

    bay_gio = bay_gio_utc()
    if khach.khoa_den and khach.khoa_den > bay_gio:
        return KetQuaKiemTraDangNhap(KetQuaDangNhap.KHOA_TAM, thu_lai_sau_giay=_giay_con_lai(khach.khoa_den, bay_gio))

    if not await kiem_tra_mat_khau_async(mat_khau, khach.mat_khau_hash):
        toi_da = int(await doc_cau_hinh(db, "so_lan_dang_nhap_sai_toi_da", SO_LAN_SAI_MAC_DINH))
        khach.so_lan_dang_nhap_sai += 1
        if khach.so_lan_dang_nhap_sai >= toi_da:
            phut = int(await doc_cau_hinh(db, "thoi_gian_khoa_dang_nhap_phut", THOI_GIAN_KHOA_PHUT_MAC_DINH))
            khach.khoa_den = bay_gio + timedelta(minutes=phut)
            khach.so_lan_dang_nhap_sai = 0
            return KetQuaKiemTraDangNhap(KetQuaDangNhap.KHOA_TAM, thu_lai_sau_giay=phut * 60)
        return KetQuaKiemTraDangNhap(KetQuaDangNhap.SAI_THONG_TIN)

    if khach.trang_thai != TrangThaiTaiKhoan.hoat_dong:
        return KetQuaKiemTraDangNhap(KetQuaDangNhap.TAI_KHOAN_BI_KHOA)
    khach.so_lan_dang_nhap_sai = 0
    khach.khoa_den = None
    return KetQuaKiemTraDangNhap(KetQuaDangNhap.OK, khach)


def _giay_con_lai(den, bay_gio) -> int:
    return max(1, int((den - bay_gio).total_seconds()) + 1)

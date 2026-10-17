"""Đăng nhập (KVL10 khách, NV01 nhân viên): kiểm tra mật khẩu, khóa tạm khi sai nhiều lần.

Bộ đếm sai và `khoa_den` phải được lưu dù request trả lỗi, nên service trả kết quả (enum) và route TRẢ VỀ lỗi
bằng `core.loi.tra_loi` (xem `core/loi.py`). Chống dò tài khoản: số/email không tồn tại và mật khẩu sai cho cùng
phản hồi và cùng thời gian (vẫn băm một lần với mã băm giả); định danh không tồn tại cũng bị khóa tạm sau cùng số lần
sai (bộ đếm trong bộ nhớ tiến trình) để việc "bị khóa" không lộ tài khoản có thật.
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
from app.models.he_thong import NhanVien
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
    tai_khoan: KhachHang | NhanVien | None = None
    thu_lai_sau_giay: int | None = None
    vua_bi_khoa: bool = False
    """`True` đúng lần sai làm tài khoản vừa bị khóa tạm (để ghi nhật ký một lần, không ghi mỗi lần thử khi khóa)."""


@cache
def _ma_bam_gia() -> str:
    """Mã băm Argon2 của một chuỗi ngẫu nhiên: để đường "không có tài khoản" cũng tốn đúng một lần băm."""
    return bam_mat_khau(secrets.token_urlsafe(16))


_SAI_KHONG_TON_TAI: dict[str, list] = {}
"""Định danh không có tài khoản -> [số lần sai, khóa đến]. Giới hạn kích thước để không bị làm đầy bộ nhớ."""
_TOI_DA_DINH_DANH_THEO_DOI = 10_000


async def _dem_sai_khong_ton_tai(db: AsyncSession, dinh_danh: str, bay_gio) -> KetQuaKiemTraDangNhap:
    muc = _SAI_KHONG_TON_TAI.get(dinh_danh)
    if muc and muc[1] and muc[1] > bay_gio:
        return KetQuaKiemTraDangNhap(KetQuaDangNhap.KHOA_TAM, thu_lai_sau_giay=_giay_con_lai(muc[1], bay_gio))
    if len(_SAI_KHONG_TON_TAI) >= _TOI_DA_DINH_DANH_THEO_DOI and dinh_danh not in _SAI_KHONG_TON_TAI:
        for k in [k for k, v in _SAI_KHONG_TON_TAI.items() if not v[1] or v[1] <= bay_gio]:
            del _SAI_KHONG_TON_TAI[k]
        if len(_SAI_KHONG_TON_TAI) >= _TOI_DA_DINH_DANH_THEO_DOI:
            return KetQuaKiemTraDangNhap(KetQuaDangNhap.SAI_THONG_TIN)  # đầy: bỏ qua đếm, vẫn trả như sai thông tin
    muc = _SAI_KHONG_TON_TAI.setdefault(dinh_danh, [0, None])
    muc[0] += 1
    toi_da = int(await doc_cau_hinh(db, "so_lan_dang_nhap_sai_toi_da", SO_LAN_SAI_MAC_DINH))
    if muc[0] >= toi_da:
        phut = int(await doc_cau_hinh(db, "thoi_gian_khoa_dang_nhap_phut", THOI_GIAN_KHOA_PHUT_MAC_DINH))
        muc[0], muc[1] = 0, bay_gio + timedelta(minutes=phut)
        return KetQuaKiemTraDangNhap(KetQuaDangNhap.KHOA_TAM, thu_lai_sau_giay=phut * 60)
    return KetQuaKiemTraDangNhap(KetQuaDangNhap.SAI_THONG_TIN)


def _tim_khach_theo(dinh_danh: str):
    """Điều kiện tìm khách: có `@` là email, ngược lại là số điện thoại; không hợp lệ thì None."""
    dinh_danh = dinh_danh.strip()
    if "@" in dinh_danh:
        return func.lower(KhachHang.email) == dinh_danh.lower()
    try:
        return KhachHang.so_dien_thoai == chuan_hoa_sdt(dinh_danh)
    except ValueError:
        return None


async def kiem_tra_mat_khau_va_khoa(
    db: AsyncSession, tai_khoan: KhachHang | NhanVien, mat_khau: str
) -> KetQuaKiemTraDangNhap:
    """Kiểm tra mật khẩu của một tài khoản đã tìm thấy, cập nhật bộ đếm sai và khóa tạm.

    Dùng chung cho đăng nhập và đổi mật khẩu (mật khẩu cũ sai cũng bị đếm, để phiên bị đánh cắp không dò được mật khẩu).
    Tài khoản phải được khóa dòng (`FOR UPDATE`) bởi người gọi.
    """
    bay_gio = bay_gio_utc()
    if tai_khoan.khoa_den and tai_khoan.khoa_den > bay_gio:
        await kiem_tra_mat_khau_async(mat_khau, _ma_bam_gia())  # cùng thời gian với đường không bị khóa
        return KetQuaKiemTraDangNhap(
            KetQuaDangNhap.KHOA_TAM, thu_lai_sau_giay=_giay_con_lai(tai_khoan.khoa_den, bay_gio)
        )

    if not await kiem_tra_mat_khau_async(mat_khau, tai_khoan.mat_khau_hash):
        toi_da = int(await doc_cau_hinh(db, "so_lan_dang_nhap_sai_toi_da", SO_LAN_SAI_MAC_DINH))
        tai_khoan.so_lan_dang_nhap_sai += 1
        if tai_khoan.so_lan_dang_nhap_sai >= toi_da:
            phut = int(await doc_cau_hinh(db, "thoi_gian_khoa_dang_nhap_phut", THOI_GIAN_KHOA_PHUT_MAC_DINH))
            tai_khoan.khoa_den = bay_gio + timedelta(minutes=phut)
            tai_khoan.so_lan_dang_nhap_sai = 0
            return KetQuaKiemTraDangNhap(
                KetQuaDangNhap.KHOA_TAM, tai_khoan=tai_khoan, thu_lai_sau_giay=phut * 60, vua_bi_khoa=True
            )
        return KetQuaKiemTraDangNhap(KetQuaDangNhap.SAI_THONG_TIN, tai_khoan=tai_khoan)

    if tai_khoan.trang_thai != TrangThaiTaiKhoan.hoat_dong:
        return KetQuaKiemTraDangNhap(KetQuaDangNhap.TAI_KHOAN_BI_KHOA, tai_khoan=tai_khoan)
    tai_khoan.so_lan_dang_nhap_sai = 0
    tai_khoan.khoa_den = None
    return KetQuaKiemTraDangNhap(KetQuaDangNhap.OK, tai_khoan)


async def _tim_va_kiem_tra(db: AsyncSession, truy_van, mat_khau: str, dinh_danh: str) -> KetQuaKiemTraDangNhap:
    tai_khoan = None if truy_van is None else (await db.execute(truy_van.with_for_update())).scalar_one_or_none()
    if tai_khoan is None:
        await kiem_tra_mat_khau_async(mat_khau, _ma_bam_gia())  # cân bằng thời gian với đường có tài khoản
        return await _dem_sai_khong_ton_tai(db, dinh_danh.strip().lower(), bay_gio_utc())
    return await kiem_tra_mat_khau_va_khoa(db, tai_khoan, mat_khau)


async def kiem_tra_dang_nhap(db: AsyncSession, *, ten_dang_nhap: str, mat_khau: str) -> KetQuaKiemTraDangNhap:
    """Kiểm tra đăng nhập của khách (số điện thoại hoặc email). Không tạo phiên (route làm khi `OK`)."""
    dieu_kien = _tim_khach_theo(ten_dang_nhap)
    truy_van = None if dieu_kien is None else select(KhachHang).where(dieu_kien, KhachHang.deleted_at.is_(None))
    return await _tim_va_kiem_tra(db, truy_van, mat_khau, f"khach:{ten_dang_nhap}")


async def kiem_tra_dang_nhap_nhan_vien(db: AsyncSession, *, email: str, mat_khau: str) -> KetQuaKiemTraDangNhap:
    """Kiểm tra đăng nhập của nhân viên bằng email (không phân biệt hoa thường). Không tạo phiên."""
    email = email.strip().lower()
    truy_van = select(NhanVien).where(func.lower(NhanVien.email) == email, NhanVien.deleted_at.is_(None))
    return await _tim_va_kiem_tra(db, truy_van, mat_khau, f"nv:{email}")


def _giay_con_lai(den, bay_gio) -> int:
    return max(1, int((den - bay_gio).total_seconds()) + 1)

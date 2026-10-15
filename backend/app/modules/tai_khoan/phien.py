"""Phiên đăng nhập: access token ngắn hạn + refresh token xoay vòng (spec 06 mục 3).

- Refresh token là chuỗi ngẫu nhiên 256 bit; DB chỉ lưu SHA-256 (token đủ ngẫu nhiên nên không cần hash chậm).
- Mỗi lần làm mới, token cũ bị thu hồi và cấp token mới. Dùng lại token đã thu hồi nghĩa là token đã bị lộ: thu hồi
  TOÀN BỘ phiên của tài khoản. Tài khoản bị Admin khóa/xóa mềm thì cũng thu hồi toàn bộ; khóa tạm do đoán sai mật khẩu
  thì KHÔNG đụng tới phiên nào (QĐ-12). Việc thu hồi phải được commit dù request trả lỗi, nên route TRẢ VỀ lỗi
  (`core.loi.tra_loi`).
- Dùng chung cho khách (`khach_hang_id`) và nhân viên (`nhan_vien_id`, T1.3); `loai` quyết định `aud` của access token.
"""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from typing import Literal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bao_mat import tao_access_token
from app.core.config import settings
from app.core.thoi_gian import bay_gio_utc
from app.models.enums import TrangThaiTaiKhoan
from app.models.he_thong import NhanVien, PhienDangNhap
from app.models.khach_hang import KhachHang

LoaiPhien = Literal["khach", "noi_bo"]


def bam_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass(frozen=True)
class CapToken:
    access_token: str
    refresh_token: str
    het_han_giay: int


class KetQuaLamMoi(StrEnum):
    OK = "ok"
    KHONG_HOP_LE = "khong_hop_le"  # không có, không tồn tại, hoặc thuộc loại tài khoản khác
    HET_HAN = "het_han"
    DA_THU_HOI = "da_thu_hoi"  # dùng lại token đã thu hồi: đã thu hồi toàn bộ phiên
    KHOA_TAM = (
        "khoa_tam"  # khóa tạm do đoán sai mật khẩu: KHÔNG xoay vòng, KHÔNG thu hồi (token dùng tiếp khi hết khóa)
    )
    BI_KHOA = "bi_khoa"  # Admin khóa hoặc đã xóa mềm: đã thu hồi toàn bộ phiên


class TinhTrangTaiKhoan(StrEnum):
    CON_DUNG = "con_dung"
    KHOA_TAM = "khoa_tam"
    BI_KHOA = "bi_khoa"


@dataclass(frozen=True)
class KetQuaLamMoiPhien:
    ket_qua: KetQuaLamMoi
    cap_token: CapToken | None = None
    chu_id: int | None = None
    thu_lai_sau_giay: int | None = None


def _cot_chu(loai: LoaiPhien):
    return PhienDangNhap.khach_hang_id if loai == "khach" else PhienDangNhap.nhan_vien_id


def _cap(loai: LoaiPhien, chu_id: int) -> tuple[str, str]:
    return tao_access_token(chu_id, loai), secrets.token_urlsafe(32)


async def tao_phien(
    db: AsyncSession, *, loai: LoaiPhien, chu_id: int, thiet_bi: str | None = None, ip: str | None = None
) -> CapToken:
    """Tạo phiên mới (đăng nhập thành công): trả access token và refresh token (chỉ trả một lần, DB chỉ lưu hash)."""
    access_token, refresh_token = _cap(loai, chu_id)
    db.add(
        PhienDangNhap(
            **{("khach_hang_id" if loai == "khach" else "nhan_vien_id"): chu_id},
            refresh_token_hash=bam_refresh_token(refresh_token),
            thiet_bi=(thiet_bi or None) and thiet_bi[:255],
            ip=ip,
            het_han=bay_gio_utc() + timedelta(days=settings.REFRESH_NGAY),
        )
    )
    await db.flush()
    return CapToken(access_token, refresh_token, settings.JWT_ACCESS_PHUT * 60)


async def thu_hoi_tat_ca(db: AsyncSession, loai: LoaiPhien, chu_id: int) -> None:
    """Thu hồi mọi phiên còn hiệu lực của một tài khoản (đổi/đặt lại mật khẩu, khóa, phát hiện token bị lộ)."""
    await db.execute(
        update(PhienDangNhap)
        .where(_cot_chu(loai) == chu_id, PhienDangNhap.thu_hoi_luc.is_(None))
        .values(thu_hoi_luc=bay_gio_utc())
    )


async def thu_hoi_phien(db: AsyncSession, refresh_token: str) -> None:
    """Đăng xuất: thu hồi đúng phiên của refresh token này (không có hoặc không đúng thì không làm gì)."""
    await db.execute(
        update(PhienDangNhap)
        .where(
            PhienDangNhap.refresh_token_hash == bam_refresh_token(refresh_token), PhienDangNhap.thu_hoi_luc.is_(None)
        )
        .values(thu_hoi_luc=bay_gio_utc())
    )


async def _khoa_va_doc_tinh_trang(
    db: AsyncSession, loai: LoaiPhien, chu_id: int
) -> tuple[TinhTrangTaiKhoan, int | None]:
    """Khóa dòng tài khoản (`FOR UPDATE`) rồi đọc trạng thái. Trả (tình trạng, số giây còn khóa tạm)."""
    mo_hinh = KhachHang if loai == "khach" else NhanVien
    tai_khoan = (
        await db.execute(
            select(mo_hinh).where(mo_hinh.id == chu_id).with_for_update().execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if tai_khoan is None or tai_khoan.deleted_at is not None or tai_khoan.trang_thai != TrangThaiTaiKhoan.hoat_dong:
        return TinhTrangTaiKhoan.BI_KHOA, None
    bay_gio = bay_gio_utc()
    if tai_khoan.khoa_den is not None and tai_khoan.khoa_den > bay_gio:
        return TinhTrangTaiKhoan.KHOA_TAM, max(1, int((tai_khoan.khoa_den - bay_gio).total_seconds()) + 1)
    return TinhTrangTaiKhoan.CON_DUNG, None


async def lam_moi_phien(
    db: AsyncSession, *, refresh_token: str | None, loai: LoaiPhien, thiet_bi: str | None = None, ip: str | None = None
) -> KetQuaLamMoiPhien:
    """Xoay vòng refresh token.

    Thứ tự khóa: dòng tài khoản TRƯỚC, dòng phiên SAU, giống đăng nhập, đổi mật khẩu và đặt lại mật khẩu. Đảo thứ tự
    làm làm mới và đổi/đặt lại mật khẩu giữ khóa chéo nhau (deadlock). Khóa tài khoản cũng khiến "thu hồi tất cả"
    luôn thấy phiên vừa cấp. Hai request cùng một token chỉ một bên thắng, bên còn lại thấy token đã thu hồi.

    Trạng thái tài khoản được kiểm tra TRONG lần khóa này: Admin khóa hoặc xóa mềm thì thu hồi toàn bộ phiên
    (`BI_KHOA`); chỉ khóa tạm do đoán sai mật khẩu thì không đụng tới phiên nào (`KHOA_TAM`, QĐ-12), để người lạ gửi
    sai mật khẩu không đăng xuất được chủ tài khoản.
    """
    if not refresh_token:
        return KetQuaLamMoiPhien(KetQuaLamMoi.KHONG_HOP_LE)
    ma_bam = bam_refresh_token(refresh_token)
    # Đọc không khóa chỉ để biết chủ phiên; trạng thái thật được đọc lại sau khi khóa.
    phien_doc = (
        await db.execute(select(PhienDangNhap).where(PhienDangNhap.refresh_token_hash == ma_bam))
    ).scalar_one_or_none()
    chu_id = None if phien_doc is None else (phien_doc.khach_hang_id if loai == "khach" else phien_doc.nhan_vien_id)
    if chu_id is None:
        return KetQuaLamMoiPhien(KetQuaLamMoi.KHONG_HOP_LE)  # không có, hoặc thuộc loại tài khoản khác

    tinh_trang, thu_lai_sau_giay = await _khoa_va_doc_tinh_trang(db, loai, chu_id)
    phien = (
        await db.execute(
            select(PhienDangNhap)
            .where(PhienDangNhap.refresh_token_hash == ma_bam)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    if phien.thu_hoi_luc is not None:
        await thu_hoi_tat_ca(db, loai, chu_id)
        return KetQuaLamMoiPhien(KetQuaLamMoi.DA_THU_HOI, chu_id=chu_id)
    if phien.het_han <= bay_gio_utc():
        return KetQuaLamMoiPhien(KetQuaLamMoi.HET_HAN, chu_id=chu_id)
    if tinh_trang is TinhTrangTaiKhoan.BI_KHOA:
        await thu_hoi_tat_ca(db, loai, chu_id)
        return KetQuaLamMoiPhien(KetQuaLamMoi.BI_KHOA, chu_id=chu_id)
    if tinh_trang is TinhTrangTaiKhoan.KHOA_TAM:
        return KetQuaLamMoiPhien(KetQuaLamMoi.KHOA_TAM, chu_id=chu_id, thu_lai_sau_giay=thu_lai_sau_giay)
    phien.thu_hoi_luc = bay_gio_utc()
    cap = await tao_phien(db, loai=loai, chu_id=chu_id, thiet_bi=thiet_bi or phien.thiet_bi, ip=ip or phien.ip)
    return KetQuaLamMoiPhien(KetQuaLamMoi.OK, cap, chu_id)

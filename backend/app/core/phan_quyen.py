"""Xác thực và phân quyền cho route (spec 03 mục 8). Phần khách ở đây; `nhan_vien_hien_tai`, `yeu_cau_quyen` ở T1.3.

Trạng thái tài khoản được kiểm tra ở MỖI request (không tin access token đã ký), nên khóa tài khoản có hiệu lực ngay
chứ không chờ token hết hạn.
"""

import jwt
from fastapi import Request
from sqlalchemy import select

from app.core.bao_mat import giai_ma_access_token
from app.core.db import Db
from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc
from app.models.enums import TrangThaiTaiKhoan
from app.models.khach_hang import KhachHang

_TIEN_TO = "bearer "


def _lay_token(request: Request) -> str | None:
    gia_tri = request.headers.get("Authorization", "")
    if gia_tri[: len(_TIEN_TO)].lower() != _TIEN_TO:
        return None
    return gia_tri[len(_TIEN_TO) :].strip() or None


async def _khach_tu_token(token: str, db: Db) -> KhachHang:
    try:
        claim = giai_ma_access_token(token, "khach")
        khach_id = int(claim["sub"])
    except jwt.ExpiredSignatureError as loi:
        raise LoiNghiepVu("TOKEN_HET_HAN", "Phiên đăng nhập đã hết hạn") from loi
    except (jwt.InvalidTokenError, ValueError) as loi:  # chữ ký sai, sai aud, thiếu claim, sub không phải số
        raise LoiNghiepVu("CHUA_DANG_NHAP", "Bạn chưa đăng nhập") from loi
    khach = (
        await db.execute(select(KhachHang).where(KhachHang.id == khach_id, KhachHang.deleted_at.is_(None)))
    ).scalar_one_or_none()
    if khach is None:
        raise LoiNghiepVu("CHUA_DANG_NHAP", "Bạn chưa đăng nhập")
    if khach.trang_thai != TrangThaiTaiKhoan.hoat_dong or (khach.khoa_den and khach.khoa_den > bay_gio_utc()):
        raise LoiNghiepVu("TAI_KHOAN_BI_KHOA", "Tài khoản đang bị khóa")
    return khach


async def khach_hien_tai(request: Request, db: Db) -> KhachHang:
    """Bắt buộc đăng nhập: access token `aud = khach`, tài khoản `hoat_dong` và không bị `khoa_den`.

    Mọi API của khách lấy `khach_hang_id` từ đây, không bao giờ nhận id khách từ client (CLAUDE.md quy tắc 3).
    """
    token = _lay_token(request)
    if token is None:
        raise LoiNghiepVu("CHUA_DANG_NHAP", "Bạn chưa đăng nhập")
    return await _khach_tu_token(token, db)


async def khach_tuy_chon(request: Request, db: Db) -> KhachHang | None:
    """Cho route công khai cần biết khách nếu có. Không có token hoặc token vô nghĩa thì coi là khách vãng lai.

    Token hết hạn thì trả 401 `TOKEN_HET_HAN` để client làm mới rồi gọi lại; tài khoản bị khóa cũng coi như vãng lai.
    """
    token = _lay_token(request)
    if token is None:
        return None
    try:
        return await _khach_tu_token(token, db)
    except LoiNghiepVu as loi:
        if loi.ma_loi == "TOKEN_HET_HAN":
            raise
        return None

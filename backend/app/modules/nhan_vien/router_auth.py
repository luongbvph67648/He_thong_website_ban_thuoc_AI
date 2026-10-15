"""Xác thực nhân viên (NV01): `/api/v1/noi-bo/auth/*`.

`dang-nhap`, `lam-moi`, `dang-xuat` là route công khai duy nhất dưới `/noi-bo` (không có phiên thì không thể có quyền);
`doi-mat-khau` đòi `profile.self`. Ngoại lệ này được khai báo trong `tests/phan_quyen/registry.py`.
"""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import Db
from app.core.gioi_han import GioiHanCuaSoTruot, lay_bo_gioi_han_dang_nhap
from app.core.loi import tra_loi
from app.core.phan_quyen import yeu_cau_quyen
from app.core.thoi_gian import bay_gio_utc
from app.models.enums import TrangThaiTaiKhoan
from app.models.he_thong import NhanVien
from app.modules.nhan_vien import service
from app.modules.nhan_vien.schemas import (
    DangNhapNhanVienYeuCau,
    DoiMatKhauYeuCau,
    PhienNhanVienPhanHoi,
)
from app.modules.tai_khoan.cookie import TEN_COOKIE_REFRESH_NOI_BO, dat_cookie_refresh
from app.modules.tai_khoan.dang_nhap import KetQuaDangNhap
from app.modules.tai_khoan.phien_http import (
    dang_xuat_http,
    gioi_han_dang_nhap_theo_ip,
    ip_va_thiet_bi,
    lam_moi_http,
)
from app.modules.tai_khoan.schemas import CapTokenPhanHoi

router = APIRouter(prefix="/noi-bo/auth", tags=["Xác thực nội bộ"])

NhanVienDoiMatKhau = Annotated[NhanVien, Depends(yeu_cau_quyen("profile.self", ke_ca_chua_doi_mat_khau=True))]


async def _phan_hoi_phien(db: AsyncSession, response: Response, nhan_vien: NhanVien, cap) -> PhienNhanVienPhanHoi:
    dat_cookie_refresh(response, cap.refresh_token, "noi_bo")
    return PhienNhanVienPhanHoi(
        access_token=cap.access_token,
        het_han_giay=cap.het_han_giay,
        nhan_vien=await service.dung_ho_so(db, nhan_vien),
    )


@router.post("/dang-nhap", response_model=PhienNhanVienPhanHoi, summary="Đăng nhập nhân viên (NV01)")
async def dang_nhap(
    du_lieu: DangNhapNhanVienYeuCau,
    request: Request,
    response: Response,
    db: Db,
    bo_gioi_han_ip: GioiHanCuaSoTruot = Depends(lay_bo_gioi_han_dang_nhap),
):
    """Đăng nhập bằng email.

    Tài khoản còn `phai_doi_mat_khau` vẫn đăng nhập được nhưng chỉ dùng được `/noi-bo/toi` và đổi mật khẩu.
    """
    ip, thiet_bi = ip_va_thiet_bi(request)
    gioi_han_dang_nhap_theo_ip(bo_gioi_han_ip, "noi_bo", ip)
    kq = await service.dang_nhap_nhan_vien(db, email=du_lieu.email, mat_khau=du_lieu.mat_khau, ip=ip, thiet_bi=thiet_bi)
    # Trả về (không raise) các lỗi sau để bộ đếm sai/khoa_den và nhật ký được commit.
    if kq.ket_qua is KetQuaDangNhap.SAI_THONG_TIN:
        return tra_loi("SAI_THONG_TIN_DANG_NHAP", "Email hoặc mật khẩu không đúng")
    if kq.ket_qua is KetQuaDangNhap.KHOA_TAM:
        return tra_loi(
            "TAI_KHOAN_BI_KHOA",
            "Tài khoản bị khóa tạm do nhập sai nhiều lần, vui lòng thử lại sau",
            {"thu_lai_sau_giay": kq.thu_lai_sau_giay},
        )
    if kq.ket_qua is KetQuaDangNhap.TAI_KHOAN_BI_KHOA:
        return tra_loi("TAI_KHOAN_BI_KHOA", "Tài khoản đã bị khóa, vui lòng liên hệ quản trị viên")
    return await _phan_hoi_phien(db, response, kq.nhan_vien, kq.cap_token)


async def _nhan_vien_con_dung(db: AsyncSession, nhan_vien_id: int) -> bool:
    nhan_vien = (await db.execute(select(NhanVien).where(NhanVien.id == nhan_vien_id))).scalar_one()
    return not (
        nhan_vien.deleted_at is not None
        or nhan_vien.trang_thai != TrangThaiTaiKhoan.hoat_dong
        or (nhan_vien.khoa_den and nhan_vien.khoa_den > bay_gio_utc())
    )


@router.post("/lam-moi", response_model=CapTokenPhanHoi, summary="Làm mới access token nhân viên (NV01)")
async def lam_moi(
    request: Request,
    response: Response,
    db: Db,
    refresh_token: str | None = Cookie(default=None, alias=TEN_COOKIE_REFRESH_NOI_BO),
):
    """Xoay vòng refresh token. Dùng lại token đã thu hồi thì thu hồi toàn bộ phiên của nhân viên đó."""
    return await lam_moi_http(
        db, request, response, loai="noi_bo", refresh_token=refresh_token, con_dung=_nhan_vien_con_dung
    )


@router.post("/dang-xuat", status_code=204, summary="Đăng xuất nhân viên (NV01)")
async def dang_xuat(
    db: Db,
    refresh_token: str | None = Cookie(default=None, alias=TEN_COOKIE_REFRESH_NOI_BO),
) -> Response:
    """Thu hồi phiên hiện tại và xóa cookie. Gọi nhiều lần, hoặc không có cookie, vẫn trả 204."""
    return await dang_xuat_http(db, loai="noi_bo", refresh_token=refresh_token)


@router.post("/doi-mat-khau", response_model=PhienNhanVienPhanHoi, summary="Đổi mật khẩu của chính mình (NV01)")
async def doi_mat_khau(
    du_lieu: DoiMatKhauYeuCau, request: Request, response: Response, nhan_vien: NhanVienDoiMatKhau, db: Db
):
    """Đổi mật khẩu: mọi phiên cũ bị thu hồi, thiết bị này nhận phiên mới. Dùng được cả khi đang bị bắt đổi mật khẩu."""
    ip, thiet_bi = ip_va_thiet_bi(request)
    kq = await service.doi_mat_khau(
        db, nhan_vien.id, mat_khau_cu=du_lieu.mat_khau_cu, mat_khau_moi=du_lieu.mat_khau_moi, ip=ip, thiet_bi=thiet_bi
    )
    if kq.ket_qua is service.KetQuaDoiMatKhau.MAT_KHAU_CU_SAI:
        return tra_loi("MAT_KHAU_CU_SAI", "Mật khẩu hiện tại không đúng")
    if kq.ket_qua is service.KetQuaDoiMatKhau.KHOA_TAM:
        return tra_loi(
            "TAI_KHOAN_BI_KHOA",
            "Tài khoản bị khóa tạm do nhập sai nhiều lần, vui lòng thử lại sau",
            {"thu_lai_sau_giay": kq.thu_lai_sau_giay},
        )
    return await _phan_hoi_phien(db, response, kq.nhan_vien, kq.cap_token)

"""Phần HTTP dùng chung của phiên đăng nhập khách và nhân viên: giới hạn theo IP, làm mới, đăng xuất.

Gom một chỗ để logic nhạy cảm về bảo mật (xoay vòng, phát hiện dùng lại token, thu hồi khi tài khoản bị khóa) không bị
viết hai lần rồi lệch nhau. Mọi lỗi được TRẢ VỀ (`core.loi.tra_loi`), không raise, để thay đổi ở DB (thu hồi phiên, bộ
đếm) được commit.
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.gioi_han import GioiHanCuaSoTruot
from app.core.loi import LoiNghiepVu, tra_loi
from app.modules.tai_khoan import phien
from app.modules.tai_khoan.cookie import dat_cookie_refresh, xoa_cookie_refresh
from app.modules.tai_khoan.phien import LoaiPhien
from app.modules.tai_khoan.schemas import CapTokenPhanHoi

DANG_NHAP_TOI_DA_MOI_IP = 20
CUA_SO_DANG_NHAP_GIAY = 600


def dia_chi_ip(request: Request) -> str:
    return request.client.host if request.client else "khong-ro"


def ip_va_thiet_bi(request: Request) -> tuple[str, str | None]:
    return dia_chi_ip(request), request.headers.get("User-Agent")


def gioi_han_dang_nhap_theo_ip(bo_gioi_han: GioiHanCuaSoTruot, loai: LoaiPhien, ip: str) -> None:
    """Một IP thử đăng nhập quá `DANG_NHAP_TOI_DA_MOI_IP` lần trong cửa sổ thì bị 429 (tính cả lần đúng)."""
    cho = bo_gioi_han.thu(f"dang-nhap:{loai}:{ip}", DANG_NHAP_TOI_DA_MOI_IP, CUA_SO_DANG_NHAP_GIAY)
    if cho is not None:
        giay = int(cho) + 1
        raise LoiNghiepVu(
            "QUA_GIOI_HAN",
            "Bạn thử đăng nhập quá nhiều lần, vui lòng thử lại sau",
            chi_tiet={"thu_lai_sau_giay": giay},
            headers={"Retry-After": str(giay)},
        )


def _loi_phien(loai: LoaiPhien, ma_loi: str, thong_diep: str) -> JSONResponse:
    """Lỗi làm mới phiên: xóa luôn cookie refresh để trình duyệt không gửi lại token vô dụng."""
    phan_hoi = tra_loi(ma_loi, thong_diep)
    xoa_cookie_refresh(phan_hoi, loai)
    return phan_hoi


async def lam_moi_http(
    db: AsyncSession,
    request: Request,
    response: Response,
    *,
    loai: LoaiPhien,
    refresh_token: str | None,
) -> CapTokenPhanHoi | JSONResponse:
    """Xoay vòng refresh token. Dùng lại token đã thu hồi thì thu hồi toàn bộ phiên (nghi bị đánh cắp)."""
    ip, thiet_bi = ip_va_thiet_bi(request)
    kq = await phien.lam_moi_phien(db, refresh_token=refresh_token, loai=loai, thiet_bi=thiet_bi, ip=ip)
    if kq.ket_qua is phien.KetQuaLamMoi.KHONG_HOP_LE:
        return _loi_phien(loai, "CHUA_DANG_NHAP", "Bạn chưa đăng nhập")
    if kq.ket_qua is phien.KetQuaLamMoi.DA_THU_HOI:
        return _loi_phien(loai, "CHUA_DANG_NHAP", "Phiên đăng nhập không còn hiệu lực, vui lòng đăng nhập lại")
    if kq.ket_qua is phien.KetQuaLamMoi.HET_HAN:
        return _loi_phien(loai, "TOKEN_HET_HAN", "Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại")

    if kq.ket_qua is phien.KetQuaLamMoi.BI_KHOA:  # đã thu hồi toàn bộ phiên trong `lam_moi_phien`
        return _loi_phien(loai, "TAI_KHOAN_BI_KHOA", "Tài khoản đang bị khóa")
    if kq.ket_qua is phien.KetQuaLamMoi.KHOA_TAM:
        # Không xóa cookie: token còn nguyên giá trị, dùng tiếp được khi hết khóa.
        return tra_loi(
            "TAI_KHOAN_BI_KHOA",
            "Tài khoản đang bị khóa tạm, vui lòng thử lại sau",
            {"thu_lai_sau_giay": kq.thu_lai_sau_giay},
        )
    dat_cookie_refresh(response, kq.cap_token.refresh_token, loai)
    return CapTokenPhanHoi(access_token=kq.cap_token.access_token, het_han_giay=kq.cap_token.het_han_giay)


async def dang_xuat_http(db: AsyncSession, *, loai: LoaiPhien, refresh_token: str | None) -> Response:
    """Thu hồi phiên hiện tại và xóa cookie. Gọi nhiều lần, hoặc không có cookie, vẫn trả 204."""
    if refresh_token:
        await phien.thu_hoi_phien(db, refresh_token)
    phan_hoi = Response(status_code=204)
    xoa_cookie_refresh(phan_hoi, loai)
    return phan_hoi

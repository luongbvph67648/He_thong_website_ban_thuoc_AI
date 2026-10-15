"""Route công khai của khách: OTP, đăng ký (KVL09), đăng nhập, làm mới, đăng xuất, đặt lại mật khẩu (KVL10)."""

from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy import select

from app.core.bao_mat import bam_mat_khau_async
from app.core.db import Db
from app.core.gioi_han import GioiHanCuaSoTruot, lay_bo_gioi_han_dang_nhap, lay_bo_gioi_han_otp
from app.core.loi import LoiNghiepVu, tra_loi
from app.core.thoi_gian import bay_gio_utc
from app.models.enums import TrangThaiTaiKhoan
from app.models.khach_hang import KhachHang
from app.modules.tai_khoan import dang_ky, dang_nhap, otp, phien
from app.modules.tai_khoan.cookie import TEN_COOKIE_REFRESH_KHACH, dat_cookie_refresh, xoa_cookie_refresh
from app.modules.tai_khoan.schemas import (
    CapTokenPhanHoi,
    DangKyYeuCau,
    DangNhapPhanHoi,
    DangNhapYeuCau,
    DatLaiMatKhauPhanHoi,
    DatLaiMatKhauYeuCau,
    KhachHangDoc,
    OtpPhanHoi,
    OtpYeuCau,
)
from app.tich_hop.tin_nhan import KenhTinNhan, lay_kenh_tin_nhan

DANG_NHAP_TOI_DA_MOI_IP = 20
CUA_SO_DANG_NHAP_GIAY = 600

router = APIRouter(prefix="/auth", tags=["Xác thực khách"])


def _dia_chi_ip(request: Request) -> str:
    return request.client.host if request.client else "khong-ro"


@router.post("/otp", response_model=OtpPhanHoi, summary="Gửi mã OTP đăng ký hoặc lấy lại mật khẩu (KVL09, KVL10)")
async def gui_ma_otp(
    du_lieu: OtpYeuCau,
    request: Request,
    db: Db,
    kenh: KenhTinNhan = Depends(lay_kenh_tin_nhan),
    bo_gioi_han_ip: GioiHanCuaSoTruot = Depends(lay_bo_gioi_han_otp),
) -> OtpPhanHoi:
    """Phản hồi luôn giống nhau dù số đã đăng ký hay chưa (chống dò tài khoản)."""
    await otp.gui_otp(
        db,
        kenh,
        so_dien_thoai=du_lieu.so_dien_thoai,
        muc_dich=du_lieu.muc_dich,
        ip=_dia_chi_ip(request),
        bo_gioi_han_ip=bo_gioi_han_ip,
        kenh_gui=du_lieu.kenh,
    )
    return OtpPhanHoi(da_gui=True, het_han_giay=otp.HIEU_LUC_PHUT * 60)


@router.post(
    "/dang-ky",
    status_code=201,
    response_model=KhachHangDoc,
    summary="Đăng ký tài khoản khách bằng SĐT và OTP (KVL09)",
)
async def dang_ky_khach(du_lieu: DangKyYeuCau, db: Db):
    ket_qua = await otp.kiem_tra_otp(db, dich_den=du_lieu.so_dien_thoai, muc_dich="dang_ky", ma=du_lieu.otp)
    loi = otp.loi_otp(ket_qua)
    if loi is not None:
        return loi  # trả về (không raise) để bộ đếm lần thử sai được commit
    return await dang_ky.tao_khach(
        db,
        so_dien_thoai=du_lieu.so_dien_thoai,
        mat_khau=du_lieu.mat_khau,
        ho_ten=du_lieu.ho_ten,
        email=du_lieu.email,
    )


def _ip_va_thiet_bi(request: Request) -> tuple[str, str | None]:
    return _dia_chi_ip(request), request.headers.get("User-Agent")


@router.post("/dang-nhap", response_model=DangNhapPhanHoi, summary="Đăng nhập khách (KVL10)")
async def dang_nhap_khach(
    du_lieu: DangNhapYeuCau,
    request: Request,
    response: Response,
    db: Db,
    bo_gioi_han_ip: GioiHanCuaSoTruot = Depends(lay_bo_gioi_han_dang_nhap),
):
    ip, thiet_bi = _ip_va_thiet_bi(request)
    cho = bo_gioi_han_ip.thu(f"dang-nhap:{ip}", DANG_NHAP_TOI_DA_MOI_IP, CUA_SO_DANG_NHAP_GIAY)
    if cho is not None:
        giay = int(cho) + 1
        raise LoiNghiepVu(
            "QUA_GIOI_HAN",
            "Bạn thử đăng nhập quá nhiều lần, vui lòng thử lại sau",
            chi_tiet={"thu_lai_sau_giay": giay},
            headers={"Retry-After": str(giay)},
        )
    kq = await dang_nhap.kiem_tra_dang_nhap(db, ten_dang_nhap=du_lieu.ten_dang_nhap, mat_khau=du_lieu.mat_khau)
    # Trả về (không raise) các lỗi sau để bộ đếm sai/khoa_den được commit.
    if kq.ket_qua is dang_nhap.KetQuaDangNhap.SAI_THONG_TIN:
        return tra_loi("SAI_THONG_TIN_DANG_NHAP", "Số điện thoại/email hoặc mật khẩu không đúng")
    if kq.ket_qua is dang_nhap.KetQuaDangNhap.KHOA_TAM:
        return tra_loi(
            "TAI_KHOAN_BI_KHOA",
            "Tài khoản bị khóa tạm do nhập sai nhiều lần, vui lòng thử lại sau",
            {"thu_lai_sau_giay": kq.thu_lai_sau_giay},
        )
    if kq.ket_qua is dang_nhap.KetQuaDangNhap.TAI_KHOAN_BI_KHOA:
        return tra_loi("TAI_KHOAN_BI_KHOA", "Tài khoản đã bị khóa, vui lòng liên hệ nhà thuốc")
    cap = await phien.tao_phien(db, loai="khach", chu_id=kq.khach.id, thiet_bi=thiet_bi, ip=ip)
    dat_cookie_refresh(response, cap.refresh_token)
    return DangNhapPhanHoi(
        access_token=cap.access_token, het_han_giay=cap.het_han_giay, khach_hang=KhachHangDoc.model_validate(kq.khach)
    )


def _loi_phien(ma_loi: str, thong_diep: str):
    """Lỗi làm mới phiên: xóa luôn cookie refresh để trình duyệt không gửi lại token vô dụng."""
    phan_hoi = tra_loi(ma_loi, thong_diep)
    xoa_cookie_refresh(phan_hoi)
    return phan_hoi


@router.post("/lam-moi", response_model=CapTokenPhanHoi, summary="Làm mới access token bằng refresh token (KVL10)")
async def lam_moi(
    request: Request,
    response: Response,
    db: Db,
    refresh_token: str | None = Cookie(default=None, alias=TEN_COOKIE_REFRESH_KHACH),
):
    """Xoay vòng refresh token. Dùng lại token đã thu hồi thì thu hồi toàn bộ phiên (nghi bị đánh cắp)."""
    ip, thiet_bi = _ip_va_thiet_bi(request)
    kq = await phien.lam_moi_phien(db, refresh_token=refresh_token, loai="khach", thiet_bi=thiet_bi, ip=ip)
    if kq.ket_qua is phien.KetQuaLamMoi.KHONG_HOP_LE:
        return _loi_phien("CHUA_DANG_NHAP", "Bạn chưa đăng nhập")
    if kq.ket_qua is phien.KetQuaLamMoi.DA_THU_HOI:
        return _loi_phien("CHUA_DANG_NHAP", "Phiên đăng nhập không còn hiệu lực, vui lòng đăng nhập lại")
    if kq.ket_qua is phien.KetQuaLamMoi.HET_HAN:
        return _loi_phien("TOKEN_HET_HAN", "Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại")

    khach = (await db.execute(select(KhachHang).where(KhachHang.id == kq.chu_id))).scalar_one()
    if (
        khach.deleted_at is not None
        or khach.trang_thai != TrangThaiTaiKhoan.hoat_dong
        or (khach.khoa_den and khach.khoa_den > bay_gio_utc())
    ):
        await phien.thu_hoi_tat_ca(db, "khach", khach.id)  # kể cả phiên vừa cấp
        return _loi_phien("TAI_KHOAN_BI_KHOA", "Tài khoản đang bị khóa")
    dat_cookie_refresh(response, kq.cap_token.refresh_token)
    return CapTokenPhanHoi(access_token=kq.cap_token.access_token, het_han_giay=kq.cap_token.het_han_giay)


@router.post("/dang-xuat", status_code=204, summary="Đăng xuất khách (KVL10)")
async def dang_xuat(
    db: Db,
    refresh_token: str | None = Cookie(default=None, alias=TEN_COOKIE_REFRESH_KHACH),
) -> Response:
    """Thu hồi phiên hiện tại và xóa cookie. Gọi nhiều lần, hoặc không có cookie, vẫn trả 204."""
    if refresh_token:
        await phien.thu_hoi_phien(db, refresh_token)
    phan_hoi = Response(status_code=204)
    xoa_cookie_refresh(phan_hoi)
    return phan_hoi


@router.post(
    "/dat-lai-mat-khau",
    response_model=DatLaiMatKhauPhanHoi,
    summary="Đặt lại mật khẩu bằng OTP (KVL10)",
)
async def dat_lai_mat_khau(du_lieu: DatLaiMatKhauYeuCau, db: Db):
    """Đặt lại mật khẩu: đúng OTP `quen_mat_khau` thì đổi mật khẩu, mở khóa tạm và thu hồi mọi phiên đăng nhập."""
    ket_qua = await otp.kiem_tra_otp(db, dich_den=du_lieu.so_dien_thoai, muc_dich="quen_mat_khau", ma=du_lieu.otp)
    loi = otp.loi_otp(ket_qua)
    if loi is not None:
        return loi  # trả về (không raise) để bộ đếm lần thử sai được commit
    khach = (
        await db.execute(
            select(KhachHang)
            .where(KhachHang.so_dien_thoai == du_lieu.so_dien_thoai, KhachHang.deleted_at.is_(None))
            .with_for_update()
        )
    ).scalar_one_or_none()
    if khach is None:  # OTP khớp nhưng tài khoản vừa bị xóa: coi như mã không dùng được
        return tra_loi("OTP_SAI", "Mã OTP không đúng", {"so_lan_con_lai": 0})
    khach.mat_khau_hash = await bam_mat_khau_async(du_lieu.mat_khau_moi)
    khach.so_lan_dang_nhap_sai = 0
    khach.khoa_den = None
    await phien.thu_hoi_tat_ca(db, "khach", khach.id)
    return DatLaiMatKhauPhanHoi(da_dat_lai=True)

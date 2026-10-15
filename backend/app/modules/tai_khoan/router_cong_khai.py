"""Route công khai của khách vãng lai: OTP và đăng ký (KVL09). Đăng nhập, làm mới, quên mật khẩu ở T1.2."""

from fastapi import APIRouter, Depends, Request

from app.core.db import Db
from app.core.gioi_han import GioiHanCuaSoTruot, lay_bo_gioi_han_otp
from app.modules.tai_khoan import dang_ky, otp
from app.modules.tai_khoan.schemas import DangKyYeuCau, KhachHangDoc, OtpPhanHoi, OtpYeuCau
from app.tich_hop.tin_nhan import KenhTinNhan, lay_kenh_tin_nhan

router = APIRouter(prefix="/auth", tags=["Xác thực khách"])


def _dia_chi_ip(request: Request) -> str:
    return request.client.host if request.client else "khong-ro"


@router.post("/otp", response_model=OtpPhanHoi, summary="Gửi mã OTP đăng ký (KVL09)")
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

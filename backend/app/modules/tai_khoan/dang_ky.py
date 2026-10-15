"""Đăng ký khách hàng (KVL09). Việc xác thực OTP do route gọi `otp.kiem_tra_otp` trước."""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bao_mat import bam_mat_khau_async
from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc
from app.models.khach_hang import KhachHang


def _trung(truong: str) -> LoiNghiepVu:
    return LoiNghiepVu(
        "TRUNG_DU_LIEU", "Thông tin này đã được dùng cho một tài khoản khác", chi_tiet={"truong": truong}
    )


async def tao_khach(
    db: AsyncSession, *, so_dien_thoai: str, mat_khau: str, ho_ten: str, email: str | None
) -> KhachHang:
    """Tạo khách hàng với mật khẩu Argon2id và thời điểm đồng ý chính sách. Trùng SĐT hoặc email thì `TRUNG_DU_LIEU`."""
    if (await db.execute(select(KhachHang.id).where(KhachHang.so_dien_thoai == so_dien_thoai))).first():
        raise _trung("so_dien_thoai")
    if email and (await db.execute(select(KhachHang.id).where(func.lower(KhachHang.email) == email))).first():
        raise _trung("email")
    khach = KhachHang(
        ho_ten=ho_ten,
        so_dien_thoai=so_dien_thoai,
        email=email,
        mat_khau_hash=await bam_mat_khau_async(mat_khau),
        dong_y_chinh_sach_luc=bay_gio_utc(),
    )
    db.add(khach)
    try:
        async with db.begin_nested():  # savepoint: vi phạm unique do đua nhau không làm hỏng cả transaction
            await db.flush()
    except IntegrityError as loi:
        raise _trung("so_dien_thoai hoặc email") from loi
    return khach

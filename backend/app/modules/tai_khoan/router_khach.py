"""API của khách thành viên đã đăng nhập (`/api/v1/toi/*`). Mọi dữ liệu lọc theo khách lấy từ token (quy tắc 3)."""

from fastapi import APIRouter, Depends

from app.core.phan_quyen import khach_hien_tai
from app.models.khach_hang import KhachHang
from app.modules.tai_khoan.schemas import KhachHangDoc

router = APIRouter(prefix="/toi", tags=["Khách thành viên"])


@router.get("", response_model=KhachHangDoc, summary="Hồ sơ của tôi (KTV01)")
async def ho_so_cua_toi(khach: KhachHang = Depends(khach_hien_tai)) -> KhachHang:
    return khach

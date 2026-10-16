"""Hồ sơ sức khỏe của tôi (`/api/v1/toi/ho-so-suc-khoe`, KTV11). `khach_hang_id` lấy từ token."""

from fastapi import APIRouter, Depends, Response

from app.core.db import Db
from app.core.phan_quyen import khach_hien_tai
from app.core.tham_so import tu_khoa_tim
from app.models.khach_hang import KhachHang
from app.modules.suc_khoe import dich_vu
from app.modules.suc_khoe.schemas import HoatChatChon, HoSoRa, HoSoVao

router = APIRouter(tags=["Hồ sơ sức khỏe"])
Khach = Depends(khach_hien_tai)


@router.get("/toi/ho-so-suc-khoe", response_model=HoSoRa, summary="Xem hồ sơ sức khỏe của tôi (KTV11)")
async def xem(db: Db, khach: KhachHang = Khach):
    return await dich_vu.xem(db, khach)


@router.put("/toi/ho-so-suc-khoe", response_model=HoSoRa, summary="Lưu hồ sơ sức khỏe, cần đồng ý (KTV11)")
async def luu(vao: HoSoVao, db: Db, khach: KhachHang = Khach):
    return await dich_vu.luu(db, khach, vao)


@router.delete("/toi/ho-so-suc-khoe", status_code=204, summary="Xóa hồ sơ và thu hồi đồng ý (KTV11)")
async def xoa(db: Db, khach: KhachHang = Khach):
    await dich_vu.xoa(db, khach)
    return Response(status_code=204)


@router.get(
    "/toi/ho-so-suc-khoe/hoat-chat",
    response_model=list[HoatChatChon],
    summary="Tìm hoạt chất để khai dị ứng (KTV11)",
)
async def tim_hoat_chat(
    db: Db, q: tu_khoa_tim("Tên hoạt chất (không dấu cũng được)", 100) = None, khach: KhachHang = Khach
):
    return await dich_vu.tim_hoat_chat(db, q)

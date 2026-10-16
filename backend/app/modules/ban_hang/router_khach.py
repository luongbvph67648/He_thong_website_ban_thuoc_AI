"""Đơn hàng của khách thành viên: `/api/v1/toi/don-hang` (KTV02)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header

from app.core import idempotency
from app.core.db import Db
from app.core.phan_quyen import khach_hien_tai
from app.models.khach_hang import KhachHang
from app.modules.ban_hang import dat_hang
from app.modules.ban_hang.schemas import DatHangVao, DonHangRa, XemTruocRa

router = APIRouter(tags=["Đơn hàng"])
Khach = Annotated[KhachHang, Depends(khach_hien_tai)]


@router.post("/toi/don-hang", response_model=DonHangRa, status_code=201, summary="Đặt hàng từ giỏ (KTV02)")
async def tao(
    vao: DatHangVao,
    db: Db,
    khach: Khach,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    return await dat_hang.dat_hang(db, khach, vao, idempotency.doc_khoa(idempotency_key))


@router.post("/toi/don-hang/xem-truoc", response_model=XemTruocRa, summary="Tính thử đơn: phí ship, giảm giá (KTV02)")
async def xem_truoc(vao: DatHangVao, db: Db, khach: Khach):
    return await dat_hang.xem_truoc(db, khach, vao)


@router.get("/toi/don-hang/{ma_don}", response_model=DonHangRa, summary="Chi tiết đơn của tôi (KTV02)")
async def chi_tiet(ma_don: str, db: Db, khach: Khach):
    return await dat_hang.don_cua_khach(db, khach, ma_don)

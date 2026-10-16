"""Khách xác nhận đơn từ đơn thuốc: thành viên `/toi/don-hang/{ma}/...`, vãng lai `/xac-nhan-don/{token}` (KTV07)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request

from app.core import idempotency
from app.core.db import Db
from app.core.phan_quyen import khach_hien_tai
from app.models.khach_hang import KhachHang
from app.modules.ban_hang.schemas import DonHangRa
from app.modules.don_thuoc import xac_nhan
from app.modules.don_thuoc.schemas_xac_nhan import DonXacNhanRa, XacNhanVao
from app.modules.thanh_toan.router_khach import ThanhToanRa

router = APIRouter(tags=["Xác nhận đơn từ đơn thuốc"])
Khach = Annotated[KhachHang, Depends(khach_hien_tai)]
Khoa = Annotated[str | None, Header(alias="Idempotency-Key")]


def _ip(request: Request) -> str:
    return request.client.host if request.client else "127.0.0.1"


# --- Thành viên ---


@router.get("/toi/don-hang/{ma_don}/xac-nhan", response_model=DonXacNhanRa, summary="Đơn chờ tôi xác nhận (KTV07)")
async def xem(ma_don: str, db: Db, khach: Khach):
    return await xac_nhan.xem(db, await xac_nhan.don_cua_khach(db, khach, ma_don))


@router.post(
    "/toi/don-hang/{ma_don}/xac-nhan", response_model=DonXacNhanRa, summary="Xác nhận đơn từ đơn thuốc (KTV07)"
)
async def xac_nhan_don(ma_don: str, vao: XacNhanVao, db: Db, khach: Khach):
    return await xac_nhan.xac_nhan(db, await xac_nhan.don_cua_khach(db, khach, ma_don), khach, vao)


@router.post("/toi/don-hang/{ma_don}/tu-choi", response_model=DonHangRa, summary="Từ chối đơn từ đơn thuốc (KTV07)")
async def tu_choi(ma_don: str, db: Db, khach: Khach):
    return await xac_nhan.tu_choi(db, await xac_nhan.don_cua_khach(db, khach, ma_don), khach)


# --- Khách vãng lai qua link mã truy cập ---


@router.get("/xac-nhan-don/{token}", response_model=DonXacNhanRa, summary="Xem đơn qua link mã truy cập (KTV07)")
async def xem_token(token: str, db: Db):
    return await xac_nhan.xem(db, await xac_nhan.don_theo_token(db, token))


@router.post("/xac-nhan-don/{token}/xac-nhan", response_model=DonXacNhanRa, summary="Xác nhận qua link (KTV07)")
async def xac_nhan_token(token: str, vao: XacNhanVao, db: Db):
    return await xac_nhan.xac_nhan(db, await xac_nhan.don_theo_token(db, token), None, vao)


@router.post("/xac-nhan-don/{token}/tu-choi", response_model=DonHangRa, summary="Từ chối qua link (KTV07)")
async def tu_choi_token(token: str, db: Db):
    return await xac_nhan.tu_choi(db, await xac_nhan.don_theo_token(db, token), None)


@router.post(
    "/xac-nhan-don/{token}/thanh-toan", response_model=ThanhToanRa, summary="Thanh toán online qua link (KTV03)"
)
async def thanh_toan_token(token: str, request: Request, db: Db, idempotency_key: Khoa = None):
    don = await xac_nhan.don_theo_token(db, token)
    return await xac_nhan.thanh_toan_online(db, don, None, idempotency.doc_khoa(idempotency_key), _ip(request))

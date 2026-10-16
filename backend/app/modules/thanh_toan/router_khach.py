"""Thanh toán online của khách: `POST /api/v1/toi/don-hang/{ma_don}/thanh-toan` (KTV03)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel

from app.core import idempotency
from app.core.db import Db
from app.core.phan_quyen import khach_hien_tai
from app.models.khach_hang import KhachHang
from app.modules.thanh_toan import dich_vu

router = APIRouter(tags=["Thanh toán online"])
Khach = Annotated[KhachHang, Depends(khach_hien_tai)]


class ThanhToanRa(BaseModel):
    url_thanh_toan: str
    han_thanh_toan: str | None


@router.post(
    "/toi/don-hang/{ma_don}/thanh-toan", response_model=ThanhToanRa, summary="Tạo giao dịch thanh toán online (KTV03)"
)
async def tao(
    ma_don: str,
    request: Request,
    db: Db,
    khach: Khach,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    ip = request.client.host if request.client else "127.0.0.1"
    return await dich_vu.tao_thanh_toan(db, khach.id, ma_don, idempotency.doc_khoa(idempotency_key), ip)

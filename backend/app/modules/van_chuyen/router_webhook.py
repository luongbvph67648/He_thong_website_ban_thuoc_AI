"""Webhook vận chuyển: `/api/v1/webhook/ghn` (HT05, token của GHN) và `/webhook/gia-van-chuyen` (chỉ khi chế độ giả)."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.db import Db
from app.modules.van_chuyen.dich_vu import xu_ly_su_kien
from app.tich_hop.van_chuyen import WebhookKhongHopLe
from app.tich_hop.van_chuyen.ghn import VanChuyenGhn
from app.tich_hop.van_chuyen.gia import VanChuyenGia

router = APIRouter(prefix="/webhook", tags=["Webhook vận chuyển"])
router_gia = APIRouter(prefix="/webhook", tags=["Webhook vận chuyển"])


async def _doc_than(request: Request) -> dict:
    try:
        than = await request.json()
    except ValueError:
        raise WebhookKhongHopLe("Thân không phải JSON") from None
    if not isinstance(than, dict):
        raise WebhookKhongHopLe("Thân phải là đối tượng JSON")
    return than


def _tu_choi(ly_do: str, status: int) -> JSONResponse:
    return JSONResponse({"ma_loi": "WEBHOOK_KHONG_HOP_LE", "thong_diep": ly_do}, status_code=status)


@router.post("/ghn", summary="Webhook GHN (HT05)")
async def ghn(request: Request, db: Db):
    try:
        su_kien = VanChuyenGhn().xac_thuc_webhook(dict(request.headers), await _doc_than(request))
    except WebhookKhongHopLe as e:
        return _tu_choi(str(e), 401)
    await xu_ly_su_kien(db, su_kien)  # mã không có cũng trả 200 để GHN không gọi lại mãi
    return {"trang_thai": "ok"}


class SuKienGiaVao(BaseModel):
    ma_van_don: str = Field(min_length=1, max_length=50)
    trang_thai_doi_tac: str = Field(min_length=1, max_length=50)


@router_gia.post("/gia-van-chuyen", summary="Sự kiện vận chuyển giả (chỉ khi VAN_CHUYEN_CHE_DO=gia)")
async def gia(vao: SuKienGiaVao, db: Db):
    su_kien = VanChuyenGia().xac_thuc_webhook({}, vao.model_dump())
    await xu_ly_su_kien(db, su_kien)
    return {"trang_thai": "ok"}

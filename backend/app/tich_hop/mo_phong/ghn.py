"""Mô phỏng GHN API v2: tính phí, tạo vận đơn, hủy vận đơn và đẩy webhook trạng thái.

Đúng đường dẫn `/shiip/public-api/v2/...`, tiêu đề `Token` + `ShopId`, khuôn phản hồi `{code, message, data}`; hủy
đơn chỉ được khi vận đơn chưa được lấy hàng (`ready_to_pick`, `picking`). Webhook là POST JSON có tiêu đề `Token`.
Tên trường và quy tắc kiểm tra cần đối chiếu lại với tài liệu GHN hiện hành khi chạy sandbox thật (QĐ-56).
"""

import re
import secrets
from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.core.db import Db
from app.core.thoi_gian import bay_gio_utc
from app.models.ban_hang import DonHang, VanDon
from app.tich_hop import cau_hinh
from app.tich_hop.mo_phong.chung import client_ung_dung_chinh

router = APIRouter(prefix="/ghn", tags=["Mô phỏng GHN"])

SDT_VN = re.compile(r"^(0|\+84)\d{9}$")
GHI_CHU_BAT_BUOC = {"KHONGCHOXEMHANG", "CHOXEMHANGKHONGTHU", "CHOXEMHANG"}
CHO_PHEP_HUY = {None, "", "ready_to_pick", "picking"}
COD_TOI_DA = 50_000_000
KHOI_LUONG_TOI_DA_GRAM = 50_000


def _loi(ma: int, thong_diep: str, http: int = 400) -> JSONResponse:
    return JSONResponse(
        {"code": ma, "code_message": thong_diep.upper().replace(" ", "_")[:40], "message": thong_diep}, http
    )


def _phi(khoi_luong_gram: int) -> int:
    so_kg = max(1, -(-khoi_luong_gram // 1000))
    return min(25_000 + 5_000 * (so_kg - 1), 100_000)


async def xac_thuc(
    token: Annotated[str | None, Header()] = None, shopid: Annotated[str | None, Header()] = None
) -> None:
    """GHN nhận `Token` (khóa API) và `ShopId` ở tiêu đề; sai thì HTTP 401."""
    if token != cau_hinh.ghn_token() or not shopid:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail={"code": 401, "message": "Token is invalid or ShopId is missing"})


Xac = Annotated[None, Depends(xac_thuc)]


@router.post("/shiip/public-api/v2/shipping-order/fee", summary="Tính phí vận chuyển GHN (mô phỏng)")
async def tinh_phi(yeu_cau: dict[str, Any], _: Xac):
    khoi_luong = yeu_cau.get("weight")
    if not yeu_cau.get("to_ward_code") or not isinstance(khoi_luong, int) or khoi_luong <= 0:
        return _loi(400, "to_ward_code and weight are required")
    phi = _phi(khoi_luong)
    phu = dict.fromkeys(("insurance_fee", "pick_station_fee", "coupon_value", "r2s_fee", "cod_fee"), 0)
    return {"code": 200, "message": "Success", "data": {"total": phi, "service_fee": phi, **phu}}


@router.post("/shiip/public-api/v2/shipping-order/create", summary="Tạo vận đơn GHN (mô phỏng)")
async def tao_van_don(yeu_cau: dict[str, Any], _: Xac):
    if yeu_cau.get("payment_type_id") not in (1, 2):
        return _loi(400, "payment_type_id must be 1 or 2")
    if yeu_cau.get("required_note") not in GHI_CHU_BAT_BUOC:
        return _loi(400, "required_note is invalid")
    thieu = [t for t in ("to_name", "to_phone", "to_address", "to_ward_code", "service_type_id") if not yeu_cau.get(t)]
    if thieu:
        return _loi(400, f"Missing field(s): {', '.join(thieu)}")
    if not SDT_VN.match(str(yeu_cau["to_phone"])):
        return _loi(400, "to_phone is invalid")
    khoi_luong, cod = yeu_cau.get("weight"), yeu_cau.get("cod_amount", 0)
    if not isinstance(khoi_luong, int) or not 0 < khoi_luong <= KHOI_LUONG_TOI_DA_GRAM:
        return _loi(400, "weight must be between 1 and 50000 grams")
    if not isinstance(cod, int) or not 0 <= cod <= COD_TOI_DA:
        return _loi(400, "cod_amount must be between 0 and 50000000")
    cac_mon = yeu_cau.get("items")
    if not isinstance(cac_mon, list) or not cac_mon or any(not m.get("name") or not m.get("quantity") for m in cac_mon):
        return _loi(400, "items must be a non-empty list of {name, quantity}")
    phi = _phi(khoi_luong)
    ma = "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(8))
    han = (bay_gio_utc() + timedelta(days=3)).isoformat()
    return {
        "code": 200,
        "message": "Success",
        "data": {
            "order_code": ma,
            "sort_code": f"{ma[:3]}-{ma[3:5]}-01",
            "trans_type": "truck",
            "total_fee": phi,
            "expected_delivery_time": han,
            "fee": {
                "main_service": phi,
                "insurance": 0,
                "cod_fee": 0,
                "station_do": 0,
                "station_pu": 0,
                "return": 0,
                "r2s": 0,
            },
        },
    }


class HuyVao(BaseModel):
    order_codes: list[str]


@router.post("/shiip/public-api/v2/switch-status/cancel", summary="Hủy vận đơn GHN (mô phỏng)")
async def huy_van_don(vao: HuyVao, _: Xac, db: Db):
    if not vao.order_codes:
        return _loi(400, "order_codes is required")
    ket_qua = []
    for ma in vao.order_codes:
        van_don = (await db.execute(select(VanDon).where(VanDon.ma_van_don == ma))).scalar_one_or_none()
        if van_don is None:
            ket_qua.append({"order_code": ma, "result": False, "message": "Order Not Found"})
        elif van_don.trang_thai_doi_tac == "cancel":
            ket_qua.append({"order_code": ma, "result": False, "message": "Order is already cancelled"})
        elif van_don.trang_thai_doi_tac in CHO_PHEP_HUY:
            ket_qua.append({"order_code": ma, "result": True, "message": "Success"})
        else:
            ket_qua.append({"order_code": ma, "result": False, "message": "Order status does not allow cancel"})
    return {"code": 200, "message": "Success", "data": ket_qua}


class SuKienVao(BaseModel):
    order_code: str
    status: str
    """Trạng thái GHN: `picked`, `delivering`, `delivered`, `delivery_fail`, `waiting_to_return`, `returned`..."""


@router.post("/phat-su-kien", summary="Phát webhook trạng thái GHN tới cửa hàng (công cụ demo)")
async def phat_su_kien(vao: SuKienVao, db: Db):
    """Giả lập GHN đổi trạng thái vận đơn: gửi webhook đúng khuôn GHN, kèm `Token`, tới `/webhook/ghn` của cửa hàng."""
    ma_don = await db.scalar(
        select(DonHang.ma_don).join(VanDon, VanDon.don_hang_id == DonHang.id).where(VanDon.ma_van_don == vao.order_code)
    )
    than = {
        "Type": "switch_status",
        "OrderCode": vao.order_code,
        "ClientOrderCode": ma_don or "",
        "Status": vao.status,
        "Description": f"Trạng thái: {vao.status}",
        "Time": bay_gio_utc().isoformat(),
        "ShopID": cau_hinh.ghn_shop_id(),
        "Reason": "",
        "ReasonCode": "",
        "Warehouse": "",
    }
    async with client_ung_dung_chinh() as client:
        r = await client.post("/api/v1/webhook/ghn", json=than, headers={"Token": cau_hinh.ghn_webhook_token()})
    return JSONResponse(
        {"ma_phan_hoi": r.status_code, "than": than}, status_code=200 if r.is_success else r.status_code
    )

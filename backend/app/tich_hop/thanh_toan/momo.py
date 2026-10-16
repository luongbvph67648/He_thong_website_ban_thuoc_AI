"""MoMo (spec 08 mục 3). Chữ ký HMAC-SHA256 theo đúng thứ tự trường của từng API. Hoàn tiền ở T6.3."""

import hashlib
import hmac
import uuid
from decimal import Decimal
from typing import Any

import httpx

from app.core.config import settings
from app.core.loi import LoiNghiepVu
from app.models.ban_hang import DonHang, ThanhToan
from app.tich_hop.thanh_toan import KetQuaHoan, KetQuaIpn, tham_chieu

TRUONG_IPN = (
    "accessKey", "amount", "extraData", "message", "orderId", "orderInfo", "orderType",
    "partnerCode", "payType", "requestId", "responseTime", "resultCode", "transId",
)  # fmt: skip
TRUONG_TAO = (
    "accessKey", "amount", "extraData", "ipnUrl", "orderId", "orderInfo", "partnerCode", "redirectUrl", "requestId",
    "requestType",
)  # fmt: skip


def ky(tham_so: dict[str, Any], truong: tuple[str, ...], khoa: str) -> str:
    chuoi = "&".join(f"{k}={tham_so.get(k, '')}" for k in truong)
    return hmac.new(khoa.encode(), chuoi.encode(), hashlib.sha256).hexdigest()


class CongMomo:
    def __init__(self) -> None:
        self.khoa = settings.MOMO_SECRET_KEY.get_secret_value()

    async def tao_url_thanh_toan(self, don: DonHang, giao_dich: ThanhToan, ip: str) -> str:
        yeu_cau: dict[str, Any] = {
            "partnerCode": settings.MOMO_PARTNER_CODE,
            "accessKey": settings.MOMO_ACCESS_KEY,
            "requestId": str(uuid.uuid4()),
            "amount": int(giao_dich.so_tien),
            "orderId": tham_chieu(don, giao_dich),
            "orderInfo": f"Thanh toan don hang {don.ma_don}",
            "redirectUrl": settings.MOMO_RETURN_URL,
            "ipnUrl": settings.MOMO_IPN_URL,
            "requestType": "captureWallet",
            "extraData": "",
            "lang": "vi",
        }
        yeu_cau["signature"] = ky(yeu_cau, TRUONG_TAO, self.khoa)
        yeu_cau.pop("accessKey")
        try:  # không thử lại POST tạo giao dịch (spec 08 mục 1)
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(settings.MOMO_ENDPOINT, json=yeu_cau)
            du_lieu = r.json()
        except (httpx.HTTPError, ValueError):
            raise LoiNghiepVu("LOI_DOI_TAC", "Không kết nối được MoMo, vui lòng thử lại sau") from None
        if du_lieu.get("resultCode") != 0 or not du_lieu.get("payUrl"):
            raise LoiNghiepVu("LOI_DOI_TAC", "MoMo từ chối tạo giao dịch, vui lòng thử lại sau")
        return du_lieu["payUrl"]

    def xac_thuc_ipn(self, tham_so: dict[str, Any]) -> KetQuaIpn:
        day_du = {**tham_so, "accessKey": settings.MOMO_ACCESS_KEY}
        hop_le = hmac.compare_digest(str(tham_so.get("signature", "")), ky(day_du, TRUONG_IPN, self.khoa))
        try:
            so_tien = Decimal(str(tham_so.get("amount")))
        except ArithmeticError:
            so_tien = None
        ma_gd = tham_so.get("transId")
        return KetQuaIpn(
            hop_le,
            str(tham_so.get("orderId", "")),
            so_tien,
            None if ma_gd in (None, "") else str(ma_gd),
            tham_so.get("resultCode") == 0,
            {k: v for k, v in tham_so.items() if k != "signature"},
        )

    async def hoan_tien(self, giao_dich_goc: ThanhToan, so_tien: Decimal, ly_do: str) -> KetQuaHoan:
        raise NotImplementedError("Hoàn tiền MoMo làm ở T6.3")

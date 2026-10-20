"""MoMo (spec 08 mục 3). Chữ ký HMAC-SHA256 theo đúng thứ tự trường của từng API; hoàn tiền qua API `refund`."""

import hashlib
import hmac
import uuid
from decimal import Decimal
from typing import Any

import httpx

from app.core.loi import LoiNghiepVu
from app.models.ban_hang import DonHang, ThanhToan
from app.tich_hop import cau_hinh
from app.tich_hop.http import tao_client
from app.tich_hop.thanh_toan import KetQuaHoan, KetQuaIpn, tham_chieu

TRUONG_IPN = (
    "accessKey", "amount", "extraData", "message", "orderId", "orderInfo", "orderType",
    "partnerCode", "payType", "requestId", "responseTime", "resultCode", "transId",
)  # fmt: skip
TRUONG_TAO = (
    "accessKey", "amount", "extraData", "ipnUrl", "orderId", "orderInfo", "partnerCode", "redirectUrl", "requestId",
    "requestType",
)  # fmt: skip


TRUONG_HOAN = ("accessKey", "amount", "description", "orderId", "partnerCode", "requestId", "transId")
THOI_GIAN_CHO_GIAY = 15.0


def ky(tham_so: dict[str, Any], truong: tuple[str, ...], khoa: str) -> str:
    chuoi = "&".join(f"{k}={tham_so.get(k, '')}" for k in truong)
    return hmac.new(khoa.encode(), chuoi.encode(), hashlib.sha256).hexdigest()


class CongMomo:
    def __init__(self) -> None:
        self.khoa = cau_hinh.momo_secret_key()

    async def tao_url_thanh_toan(self, don: DonHang, giao_dich: ThanhToan, ip: str) -> str:
        yeu_cau: dict[str, Any] = {
            "partnerCode": cau_hinh.momo_partner_code(),
            "accessKey": cau_hinh.momo_access_key(),
            "requestId": str(uuid.uuid4()),
            "amount": int(giao_dich.so_tien),
            "orderId": tham_chieu(don, giao_dich),
            "orderInfo": f"Thanh toan don hang {don.ma_don}",
            "redirectUrl": cau_hinh.momo_return_url(),
            "ipnUrl": cau_hinh.momo_ipn_url(),
            "requestType": "captureWallet",
            "extraData": "",
            "lang": "vi",
        }
        yeu_cau["signature"] = ky(yeu_cau, TRUONG_TAO, self.khoa)
        yeu_cau.pop("accessKey")
        try:  # không thử lại POST tạo giao dịch (spec 08 mục 1)
            url = cau_hinh.momo_endpoint()
            async with tao_client(url, timeout=10) as client:
                r = await client.post(url, json=yeu_cau)
            du_lieu = r.json()
        except (httpx.HTTPError, ValueError):
            raise LoiNghiepVu("LOI_DOI_TAC", "Không kết nối được MoMo, vui lòng thử lại sau") from None
        if du_lieu.get("resultCode") != 0 or not du_lieu.get("payUrl"):
            raise LoiNghiepVu("LOI_DOI_TAC", "MoMo từ chối tạo giao dịch, vui lòng thử lại sau")
        return du_lieu["payUrl"]

    def xac_thuc_ipn(self, tham_so: dict[str, Any]) -> KetQuaIpn:
        day_du = {**tham_so, "accessKey": cau_hinh.momo_access_key()}
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

    async def hoan_tien(
        self, giao_dich_goc: ThanhToan, so_tien: Decimal, ly_do: str, ma_yeu_cau: str = ""
    ) -> KetQuaHoan:
        """API `refund` theo `transId` gốc. `orderId` và `requestId` cố định theo giao dịch hoàn (`ma_yeu_cau`) để
        gọi lại không hoàn hai lần; không thử lại POST (spec 08 mục 1): lỗi mạng ném ra cho nơi gọi."""
        ma = ma_yeu_cau or f"HT{giao_dich_goc.id}"
        yeu_cau: dict[str, Any] = {
            "partnerCode": cau_hinh.momo_partner_code(),
            "orderId": ma,
            "requestId": ma,
            "amount": int(so_tien),
            "transId": int(giao_dich_goc.ma_giao_dich_cong or 0),
            "lang": "vi",
            "description": ly_do[:200],
        }
        yeu_cau["signature"] = ky({**yeu_cau, "accessKey": cau_hinh.momo_access_key()}, TRUONG_HOAN, self.khoa)
        url = cau_hinh.momo_refund_endpoint()
        async with tao_client(url, timeout=THOI_GIAN_CHO_GIAY) as client:
            r = await client.post(url, json=yeu_cau)
        phan_hoi = r.json()
        if phan_hoi.get("resultCode") != 0:
            return KetQuaHoan(False, None, f"{phan_hoi.get('resultCode')}: {phan_hoi.get('message', '')}")
        return KetQuaHoan(True, f"HOAN-{phan_hoi.get('transId')}")

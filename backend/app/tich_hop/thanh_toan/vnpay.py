"""VNPay (spec 08 mục 2). Chữ ký HMAC-SHA512 trên các tham số `vnp_*` đã sắp xếp theo tên. Hoàn tiền ở T6.3."""

import hashlib
import hmac
from datetime import datetime
from decimal import Decimal
from typing import Any
from urllib.parse import quote_plus

from app.core.config import settings
from app.core.thoi_gian import VN_TZ, bay_gio_utc
from app.models.ban_hang import DonHang, ThanhToan
from app.tich_hop.thanh_toan import KetQuaHoan, KetQuaIpn, tham_chieu

THANH_CONG = "00"


def _chuoi_ky(tham_so: dict[str, Any]) -> str:
    return "&".join(
        f"{k}={quote_plus(str(v))}"
        for k, v in sorted(tham_so.items())
        if k.startswith("vnp_") and k not in ("vnp_SecureHash", "vnp_SecureHashType") and v not in (None, "")
    )


def ky(tham_so: dict[str, Any], khoa: str) -> str:
    return hmac.new(khoa.encode(), _chuoi_ky(tham_so).encode(), hashlib.sha512).hexdigest()


def _gio_vn(t: datetime) -> str:
    return t.astimezone(VN_TZ).strftime("%Y%m%d%H%M%S")


class CongVnpay:
    def __init__(self) -> None:
        self.khoa = settings.VNPAY_HASH_SECRET.get_secret_value()

    async def tao_url_thanh_toan(self, don: DonHang, giao_dich: ThanhToan, ip: str) -> str:
        tham_so: dict[str, Any] = {
            "vnp_Version": "2.1.0",
            "vnp_Command": "pay",
            "vnp_TmnCode": settings.VNPAY_TMN_CODE,
            "vnp_Amount": int(giao_dich.so_tien) * 100,
            "vnp_CurrCode": "VND",
            "vnp_TxnRef": tham_chieu(don, giao_dich),
            "vnp_OrderInfo": f"Thanh toan don hang {don.ma_don}",
            "vnp_OrderType": "other",
            "vnp_Locale": "vn",
            "vnp_ReturnUrl": settings.VNPAY_RETURN_URL,
            "vnp_IpAddr": ip,
            "vnp_CreateDate": _gio_vn(bay_gio_utc()),
        }
        if don.han_thanh_toan is not None:
            tham_so["vnp_ExpireDate"] = _gio_vn(don.han_thanh_toan)
        return f"{settings.VNPAY_URL}?{_chuoi_ky(tham_so)}&vnp_SecureHash={ky(tham_so, self.khoa)}"

    def xac_thuc_ipn(self, tham_so: dict[str, Any]) -> KetQuaIpn:
        hop_le = hmac.compare_digest(str(tham_so.get("vnp_SecureHash", "")).lower(), ky(tham_so, self.khoa))
        du_lieu = {k: v for k, v in tham_so.items() if k not in ("vnp_SecureHash", "vnp_SecureHashType")}
        try:
            so_tien = Decimal(str(tham_so.get("vnp_Amount"))) / 100
        except ArithmeticError:
            so_tien = None
        thanh_cong = (
            tham_so.get("vnp_ResponseCode") == THANH_CONG and tham_so.get("vnp_TransactionStatus") == THANH_CONG
        )
        return KetQuaIpn(
            hop_le, str(tham_so.get("vnp_TxnRef", "")), so_tien, tham_so.get("vnp_TransactionNo"), thanh_cong, du_lieu
        )

    async def hoan_tien(self, giao_dich_goc: ThanhToan, so_tien: Decimal, ly_do: str) -> KetQuaHoan:
        raise NotImplementedError("Hoàn tiền VNPay làm ở T6.3")

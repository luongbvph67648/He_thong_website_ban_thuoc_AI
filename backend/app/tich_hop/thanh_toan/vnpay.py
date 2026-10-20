"""VNPay (spec 08 mục 2). Chữ ký HMAC-SHA512 trên các tham số `vnp_*` đã sắp xếp theo tên; hoàn tiền qua API
`merchant_webapi` (JSON, ký trên các trường nối bằng `|`)."""

import hashlib
import hmac
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any
from urllib.parse import quote_plus

from app.core.thoi_gian import VN_TZ, bay_gio_utc
from app.models.ban_hang import DonHang, ThanhToan
from app.tich_hop import cau_hinh
from app.tich_hop.http import tao_client
from app.tich_hop.thanh_toan import KetQuaHoan, KetQuaIpn, tham_chieu

logger = logging.getLogger(__name__)

THANH_CONG = "00"

TRUONG_HOAN = (
    "vnp_RequestId", "vnp_Version", "vnp_Command", "vnp_TmnCode", "vnp_TransactionType", "vnp_TxnRef", "vnp_Amount",
    "vnp_TransactionNo", "vnp_TransactionDate", "vnp_CreateBy", "vnp_CreateDate", "vnp_IpAddr", "vnp_OrderInfo",
)  # fmt: skip
TRUONG_PHAN_HOI_HOAN = (
    "vnp_ResponseId", "vnp_Command", "vnp_ResponseCode", "vnp_Message", "vnp_TmnCode", "vnp_TxnRef", "vnp_Amount",
    "vnp_BankCode", "vnp_PayDate", "vnp_TransactionNo", "vnp_TransactionType", "vnp_TransactionStatus", "vnp_OrderInfo",
    "vnp_PromotionCode", "vnp_PromotionAmount",
)  # fmt: skip
THOI_GIAN_CHO_GIAY = 15.0


def _chuoi_ky(tham_so: dict[str, Any]) -> str:
    return "&".join(
        f"{k}={quote_plus(str(v))}"
        for k, v in sorted(tham_so.items())
        if k.startswith("vnp_") and k not in ("vnp_SecureHash", "vnp_SecureHashType") and v not in (None, "")
    )


def ky(tham_so: dict[str, Any], khoa: str) -> str:
    return hmac.new(khoa.encode(), _chuoi_ky(tham_so).encode(), hashlib.sha512).hexdigest()


def ky_chuoi_gach_doc(tham_so: dict[str, Any], truong: tuple[str, ...], khoa: str) -> str:
    """HMAC-SHA512 trên giá trị các trường nối bằng `|` (thiếu thì chuỗi rỗng): cách ký của API hoàn tiền VNPay."""
    chuoi = "|".join("" if tham_so.get(t) is None else str(tham_so[t]) for t in truong)
    return hmac.new(khoa.encode(), chuoi.encode(), hashlib.sha512).hexdigest()


def _gio_vn(t: datetime) -> str:
    return t.astimezone(VN_TZ).strftime("%Y%m%d%H%M%S")


class CongVnpay:
    def __init__(self) -> None:
        self.khoa = cau_hinh.vnpay_hash_secret()

    async def tao_url_thanh_toan(self, don: DonHang, giao_dich: ThanhToan, ip: str) -> str:
        tham_so: dict[str, Any] = {
            "vnp_Version": "2.1.0",
            "vnp_Command": "pay",
            "vnp_TmnCode": cau_hinh.vnpay_tmn_code(),
            "vnp_Amount": int(giao_dich.so_tien) * 100,
            "vnp_CurrCode": "VND",
            "vnp_TxnRef": tham_chieu(don, giao_dich),
            "vnp_OrderInfo": f"Thanh toan don hang {don.ma_don}",
            "vnp_OrderType": "other",
            "vnp_Locale": "vn",
            "vnp_ReturnUrl": cau_hinh.vnpay_return_url(),
            "vnp_IpAddr": ip,
            "vnp_CreateDate": _gio_vn(bay_gio_utc()),
        }
        if don.han_thanh_toan is not None:
            tham_so["vnp_ExpireDate"] = _gio_vn(don.han_thanh_toan)
        return f"{cau_hinh.vnpay_url()}?{_chuoi_ky(tham_so)}&vnp_SecureHash={ky(tham_so, self.khoa)}"

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

    async def hoan_tien(
        self, giao_dich_goc: ThanhToan, so_tien: Decimal, ly_do: str, ma_yeu_cau: str = ""
    ) -> KetQuaHoan:
        """API hoàn tiền (`vnp_Command=refund`). `ma_yeu_cau` cố định theo giao dịch hoàn nên gọi lại (lỗi mạng,
        Admin bấm lại) cho cùng kết quả thay vì hoàn hai lần. Không thử lại POST (spec 08 mục 1): lỗi mạng ném ra."""
        du_lieu = giao_dich_goc.du_lieu_ipn or {}
        yeu_cau: dict[str, Any] = {
            "vnp_RequestId": ma_yeu_cau[:32] or f"HT{giao_dich_goc.id}",
            "vnp_Version": "2.1.0",
            "vnp_Command": "refund",
            "vnp_TmnCode": cau_hinh.vnpay_tmn_code(),
            "vnp_TransactionType": "02" if so_tien == giao_dich_goc.so_tien else "03",  # 02 toàn phần, 03 một phần
            "vnp_TxnRef": du_lieu.get("vnp_TxnRef", ""),
            "vnp_Amount": int(so_tien) * 100,
            "vnp_OrderInfo": ly_do[:255],
            "vnp_TransactionNo": giao_dich_goc.ma_giao_dich_cong or "",
            "vnp_TransactionDate": du_lieu.get("vnp_PayDate", ""),
            "vnp_CreateBy": "he-thong",
            "vnp_CreateDate": _gio_vn(bay_gio_utc()),
            "vnp_IpAddr": "127.0.0.1",
        }
        yeu_cau["vnp_SecureHash"] = ky_chuoi_gach_doc(yeu_cau, TRUONG_HOAN, self.khoa)
        url = cau_hinh.vnpay_api_url()
        async with tao_client(url, timeout=THOI_GIAN_CHO_GIAY) as client:
            r = await client.post(url, json=yeu_cau)
        phan_hoi = r.json()
        dung = ky_chuoi_gach_doc(phan_hoi, TRUONG_PHAN_HOI_HOAN, self.khoa)
        if not hmac.compare_digest(str(phan_hoi.get("vnp_SecureHash", "")).lower(), dung):
            return KetQuaHoan(False, None, "Chữ ký phản hồi hoàn tiền của VNPay không hợp lệ")
        if phan_hoi.get("vnp_ResponseCode") != THANH_CONG:
            return KetQuaHoan(False, None, f"{phan_hoi.get('vnp_ResponseCode')}: {phan_hoi.get('vnp_Message', '')}")
        return KetQuaHoan(True, f"HOAN-{phan_hoi.get('vnp_TransactionNo')}")

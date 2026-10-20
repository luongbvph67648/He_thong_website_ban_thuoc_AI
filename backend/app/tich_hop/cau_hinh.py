"""Cấu hình hiệu lực của VNPay, MoMo, GHN: giá trị trong `.env`, nếu để trống và đang ở chế độ `mo_phong` thì dùng
mặc định của máy chủ mô phỏng (không cần đăng ký tài khoản đối tác). Đọc mỗi lần gọi để đổi chế độ lúc chạy
(test) có hiệu lực.

Chế độ `sandbox`/`ghn`/production không bao giờ dùng mặc định: thiếu cấu hình là lỗi cấu hình (chốt chặn ở
`Settings.kiem_tra_san_xuat`), không âm thầm rơi về khóa mô phỏng.
"""

from app.core.config import settings
from app.tich_hop.http import GOC_MO_PHONG


def _tt_mo_phong() -> bool:
    return settings.THANH_TOAN_CHE_DO == "mo_phong"


def _vc_mo_phong() -> bool:
    return settings.VAN_CHUYEN_CHE_DO == "mo_phong"


def _goc_frontend() -> str:
    return settings.FRONTEND_URL.rstrip("/")


# --- VNPay ---
def vnpay_tmn_code() -> str:
    return settings.VNPAY_TMN_CODE or ("MOPHONG1" if _tt_mo_phong() else "")


def vnpay_hash_secret() -> str:
    return settings.VNPAY_HASH_SECRET.get_secret_value() or ("mo-phong-vnpay-hash-secret" if _tt_mo_phong() else "")


def vnpay_url() -> str:
    return settings.VNPAY_URL or (f"{_goc_frontend()}/api/v1/mo-phong/vnpay/vpcpay.html" if _tt_mo_phong() else "")


def vnpay_return_url() -> str:
    return settings.VNPAY_RETURN_URL or (f"{_goc_frontend()}/thanh-toan/ket-qua" if _tt_mo_phong() else "")


def vnpay_api_url() -> str:
    return settings.VNPAY_API_URL or (f"{GOC_MO_PHONG}/vnpay/merchant_webapi/api/transaction" if _tt_mo_phong() else "")


# --- MoMo ---
def momo_partner_code() -> str:
    return settings.MOMO_PARTNER_CODE or ("MOMOMOPHONG" if _tt_mo_phong() else "")


def momo_access_key() -> str:
    return settings.MOMO_ACCESS_KEY or ("mo-phong-access-key" if _tt_mo_phong() else "")


def momo_secret_key() -> str:
    return settings.MOMO_SECRET_KEY.get_secret_value() or ("mo-phong-momo-secret-key" if _tt_mo_phong() else "")


def momo_endpoint() -> str:
    return settings.MOMO_ENDPOINT or (f"{GOC_MO_PHONG}/momo/v2/gateway/api/create" if _tt_mo_phong() else "")


def momo_refund_endpoint() -> str:
    return settings.MOMO_REFUND_ENDPOINT or (f"{GOC_MO_PHONG}/momo/v2/gateway/api/refund" if _tt_mo_phong() else "")


def momo_return_url() -> str:
    return settings.MOMO_RETURN_URL or (f"{_goc_frontend()}/thanh-toan/ket-qua" if _tt_mo_phong() else "")


def momo_ipn_url() -> str:
    return settings.MOMO_IPN_URL or (f"{_goc_frontend()}/api/v1/webhook/momo-ipn" if _tt_mo_phong() else "")


# --- GHN ---
def ghn_token() -> str:
    return settings.GHN_TOKEN.get_secret_value() or ("mo-phong-ghn-token" if _vc_mo_phong() else "")


def ghn_shop_id() -> str:
    return settings.GHN_SHOP_ID or ("1234567" if _vc_mo_phong() else "")


def ghn_url() -> str:
    return settings.GHN_URL or (f"{GOC_MO_PHONG}/ghn" if _vc_mo_phong() else "")


def ghn_webhook_token() -> str:
    return settings.GHN_WEBHOOK_TOKEN.get_secret_value() or ("mo-phong-ghn-webhook-token" if _vc_mo_phong() else "")

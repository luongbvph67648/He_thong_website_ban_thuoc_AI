"""Mô phỏng MoMo (API v2): tạo giao dịch `captureWallet`, IPN và hoàn tiền `refund`.

Chữ ký HMAC-SHA256 trên chuỗi `k=v&...` theo thứ tự trường của từng API (xem `thanh_toan/momo.py`); IPN là POST
JSON tới `ipnUrl` và cửa hàng phải trả HTTP 204. Mã kết quả: `0` thành công, `1006` khách từ chối, `1001` không đủ
tiền, `1005` hết hạn, `13` xác thực doanh nghiệp thất bại (sai chữ ký), `20` sai định dạng, `22` số tiền không hợp
lệ, `42` không tìm thấy đơn. Tên trường và bảng mã cần đối chiếu lại với tài liệu MoMo hiện hành khi chạy sandbox
thật (QĐ-56).
"""

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Literal
from urllib.parse import urlencode

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.core.config import settings
from app.core.db import Db
from app.core.loi import LoiNghiepVu
from app.models.ban_hang import ThanhToan
from app.models.enums import PhuongThucThanhToan, TrangThaiGiaoDich
from app.tich_hop import cau_hinh
from app.tich_hop.mo_phong.chung import (
    GiaoDichMoPhongRa,
    KetQuaMoPhongRa,
    client_ung_dung_chinh,
    da_hoan,
    duong_dan_cua,
    so_tu_chuoi,
    tra_cuu_giao_dich,
)
from app.tich_hop.thanh_toan import momo
from app.tich_hop.thanh_toan.momo import TRUONG_HOAN

router = APIRouter(prefix="/momo", tags=["Mô phỏng MoMo"])

TOI_THIEU, TOI_DA = 1_000, 50_000_000  # giới hạn số tiền một giao dịch captureWallet

# (resultCode, message) theo kết quả khách chọn trên trang mô phỏng
KET_QUA: dict[str, tuple[int, str]] = {
    "thanh_cong": (0, "Successful."),
    "tu_choi": (1006, "Transaction denied by user."),
    "khong_du_tien": (1001, "Transaction failed due to insufficient fund."),
    "het_han": (1005, "Transaction is expired."),
}


def _khoa() -> str:
    return cau_hinh.momo_secret_key()


def _ms() -> int:
    return int(time.time() * 1000)


def _phan_hoi(yeu_cau: dict[str, Any], ma: int, thong_diep: str, **them: Any) -> dict[str, Any]:
    return {
        "partnerCode": cau_hinh.momo_partner_code(),
        "orderId": yeu_cau.get("orderId", ""),
        "requestId": yeu_cau.get("requestId", ""),
        "amount": yeu_cau.get("amount", 0),
        "responseTime": _ms(),
        "message": thong_diep,
        "resultCode": ma,
        **them,
    }


def _ma_hoa_the(du_lieu: dict[str, Any]) -> str:
    """Đính thông tin giao dịch vào `payUrl` có chữ ký: máy chủ mô phỏng không cần lưu trạng thái."""
    than = base64.urlsafe_b64encode(json.dumps(du_lieu, separators=(",", ":")).encode()).decode().rstrip("=")
    return f"{than}.{hmac.new(_khoa().encode(), than.encode(), hashlib.sha256).hexdigest()}"


def _giai_ma_the(the: str) -> dict[str, Any]:
    than, _, chu_ky = the.partition(".")
    dung = hmac.new(_khoa().encode(), than.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(chu_ky, dung):
        raise LoiNghiepVu("DU_LIEU_KHONG_HOP_LE", "MoMo: liên kết thanh toán không hợp lệ")
    return json.loads(base64.urlsafe_b64decode(than + "=" * (-len(than) % 4)))


@router.post("/v2/gateway/api/create", summary="Tạo giao dịch thanh toán MoMo (mô phỏng)")
async def tao_giao_dich(yeu_cau: dict[str, Any]):
    day_du = {**yeu_cau, "accessKey": cau_hinh.momo_access_key()}
    if yeu_cau.get("partnerCode") != cau_hinh.momo_partner_code() or not hmac.compare_digest(
        str(yeu_cau.get("signature", "")), momo.ky(day_du, momo.TRUONG_TAO, _khoa())
    ):
        return _phan_hoi(yeu_cau, 13, "Xác thực doanh nghiệp thất bại.")
    cac_truong = ("orderId", "requestId", "amount", "orderInfo", "redirectUrl", "ipnUrl", "requestType")
    if any(yeu_cau.get(t) in (None, "") for t in cac_truong) or yeu_cau["requestType"] != "captureWallet":
        return _phan_hoi(yeu_cau, 20, "Yêu cầu sai định dạng.")
    if not isinstance(yeu_cau["amount"], int) or not TOI_THIEU <= yeu_cau["amount"] <= TOI_DA:
        return _phan_hoi(yeu_cau, 22, "Số tiền giao dịch không hợp lệ (từ 1.000 đến 50.000.000 VND).")
    the = _ma_hoa_the({t: yeu_cau.get(t, "") for t in (*cac_truong, "extraData", "partnerCode")})
    pay_url = f"{settings.FRONTEND_URL.rstrip('/')}/thanh-toan-gia?cong=momo&token={the}"
    return _phan_hoi(
        yeu_cau,
        0,
        "Thành công.",
        payUrl=pay_url,
        deeplink=f"momo://app?token={the[:16]}",
        qrCodeUrl=pay_url,
        shortLink=pay_url,
    )


@router.get("/giao-dich", response_model=GiaoDichMoPhongRa, summary="Thông tin giao dịch từ payUrl (mô phỏng)")
async def giao_dich(token: str, db: Db):
    d = _giai_ma_the(token)
    gd, don = await tra_cuu_giao_dich(db, d["orderId"], PhuongThucThanhToan.momo)
    return GiaoDichMoPhongRa(
        cong=PhuongThucThanhToan.momo,
        tham_chieu=d["orderId"],
        ma_don=don.ma_don if don else d["orderId"].rpartition("-")[0],
        so_tien=int(d["amount"]),
        noi_dung=d["orderInfo"],
        trang_thai=gd.trang_thai.value if gd else "khong_ro",
        het_han_luc=don.han_thanh_toan.isoformat() if don and don.han_thanh_toan else None,
    )


class ThanhToanVao(BaseModel):
    token: str
    ket_qua: Literal["thanh_cong", "tu_choi", "khong_du_tien", "het_han"]


@router.post(
    "/thanh-toan", response_model=KetQuaMoPhongRa, summary="Khách hoàn tất trên MoMo: báo IPN, trả redirectUrl"
)
async def thanh_toan(vao: ThanhToanVao):
    d = _giai_ma_the(vao.token)
    ma, thong_diep = KET_QUA[vao.ket_qua]
    ipn: dict[str, Any] = {
        "partnerCode": cau_hinh.momo_partner_code(),
        "orderId": d["orderId"],
        "requestId": d["requestId"],
        "amount": int(d["amount"]),
        "orderInfo": d["orderInfo"],
        "orderType": "momo_wallet",
        "transId": 2_000_000_000 + int(so_tu_chuoi(secrets.token_hex(8), 9)),
        "resultCode": ma,
        "message": thong_diep,
        "payType": "qr",
        "responseTime": _ms(),
        "extraData": d.get("extraData", ""),
    }
    ipn["signature"] = momo.ky({**ipn, "accessKey": cau_hinh.momo_access_key()}, momo.TRUONG_IPN, _khoa())
    # IPN: POST JSON server-to-server tới ipnUrl của cửa hàng, cửa hàng phải trả HTTP 204
    async with client_ung_dung_chinh() as client:
        r = await client.post(duong_dan_cua(d["ipnUrl"]), json=ipn)
    goc = d["redirectUrl"]
    return KetQuaMoPhongRa(
        thanh_cong=ma == 0,
        redirect_url=f"{goc}{'&' if '?' in goc else '?'}{urlencode(ipn)}",
        ma_phan_hoi=str(r.status_code),
    )


@router.post("/v2/gateway/api/refund", summary="Hoàn tiền MoMo (mô phỏng)")
async def hoan_tien(yeu_cau: dict[str, Any], db: Db):
    day_du = {**yeu_cau, "accessKey": cau_hinh.momo_access_key()}
    if yeu_cau.get("partnerCode") != cau_hinh.momo_partner_code() or not hmac.compare_digest(
        str(yeu_cau.get("signature", "")), momo.ky(day_du, TRUONG_HOAN, _khoa())
    ):
        return _phan_hoi(yeu_cau, 13, "Xác thực doanh nghiệp thất bại.")
    if any(yeu_cau.get(t) in (None, "") for t in ("orderId", "requestId", "amount", "transId")):
        return _phan_hoi(yeu_cau, 20, "Yêu cầu sai định dạng.")
    goc = (
        await db.execute(
            select(ThanhToan).where(
                ThanhToan.ma_giao_dich_cong == str(yeu_cau["transId"]),
                ThanhToan.cong_thanh_toan == PhuongThucThanhToan.momo,
                ThanhToan.trang_thai == TrangThaiGiaoDich.thanh_cong,
            )
        )
    ).scalar_one_or_none()
    if goc is None:
        return _phan_hoi(yeu_cau, 42, "Không tìm thấy giao dịch cần hoàn.")
    trans_id_hoan = 2_000_000_000 + int(so_tu_chuoi(str(yeu_cau["requestId"]), 9))
    if await db.scalar(
        select(ThanhToan.id).where(
            ThanhToan.thanh_toan_goc_id == goc.id, ThanhToan.ma_giao_dich_cong == f"HOAN-{trans_id_hoan}"
        )
    ):  # cùng requestId đã hoàn rồi: trả lại đúng kết quả cũ
        return _phan_hoi(yeu_cau, 0, "Thành công.", transId=trans_id_hoan)
    so_tien = yeu_cau["amount"]
    if not isinstance(so_tien, int) or not TOI_THIEU <= so_tien <= int(goc.so_tien) - await da_hoan(db, goc.id):
        return _phan_hoi(yeu_cau, 22, "Số tiền hoàn không hợp lệ.")
    return _phan_hoi(yeu_cau, 0, "Thành công.", transId=trans_id_hoan)

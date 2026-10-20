"""Mô phỏng VNPay: trang thanh toán `vpcpay.html`, ReturnUrl, IPN và API hoàn tiền `merchant_webapi`.

Đúng theo tài liệu VNPay v2.1.0: chữ ký HMAC-SHA512 trên tham số `vnp_*` sắp xếp theo tên; mã phản hồi `00` thành công,
`24` khách hủy, `51` không đủ số dư, `11` hết hạn, `09` thẻ chưa đăng ký dịch vụ, `12` thẻ bị khóa, `13` sai OTP; hoàn
tiền ký HMAC-SHA512 trên các trường nối bằng `|` theo thứ tự tài liệu (tên trường và bảng mã cần đối chiếu lại với tài
liệu VNPay hiện hành khi chạy sandbox thật, QĐ-56).
"""

import hmac
import secrets
from datetime import datetime
from typing import Any, Literal
from urllib.parse import parse_qsl, urlencode

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.core.config import settings
from app.core.db import Db
from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import VN_TZ, bay_gio_utc
from app.models.ban_hang import ThanhToan
from app.models.enums import PhuongThucThanhToan, TrangThaiGiaoDich
from app.tich_hop import cau_hinh
from app.tich_hop.mo_phong.chung import (
    GiaoDichMoPhongRa,
    KetQuaMoPhongRa,
    client_ung_dung_chinh,
    da_hoan,
    gio_vn,
    so_tu_chuoi,
    tra_cuu_giao_dich,
)
from app.tich_hop.thanh_toan import vnpay
from app.tich_hop.thanh_toan.vnpay import TRUONG_HOAN, TRUONG_PHAN_HOI_HOAN, ky_chuoi_gach_doc

router = APIRouter(prefix="/vnpay", tags=["Mô phỏng VNPay"])

# (vnp_ResponseCode, vnp_TransactionStatus) theo kết quả khách chọn trên trang mô phỏng
KET_QUA: dict[str, tuple[str, str]] = {
    "thanh_cong": ("00", "00"),
    "khach_huy": ("24", "02"),
    "khong_du_so_du": ("51", "02"),
    "the_chua_dang_ky": ("09", "02"),
    "the_bi_khoa": ("12", "02"),
    "het_han": ("11", "02"),
    "sai_otp": ("13", "02"),
}


def _khoa() -> str:
    return cau_hinh.vnpay_hash_secret()


def _hop_le(tham_so: dict[str, Any]) -> bool:
    return (
        hmac.compare_digest(str(tham_so.get("vnp_SecureHash", "")).lower(), vnpay.ky(tham_so, _khoa()))
        and tham_so.get("vnp_TmnCode") == cau_hinh.vnpay_tmn_code()
    )


def _loi_html(ma: str, thong_diep: str) -> HTMLResponse:
    return HTMLResponse(f"<h3>VNPAY: {ma}</h3><p>{thong_diep}</p>", status_code=400)


@router.get("/vpcpay.html", summary="Trang thanh toán VNPay (mô phỏng): kiểm chữ ký rồi chuyển sang giao diện mô phỏng")
async def trang_thanh_toan(request: Request):
    tham_so = dict(request.query_params)
    if not _hop_le(tham_so):
        return _loi_html("70", "Sai chữ ký")
    if tham_so.get("vnp_Command") != "pay" or not str(tham_so.get("vnp_Amount", "")).isdigit():
        return _loi_html("03", "Dữ liệu gửi sang không đúng định dạng")
    return RedirectResponse(f"{settings.FRONTEND_URL.rstrip('/')}/thanh-toan-gia?cong=vnpay&{request.url.query}")


async def _giao_dich_tu_query(db: Db, query: str) -> tuple[dict[str, str], GiaoDichMoPhongRa]:
    tham_so = dict(parse_qsl(query, keep_blank_values=True))
    if not _hop_le(tham_so):
        raise LoiNghiepVu("DU_LIEU_KHONG_HOP_LE", "VNPAY: sai chữ ký (mã 70)")
    ref = tham_so.get("vnp_TxnRef", "")
    gd, don = await tra_cuu_giao_dich(db, ref, PhuongThucThanhToan.vnpay)
    het_han = None
    if tham_so.get("vnp_ExpireDate"):
        het_han = datetime.strptime(tham_so["vnp_ExpireDate"], "%Y%m%d%H%M%S").replace(tzinfo=VN_TZ).isoformat()
    return tham_so, GiaoDichMoPhongRa(
        cong=PhuongThucThanhToan.vnpay,
        tham_chieu=ref,
        ma_don=don.ma_don if don else ref.rpartition("-")[0],
        so_tien=int(tham_so.get("vnp_Amount", "0")) // 100,
        noi_dung=tham_so.get("vnp_OrderInfo", ""),
        trang_thai=gd.trang_thai.value if gd else "khong_ro",
        het_han_luc=het_han,
    )


@router.get("/giao-dich", response_model=GiaoDichMoPhongRa, summary="Thông tin giao dịch từ URL thanh toán (mô phỏng)")
async def giao_dich(request: Request, db: Db):
    return (await _giao_dich_tu_query(db, request.url.query))[1]


class ThanhToanVao(BaseModel):
    query: str
    """Nguyên chuỗi query của URL thanh toán (đã có `vnp_SecureHash`) mà cửa hàng tạo ra."""
    ket_qua: Literal[
        "thanh_cong", "khach_huy", "khong_du_so_du", "the_chua_dang_ky", "the_bi_khoa", "het_han", "sai_otp"
    ]
    ngan_hang: str = "NCB"


@router.post(
    "/thanh-toan", response_model=KetQuaMoPhongRa, summary="Khách hoàn tất trên trang VNPay: báo IPN, trả ReturnUrl"
)
async def thanh_toan(vao: ThanhToanVao, db: Db):
    tham_so, gd = await _giao_dich_tu_query(db, vao.query)
    ma_phan_hoi, trang_thai = KET_QUA[vao.ket_qua]
    ket_qua: dict[str, Any] = {
        "vnp_TmnCode": cau_hinh.vnpay_tmn_code(),
        "vnp_Amount": tham_so["vnp_Amount"],
        "vnp_BankCode": vao.ngan_hang,
        "vnp_BankTranNo": f"VNP{so_tu_chuoi(secrets.token_hex(8), 8)}",
        "vnp_CardType": "ATM",
        "vnp_OrderInfo": tham_so.get("vnp_OrderInfo", ""),
        "vnp_PayDate": gio_vn(bay_gio_utc()),
        "vnp_ResponseCode": ma_phan_hoi,
        "vnp_TransactionNo": so_tu_chuoi(secrets.token_hex(8), 8),
        "vnp_TransactionStatus": trang_thai,
        "vnp_TxnRef": tham_so["vnp_TxnRef"],
    }
    ket_qua["vnp_SecureHash"] = vnpay.ky(ket_qua, _khoa())
    # IPN: đối tác gọi máy chủ cửa hàng (server-to-server), KHÔNG qua trình duyệt của khách
    async with client_ung_dung_chinh() as client:
        r = await client.get("/api/v1/webhook/vnpay-ipn", params=ket_qua)
    try:
        rsp = str(r.json().get("RspCode", ""))
    except ValueError:
        rsp = ""
    goc = tham_so.get("vnp_ReturnUrl", cau_hinh.vnpay_return_url())
    return KetQuaMoPhongRa(
        thanh_cong=ma_phan_hoi == "00",
        redirect_url=f"{goc}{'&' if '?' in goc else '?'}{urlencode(ket_qua)}",
        ma_phan_hoi=rsp,
    )


def _phan_hoi_hoan(yeu_cau: dict[str, Any], ma: str, thong_diep: str, **them: Any) -> JSONResponse:
    kq: dict[str, Any] = {
        "vnp_ResponseId": so_tu_chuoi(str(yeu_cau.get("vnp_RequestId", "")) + "resp", 10),
        "vnp_Command": "refund",
        "vnp_ResponseCode": ma,
        "vnp_Message": thong_diep,
        "vnp_TmnCode": cau_hinh.vnpay_tmn_code(),
        "vnp_TxnRef": yeu_cau.get("vnp_TxnRef", ""),
        "vnp_Amount": yeu_cau.get("vnp_Amount", ""),
        "vnp_BankCode": "",
        "vnp_PayDate": "",
        "vnp_TransactionNo": "",
        "vnp_TransactionType": yeu_cau.get("vnp_TransactionType", ""),
        "vnp_TransactionStatus": "",
        "vnp_OrderInfo": yeu_cau.get("vnp_OrderInfo", ""),
        "vnp_PromotionCode": "",
        "vnp_PromotionAmount": "",
        **them,
    }
    kq["vnp_SecureHash"] = ky_chuoi_gach_doc(kq, TRUONG_PHAN_HOI_HOAN, _khoa())
    return JSONResponse(kq)


@router.post("/merchant_webapi/api/transaction", summary="API hoàn tiền VNPay (mô phỏng)")
async def hoan_tien(yeu_cau: dict[str, Any], db: Db):
    """`vnp_Command=refund`. Cùng `vnp_RequestId` cho cùng `vnp_TransactionNo` hoàn: gọi lại an toàn."""
    ky_dung = ky_chuoi_gach_doc(yeu_cau, TRUONG_HOAN, _khoa())
    if not hmac.compare_digest(str(yeu_cau.get("vnp_SecureHash", "")).lower(), ky_dung):
        return _phan_hoi_hoan(yeu_cau, "97", "Sai chữ ký")
    if yeu_cau.get("vnp_TmnCode") != cau_hinh.vnpay_tmn_code():
        return _phan_hoi_hoan(yeu_cau, "02", "Mã website không hợp lệ")
    so_tien = str(yeu_cau.get("vnp_Amount", ""))
    if (
        yeu_cau.get("vnp_Command") != "refund"
        or not so_tien.isdigit()
        or yeu_cau.get("vnp_TransactionType") not in ("02", "03")
    ):
        return _phan_hoi_hoan(yeu_cau, "03", "Dữ liệu gửi sang không đúng định dạng")
    gd, _ = await tra_cuu_giao_dich(db, str(yeu_cau.get("vnp_TxnRef", "")), PhuongThucThanhToan.vnpay)
    ma_gd_goc = str(yeu_cau.get("vnp_TransactionNo", ""))
    if gd is None or gd.trang_thai != TrangThaiGiaoDich.thanh_cong or (ma_gd_goc and gd.ma_giao_dich_cong != ma_gd_goc):
        return _phan_hoi_hoan(yeu_cau, "91", "Không tìm thấy giao dịch yêu cầu hoàn trả")
    ma_hoan = so_tu_chuoi(str(yeu_cau.get("vnp_RequestId", "")), 8)
    if await db.scalar(
        select(ThanhToan.id).where(
            ThanhToan.thanh_toan_goc_id == gd.id, ThanhToan.ma_giao_dich_cong == f"HOAN-{ma_hoan}"
        )
    ):  # cùng RequestId đã hoàn rồi: trả lại đúng kết quả cũ (cổng không hoàn hai lần)
        return _phan_hoi_hoan(
            yeu_cau,
            "00",
            "Refund Success",
            vnp_BankCode=str((gd.du_lieu_ipn or {}).get("vnp_BankCode", "")),
            vnp_PayDate=gio_vn(bay_gio_utc()),
            vnp_TransactionNo=ma_hoan,
            vnp_TransactionStatus="05",
        )
    con_lai = int(gd.so_tien) - await da_hoan(db, gd.id)
    so_tien_hoan = int(so_tien) // 100
    if (
        so_tien_hoan <= 0
        or so_tien_hoan > con_lai
        or (yeu_cau["vnp_TransactionType"] == "02" and so_tien_hoan != int(gd.so_tien))
    ):
        return _phan_hoi_hoan(
            yeu_cau, "93", "Số tiền hoàn trả không hợp lệ. Số tiền hoàn trả phải nhỏ hơn hoặc bằng số tiền thanh toán"
        )
    du_lieu = gd.du_lieu_ipn or {}
    return _phan_hoi_hoan(
        yeu_cau,
        "00",
        "Refund Success",
        vnp_BankCode=str(du_lieu.get("vnp_BankCode", "")),
        vnp_PayDate=gio_vn(bay_gio_utc()),
        vnp_TransactionNo=ma_hoan,
        vnp_TransactionStatus="05",
    )

"""IPN của cổng thanh toán: `/api/v1/webhook/*` (HT04). Xác thực bằng chữ ký của cổng, không dùng đăng nhập."""

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel
from sqlalchemy import select

from app.core.db import Db
from app.models.ban_hang import DonHang, ThanhToan
from app.models.enums import PhuongThucThanhToan
from app.modules.thanh_toan.dich_vu import KetQuaXuLy, xu_ly_ipn
from app.tich_hop.thanh_toan import lay_cong
from app.tich_hop.thanh_toan.gia import CongGia, dung_ipn

router = APIRouter(prefix="/webhook", tags=["Webhook thanh toán"])
router_gia = APIRouter(prefix="/webhook", tags=["Webhook thanh toán"])

# Bảng mã của VNPay (spec 08 mục 2)
RSP_VNPAY: dict[KetQuaXuLy, tuple[str, str]] = {
    KetQuaXuLy.thanh_cong: ("00", "Confirm Success"),
    KetQuaXuLy.khong_tim_thay: ("01", "Order not found"),
    KetQuaXuLy.da_xu_ly: ("02", "Order already confirmed"),
    KetQuaXuLy.sai_so_tien: ("04", "Invalid amount"),
    KetQuaXuLy.sai_chu_ky: ("97", "Invalid signature"),
}


def _vnpay(kq: KetQuaXuLy) -> dict:
    ma, thong_diep = RSP_VNPAY[kq]
    return {"RspCode": ma, "Message": thong_diep}


@router.get("/vnpay-ipn", summary="IPN VNPay (HT04)")
async def vnpay_ipn(request: Request, db: Db):
    ket_qua = lay_cong(PhuongThucThanhToan.vnpay).xac_thuc_ipn(dict(request.query_params))
    return _vnpay(await xu_ly_ipn(db, PhuongThucThanhToan.vnpay, ket_qua))


@router.post("/momo-ipn", summary="IPN MoMo (HT04)")
async def momo_ipn(request: Request, db: Db):
    try:
        tham_so = await request.json()
    except ValueError:
        return Response(status_code=400)
    ket_qua = lay_cong(PhuongThucThanhToan.momo).xac_thuc_ipn(tham_so if isinstance(tham_so, dict) else {})
    kq = await xu_ly_ipn(db, PhuongThucThanhToan.momo, ket_qua)
    # MoMo chỉ cần HTTP 204 để ngừng gọi lại; lỗi dữ liệu trả 400 (không thử lại có ích)
    if kq in (KetQuaXuLy.thanh_cong, KetQuaXuLy.da_xu_ly):
        return Response(status_code=204)
    return Response(status_code=400)


class GiaIpnVao(BaseModel):
    giao_dich: str
    thanh_cong: bool


@router_gia.post("/gia-ipn", summary="IPN của cổng giả (chỉ khi THANH_TOAN_CHE_DO=gia)")
async def gia_ipn(vao: GiaIpnVao, db: Db):
    """Dựng IPN ký bằng khóa giả cho giao dịch này rồi đi qua đúng hàm xử lý IPN như cổng thật."""
    so_tien = 0
    id_text = vao.giao_dich.rpartition("-")[2]
    if id_text.isascii() and id_text.isdigit() and len(id_text) <= 12:
        tong = await db.scalar(
            select(DonHang.tong_tien)
            .join(ThanhToan, ThanhToan.don_hang_id == DonHang.id)
            .where(ThanhToan.id == int(id_text))
        )
        so_tien = tong if tong is not None else 0
    ipn = dung_ipn(vao.giao_dich, so_tien, vao.thanh_cong)
    ket_qua = CongGia().xac_thuc_ipn(ipn)
    # Giao dịch có thể thuộc VNPay hoặc MoMo (đơn chọn cổng nào), cổng giả thay cả hai
    cong = (
        await db.scalar(select(ThanhToan.cong_thanh_toan).where(ThanhToan.id == int(id_text)))
        if (id_text.isascii() and id_text.isdigit() and len(id_text) <= 12)
        else None
    )
    return _vnpay(await xu_ly_ipn(db, cong or PhuongThucThanhToan.vnpay, ket_qua))

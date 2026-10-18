"""IPN của cổng thanh toán: `/api/v1/webhook/*` (HT04). Xác thực bằng chữ ký của cổng, không dùng đăng nhập."""

from datetime import datetime

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel
from sqlalchemy import select

from app.core.db import Db
from app.core.loi import LoiNghiepVu
from app.models.ban_hang import DonHang, ThanhToan
from app.models.enums import LoaiGiaoDich, PhuongThucThanhToan
from app.modules.thanh_toan.dich_vu import KetQuaXuLy, xu_ly_ipn
from app.tich_hop.thanh_toan import lay_cong, tham_chieu
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


class GiaGiaoDichRa(BaseModel):
    """Thông tin để trang cổng giả dựng giao diện giống VNPay/MoMo (cổng thật cũng nhận số tiền và mã đơn từ URL)."""

    giao_dich: str
    ma_don: str
    so_tien: int
    cong: PhuongThucThanhToan
    trang_thai: str
    """`khoi_tao` (đang chờ khách thanh toán), `thanh_cong` hoặc `that_bai`."""
    het_han_luc: datetime | None = None


@router_gia.get("/gia-giao-dich", response_model=GiaGiaoDichRa, summary="Thông tin giao dịch cho cổng giả")
async def gia_giao_dich(giao_dich: str, db: Db):
    id_text = giao_dich.rpartition("-")[2]
    if not (id_text.isascii() and id_text.isdigit() and len(id_text) <= 12):
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy giao dịch")
    dong = (
        await db.execute(
            select(ThanhToan, DonHang)
            .join(DonHang, DonHang.id == ThanhToan.don_hang_id)
            .where(ThanhToan.id == int(id_text), ThanhToan.loai == LoaiGiaoDich.thanh_toan)
        )
    ).first()
    if dong is None or giao_dich != tham_chieu(dong[1], dong[0]):
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy giao dịch")
    tt, don = dong
    return GiaGiaoDichRa(
        giao_dich=giao_dich,
        ma_don=don.ma_don,
        so_tien=int(tt.so_tien),
        cong=tt.cong_thanh_toan,
        trang_thai=tt.trang_thai.value,
        het_han_luc=don.han_thanh_toan,
    )


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

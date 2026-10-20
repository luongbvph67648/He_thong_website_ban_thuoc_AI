"""Phần dùng chung của máy chủ mô phỏng: gọi lại IPN/webhook vào ứng dụng chính và sổ tra cứu giao dịch."""

import hashlib
from typing import Any

import httpx
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.thoi_gian import VN_TZ
from app.models.ban_hang import DonHang, ThanhToan
from app.models.enums import LoaiGiaoDich, PhuongThucThanhToan, TrangThaiGiaoDich
from app.tich_hop.mo_phong import ung_dung_chinh


class GiaoDichMoPhongRa(BaseModel):
    """Thông tin giao dịch để trang đối tác mô phỏng (frontend) dựng giao diện giống VNPay/MoMo thật."""

    cong: PhuongThucThanhToan
    tham_chieu: str
    ma_don: str
    so_tien: int
    noi_dung: str
    trang_thai: str
    """`khoi_tao` (đang chờ khách trả), `thanh_cong`, `that_bai`, hoặc `khong_ro` khi cửa hàng chưa có giao dịch này."""
    het_han_luc: str | None = None


class KetQuaMoPhongRa(BaseModel):
    """Kết quả sau khi khách thao tác trên trang đối tác: nơi đưa trình duyệt về (như `ReturnUrl` thật)."""

    thanh_cong: bool
    redirect_url: str
    ma_phan_hoi: str
    """Mã cửa hàng trả lời IPN: VNPay `RspCode`, MoMo HTTP status."""


def gio_vn(t) -> str:
    return t.astimezone(VN_TZ).strftime("%Y%m%d%H%M%S")


def so_tu_chuoi(chuoi: str, so_chu_so: int) -> str:
    """Số `so_chu_so` chữ số suy ra TẤT ĐỊNH từ `chuoi`: cùng `requestId` thì cùng mã (gọi lại an toàn)."""
    return str(int(hashlib.sha256(chuoi.encode()).hexdigest()[:15], 16) % 10**so_chu_so).zfill(so_chu_so)


def tach_tham_chieu(tham_chieu: str) -> tuple[str, int | None]:
    ma_don, _, id_text = tham_chieu.rpartition("-")
    ok = id_text.isascii() and id_text.isdigit() and len(id_text) <= 12
    return ma_don, int(id_text) if ok else None


async def tra_cuu_giao_dich(
    db: AsyncSession, tham_chieu: str, cong: PhuongThucThanhToan
) -> tuple[ThanhToan | None, DonHang | None]:
    ma_don, gd_id = tach_tham_chieu(tham_chieu)
    if gd_id is None:
        return None, None
    dong = (
        await db.execute(
            select(ThanhToan, DonHang)
            .join(DonHang, DonHang.id == ThanhToan.don_hang_id)
            .where(
                ThanhToan.id == gd_id,
                ThanhToan.loai == LoaiGiaoDich.thanh_toan,
                ThanhToan.cong_thanh_toan == cong,
                DonHang.ma_don == ma_don,
            )
        )
    ).first()
    return (None, None) if dong is None else (dong[0], dong[1])


async def da_hoan(db: AsyncSession, goc_id: int) -> int:
    """Tổng đã hoàn thành công cho một giao dịch gốc (cổng chỉ cho hoàn tối đa số đã trả)."""
    return int(
        await db.scalar(
            select(func.coalesce(func.sum(ThanhToan.so_tien), 0)).where(
                ThanhToan.thanh_toan_goc_id == goc_id,
                ThanhToan.loai == LoaiGiaoDich.hoan_tien,
                ThanhToan.trang_thai == TrangThaiGiaoDich.thanh_cong,
            )
        )
        or 0
    )


def client_ung_dung_chinh() -> httpx.AsyncClient:
    """Client gọi vào ứng dụng chính như đối tác gọi IPN/webhook của cửa hàng (qua ASGI, không cần mở cổng)."""
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=ung_dung_chinh()), base_url="http://mo-phong.local")


def duong_dan_cua(url: str) -> str:
    """Chỉ lấy đường dẫn của URL IPN: đối tác thật gọi đúng địa chỉ công khai, mô phỏng đi thẳng vào ứng dụng."""
    return httpx.URL(url).raw_path.decode()


def thieu_truong(tham_so: dict[str, Any], *ten: str) -> list[str]:
    return [t for t in ten if tham_so.get(t) in (None, "")]

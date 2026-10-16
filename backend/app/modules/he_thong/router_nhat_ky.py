"""Tra cứu nhật ký hệ thống (AD15): `/api/v1/noi-bo/nhat-ky`, chỉ đọc. Cần `audit.view`."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.core.phan_trang import PhanTrang, Trang, tao_trang
from app.core.tham_so import IdInt
from app.models.he_thong import NhanVien
from app.modules.he_thong import nhat_ky_service
from app.modules.he_thong.schemas import GiaTriLocNhatKy, NhatKyDoc

router = APIRouter(prefix="/noi-bo/nhat-ky", tags=["Nhật ký hệ thống"])

NhatKyXem = Annotated[NhanVien, Depends(yeu_cau_quyen("audit.view", "xem"))]
KHONG_NUL = r"^[^\x00]*$"  # byte NUL làm PostgreSQL báo lỗi (500): chặn từ đầu


def _chuoi(toi_da: int, mo_ta: str):
    return Annotated[str | None, Query(max_length=toi_da, pattern=KHONG_NUL, description=mo_ta)]


@router.get("", response_model=Trang[NhatKyDoc], summary="Tra cứu nhật ký hệ thống (AD15)")
async def tra_cuu(
    actor: NhatKyXem,
    db: Db,
    tp: PhanTrang,
    bang: _chuoi(60, "Tên bảng, khớp chính xác") = None,
    ban_ghi_id: _chuoi(60, "Id bản ghi, khớp chính xác") = None,
    nhan_vien_id: Annotated[IdInt | None, Query(description="Người thực hiện")] = None,
    hanh_dong: _chuoi(30, "Hành động, khớp chính xác") = None,
    tu_ngay: Annotated[date | None, Query(description="Từ ngày (giờ Việt Nam), gồm cả ngày này")] = None,
    den_ngay: Annotated[date | None, Query(description="Đến ngày (giờ Việt Nam), gồm cả ngày này")] = None,
):
    dong, tong = await nhat_ky_service.tim(
        db,
        bang=bang,
        ban_ghi_id=ban_ghi_id,
        nhan_vien_id=nhan_vien_id,
        hanh_dong=hanh_dong,
        tu_ngay=tu_ngay,
        den_ngay=den_ngay,
        tp=tp,
    )
    return tao_trang([nhat_ky_service.doc(d) for d in dong], tong, tp)


@router.get(
    "/gia-tri-loc", response_model=GiaTriLocNhatKy, summary="Các bảng và hành động đang có trong nhật ký (AD15)"
)
async def gia_tri_loc(actor: NhatKyXem, db: Db):
    return await nhat_ky_service.gia_tri_loc(db)

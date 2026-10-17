"""KHO14: đề xuất nhập hàng từ dự báo AI (`/api/v1/noi-bo/de-xuat-nhap`, mã quyền `forecast.view`)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.core.phan_trang import PhanTrang, Trang
from app.core.tham_so import KHONG_NUL, IdInt
from app.models.he_thong import NhanVien
from app.modules.du_bao import dich_vu
from app.modules.du_bao.schemas import BieuDoDeXuat, DaXuLyVao, DeXuatRa, KyDeXuat

router = APIRouter(prefix="/noi-bo/de-xuat-nhap", tags=["Đề xuất nhập hàng từ AI"])
Xem = Annotated[NhanVien, Depends(yeu_cau_quyen("forecast.view", "xem"))]
Ghi = Annotated[NhanVien, Depends(yeu_cau_quyen("forecast.view"))]


@router.get("/ky", response_model=list[KyDeXuat], summary="Các kỳ đã có đề xuất, mới nhất trước (KHO14)")
async def cac_ky(nv: Xem, db: Db):
    return await dich_vu.cac_ky(db)


@router.get("", response_model=Trang[DeXuatRa], summary="Đề xuất nhập hàng của một kỳ (KHO14)")
async def danh_sach(
    nv: Xem,
    db: Db,
    tp: PhanTrang,
    ky: date | None = None,
    chi_can_nhap: bool = True,
    da_xu_ly: bool | None = None,
    q: Annotated[str | None, Query(max_length=100, pattern=KHONG_NUL)] = None,
):
    return await dich_vu.danh_sach(db, tp, ky=ky, chi_can_nhap=chi_can_nhap, da_xu_ly=da_xu_ly, q=q)


@router.get("/{de_xuat_id}/bieu-do", response_model=BieuDoDeXuat, summary="Lịch sử bán và dự báo theo tuần (KHO14)")
async def bieu_do(de_xuat_id: IdInt, nv: Xem, db: Db):
    return await dich_vu.bieu_do(db, de_xuat_id)


@router.put("/{de_xuat_id}/da-xu-ly", response_model=DeXuatRa, summary="Đánh dấu đã (chưa) xử lý đề xuất (KHO14)")
async def da_xu_ly(de_xuat_id: IdInt, vao: DaXuLyVao, nv: Ghi, db: Db):
    return await dich_vu.danh_dau_da_xu_ly(db, de_xuat_id, vao.da_xu_ly)

"""Soạn hàng và đóng gói của kho: `/api/v1/noi-bo/soan-hang` (KHO03, KHO04). Hàng đợi lấy từ `GET /noi-bo/don-hang`."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.core.tham_so import IdInt
from app.models.he_thong import NhanVien
from app.modules.ban_hang import soan_hang
from app.modules.ban_hang.schemas_soan_hang import DoiLoVao, SoanHangRa

router = APIRouter(tags=["Soạn hàng, đóng gói"])
Xem = Annotated[NhanVien, Depends(yeu_cau_quyen("order.pick", "xem"))]
Soan = Annotated[NhanVien, Depends(yeu_cau_quyen("order.pick"))]
DongGoi = Annotated[NhanVien, Depends(yeu_cau_quyen("shipment.create"))]
GOC = "/noi-bo/soan-hang/{don_id}"


@router.get(GOC, response_model=SoanHangRa, summary="Phiếu soạn hàng: dòng, lô giữ, lô gợi ý FEFO (KHO03)")
async def chi_tiet(don_id: IdInt, nv: Xem, db: Db):
    return await soan_hang.chi_tiet(db, don_id)


@router.post(GOC + "/doi-lo", response_model=SoanHangRa, summary="Đổi lô, bắt buộc lý do (KHO03)")
async def doi_lo(don_id: IdInt, vao: DoiLoVao, nv: Soan, db: Db):
    return await soan_hang.doi_lo(db, don_id, vao)


@router.post(GOC + "/bat-dau", response_model=SoanHangRa, summary="Bắt đầu soạn hàng: chốt lô, trừ tồn (KHO03)")
async def bat_dau(don_id: IdInt, nv: Soan, db: Db):
    return await soan_hang.bat_dau_soan(db, nv, don_id)


@router.post(GOC + "/dong-goi", response_model=SoanHangRa, summary="Đóng gói, tạo vận đơn, chờ lấy hàng (KHO04)")
async def dong_goi(don_id: IdInt, nv: DongGoi, db: Db):
    return await soan_hang.dong_goi(db, nv, don_id)

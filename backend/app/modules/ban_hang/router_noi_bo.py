"""Quản lý đơn hàng nội bộ: `/api/v1/noi-bo/don-hang` (DS01 xem/lọc, DS02 xác nhận, DS03 hủy)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.core.phan_trang import PhanTrang, Trang
from app.core.tham_so import IdInt
from app.models.enums import KenhBan, PhuongThucThanhToan, TrangThaiDon
from app.models.he_thong import NhanVien
from app.modules.ban_hang import dich_vu_don
from app.modules.ban_hang.schemas import DonNoiBoChiTiet, DonNoiBoTomTat, HuyNoiBoVao

router = APIRouter(tags=["Quản lý đơn hàng"])
Xem = Annotated[NhanVien, Depends(yeu_cau_quyen("order.view", "xem"))]
XacNhan = Annotated[NhanVien, Depends(yeu_cau_quyen("order.confirm"))]
Huy = Annotated[NhanVien, Depends(yeu_cau_quyen("order.cancel"))]
GOC = "/noi-bo/don-hang"


@router.get(GOC, response_model=Trang[DonNoiBoTomTat], summary="Danh sách, lọc đơn hàng (DS01)")
async def danh_sach(
    nv: Xem,
    db: Db,
    tp: PhanTrang,
    trang_thai: TrangThaiDon | None = None,
    tu_ngay: date | None = None,
    den_ngay: date | None = None,
    phuong_thuc_tt: PhuongThucThanhToan | None = None,
    kenh_ban: KenhBan | None = None,
    q: str | None = None,
):
    return await dich_vu_don.danh_sach_noi_bo(
        db,
        nv,
        tp,
        trang_thai=trang_thai,
        tu_ngay=tu_ngay,
        den_ngay=den_ngay,
        phuong_thuc_tt=phuong_thuc_tt,
        kenh_ban=kenh_ban,
        q=q,
    )


@router.get(GOC + "/{don_id}", response_model=DonNoiBoChiTiet, summary="Chi tiết đơn và dòng thời gian (DS01)")
async def chi_tiet(don_id: IdInt, nv: Xem, db: Db):
    return await dich_vu_don.chi_tiet_noi_bo(db, nv, don_id)


@router.post(GOC + "/{don_id}/xac-nhan", response_model=DonNoiBoChiTiet, summary="Xác nhận đơn (DS02)")
async def xac_nhan(don_id: IdInt, nv: XacNhan, db: Db):
    return await dich_vu_don.xac_nhan(db, nv, don_id)


@router.post(GOC + "/{don_id}/huy", response_model=DonNoiBoChiTiet, summary="Hủy đơn kèm lý do (DS03)")
async def huy(don_id: IdInt, vao: HuyNoiBoVao, nv: Huy, db: Db):
    return await dich_vu_don.huy(db, nv, don_id, vao.ly_do)

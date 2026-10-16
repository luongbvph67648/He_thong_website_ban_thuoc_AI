"""Duyệt yêu cầu đơn thuốc và tạo đơn từ đơn thuốc (DS04, DS05): `/api/v1/noi-bo/don-thuoc`."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.core.tham_so import KHONG_NUL, IdInt
from app.models.he_thong import NhanVien
from app.modules.don_thuoc import duyet
from app.modules.don_thuoc.schemas_duyet import (
    CanhBaoRa,
    CanhBaoVao,
    HangChoRa,
    SanPhamChon,
    TaoDonRa,
    TaoDonVao,
    TuChoiVao,
    YeuCauDuyetRa,
)
from app.tich_hop.tin_nhan import KenhTinNhan, lay_kenh_tin_nhan

router = APIRouter(tags=["Duyệt đơn thuốc"])
Duyet = Annotated[NhanVien, Depends(yeu_cau_quyen("rx_request.review"))]
TaoDon = Annotated[NhanVien, Depends(yeu_cau_quyen("rx_order.create"))]


@router.get("/noi-bo/don-thuoc", response_model=list[HangChoRa], summary="Hàng chờ đơn thuốc (DS04)")
async def hang_cho(nv: Duyet, db: Db):
    return await duyet.hang_cho(db, nv)


@router.get("/noi-bo/don-thuoc/{yc_id}", response_model=YeuCauDuyetRa, summary="Màn duyệt đơn thuốc (DS04)")
async def chi_tiet(yc_id: IdInt, nv: Duyet, db: Db):
    return await duyet.chi_tiet(db, nv, yc_id)


@router.post("/noi-bo/don-thuoc/{yc_id}/nhan", response_model=YeuCauDuyetRa, summary="Nhận xử lý, khóa yêu cầu (DS04)")
async def nhan(yc_id: IdInt, nv: Duyet, db: Db):
    return await duyet.nhan_xu_ly(db, nv, yc_id)


@router.post("/noi-bo/don-thuoc/{yc_id}/nha", status_code=204, summary="Trả yêu cầu về hàng chờ (DS04)")
async def nha(yc_id: IdInt, nv: Duyet, db: Db):
    await duyet.nha_khoa(db, nv, yc_id)
    return Response(status_code=204)


@router.post("/noi-bo/don-thuoc/{yc_id}/tu-choi", status_code=204, summary="Từ chối yêu cầu, bắt buộc lý do (DS04)")
async def tu_choi(yc_id: IdInt, vao: TuChoiVao, nv: Duyet, db: Db, kenh: KenhTinNhan = Depends(lay_kenh_tin_nhan)):
    await duyet.tu_choi(db, nv, yc_id, vao.ly_do, kenh)
    return Response(status_code=204)


@router.post(
    "/noi-bo/don-thuoc/{yc_id}/canh-bao", response_model=CanhBaoRa, summary="Cảnh báo tương tác, dị ứng (DS04)"
)
async def canh_bao(yc_id: IdInt, vao: CanhBaoVao, nv: Duyet, db: Db):
    return await duyet.tinh_canh_bao(db, nv, yc_id, vao)


@router.get(
    "/noi-bo/don-thuoc/{yc_id}/san-pham",
    response_model=list[SanPhamChon],
    summary="Tìm sản phẩm để chọn vào đơn (DS05)",
)
async def tim_san_pham(
    yc_id: IdInt, nv: TaoDon, db: Db, q: Annotated[str, Query(max_length=100, pattern=KHONG_NUL)] = ""
):
    return await duyet.tim_san_pham(db, nv, yc_id, q)


@router.post(
    "/noi-bo/don-thuoc/{yc_id}/tao-don", response_model=TaoDonRa, status_code=201, summary="Tạo đơn từ đơn thuốc (DS05)"
)
async def tao_don(yc_id: IdInt, vao: TaoDonVao, nv: TaoDon, db: Db, kenh: KenhTinNhan = Depends(lay_kenh_tin_nhan)):
    return await duyet.tao_don(db, nv, yc_id, vao, kenh)

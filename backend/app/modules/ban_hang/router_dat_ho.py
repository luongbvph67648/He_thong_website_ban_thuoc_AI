"""Tạo đơn hộ khách (DS07) và giao đơn tại quầy (DS15): `/api/v1/noi-bo/...`."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query

from app.core import idempotency
from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.core.tham_so import IdInt
from app.models.he_thong import NhanVien
from app.modules.ban_hang import dat_ho, giao_tai_quay
from app.modules.ban_hang.schemas_dat_ho import DonHoRa, DonHoVao, DonQuayRa, GiaoQuayVao, KhachTimRa
from app.modules.tai_khoan.schemas import SoDienThoai

router = APIRouter(tags=["Đơn qua điện thoại và giao tại quầy"])
TaoHo = Annotated[NhanVien, Depends(yeu_cau_quyen("order.create_phone"))]
GiaoQuay = Annotated[NhanVien, Depends(yeu_cau_quyen("order.pickup_handover"))]


@router.get("/noi-bo/don-ho/khach", response_model=KhachTimRa, summary="Tìm khách theo SĐT để tạo đơn hộ (DS07)")
async def tim_khach(nv: TaoHo, db: Db, sdt: Annotated[SoDienThoai, Query()]):
    return await dat_ho.tim_khach(db, sdt)


@router.post("/noi-bo/don-ho", response_model=DonHoRa, status_code=201, summary="Tạo đơn hộ khách (DS07)")
async def tao(
    vao: DonHoVao,
    nv: TaoHo,
    db: Db,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    return await dat_ho.tao_don_ho(db, nv, vao, idempotency.doc_khoa(idempotency_key))


@router.get("/noi-bo/giao-tai-quay", response_model=list[DonQuayRa], summary="Tìm đơn nhận tại quầy (DS15)")
async def tim_don(nv: GiaoQuay, db: Db, q: str = Query(max_length=40)):
    return await giao_tai_quay.tim(db, q)


@router.post("/noi-bo/giao-tai-quay/{don_id}", response_model=DonQuayRa, summary="Giao đơn tại quầy, thu tiền (DS15)")
async def giao(don_id: IdInt, vao: GiaoQuayVao, nv: GiaoQuay, db: Db):
    return await giao_tai_quay.giao(db, nv, don_id, vao.phuong_thuc_thu)

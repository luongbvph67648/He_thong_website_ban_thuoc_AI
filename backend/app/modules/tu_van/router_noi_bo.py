"""Hàng chờ và cửa sổ chat của dược sĩ (DS06): `/api/v1/noi-bo/tu-van`, mã quyền `chat.handle`."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.core.tham_so import IdBigInt
from app.models.he_thong import NhanVien
from app.modules.tu_van import chuyen_duoc_si
from app.modules.tu_van.hub import HUB
from app.modules.tu_van.schemas import ChatChiTiet, ChatTomTat, TinNhanVao

router = APIRouter(prefix="/noi-bo/tu-van", tags=["Tư vấn trực tiếp"])
Xem = Annotated[NhanVien, Depends(yeu_cau_quyen("chat.handle", "xem"))]
Ghi = Annotated[NhanVien, Depends(yeu_cau_quyen("chat.handle"))]


@router.get("", response_model=list[ChatTomTat], summary="Hàng chờ tư vấn (DS06)")
async def hang_cho(nv: Xem, db: Db):
    return await chuyen_duoc_si.hang_cho(db, nv)


@router.get("/{hoi_thoai_id}", response_model=ChatChiTiet, summary="Chi tiết phiên kèm tóm tắt (DS06)")
async def chi_tiet(hoi_thoai_id: IdBigInt, nv: Xem, db: Db):
    return await chuyen_duoc_si.chi_tiet(db, nv, hoi_thoai_id)


@router.post("/{hoi_thoai_id}/nhan", response_model=ChatChiTiet, summary="Nhận phiên (DS06)")
async def nhan(hoi_thoai_id: IdBigInt, nv: Ghi, db: Db):
    return await chuyen_duoc_si.nhan_phien(db, nv, hoi_thoai_id)


@router.post("/{hoi_thoai_id}/dong", response_model=ChatChiTiet, summary="Kết thúc tư vấn hoặc đã gọi lại (DS06)")
async def dong(hoi_thoai_id: IdBigInt, nv: Ghi, db: Db):
    return await chuyen_duoc_si.dong_phien(db, nv, hoi_thoai_id)


@router.post(
    "/{hoi_thoai_id}/tin-nhan", status_code=201, summary="Gửi tin nhắn qua REST khi WebSocket không dùng được (DS06)"
)
async def gui_tin(hoi_thoai_id: IdBigInt, vao: TinNhanVao, nv: Ghi, db: Db):
    await chuyen_duoc_si.dam_bao_duoc_si(db, nv)
    su_kien = await chuyen_duoc_si.gui_tin(db, hoi_thoai_id, "duoc_si", vao.noi_dung, nv.id)
    ma = await chuyen_duoc_si.ma_phien_cua(db, hoi_thoai_id)
    await HUB.phat(str(ma), su_kien)
    return su_kien

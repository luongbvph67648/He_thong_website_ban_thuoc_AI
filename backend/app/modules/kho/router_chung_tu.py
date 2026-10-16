"""Xem gộp chứng từ kho (AD16): `GET /noi-bo/chung-tu-kho`, mã quyền `stock_doc.view` (Admin chỉ xem)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.core.phan_trang import PhanTrang, Trang
from app.models.he_thong import NhanVien
from app.modules.kho import chung_tu_kho
from app.modules.kho.chung_tu_kho import ChungTuKho, LoaiChungTu

router = APIRouter(prefix="/noi-bo/chung-tu-kho", tags=["Xem chứng từ kho"])
Xem = Annotated[NhanVien, Depends(yeu_cau_quyen("stock_doc.view", "xem"))]


@router.get("", response_model=Trang[ChungTuKho], summary="Gộp chứng từ kho, chỉ xem (AD16)")
async def danh_sach(nv: Xem, db: Db, tp: PhanTrang, loai: LoaiChungTu | None = None):
    return await chung_tu_kho.danh_sach(db, tp, loai)

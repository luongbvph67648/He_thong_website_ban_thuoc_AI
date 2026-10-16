"""Phiếu nhập kho (KHO02): `/api/v1/noi-bo/phieu-nhap`. Cần `stock.import` (kho ghi, Admin xem)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.core.phan_trang import PhanTrang, Trang
from app.core.tham_so import IdInt
from app.models.he_thong import NhanVien
from app.modules.kho import phieu_nhap as dich_vu
from app.modules.kho.schemas_phieu_nhap import PhieuNhapChiTiet, PhieuNhapTao, PhieuNhapTomTat, SanPhamTraCuu
from app.modules.tai_khoan.phien_http import dia_chi_ip

router = APIRouter(prefix="/noi-bo/phieu-nhap", tags=["Phiếu nhập kho"])

Xem = Annotated[NhanVien, Depends(yeu_cau_quyen("stock.import", "xem"))]
Ghi = Annotated[NhanVien, Depends(yeu_cau_quyen("stock.import"))]


@router.get("", response_model=Trang[PhieuNhapTomTat], summary="Danh sách phiếu nhập (KHO02)")
async def danh_sach(
    actor: Xem,
    db: Db,
    tp: PhanTrang,
    q: Annotated[str | None, Query(max_length=100)] = None,
    nha_cung_cap_id: Annotated[int | None, Query(ge=1, le=2_147_483_647)] = None,
    tu_ngay: date | None = None,
    den_ngay: date | None = None,
):
    return await dich_vu.danh_sach(db, q, nha_cung_cap_id, tu_ngay, den_ngay, tp)


@router.get("/tra-cuu-san-pham", response_model=list[SanPhamTraCuu], summary="Tìm sản phẩm để nhập, gồm quét mã vạch")
async def tra_cuu_san_pham(actor: Xem, db: Db, q: Annotated[str, Query(max_length=100)] = ""):
    return await dich_vu.tra_cuu_san_pham(db, q)


@router.get("/{phieu_id}", response_model=PhieuNhapChiTiet, summary="Chi tiết phiếu nhập (KHO02)")
async def chi_tiet(phieu_id: IdInt, actor: Xem, db: Db):
    return await dich_vu.chi_tiet(db, phieu_id)


@router.post("", status_code=201, response_model=PhieuNhapChiTiet, summary="Lập phiếu nhập kho (KHO02)")
async def tao(du_lieu: PhieuNhapTao, request: Request, actor: Ghi, db: Db):
    return await dich_vu.tao(db, actor, du_lieu, ip=dia_chi_ip(request))

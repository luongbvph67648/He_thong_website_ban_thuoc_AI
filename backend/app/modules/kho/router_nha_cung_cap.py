"""Nhà cung cấp (KHO01): `/api/v1/noi-bo/nha-cung-cap`. Cần `supplier.manage` (kho ghi, Admin xem)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.core.phan_trang import PhanTrang, Trang
from app.core.tham_so import IdInt
from app.models.he_thong import NhanVien
from app.modules.kho import nha_cung_cap as dich_vu
from app.modules.kho.schemas_nha_cung_cap import NhaCungCapRa, NhaCungCapSua, NhaCungCapTao
from app.modules.tai_khoan.phien_http import dia_chi_ip

router = APIRouter(prefix="/noi-bo/nha-cung-cap", tags=["Nhà cung cấp"])

Xem = Annotated[NhanVien, Depends(yeu_cau_quyen("supplier.manage", "xem"))]
Ghi = Annotated[NhanVien, Depends(yeu_cau_quyen("supplier.manage"))]


@router.get("", response_model=Trang[NhaCungCapRa], summary="Danh sách nhà cung cấp (KHO01)")
async def danh_sach(
    actor: Xem,
    db: Db,
    tp: PhanTrang,
    q: Annotated[str | None, Query(max_length=100)] = None,
    trang_thai: dich_vu.TrangThaiLoc = "dang_hop_tac",
):
    return await dich_vu.danh_sach(db, q, trang_thai, tp)


@router.get("/{nha_cung_cap_id}", response_model=NhaCungCapRa, summary="Chi tiết nhà cung cấp (KHO01)")
async def chi_tiet(nha_cung_cap_id: IdInt, actor: Xem, db: Db):
    return await dich_vu.chi_tiet(db, nha_cung_cap_id)


@router.post("", status_code=201, response_model=NhaCungCapRa, summary="Thêm nhà cung cấp (KHO01)")
async def tao(du_lieu: NhaCungCapTao, request: Request, actor: Ghi, db: Db):
    return await dich_vu.tao(db, actor, du_lieu, ip=dia_chi_ip(request))


@router.patch("/{nha_cung_cap_id}", response_model=NhaCungCapRa, summary="Sửa nhà cung cấp (KHO01)")
async def sua(nha_cung_cap_id: IdInt, du_lieu: NhaCungCapSua, request: Request, actor: Ghi, db: Db):
    return await dich_vu.sua(db, actor, nha_cung_cap_id, du_lieu, ip=dia_chi_ip(request))


@router.delete("/{nha_cung_cap_id}", status_code=204, summary="Ngừng hợp tác = xóa mềm (KHO01)")
async def ngung(
    nha_cung_cap_id: IdInt,
    phien_ban: Annotated[str, Query(min_length=1, max_length=32)],
    request: Request,
    actor: Ghi,
    db: Db,
) -> Response:
    await dich_vu.ngung_hop_tac(db, actor, nha_cung_cap_id, phien_ban, ip=dia_chi_ip(request))
    return Response(status_code=204)


@router.post("/{nha_cung_cap_id}/hop-tac-lai", response_model=NhaCungCapRa, summary="Hợp tác lại (KHO01)")
async def hop_tac_lai(nha_cung_cap_id: IdInt, request: Request, actor: Ghi, db: Db):
    return await dich_vu.hop_tac_lai(db, actor, nha_cung_cap_id, ip=dia_chi_ip(request))

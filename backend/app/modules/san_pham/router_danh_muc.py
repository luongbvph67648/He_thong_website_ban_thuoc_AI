"""Quản lý danh mục của Admin (AD03): `/api/v1/noi-bo/danh-muc`. Cần `category.manage`."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.core.tham_so import IdInt
from app.models.he_thong import NhanVien
from app.modules.san_pham import danh_muc
from app.modules.san_pham.schemas_danh_muc import DanhMucNut, DanhMucSua, DanhMucTao, ViTriDanhMuc
from app.modules.tai_khoan.phien_http import dia_chi_ip

router = APIRouter(prefix="/noi-bo/danh-muc", tags=["Quản lý danh mục"])

DanhMucXem = Annotated[NhanVien, Depends(yeu_cau_quyen("category.manage", "xem"))]
DanhMucSuaQuyen = Annotated[NhanVien, Depends(yeu_cau_quyen("category.manage"))]


@router.get("", response_model=list[DanhMucNut], summary="Cây danh mục (AD03)")
async def cay(actor: DanhMucXem, db: Db):
    return await danh_muc.cay(db)


@router.post("", status_code=201, response_model=DanhMucNut, summary="Thêm danh mục (AD03)")
async def tao(du_lieu: DanhMucTao, request: Request, actor: DanhMucSuaQuyen, db: Db):
    return await danh_muc.tao(db, actor, du_lieu, ip=dia_chi_ip(request))


@router.patch("/{danh_muc_id}", response_model=DanhMucNut, summary="Sửa tên, ảnh, hiển thị (AD03)")
async def sua(danh_muc_id: IdInt, du_lieu: DanhMucSua, request: Request, actor: DanhMucSuaQuyen, db: Db):
    return await danh_muc.sua(db, actor, danh_muc_id, du_lieu, ip=dia_chi_ip(request))


@router.put("/{danh_muc_id}/vi-tri", response_model=list[DanhMucNut], summary="Sắp xếp hoặc chuyển danh mục (AD03)")
async def dat_vi_tri(danh_muc_id: IdInt, du_lieu: ViTriDanhMuc, request: Request, actor: DanhMucSuaQuyen, db: Db):
    """Kéo thả: đặt dưới `danh_muc_cha_id` tại chỉ số `vi_tri`; trả cả cây mới."""
    return await danh_muc.dat_vi_tri(
        db, actor, danh_muc_id, du_lieu.danh_muc_cha_id, du_lieu.vi_tri, ip=dia_chi_ip(request)
    )


@router.delete("/{danh_muc_id}", status_code=204, summary="Xóa mềm danh mục (AD03)")
async def xoa(danh_muc_id: IdInt, request: Request, actor: DanhMucSuaQuyen, db: Db) -> Response:
    await danh_muc.xoa(db, actor, danh_muc_id, ip=dia_chi_ip(request))
    return Response(status_code=204)

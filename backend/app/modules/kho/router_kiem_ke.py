"""Kiểm kê (KHO07): `/noi-bo/kiem-ke`; phiếu điều chỉnh tồn (KHO08): `/noi-bo/dieu-chinh`."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.core.phan_trang import PhanTrang, Trang
from app.core.tham_so import IdInt
from app.models.enums import TrangThaiDuyet, TrangThaiKiemKe
from app.models.he_thong import NhanVien
from app.modules.kho import dieu_chinh, kiem_ke
from app.modules.kho.schemas_kiem_ke import (
    DieuChinhChiTiet,
    DieuChinhTao,
    DieuChinhTomTat,
    KiemKeChiTiet,
    KiemKeTao,
    KiemKeTomTat,
    NhapSoLuong,
)
from app.modules.tai_khoan.phien_http import dia_chi_ip

router = APIRouter(tags=["Kiểm kê và điều chỉnh tồn"])
XemKK = Annotated[NhanVien, Depends(yeu_cau_quyen("stocktake.manage", "xem"))]
GhiKK = Annotated[NhanVien, Depends(yeu_cau_quyen("stocktake.manage"))]
DieuChinh = Annotated[NhanVien, Depends(yeu_cau_quyen("stock_adjust.create"))]
GOC_KK = "/noi-bo/kiem-ke"
GOC_DC = "/noi-bo/dieu-chinh"


@router.get(GOC_KK, response_model=Trang[KiemKeTomTat], summary="Danh sách phiếu kiểm kê (KHO07)")
async def ds_kiem_ke(actor: XemKK, db: Db, tp: PhanTrang, trang_thai: TrangThaiKiemKe | None = None):
    return await kiem_ke.danh_sach(db, trang_thai, tp)


@router.post(
    GOC_KK, status_code=201, response_model=KiemKeChiTiet, summary="Lập phiếu kiểm kê, chụp tồn sổ sách (KHO07)"
)
async def tao_kiem_ke(du_lieu: KiemKeTao, request: Request, actor: GhiKK, db: Db):
    return await kiem_ke.tao(db, actor, du_lieu.danh_muc_id, ip=dia_chi_ip(request))


@router.get(GOC_KK + "/{phieu_id}", response_model=KiemKeChiTiet, summary="Chi tiết phiếu kiểm kê (KHO07)")
async def chi_tiet_kiem_ke(phieu_id: IdInt, actor: XemKK, db: Db):
    return await kiem_ke.chi_tiet(db, phieu_id)


@router.put(GOC_KK + "/{phieu_id}/so-luong", response_model=KiemKeChiTiet, summary="Nhập số lượng thực tế (KHO07)")
async def nhap_so_luong(phieu_id: IdInt, du_lieu: NhapSoLuong, actor: GhiKK, db: Db):
    return await kiem_ke.nhap_so_luong(db, actor, phieu_id, du_lieu)


@router.post(GOC_KK + "/{phieu_id}/chot", response_model=KiemKeChiTiet, summary="Chốt kiểm kê, tính chênh lệch (KHO07)")
async def chot_kiem_ke(phieu_id: IdInt, request: Request, actor: GhiKK, db: Db):
    return await kiem_ke.chot(db, actor, phieu_id, ip=dia_chi_ip(request))


@router.delete(GOC_KK + "/{phieu_id}", status_code=204, summary="Xóa phiếu kiểm kê đang kiểm (KHO07)")
async def xoa_kiem_ke(phieu_id: IdInt, request: Request, actor: GhiKK, db: Db) -> Response:
    await kiem_ke.xoa(db, actor, phieu_id, ip=dia_chi_ip(request))
    return Response(status_code=204)


@router.get(GOC_DC, response_model=Trang[DieuChinhTomTat], summary="Danh sách phiếu điều chỉnh tồn (KHO08)")
async def ds_dieu_chinh(actor: DieuChinh, db: Db, tp: PhanTrang, trang_thai_duyet: TrangThaiDuyet | None = None):
    return await dieu_chinh.danh_sach(db, trang_thai_duyet, tp)


@router.post(GOC_DC, status_code=201, response_model=DieuChinhChiTiet, summary="Lập phiếu điều chỉnh tồn (KHO08)")
async def tao_dieu_chinh(du_lieu: DieuChinhTao, request: Request, actor: DieuChinh, db: Db):
    return await dieu_chinh.tao(db, actor, du_lieu, ip=dia_chi_ip(request))


@router.get(GOC_DC + "/{phieu_id}", response_model=DieuChinhChiTiet, summary="Chi tiết phiếu điều chỉnh tồn (KHO08)")
async def chi_tiet_dieu_chinh(phieu_id: IdInt, actor: DieuChinh, db: Db):
    return await dieu_chinh.chi_tiet(db, phieu_id)

"""Phiếu hủy (KHO09), phiếu xuất trả NCC (KHO11): `/noi-bo/phieu-huy`, `/noi-bo/xuat-tra`; duyệt (AD12):
`/noi-bo/duyet-phieu`."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.core.phan_trang import PhanTrang, Trang
from app.core.tham_so import IdInt
from app.models.enums import TrangThaiDuyet
from app.models.he_thong import NhanVien
from app.modules.kho import duyet_phieu, phieu_huy, phieu_xuat_tra
from app.modules.kho.schemas_kiem_ke import DieuChinhChiTiet
from app.modules.kho.schemas_phieu_kho import (
    LoaiPhieu,
    PhieuChoDuyet,
    PhieuHuyChiTiet,
    PhieuHuyTao,
    PhieuHuyTomTat,
    PhieuXuatTraChiTiet,
    PhieuXuatTraTao,
    PhieuXuatTraTomTat,
    TuChoi,
)
from app.modules.tai_khoan.phien_http import dia_chi_ip

router = APIRouter(tags=["Phiếu hủy, xuất trả và duyệt phiếu kho"])
LapHuy = Annotated[NhanVien, Depends(yeu_cau_quyen("disposal.create"))]
LapXuatTra = Annotated[NhanVien, Depends(yeu_cau_quyen("supplier_return.create"))]
Duyet = Annotated[NhanVien, Depends(yeu_cau_quyen("stock_doc.approve"))]
DuyetXem = Annotated[NhanVien, Depends(yeu_cau_quyen("stock_doc.approve", "xem"))]
GOC_HUY = "/noi-bo/phieu-huy"
GOC_XT = "/noi-bo/xuat-tra"
GOC_DUYET = "/noi-bo/duyet-phieu"


@router.get(GOC_HUY, response_model=Trang[PhieuHuyTomTat], summary="Danh sách phiếu hủy (KHO09)")
async def ds_huy(actor: LapHuy, db: Db, tp: PhanTrang, trang_thai_duyet: TrangThaiDuyet | None = None):
    return await phieu_huy.danh_sach(db, trang_thai_duyet, tp)


@router.post(GOC_HUY, status_code=201, response_model=PhieuHuyChiTiet, summary="Lập phiếu hủy hàng (KHO09)")
async def tao_huy(du_lieu: PhieuHuyTao, request: Request, actor: LapHuy, db: Db):
    return await phieu_huy.tao(db, actor, du_lieu, ip=dia_chi_ip(request))


@router.get(GOC_HUY + "/{phieu_id}", response_model=PhieuHuyChiTiet, summary="Chi tiết phiếu hủy (KHO09)")
async def chi_tiet_huy(phieu_id: IdInt, actor: LapHuy, db: Db):
    return await phieu_huy.chi_tiet(db, phieu_id)


@router.get(GOC_XT, response_model=Trang[PhieuXuatTraTomTat], summary="Danh sách phiếu xuất trả NCC (KHO11)")
async def ds_xuat_tra(actor: LapXuatTra, db: Db, tp: PhanTrang, trang_thai_duyet: TrangThaiDuyet | None = None):
    return await phieu_xuat_tra.danh_sach(db, trang_thai_duyet, tp)


@router.post(GOC_XT, status_code=201, response_model=PhieuXuatTraChiTiet, summary="Lập phiếu xuất trả NCC (KHO11)")
async def tao_xuat_tra(du_lieu: PhieuXuatTraTao, request: Request, actor: LapXuatTra, db: Db):
    return await phieu_xuat_tra.tao(db, actor, du_lieu, ip=dia_chi_ip(request))


@router.get(GOC_XT + "/{phieu_id}", response_model=PhieuXuatTraChiTiet, summary="Chi tiết phiếu xuất trả NCC (KHO11)")
async def chi_tiet_xuat_tra(phieu_id: IdInt, actor: LapXuatTra, db: Db):
    return await phieu_xuat_tra.chi_tiet(db, phieu_id)


@router.get(GOC_DUYET, response_model=Trang[PhieuChoDuyet], summary="Danh sách phiếu kho cần duyệt, gộp ba loại (AD12)")
async def ds_duyet(
    actor: DuyetXem,
    db: Db,
    tp: PhanTrang,
    loai: LoaiPhieu | None = None,
    trang_thai_duyet: TrangThaiDuyet | None = None,
):
    return await duyet_phieu.danh_sach(db, loai, trang_thai_duyet, tp)


@router.get(
    GOC_DUYET + "/{loai}/{phieu_id}",
    response_model=PhieuHuyChiTiet | PhieuXuatTraChiTiet | DieuChinhChiTiet,
    summary="Chi tiết phiếu kho cần duyệt (AD12)",
)
async def chi_tiet_duyet(loai: LoaiPhieu, phieu_id: IdInt, actor: DuyetXem, db: Db):
    return await duyet_phieu.chi_tiet(db, loai, phieu_id)


@router.post(
    GOC_DUYET + "/{loai}/{phieu_id}/duyet",
    response_model=PhieuHuyChiTiet | PhieuXuatTraChiTiet | DieuChinhChiTiet,
    summary="Duyệt phiếu kho, đổi tồn (AD12)",
)
async def duyet(loai: LoaiPhieu, phieu_id: IdInt, request: Request, actor: Duyet, db: Db):
    return await duyet_phieu.duyet(db, actor, loai, phieu_id, ip=dia_chi_ip(request))


@router.post(
    GOC_DUYET + "/{loai}/{phieu_id}/tu-choi",
    response_model=PhieuHuyChiTiet | PhieuXuatTraChiTiet | DieuChinhChiTiet,
    summary="Từ chối phiếu kho, bắt buộc lý do (AD12)",
)
async def tu_choi(loai: LoaiPhieu, phieu_id: IdInt, du_lieu: TuChoi, request: Request, actor: Duyet, db: Db):
    return await duyet_phieu.tu_choi(db, actor, loai, phieu_id, du_lieu.ly_do, ip=dia_chi_ip(request))

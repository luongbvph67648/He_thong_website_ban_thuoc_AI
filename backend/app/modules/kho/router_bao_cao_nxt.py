"""Báo cáo nhập - xuất - tồn (KHO13): `/api/v1/noi-bo/bao-cao/nhap-xuat-ton`."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.core.phan_trang import PhanTrang, Trang
from app.models.enums import KhuTon
from app.models.he_thong import NhanVien
from app.modules.kho import bao_cao_nxt as dich_vu
from app.modules.kho.bao_cao_nxt import DongNxt, Nhom

router = APIRouter(tags=["Báo cáo kho"])
XemBaoCao = Annotated[NhanVien, Depends(yeu_cau_quyen("report.inventory", "xem"))]
TuNgay = Annotated[date, Query(description="Từ ngày (giờ VN), gồm ngày này")]
DenNgay = Annotated[date, Query(description="Đến ngày (giờ VN), gồm ngày này")]
IdSanPham = Annotated[int | None, Query(ge=1, le=2_147_483_647)]
Q = Annotated[str | None, Query(max_length=100)]
LOAI_EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/noi-bo/bao-cao/nhap-xuat-ton", response_model=Trang[DongNxt], summary="Báo cáo nhập xuất tồn (KHO13)")
async def bao_cao(
    actor: XemBaoCao,
    db: Db,
    tp: PhanTrang,
    tu_ngay: TuNgay,
    den_ngay: DenNgay,
    khu: KhuTon = KhuTon.kho_ban,
    nhom: Nhom = Nhom.san_pham,
    san_pham_id: IdSanPham = None,
    q: Q = None,
):
    return await dich_vu.bao_cao(
        db, tp, tu_ngay=tu_ngay, den_ngay=den_ngay, khu=khu, nhom=nhom, san_pham_id=san_pham_id, q=q
    )


@router.get("/noi-bo/bao-cao/nhap-xuat-ton/excel", summary="Xuất Excel báo cáo nhập xuất tồn (KHO13)")
async def xuat_excel(
    actor: XemBaoCao,
    db: Db,
    tu_ngay: TuNgay,
    den_ngay: DenNgay,
    khu: KhuTon = KhuTon.kho_ban,
    nhom: Nhom = Nhom.san_pham,
    san_pham_id: IdSanPham = None,
    q: Q = None,
):
    noi_dung = await dich_vu.xuat_excel(
        db, tu_ngay=tu_ngay, den_ngay=den_ngay, khu=khu, nhom=nhom, san_pham_id=san_pham_id, q=q
    )
    ten = f"nhap-xuat-ton_{tu_ngay:%Y%m%d}_{den_ngay:%Y%m%d}.xlsx"
    return Response(noi_dung, media_type=LOAI_EXCEL, headers={"Content-Disposition": f'attachment; filename="{ten}"'})

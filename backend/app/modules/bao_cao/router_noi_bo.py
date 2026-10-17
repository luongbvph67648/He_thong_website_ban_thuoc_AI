"""AD14 (`report.all`) và DS14 (`report.shift`): `/api/v1/noi-bo/bao-cao/...`."""

from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.models.he_thong import NhanVien
from app.modules.bao_cao import ca, tong_hop
from app.modules.bao_cao.schemas import BaoCaoCa, BaoCaoTongHop

router = APIRouter(tags=["Báo cáo"])
TongHop = Annotated[NhanVien, Depends(yeu_cau_quyen("report.all", "xem"))]
Ca = Annotated[NhanVien, Depends(yeu_cau_quyen("report.shift", "xem"))]
TuNgay = Annotated[date, Query(description="Từ ngày (giờ VN), gồm ngày này")]
DenNgay = Annotated[date, Query(description="Đến ngày (giờ VN), gồm ngày này")]
LOAI_EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/noi-bo/bao-cao/tong-hop", response_model=BaoCaoTongHop, summary="Báo cáo thống kê tổng hợp (AD14)")
async def tong_hop_bao_cao(nv: TongHop, db: Db, tu_ngay: TuNgay, den_ngay: DenNgay):
    return await tong_hop.bao_cao(db, tu_ngay, den_ngay)


@router.get("/noi-bo/bao-cao/tong-hop/excel", summary="Xuất Excel báo cáo tổng hợp (AD14)")
async def tong_hop_excel(nv: TongHop, db: Db, tu_ngay: TuNgay, den_ngay: DenNgay):
    noi_dung = await tong_hop.xuat_excel(db, tu_ngay, den_ngay)
    ten = f"bao-cao-tong-hop_{tu_ngay:%Y%m%d}_{den_ngay:%Y%m%d}.xlsx"
    return Response(noi_dung, media_type=LOAI_EXCEL, headers={"Content-Disposition": f'attachment; filename="{ten}"'})


@router.get("/noi-bo/bao-cao/ca", response_model=BaoCaoCa, summary="Báo cáo bán hàng của ca của tôi (DS14)")
async def bao_cao_ca(
    nv: Ca,
    db: Db,
    tu: Annotated[datetime, Query(description="Đầu ca; không kèm múi giờ thì tính giờ VN")],
    den: Annotated[datetime, Query(description="Cuối ca (loại trừ)")],
):
    return await ca.bao_cao_ca(db, nv, tu, den)

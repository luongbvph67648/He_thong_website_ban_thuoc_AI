"""Sổ địa chỉ (`/api/v1/toi/dia-chi`, KTV01) và danh mục địa giới công khai (`/api/v1/dia-gioi`)."""

from fastapi import APIRouter, Depends, Response

from app.core.db import Db
from app.core.loi import LoiNghiepVu
from app.core.phan_quyen import khach_hien_tai
from app.core.tham_so import IdInt
from app.models.khach_hang import KhachHang
from app.modules.dia_chi import dich_vu
from app.modules.dia_chi.schemas import DiaChiRa, DiaChiTao, DiaChiVao
from app.tich_hop.van_chuyen import DonViHanhChinh, lay_danh_muc_dia_gioi

router = APIRouter(tags=["Sổ địa chỉ"])
Khach = Depends(khach_hien_tai)


@router.get("/toi/dia-chi", response_model=list[DiaChiRa], summary="Sổ địa chỉ của tôi (KTV01)")
async def danh_sach(db: Db, khach: KhachHang = Khach):
    return await dich_vu.danh_sach(db, khach)


@router.post("/toi/dia-chi", response_model=DiaChiRa, status_code=201, summary="Thêm địa chỉ (KTV01)")
async def tao(vao: DiaChiTao, db: Db, khach: KhachHang = Khach):
    return await dich_vu.tao(db, khach, DiaChiVao(**vao.model_dump(exclude={"la_mac_dinh"})), vao.la_mac_dinh)


@router.put("/toi/dia-chi/{dia_chi_id}", response_model=DiaChiRa, summary="Sửa địa chỉ (KTV01)")
async def sua(dia_chi_id: IdInt, vao: DiaChiVao, db: Db, khach: KhachHang = Khach):
    return await dich_vu.sua(db, khach, dia_chi_id, vao)


@router.post("/toi/dia-chi/{dia_chi_id}/mac-dinh", response_model=DiaChiRa, summary="Đặt địa chỉ mặc định (KTV01)")
async def mac_dinh(dia_chi_id: IdInt, db: Db, khach: KhachHang = Khach):
    return await dich_vu.dat_mac_dinh(db, khach, dia_chi_id)


@router.delete("/toi/dia-chi/{dia_chi_id}", status_code=204, summary="Xóa địa chỉ (KTV01)")
async def xoa(dia_chi_id: IdInt, db: Db, khach: KhachHang = Khach):
    await dich_vu.xoa(db, khach, dia_chi_id)
    return Response(status_code=204)


@router.get("/dia-gioi/tinh", response_model=list[DonViHanhChinh], summary="Danh mục tỉnh (spec 08 mục 8)")
async def tinh():
    return lay_danh_muc_dia_gioi().danh_sach_tinh()


@router.get(
    "/dia-gioi/tinh/{ma_tinh}/xa", response_model=list[DonViHanhChinh], summary="Danh mục phường/xã của một tỉnh"
)
async def xa(ma_tinh: str):
    ds = lay_danh_muc_dia_gioi().danh_sach_xa(ma_tinh)
    if ds is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy tỉnh")
    return ds

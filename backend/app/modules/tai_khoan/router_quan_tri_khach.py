"""Quản lý khách hàng của Admin (AD02): `/api/v1/noi-bo/khach-hang`. Cần `customer.manage`."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.core.phan_trang import PhanTrang, SapXepQuery, Trang, tao_trang
from app.core.tham_so import IdInt
from app.models.enums import TrangThaiTaiKhoan
from app.models.he_thong import NhanVien
from app.models.khach_hang import KhachHang
from app.modules.tai_khoan import quan_tri_khach
from app.modules.tai_khoan.phien_http import dia_chi_ip
from app.modules.tai_khoan.schemas_quan_tri_khach import (
    DonHangCuaKhach,
    KhachHangChiTiet,
    KhachHangTomTat,
    KhoaKhachYeuCau,
)

router = APIRouter(prefix="/noi-bo/khach-hang", tags=["Quản lý khách hàng"])

QuanLyXem = Annotated[NhanVien, Depends(yeu_cau_quyen("customer.manage", "xem"))]
QuanLySua = Annotated[NhanVien, Depends(yeu_cau_quyen("customer.manage"))]


def _chi_tiet(khach: KhachHang, so_don: int) -> KhachHangChiTiet:
    truong = {ten: getattr(khach, ten) for ten in KhachHangChiTiet.model_fields if ten != "so_don_hang"}
    return KhachHangChiTiet(**truong, so_don_hang=so_don)


@router.get("", response_model=Trang[KhachHangTomTat], summary="Danh sách khách hàng (AD02)")
async def danh_sach(
    actor: QuanLyXem,
    db: Db,
    tp: PhanTrang,
    q: Annotated[
        str | None, Query(max_length=100, description="Tìm theo tên (không phân biệt dấu), email, số điện thoại")
    ] = None,
    trang_thai: TrangThaiTaiKhoan | None = None,
    sap_xep: SapXepQuery = None,
):
    """`sap_xep` nhận `created_at` (mặc định, giảm dần), `ho_ten`, `email`, `so_dien_thoai`; thêm `-` để giảm dần."""
    dong, tong = await quan_tri_khach.danh_sach(db, q=q, trang_thai=trang_thai, sap_xep=sap_xep, tp=tp)
    return tao_trang([KhachHangTomTat.model_validate(d) for d in dong], tong, tp)


@router.get("/{khach_id}", response_model=KhachHangChiTiet, summary="Chi tiết khách hàng (AD02)")
async def chi_tiet(khach_id: IdInt, actor: QuanLyXem, db: Db):
    khach, so_don = await quan_tri_khach.chi_tiet(db, khach_id)
    return _chi_tiet(khach, so_don)


@router.get("/{khach_id}/don-hang", response_model=Trang[DonHangCuaKhach], summary="Lịch sử mua của khách (AD02)")
async def lich_su_mua(khach_id: IdInt, actor: QuanLyXem, db: Db, tp: PhanTrang):
    dong, tong = await quan_tri_khach.lich_su_mua(db, khach_id, tp=tp)
    return tao_trang([DonHangCuaKhach.model_validate(d) for d in dong], tong, tp)


@router.post("/{khach_id}/khoa", response_model=KhachHangChiTiet, summary="Khóa khách, thu hồi phiên (AD02)")
async def khoa(khach_id: IdInt, request: Request, actor: QuanLySua, db: Db, du_lieu: KhoaKhachYeuCau | None = None):
    khach = await quan_tri_khach.khoa(
        db, actor, khach_id, ly_do=du_lieu.ly_do if du_lieu else None, ip=dia_chi_ip(request)
    )
    _, so_don = await quan_tri_khach.chi_tiet(db, khach_id)
    return _chi_tiet(khach, so_don)


@router.post("/{khach_id}/mo-khoa", response_model=KhachHangChiTiet, summary="Mở khóa khách (AD02)")
async def mo_khoa(khach_id: IdInt, request: Request, actor: QuanLySua, db: Db):
    khach = await quan_tri_khach.mo_khoa(db, actor, khach_id, ip=dia_chi_ip(request))
    _, so_don = await quan_tri_khach.chi_tiet(db, khach_id)
    return _chi_tiet(khach, so_don)

"""Quản lý tài khoản nhân viên của Admin (AD01): `/api/v1/noi-bo/nhan-vien`. Cần `staff.manage`."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.core.phan_trang import PhanTrang, SapXepQuery, Trang, tao_trang
from app.core.tham_so import IdInt
from app.models.enums import TrangThaiTaiKhoan
from app.models.he_thong import NhanVien
from app.modules.nhan_vien import quan_tri
from app.modules.nhan_vien.schemas_quan_tri import (
    NhanVienDaGuiMatKhau,
    NhanVienQuanTriDoc,
    NhanVienSua,
    NhanVienTao,
)
from app.modules.tai_khoan.phien_http import dia_chi_ip
from app.tich_hop.tin_nhan import KenhTinNhan, lay_kenh_tin_nhan

router = APIRouter(prefix="/noi-bo/nhan-vien", tags=["Quản lý nhân viên"])

QuanLyXem = Annotated[NhanVien, Depends(yeu_cau_quyen("staff.manage", "xem"))]
QuanLySua = Annotated[NhanVien, Depends(yeu_cau_quyen("staff.manage"))]
Kenh = Annotated[KenhTinNhan, Depends(lay_kenh_tin_nhan)]


def _doc(nv: NhanVien) -> NhanVienQuanTriDoc:
    return NhanVienQuanTriDoc.model_validate(nv)


def _da_gui(ket_qua: quan_tri.KetQuaDaGuiMatKhau) -> NhanVienDaGuiMatKhau:
    return NhanVienDaGuiMatKhau(**_doc(ket_qua.nhan_vien).model_dump(), gui_den=ket_qua.gui_den)


@router.get("", response_model=Trang[NhanVienQuanTriDoc], summary="Danh sách nhân viên (AD01)")
async def danh_sach(
    actor: QuanLyXem,
    db: Db,
    tp: PhanTrang,
    q: Annotated[str | None, Query(max_length=100, description="Tìm theo tên (không phân biệt dấu), email, mã")] = None,
    vai_tro: Annotated[str | None, Query(max_length=30, description="Mã vai trò: PHARMACIST, WAREHOUSE, ADMIN")] = None,
    trang_thai: TrangThaiTaiKhoan | None = None,
    sap_xep: SapXepQuery = None,
):
    """`sap_xep` nhận `created_at` (mặc định, giảm dần), `ma_nhan_vien`, `ho_ten`, `email`; thêm `-` để giảm dần."""
    dong, tong = await quan_tri.danh_sach(db, q=q, vai_tro=vai_tro, trang_thai=trang_thai, sap_xep=sap_xep, tp=tp)
    return tao_trang([_doc(d) for d in dong], tong, tp)


@router.get("/{nhan_vien_id}", response_model=NhanVienQuanTriDoc, summary="Chi tiết nhân viên (AD01)")
async def chi_tiet(nhan_vien_id: IdInt, actor: QuanLyXem, db: Db):
    return _doc(await quan_tri.chi_tiet(db, nhan_vien_id))


@router.post("", status_code=201, response_model=NhanVienDaGuiMatKhau, summary="Tạo tài khoản nhân viên (AD01)")
async def tao(du_lieu: NhanVienTao, request: Request, actor: QuanLySua, db: Db, kenh: Kenh):
    """Mật khẩu tạm gửi tới email của nhân viên (Admin không thấy); nhân viên bị bắt đổi ở lần đăng nhập đầu."""
    return _da_gui(await quan_tri.tao(db, actor, kenh, du_lieu, ip=dia_chi_ip(request)))


@router.patch("/{nhan_vien_id}", response_model=NhanVienQuanTriDoc, summary="Sửa nhân viên, gán vai trò (AD01)")
async def sua(nhan_vien_id: IdInt, du_lieu: NhanVienSua, request: Request, actor: QuanLySua, db: Db):
    return _doc(await quan_tri.sua(db, actor, nhan_vien_id, du_lieu, ip=dia_chi_ip(request)))


@router.post("/{nhan_vien_id}/khoa", response_model=NhanVienQuanTriDoc, summary="Khóa tài khoản, thu hồi phiên (AD01)")
async def khoa(nhan_vien_id: IdInt, request: Request, actor: QuanLySua, db: Db):
    return _doc(await quan_tri.khoa(db, actor, nhan_vien_id, ip=dia_chi_ip(request)))


@router.post("/{nhan_vien_id}/mo-khoa", response_model=NhanVienQuanTriDoc, summary="Mở khóa tài khoản (AD01)")
async def mo_khoa(nhan_vien_id: IdInt, request: Request, actor: QuanLySua, db: Db):
    return _doc(await quan_tri.mo_khoa(db, actor, nhan_vien_id, ip=dia_chi_ip(request)))


@router.post(
    "/{nhan_vien_id}/dat-lai-mat-khau", response_model=NhanVienDaGuiMatKhau, summary="Đặt lại mật khẩu tạm (AD01)"
)
async def dat_lai_mat_khau(nhan_vien_id: IdInt, request: Request, actor: QuanLySua, db: Db, kenh: Kenh):
    """Mật khẩu tạm mới gửi tới email nhân viên (Admin không thấy), bắt đổi ở lần đăng nhập kế, thu hồi mọi phiên."""
    return _da_gui(await quan_tri.dat_lai_mat_khau(db, actor, kenh, nhan_vien_id, ip=dia_chi_ip(request)))


@router.delete("/{nhan_vien_id}", status_code=204, summary="Xóa mềm nhân viên (AD01)")
async def xoa(nhan_vien_id: IdInt, request: Request, actor: QuanLySua, db: Db) -> Response:
    await quan_tri.xoa_mem(db, actor, nhan_vien_id, ip=dia_chi_ip(request))
    return Response(status_code=204)

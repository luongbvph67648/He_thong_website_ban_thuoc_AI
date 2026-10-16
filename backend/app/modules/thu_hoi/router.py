"""Thu hồi lô: Admin `/noi-bo/thu-hoi` (AD13), kho `/noi-bo/thu-hoi/thuc-hien` (KHO12), dược sĩ
`/noi-bo/thu-hoi/lien-he` (DS13). Route tĩnh khai báo trước route có `{id}`."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.core.phan_trang import PhanTrang, Trang
from app.core.tham_so import IdInt
from app.models.enums import TrangThaiThuHoi
from app.models.he_thong import NhanVien
from app.modules.tai_khoan.phien_http import dia_chi_ip
from app.modules.thu_hoi import dich_vu
from app.modules.thu_hoi.schemas import KhachThuHoi, LenhChiTiet, LenhTao, LenhTomTat, LienHeVao

router = APIRouter(prefix="/noi-bo/thu-hoi", tags=["Thu hồi lô"])
TaoLenh = Annotated[NhanVien, Depends(yeu_cau_quyen("recall.create"))]
XemLenh = Annotated[NhanVien, Depends(yeu_cau_quyen("recall.create", muc="xem"))]
KhoXem = Annotated[NhanVien, Depends(yeu_cau_quyen("recall.execute", muc="xem"))]
LienHeXem = Annotated[NhanVien, Depends(yeu_cau_quyen("recall.contact", muc="xem"))]
LienHeGhi = Annotated[NhanVien, Depends(yeu_cau_quyen("recall.contact"))]


@router.get("/thuc-hien", response_model=Trang[LenhTomTat], summary="Lệnh thu hồi đang mở cho kho (KHO12)")
async def kho_danh_sach(nv: KhoXem, db: Db, tp: PhanTrang):
    return await dich_vu.danh_sach(db, tp, None, chi_dang_mo=True)


@router.get("/thuc-hien/{lenh_id}", response_model=LenhChiTiet, summary="Lô cần gom của lệnh thu hồi (KHO12)")
async def kho_chi_tiet(lenh_id: IdInt, nv: KhoXem, db: Db):
    return await dich_vu.chi_tiet(db, lenh_id)


@router.get("/lien-he", response_model=Trang[LenhTomTat], summary="Lệnh thu hồi đang mở cho dược sĩ (DS13)")
async def lien_he_danh_sach(nv: LienHeXem, db: Db, tp: PhanTrang):
    return await dich_vu.danh_sach(db, tp, None, chi_dang_mo=True)


@router.get("/lien-he/{lenh_id}/khach", response_model=list[KhachThuHoi], summary="Khách cần liên hệ (DS13)")
async def lien_he_khach(lenh_id: IdInt, nv: LienHeXem, db: Db):
    return await dich_vu.danh_sach_khach(db, nv, lenh_id)


@router.put("/lien-he/khach/{ct_id}", response_model=KhachThuHoi, summary="Ghi kết quả liên hệ khách (DS13)")
async def lien_he_cap_nhat(ct_id: IdInt, vao: LienHeVao, nv: LienHeGhi, db: Db):
    return await dich_vu.cap_nhat_lien_he(db, nv, ct_id, vao)


@router.get("", response_model=Trang[LenhTomTat], summary="Danh sách lệnh thu hồi (AD13)")
async def danh_sach(nv: XemLenh, db: Db, tp: PhanTrang, trang_thai: TrangThaiThuHoi | None = None):
    return await dich_vu.danh_sach(db, tp, trang_thai)


@router.post("", response_model=LenhChiTiet, status_code=201, summary="Khởi tạo lệnh thu hồi lô (AD13)")
async def tao(vao: LenhTao, nv: TaoLenh, db: Db, request: Request):
    return await dich_vu.tao_lenh(db, nv, vao, ip=dia_chi_ip(request))


@router.get("/{lenh_id}", response_model=LenhChiTiet, summary="Chi tiết lệnh thu hồi (AD13)")
async def chi_tiet(lenh_id: IdInt, nv: XemLenh, db: Db):
    return await dich_vu.chi_tiet(db, lenh_id)


@router.post("/{lenh_id}/dong", response_model=LenhChiTiet, summary="Đóng lệnh thu hồi khi đã xử lý xong (AD13)")
async def dong(lenh_id: IdInt, nv: TaoLenh, db: Db, request: Request):
    return await dich_vu.dong_lenh(db, nv, lenh_id, ip=dia_chi_ip(request))

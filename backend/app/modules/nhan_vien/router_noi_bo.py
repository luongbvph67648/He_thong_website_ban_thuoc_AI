"""Hồ sơ cá nhân của nhân viên (NV02): `/api/v1/noi-bo/toi`."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.models.he_thong import NhanVien
from app.modules.nhan_vien import service
from app.modules.nhan_vien.schemas import CapNhatHoSoYeuCau, NhanVienToi
from app.modules.tai_khoan.phien_http import dia_chi_ip

router = APIRouter(prefix="/noi-bo", tags=["Nhân viên"])

# Cho phép cả khi đang bị bắt đổi mật khẩu: giao diện cần đọc hồ sơ để biết phải chuyển sang màn đổi mật khẩu.
NhanVienXemHoSo = Annotated[NhanVien, Depends(yeu_cau_quyen("profile.self", "xem", ke_ca_chua_doi_mat_khau=True))]
NhanVienSuaHoSo = Annotated[NhanVien, Depends(yeu_cau_quyen("profile.self"))]


@router.get("/toi", response_model=NhanVienToi, summary="Hồ sơ và quyền của tôi (NV02)")
async def ho_so_cua_toi(nhan_vien: NhanVienXemHoSo, db: Db) -> NhanVienToi:
    return await service.dung_ho_so(db, nhan_vien)


@router.patch("/toi", response_model=NhanVienToi, summary="Cập nhật hồ sơ cá nhân (NV02)")
async def cap_nhat_ho_so(
    du_lieu: CapNhatHoSoYeuCau, request: Request, nhan_vien: NhanVienSuaHoSo, db: Db
) -> NhanVienToi:
    nhan_vien = await service.cap_nhat_ho_so(db, nhan_vien, du_lieu, ip=dia_chi_ip(request))
    return await service.dung_ho_so(db, nhan_vien)

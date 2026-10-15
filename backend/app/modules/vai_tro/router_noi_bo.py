"""Vai trò và phân quyền (AD18): `/api/v1/noi-bo/vai-tro`. Cần `role.manage`."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request

from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.models.he_thong import NhanVien
from app.modules.tai_khoan.phien_http import dia_chi_ip
from app.modules.vai_tro import service
from app.modules.vai_tro.schemas import CapNhatQuyenYeuCau, VaiTroChiTiet, VaiTroTomTat

router = APIRouter(prefix="/noi-bo/vai-tro", tags=["Vai trò và phân quyền"])

PhanQuyenXem = Annotated[NhanVien, Depends(yeu_cau_quyen("role.manage", "xem"))]
PhanQuyenSua = Annotated[NhanVien, Depends(yeu_cau_quyen("role.manage"))]
MaVaiTroPath = Annotated[str, Path(min_length=1, max_length=30, pattern=r"^[A-Z_]+$")]


@router.get("", response_model=list[VaiTroTomTat], summary="Danh sách vai trò (AD18)")
async def danh_sach(actor: PhanQuyenXem, db: Db):
    return await service.danh_sach(db)


@router.get("/{ma}", response_model=VaiTroChiTiet, summary="Ma trận quyền của một vai trò (AD18)")
async def chi_tiet(ma: MaVaiTroPath, actor: PhanQuyenXem, db: Db):
    return await service.chi_tiet(db, ma)


@router.put("/{ma}/quyen", response_model=VaiTroChiTiet, summary="Thay toàn bộ quyền của vai trò (AD18)")
async def cap_nhat_quyen(ma: MaVaiTroPath, du_lieu: CapNhatQuyenYeuCau, request: Request, actor: PhanQuyenSua, db: Db):
    """Mã quyền không có trong `quyen` bị gỡ. ADMIN không sửa được; `profile.self` bắt buộc ở mức đầy đủ."""
    return await service.cap_nhat_quyen(db, actor, ma, du_lieu.quyen, ip=dia_chi_ip(request))

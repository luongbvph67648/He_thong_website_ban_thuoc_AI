"""Cấu hình hệ thống của Admin (AD08): `/api/v1/noi-bo/cau-hinh`. Cần `config.manage`."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request

from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.models.he_thong import NhanVien
from app.modules.he_thong import cau_hinh_service
from app.modules.he_thong.schemas import CauHinhCapNhat, CauHinhDoc
from app.modules.tai_khoan.phien_http import dia_chi_ip

router = APIRouter(prefix="/noi-bo/cau-hinh", tags=["Cấu hình hệ thống"])

CauHinhXem = Annotated[NhanVien, Depends(yeu_cau_quyen("config.manage", "xem"))]
CauHinhSua = Annotated[NhanVien, Depends(yeu_cau_quyen("config.manage"))]
KhoaPath = Annotated[str, Path(min_length=1, max_length=80, pattern=r"^[a-z0-9_]+$")]


@router.get("", response_model=list[CauHinhDoc], summary="Danh sách cấu hình hệ thống (AD08)")
async def danh_sach(actor: CauHinhXem, db: Db):
    return await cau_hinh_service.danh_sach(db)


@router.put("/{khoa}", response_model=CauHinhDoc, summary="Đặt giá trị của một khóa cấu hình (AD08)")
async def cap_nhat(khoa: KhoaPath, du_lieu: CauHinhCapNhat, request: Request, actor: CauHinhSua, db: Db):
    """Giá trị được kiểm tra kiểu và khoảng theo từng khóa; `phien_ban` phải là bản vừa đọc, nếu không là 409."""
    return await cau_hinh_service.cap_nhat(db, actor, khoa, du_lieu.gia_tri, du_lieu.phien_ban, ip=dia_chi_ip(request))

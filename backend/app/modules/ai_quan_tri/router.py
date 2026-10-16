"""Quản trị AI: cấu hình (AD09, `ai.config`) và kho tri thức (AD10, `ai.knowledge.sync`)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core.db import Db
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_quyen import dam_bao_la_admin, yeu_cau_quyen
from app.models.he_thong import NhanVien
from app.modules.ai_quan_tri import cau_hinh_ai, tri_thuc
from app.modules.ai_quan_tri.cau_hinh_ai import CauHinhAiDoc, CauHinhAiSua
from app.modules.ai_quan_tri.tri_thuc import KetQuaDongBo, ThongKeTriThuc
from app.modules.tai_khoan.phien_http import dia_chi_ip

router = APIRouter(tags=["Quản trị AI"])
CauHinhXem = Annotated[NhanVien, Depends(yeu_cau_quyen("ai.config", "xem"))]
CauHinhGhi = Annotated[NhanVien, Depends(yeu_cau_quyen("ai.config"))]
TriThucXem = Annotated[NhanVien, Depends(yeu_cau_quyen("ai.knowledge.sync", "xem"))]
TriThucGhi = Annotated[NhanVien, Depends(yeu_cau_quyen("ai.knowledge.sync"))]


@router.get("/noi-bo/cau-hinh-ai", response_model=CauHinhAiDoc, summary="Cấu hình AI (AD09)")
async def lay_cau_hinh(nv: CauHinhXem, db: Db):
    return await cau_hinh_ai.lay(db)


@router.put("/noi-bo/cau-hinh-ai", response_model=CauHinhAiDoc, summary="Sửa cấu hình AI (AD09)")
async def sua_cau_hinh(vao: CauHinhAiSua, nv: CauHinhGhi, db: Db, request: Request):
    return await cau_hinh_ai.cap_nhat(db, nv, vao, ip=dia_chi_ip(request))


@router.get("/noi-bo/tri-thuc", response_model=ThongKeTriThuc, summary="Thống kê kho tri thức AI (AD10)")
async def thong_ke(nv: TriThucXem, db: Db):
    return await tri_thuc.thong_ke(db)


@router.post("/noi-bo/tri-thuc/dong-bo", response_model=KetQuaDongBo, summary="Đồng bộ kho tri thức AI (AD10)")
async def dong_bo(nv: TriThucGhi, db: Db, request: Request):
    await dam_bao_la_admin(db, nv)
    kq = await tri_thuc.dong_bo(db)
    await ghi_nhat_ky(
        db, nhan_vien_id=nv.id, hanh_dong="dong_bo", bang="tai_lieu_tri_thuc", ban_ghi_id=None,
        gia_tri_moi=kq.model_dump(), ip=dia_chi_ip(request),
    )  # fmt: skip
    return kq

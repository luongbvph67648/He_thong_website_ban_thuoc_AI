"""Duyệt bài viết sức khỏe (DS10): `/api/v1/noi-bo/bai-viet-cho-duyet` (spec 06 mục 3.12). Cần `content.approve`."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.core.phan_trang import PhanTrang, Trang, tao_trang
from app.core.tham_so import IdInt, tu_khoa_tim
from app.models.he_thong import NhanVien
from app.modules.chuyen_mon import bai_viet_duyet as dich_vu
from app.modules.chuyen_mon.schemas_bai_viet import BaiVietChiTiet, BaiVietTomTat, DuyetBaiViet
from app.modules.tai_khoan.phien_http import dia_chi_ip

router = APIRouter(prefix="/noi-bo/bai-viet-cho-duyet", tags=["Duyệt bài viết sức khỏe"])

BaiVietXem = Annotated[NhanVien, Depends(yeu_cau_quyen("content.approve", "xem"))]
BaiVietDuyet = Annotated[NhanVien, Depends(yeu_cau_quyen("content.approve"))]


@router.get("", response_model=Trang[BaiVietTomTat], summary="Bài viết sức khỏe chờ duyệt (DS10)")
async def danh_sach(
    actor: BaiVietXem,
    db: Db,
    tp: PhanTrang,
    q: tu_khoa_tim("Tìm theo tiêu đề (không phân biệt dấu)") = None,  # type: ignore[valid-type]
):
    dong, tong = await dich_vu.danh_sach_cho_duyet(db, q=q, tp=tp)
    return tao_trang(dong, tong, tp)


@router.get("/{bai_viet_id}", response_model=BaiVietChiTiet, summary="Nội dung một bài viết cần duyệt")
async def chi_tiet(bai_viet_id: IdInt, actor: BaiVietXem, db: Db):
    return await dich_vu.lay(db, bai_viet_id)


@router.post("/{bai_viet_id}/duyet", response_model=BaiVietChiTiet, summary="Duyệt bài viết (cho phép đăng)")
async def duyet(bai_viet_id: IdInt, du_lieu: DuyetBaiViet, request: Request, actor: BaiVietDuyet, db: Db):
    return await dich_vu.duyet(db, actor, bai_viet_id, du_lieu.phien_ban, ip=dia_chi_ip(request))

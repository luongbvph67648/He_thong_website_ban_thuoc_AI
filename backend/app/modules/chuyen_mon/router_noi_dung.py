"""Nội dung chuyên môn của sản phẩm (DS10): `/api/v1/noi-bo/chuyen-mon` (spec 06 mục 3.12).

Đọc cần `content.professional.edit` mức `xem` (Admin giữ `chi_xem`); biên soạn và lưu trữ bản nháp cần mức đầy đủ;
duyệt cần `content.approve`. Mọi thao tác ghi còn đòi người thực hiện là DƯỢC SĨ (`dam_bao_la_duoc_si`).
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request

from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.core.phan_trang import PhanTrang, Trang, tao_trang
from app.core.tham_so import IdInt, tu_khoa_tim
from app.models.he_thong import NhanVien
from app.modules.chuyen_mon import noi_dung as dich_vu
from app.modules.chuyen_mon.schemas_noi_dung import DongNoiDung, NoiDungSanPham, NoiDungVao, PhienBanNoiDung
from app.modules.tai_khoan.phien_http import dia_chi_ip

router = APIRouter(prefix="/noi-bo/chuyen-mon", tags=["Nội dung chuyên môn"])

ChuyenMonXem = Annotated[NhanVien, Depends(yeu_cau_quyen("content.professional.edit", "xem"))]
ChuyenMonSoan = Annotated[NhanVien, Depends(yeu_cau_quyen("content.professional.edit"))]
ChuyenMonDuyet = Annotated[NhanVien, Depends(yeu_cau_quyen("content.approve"))]


@router.get("", response_model=Trang[DongNoiDung], summary="Sản phẩm và tình trạng nội dung chuyên môn (DS10)")
async def danh_sach(
    actor: ChuyenMonXem,
    db: Db,
    tp: PhanTrang,
    q: tu_khoa_tim("Tìm theo tên (không phân biệt dấu) hoặc SKU") = None,  # type: ignore[valid-type]
    loc: Literal["cho_duyet", "da_duyet", "chua_co_noi_dung"] | None = None,
):
    dong, tong = await dich_vu.danh_sach(db, q=q, loc=loc, tp=tp)
    return tao_trang(dong, tong, tp)


@router.get("/san-pham/{san_pham_id}", response_model=NoiDungSanPham, summary="Mọi phiên bản nội dung của một sản phẩm")
async def theo_san_pham(san_pham_id: IdInt, actor: ChuyenMonXem, db: Db):
    return await dich_vu.lay_theo_san_pham(db, san_pham_id)


@router.post(
    "/san-pham/{san_pham_id}",
    status_code=201,
    response_model=PhienBanNoiDung,
    summary="Tạo phiên bản nội dung mới (nháp)",
)
async def tao_phien_ban(san_pham_id: IdInt, du_lieu: NoiDungVao, request: Request, actor: ChuyenMonSoan, db: Db):
    return await dich_vu.tao_phien_ban(db, actor, san_pham_id, du_lieu, ip=dia_chi_ip(request))


@router.post("/{phien_ban_id}/duyet", response_model=PhienBanNoiDung, summary="Duyệt một bản nháp (hiển thị cho khách)")
async def duyet(phien_ban_id: IdInt, request: Request, actor: ChuyenMonDuyet, db: Db):
    return await dich_vu.duyet(db, actor, phien_ban_id, ip=dia_chi_ip(request))


@router.post("/{phien_ban_id}/luu-tru", response_model=PhienBanNoiDung, summary="Bỏ một bản nháp (lưu trữ)")
async def luu_tru(phien_ban_id: IdInt, request: Request, actor: ChuyenMonSoan, db: Db):
    return await dich_vu.luu_tru_ban_nhap(db, actor, phien_ban_id, ip=dia_chi_ip(request))

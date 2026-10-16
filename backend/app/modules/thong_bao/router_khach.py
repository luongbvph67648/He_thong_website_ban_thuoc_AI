"""Thông báo của khách (KTV13): `/api/v1/toi/thong-bao`. `khach_hang_id` lấy từ token."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.db import Db
from app.core.phan_quyen import khach_hien_tai
from app.core.phan_trang import PhanTrang, Trang, tao_trang
from app.core.tham_so import IdBigInt
from app.models.khach_hang import KhachHang
from app.modules.thong_bao import service
from app.modules.thong_bao.schemas import DaDocTatCa, SoChuaDoc, ThongBaoDoc

router = APIRouter(prefix="/toi/thong-bao", tags=["Thông báo của khách"])
Khach = Annotated[KhachHang, Depends(khach_hien_tai)]


@router.get("", response_model=Trang[ThongBaoDoc], summary="Thông báo của tôi (KTV13)")
async def danh_sach(
    khach: Khach, db: Db, tp: PhanTrang, da_doc: Annotated[bool | None, Query(description="true/false/bỏ trống")] = None
):
    dong, tong = await service.danh_sach_cua_khach(db, khach.id, da_doc=da_doc, tp=tp)
    return tao_trang([ThongBaoDoc.model_validate(d) for d in dong], tong, tp)


@router.get("/so-chua-doc", response_model=SoChuaDoc, summary="Số thông báo chưa đọc")
async def so_chua_doc(khach: Khach, db: Db) -> SoChuaDoc:
    return SoChuaDoc(so_chua_doc=await service.so_chua_doc_cua_khach(db, khach.id))


@router.post("/da-doc-tat-ca", response_model=DaDocTatCa, summary="Đánh dấu tất cả đã đọc")
async def da_doc_tat_ca(khach: Khach, db: Db) -> DaDocTatCa:
    return DaDocTatCa(da_cap_nhat=await service.danh_dau_tat_ca_da_doc_cua_khach(db, khach.id))


@router.post("/{thong_bao_id}/da-doc", response_model=ThongBaoDoc, summary="Đánh dấu một thông báo đã đọc")
async def da_doc(thong_bao_id: IdBigInt, khach: Khach, db: Db) -> ThongBaoDoc:
    return ThongBaoDoc.model_validate(await service.danh_dau_da_doc_cua_khach(db, khach.id, thong_bao_id))

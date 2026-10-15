"""Thông báo của nhân viên (NV02): `/api/v1/noi-bo/thong-bao`. Chỉ thấy thông báo gửi cho chính mình."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.core.phan_trang import PhanTrang, Trang, tao_trang
from app.models.he_thong import NhanVien
from app.modules.thong_bao import service
from app.modules.thong_bao.schemas import DaDocTatCa, SoChuaDoc, ThongBaoDoc

router = APIRouter(prefix="/noi-bo/thong-bao", tags=["Thông báo nội bộ"])

NhanVienXemThongBao = Annotated[NhanVien, Depends(yeu_cau_quyen("profile.self", "xem"))]
NhanVienSuaThongBao = Annotated[NhanVien, Depends(yeu_cau_quyen("profile.self"))]


@router.get("", response_model=Trang[ThongBaoDoc], summary="Thông báo của tôi (NV02)")
async def danh_sach(
    nhan_vien: NhanVienXemThongBao,
    db: Db,
    tp: PhanTrang,
    da_doc: Annotated[bool | None, Query(description="true: đã đọc, false: chưa đọc, bỏ trống: tất cả")] = None,
):
    dong, tong = await service.danh_sach_cua_nhan_vien(db, nhan_vien.id, da_doc=da_doc, tp=tp)
    return tao_trang([ThongBaoDoc.model_validate(d) for d in dong], tong, tp)


@router.get("/so-chua-doc", response_model=SoChuaDoc, summary="Số thông báo chưa đọc (chuông thông báo)")
async def so_chua_doc(nhan_vien: NhanVienXemThongBao, db: Db) -> SoChuaDoc:
    return SoChuaDoc(so_chua_doc=await service.so_chua_doc(db, nhan_vien.id))


@router.post("/da-doc-tat-ca", response_model=DaDocTatCa, summary="Đánh dấu tất cả đã đọc")
async def da_doc_tat_ca(nhan_vien: NhanVienSuaThongBao, db: Db) -> DaDocTatCa:
    return DaDocTatCa(da_cap_nhat=await service.danh_dau_tat_ca_da_doc(db, nhan_vien.id))


@router.post("/{thong_bao_id}/da-doc", response_model=ThongBaoDoc, summary="Đánh dấu một thông báo đã đọc")
async def da_doc(thong_bao_id: int, nhan_vien: NhanVienSuaThongBao, db: Db) -> ThongBaoDoc:
    return ThongBaoDoc.model_validate(await service.danh_dau_da_doc(db, nhan_vien.id, thong_bao_id))

"""Xác nhận hoàn tiền (AD17): `/noi-bo/hoan-tien`, mã quyền `refund.confirm` (Admin)."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.core import luu_tru
from app.core.db import Db
from app.core.loi import LoiNghiepVu
from app.core.phan_quyen import yeu_cau_quyen
from app.core.tham_so import IdInt
from app.models.enums import TrangThaiGiaoDich
from app.models.he_thong import NhanVien
from app.modules.hoan_tien import dich_vu
from app.modules.hoan_tien.schemas import HoanTienRa

router = APIRouter(prefix="/noi-bo/hoan-tien", tags=["Hoàn tiền"])
Admin = Annotated[NhanVien, Depends(yeu_cau_quyen("refund.confirm"))]
TOI_DA_CHUNG_TU_BYTE = luu_tru.TOI_DA_ANH_BYTE


@router.get("", response_model=list[HoanTienRa], summary="Giao dịch hoàn tiền (AD17)")
async def danh_sach(nv: Admin, db: Db, trang_thai: TrangThaiGiaoDich | None = None):
    return await dich_vu.danh_sach(db, nv, trang_thai)


@router.post(
    "/{gd_id}/xac-nhan",
    response_model=HoanTienRa,
    summary="Xác nhận hoàn tiền: gọi cổng (VNPay/MoMo) hoặc đính kèm chứng từ chuyển khoản (AD17)",
)
async def xac_nhan(
    gd_id: IdInt,
    nv: Admin,
    db: Db,
    chung_tu: Annotated[UploadFile | None, File(description="Ảnh chứng từ chuyển khoản (jpeg/png/webp, 5 MB)")] = None,
):
    goi = None
    if chung_tu is not None:
        nd = await chung_tu.read(TOI_DA_CHUNG_TU_BYTE + 1)
        kieu = luu_tru.nhan_dang_tep(nd)
        if kieu is None or kieu == "video/mp4" or len(nd) > TOI_DA_CHUNG_TU_BYTE:
            raise LoiNghiepVu(
                "DU_LIEU_KHONG_HOP_LE",
                "Dữ liệu không hợp lệ",
                chi_tiet=[{"truong": "chung_tu", "loi": "Chỉ nhận ảnh jpeg, png, webp tối đa 5 MB"}],
            )
        goi = (nd, kieu)
    return await dich_vu.xac_nhan(db, nv, gd_id, goi)

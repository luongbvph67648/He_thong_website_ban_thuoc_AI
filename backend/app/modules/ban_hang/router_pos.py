"""Bán tại quầy POS (DS08): `/api/v1/noi-bo/pos/...`, mã quyền `pos.sell`."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, Query, UploadFile

from app.core import idempotency, luu_tru
from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.core.tham_so import KHONG_NUL, IdInt
from app.models.he_thong import NhanVien
from app.modules.ban_hang import pos
from app.modules.ban_hang.schemas_pos import (
    CanhBaoPosRa,
    CanhBaoPosVao,
    DonPosRa,
    DonPosVao,
    HoaDonRa,
    SanPhamPos,
    YeuCauQuayRa,
    YeuCauQuayVao,
)

router = APIRouter(tags=["Bán tại quầy (POS)"])
Pos = Annotated[NhanVien, Depends(yeu_cau_quyen("pos.sell"))]


@router.get("/noi-bo/pos/san-pham", response_model=list[SanPhamPos], summary="Tìm sản phẩm hoặc quét mã vạch (DS08)")
async def tim_san_pham(nv: Pos, db: Db, q: Annotated[str, Query(max_length=100, pattern=KHONG_NUL)] = ""):
    return await pos.tim_san_pham(db, nv, q)


@router.post(
    "/noi-bo/pos/canh-bao", response_model=CanhBaoPosRa, summary="Cảnh báo tương tác, dị ứng của giỏ POS (DS08)"
)
async def canh_bao(vao: CanhBaoPosVao, nv: Pos, db: Db):
    return await pos.tinh_canh_bao(db, nv, vao)


@router.post(
    "/noi-bo/pos/don-thuoc",
    response_model=YeuCauQuayRa,
    status_code=201,
    summary="Lập yêu cầu đơn thuốc kênh tại quầy: ảnh đơn và người bệnh (DS08)",
)
async def lap_yeu_cau(
    nv: Pos,
    db: Db,
    anh: Annotated[list[UploadFile], File(description="1 đến 5 ảnh đơn thuốc, mỗi ảnh tối đa 5 MB")],
    ho_ten: Annotated[str, Form(min_length=1, max_length=150, pattern=KHONG_NUL)],
    tuoi_hoac_nam_sinh: Annotated[str | None, Form(max_length=20, pattern=KHONG_NUL)] = None,
    so_dien_thoai: Annotated[str | None, Form(max_length=30)] = None,
    ghi_chu: Annotated[str | None, Form(max_length=500, pattern=KHONG_NUL)] = None,
):
    ds_anh = [await f.read(luu_tru.TOI_DA_ANH_BYTE + 1) for f in anh]
    vao = YeuCauQuayVao(
        ho_ten=ho_ten, tuoi_hoac_nam_sinh=tuoi_hoac_nam_sinh, so_dien_thoai=so_dien_thoai or None, ghi_chu=ghi_chu
    )
    return await pos.tao_yeu_cau_quay(db, nv, vao, ds_anh)


@router.post("/noi-bo/pos/don", response_model=DonPosRa, status_code=201, summary="Bán hàng, thu tiền, xuất kho (DS08)")
async def ban(
    vao: DonPosVao,
    nv: Pos,
    db: Db,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    return await pos.ban_hang(db, nv, vao, idempotency.doc_khoa(idempotency_key))


@router.get("/noi-bo/pos/don/{don_id}/hoa-don", response_model=HoaDonRa, summary="In lại hóa đơn (DS08)")
async def hoa_don(don_id: IdInt, nv: Pos, db: Db):
    return await pos.hoa_don(db, nv, don_id)

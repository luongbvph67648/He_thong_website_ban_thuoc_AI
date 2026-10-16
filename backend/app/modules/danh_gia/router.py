"""Đánh giá (KTV10), hỏi đáp (KTV15) và kiểm duyệt (DS11)."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile

from app.core.db import Db
from app.core.phan_quyen import khach_hien_tai, yeu_cau_quyen
from app.core.phan_trang import PhanTrang, Trang
from app.core.tham_so import KHONG_NUL, IdInt
from app.models.he_thong import NhanVien
from app.models.khach_hang import KhachHang
from app.modules.danh_gia import dich_vu
from app.modules.danh_gia.schemas import (
    DanhGiaCuaToi,
    DanhGiaNoiBo,
    DongCoTheDanhGia,
    HienThiVao,
    HoiDapCongKhai,
    HoiDapCuaToi,
    HoiDapNoiBo,
    HoiVao,
    PhanHoiVao,
    TraLoiVao,
)

router = APIRouter(tags=["Đánh giá và hỏi đáp"])
Khach = Annotated[KhachHang, Depends(khach_hien_tai)]
KiemDuyetDanhGia = Annotated[NhanVien, Depends(yeu_cau_quyen("review.moderate"))]
TraLoiHoiDap = Annotated[NhanVien, Depends(yeu_cau_quyen("qa.answer"))]
GOC_DG = "/noi-bo/kiem-duyet/danh-gia"
GOC_HD = "/noi-bo/kiem-duyet/hoi-dap"


@router.get("/toi/danh-gia/cho", response_model=list[DongCoTheDanhGia], summary="Dòng đơn có thể đánh giá (KTV10)")
async def cho_danh_gia(khach: Khach, db: Db):
    return await dich_vu.dong_co_the_danh_gia(db, khach)


@router.get("/toi/danh-gia", response_model=list[DanhGiaCuaToi], summary="Đánh giá của tôi (KTV10)")
async def danh_gia_cua_toi(khach: Khach, db: Db):
    return await dich_vu.danh_gia_cua_toi(db, khach)


@router.post("/toi/danh-gia", response_model=DanhGiaCuaToi, status_code=201, summary="Đánh giá một dòng đơn (KTV10)")
async def danh_gia(
    khach: Khach,
    db: Db,
    ct_don_hang_id: Annotated[int, Form(ge=1, le=2_147_483_647)],
    so_sao: Annotated[int, Form(ge=1, le=5)],
    noi_dung: Annotated[str | None, Form(max_length=2000, pattern=KHONG_NUL)] = None,
    tep: Annotated[list[UploadFile] | None, File(description="Tối đa 3 ảnh jpeg/png/webp, mỗi ảnh 5 MB")] = None,
):
    nd = [await f.read() for f in tep or []]
    return await dich_vu.tao_danh_gia(db, khach, ct_don_hang_id, so_sao, noi_dung, nd)


@router.get("/san-pham/{slug}/hoi-dap", response_model=Trang[HoiDapCongKhai], summary="Hỏi đáp của sản phẩm (KTV15)")
async def hoi_dap_cong_khai(slug: str, db: Db, tp: PhanTrang):
    return await dich_vu.hoi_dap_cong_khai(db, slug[:200], tp)


@router.post(
    "/san-pham/{slug}/hoi-dap", response_model=HoiDapCuaToi, status_code=201, summary="Đặt câu hỏi về sản phẩm (KTV15)"
)
async def hoi(slug: str, vao: HoiVao, khach: Khach, db: Db):
    return await dich_vu.dat_cau_hoi(db, khach, slug[:200], vao.cau_hoi)


@router.get("/toi/hoi-dap", response_model=list[HoiDapCuaToi], summary="Câu hỏi của tôi (KTV15)")
async def hoi_dap_cua_toi(khach: Khach, db: Db):
    return await dich_vu.hoi_dap_cua_toi(db, khach)


@router.put("/toi/hoi-dap/{hoi_id}", response_model=HoiDapCuaToi, summary="Sửa câu hỏi chưa được trả lời (KTV15)")
async def sua(hoi_id: IdInt, vao: HoiVao, khach: Khach, db: Db):
    return await dich_vu.sua_cau_hoi(db, khach, hoi_id, vao.cau_hoi)


@router.delete("/toi/hoi-dap/{hoi_id}", status_code=204, summary="Xóa câu hỏi chưa được trả lời (KTV15)")
async def xoa(hoi_id: IdInt, khach: Khach, db: Db):
    await dich_vu.xoa_cau_hoi(db, khach, hoi_id)
    return Response(status_code=204)


@router.get(GOC_DG, response_model=Trang[DanhGiaNoiBo], summary="Đánh giá cần kiểm duyệt (DS11)")
async def ds_danh_gia(
    nv: KiemDuyetDanhGia, db: Db, tp: PhanTrang, dang_hien: bool | None = None, so_sao: int | None = None
):
    return await dich_vu.ds_danh_gia_noi_bo(db, nv, tp, dang_hien, so_sao)


@router.put(GOC_DG + "/{dg_id}/hien-thi", response_model=DanhGiaNoiBo, summary="Ẩn/hiện đánh giá (DS11)")
async def hien_thi_danh_gia(dg_id: IdInt, vao: HienThiVao, nv: KiemDuyetDanhGia, db: Db):
    return await dich_vu.dat_hien_thi_danh_gia(db, nv, dg_id, vao.dang_hien)


@router.put(GOC_DG + "/{dg_id}/phan-hoi", response_model=DanhGiaNoiBo, summary="Phản hồi đánh giá (DS11)")
async def phan_hoi(dg_id: IdInt, vao: PhanHoiVao, nv: KiemDuyetDanhGia, db: Db):
    return await dich_vu.phan_hoi_danh_gia(db, nv, dg_id, vao.phan_hoi)


@router.get(GOC_HD, response_model=Trang[HoiDapNoiBo], summary="Câu hỏi của khách (DS11)")
async def ds_hoi_dap(nv: TraLoiHoiDap, db: Db, tp: PhanTrang, chua_tra_loi: bool | None = None):
    return await dich_vu.ds_hoi_dap_noi_bo(db, nv, tp, chua_tra_loi)


@router.post(GOC_HD + "/{hoi_id}/tra-loi", response_model=HoiDapNoiBo, summary="Trả lời câu hỏi (DS11)")
async def tra_loi(hoi_id: IdInt, vao: TraLoiVao, nv: TraLoiHoiDap, db: Db):
    return await dich_vu.tra_loi_cau_hoi(db, nv, hoi_id, vao.tra_loi)


@router.put(GOC_HD + "/{hoi_id}/hien-thi", response_model=HoiDapNoiBo, summary="Ẩn/hiện câu hỏi (DS11)")
async def hien_thi_hoi_dap(hoi_id: IdInt, vao: HienThiVao, nv: TraLoiHoiDap, db: Db):
    return await dich_vu.dat_hien_thi_hoi_dap(db, nv, hoi_id, vao.dang_hien)

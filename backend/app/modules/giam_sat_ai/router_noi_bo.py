"""DS12 `/noi-bo/danh-gia-ai` (mã quyền `ai_answer.review`) và AD11 `/noi-bo/giam-sat-ai` (mã quyền `ai.monitor`)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.core.phan_trang import PhanTrang, Trang
from app.core.tham_so import IdBigInt
from app.models.he_thong import NhanVien
from app.modules.giam_sat_ai import dich_vu
from app.modules.giam_sat_ai.schemas import (
    DanhGiaDuocSiVao,
    HoiThoaiAnDanhChiTiet,
    HoiThoaiAnDanhTom,
    ThongKeAi,
    TimKiemKhongKetQua,
)

router = APIRouter(tags=["Đánh giá và giám sát AI"])
XemDanhGia = Annotated[NhanVien, Depends(yeu_cau_quyen("ai_answer.review", "xem"))]
GhiDanhGia = Annotated[NhanVien, Depends(yeu_cau_quyen("ai_answer.review"))]
GiamSat = Annotated[NhanVien, Depends(yeu_cau_quyen("ai.monitor", "xem"))]


@router.get("/noi-bo/danh-gia-ai", response_model=Trang[HoiThoaiAnDanhTom], summary="Hội thoại AI bị gắn cờ (DS12)")
async def ds_gan_co(nv: XemDanhGia, db: Db, tp: PhanTrang, chua_danh_gia: bool = False):
    return await dich_vu.ds_gan_co(db, tp, chua_danh_gia=chua_danh_gia)


@router.get(
    "/noi-bo/danh-gia-ai/{hoi_thoai_id}",
    response_model=HoiThoaiAnDanhChiTiet,
    summary="Nội dung hội thoại bị gắn cờ, đã ẩn danh (DS12)",
)
async def chi_tiet_gan_co(hoi_thoai_id: IdBigInt, nv: XemDanhGia, db: Db):
    return await dich_vu.chi_tiet_gan_co(db, nv, hoi_thoai_id)


@router.put(
    "/noi-bo/danh-gia-ai/{hoi_thoai_id}/tin-nhan/{tin_nhan_id}",
    response_model=HoiThoaiAnDanhChiTiet,
    summary="Đánh dấu câu trả lời AI đúng hoặc sai, ghi nội dung đúng (DS12)",
)
async def danh_gia(hoi_thoai_id: IdBigInt, tin_nhan_id: IdBigInt, vao: DanhGiaDuocSiVao, nv: GhiDanhGia, db: Db):
    return await dich_vu.danh_gia_tin_nhan(db, nv, hoi_thoai_id, tin_nhan_id, vao)


@router.get("/noi-bo/giam-sat-ai/thong-ke", response_model=ThongKeAi, summary="Thống kê AI (AD11)")
async def thong_ke(nv: GiamSat, db: Db, tu_ngay: date | None = None, den_ngay: date | None = None):
    return await dich_vu.thong_ke(db, tu_ngay=tu_ngay, den_ngay=den_ngay)


@router.get(
    "/noi-bo/giam-sat-ai/hoi-thoai", response_model=Trang[HoiThoaiAnDanhTom], summary="Hội thoại AI đã ẩn danh (AD11)"
)
async def ds_hoi_thoai(
    nv: GiamSat,
    db: Db,
    tp: PhanTrang,
    tu_ngay: date | None = None,
    den_ngay: date | None = None,
    bi_gan_co: bool | None = None,
    da_chuyen_duoc_si: bool | None = None,
):
    return await dich_vu.ds_giam_sat(
        db, tp, tu_ngay=tu_ngay, den_ngay=den_ngay, bi_gan_co=bi_gan_co, da_chuyen_duoc_si=da_chuyen_duoc_si
    )


@router.get(
    "/noi-bo/giam-sat-ai/hoi-thoai/{hoi_thoai_id}",
    response_model=HoiThoaiAnDanhChiTiet,
    summary="Nội dung một hội thoại đã ẩn danh (AD11)",
)
async def chi_tiet_hoi_thoai(hoi_thoai_id: IdBigInt, nv: GiamSat, db: Db):
    return await dich_vu.chi_tiet_giam_sat(db, hoi_thoai_id)


@router.get(
    "/noi-bo/giam-sat-ai/tim-kiem-khong-ket-qua",
    response_model=list[TimKiemKhongKetQua],
    summary="Từ khóa tìm kiếm không có kết quả (AD11)",
)
async def tim_kiem_khong_ket_qua(nv: GiamSat, db: Db, tu_ngay: date | None = None, den_ngay: date | None = None):
    return await dich_vu.tim_kiem_khong_ket_qua(db, tu_ngay=tu_ngay, den_ngay=den_ngay)

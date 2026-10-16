"""Đổi trả: khách `/toi/...` (KTV09) và dược sĩ `/noi-bo/doi-tra` (DS09, `return.review`)."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import TypeAdapter, ValidationError

from app.core.db import Db
from app.core.loi import LoiNghiepVu
from app.core.phan_quyen import khach_hien_tai, yeu_cau_quyen
from app.core.tham_so import KHONG_NUL, IdInt
from app.models.enums import LyDoDoiTra, TrangThaiDoiTra
from app.models.he_thong import NhanVien
from app.models.khach_hang import KhachHang
from app.modules.doi_tra import dich_vu, xu_ly
from app.modules.doi_tra.schemas import (
    DoiTraChiTietKhach,
    DoiTraNoiBoChiTiet,
    DoiTraNoiBoTom,
    DoiTraTom,
    DongTraVao,
    DuyetVao,
    TaiKhoanNhanHoanVao,
    TuChoiDoiTraVao,
)

router = APIRouter(tags=["Đổi trả"])
Khach = Annotated[KhachHang, Depends(khach_hien_tai)]
DuocSi = Annotated[NhanVien, Depends(yeu_cau_quyen("return.review"))]
_DONG = TypeAdapter(list[DongTraVao])


@router.post(
    "/toi/don-hang/{ma_don}/doi-tra",
    response_model=DoiTraChiTietKhach,
    status_code=201,
    summary="Gửi yêu cầu đổi trả kèm ảnh/video (KTV09)",
)
async def gui(
    ma_don: str,
    db: Db,
    khach: Khach,
    dong: Annotated[str, Form(max_length=5000, description='JSON: [{"ct_don_hang_id": 1, "so_luong": 1}]')],
    ly_do: Annotated[LyDoDoiTra, Form()],
    tep: Annotated[list[UploadFile], File(description="Ảnh jpeg/png/webp (5 MB) hoặc video mp4 (30 MB), tối đa 8 tệp")],
    mo_ta: Annotated[str | None, Form(max_length=1000, pattern=KHONG_NUL)] = None,
):
    try:
        ds_dong = _DONG.validate_json(dong)
    except (ValidationError, json.JSONDecodeError) as e:
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE",
            "Dữ liệu không hợp lệ",
            chi_tiet=[{"truong": "dong", "loi": "Danh sách dòng trả sai định dạng"}],
        ) from e
    ds_tep = [await f.read(30 * 1024 * 1024 + 1) for f in tep]
    return await dich_vu.tao_yeu_cau(db, khach, ma_don[:20], ds_dong, ly_do, mo_ta, ds_tep)


@router.get("/toi/doi-tra", response_model=list[DoiTraTom], summary="Yêu cầu đổi trả của tôi (KTV09)")
async def danh_sach_khach(db: Db, khach: Khach):
    return await dich_vu.danh_sach_khach(db, khach)


@router.get("/toi/doi-tra/{ma_yeu_cau}", response_model=DoiTraChiTietKhach, summary="Chi tiết đổi trả (KTV09)")
async def chi_tiet_khach(ma_yeu_cau: str, db: Db, khach: Khach):
    return await dich_vu.chi_tiet_khach(db, khach, ma_yeu_cau)


@router.put(
    "/toi/doi-tra/{ma_yeu_cau}/tai-khoan-nhan-hoan",
    response_model=DoiTraChiTietKhach,
    summary="Nhập tài khoản nhận hoàn tiền (đơn COD/tiền mặt) (KTV09)",
)
async def tai_khoan_hoan(ma_yeu_cau: str, vao: TaiKhoanNhanHoanVao, db: Db, khach: Khach):
    return await dich_vu.nhap_tai_khoan_hoan(db, khach, ma_yeu_cau, vao)


@router.get("/noi-bo/doi-tra", response_model=list[DoiTraNoiBoTom], summary="Yêu cầu đổi trả cần xử lý (DS09)")
async def danh_sach(nv: DuocSi, db: Db, trang_thai: TrangThaiDoiTra | None = None):
    return await xu_ly.danh_sach(db, nv, trang_thai)


@router.get("/noi-bo/doi-tra/{yc_id}", response_model=DoiTraNoiBoChiTiet, summary="Chi tiết đổi trả (DS09)")
async def chi_tiet(yc_id: IdInt, nv: DuocSi, db: Db):
    return await xu_ly.chi_tiet(db, nv, yc_id)


@router.post(
    "/noi-bo/doi-tra/{yc_id}/duyet", response_model=DoiTraNoiBoChiTiet, summary="Duyệt, tạo vận đơn trả (DS09)"
)
async def duyet(yc_id: IdInt, vao: DuyetVao, nv: DuocSi, db: Db):
    return await xu_ly.duyet(db, nv, yc_id, vao.huong_xu_ly)


@router.post("/noi-bo/doi-tra/{yc_id}/tu-choi", response_model=DoiTraNoiBoChiTiet, summary="Từ chối đổi trả (DS09)")
async def tu_choi(yc_id: IdInt, vao: TuChoiDoiTraVao, nv: DuocSi, db: Db):
    return await xu_ly.tu_choi(db, nv, yc_id, vao.ly_do)


@router.post(
    "/noi-bo/doi-tra/{yc_id}/hoan-tien", response_model=DoiTraNoiBoChiTiet, summary="Tạo giao dịch hoàn tiền (DS09)"
)
async def hoan_tien(yc_id: IdInt, nv: DuocSi, db: Db):
    return await xu_ly.tao_hoan_tien(db, nv, yc_id)


@router.post("/noi-bo/doi-tra/{yc_id}/thay-the", response_model=DoiTraNoiBoChiTiet, summary="Gửi hàng thay thế (DS09)")
async def thay_the(yc_id: IdInt, nv: DuocSi, db: Db):
    return await xu_ly.gui_hang_thay_the(db, nv, yc_id)

"""Yêu cầu tư vấn đơn thuốc: công khai `POST /don-thuoc` (KVL08, KTV07) và `/toi/don-thuoc` (KTV07)."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import TypeAdapter, ValidationError

from app.core import luu_tru
from app.core.db import Db
from app.core.loi import LoiNghiepVu
from app.core.phan_quyen import khach_hien_tai, khach_tuy_chon
from app.core.tham_so import KHONG_NUL
from app.models.khach_hang import KhachHang
from app.modules.don_thuoc import dich_vu
from app.modules.don_thuoc.schemas import YeuCauDonThuocChiTiet, YeuCauDonThuocTao, YeuCauDonThuocTom
from app.modules.tai_khoan import otp
from app.modules.tai_khoan.schemas import SoDienThoai

router = APIRouter(tags=["Đơn thuốc của khách"])
Khach = Depends(khach_hien_tai)
_SDT = TypeAdapter(SoDienThoai)


@router.post(
    "/don-thuoc",
    status_code=201,
    response_model=YeuCauDonThuocTao,
    summary="Gửi ảnh đơn thuốc nhờ dược sĩ tư vấn (KVL08, KTV07)",
)
async def gui(
    db: Db,
    anh: Annotated[list[UploadFile], File(description="1 đến 5 ảnh jpeg/png/webp, mỗi ảnh tối đa 5 MB")],
    ho_ten: Annotated[str | None, Form(max_length=150, pattern=KHONG_NUL)] = None,
    so_dien_thoai: Annotated[str | None, Form(max_length=30)] = None,
    ghi_chu: Annotated[str | None, Form(max_length=1000, pattern=KHONG_NUL)] = None,
    otp_ma: Annotated[str | None, Form(alias="otp", max_length=10)] = None,
    khach: KhachHang | None = Depends(khach_tuy_chon),
):
    """Thành viên đã đăng nhập: gắn vào tài khoản, không cần OTP. Khách vãng lai: bắt buộc `so_dien_thoai` và `otp`
    (mục đích `don_thuoc_khach`)."""
    ten = (ho_ten or (khach.ho_ten if khach else "") or "").strip()
    sdt_tho = so_dien_thoai or (khach.so_dien_thoai if khach else None)
    if not ten or not sdt_tho:
        raise LoiNghiepVu("DU_LIEU_KHONG_HOP_LE", "Cần họ tên và số điện thoại")
    try:
        sdt = _SDT.validate_python(sdt_tho)
    except ValidationError as loi:
        raise LoiNghiepVu("DU_LIEU_KHONG_HOP_LE", "Số điện thoại không hợp lệ") from loi
    ds_anh = [await f.read(luu_tru.TOI_DA_ANH_BYTE + 1) for f in anh]
    dich_vu.kiem_tra_anh(ds_anh)  # lỗi ảnh trước khi đốt lần thử OTP
    if khach is None:
        if not otp_ma:
            raise LoiNghiepVu("DU_LIEU_KHONG_HOP_LE", "Khách vãng lai cần mã OTP gửi về số điện thoại")
        kq = await otp.kiem_tra_otp(db, dich_den=sdt, muc_dich="don_thuoc_khach", ma=otp_ma)
        loi_otp = otp.loi_otp(kq)
        if loi_otp is not None:
            return loi_otp  # trả về (không raise) để bộ đếm lần thử được commit
    return await dich_vu.gui_yeu_cau(db, khach=khach, ho_ten=ten, so_dien_thoai=sdt, ghi_chu=ghi_chu, ds_anh=ds_anh)


@router.get("/toi/don-thuoc", response_model=list[YeuCauDonThuocTom], summary="Đơn thuốc của tôi (KTV07)")
async def danh_sach(db: Db, khach: KhachHang = Khach):
    return await dich_vu.danh_sach(db, khach)


@router.get("/toi/don-thuoc/{ma_yeu_cau}", response_model=YeuCauDonThuocChiTiet, summary="Chi tiết yêu cầu (KTV07)")
async def chi_tiet(ma_yeu_cau: str, db: Db, khach: KhachHang = Khach):
    return await dich_vu.chi_tiet(db, khach, ma_yeu_cau[:20])


@router.post("/toi/don-thuoc/{ma_yeu_cau}/huy", response_model=YeuCauDonThuocTom, summary="Hủy yêu cầu (KTV07)")
async def huy(ma_yeu_cau: str, db: Db, khach: KhachHang = Khach):
    return await dich_vu.huy(db, khach, ma_yeu_cau[:20])

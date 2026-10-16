"""KVL06: tra cứu thuốc bằng ảnh. Công khai, giới hạn lượt theo IP, phiên và toàn hệ thống."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Header, Request, UploadFile
from pydantic import ValidationError

from app.ai import claude, doc_anh
from app.ai.anh import AnhKhongDoc, chuan_bi_anh
from app.core import luu_tru
from app.core.db import TaoPhien, lay_tao_phien
from app.core.gioi_han import GioiHanCuaSoTruot, lay_bo_gioi_han_tra_anh
from app.core.loi import LoiNghiepVu
from app.modules.ai_quan_tri import cau_hinh_ai
from app.modules.tai_khoan.phien_http import dia_chi_ip
from app.modules.tra_cuu_anh import dich_vu
from app.modules.tra_cuu_anh.schemas import TraCuuAnhRa

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Tra cứu thuốc bằng ảnh"])

TOI_DA_MOI_IP = 10
TOI_DA_MOI_PHIEN = 5
TOI_DA_MOI_NGAY = 500
CUA_SO_GIAY = 600
CUA_SO_NGAY_GIAY = 86_400
THONG_DIEP_GIOI_HAN = "Bạn tra cứu ảnh quá nhiều, vui lòng chờ một lúc rồi thử lại"


def _gioi_han(bo: GioiHanCuaSoTruot, ip: str, ma_phien: str | None) -> None:
    quy_tac = [(f"anh-ip:{ip}", TOI_DA_MOI_IP, CUA_SO_GIAY), ("anh-ngay", TOI_DA_MOI_NGAY, CUA_SO_NGAY_GIAY)]
    if ma_phien:
        quy_tac.insert(1, (f"anh-phien:{ma_phien[:64]}", TOI_DA_MOI_PHIEN, CUA_SO_GIAY))
    for khoa, toi_da, cua_so in quy_tac:
        cho = bo.thu(khoa, toi_da, cua_so)
        if cho is not None:
            giay = int(cho) + 1
            raise LoiNghiepVu(
                "QUA_GIOI_HAN",
                THONG_DIEP_GIOI_HAN,
                chi_tiet={"thu_lai_sau_giay": giay},
                headers={"Retry-After": str(giay)},
            )


def _loi_anh(thong_diep: str) -> LoiNghiepVu:
    return LoiNghiepVu("DU_LIEU_KHONG_HOP_LE", thong_diep, chi_tiet=[{"truong": "anh", "loi": thong_diep}])


@router.post("/tra-cuu-anh", response_model=TraCuuAnhRa, summary="Tra cứu thuốc bằng ảnh hộp thuốc (KVL06, AI05)")
async def tra_cuu_anh(
    request: Request,
    anh: Annotated[UploadFile, File(description="Ảnh jpeg/png/webp tối đa 5 MB")],
    bo_gioi_han: Annotated[GioiHanCuaSoTruot, Depends(lay_bo_gioi_han_tra_anh)],
    tao_phien: Annotated[TaoPhien, Depends(lay_tao_phien)],
    ma_phien: Annotated[str | None, Header(alias="X-Ma-Phien", max_length=64)] = None,
):
    """Kiểm tra và thu nhỏ ảnh TRƯỚC khi tính lượt và gọi Claude; hai pha DB riêng, không giữ kết nối khi chờ AI."""
    noi_dung = await anh.read(luu_tru.TOI_DA_ANH_BYTE + 1)
    if not noi_dung or len(noi_dung) > luu_tru.TOI_DA_ANH_BYTE:
        raise _loi_anh("Ảnh tối đa 5 MB" if noi_dung else "Cần một ảnh")
    if luu_tru.nhan_dang_anh(noi_dung) is None:
        raise _loi_anh("Chỉ nhận ảnh jpeg, png hoặc webp")
    try:
        anh_b64 = chuan_bi_anh(noi_dung)
    except AnhKhongDoc as e:
        raise _loi_anh(str(e)) from e
    _gioi_han(bo_gioi_han, dia_chi_ip(request), ma_phien)
    async with tao_phien() as db:
        bat = await cau_hinh_ai.module_bat(db, "tra_anh")
    loi_ai = LoiNghiepVu("LOI_DOI_TAC", "Chưa đọc được ảnh lúc này, vui lòng thử lại sau hoặc tìm thuốc theo tên")
    if not bat:
        raise LoiNghiepVu("LOI_DOI_TAC", "Tính năng tra cứu bằng ảnh đang tạm tắt, vui lòng tìm thuốc theo tên")
    su_dung = claude.SuDung()
    try:
        doc = await doc_anh.doc_hop_thuoc(anh_b64, su_dung)
    except (claude.AiLoi, claude.AiTuChoi, ValidationError) as e:
        logger.warning("AI05 không đọc được ảnh: %s", type(e).__name__)
        raise loi_ai from e
    logger.info("AI05 xong", extra={"token": su_dung.tong_token, "chi_phi_usd": str(su_dung.chi_phi_usd())})
    async with tao_phien() as db:
        return await dich_vu.doi_chieu(db, doc)

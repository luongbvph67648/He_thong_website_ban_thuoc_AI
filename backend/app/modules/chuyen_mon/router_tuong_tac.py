"""Tương tác giữa các hoạt chất (DS10): `/api/v1/noi-bo/tuong-tac` (spec 06 mục 3.12), `content.professional.edit`."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.core.phan_trang import PhanTrang, Trang, tao_trang
from app.core.tham_so import IdInt, tu_khoa_tim
from app.models.enums import MucDoTuongTac
from app.models.he_thong import NhanVien
from app.modules.chuyen_mon import tuong_tac as dich_vu
from app.modules.chuyen_mon.schemas_tuong_tac import PhienBan, TuongTacDoc, TuongTacSua, TuongTacTao
from app.modules.tai_khoan.phien_http import dia_chi_ip

router = APIRouter(prefix="/noi-bo/tuong-tac", tags=["Tương tác hoạt chất"])

TuongTacXem = Annotated[NhanVien, Depends(yeu_cau_quyen("content.professional.edit", "xem"))]
TuongTacGhi = Annotated[NhanVien, Depends(yeu_cau_quyen("content.professional.edit"))]


@router.get("", response_model=Trang[TuongTacDoc], summary="Danh sách tương tác hoạt chất (DS10)")
async def danh_sach(
    actor: TuongTacXem,
    db: Db,
    tp: PhanTrang,
    q: tu_khoa_tim("Tìm theo tên một trong hai hoạt chất (không phân biệt dấu)") = None,  # type: ignore[valid-type]
    muc_do: MucDoTuongTac | None = None,
):
    dong, tong = await dich_vu.danh_sach(db, q=q, muc_do=muc_do, tp=tp)
    return tao_trang(dong, tong, tp)


@router.get("/{hoat_chat_1_id}/{hoat_chat_2_id}", response_model=TuongTacDoc, summary="Chi tiết một cặp (thứ tự tùy ý)")
async def chi_tiet(hoat_chat_1_id: IdInt, hoat_chat_2_id: IdInt, actor: TuongTacXem, db: Db):
    return await dich_vu.lay(db, hoat_chat_1_id, hoat_chat_2_id)


@router.post("", status_code=201, response_model=TuongTacDoc, summary="Thêm tương tác cho một cặp hoạt chất")
async def tao(du_lieu: TuongTacTao, request: Request, actor: TuongTacGhi, db: Db):
    return await dich_vu.tao(db, actor, du_lieu, ip=dia_chi_ip(request))


@router.put("/{hoat_chat_1_id}/{hoat_chat_2_id}", response_model=TuongTacDoc, summary="Sửa tương tác của một cặp")
async def sua(
    hoat_chat_1_id: IdInt, hoat_chat_2_id: IdInt, du_lieu: TuongTacSua, request: Request, actor: TuongTacGhi, db: Db
):
    return await dich_vu.sua(db, actor, hoat_chat_1_id, hoat_chat_2_id, du_lieu, ip=dia_chi_ip(request))


@router.delete("/{hoat_chat_1_id}/{hoat_chat_2_id}", status_code=204, summary="Xóa tương tác của một cặp")
async def xoa(
    hoat_chat_1_id: IdInt,
    hoat_chat_2_id: IdInt,
    phien_ban: Annotated[PhienBan, Query(description="`phien_ban` lấy từ `GET` (khóa lạc quan)")],
    request: Request,
    actor: TuongTacGhi,
    db: Db,
):
    await dich_vu.xoa(db, actor, hoat_chat_1_id, hoat_chat_2_id, phien_ban, ip=dia_chi_ip(request))
    return Response(status_code=204)

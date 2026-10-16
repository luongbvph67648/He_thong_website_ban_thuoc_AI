"""Giỏ hàng: `/api/v1/toi/gio-hang` (khách thành viên) và `/api/v1/gio-hang` (công khai, giỏ localStorage)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.core.db import Db
from app.core.phan_quyen import khach_hien_tai
from app.core.tham_so import IdInt
from app.models.khach_hang import KhachHang
from app.modules.gio_hang import dich_vu
from app.modules.gio_hang.schemas import (
    DanhSachDongVao,
    DongVao,
    GioHangRa,
    KetQuaGop,
    MuaKem,
    SuaDong,
)

router = APIRouter(tags=["Giỏ hàng"])
Khach = Depends(khach_hien_tai)


@router.get("/toi/gio-hang", response_model=GioHangRa, summary="Giỏ hàng của tôi (KVL07)")
async def xem(db: Db, khach: KhachHang = Khach):
    return await dich_vu.xem_gio(db, khach)


@router.post("/toi/gio-hang/dong", response_model=GioHangRa, summary="Thêm vào giỏ, cộng dồn (KVL07)")
async def them(vao: DongVao, db: Db, khach: KhachHang = Khach):
    return await dich_vu.them_dong(db, khach, vao)


@router.put("/toi/gio-hang/gop", response_model=KetQuaGop, summary="Gộp giỏ localStorage khi đăng nhập (KVL07)")
async def gop(vao: DanhSachDongVao, db: Db, khach: KhachHang = Khach):
    return await dich_vu.gop_gio(db, khach, vao.dong)


@router.put("/toi/gio-hang/dong/{dong_id}", response_model=GioHangRa, summary="Đổi số lượng hoặc đơn vị (KVL07)")
async def sua(dong_id: IdInt, vao: SuaDong, db: Db, khach: KhachHang = Khach):
    return await dich_vu.sua_dong(db, khach, dong_id, vao.so_luong, vao.don_vi_id)


@router.delete("/toi/gio-hang/dong/{dong_id}", response_model=GioHangRa, summary="Xóa một dòng giỏ (KVL07)")
async def xoa_dong(dong_id: IdInt, db: Db, khach: KhachHang = Khach):
    return await dich_vu.xoa_dong(db, khach, dong_id)


@router.delete("/toi/gio-hang", status_code=204, summary="Xóa hết giỏ (KVL07)")
async def xoa_het(db: Db, khach: KhachHang = Khach):
    await dich_vu.xoa_het(db, khach)
    return Response(status_code=204)


@router.post("/gio-hang/xem", response_model=GioHangRa, summary="Dựng giỏ localStorage của khách vãng lai (KVL07)")
async def xem_vang_lai(vao: DanhSachDongVao, db: Db):
    return await dich_vu.dung_gio(db, [(None, d.san_pham_id, d.don_vi_id, d.so_luong) for d in vao.dong])


@router.get("/gio-hang/mua-kem", response_model=list[MuaKem], summary='Gợi ý "Thường được mua cùng" (KVL07)')
async def mua_kem(
    db: Db,
    san_pham_id: Annotated[
        list[Annotated[int, Query(ge=1, le=2_147_483_647)]], Query(max_length=dich_vu.TOI_DA_ID_MUA_KEM)
    ] = [],  # noqa: B006
):
    return await dich_vu.mua_kem(db, set(san_pham_id))

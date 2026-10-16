"""Tồn kho (KHO05) và cảnh báo kho (KHO06): `/api/v1/noi-bo/ton-kho`, `/api/v1/noi-bo/canh-bao-kho`."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.db import Db
from app.core.phan_quyen import quyen_cua_vai_tro, yeu_cau_quyen
from app.core.phan_trang import PhanTrang, Trang
from app.core.tham_so import IdInt
from app.models.enums import TrangThaiLo
from app.models.he_thong import NhanVien
from app.modules.kho import canh_bao as dich_vu_canh_bao
from app.modules.kho import ton_kho_tra_cuu as dich_vu
from app.modules.kho.ton_kho_tra_cuu import TonLo, TonSanPham

router = APIRouter(tags=["Tồn kho"])
XemTon = Annotated[NhanVien, Depends(yeu_cau_quyen("stock.view", "xem"))]
XemCanhBao = Annotated[NhanVien, Depends(yeu_cau_quyen("stock.alert.view", "xem"))]


async def _xem_day_du(db: Db, actor: NhanVien) -> bool:
    """Giá nhập, số đang giữ và biệt trữ chỉ cho vai trò có quyền nhập kho (dược sĩ chỉ thấy tồn khả dụng)."""
    return "stock.import" in await quyen_cua_vai_tro(db, actor.vai_tro_id)


@router.get("/noi-bo/ton-kho", response_model=Trang[TonSanPham], summary="Tồn kho theo sản phẩm (KHO05)")
async def ton_theo_san_pham(
    actor: XemTon,
    db: Db,
    tp: PhanTrang,
    q: Annotated[str | None, Query(max_length=100)] = None,
    chi_thap: bool = False,
):
    return await dich_vu.danh_sach(db, q, chi_thap, tp, xem_day_du=await _xem_day_du(db, actor))


@router.get("/noi-bo/ton-kho/{san_pham_id}/lo", response_model=list[TonLo], summary="Các lô của sản phẩm (KHO05)")
async def ton_theo_lo(san_pham_id: IdInt, actor: XemTon, db: Db):
    return await dich_vu.cac_lo(db, san_pham_id, xem_day_du=await _xem_day_du(db, actor))


class SanPhamThap(BaseModel):
    san_pham_id: int
    sku: str
    ten: str
    ton_kha_dung: int
    ton_toi_thieu: int


class LoCanhBao(BaseModel):
    lo_id: int
    san_pham_id: int
    sku: str
    ten_san_pham: str
    so_lo: str
    han_su_dung: date
    trang_thai: TrangThaiLo
    so_luong_ton: int
    so_luong_biet_tru: int


class NhomCanhBao[T](BaseModel):
    tong: int
    """Tổng số mục; `du_lieu` cắt ở 200 mục đầu."""
    du_lieu: list[T]


class CanhBaoKhoRa(BaseModel):
    ton_thap: NhomCanhBao[SanPhamThap]
    can_han: NhomCanhBao[LoCanhBao]
    het_han: NhomCanhBao[LoCanhBao]


def _lo(lo, sp) -> LoCanhBao:
    return LoCanhBao(
        lo_id=lo.id,
        san_pham_id=sp.id,
        sku=sp.sku,
        ten_san_pham=sp.ten,
        so_lo=lo.so_lo,
        han_su_dung=lo.han_su_dung,
        trang_thai=lo.trang_thai,
        so_luong_ton=lo.so_luong_ton,
        so_luong_biet_tru=lo.so_luong_biet_tru,
    )


@router.get("/noi-bo/canh-bao-kho", response_model=CanhBaoKhoRa, summary="Cảnh báo tồn thấp, cận hạn, hết hạn (KHO06)")
async def canh_bao_kho(actor: XemCanhBao, db: Db):
    cb = await dich_vu_canh_bao.lay_canh_bao(db)
    return CanhBaoKhoRa(
        ton_thap=NhomCanhBao(
            tong=cb.tong_ton_thap,
            du_lieu=[
                SanPhamThap(san_pham_id=sp.id, sku=sp.sku, ten=sp.ten, ton_kha_dung=kd, ton_toi_thieu=sp.ton_toi_thieu)
                for sp, kd in cb.ton_thap
            ],
        ),
        can_han=NhomCanhBao(tong=cb.tong_can_han, du_lieu=[_lo(lo, sp) for lo, sp in cb.can_han]),
        het_han=NhomCanhBao(tong=cb.tong_het_han, du_lieu=[_lo(lo, sp) for lo, sp in cb.het_han]),
    )

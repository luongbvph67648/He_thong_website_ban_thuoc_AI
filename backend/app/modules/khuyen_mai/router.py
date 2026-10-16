"""Khuyến mãi: Admin `/api/v1/noi-bo/khuyen-mai` (AD06) và khách `/api/v1/toi/ma-giam-gia` (KTV04)."""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select

from app.core.db import Db
from app.core.gioi_han import GioiHanCuaSoTruot, lay_bo_gioi_han_ma_giam_gia
from app.core.loi import LoiNghiepVu
from app.core.phan_quyen import khach_hien_tai, yeu_cau_quyen
from app.core.phan_trang import PhanTrang, Trang
from app.core.tham_so import IdInt
from app.models.enums import LoaiSanPham
from app.models.he_thong import NhanVien
from app.models.khach_hang import KhachHang
from app.models.san_pham import SanPham
from app.modules.cua_hang.hien_thi import nap_cay_hien_thi
from app.modules.gio_hang import dich_vu as dich_vu_gio
from app.modules.khuyen_mai import ap_dung, quan_tri
from app.modules.khuyen_mai.schemas import (
    KetQuaKiemTraMa,
    KhuyenMaiChiTiet,
    KhuyenMaiCongKhai,
    KhuyenMaiSua,
    KhuyenMaiTomTat,
    KhuyenMaiVao,
    KiemTraMaVao,
    MaRa,
    SinhMa,
    TrangThaiHieuLuc,
)
from app.modules.tai_khoan.phien_http import dia_chi_ip

router = APIRouter(tags=["Khuyến mãi"])
Xem = Annotated[NhanVien, Depends(yeu_cau_quyen("promotion.manage", "xem"))]
Ghi = Annotated[NhanVien, Depends(yeu_cau_quyen("promotion.manage"))]
KIEM_TRA_TOI_DA = 30
KIEM_TRA_CUA_SO_GIAY = 600


@router.get("/noi-bo/khuyen-mai", response_model=Trang[KhuyenMaiTomTat], summary="Danh sách khuyến mãi (AD06)")
async def ds(
    actor: Xem,
    db: Db,
    tp: PhanTrang,
    trang_thai: TrangThaiHieuLuc | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
):
    return await quan_tri.danh_sach(db, tp, trang_thai=trang_thai, q=q)


@router.post("/noi-bo/khuyen-mai", response_model=KhuyenMaiChiTiet, status_code=201, summary="Tạo khuyến mãi (AD06)")
async def tao(vao: KhuyenMaiVao, actor: Ghi, db: Db, request: Request):
    return await quan_tri.tao(db, actor, vao, dia_chi_ip(request))


@router.get("/noi-bo/khuyen-mai/{km_id}", response_model=KhuyenMaiChiTiet, summary="Chi tiết khuyến mãi (AD06)")
async def chi_tiet(km_id: IdInt, actor: Xem, db: Db):
    return await quan_tri.chi_tiet(db, km_id)


@router.put("/noi-bo/khuyen-mai/{km_id}", response_model=KhuyenMaiChiTiet, summary="Sửa khuyến mãi (AD06)")
async def sua(km_id: IdInt, vao: KhuyenMaiSua, actor: Ghi, db: Db, request: Request):
    return await quan_tri.sua(db, actor, km_id, vao, dia_chi_ip(request))


@router.delete("/noi-bo/khuyen-mai/{km_id}", status_code=204, summary="Xóa khuyến mãi chưa có đơn dùng (AD06)")
async def xoa(km_id: IdInt, actor: Ghi, db: Db, request: Request):
    await quan_tri.xoa(db, actor, km_id, dia_chi_ip(request))
    return Response(status_code=204)


@router.post(
    "/noi-bo/khuyen-mai/{km_id}/ma",
    response_model=list[MaRa],
    status_code=201,
    summary="Sinh hoặc thêm mã giảm giá (AD06)",
)
async def sinh_ma(km_id: IdInt, vao: SinhMa, actor: Ghi, db: Db, request: Request):
    return await quan_tri.sinh_ma(db, actor, km_id, vao, dia_chi_ip(request))


@router.delete("/noi-bo/khuyen-mai/{km_id}/ma/{ma_id}", status_code=204, summary="Xóa mã chưa dùng (AD06)")
async def xoa_ma(km_id: IdInt, ma_id: IdInt, actor: Ghi, db: Db, request: Request):
    await quan_tri.xoa_ma(db, actor, km_id, ma_id, dia_chi_ip(request))
    return Response(status_code=204)


async def dong_tu_gio(db: Db, khach: KhachHang) -> list[ap_dung.DongGio]:
    """Các dòng mua được trong giỏ của khách, kèm danh mục (và tổ tiên) để lọc phạm vi."""
    gio = await dich_vu_gio.xem_gio(db, khach)
    dong = [d for d in gio.dong if d.mua_duoc]
    if not dong:
        return []
    ids = [d.san_pham.id for d in dong]
    sp = {s.id: s for s in (await db.execute(select(SanPham).where(SanPham.id.in_(ids)))).scalars()}
    cay = await nap_cay_hien_thi(db)
    return [
        ap_dung.DongGio(
            khoa=i,
            san_pham_id=d.san_pham.id,
            duong_danh_muc=frozenset(x.id for x in cay.duong_dan(sp[d.san_pham.id].danh_muc_id)),
            la_ke_don=sp[d.san_pham.id].loai_san_pham == LoaiSanPham.thuoc_ke_don,
            thanh_tien_goc=Decimal(d.thanh_tien),
        )
        for i, d in enumerate(dong)
    ]


@router.post(
    "/toi/ma-giam-gia/kiem-tra", response_model=KetQuaKiemTraMa, summary="Kiểm tra mã giảm giá theo giỏ của tôi (KTV04)"
)
async def kiem_tra(
    vao: KiemTraMaVao,
    db: Db,
    bo_gioi_han: Annotated[GioiHanCuaSoTruot, Depends(lay_bo_gioi_han_ma_giam_gia)],
    khach: KhachHang = Depends(khach_hien_tai),
):
    cho = bo_gioi_han.thu(f"ma-giam-gia:{khach.id}", KIEM_TRA_TOI_DA, KIEM_TRA_CUA_SO_GIAY)
    if cho is not None:  # chặn dò mã hàng loạt
        raise LoiNghiepVu(
            "QUA_GIOI_HAN",
            "Bạn thử mã quá nhiều lần, vui lòng thử lại sau",
            chi_tiet={"thu_lai_sau_giay": int(cho) + 1},
        )
    kq = await ap_dung.kiem_tra_ma(db, khach.id, vao.ma, await dong_tu_gio(db, khach))
    km = kq.khuyen_mai
    return KetQuaKiemTraMa(
        hop_le=kq.hop_le,
        ma=ap_dung.chuan_hoa_ma(vao.ma),
        khuyen_mai=KhuyenMaiCongKhai(
            ten=km.ten,
            loai_giam=km.loai_giam,
            gia_tri=km.gia_tri,
            giam_toi_da=km.giam_toi_da,
            don_toi_thieu=km.don_toi_thieu,
        )
        if km
        else None,
        co_so_giam=kq.co_so_giam,
        giam=kq.giam,
        ma_ly_do=kq.ma_ly_do,
        ly_do=kq.ly_do,
    )

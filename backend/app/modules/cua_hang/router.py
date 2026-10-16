"""Route công khai của cửa hàng (spec 06 mục 3.13). Chỉ chi tiết sản phẩm đọc token (để ghi lịch sử xem)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Query, Request
from pydantic import Field

from app.core.db import Db
from app.core.gioi_han import GioiHanCuaSoTruot, lay_bo_gioi_han_lich_su_xem
from app.core.phan_quyen import khach_tuy_chon
from app.core.phan_trang import PhanTrang, Trang
from app.core.tham_so import KHONG_NUL
from app.models.enums import LoaiSanPham
from app.models.khach_hang import KhachHang
from app.modules.cua_hang import chi_tiet as dich_vu_chi_tiet
from app.modules.cua_hang import danh_muc as dich_vu_danh_muc
from app.modules.cua_hang import danh_sach as dich_vu_danh_sach
from app.modules.cua_hang.chi_tiet import NguonXem
from app.modules.cua_hang.danh_sach import BoLoc, SapXep
from app.modules.cua_hang.schemas import (
    BannerCongKhai,
    BoLocSanPham,
    DanhMucChiTiet,
    DanhMucCongKhai,
    SanPhamChiTietCongKhai,
    SanPhamThe,
    TrangChu,
)
from app.modules.tai_khoan.phien_http import dia_chi_ip

router = APIRouter(tags=["Cửa hàng"])

MAU_SLUG = r"^[a-z0-9]+(-[a-z0-9]+)*$"
SlugDuongDan = Annotated[str, Path(max_length=300, pattern=MAU_SLUG)]
SlugDanhMuc = Annotated[str | None, Query(max_length=180, pattern=MAU_SLUG, description="Slug danh mục")]
GIA_TOI_DA = 10**12
IdThuongHieu = Annotated[int, Field(ge=1, le=2_147_483_647)]


@router.get("/danh-muc", response_model=list[DanhMucCongKhai], summary="Cây danh mục (KVL01)")
async def cay_danh_muc(db: Db):
    return await dich_vu_danh_muc.cay_cong_khai(db)


@router.get("/danh-muc/{slug}", response_model=DanhMucChiTiet, summary="Chi tiết danh mục (KVL01)")
async def chi_tiet_danh_muc(slug: SlugDuongDan, db: Db):
    return await dich_vu_danh_muc.chi_tiet_theo_slug(db, slug)


@router.get("/banner", response_model=list[BannerCongKhai], summary="Banner đang hiển thị (KVL01)")
async def banner(db: Db, vi_tri: Annotated[str | None, Query(max_length=30, pattern=r"^[a-z0-9_]+$")] = None):
    return await dich_vu_danh_muc.banner_dang_hien(db, vi_tri)


@router.get("/trang-chu", response_model=TrangChu, summary="Trang chủ: banner, nổi bật, bán chạy (KVL01)")
async def trang_chu(db: Db):
    return await dich_vu_danh_sach.trang_chu(db)


@router.get("/san-pham", response_model=Trang[SanPhamThe], summary="Danh sách, lọc, sắp xếp sản phẩm (KVL02)")
async def danh_sach_san_pham(
    db: Db,
    tp: PhanTrang,
    danh_muc: SlugDanhMuc = None,
    loai: LoaiSanPham | None = None,
    thuong_hieu_id: Annotated[list[IdThuongHieu] | None, Query(max_length=20)] = None,
    gia_tu: Annotated[int | None, Query(ge=0, le=GIA_TOI_DA)] = None,
    gia_den: Annotated[int | None, Query(ge=0, le=GIA_TOI_DA)] = None,
    doi_tuong: Annotated[str | None, Query(max_length=100, pattern=KHONG_NUL)] = None,
    con_hang: bool = False,
    sap_xep: SapXep = "moi",
):
    loc = BoLoc(
        danh_muc_slug=danh_muc,
        loai=loai,
        thuong_hieu_ids=thuong_hieu_id or [],
        gia_tu=gia_tu,
        gia_den=gia_den,
        doi_tuong=doi_tuong,
        con_hang=con_hang,
        sap_xep=sap_xep,
    )
    return await dich_vu_danh_sach.danh_sach(db, loc, tp)


@router.get("/bo-loc-san-pham", response_model=BoLocSanPham, summary="Lựa chọn của bộ lọc sản phẩm (KVL02)")
async def bo_loc(db: Db, danh_muc: SlugDanhMuc = None):
    return await dich_vu_danh_sach.bo_loc(db, danh_muc)


GHI_XEM_TOI_DA_MOI_IP = 120
GHI_XEM_CUA_SO_GIAY = 600


@router.get("/san-pham/{slug}", response_model=SanPhamChiTietCongKhai, summary="Chi tiết sản phẩm (KVL03)")
async def chi_tiet_san_pham(
    slug: SlugDuongDan,
    request: Request,
    db: Db,
    khach: Annotated[KhachHang | None, Depends(khach_tuy_chon)],
    bo_gioi_han: Annotated[GioiHanCuaSoTruot, Depends(lay_bo_gioi_han_lich_su_xem)],
    nguon: NguonXem | None = None,
    x_ma_phien: Annotated[str | None, Header(max_length=200)] = None,
):
    ma_phien = dich_vu_chi_tiet.ma_phien_hop_le(x_ma_phien)
    # Mã phiên do client tự chọn nên một IP quay mã liên tục sẽ làm phình `lich_su_xem` và lệch gợi ý: quá giới hạn thì
    # vẫn trả sản phẩm, chỉ không ghi lịch sử.
    duoc_ghi = bo_gioi_han.thu(f"xem:{dia_chi_ip(request)}", GHI_XEM_TOI_DA_MOI_IP, GHI_XEM_CUA_SO_GIAY) is None
    return await dich_vu_chi_tiet.chi_tiet(db, slug, khach=khach, ma_phien=ma_phien, nguon=nguon, duoc_ghi=duoc_ghi)

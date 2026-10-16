"""Quản lý sản phẩm của Admin (AD04): `/api/v1/noi-bo/san-pham`. Cần `product.commercial.manage` (mục 3.11 spec 06)."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile

from app.core import luu_tru
from app.core.db import Db
from app.core.loi import LoiNghiepVu
from app.core.phan_quyen import yeu_cau_quyen
from app.core.phan_trang import PhanTrang, SapXepQuery, Trang, tao_trang
from app.core.tham_so import IdInt, tu_khoa_tim
from app.models.enums import LoaiSanPham, TrangThaiKinhDoanh
from app.models.he_thong import NhanVien
from app.modules.san_pham import san_pham as dich_vu
from app.modules.san_pham import san_pham_anh, san_pham_don_vi
from app.modules.san_pham.schemas_san_pham import (
    DatAnhChinh,
    DatThuTuAnh,
    PhienBan,
    SanPhamChiTiet,
    SanPhamSua,
    SanPhamTao,
    SanPhamTomTat,
    ThayDonVi,
    ThayThanhPhan,
)
from app.modules.tai_khoan.phien_http import dia_chi_ip

router = APIRouter(prefix="/noi-bo/san-pham", tags=["Quản lý sản phẩm"])

SanPhamXem = Annotated[NhanVien, Depends(yeu_cau_quyen("product.commercial.manage", "xem"))]
SanPhamSuaQuyen = Annotated[NhanVien, Depends(yeu_cau_quyen("product.commercial.manage"))]
PhienBanQuery = Annotated[PhienBan, Query(description="`phien_ban` lấy từ `GET /{id}` (khóa lạc quan)")]


@router.get("", response_model=Trang[SanPhamTomTat], summary="Danh sách sản phẩm (AD04)")
async def danh_sach(
    actor: SanPhamXem,
    db: Db,
    tp: PhanTrang,
    q: tu_khoa_tim("Tìm theo tên (không phân biệt dấu) hoặc SKU") = None,  # type: ignore[valid-type]
    loai: LoaiSanPham | None = None,
    danh_muc_id: Annotated[int | None, Query(ge=1, le=2_147_483_647, description="Gồm cả danh mục con")] = None,
    trang_thai: TrangThaiKinhDoanh | None = None,
    sap_xep: SapXepQuery = None,
):
    """`sap_xep` nhận `created_at` (mặc định, giảm dần), `ten`, `sku`; thêm `-` để giảm dần."""
    dong, tong = await dich_vu.danh_sach(
        db, q=q, loai=loai, danh_muc_id=danh_muc_id, trang_thai=trang_thai, sap_xep=sap_xep, tp=tp
    )
    return tao_trang(dong, tong, tp)


@router.get("/{san_pham_id}", response_model=SanPhamChiTiet, summary="Chi tiết sản phẩm (AD04)")
async def chi_tiet(san_pham_id: IdInt, actor: SanPhamXem, db: Db):
    return await dich_vu.lay(db, san_pham_id)


@router.post("", status_code=201, response_model=SanPhamChiTiet, summary="Thêm sản phẩm (AD04)")
async def tao(du_lieu: SanPhamTao, request: Request, actor: SanPhamSuaQuyen, db: Db):
    return await dich_vu.tao(db, actor, du_lieu, ip=dia_chi_ip(request))


@router.patch("/{san_pham_id}", response_model=SanPhamChiTiet, summary="Sửa thông tin thương mại (AD04)")
async def sua(san_pham_id: IdInt, du_lieu: SanPhamSua, request: Request, actor: SanPhamSuaQuyen, db: Db):
    return await dich_vu.sua(db, actor, san_pham_id, du_lieu, ip=dia_chi_ip(request))


@router.delete("/{san_pham_id}", status_code=204, summary="Xóa mềm sản phẩm (AD04)")
async def xoa(
    san_pham_id: IdInt, phien_ban: PhienBanQuery, request: Request, actor: SanPhamSuaQuyen, db: Db
) -> Response:
    await dich_vu.xoa(db, actor, san_pham_id, phien_ban, ip=dia_chi_ip(request))
    return Response(status_code=204)


@router.put("/{san_pham_id}/don-vi", response_model=SanPhamChiTiet, summary="Thay danh sách đơn vị quy đổi (AD04)")
async def thay_don_vi(san_pham_id: IdInt, du_lieu: ThayDonVi, request: Request, actor: SanPhamSuaQuyen, db: Db):
    return await san_pham_don_vi.thay_don_vi(db, actor, san_pham_id, du_lieu, ip=dia_chi_ip(request))


@router.put("/{san_pham_id}/thanh-phan", response_model=SanPhamChiTiet, summary="Thay danh sách thành phần (AD04)")
async def thay_thanh_phan(san_pham_id: IdInt, du_lieu: ThayThanhPhan, request: Request, actor: SanPhamSuaQuyen, db: Db):
    return await san_pham_don_vi.thay_thanh_phan(db, actor, san_pham_id, du_lieu, ip=dia_chi_ip(request))


@router.post(
    "/{san_pham_id}/anh", status_code=201, response_model=SanPhamChiTiet, summary="Tải ảnh sản phẩm lên (AD04)"
)
async def them_anh(
    san_pham_id: IdInt,
    phien_ban: PhienBanQuery,
    request: Request,
    actor: SanPhamSuaQuyen,
    db: Db,
    tep: Annotated[UploadFile, File(description="Ảnh jpeg, png hoặc webp, tối đa 5 MB")],
):
    # Đọc tối đa 5 MB + 1 byte để biết có vượt hay không mà không nạp cả file khổng lồ vào bộ nhớ.
    noi_dung = await tep.read(luu_tru.TOI_DA_ANH_BYTE + 1)
    if not noi_dung:
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE", "Dữ liệu không hợp lệ", chi_tiet=[{"truong": "tep", "loi": "File rỗng"}]
        )
    return await san_pham_anh.them_anh(db, actor, san_pham_id, phien_ban, noi_dung, ip=dia_chi_ip(request))


@router.put("/{san_pham_id}/anh/thu-tu", response_model=SanPhamChiTiet, summary="Sắp xếp ảnh (AD04)")
async def dat_thu_tu_anh(san_pham_id: IdInt, du_lieu: DatThuTuAnh, request: Request, actor: SanPhamSuaQuyen, db: Db):
    return await san_pham_anh.dat_thu_tu(db, actor, san_pham_id, du_lieu.phien_ban, du_lieu.ids, ip=dia_chi_ip(request))


@router.put("/{san_pham_id}/anh/{anh_id}/chinh", response_model=SanPhamChiTiet, summary="Đặt ảnh chính (AD04)")
async def dat_anh_chinh(
    san_pham_id: IdInt, anh_id: IdInt, du_lieu: DatAnhChinh, request: Request, actor: SanPhamSuaQuyen, db: Db
):
    return await san_pham_anh.dat_anh_chinh(db, actor, san_pham_id, anh_id, du_lieu.phien_ban, ip=dia_chi_ip(request))


@router.delete("/{san_pham_id}/anh/{anh_id}", response_model=SanPhamChiTiet, summary="Xóa ảnh sản phẩm (AD04)")
async def xoa_anh(
    san_pham_id: IdInt, anh_id: IdInt, phien_ban: PhienBanQuery, request: Request, actor: SanPhamSuaQuyen, db: Db
):
    return await san_pham_anh.xoa_anh(db, actor, san_pham_id, anh_id, phien_ban, ip=dia_chi_ip(request))

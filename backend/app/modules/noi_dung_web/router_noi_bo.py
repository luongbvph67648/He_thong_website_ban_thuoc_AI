"""Quản lý banner, bài viết, chính sách, FAQ của Admin (AD07): `/api/v1/noi-bo/banner`, `/noi-bo/bai-viet`.

Đọc cần `cms.manage` mức xem; ghi cần mức đầy đủ VÀ người thực hiện là ADMIN (`dam_bao_la_admin`, như AD03/AD04).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile

from app.core import luu_tru
from app.core.db import Db
from app.core.loi import LoiNghiepVu
from app.core.phan_quyen import yeu_cau_quyen
from app.core.phan_trang import PhanTrang, Trang, tao_trang
from app.core.tham_so import IdInt, tu_khoa_tim
from app.models.enums import LoaiBaiViet, TrangThaiNoiDung
from app.models.he_thong import NhanVien
from app.modules.noi_dung_web import anh as dich_vu_anh
from app.modules.noi_dung_web import bai_viet as dich_vu_bai_viet
from app.modules.noi_dung_web import banner as dich_vu_banner
from app.modules.noi_dung_web.schemas import (
    AnhDaTai,
    BaiVietAdmin,
    BaiVietSua,
    BaiVietTomTatAdmin,
    BaiVietVao,
    BannerRa,
    BannerSua,
    BannerVao,
    ChuyenTrangThai,
    PhienBan,
)
from app.modules.tai_khoan.phien_http import dia_chi_ip

banner_router = APIRouter(prefix="/noi-bo/banner", tags=["Quản lý banner"])
bai_viet_router = APIRouter(prefix="/noi-bo/bai-viet", tags=["Quản lý bài viết"])

CmsXem = Annotated[NhanVien, Depends(yeu_cau_quyen("cms.manage", "xem"))]
CmsSua = Annotated[NhanVien, Depends(yeu_cau_quyen("cms.manage"))]
PhienBanQuery = Annotated[PhienBan, Query(description="Phiên bản bản ghi bạn đã xem (khóa lạc quan)")]
TepAnh = Annotated[UploadFile, File(description="Ảnh jpeg, png hoặc webp, tối đa 5 MB")]


async def _doc_anh(tep: UploadFile) -> bytes:
    # Đọc tối đa 5 MB + 1 byte để biết có vượt hay không mà không nạp cả file khổng lồ vào bộ nhớ.
    noi_dung = await tep.read(luu_tru.TOI_DA_ANH_BYTE + 1)
    if not noi_dung:
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE", "Dữ liệu không hợp lệ", chi_tiet=[{"truong": "tep", "loi": "File rỗng"}]
        )
    return noi_dung


# --- Banner ---------------------------------------------------------------------------------------


@banner_router.get("", response_model=list[BannerRa], summary="Danh sách banner (AD07)")
async def danh_sach_banner(actor: CmsXem, db: Db):
    return await dich_vu_banner.danh_sach(db)


@banner_router.post("", status_code=201, response_model=BannerRa, summary="Thêm banner (AD07)")
async def tao_banner(du_lieu: BannerVao, request: Request, actor: CmsSua, db: Db):
    return await dich_vu_banner.tao(db, actor, du_lieu, ip=dia_chi_ip(request))


@banner_router.post("/anh", status_code=201, response_model=AnhDaTai, summary="Tải ảnh banner lên (AD07)")
async def tai_anh_banner(request: Request, actor: CmsSua, db: Db, tep: TepAnh):
    url = await dich_vu_anh.tai_anh(db, actor, "banner", await _doc_anh(tep), ip=dia_chi_ip(request))
    return AnhDaTai(url=url)


@banner_router.patch("/{banner_id}", response_model=BannerRa, summary="Sửa banner (AD07)")
async def sua_banner(banner_id: IdInt, du_lieu: BannerSua, request: Request, actor: CmsSua, db: Db):
    return await dich_vu_banner.sua(db, actor, banner_id, du_lieu, ip=dia_chi_ip(request))


@banner_router.delete("/{banner_id}", status_code=204, summary="Xóa banner (AD07)")
async def xoa_banner(banner_id: IdInt, phien_ban: PhienBanQuery, request: Request, actor: CmsSua, db: Db) -> Response:
    await dich_vu_banner.xoa(db, actor, banner_id, phien_ban, ip=dia_chi_ip(request))
    return Response(status_code=204)


# --- Bài viết, chính sách, FAQ --------------------------------------------------------------------


@bai_viet_router.get("", response_model=Trang[BaiVietTomTatAdmin], summary="Danh sách bài viết, chính sách, FAQ (AD07)")
async def danh_sach_bai_viet(
    actor: CmsXem,
    db: Db,
    tp: PhanTrang,
    loai: LoaiBaiViet | None = None,
    trang_thai: TrangThaiNoiDung | None = None,
    q: tu_khoa_tim("Tìm theo tiêu đề (không phân biệt dấu)") = None,  # type: ignore[valid-type]
):
    dong, tong = await dich_vu_bai_viet.danh_sach(db, loai=loai, trang_thai=trang_thai, q=q, tp=tp)
    return tao_trang(dong, tong, tp)


@bai_viet_router.post("", status_code=201, response_model=BaiVietAdmin, summary="Soạn bài viết, chính sách, FAQ (AD07)")
async def tao_bai_viet(du_lieu: BaiVietVao, request: Request, actor: CmsSua, db: Db):
    return await dich_vu_bai_viet.tao(db, actor, du_lieu, ip=dia_chi_ip(request))


@bai_viet_router.post("/anh", status_code=201, response_model=AnhDaTai, summary="Tải ảnh bìa bài viết lên (AD07)")
async def tai_anh_bai_viet(request: Request, actor: CmsSua, db: Db, tep: TepAnh):
    url = await dich_vu_anh.tai_anh(db, actor, "bai-viet", await _doc_anh(tep), ip=dia_chi_ip(request))
    return AnhDaTai(url=url)


@bai_viet_router.get("/{bai_viet_id}", response_model=BaiVietAdmin, summary="Chi tiết bài viết (AD07)")
async def chi_tiet_bai_viet(bai_viet_id: IdInt, actor: CmsXem, db: Db):
    return await dich_vu_bai_viet.lay(db, bai_viet_id)


@bai_viet_router.patch("/{bai_viet_id}", response_model=BaiVietAdmin, summary="Sửa bài viết, chính sách, FAQ (AD07)")
async def sua_bai_viet(bai_viet_id: IdInt, du_lieu: BaiVietSua, request: Request, actor: CmsSua, db: Db):
    return await dich_vu_bai_viet.sua(db, actor, bai_viet_id, du_lieu, ip=dia_chi_ip(request))


@bai_viet_router.post("/{bai_viet_id}/go", response_model=BaiVietAdmin, summary="Gỡ bài khỏi website (AD07)")
async def go_bai_viet(bai_viet_id: IdInt, du_lieu: ChuyenTrangThai, request: Request, actor: CmsSua, db: Db):
    return await dich_vu_bai_viet.go(db, actor, bai_viet_id, du_lieu.phien_ban, ip=dia_chi_ip(request))


@bai_viet_router.post("/{bai_viet_id}/dang", response_model=BaiVietAdmin, summary="Đăng lại bài đã gỡ (AD07)")
async def dang_bai_viet(bai_viet_id: IdInt, du_lieu: ChuyenTrangThai, request: Request, actor: CmsSua, db: Db):
    return await dich_vu_bai_viet.dang(db, actor, bai_viet_id, du_lieu.phien_ban, ip=dia_chi_ip(request))

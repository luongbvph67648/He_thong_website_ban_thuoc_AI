"""Bài viết, chính sách, FAQ công khai (KVL11): `GET /api/v1/bai-viet`, `/bai-viet/{slug}`; không cần đăng nhập."""

from typing import Annotated

from fastapi import APIRouter, Path

from app.core.db import Db
from app.core.phan_trang import PhanTrang, Trang
from app.core.tham_so import tu_khoa_tim
from app.models.enums import LoaiBaiViet
from app.modules.noi_dung_web import cong_khai as dich_vu
from app.modules.noi_dung_web.schemas import BaiVietCongKhai, BaiVietCongKhaiTomTat

router = APIRouter(prefix="/bai-viet", tags=["Bài viết công khai"])

SlugBai = Annotated[str, Path(max_length=300, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")]


@router.get(
    "", response_model=Trang[BaiVietCongKhaiTomTat], summary="Danh sách bài viết, chính sách, FAQ đã đăng (KVL11)"
)
async def danh_sach(
    db: Db,
    tp: PhanTrang,
    loai: LoaiBaiViet = LoaiBaiViet.bai_viet,
    q: tu_khoa_tim("Tìm theo tiêu đề (không phân biệt dấu)") = None,  # type: ignore[valid-type]
    kem_noi_dung: bool = False,
):
    return await dich_vu.danh_sach(db, loai=loai, q=q, kem_noi_dung=kem_noi_dung, tp=tp)


@router.get("/{slug}", response_model=BaiVietCongKhai, summary="Đọc một bài đã đăng (KVL11)")
async def chi_tiet(slug: SlugBai, db: Db):
    return await dich_vu.chi_tiet(db, slug)

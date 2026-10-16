"""Bài viết sức khỏe, chính sách, FAQ công khai (KVL11, spec 06 mục 3.14).

Chỉ bài `da_duyet`; không lộ người soạn hay người duyệt.
"""

import re
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.core.phan_trang import ThamSoPhanTrang, Trang, lay_trang, tao_trang
from app.core.tim_kiem import mau_tim_like
from app.models.enums import LoaiBaiViet, TrangThaiNoiDung
from app.models.he_thong import BaiViet
from app.modules.noi_dung_web.schemas import BaiVietCongKhai, BaiVietCongKhaiTomTat

TOM_TAT_TOI_DA = 200
_KHONG_PHAI_CHU = re.compile(
    r"```.*?```|`|!\[[^\]]*\]\([^)]*\)|\[([^\]]*)\]\([^)]*\)|[#>*_~|]+|^\s*[-+]\s+", re.S | re.M
)
_KHOANG_TRANG = re.compile(r"\s+")
_TRUOC_DAU_CAU = re.compile(r"\s+([.,;:!?])")


def tom_tat(noi_dung: str) -> str:
    """Vài chữ đầu của bài, đã bỏ ký hiệu Markdown (đoạn mã, ảnh, liên kết giữ chữ, dấu #, *, >...)."""
    sach = _KHONG_PHAI_CHU.sub(lambda m: m.group(1) or " ", noi_dung)
    sach = _TRUOC_DAU_CAU.sub(r"\1", _KHOANG_TRANG.sub(" ", sach)).strip()
    return sach if len(sach) <= TOM_TAT_TOI_DA else sach[:TOM_TAT_TOI_DA].rsplit(" ", 1)[0].rstrip() + "…"


def _ngay_dang():
    return func.coalesce(BaiViet.ngay_duyet, BaiViet.created_at)


async def danh_sach(
    db: AsyncSession, *, loai: LoaiBaiViet, q: str | None, kem_noi_dung: bool, tp: ThamSoPhanTrang
) -> Trang[BaiVietCongKhaiTomTat]:
    if kem_noi_dung and loai != LoaiBaiViet.faq:
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE",
            "Dữ liệu không hợp lệ",
            chi_tiet=[{"truong": "kem_noi_dung", "loi": "Chỉ dùng được với loai=faq"}],
        )
    stmt: Select[Any] = select(BaiViet, _ngay_dang().label("ngay_dang")).where(
        BaiViet.loai == loai, BaiViet.trang_thai == TrangThaiNoiDung.da_duyet
    )
    if q and q.strip():
        mau = mau_tim_like(q)
        stmt = stmt.where(
            func.f_unaccent(func.lower(BaiViet.tieu_de)).like(func.f_unaccent(func.lower(mau)), escape="\\")
        )
    # Bài viết: mới đăng trước. Chính sách và FAQ: theo thứ tự Admin tạo (câu hỏi quan trọng thường nhập trước).
    stmt = stmt.order_by(_ngay_dang().desc() if loai == LoaiBaiViet.bai_viet else BaiViet.created_at, BaiViet.id)
    dong, tong = await lay_trang(db, stmt, tp, nhieu_cot=True)
    return tao_trang(
        [
            BaiVietCongKhaiTomTat(
                id=bv.id,
                tieu_de=bv.tieu_de,
                slug=bv.slug,
                loai=bv.loai,
                anh_bia_url=bv.anh_bia_url,
                tom_tat=tom_tat(bv.noi_dung),
                ngay_dang=ngay,
                noi_dung=bv.noi_dung if kem_noi_dung else None,
            )
            for bv, ngay in dong
        ],
        tong,
        tp,
    )


async def chi_tiet(db: AsyncSession, slug: str) -> BaiVietCongKhai:
    dong = (
        await db.execute(
            select(BaiViet, _ngay_dang()).where(BaiViet.slug == slug, BaiViet.trang_thai == TrangThaiNoiDung.da_duyet)
        )
    ).first()
    if dong is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy bài viết")
    bv, ngay = dong
    return BaiVietCongKhai(
        id=bv.id,
        tieu_de=bv.tieu_de,
        slug=bv.slug,
        loai=bv.loai,
        anh_bia_url=bv.anh_bia_url,
        noi_dung=bv.noi_dung,
        ngay_dang=ngay,
    )

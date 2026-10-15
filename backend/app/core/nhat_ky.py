"""Nhật ký hệ thống (`nhat_ky_he_thong`, chỉ INSERT): ai làm gì, trên bản ghi nào, lúc nào, từ IP nào.

Không bao giờ ghi mật khẩu, OTP, token hay dữ liệu sức khỏe dạng rõ (CLAUDE.md quy tắc 7, spec 03 mục 5.1): mọi giá trị
cũ/mới đi qua `che_du_lieu_nhay_cam`: giá trị của các khóa nhạy cảm bị thay bằng `"***"` dù người gọi có quên.
Hàm không commit; nhật ký nằm trong cùng transaction với thao tác được ghi.
"""

from typing import Any

from pydantic_core import to_jsonable_python
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.he_thong import NhatKyHeThong

DA_CHE = "***"

# Khóa chứa một trong các đoạn này (không phân biệt hoa thường) bị che giá trị.
DOAN_KHOA_NHAY_CAM = (
    "mat_khau",
    "password",
    "otp",
    "token",
    "secret",
    "hash",
    "benh_nen",
    "di_ung",
    "suc_khoe",
    "khoa_ma_hoa",
)


def la_khoa_nhay_cam(khoa: str) -> bool:
    khoa = khoa.lower()
    return any(doan in khoa for doan in DOAN_KHOA_NHAY_CAM)


def che_du_lieu_nhay_cam(gia_tri: Any) -> Any:
    """Bản sao của `gia_tri` (dict/list lồng nhau) với giá trị của mọi khóa nhạy cảm thay bằng `"***"`."""
    if isinstance(gia_tri, dict):
        return {str(k): (DA_CHE if la_khoa_nhay_cam(str(k)) else che_du_lieu_nhay_cam(v)) for k, v in gia_tri.items()}
    if isinstance(gia_tri, list | tuple | set | frozenset):
        return [che_du_lieu_nhay_cam(v) for v in gia_tri]
    return gia_tri


def _chuan_bi(gia_tri: Any) -> Any:
    # `to_jsonable_python` đổi Decimal sang chuỗi (không qua float), nên tiền không mất độ chính xác trong nhật ký.
    return None if gia_tri is None else che_du_lieu_nhay_cam(to_jsonable_python(gia_tri))


async def ghi_nhat_ky(
    db: AsyncSession,
    *,
    nhan_vien_id: int | None,
    hanh_dong: str,
    bang: str,
    ban_ghi_id: int | str | None = None,
    gia_tri_cu: Any = None,
    gia_tri_moi: Any = None,
    ip: str | None = None,
) -> NhatKyHeThong:
    """Ghi một dòng nhật ký. `nhan_vien_id = None` là hệ thống hoặc người chưa xác định (đăng nhập thất bại).

    `hanh_dong`: `tao`, `sua`, `xoa`, `duyet`, `dang_nhap`, `khoa_tam`, `doi_mat_khau`, `doc_suc_khoe`...
    Với dữ liệu sức khỏe chỉ ghi `bang` và `ban_ghi_id`, không truyền giá trị.
    """
    dong = NhatKyHeThong(
        nhan_vien_id=nhan_vien_id,
        hanh_dong=hanh_dong,
        bang=bang,
        ban_ghi_id=None if ban_ghi_id is None else str(ban_ghi_id),
        gia_tri_cu=_chuan_bi(gia_tri_cu),
        gia_tri_moi=_chuan_bi(gia_tri_moi),
        ip=ip,
    )
    db.add(dong)
    await db.flush()
    return dong

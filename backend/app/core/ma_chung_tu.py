"""Mã chứng từ nội bộ sinh từ sequence để dễ tra cứu (spec 04 mục 7).

Mã của khách (đơn hàng `DH...`, yêu cầu `YC...`/`DT...`) dùng ký tự ngẫu nhiên để không đoán được thứ tự; làm khi có
chỗ dùng (T4.x). Số trong sequence không rollback theo transaction nên mã có thể bị bỏ trống số, không bao giờ trùng.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.thoi_gian import hom_nay_vn

_TIEN_TO_PHIEU = {
    "phieu_nhap": "PN",
    "phieu_kiem_ke": "KK",
    "phieu_dieu_chinh": "DC",
    "phieu_huy": "PH",
    "phieu_xuat_tra": "XT",
}


async def _so_tiep(db: AsyncSession, ten_sequence: str) -> int:
    return (await db.execute(text(f"SELECT nextval('{ten_sequence}')"))).scalar_one()  # tên lấy từ hằng, không từ input


def _yy() -> str:
    return f"{hom_nay_vn().year % 100:02d}"


async def ma_nhan_vien(db: AsyncSession) -> str:
    """`NV` + 4 số, ví dụ NV0007."""
    return f"NV{await _so_tiep(db, 'seq_nhan_vien'):04d}"


async def ma_phieu(db: AsyncSession, loai: str) -> str:
    """`PN`/`KK`/`DC`/`PH`/`XT` + YY + 6 số, ví dụ PN26000012. `loai` là tên bảng phiếu (`phieu_nhap`...)."""
    if loai not in _TIEN_TO_PHIEU:
        raise ValueError(f"Loại phiếu không hợp lệ: {loai}")
    return f"{_TIEN_TO_PHIEU[loai]}{_yy()}{await _so_tiep(db, f'seq_{loai}'):06d}"


async def ma_lenh_thu_hoi(db: AsyncSession) -> str:
    """`TH` + YY + 4 số, ví dụ TH260003."""
    return f"TH{_yy()}{await _so_tiep(db, 'seq_lenh_thu_hoi'):04d}"

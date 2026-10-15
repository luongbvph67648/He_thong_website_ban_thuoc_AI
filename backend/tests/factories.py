"""Hàm dựng dữ liệu tối thiểu cho test. T0.6 mở rộng thành bộ factories đầy đủ.

Chỉ dựng qua ORM, không đi qua dịch vụ nghiệp vụ, để test dịch vụ không phụ thuộc vào chính nó.
"""

from datetime import date
from itertools import count

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kho import LoThuoc
from app.models.san_pham import DanhMuc, SanPham

_dem = count(1)


async def tao_san_pham(db: AsyncSession, loai: str = "thuoc_khong_ke_don", **truong) -> SanPham:
    n = next(_dem)
    danh_muc = DanhMuc(ten=f"Danh mục {n}", slug=f"danh-muc-{n}-{id(db)}")
    db.add(danh_muc)
    await db.flush()
    gia_tri = {
        "sku": f"SKU-{n}-{id(db)}",
        "ten": f"Sản phẩm {n}",
        "slug": f"san-pham-{n}-{id(db)}",
        "loai_san_pham": loai,
        "danh_muc_id": danh_muc.id,
        "don_vi_co_so": "viên",
        **truong,
    }
    san_pham = SanPham(**gia_tri)
    db.add(san_pham)
    await db.flush()
    return san_pham


async def tao_lo(db: AsyncSession, san_pham: SanPham | None = None, **truong) -> LoThuoc:
    if san_pham is None:
        san_pham = await tao_san_pham(db)
    gia_tri = {
        "san_pham_id": san_pham.id,
        "so_lo": f"L{next(_dem):04d}",
        "han_su_dung": date(2030, 1, 1),
        "gia_nhap": 1000,
        **truong,
    }
    lo = LoThuoc(**gia_tri)
    db.add(lo)
    await db.flush()
    return lo

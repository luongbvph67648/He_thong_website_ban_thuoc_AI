"""Phần dùng chung của phiếu hủy và phiếu xuất trả NCC (KHO09, KHO11): kiểm tra dòng, dựng dòng ra."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.models.enums import KhuTon
from app.models.he_thong import NhanVien
from app.models.kho import LoThuoc
from app.models.san_pham import SanPham
from app.modules.kho.schemas_phieu_nhap import NhanVienRut, SanPhamRut


def nv_rut(n: NhanVien | None) -> NhanVienRut | None:
    return None if n is None else NhanVienRut(id=n.id, ma_nhan_vien=n.ma_nhan_vien, ho_ten=n.ho_ten)


def ton_khu(lo: LoThuoc, khu: KhuTon) -> int:
    """Số lượng có thể lấy ra khỏi `khu`: khu bán không tính hàng đang giữ cho đơn."""
    return lo.so_luong_ton - lo.so_luong_giu if khu == KhuTon.kho_ban else lo.so_luong_biet_tru


async def kiem_tra_dong(db: AsyncSession, dong: Sequence) -> dict[int, LoThuoc]:
    """Lô phải tồn tại và `so_luong` không vượt tồn khu đã chọn lúc lập (kiểm tra lại khi duyệt). Không khóa, không
    đổi tồn. Trả `lo_id -> lô`."""
    lo_thuoc = {
        lo.id: lo for lo in (await db.execute(select(LoThuoc).where(LoThuoc.id.in_([d.lo_id for d in dong])))).scalars()
    }
    for i, d in enumerate(dong):
        lo = lo_thuoc.get(d.lo_id)
        if lo is None:
            raise LoiNghiepVu(
                "DU_LIEU_KHONG_HOP_LE",
                "Lô không tồn tại",
                chi_tiet=[{"truong": f"dong.{i}.lo_id", "loi": "Không tồn tại"}],
            )
        con_lai = ton_khu(lo, d.tu_khu)
        if d.so_luong > con_lai:
            raise LoiNghiepVu(
                "HET_HANG",
                f"Lô {lo.so_lo} chỉ còn {con_lai} ở khu {d.tu_khu.value}, không đủ {d.so_luong}",
                chi_tiet={"lo_id": lo.id, "con_lai": con_lai},
            )
    return lo_thuoc


async def thong_tin_lo(db: AsyncSession, lo_ids: Sequence[int]) -> dict[int, tuple[LoThuoc, SanPhamRut]]:
    hang = (
        await db.execute(
            select(LoThuoc, SanPham).join(SanPham, SanPham.id == LoThuoc.san_pham_id).where(LoThuoc.id.in_(lo_ids))
        )
    ).all()
    return {lo.id: (lo, SanPhamRut(id=sp.id, sku=sp.sku, ten=sp.ten)) for lo, sp in hang}

"""Điều kiện "hiển thị với khách" dùng chung cho mọi truy vấn công khai (spec 06 mục 3.13).

Sản phẩm hiển thị = chưa xóa, đang kinh doanh và danh mục của nó cùng mọi tổ tiên đều chưa xóa và đang hiển thị
(QĐ-16). Cây danh mục nhỏ nên nạp cả cây một lần rồi tính nhánh hiển thị trong bộ nhớ, không dùng CTE đệ quy.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import ColumnElement, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.thoi_gian import bay_gio_utc, hom_nay_vn
from app.models.ban_hang import CtDonHang, DonHang
from app.models.enums import TrangThaiDon, TrangThaiKinhDoanh, TrangThaiLo
from app.models.kho import LoThuoc
from app.models.san_pham import DanhMuc, DonViQuyDoi, SanPham

SO_NGAY_BAN_CHAY = 30


@dataclass
class CayHienThi:
    """Các danh mục khách nhìn thấy (đã bỏ nhánh ẩn hoặc đã xóa), theo thứ tự `thu_tu` rồi `id`."""

    theo_id: dict[int, DanhMuc] = field(default_factory=dict)
    con: dict[int | None, list[DanhMuc]] = field(default_factory=lambda: defaultdict(list))

    @property
    def ids(self) -> set[int]:
        return set(self.theo_id)

    def theo_slug(self, slug: str) -> DanhMuc | None:
        return next((d for d in self.theo_id.values() if d.slug == slug), None)

    def duong_dan(self, danh_muc_id: int) -> list[DanhMuc]:
        """Từ gốc đến chính nó."""
        chuoi: list[DanhMuc] = []
        hien_tai: DanhMuc | None = self.theo_id.get(danh_muc_id)
        while hien_tai is not None and hien_tai not in chuoi:
            chuoi.append(hien_tai)
            hien_tai = self.theo_id.get(hien_tai.danh_muc_cha_id) if hien_tai.danh_muc_cha_id else None
        return chuoi[::-1]

    def con_chau_ids(self, danh_muc_id: int) -> set[int]:
        ket, can_xet = set(), [danh_muc_id]
        while can_xet:
            id_ = can_xet.pop()
            if id_ in ket:
                continue
            ket.add(id_)
            can_xet.extend(c.id for c in self.con.get(id_, []))
        return ket


async def nap_cay_hien_thi(db: AsyncSession) -> CayHienThi:
    tat_ca = {
        d.id: d
        for d in (
            await db.execute(select(DanhMuc).where(DanhMuc.deleted_at.is_(None)).order_by(DanhMuc.thu_tu, DanhMuc.id))
        ).scalars()
    }
    ket = CayHienThi()
    trang_thai: dict[int, bool] = {}

    def hien_thi(id_: int) -> bool:
        if id_ in trang_thai:
            return trang_thai[id_]
        trang_thai[id_] = False  # chặn vòng (dữ liệu không thể có vòng qua service)
        d = tat_ca[id_]
        if not d.dang_hien_thi:
            return False
        if d.danh_muc_cha_id is None:
            trang_thai[id_] = True
        else:  # cha đã xóa (không có trong `tat_ca`) hoặc đang ẩn thì cả nhánh không hiển thị
            trang_thai[id_] = d.danh_muc_cha_id in tat_ca and hien_thi(d.danh_muc_cha_id)
        return trang_thai[id_]

    for d in tat_ca.values():
        if hien_thi(d.id):
            ket.theo_id[d.id] = d
            ket.con[d.danh_muc_cha_id].append(d)
    return ket


def la_hien_thi(ids_danh_muc: set[int]) -> ColumnElement[bool]:
    """Điều kiện WHERE: sản phẩm hiển thị với khách."""
    return and_(
        SanPham.deleted_at.is_(None),
        SanPham.trang_thai == TrangThaiKinhDoanh.dang_kinh_doanh,
        SanPham.danh_muc_id.in_(ids_danh_muc),
    )


def ton_kha_dung(hom_nay: date | None = None) -> ColumnElement[int]:
    """Tồn khả dụng online của `SanPham` ngoài (spec 04 mục 2): lô `dang_ban` còn hạn (`HSD > hôm nay`)."""
    han = hom_nay or hom_nay_vn()
    return (
        select(func.coalesce(func.sum(LoThuoc.so_luong_ton - LoThuoc.so_luong_giu), 0))
        .where(
            LoThuoc.san_pham_id == SanPham.id,
            LoThuoc.trang_thai == TrangThaiLo.dang_ban,
            LoThuoc.han_su_dung > han,
        )
        .correlate(SanPham)
        .scalar_subquery()
    )


def gia_hien_thi() -> ColumnElement:
    """Giá của đơn vị bán online mặc định (không có thì `he_so` nhỏ nhất); NULL khi không bán online."""
    return (
        select(DonViQuyDoi.gia_ban)
        .where(DonViQuyDoi.san_pham_id == SanPham.id, DonViQuyDoi.ban_online.is_(True))
        .order_by(DonViQuyDoi.la_mac_dinh.desc(), DonViQuyDoi.he_so, DonViQuyDoi.id)
        .limit(1)
        .correlate(SanPham)
        .scalar_subquery()
    )


def so_dong_ban_30_ngay() -> ColumnElement[int]:
    """Số dòng `ct_don_hang` của đơn không hủy trong 30 ngày qua (chỉ số "bán chạy")."""
    moc = bay_gio_utc() - timedelta(days=SO_NGAY_BAN_CHAY)
    return (
        select(func.count(CtDonHang.id))
        .join(DonHang, DonHang.id == CtDonHang.don_hang_id)
        .where(
            CtDonHang.san_pham_id == SanPham.id,
            DonHang.created_at >= moc,
            DonHang.trang_thai != TrangThaiDon.da_huy,
        )
        .correlate(SanPham)
        .scalar_subquery()
    )


def chon_don_vi_gia(don_vi: list[DonViQuyDoi]) -> DonViQuyDoi | None:
    """Cùng quy tắc với `gia_hien_thi()` nhưng trên danh sách đã nạp."""
    online = [d for d in don_vi if d.ban_online]
    return min(online, key=lambda d: (not d.la_mac_dinh, d.he_so, d.id), default=None)

"""Quản lý khách hàng của Admin (AD02): danh sách, chi tiết, lịch sử mua, khóa/mở khóa.

- Chỉ đọc thông tin liên hệ và đơn hàng; không chạm hồ sơ sức khỏe, dị ứng (spec 03 mục 5.1, CLAUDE.md quy tắc 7).
- Khóa thu hồi mọi phiên của khách. Thứ tự khóa dòng: khách trước, phiên sau (QĐ-12), cùng thứ tự với đăng nhập, làm mới
  và đặt lại mật khẩu của khách nên không deadlock với chúng.
- Khách đã xóa (ẩn danh hóa, [DB23]) không xuất hiện và không thao tác được.
"""

import re
from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_quyen import dam_bao_la_admin
from app.core.phan_trang import ThamSoPhanTrang, lay_trang, sap_xep_theo
from app.core.thoi_gian import bay_gio_utc
from app.core.tim_kiem import mau_tim_like
from app.models.ban_hang import DonHang
from app.models.enums import TrangThaiTaiKhoan
from app.models.he_thong import NhanVien
from app.models.khach_hang import KhachHang
from app.modules.tai_khoan import phien

BANG = "khach_hang"

CAC_TRUONG_SAP_XEP = {
    "created_at": KhachHang.created_at,
    "ho_ten": func.f_unaccent(func.lower(KhachHang.ho_ten)),  # không phân biệt dấu và hoa thường, như ô tìm kiếm
    "email": func.lower(KhachHang.email),
    "so_dien_thoai": KhachHang.so_dien_thoai,
}

_NGAN_CACH_SDT = re.compile(r"[\s.\-()]")
_CHI_GOM_SO = re.compile(r"\+?\d{2,}")


def _khong_tim_thay() -> LoiNghiepVu:
    return LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy khách hàng")


def _so_dien_thoai_can_tim(q: str) -> str | None:
    """Chuỗi giống số điện thoại thì đổi về dạng lưu trong DB (`0xxxxxxxxx`) để `+84 902-345-678` tìm ra `0902345678`;
    không giống số thì `None` (chỉ tìm theo tên và email)."""
    so = _NGAN_CACH_SDT.sub("", q.strip())
    if not _CHI_GOM_SO.fullmatch(so):
        return None
    if so.startswith("+84"):
        return "0" + so[3:]
    if so.startswith("84") and len(so) >= 10:
        return "0" + so[2:]
    return so.removeprefix("+")


async def _tai_khach(db: AsyncSession, khach_id: int, *, khoa: bool = False) -> KhachHang:
    truy_van = select(KhachHang).where(KhachHang.id == khach_id, KhachHang.deleted_at.is_(None))
    if khoa:
        truy_van = truy_van.with_for_update().execution_options(populate_existing=True)
    khach = (await db.execute(truy_van)).scalar_one_or_none()
    if khach is None:
        raise _khong_tim_thay()
    return khach


# --- Đọc -------------------------------------------------------------------------------------------------------------


async def danh_sach(
    db: AsyncSession,
    *,
    q: str | None,
    trang_thai: TrangThaiTaiKhoan | None,
    sap_xep: str | None = None,
    tp: ThamSoPhanTrang,
) -> tuple[Sequence[KhachHang], int]:
    """Khách chưa xóa, mặc định mới đăng ký trước. `q` tìm theo tên (không phân biệt dấu), email, số điện thoại."""
    stmt = select(KhachHang).where(KhachHang.deleted_at.is_(None))
    if q and q.strip():
        mau = mau_tim_like(q)
        dieu_kien = [
            func.f_unaccent(func.lower(KhachHang.ho_ten)).like(func.f_unaccent(func.lower(mau)), escape="\\"),
            func.lower(KhachHang.email).like(func.lower(mau), escape="\\"),
        ]
        if so := _so_dien_thoai_can_tim(q):
            dieu_kien.append(KhachHang.so_dien_thoai.like(mau_tim_like(so), escape="\\"))
        stmt = stmt.where(or_(*dieu_kien))
    if trang_thai is not None:
        stmt = stmt.where(KhachHang.trang_thai == trang_thai)
    stmt = sap_xep_theo(stmt, sap_xep, CAC_TRUONG_SAP_XEP, mac_dinh="-created_at", khoa_phu=KhachHang.id)
    return await lay_trang(db, stmt, tp)


async def chi_tiet(db: AsyncSession, khach_id: int) -> tuple[KhachHang, int]:
    """Khách và số đơn hàng của họ (mọi trạng thái)."""
    khach = await _tai_khach(db, khach_id)
    so_don = await db.scalar(select(func.count()).select_from(DonHang).where(DonHang.khach_hang_id == khach.id))
    return khach, so_don or 0


async def lich_su_mua(db: AsyncSession, khach_id: int, *, tp: ThamSoPhanTrang) -> tuple[Sequence[DonHang], int]:
    """Đơn hàng của khách, mới nhất trước. Dùng lại khi có API đơn hàng của Admin (T4.x); hiện đọc thẳng `don_hang`."""
    await _tai_khach(db, khach_id)
    stmt = (
        select(DonHang).where(DonHang.khach_hang_id == khach_id).order_by(DonHang.created_at.desc(), DonHang.id.desc())
    )
    return await lay_trang(db, stmt, tp)


# --- Ghi -------------------------------------------------------------------------------------------------------------


async def khoa(db: AsyncSession, actor: NhanVien, khach_id: int, *, ly_do: str | None, ip: str) -> KhachHang:
    """Khóa tài khoản: không đăng nhập/làm mới được nữa và mọi phiên bị thu hồi ngay. Gọi lại thì không ghi gì thêm."""
    await dam_bao_la_admin(db, actor)
    khach = await _tai_khach(db, khach_id, khoa=True)
    if khach.trang_thai == TrangThaiTaiKhoan.bi_khoa:
        return khach
    khach.trang_thai = TrangThaiTaiKhoan.bi_khoa
    khach.updated_at = bay_gio_utc()
    await phien.thu_hoi_tat_ca(db, "khach", khach.id)
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="khoa",
        bang=BANG,
        ban_ghi_id=khach.id,
        gia_tri_moi={"ly_do": ly_do} if ly_do else None,
        ip=ip,
    )
    return khach


async def mo_khoa(db: AsyncSession, actor: NhanVien, khach_id: int, *, ip: str) -> KhachHang:
    """Mở khóa (cả khóa của Admin lẫn khóa tạm do đoán mật khẩu) và xóa bộ đếm đăng nhập sai."""
    await dam_bao_la_admin(db, actor)
    khach = await _tai_khach(db, khach_id, khoa=True)
    if khach.trang_thai == TrangThaiTaiKhoan.hoat_dong and khach.khoa_den is None and khach.so_lan_dang_nhap_sai == 0:
        return khach
    khach.trang_thai = TrangThaiTaiKhoan.hoat_dong
    khach.khoa_den = None
    khach.so_lan_dang_nhap_sai = 0
    khach.updated_at = bay_gio_utc()
    await ghi_nhat_ky(db, nhan_vien_id=actor.id, hanh_dong="mo_khoa", bang=BANG, ban_ghi_id=khach.id, ip=ip)
    return khach

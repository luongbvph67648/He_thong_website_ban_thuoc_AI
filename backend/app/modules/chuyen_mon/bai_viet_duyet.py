"""Duyệt bài viết sức khỏe (DS10): chỉ bài `loai = bai_viet` đang `nhap`; bài đã duyệt mới được đăng (spec 05 DS10).

Soạn, sửa, đăng bài là việc của Admin (AD07, `cms.manage`, T2.6) và Admin KHÔNG duyệt được bài của chính mình vì
`content.approve` chỉ dược sĩ giữ (`dam_bao_la_duoc_si`). Chính sách và FAQ không qua dược sĩ nên không nằm ở đây.
"""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cau_hinh_khoa import dau_van_tay
from app.core.loi import LoiNghiepVu
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_quyen import dam_bao_la_duoc_si
from app.core.phan_trang import ThamSoPhanTrang, lay_trang
from app.core.thoi_gian import bay_gio_utc
from app.core.tim_kiem import mau_tim_like
from app.models.enums import LoaiBaiViet, TrangThaiNoiDung
from app.models.he_thong import BaiViet, NhanVien
from app.modules.chuyen_mon.schemas_bai_viet import BaiVietChiTiet, BaiVietTomTat

BANG = "bai_viet"


def phien_ban_bai_viet(bv: BaiViet) -> str:
    """Dấu vân tay nội dung bài viết. Dược sĩ duyệt đúng phiên bản đã đọc: Admin sửa bài giữa chừng thì duyệt bị `409`
    (nếu không, bài vừa sửa được duyệt dù dược sĩ chưa đọc bản mới)."""
    return dau_van_tay(
        {
            "loai": bv.loai,
            "tieu_de": bv.tieu_de,
            "noi_dung": bv.noi_dung,
            "anh_bia_url": bv.anh_bia_url,
            "dua_vao_ai": bv.dua_vao_ai,
            "trang_thai": bv.trang_thai,
        }
    )


def _khong_tim_thay() -> LoiNghiepVu:
    return LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy bài viết cần duyệt")


def _tom_tat(bv: BaiViet, tac_gia: str) -> dict[str, Any]:
    return {
        "id": bv.id,
        "tieu_de": bv.tieu_de,
        "slug": bv.slug,
        "loai": bv.loai,
        "trang_thai": bv.trang_thai,
        "tac_gia": tac_gia,
        "created_at": bv.created_at,
        "updated_at": bv.updated_at,
    }


async def danh_sach_cho_duyet(
    db: AsyncSession, *, q: str | None, tp: ThamSoPhanTrang
) -> tuple[Sequence[BaiVietTomTat], int]:
    """Bài viết sức khỏe đang chờ duyệt (`nhap`), cũ nhất trước."""
    stmt: Select[Any] = (
        select(BaiViet, NhanVien.ho_ten)
        .join(NhanVien, NhanVien.id == BaiViet.tac_gia_id)
        .where(BaiViet.loai == LoaiBaiViet.bai_viet, BaiViet.trang_thai == TrangThaiNoiDung.nhap)
    )
    if q and q.strip():
        mau = mau_tim_like(q)
        stmt = stmt.where(
            or_(func.f_unaccent(func.lower(BaiViet.tieu_de)).like(func.f_unaccent(func.lower(mau)), escape="\\"))
        )
    stmt = stmt.order_by(BaiViet.created_at, BaiViet.id)
    dong, tong = await lay_trang(db, stmt, tp, nhieu_cot=True)
    return [BaiVietTomTat(**_tom_tat(bv, tac_gia)) for bv, tac_gia in dong], tong


async def _chi_tiet(db: AsyncSession, bv: BaiViet) -> BaiVietChiTiet:
    await db.refresh(bv)
    tac_gia = await db.scalar(select(NhanVien.ho_ten).where(NhanVien.id == bv.tac_gia_id))
    nguoi_duyet = (
        await db.scalar(select(NhanVien.ho_ten).where(NhanVien.id == bv.duoc_si_duyet_id))
        if bv.duoc_si_duyet_id
        else None
    )
    return BaiVietChiTiet(
        **_tom_tat(bv, tac_gia or ""),
        noi_dung=bv.noi_dung,
        anh_bia_url=bv.anh_bia_url,
        dua_vao_ai=bv.dua_vao_ai,
        duoc_si_duyet=nguoi_duyet,
        ngay_duyet=bv.ngay_duyet,
        phien_ban=phien_ban_bai_viet(bv),
    )


async def _lay(db: AsyncSession, bai_viet_id: int, *, khoa: bool = False) -> BaiViet:
    stmt = select(BaiViet).where(BaiViet.id == bai_viet_id, BaiViet.loai == LoaiBaiViet.bai_viet)
    if khoa:
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    bv = (await db.execute(stmt)).scalar_one_or_none()
    if bv is None:
        raise _khong_tim_thay()
    return bv


async def lay(db: AsyncSession, bai_viet_id: int) -> BaiVietChiTiet:
    return await _chi_tiet(db, await _lay(db, bai_viet_id))


async def duyet(db: AsyncSession, actor: NhanVien, bai_viet_id: int, phien_ban: str, *, ip: str) -> BaiVietChiTiet:
    """`nhap` -> `da_duyet`, ghi người duyệt và ngày duyệt. Duyệt bài không còn ở `nhap` hoặc đã bị sửa sau khi dược sĩ
    mở (`phien_ban` lệch) là `409`."""
    await dam_bao_la_duoc_si(db, actor)
    bv = await _lay(db, bai_viet_id, khoa=True)
    if bv.trang_thai != TrangThaiNoiDung.nhap:
        raise LoiNghiepVu("DU_LIEU_DA_THAY_DOI", "Bài viết này không còn ở trạng thái chờ duyệt")
    hien_tai = phien_ban_bai_viet(bv)
    if hien_tai != phien_ban:
        raise LoiNghiepVu(
            "DU_LIEU_DA_THAY_DOI",
            "Bài viết đã được sửa sau khi bạn mở. Hãy đọc lại bản mới rồi duyệt",
            chi_tiet={"phien_ban_hien_tai": hien_tai},
        )
    bv.trang_thai = TrangThaiNoiDung.da_duyet
    bv.duoc_si_duyet_id = actor.id
    bv.ngay_duyet = bay_gio_utc()
    await db.flush()
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="duyet",
        bang=BANG,
        ban_ghi_id=bv.id,
        gia_tri_cu={"trang_thai": "nhap"},
        gia_tri_moi={"trang_thai": "da_duyet"},
        ip=ip,
    )
    return await _chi_tiet(db, bv)

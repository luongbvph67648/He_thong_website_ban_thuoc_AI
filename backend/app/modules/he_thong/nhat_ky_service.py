"""Tra cứu nhật ký hệ thống (AD15): chỉ đọc, giá trị luôn đi qua `che_khi_doc` (không lộ sức khỏe hay bí mật)."""

from collections.abc import Sequence
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.loi import LoiNghiepVu
from app.core.nhat_ky import che_khi_doc
from app.core.phan_trang import ThamSoPhanTrang, lay_trang
from app.core.thoi_gian import VN_TZ
from app.models.he_thong import NhanVien, NhatKyHeThong
from app.modules.he_thong.schemas import GiaTriLocNhatKy, NhanVienTomTat, NhatKyDoc

TOI_DA_GIA_TRI_LOC = 200


def _dau_ngay_vn(ngay: date) -> datetime:
    return datetime.combine(ngay, time.min, tzinfo=VN_TZ)


async def tim(
    db: AsyncSession,
    *,
    bang: str | None,
    ban_ghi_id: str | None,
    nhan_vien_id: int | None,
    hanh_dong: str | None,
    tu_ngay: date | None,
    den_ngay: date | None,
    tp: ThamSoPhanTrang,
) -> tuple[Sequence[NhatKyHeThong], int]:
    """Các bộ lọc kết hợp bằng AND; `tu_ngay`, `den_ngay` là ngày theo giờ Việt Nam và gồm cả hai đầu."""
    if tu_ngay and den_ngay and tu_ngay > den_ngay:
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE",
            "Dữ liệu không hợp lệ",
            chi_tiet=[{"truong": "tu_ngay", "loi": "Ngày bắt đầu phải trước hoặc bằng ngày kết thúc"}],
        )
    stmt = select(NhatKyHeThong).options(
        selectinload(NhatKyHeThong.nhan_vien).load_only(NhanVien.id, NhanVien.ma_nhan_vien, NhanVien.ho_ten)
    )
    if bang:
        stmt = stmt.where(NhatKyHeThong.bang == bang)
    if ban_ghi_id:
        stmt = stmt.where(NhatKyHeThong.ban_ghi_id == ban_ghi_id)
    if nhan_vien_id is not None:
        stmt = stmt.where(NhatKyHeThong.nhan_vien_id == nhan_vien_id)
    if hanh_dong:
        stmt = stmt.where(NhatKyHeThong.hanh_dong == hanh_dong)
    if tu_ngay:
        stmt = stmt.where(NhatKyHeThong.created_at >= _dau_ngay_vn(tu_ngay))
    if den_ngay:
        stmt = stmt.where(NhatKyHeThong.created_at < _dau_ngay_vn(den_ngay + timedelta(days=1)))
    return await lay_trang(db, stmt.order_by(NhatKyHeThong.created_at.desc(), NhatKyHeThong.id.desc()), tp)


def doc(dong: NhatKyHeThong) -> NhatKyDoc:
    return NhatKyDoc(
        id=dong.id,
        created_at=dong.created_at,
        nhan_vien=NhanVienTomTat.model_validate(dong.nhan_vien) if dong.nhan_vien else None,
        hanh_dong=dong.hanh_dong,
        bang=dong.bang,
        ban_ghi_id=dong.ban_ghi_id,
        gia_tri_cu=che_khi_doc(dong.bang, dong.gia_tri_cu),
        gia_tri_moi=che_khi_doc(dong.bang, dong.gia_tri_moi),
        ip=dong.ip,
    )


async def gia_tri_loc(db: AsyncSession) -> GiaTriLocNhatKy:
    """Các `bang` và `hanh_dong` đang có trong nhật ký (tối đa `TOI_DA_GIA_TRI_LOC` mỗi loại) để dựng ô lọc."""

    async def khac_nhau(cot) -> list[str]:
        truy_van = select(cot).distinct().order_by(cot).limit(TOI_DA_GIA_TRI_LOC)
        return list((await db.execute(truy_van)).scalars())

    return GiaTriLocNhatKy(bang=await khac_nhau(NhatKyHeThong.bang), hanh_dong=await khac_nhau(NhatKyHeThong.hanh_dong))

"""AI07: sản phẩm tương tự và "dành cho bạn" (spec 07 mục 7). Mọi thẻ ra khỏi module đều qua `loc_an_toan.the_hop_le`.

Tương tự: (1) cùng tập hoạt chất, (2) cùng danh mục, (3) gần nhất theo vector của đoạn "tổng quan"; mỗi tầng xếp bán
chạy trước. Tầng vector chỉ chạy khi module `goi_y` bật và sản phẩm đã có vector, nên hai tầng đầu luôn là dự phòng."""

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import embedding
from app.core.thoi_gian import bay_gio_utc
from app.models.ai import LichSuXem, TaiLieuTriThuc
from app.models.ban_hang import CtDonHang, DonHang
from app.models.enums import LoaiSanPham, TrangThaiDon
from app.models.khach_hang import KhachHang
from app.models.san_pham import SanPham, ThanhPhan
from app.modules.ai_quan_tri import cau_hinh_ai
from app.modules.cua_hang.hien_thi import ban_chay_30_ngay, la_hien_thi, nap_cay_hien_thi
from app.modules.cua_hang.loc_an_toan import di_ung_cua_khach, loc_di_ung, the_hop_le
from app.modules.cua_hang.schemas import SanPhamThe
from app.modules.cua_hang.tim_kiem_lai import NGUONG_KHOANG_CACH

SO_GOI_Y = 8
SO_UNG_VIEN = 40
"""Lấy dư rồi mới lọc an toàn, để sau lọc vẫn đủ `SO_GOI_Y`."""
SO_NGAY_LICH_SU = 30


def _gop(*nhom: list[int]) -> list[int]:
    """Nối các tầng giữ thứ tự, bỏ trùng."""
    thay: dict[int, None] = {}
    for n in nhom:
        for i in n:
            thay.setdefault(i, None)
    return list(thay)


async def _cung_tap_hoat_chat(db: AsyncSession, sp_id: int, ids_hoat_chat: list[int], dieu_kien) -> list[int]:
    if not ids_hoat_chat:
        return []
    gop = ban_chay_30_ngay()
    cung = (
        select(ThanhPhan.san_pham_id)
        .group_by(ThanhPhan.san_pham_id)
        .having(
            func.count() == len(ids_hoat_chat),
            func.count().filter(ThanhPhan.hoat_chat_id.in_(ids_hoat_chat)) == len(ids_hoat_chat),
        )
    )
    return list(
        (
            await db.execute(
                select(SanPham.id)
                .outerjoin(gop, gop.c.san_pham_id == SanPham.id)
                .where(*dieu_kien, SanPham.id != sp_id, SanPham.id.in_(cung))
                .order_by(func.coalesce(gop.c.so_dong, 0).desc(), SanPham.id)
                .limit(SO_UNG_VIEN)
            )
        ).scalars()
    )


async def _cung_danh_muc(db: AsyncSession, sp: SanPham, dieu_kien) -> list[int]:
    gop = ban_chay_30_ngay()
    return list(
        (
            await db.execute(
                select(SanPham.id)
                .outerjoin(gop, gop.c.san_pham_id == SanPham.id)
                .where(*dieu_kien, SanPham.id != sp.id, SanPham.danh_muc_id == sp.danh_muc_id)
                .order_by(func.coalesce(gop.c.so_dong, 0).desc(), SanPham.id)
                .limit(SO_UNG_VIEN)
            )
        ).scalars()
    )


async def _gan_vector(db: AsyncSession, sp_id: int) -> list[int]:
    goc = await db.scalar(
        select(TaiLieuTriThuc.embedding).where(
            TaiLieuTriThuc.san_pham_id == sp_id,
            TaiLieuTriThuc.truong == "tong_quan",
            TaiLieuTriThuc.embedding.is_not(None),
            TaiLieuTriThuc.mo_hinh_embedding == embedding.ten_mo_hinh(),
        )
    )
    if goc is None:
        return []
    kc = TaiLieuTriThuc.embedding.cosine_distance(goc)
    hang = (
        await db.execute(
            select(TaiLieuTriThuc.san_pham_id, kc.label("kc"))
            .where(
                TaiLieuTriThuc.truong == "tong_quan",
                TaiLieuTriThuc.san_pham_id.is_not(None),
                TaiLieuTriThuc.san_pham_id != sp_id,
                TaiLieuTriThuc.embedding.is_not(None),
                TaiLieuTriThuc.mo_hinh_embedding == embedding.ten_mo_hinh(),
                TaiLieuTriThuc.metadata_["can_ke_don"].astext == "false",
            )
            .order_by(kc)
            .limit(SO_UNG_VIEN)
        )
    ).all()
    return [sp for sp, k in hang if k <= NGUONG_KHOANG_CACH]


async def san_pham_tuong_tu(
    db: AsyncSession, sp: SanPham, ids_hoat_chat: list[int], khach: KhachHang | None, *, gioi_han: int = SO_GOI_Y
) -> list[SanPhamThe]:
    cay = await nap_cay_hien_thi(db)
    dieu_kien = [la_hien_thi(cay.ids), SanPham.loai_san_pham != LoaiSanPham.thuoc_ke_don]
    ids_di_ung = await di_ung_cua_khach(db, khach)
    if ids_di_ung:
        dieu_kien.append(loc_di_ung(ids_di_ung))
    tang1 = await _cung_tap_hoat_chat(db, sp.id, ids_hoat_chat, dieu_kien)
    tang2 = await _cung_danh_muc(db, sp, dieu_kien)
    tang3 = await _gan_vector(db, sp.id) if await cau_hinh_ai.module_bat(db, "goi_y") else []
    ids = _gop(tang1, tang2, tang3)
    # Hai tầng đầu đã lọc ở SQL; tầng vector chưa, và mọi thẻ vẫn phải qua bộ lọc chung trước khi ra khỏi hàm.
    return (await the_hop_le(db, ids, ids_di_ung))[:gioi_han]


async def danh_cho_ban(
    db: AsyncSession, khach: KhachHang | None, ma_phien: str | None, *, gioi_han: int = SO_GOI_Y
) -> list[SanPhamThe]:
    """Danh mục khách xem trong 30 ngày, sản phẩm bán chạy trong các danh mục đó mà khách chưa mua. Chưa có lịch sử
    (hoặc module tắt) thì rỗng: giao diện tự ẩn khu này."""
    if khach is None and ma_phien is None:
        return []
    if not await cau_hinh_ai.module_bat(db, "goi_y"):
        return []
    cua_toi = LichSuXem.khach_hang_id == khach.id if khach is not None else LichSuXem.ma_phien == ma_phien
    danh_muc_xem = (
        select(SanPham.danh_muc_id)
        .join(LichSuXem, LichSuXem.san_pham_id == SanPham.id)
        .where(cua_toi, LichSuXem.created_at >= bay_gio_utc() - timedelta(days=SO_NGAY_LICH_SU))
    )
    cay = await nap_cay_hien_thi(db)
    dieu_kien = [
        la_hien_thi(cay.ids),
        SanPham.loai_san_pham != LoaiSanPham.thuoc_ke_don,
        SanPham.danh_muc_id.in_(danh_muc_xem),
    ]
    if khach is not None:
        da_mua = (
            select(CtDonHang.san_pham_id)
            .join(DonHang, DonHang.id == CtDonHang.don_hang_id)
            .where(DonHang.khach_hang_id == khach.id, DonHang.trang_thai != TrangThaiDon.da_huy)
        )
        dieu_kien.append(SanPham.id.not_in(da_mua))
    ids_di_ung = await di_ung_cua_khach(db, khach)
    if ids_di_ung:
        dieu_kien.append(loc_di_ung(ids_di_ung))
    gop = ban_chay_30_ngay()
    ids = list(
        (
            await db.execute(
                select(SanPham.id)
                .outerjoin(gop, gop.c.san_pham_id == SanPham.id)
                .where(*dieu_kien)
                .order_by(func.coalesce(gop.c.so_dong, 0).desc(), SanPham.id)
                .limit(SO_UNG_VIEN)
            )
        ).scalars()
    )
    return (await the_hop_le(db, ids, ids_di_ung))[:gioi_han]

"""Tìm kiếm từ khóa (KVL04, T2.5): tên sản phẩm, hoạt chất và tên khác, không dấu, gõ sai, theo tiền tố.

Dùng `word_similarity` (toán tử `<%`, ngưỡng mặc định 0.6 của pg_trgm) trên ĐÚNG biểu thức `f_unaccent(lower(...))`
của các index GIN ở spec 02 mục 4.1 để PostgreSQL dùng được index. Không dùng `%`: nó so cả chuỗi nên từ khóa ngắn
hoặc đang gõ dở bị điểm thấp. Tìm theo ngữ nghĩa (triệu chứng, công dụng) nối vào ở T7.2.

Xếp hạng (spec 11 T2.5): độ khớp (làm tròn 0,1 để chênh lệch nhỏ không lấn át các tiêu chí sau), rồi còn hàng, rồi
bán chạy 30 ngày, rồi độ khớp thô và id (thứ tự ổn định giữa các trang).
"""

import re
from datetime import timedelta

from sqlalchemy import ColumnElement, Numeric, Text, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.phan_trang import ThamSoPhanTrang, Trang, tao_trang
from app.core.thoi_gian import bay_gio_utc, hom_nay_vn
from app.models.ai import LichSuTimKiem
from app.models.khach_hang import KhachHang
from app.models.san_pham import HoatChat, SanPham, ThanhPhan
from app.modules.cua_hang.danh_sach import chon_the, dung_the
from app.modules.cua_hang.hien_thi import (
    CayHienThi,
    ban_chay_30_ngay,
    la_hien_thi,
    nap_cay_hien_thi,
    ton_kha_dung,
)
from app.modules.cua_hang.schemas import GoiYTimKiem, SanPhamThe

TOI_THIEU_KY_TU = 2
TOI_DA_KY_TU = 100
TOI_DA_GOI_Y = 8
TOI_DA_GOI_Y_HOAT_CHAT = 2
CUA_SO_GHI_TRUNG = timedelta(minutes=30)
_KHOANG_TRANG = re.compile(r"\s+")


def chuan_hoa_tu_khoa(q: str | None) -> str:
    """Bỏ khoảng trắng thừa (kể cả xuống dòng, tab), cắt ở 100 ký tự. Rỗng nghĩa là không tìm."""
    return _KHOANG_TRANG.sub(" ", (q or "").strip())[:TOI_DA_KY_TU].strip()


def _chuan(cot: ColumnElement) -> ColumnElement:
    return func.f_unaccent(func.lower(cot))


def _bo_dieu_kien(q: str) -> tuple[ColumnElement[bool], ColumnElement[float], ColumnElement[bool]]:
    """(điều kiện khớp sản phẩm, điểm khớp, điều kiện khớp hoạt chất) cho từ khóa đã chuẩn hóa."""
    qn = _chuan(literal(q, type_=Text))
    ten_sp = _chuan(SanPham.ten)
    ten_hc = _chuan(HoatChat.ten)
    ten_khac = _chuan(func.coalesce(HoatChat.ten_khac, ""))
    khop_hc = or_(qn.op("<%")(ten_hc), qn.op("<%")(ten_khac))
    diem_hc = (
        select(func.max(func.greatest(func.word_similarity(qn, ten_hc), func.word_similarity(qn, ten_khac))))
        .select_from(ThanhPhan)
        .join(HoatChat, HoatChat.id == ThanhPhan.hoat_chat_id)
        .where(ThanhPhan.san_pham_id == SanPham.id)
        .correlate(SanPham)
        .scalar_subquery()
    )
    hc_khop_ids = select(HoatChat.id).where(khop_hc)
    khop_sp = or_(
        qn.op("<%")(ten_sp),
        SanPham.id.in_(select(ThanhPhan.san_pham_id).where(ThanhPhan.hoat_chat_id.in_(hc_khop_ids))),
    )
    diem = func.greatest(func.word_similarity(qn, ten_sp), func.coalesce(diem_hc, 0.0))
    return khop_sp, diem, khop_hc


async def tim_san_pham(
    db: AsyncSession, q: str, tp: ThamSoPhanTrang, cay: CayHienThi | None = None
) -> Trang[SanPhamThe]:
    """Trang kết quả cho từ khóa đã chuẩn hóa (`chuan_hoa_tu_khoa`); từ khóa quá ngắn thì rỗng."""
    if len(q) < TOI_THIEU_KY_TU:
        return tao_trang([], 0, tp)
    cay = cay or await nap_cay_hien_thi(db)
    khop, diem, _ = _bo_dieu_kien(q)
    dieu_kien = [la_hien_thi(cay.ids), khop]
    tong = await db.scalar(select(func.count()).select_from(SanPham).where(*dieu_kien)) or 0
    ban_chay = ban_chay_30_ngay()
    ton = ton_kha_dung(hom_nay_vn())
    dong = (
        await db.execute(
            chon_the()
            .outerjoin(ban_chay, ban_chay.c.san_pham_id == SanPham.id)
            .where(*dieu_kien)
            .order_by(
                func.round(diem.cast(Numeric(4, 2)), 1).desc(),
                (ton > 0).desc(),
                func.coalesce(ban_chay.c.so_dong, 0).desc(),
                diem.desc(),
                SanPham.id,
            )
            .limit(tp.limit)
            .offset(tp.offset)
        )
    ).all()
    return tao_trang(await dung_the(db, dong), tong, tp)


async def goi_y(db: AsyncSession, q: str) -> list[GoiYTimKiem]:
    """Tối đa 8 gợi ý khi đang gõ: sản phẩm xếp như kết quả tìm, sau đó tối đa 2 hoạt chất có sản phẩm hiển thị."""
    if len(q) < TOI_THIEU_KY_TU:
        return []
    cay = await nap_cay_hien_thi(db)
    trang = await tim_san_pham(db, q, ThamSoPhanTrang(1, TOI_DA_GOI_Y - TOI_DA_GOI_Y_HOAT_CHAT), cay)
    ket: list[GoiYTimKiem] = [
        GoiYTimKiem(kieu="san_pham", ten=t.ten, slug=t.slug, loai_san_pham=t.loai_san_pham, can_tu_van=t.can_tu_van)
        for t in trang.du_lieu
    ]
    _, _, khop_hc = _bo_dieu_kien(q)
    qn = _chuan(literal(q, type_=Text))
    diem_hc = func.greatest(
        func.word_similarity(qn, _chuan(HoatChat.ten)),
        func.word_similarity(qn, _chuan(func.coalesce(HoatChat.ten_khac, ""))),
    )
    hoat_chat = (
        (
            await db.execute(
                select(HoatChat.ten)
                .where(
                    khop_hc,
                    HoatChat.id.in_(
                        select(ThanhPhan.hoat_chat_id)
                        .join(SanPham, SanPham.id == ThanhPhan.san_pham_id)
                        .where(la_hien_thi(cay.ids))
                    ),
                )
                .order_by(diem_hc.desc(), HoatChat.id)
                .limit(TOI_DA_GOI_Y_HOAT_CHAT)
            )
        )
        .scalars()
        .all()
    )
    ket += [GoiYTimKiem(kieu="hoat_chat", ten=t, slug=None, loai_san_pham=None, can_tu_van=False) for t in hoat_chat]
    return ket[:TOI_DA_GOI_Y]


async def ghi_lich_su_tim_kiem(
    db: AsyncSession, q: str, so_ket_qua: int, *, khach: KhachHang | None, ma_phien: str | None
) -> None:
    """Ghi `lich_su_tim_kiem` (`che_do = tu_khoa`). Khách đăng nhập theo token, vãng lai theo mã phiên. Cùng người tìm
    cùng từ khóa (không phân biệt hoa thường) trong 30 phút chỉ giữ một dòng."""
    tu_khoa = q[:255]
    nguoi = (
        LichSuTimKiem.khach_hang_id == khach.id
        if khach is not None
        else (LichSuTimKiem.ma_phien == ma_phien if ma_phien is not None else LichSuTimKiem.ma_phien.is_(None))
    )
    da_co = await db.scalar(
        select(LichSuTimKiem.id)
        .where(
            nguoi,
            func.lower(LichSuTimKiem.tu_khoa) == tu_khoa.lower(),
            LichSuTimKiem.created_at >= bay_gio_utc() - CUA_SO_GHI_TRUNG,
        )
        .limit(1)
    )
    if da_co is not None:
        return
    db.add(
        LichSuTimKiem(
            khach_hang_id=khach.id if khach is not None else None,
            ma_phien=None if khach is not None else ma_phien,
            tu_khoa=tu_khoa,
            che_do="tu_khoa",
            so_ket_qua=so_ket_qua,
        )
    )
    await db.flush()

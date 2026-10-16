"""Hàm kiểm tra bất biến tồn kho bằng SQL (spec 04 mục 3.2, spec 10 mục 4). Trả danh sách mô tả vi phạm, rỗng là đạt.

Có bất biến 1 đến 3 (chỉ cần bảng kho). Bất biến 4 và 5 gắn với đơn hàng nên thêm cùng module bán hàng (T4.4).
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_KIEM_TRA = {
    "1: tồn, giữ hoặc biệt trữ vi phạm 0 <= giữ <= tồn": (
        "SELECT id FROM lo_thuoc WHERE so_luong_ton < 0 OR so_luong_giu < 0 OR so_luong_giu > so_luong_ton "
        "OR so_luong_biet_tru < 0"
    ),
    "2: so_luong_giu khác tổng phân bổ dang_giu": (
        "SELECT l.id FROM lo_thuoc l LEFT JOIN ("
        " SELECT lo_id, sum(so_luong_co_so) AS giu FROM phan_bo_lo WHERE trang_thai = 'dang_giu' GROUP BY lo_id"
        ") p ON p.lo_id = l.id WHERE l.so_luong_giu <> coalesce(p.giu, 0)"
    ),
    "3: tồn hoặc biệt trữ khác tổng thẻ kho": (
        "SELECT l.id FROM lo_thuoc l LEFT JOIN ("
        " SELECT lo_id, sum(so_luong) FILTER (WHERE khu = 'kho_ban') AS ban,"
        " sum(so_luong) FILTER (WHERE khu = 'biet_tru') AS bt FROM bien_dong_kho GROUP BY lo_id"
        ") b ON b.lo_id = l.id WHERE l.so_luong_ton <> coalesce(b.ban, 0) OR l.so_luong_biet_tru <> coalesce(b.bt, 0)"
    ),
    "3: ton_sau của thẻ kho cuối khác tồn hiện tại": (
        "SELECT l.id FROM lo_thuoc l JOIN LATERAL ("
        " SELECT khu, ton_sau FROM bien_dong_kho WHERE lo_id = l.id ORDER BY id DESC LIMIT 1) cuoi ON true "
        "JOIN LATERAL (SELECT ton_sau AS ban FROM bien_dong_kho WHERE lo_id = l.id AND khu = 'kho_ban'"
        " ORDER BY id DESC LIMIT 1) t ON true WHERE t.ban <> l.so_luong_ton"
    ),
}


async def kiem_tra_bat_bien(db: AsyncSession) -> list[str]:
    """Chạy các bất biến; mỗi vi phạm là một chuỗi `"<bất biến>: lô <id>"`."""
    vi_pham: list[str] = []
    for ten, sql in _KIEM_TRA.items():
        vi_pham += [f"{ten}: lô {dong[0]}" for dong in (await db.execute(text(sql))).all()]
    return vi_pham

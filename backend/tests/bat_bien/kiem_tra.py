"""Hàm kiểm tra bất biến tồn kho bằng SQL (spec 04 mục 3.2, spec 10 mục 4). Trả danh sách mô tả vi phạm, rỗng là đạt.

Bất biến 1 đến 3 chỉ cần bảng kho; 4 và 5 gắn với đơn hàng (thêm ở T4.4). Mỗi vi phạm ghi đối tượng sai
(`lô`, `đơn`, `dòng đơn`) theo tên cột đầu của câu SQL.
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
    "4: đơn từ đang soạn hàng trở đi (trừ đã hủy) còn phân bổ dang_giu": (
        "SELECT DISTINCT d.id FROM don_hang d JOIN ct_don_hang c ON c.don_hang_id = d.id "
        "JOIN phan_bo_lo p ON p.ct_don_hang_id = c.id WHERE p.trang_thai = 'dang_giu' AND d.trang_thai IN "
        "('dang_soan_hang','cho_lay_hang','dang_giao','da_giao','hoan_tat','giao_that_bai','hoan_ve_kho','da_huy')"
    ),
    "5: dòng đơn chưa hủy có tổng phân bổ khác so_luong x he_so": (
        "SELECT c.id FROM ct_don_hang c JOIN don_hang d ON d.id = c.don_hang_id LEFT JOIN ("
        " SELECT ct_don_hang_id, sum(so_luong_co_so) AS tong FROM phan_bo_lo"
        " WHERE trang_thai IN ('dang_giu','da_xuat','da_hoan_nhap') GROUP BY ct_don_hang_id"
        ") p ON p.ct_don_hang_id = c.id WHERE d.trang_thai <> 'da_huy' AND coalesce(p.tong, 0) <> c.so_luong * c.he_so"
    ),
}


async def kiem_tra_bat_bien(db: AsyncSession, *, co_don_hang: bool = True) -> list[str]:
    """Chạy các bất biến (`co_don_hang=False`: chỉ 1 đến 3, cho test dựng đơn bằng factory mà không phân bổ đủ); mỗi vi phạm là một chuỗi `"<bất biến>: <lô|đơn|dòng đơn> <id>"`."""
    vi_pham: list[str] = []
    for ten, sql in _KIEM_TRA.items():
        if not co_don_hang and ten[0] in "45":
            continue
        vi_pham += [
            f"{ten}: {'dòng đơn' if ten[0] == '5' else 'đơn' if ten[0] == '4' else 'lô'} {dong[0]}"
            for dong in (await db.execute(text(sql))).all()
        ]
    return vi_pham

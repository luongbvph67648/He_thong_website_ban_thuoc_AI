"""AI08 (job hằng tuần): tính luật "thường được mua cùng" từ đơn `hoan_tat` 180 ngày, ghi đè `luat_mua_kem`.

Tính hoàn toàn bằng SQL (spec 07 mục 7). Mỗi đơn đếm một lần cho mỗi sản phẩm; thuốc kê đơn bị loại ở cả hai vế (không
bao giờ có trong giỏ nên cũng không được gợi ý). Luật có hướng: (A, B) và (B, A) là hai dòng riêng."""

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import delete, insert, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.thoi_gian import bay_gio_utc
from app.models.ai import LuatMuaKem
from app.modules.ai_quan_tri import cau_hinh_ai

SO_NGAY = 180
SUPPORT_TOI_THIEU = Decimal("0.005")
CONFIDENCE_TOI_THIEU = Decimal("0.1")
LIFT_TOI_THIEU = Decimal(1)

_SQL = text(
    """
WITH don AS (
    SELECT d.id
    FROM don_hang d
    WHERE d.trang_thai = 'hoan_tat'
      AND coalesce(
            (SELECT max(l.created_at) FROM lich_su_trang_thai l
              WHERE l.don_hang_id = d.id AND l.den_trang_thai = 'hoan_tat'),
            d.created_at) >= :moc
),
dong AS (
    SELECT DISTINCT c.don_hang_id, c.san_pham_id
    FROM ct_don_hang c
    JOIN don ON don.id = c.don_hang_id
    JOIN san_pham s ON s.id = c.san_pham_id
    WHERE s.loai_san_pham <> 'thuoc_ke_don'
),
tong AS (SELECT count(*)::numeric AS n FROM don),
dem_sp AS (SELECT san_pham_id, count(*)::numeric AS so FROM dong GROUP BY san_pham_id),
cap AS (
    SELECT a.san_pham_id AS a, b.san_pham_id AS b, count(*)::numeric AS so
    FROM dong a JOIN dong b ON a.don_hang_id = b.don_hang_id AND a.san_pham_id <> b.san_pham_id
    GROUP BY a.san_pham_id, b.san_pham_id
)
SELECT cap.a, cap.b,
       cap.so / tong.n AS support,
       cap.so / sa.so AS confidence,
       (cap.so / sa.so) / (sb.so / tong.n) AS lift
FROM cap
CROSS JOIN tong
JOIN dem_sp sa ON sa.san_pham_id = cap.a
JOIN dem_sp sb ON sb.san_pham_id = cap.b
WHERE tong.n > 0
  AND cap.so / tong.n >= :support
  AND cap.so / sa.so >= :confidence
  AND (cap.so / sa.so) / (sb.so / tong.n) > :lift
ORDER BY cap.a, cap.b
"""
)


@dataclass
class KetQuaAi08:
    bo_qua: bool = False
    so_luat: int = 0


def _lam_tron(v: Decimal, chu_so: str) -> Decimal:
    return v.quantize(Decimal(chu_so))


async def tinh_luat_mua_kem(db: AsyncSession) -> KetQuaAi08:
    """Một transaction: xóa luật cũ rồi ghi luật mới (lỗi giữa chừng thì rollback, giữ nguyên luật cũ)."""
    if not await cau_hinh_ai.module_bat(db, "goi_y"):
        return KetQuaAi08(bo_qua=True)
    hang = (
        await db.execute(
            _SQL,
            {
                "moc": bay_gio_utc() - timedelta(days=SO_NGAY),
                "support": SUPPORT_TOI_THIEU,
                "confidence": CONFIDENCE_TOI_THIEU,
                "lift": LIFT_TOI_THIEU,
            },
        )
    ).all()
    await db.execute(delete(LuatMuaKem))
    if hang:
        await db.execute(
            insert(LuatMuaKem),
            [
                {
                    "san_pham_a_id": h.a,
                    "san_pham_b_id": h.b,
                    "support": _lam_tron(h.support, "0.000001"),
                    "confidence": _lam_tron(h.confidence, "0.000001"),
                    "lift": _lam_tron(h.lift, "0.0001"),
                    "updated_at": bay_gio_utc(),
                }
                for h in hang
            ],
        )
    return KetQuaAi08(so_luat=len(hang))

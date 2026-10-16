"""HT05: nhận sự kiện vận chuyển và cập nhật đơn qua máy trạng thái (spec 08 mục 5, spec 04 dòng 22 đến 26).

Webhook của đối tác có thể đến lặp, trễ hoặc sai thứ tự nên mọi sự kiện đều an toàn khi xử lý lại: trạng thái đối tác
luôn được ghi vào `van_don`, còn đơn chỉ đi tới trạng thái mới nếu có đường đi hợp lệ từ trạng thái hiện tại.
"""

import logging
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.thoi_gian import bay_gio_utc
from app.models.ban_hang import DonHang, VanDon
from app.models.enums import LoaiVanDon
from app.modules.ban_hang.trang_thai import NGUON_VAN_CHUYEN, TacNhan, chuyen_trang_thai
from app.tich_hop.van_chuyen import SuKienVanChuyen
from app.tich_hop.van_chuyen.anh_xa import duong_di, trang_thai_muc_tieu

logger = logging.getLogger(__name__)


class KetQuaSuKien(StrEnum):
    da_xu_ly = "da_xu_ly"
    khong_tim_thay = "khong_tim_thay"


async def xu_ly_su_kien(db: AsyncSession, su_kien: SuKienVanChuyen) -> KetQuaSuKien:
    van_don = (
        await db.execute(
            select(VanDon).where(VanDon.ma_van_don == su_kien.ma_van_don, VanDon.loai == LoaiVanDon.giao_hang)
        )
    ).scalar_one_or_none()
    if van_don is None:
        logger.warning("Webhook vận chuyển cho mã vận đơn không có: %s", su_kien.ma_van_don)
        return KetQuaSuKien.khong_tim_thay
    don = (
        await db.execute(
            select(DonHang)
            .where(DonHang.id == van_don.don_hang_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    van_don.trang_thai_doi_tac = su_kien.trang_thai_doi_tac[:50]
    van_don.du_lieu_webhook = su_kien.du_lieu
    van_don.updated_at = bay_gio_utc()
    moi_nhat = await db.scalar(
        select(VanDon.id)
        .where(VanDon.don_hang_id == don.id, VanDon.loai == LoaiVanDon.giao_hang)
        .order_by(VanDon.id.desc())
        .limit(1)
    )
    if moi_nhat != van_don.id:  # vận đơn cũ (đã tạo lại): chỉ ghi nhận
        await db.flush()
        return KetQuaSuKien.da_xu_ly
    muc_tieu = trang_thai_muc_tieu(su_kien.trang_thai_doi_tac, don.trang_thai)
    for buoc in duong_di(don.trang_thai, muc_tieu) if muc_tieu is not None else []:
        await chuyen_trang_thai(
            db,
            don,
            buoc,
            TacNhan.he_thong(),
            NGUON_VAN_CHUYEN,
            f"{van_don.don_vi_van_chuyen}: {su_kien.trang_thai_doi_tac}",
        )
    await db.flush()
    return KetQuaSuKien.da_xu_ly

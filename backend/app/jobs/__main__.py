"""Worker job nền: `uv run python -m app.jobs`. Giờ chạy theo giờ Việt Nam."""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.db import engine
from app.core.log import cau_hinh_log
from app.core.thoi_gian import VN_TZ
from app.jobs.chay import HamJob, chay_job
from app.jobs.cong_viec import (
    ai06_doc_don_thuoc,
    ai08_luat_mua_kem,
    ai_dong_bo_tri_thuc,
    don_lich_su,
    ht01_cap_nhat_lo,
    ht02_canh_bao_kho,
    ht03_huy_qua_han,
    ht07_nhac_mua_lai,
    ht08_tu_hoan_tat,
)

# (tên, hàm, giờ, phút): HT01 00:05 hằng ngày; HT02 sau HT01 để cảnh báo thấy trạng thái lô mới.
LICH: tuple[tuple[str, HamJob, int, int], ...] = (
    ("ht01_lo", ht01_cap_nhat_lo, 0, 5),
    ("ht02_canh_bao_kho", ht02_canh_bao_kho, 7, 0),
    ("ht07_nhac_mua_lai", ht07_nhac_mua_lai, 8, 0),
    ("ai_dong_bo_tri_thuc", ai_dong_bo_tri_thuc, 2, 30),
    ("don_lich_su", don_lich_su, 3, 30),
)
# Job hằng tuần: (tên, hàm, thứ trong tuần theo cron, giờ, phút). AI08 vào Chủ nhật 03:00, lúc ít người mua.
LICH_TUAN: tuple[tuple[str, HamJob, str, int, int], ...] = (("ai08_luat_mua_kem", ai08_luat_mua_kem, "sun", 3, 0),)
# Job chạy theo chu kỳ phút: (tên, hàm, số phút giữa hai lần). HT03 hủy đơn quá hạn; HT08 tự hoàn tất đơn.
LICH_PHUT: tuple[tuple[str, HamJob, int], ...] = (
    ("ht03_huy_qua_han", ht03_huy_qua_han, 1),
    ("ht08_tu_hoan_tat", ht08_tu_hoan_tat, 15),
    ("ai06_doc_don_thuoc", ai06_doc_don_thuoc, 1),
)


def tao_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=VN_TZ)
    for ten, ham, gio, phut in LICH:
        scheduler.add_job(
            chay_job,
            CronTrigger(hour=gio, minute=phut, timezone=VN_TZ),
            args=[engine, ten, ham],
            id=ten,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=3600,
        )
    for ten, ham, thu, gio, phut in LICH_TUAN:
        scheduler.add_job(
            chay_job,
            CronTrigger(day_of_week=thu, hour=gio, minute=phut, timezone=VN_TZ),
            args=[engine, ten, ham],
            id=ten,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=3600,
        )
    for ten, ham, phut in LICH_PHUT:
        scheduler.add_job(
            chay_job,
            IntervalTrigger(minutes=phut),
            args=[engine, ten, ham],
            id=ten,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=60,
        )
    return scheduler


async def main() -> None:
    cau_hinh_log()
    scheduler = tao_scheduler()
    scheduler.start()
    logging.getLogger("jobs").info(
        "Worker job nền đã chạy: %s", ", ".join(t for t, *_ in (*LICH, *LICH_TUAN, *LICH_PHUT))
    )
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())

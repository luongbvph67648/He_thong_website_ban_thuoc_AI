"""Worker job nền: `uv run python -m app.jobs`. Giờ chạy theo giờ Việt Nam."""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.db import engine
from app.core.log import cau_hinh_log
from app.core.thoi_gian import VN_TZ
from app.jobs.chay import HamJob, chay_job
from app.jobs.cong_viec import don_lich_su, ht01_cap_nhat_lo, ht02_canh_bao_kho

# (tên, hàm, giờ, phút): HT01 00:05 hằng ngày; HT02 sau HT01 để cảnh báo thấy trạng thái lô mới.
LICH: tuple[tuple[str, HamJob, int, int], ...] = (
    ("ht01_lo", ht01_cap_nhat_lo, 0, 5),
    ("ht02_canh_bao_kho", ht02_canh_bao_kho, 7, 0),
    ("don_lich_su", don_lich_su, 3, 30),
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
    return scheduler


async def main() -> None:
    cau_hinh_log()
    scheduler = tao_scheduler()
    scheduler.start()
    logging.getLogger("jobs").info("Worker job nền đã chạy: %s", ", ".join(t for t, *_ in LICH))
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())

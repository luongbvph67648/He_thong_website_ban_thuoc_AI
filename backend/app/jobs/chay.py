"""Chạy một job với `pg_try_advisory_lock` để hai worker (hoặc hai lần chạy chồng nhau) không làm cùng một việc."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

logger = logging.getLogger("jobs")

HamJob = Callable[[AsyncSession], Awaitable[Any]]


async def chay_job(engine: AsyncEngine, ten: str, ham: HamJob) -> Any:
    """Trả kết quả của `ham`, hoặc `None` nếu job đang chạy ở nơi khác. Khóa giữ trên một kết nối riêng suốt lúc chạy
    (khóa tư vấn ở cấp phiên), `ham` chạy trong transaction riêng: lỗi thì rollback, khóa vẫn được nhả."""
    async with engine.connect() as khoa_kn:
        khoa = text("SELECT hashtext(:k)")
        ma = (await khoa_kn.execute(khoa, {"k": f"nha_thuoc.job.{ten}"})).scalar_one()
        if not (await khoa_kn.execute(text("SELECT pg_try_advisory_lock(:m)"), {"m": ma})).scalar_one():
            logger.info("Job %s đang chạy ở nơi khác, bỏ qua", ten)
            return None
        try:
            async with AsyncSession(engine, expire_on_commit=False) as db, db.begin():
                ket_qua = await ham(db)
            logger.info("Job %s xong: %s", ten, ket_qua)
            return ket_qua
        except Exception:
            logger.exception("Job %s lỗi", ten)
            raise
        finally:
            await khoa_kn.execute(text("SELECT pg_advisory_unlock(:m)"), {"m": ma})
            await khoa_kn.commit()

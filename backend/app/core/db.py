from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.core.config import settings


def tao_engine(url: str | URL) -> AsyncEngine:
    """Tạo engine. `hide_parameters=True` để lỗi SQL không ghi giá trị tham số (có thể là SĐT, dữ liệu sức khỏe...)."""
    return create_async_engine(url, pool_pre_ping=True, hide_parameters=True)


engine = tao_engine(settings.DATABASE_URL)


def get_engine() -> AsyncEngine:
    return engine


class PhienRequest(AsyncSession):
    """Session của một request. Việc commit/rollback do `get_db` quản lý, code nghiệp vụ không được gọi.

    SQLAlchemy cho phép `commit()` giữa chừng mà không báo lỗi, khiến phần đã commit ở lại trong DB dù sau đó
    request thất bại. Chặn ở đây để quy tắc "service không commit" được máy kiểm tra thay vì chỉ là lời dặn.
    """

    async def commit(self) -> None:
        raise RuntimeError(
            "Không được gọi commit() trong request: get_db tự commit khi request thành công. "
            "Cần ID của dòng vừa thêm thì dùng `await db.flush()`."
        )

    async def rollback(self) -> None:
        raise RuntimeError(
            "Không được gọi rollback() trong request: hãy raise LoiNghiepVu hoặc ngoại lệ khác, "
            "get_db sẽ rollback. Cần hoàn tác một phần thì dùng `async with db.begin_nested()`."
        )


async def get_db(engine: AsyncEngine = Depends(get_engine)) -> AsyncIterator[PhienRequest]:
    """Một session và một transaction cho mỗi request: commit khi thành công, rollback khi có ngoại lệ."""
    async with PhienRequest(engine, expire_on_commit=False) as session, session.begin():
        yield session


Db = Annotated[PhienRequest, Depends(get_db, scope="function")]
"""Dùng làm tham số của route/dependency: `async def ds(db: Db): ...`

`scope="function"` làm COMMIT chạy ngay sau khi hàm route trả về và TRƯỚC khi gửi response. Mặc định
(`scope="request"`) commit chạy sau khi response đã gửi: client nhận "200" dù commit có thể thất bại.
Hệ quả: response dạng streaming (SSE) không dùng được `db` bên trong generator, phải mở session riêng.
"""

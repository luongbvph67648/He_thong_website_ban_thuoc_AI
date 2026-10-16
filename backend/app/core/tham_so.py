"""Kiểu tham số route dùng chung."""

from typing import Annotated

from fastapi import Path, Query

IdInt = Annotated[int, Path(ge=1, le=2_147_483_647)]
"""Id cột `Integer` trong đường dẫn: số ngoài miền của PostgreSQL bị từ chối 400, không để asyncpg báo lỗi 500."""

IdBigInt = Annotated[int, Path(ge=1, le=9_223_372_036_854_775_807)]
"""Id cột `BigInteger` trong đường dẫn."""

KHONG_NUL = r"^[^\x00]*$"
"""Mẫu cho `Query(pattern=...)`: byte NUL làm PostgreSQL báo lỗi (500), nên chặn từ đầu bằng 400."""


def tu_khoa_tim(mo_ta: str, toi_da: int = 100):
    """Tham số truy vấn `q` của route danh sách: tối đa `toi_da` ký tự và không chứa NUL."""
    return Annotated[str | None, Query(max_length=toi_da, pattern=KHONG_NUL, description=mo_ta)]

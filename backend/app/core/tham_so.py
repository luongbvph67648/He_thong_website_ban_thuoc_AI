"""Kiểu tham số route dùng chung."""

from typing import Annotated

from fastapi import Path

IdInt = Annotated[int, Path(ge=1, le=2_147_483_647)]
"""Id cột `Integer` trong đường dẫn: số ngoài miền của PostgreSQL bị từ chối 400, không để asyncpg báo lỗi 500."""

IdBigInt = Annotated[int, Path(ge=1, le=9_223_372_036_854_775_807)]
"""Id cột `BigInteger` trong đường dẫn."""

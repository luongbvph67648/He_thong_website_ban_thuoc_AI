import logging
from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.db import get_engine

logger = logging.getLogger(__name__)
router = APIRouter()


class SucKhoe(BaseModel):
    trang_thai: Literal["ok", "loi"]
    db: Literal["ok", "loi"]


@router.get(
    "/health",
    summary="Kiểm tra tình trạng hệ thống",
    response_model=SucKhoe,
    responses={503: {"model": SucKhoe, "description": "Không truy vấn được CSDL"}},
)
async def health(engine: AsyncEngine = Depends(get_engine)):
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        logger.warning("Health check: không truy vấn được CSDL", exc_info=True)
        return JSONResponse(status_code=503, content={"trang_thai": "loi", "db": "loi"})
    return {"trang_thai": "ok", "db": "ok"}

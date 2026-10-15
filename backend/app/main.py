from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.log import cau_hinh_log
from app.core.loi import dang_ky_xu_ly_loi
from app.core.middleware import HEADER_REQUEST_ID, RequestIdMiddleware
from app.health import router as health_router


def create_app() -> FastAPI:
    cau_hinh_log()
    app = FastAPI(title="Nhà thuốc AI", version="0.1.0")
    dang_ky_xu_ly_loi(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[HEADER_REQUEST_ID],
    )
    # Thêm sau cùng = bọc ngoài cùng, để cả phản hồi của CORS (preflight) cũng có X-Request-ID.
    app.add_middleware(RequestIdMiddleware)
    app.include_router(health_router, prefix="/api/v1")
    return app


app = create_app()

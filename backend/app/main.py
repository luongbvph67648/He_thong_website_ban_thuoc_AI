from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.log import cau_hinh_log
from app.core.loi import dang_ky_xu_ly_loi
from app.core.middleware import HEADER_REQUEST_ID, RequestIdMiddleware
from app.health import router as health_router
from app.modules.nhan_vien.router_auth import router as nhan_vien_auth_router
from app.modules.nhan_vien.router_noi_bo import router as nhan_vien_noi_bo_router
from app.modules.tai_khoan.router_cong_khai import router as tai_khoan_cong_khai_router
from app.modules.tai_khoan.router_khach import router as tai_khoan_khach_router
from app.modules.thong_bao.router_noi_bo import router as thong_bao_noi_bo_router


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
    app.include_router(tai_khoan_cong_khai_router, prefix="/api/v1")
    app.include_router(tai_khoan_khach_router, prefix="/api/v1")
    app.include_router(nhan_vien_auth_router, prefix="/api/v1")
    app.include_router(nhan_vien_noi_bo_router, prefix="/api/v1")
    app.include_router(thong_bao_noi_bo_router, prefix="/api/v1")
    return app


app = create_app()

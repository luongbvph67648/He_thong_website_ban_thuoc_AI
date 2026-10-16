import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import luu_tru
from app.core.config import settings
from app.core.log import cau_hinh_log
from app.core.loi import dang_ky_xu_ly_loi
from app.core.middleware import HEADER_REQUEST_ID, GioiHanKichThuocThan, QuyTacThanRequest, RequestIdMiddleware
from app.health import router as health_router
from app.modules.chuyen_mon.router_bai_viet import router as bai_viet_duyet_router
from app.modules.chuyen_mon.router_noi_dung import router as noi_dung_chuyen_mon_router
from app.modules.chuyen_mon.router_tuong_tac import router as tuong_tac_router
from app.modules.cua_hang.router import router as cua_hang_router
from app.modules.dia_chi.router import router as dia_chi_router
from app.modules.gio_hang.router import router as gio_hang_router
from app.modules.he_thong.router_cau_hinh import router as cau_hinh_router
from app.modules.he_thong.router_nhat_ky import router as nhat_ky_router
from app.modules.kho.router_bao_cao_nxt import router as bao_cao_nxt_router
from app.modules.kho.router_kiem_ke import router as kiem_ke_router
from app.modules.kho.router_nha_cung_cap import router as nha_cung_cap_router
from app.modules.kho.router_phieu_huy_xuat_tra import router as phieu_huy_xuat_tra_router
from app.modules.kho.router_phieu_nhap import router as phieu_nhap_router
from app.modules.kho.router_ton_kho import router as ton_kho_router
from app.modules.khuyen_mai.router import router as khuyen_mai_router
from app.modules.nhan_vien.router_auth import router as nhan_vien_auth_router
from app.modules.nhan_vien.router_noi_bo import router as nhan_vien_noi_bo_router
from app.modules.nhan_vien.router_quan_tri import router as nhan_vien_quan_tri_router
from app.modules.noi_dung_web.router_cong_khai import router as bai_viet_cong_khai_router
from app.modules.noi_dung_web.router_noi_bo import bai_viet_router as bai_viet_noi_bo_router
from app.modules.noi_dung_web.router_noi_bo import banner_router as banner_noi_bo_router
from app.modules.san_pham.router_danh_muc import router as danh_muc_router
from app.modules.san_pham.router_du_lieu_chung import hoat_chat_router, nha_san_xuat_router, thuong_hieu_router
from app.modules.san_pham.router_san_pham import router as san_pham_router
from app.modules.tai_khoan.router_cong_khai import router as tai_khoan_cong_khai_router
from app.modules.tai_khoan.router_khach import router as tai_khoan_khach_router
from app.modules.tai_khoan.router_quan_tri_khach import router as khach_hang_quan_tri_router
from app.modules.tep.router_cong_khai import router as tep_router
from app.modules.thong_bao.router_noi_bo import router as thong_bao_noi_bo_router
from app.modules.vai_tro.router_noi_bo import router as vai_tro_noi_bo_router

# Mọi route nhận tệp phải có quy tắc ở đây (test `test_moi_route_nhan_tep_deu_co_quy_tac_gioi_han` duyệt OpenAPI).
# Mức = kích thước tệp tối đa cộng phần đầu multipart.
QUY_TAC_THAN_REQUEST = (
    QuyTacThanRequest(
        "POST",
        re.compile(r"/api/v1/noi-bo/san-pham/[0-9]+/anh"),
        luu_tru.TOI_DA_ANH_BYTE + 64 * 1024,
        "TEP_QUA_LON",
        "Ảnh tối đa 5 MB",
    ),
    QuyTacThanRequest(
        "POST",
        re.compile(r"/api/v1/noi-bo/(banner|bai-viet)/anh"),
        luu_tru.TOI_DA_ANH_BYTE + 64 * 1024,
        "TEP_QUA_LON",
        "Ảnh tối đa 5 MB",
    ),
)

# Mọi route ghi còn lại chỉ nhận JSON: FastAPI đọc cả thân vào bộ nhớ trước khi chạy xác thực, nên đặt trần chung
# (đặt SAU quy tắc tệp vì khớp theo thứ tự). Dài nhất hiện nay là nội dung chuyên môn: 10 trường x 20.000 ký tự.
TOI_DA_THAN_JSON_BYTE = 2 * 1024 * 1024
QUY_TAC_THAN_JSON = tuple(
    QuyTacThanRequest(
        phuong_thuc,
        re.compile(r"/api/v1/.*"),
        TOI_DA_THAN_JSON_BYTE,
        "THAN_QUA_LON",
        "Nội dung gửi lên quá lớn",
    )
    for phuong_thuc in ("POST", "PUT", "PATCH", "DELETE")
)


def create_app() -> FastAPI:
    cau_hinh_log()
    app = FastAPI(title="Nhà thuốc AI", version="0.1.0")
    dang_ky_xu_ly_loi(app)
    # Thêm trước CORS = nằm trong CORS: phản hồi 413 vẫn có header CORS nên trình duyệt đọc được thông điệp.
    app.add_middleware(GioiHanKichThuocThan, quy_tac=(*QUY_TAC_THAN_REQUEST, *QUY_TAC_THAN_JSON))
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
    app.include_router(nhan_vien_quan_tri_router, prefix="/api/v1")
    app.include_router(vai_tro_noi_bo_router, prefix="/api/v1")
    app.include_router(khach_hang_quan_tri_router, prefix="/api/v1")
    app.include_router(cau_hinh_router, prefix="/api/v1")
    app.include_router(nhat_ky_router, prefix="/api/v1")
    app.include_router(danh_muc_router, prefix="/api/v1")
    for router_dung_chung in (thuong_hieu_router, nha_san_xuat_router, hoat_chat_router):
        app.include_router(router_dung_chung, prefix="/api/v1")
    app.include_router(san_pham_router, prefix="/api/v1")
    app.include_router(noi_dung_chuyen_mon_router, prefix="/api/v1")
    app.include_router(tuong_tac_router, prefix="/api/v1")
    app.include_router(bai_viet_duyet_router, prefix="/api/v1")
    app.include_router(tep_router, prefix="/api/v1")
    app.include_router(cua_hang_router, prefix="/api/v1")
    app.include_router(banner_noi_bo_router, prefix="/api/v1")
    app.include_router(bai_viet_noi_bo_router, prefix="/api/v1")
    app.include_router(bai_viet_cong_khai_router, prefix="/api/v1")
    app.include_router(nha_cung_cap_router, prefix="/api/v1")
    app.include_router(phieu_nhap_router, prefix="/api/v1")
    app.include_router(ton_kho_router, prefix="/api/v1")
    app.include_router(bao_cao_nxt_router, prefix="/api/v1")
    app.include_router(gio_hang_router, prefix="/api/v1")
    app.include_router(khuyen_mai_router, prefix="/api/v1")
    app.include_router(dia_chi_router, prefix="/api/v1")
    app.include_router(kiem_ke_router, prefix="/api/v1")
    app.include_router(phieu_huy_xuat_tra_router, prefix="/api/v1")
    return app


app = create_app()

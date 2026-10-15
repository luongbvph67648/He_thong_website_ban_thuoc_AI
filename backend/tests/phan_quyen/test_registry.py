"""Registry route nội bộ phải đầy đủ và khớp dependency thật của từng route (spec 10 mục 3)."""

from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.routing import APIRouter

from app.core.phan_quyen import nhan_vien_hien_tai, yeu_cau_quyen
from app.main import create_app
from app.models.he_thong import NhanVien
from tests.phan_quyen.ma_tran import duyet_route, kiem_tra_registry
from tests.phan_quyen.registry import CHO_PHEP_KHI_CHUA_DOI_MAT_KHAU, CONG_KHAI, REGISTRY


def kiem_tra(app, registry=REGISTRY, cong_khai=CONG_KHAI, cho_phep=CHO_PHEP_KHI_CHUA_DOI_MAT_KHAU):
    return kiem_tra_registry(app, registry, cong_khai, cho_phep)


def test_registry_day_du_va_khop_route_that_cua_ung_dung():
    assert kiem_tra(create_app()) == []


def test_duyet_route_thay_het_route_cua_openapi():
    """Nếu FastAPI đổi cấu trúc nội bộ khiến việc duyệt route sót, test registry sẽ vô nghĩa: bắt ngay ở đây."""
    app = create_app()
    thay = {(r.phuong_thuc, r.duong_dan) for r in duyet_route(app)}
    openapi = {
        (phuong_thuc.upper(), duong_dan)
        for duong_dan, thao_tac in app.openapi()["paths"].items()
        for phuong_thuc in thao_tac
    }
    assert openapi <= thay and len(openapi) >= 15
    assert ("POST", "/api/v1/noi-bo/auth/dang-nhap") in thay


def test_route_noi_bo_nao_cung_co_trong_registry_hoac_la_cong_khai():
    app = create_app()
    noi_bo = {r.khoa for r in duyet_route(app) if r.duong_dan.startswith("/api/v1/noi-bo/")}
    assert noi_bo == set(REGISTRY) | CONG_KHAI


def test_chi_hai_route_duoc_mien_viec_bat_doi_mat_khau():
    assert {
        ("GET", "/api/v1/noi-bo/toi"),
        ("POST", "/api/v1/noi-bo/auth/doi-mat-khau"),
    } == CHO_PHEP_KHI_CHUA_DOI_MAT_KHAU


# --- Chứng minh bộ kiểm tra thật sự bắt được lỗi ---------------------------------------------------------------------


def app_thu(*route_them):
    app = create_app()
    router = APIRouter(prefix="/api/v1/noi-bo/_thu")
    for them in route_them:
        them(router)
    app.include_router(router)
    return app


def test_bat_route_noi_bo_moi_chua_vao_registry():
    def them(r):
        @r.get("/chua-khai-bao")
        async def f(nv=Depends(nhan_vien_hien_tai)):
            return {}

    loi = kiem_tra(app_thu(them))
    assert any("/_thu/chua-khai-bao" in x and "chưa có trong registry" in x for x in loi)


def test_bat_route_khai_bao_registry_nhung_khong_gan_yeu_cau_quyen():
    def them(r):
        @r.post("/xac-nhan")
        async def f(nv=Depends(nhan_vien_hien_tai)):  # quên Depends(yeu_cau_quyen("order.confirm"))
            return {}

    registry = {**REGISTRY, ("POST", "/api/v1/noi-bo/_thu/xac-nhan"): ("order.confirm", "day_du")}
    loi = kiem_tra(app_thu(them), registry)
    assert any("cần đúng 1 Depends(yeu_cau_quyen" in x for x in loi)


def test_bat_route_dung_nham_ma_quyen_hoac_muc():
    def them(r):
        @r.post("/xac-nhan")
        async def f(nv: Annotated[NhanVien, Depends(yeu_cau_quyen("order.view"))]):  # registry ghi order.confirm
            return {}

        @r.get("/xem")
        async def g(nv: Annotated[NhanVien, Depends(yeu_cau_quyen("order.view", "xem"))]):  # registry ghi day_du
            return {}

    registry = {
        **REGISTRY,
        ("POST", "/api/v1/noi-bo/_thu/xac-nhan"): ("order.confirm", "day_du"),
        ("GET", "/api/v1/noi-bo/_thu/xem"): ("order.view", "day_du"),
    }
    loi = kiem_tra(app_thu(them), registry)
    assert sum("registry ghi" in x for x in loi) == 2


def test_bat_thao_tac_ghi_khai_bao_muc_xem():
    def them(r):
        @r.post("/ghi")
        async def f(nv: Annotated[NhanVien, Depends(yeu_cau_quyen("order.view", "xem"))]):
            return {}

    registry = {**REGISTRY, ("POST", "/api/v1/noi-bo/_thu/ghi"): ("order.view", "xem")}
    assert any("thao tác ghi không được khai báo mức 'xem'" in x for x in kiem_tra(app_thu(them), registry))


def test_bat_registry_loi_thoi_khong_con_route():
    registry = {**REGISTRY, ("GET", "/api/v1/noi-bo/da-xoa"): ("order.view", "xem")}
    assert any("registry lỗi thời" in x for x in kiem_tra(create_app(), registry))


def test_bat_route_cong_khai_nhung_lai_co_yeu_cau_quyen():
    cong_khai = CONG_KHAI | {("GET", "/api/v1/noi-bo/toi")}
    registry = {k: v for k, v in REGISTRY.items() if k != ("GET", "/api/v1/noi-bo/toi")}
    assert any(
        "khai báo công khai nhưng route lại có yeu_cau_quyen" in x for x in kiem_tra(create_app(), registry, cong_khai)
    )


def test_bat_route_bat_co_bo_qua_doi_mat_khau_ngoai_danh_sach_cho_phep():
    def them(r):
        @r.get("/bo-qua")
        async def f(
            nv: Annotated[NhanVien, Depends(yeu_cau_quyen("profile.self", "xem", ke_ca_chua_doi_mat_khau=True))],
        ):
            return {}

    registry = {**REGISTRY, ("GET", "/api/v1/noi-bo/_thu/bo-qua"): ("profile.self", "xem")}
    assert any("ke_ca_chua_doi_mat_khau" in x for x in kiem_tra(app_thu(them), registry))


def test_ma_quyen_khong_co_trong_yaml_khong_dung_duoc_ngay_tu_dau():
    with pytest.raises(ValueError):
        yeu_cau_quyen("khong.ton.tai")


def test_app_trong_khong_co_route_noi_bo_thi_registry_bao_thieu():
    loi = kiem_tra(FastAPI())
    assert loi and all("registry lỗi thời" in x for x in loi)

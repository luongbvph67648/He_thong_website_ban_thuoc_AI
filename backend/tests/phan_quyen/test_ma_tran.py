"""Ma trận phân quyền tự sinh từ quyen.yaml cho mọi route /api/v1/noi-bo (spec 10 mục 3)."""

from typing import Annotated

import pytest
from fastapi import Depends

from app.core.phan_quyen import nhan_vien_hien_tai, yeu_cau_quyen
from app.models.he_thong import NhanVien
from tests.phan_quyen.ma_tran import (
    VAI_TRO,
    goi_route,
    kiem_tra_ma_tran,
    ky_vong_duoc_phep,
    muc_cua_vai_tro,
)
from tests.phan_quyen.registry import REGISTRY


@pytest.mark.parametrize("vai_tro", VAI_TRO)
@pytest.mark.parametrize(("phuong_thuc", "duong_dan"), list(REGISTRY), ids=lambda x: str(x))
async def test_ma_tran_tung_route_tung_vai_tro(clients_theo_vai_tro, phuong_thuc, duong_dan, vai_tro):
    ma, muc = REGISTRY[(phuong_thuc, duong_dan)]
    phan_hoi = await goi_route(clients_theo_vai_tro[vai_tro], phuong_thuc, duong_dan)
    if ky_vong_duoc_phep(vai_tro, ma, muc, phuong_thuc):
        assert phan_hoi.status_code != 403, phan_hoi.text
    else:
        assert phan_hoi.status_code == 403 and phan_hoi.json()["ma_loi"] == "KHONG_CO_QUYEN"


async def test_ma_tran_toan_bo_registry_that_khong_co_vi_pham(clients_theo_vai_tro):
    assert await kiem_tra_ma_tran(clients_theo_vai_tro, REGISTRY) == []


# --- Ma trận trên route thử đa dạng quyền: chứng minh bộ kiểm tra không chỉ "xanh" vì profile.self ai cũng có ---------

GOC = "/api/v1/noi-bo/_thu"
REGISTRY_THU = {
    ("GET", f"{GOC}/xem-don"): ("order.view", "xem"),
    ("POST", f"{GOC}/xac-nhan"): ("order.confirm", "day_du"),
    ("POST", f"{GOC}/nhap-kho"): ("stock.import", "day_du"),
    ("GET", f"{GOC}/xem-nhap-kho"): ("stock.import", "xem"),
    ("POST", f"{GOC}/duyet-phieu"): ("stock_doc.approve", "day_du"),
    ("GET", f"{GOC}/nhat-ky"): ("audit.view", "xem"),
    ("GET", f"{GOC}/du-lieu-chung"): ("master_data.manage", "xem"),
}


@pytest.fixture
def app_thu(app):
    @app.get(f"{GOC}/xem-don")
    async def a(nv: Annotated[NhanVien, Depends(yeu_cau_quyen("order.view", "xem"))]):
        return {}

    @app.post(f"{GOC}/xac-nhan")
    async def b(nv: Annotated[NhanVien, Depends(yeu_cau_quyen("order.confirm"))]):
        return {}

    @app.post(f"{GOC}/nhap-kho")
    async def c(nv: Annotated[NhanVien, Depends(yeu_cau_quyen("stock.import"))]):
        return {}

    @app.get(f"{GOC}/xem-nhap-kho")
    async def d(nv: Annotated[NhanVien, Depends(yeu_cau_quyen("stock.import", "xem"))]):
        return {}

    @app.post(f"{GOC}/duyet-phieu")
    async def e(nv: Annotated[NhanVien, Depends(yeu_cau_quyen("stock_doc.approve"))]):
        return {}

    @app.get(f"{GOC}/nhat-ky")
    async def f(nv: Annotated[NhanVien, Depends(yeu_cau_quyen("audit.view", "xem"))]):
        return {}

    @app.get(f"{GOC}/du-lieu-chung")
    async def g(nv: Annotated[NhanVien, Depends(yeu_cau_quyen("master_data.manage", "xem"))]):
        return {}

    return app


async def test_ma_tran_route_thu_da_dang_dat(app_thu, clients_theo_vai_tro):
    assert await kiem_tra_ma_tran(clients_theo_vai_tro, REGISTRY_THU) == []


async def test_ma_tran_thu_co_du_ca_dung_va_sai_cho_moi_vai_tro():
    """Bảng kỳ vọng sinh từ yaml có cả ô được lẫn ô bị chặn cho từng vai trò (nếu không, ma trận kiểm tra suông)."""
    for vai_tro in VAI_TRO:
        ket_qua = {ky_vong_duoc_phep(vai_tro, ma, muc, pt) for (pt, _), (ma, muc) in REGISTRY_THU.items()}
        assert ket_qua == {True, False}, vai_tro
    # Một vài ô cụ thể để chặn việc yaml bị đổi nhầm: kho chỉ xem order.view, Admin xem được nhưng không duyệt nhập kho.
    assert muc_cua_vai_tro("WAREHOUSE")["order.view"] == "chi_xem"
    assert ky_vong_duoc_phep("ADMIN", "stock.import", "xem", "GET") is True
    assert ky_vong_duoc_phep("ADMIN", "stock.import", "day_du", "POST") is False
    assert ky_vong_duoc_phep("PHARMACIST", "audit.view", "xem", "GET") is False


async def test_ma_tran_bat_duoc_route_quen_kiem_tra_quyen(app, clients_theo_vai_tro):
    """Route khai báo `order.confirm` trong registry nhưng chỉ kiểm tra đăng nhập: kho và Admin lọt vào => bị bắt."""

    @app.post(f"{GOC}/quen-quyen")
    async def f(nv=Depends(nhan_vien_hien_tai)):
        return {}

    registry = {("POST", f"{GOC}/quen-quyen"): ("order.confirm", "day_du")}
    loi = await kiem_tra_ma_tran(clients_theo_vai_tro, registry)
    assert len(loi) == 2 and all("đáng lẽ 403" in x for x in loi)
    assert {x.split()[0] for x in loi} == {"WAREHOUSE", "ADMIN"}


async def test_ma_tran_bat_duoc_route_chan_nham_nguoi_dung_dung_quyen(app, clients_theo_vai_tro):
    """Route đòi nhầm quyền chỉ Admin có: dược sĩ đáng lẽ được phép (theo registry) nhưng nhận 403 => bị bắt."""

    @app.post(f"{GOC}/chan-nham")
    async def f(nv: Annotated[NhanVien, Depends(yeu_cau_quyen("staff.manage"))]):
        return {}

    registry = {("POST", f"{GOC}/chan-nham"): ("order.confirm", "day_du")}
    loi = await kiem_tra_ma_tran(clients_theo_vai_tro, registry)
    assert any(x.startswith("PHARMACIST") and "đáng lẽ được phép" in x for x in loi)
    assert any(x.startswith("ADMIN") and "đáng lẽ 403" in x for x in loi)  # Admin lại lọt vào

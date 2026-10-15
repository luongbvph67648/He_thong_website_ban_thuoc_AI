"""core/log.py + core/middleware.py: X-Request-ID và log JSON."""

import json
import logging
import re

import pytest
from fastapi import APIRouter

from app.core.log import JsonFormatter, cau_hinh_log
from app.main import create_app

HEX32 = re.compile(r"^[0-9a-f]{32}$")


@pytest.fixture
def app_log():
    app = create_app()

    @app.get("/thu/ok")
    async def ok():
        logging.getLogger("app.thu").info("đang xử lý trong route")
        return {"ok": True}

    @app.get("/thu/no")
    async def no():
        raise RuntimeError("hong")

    @app.get("/thu/token/{token}")
    async def theo_token(token: str):
        return {"ok": True}

    # Mọi route thật của dự án nằm trong router có tiền tố (/api/v1/toi, /api/v1/noi-bo...)
    router = APIRouter()

    @router.get("/don/{ma_don}/dong/{so_dong:int}")
    async def don_co_tien_to(ma_don: str, so_dong: int):
        return {"ok": True}

    app.include_router(router, prefix="/thu/toi")

    return app


# ---------- Header ----------


async def test_tu_sinh_request_id_khi_client_khong_gui(app_log, mo_client):
    async with mo_client(app_log) as c:
        resp = await c.get("/thu/ok")
    assert HEX32.match(resp.headers["x-request-id"])


async def test_giu_nguyen_request_id_hop_le_cua_client(app_log, mo_client):
    async with mo_client(app_log) as c:
        resp = await c.get("/thu/ok", headers={"X-Request-ID": "web-abc_123.456"})
    assert resp.headers["x-request-id"] == "web-abc_123.456"


@pytest.mark.parametrize(
    "sai",
    # Phần tử cuối là bytes để gửi được header non-ASCII.
    [
        "ngan",
        "co khoang trang 12345",
        "a;b<script>12345678",
        "x" * 65,
        "tiếng-việt-12345".encode(),
        b"abcdefgh\n",  # `$` trong regex cho phép \n ở cuối, fullmatch thì không
    ],
)
async def test_thay_request_id_khong_hop_le(app_log, mo_client, sai):
    async with mo_client(app_log) as c:
        resp = await c.get("/thu/ok", headers={"X-Request-ID": sai})
    assert HEX32.match(resp.headers["x-request-id"])


@pytest.mark.parametrize(("method", "path", "status"), [("GET", "/khong-co", 404), ("POST", "/thu/ok", 405)])
async def test_loi_cung_co_request_id(app_log, mo_client, method, path, status):
    async with mo_client(app_log) as c:
        resp = await c.request(method, path)
    assert resp.status_code == status
    assert HEX32.match(resp.headers["x-request-id"])


async def test_request_id_tren_phan_hoi_preflight_cors(app_log, mo_client):
    async with mo_client(app_log) as c:
        resp = await c.options(
            "/thu/ok", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"}
        )
    assert HEX32.match(resp.headers["x-request-id"])


async def test_trinh_duyet_doc_duoc_header_request_id(app_log, mo_client):
    async with mo_client(app_log) as c:
        resp = await c.get("/thu/ok", headers={"Origin": "http://localhost:5173"})
    assert "x-request-id" in resp.headers["access-control-expose-headers"].lower()


# ---------- Log JSON ----------


async def test_log_truy_cap_co_request_id_va_khong_ghi_query(app_log, mo_client, bat_log):
    async with mo_client(app_log) as c:
        resp = await c.get("/thu/ok?otp=123456&token=bi-mat")
    dong = [d for d in bat_log() if d["logger"] == "app.truy_cap"]
    assert len(dong) == 1
    d = dong[0]
    assert d["request_id"] == resp.headers["x-request-id"]
    assert (d["method"], d["path"], d["trang_thai"]) == ("GET", "/thu/ok", 200)
    assert d["thoi_gian_ms"] >= 0
    assert "123456" not in json.dumps(d) and "bi-mat" not in json.dumps(d)


async def test_log_trong_route_tu_dong_co_request_id(app_log, mo_client, bat_log):
    async with mo_client(app_log) as c:
        resp = await c.get("/thu/ok")
    d = next(d for d in bat_log() if d["logger"] == "app.thu")
    assert d["thong_diep"] == "đang xử lý trong route"
    assert d["request_id"] == resp.headers["x-request-id"]


async def test_loi_he_thong_duoc_log_kem_stack_va_request_id(app_log, mo_client, bat_log):
    async with mo_client(app_log, raise_app_exceptions=False) as c:
        resp = await c.get("/thu/no")
    assert resp.status_code == 500
    rid = resp.headers["x-request-id"]
    loi = [d for d in bat_log() if d["muc"] == "ERROR"]
    assert loi, "phải có log mức ERROR cho lỗi không bắt được"
    assert loi[0]["request_id"] == rid
    assert "RuntimeError" in loi[0]["loi"]
    truy_cap = [d for d in bat_log() if d["logger"] == "app.truy_cap"]
    assert truy_cap[0]["trang_thai"] == 500
    assert truy_cap[0]["request_id"] == rid


# ---------- JsonFormatter / cau_hinh_log ----------


def test_json_formatter_giu_tieng_viet_va_truong_bo_sung():
    ban_ghi = logging.LogRecord("app.x", logging.WARNING, __file__, 1, "Xin chào %s", ("bạn",), None)
    ban_ghi.ma_don = "DH12345678"
    d = json.loads(JsonFormatter().format(ban_ghi))
    assert d["thong_diep"] == "Xin chào bạn"
    assert d["muc"] == "WARNING"
    assert d["ma_don"] == "DH12345678"
    assert "Xin chào bạn" in JsonFormatter().format(ban_ghi)  # không escape \uXXXX


def test_cau_hinh_log_chay_nhieu_lan_chi_co_mot_handler():
    cau_hinh_log()
    cau_hinh_log()
    cau_hinh_log()
    dem = [h for h in logging.getLogger().handlers if getattr(h, "_nha_thuoc", False)]
    assert len(dem) == 1


# ---------- Không để lọt dữ liệu nhạy cảm vào log ----------


async def test_log_truy_cap_ghi_mau_route_khong_ghi_gia_tri_token(app_log, mo_client, bat_log):
    """Token nằm trong path (vd /xac-nhan-don/{token}) cho phép mở đơn của khách, không được lộ ra log."""
    async with mo_client(app_log) as c:
        await c.get("/thu/token/TOKEN-BI-MAT-abc123")
    dong = [d for d in bat_log() if d["logger"] == "app.truy_cap"]
    assert dong[0]["path"] == "/thu/token/{token}"
    assert "TOKEN-BI-MAT" not in json.dumps(dong, ensure_ascii=False)


async def test_log_truy_cap_route_khong_khop(app_log, mo_client, bat_log):
    async with mo_client(app_log) as c:
        await c.get("/thu/token-nhay-cam-123456/lung-tung")
    dong = [d for d in bat_log() if d["logger"] == "app.truy_cap"]
    assert dong[0]["path"] == "<khong-khop>"
    assert dong[0]["trang_thai"] == 404
    assert "nhay-cam" not in json.dumps(dong)


async def test_log_truy_cap_giu_tien_to_router_va_che_moi_tham_so_trong_path(app_log, mo_client, bat_log):
    async with mo_client(app_log) as c:
        resp = await c.get("/thu/toi/don/DH-BI-MAT-1/dong/7")
    assert resp.status_code == 200
    d = next(d for d in bat_log() if d["logger"] == "app.truy_cap")
    assert d["path"] == "/thu/toi/don/{ma_don}/dong/{so_dong}"
    assert "BI-MAT" not in json.dumps(d)


def test_tat_log_truy_cap_cua_uvicorn_vi_no_ghi_ca_query_string():
    cau_hinh_log()
    assert logging.getLogger("uvicorn.access").disabled


async def test_loi_he_thong_khong_nem_lai_cho_server(app_log, mo_client):
    """Ném lại ngoại lệ thì uvicorn tự in thêm một traceback dạng text, không có request_id, không qua bộ che."""
    async with mo_client(app_log) as c:  # mặc định raise_app_exceptions=True: nếu có ném lại, dòng này sẽ nổ
        resp = await c.get("/thu/no")
    assert resp.status_code == 500
    assert resp.json()["ma_loi"] == "LOI_HE_THONG"

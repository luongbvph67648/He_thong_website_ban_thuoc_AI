"""core/log.py + core/middleware.py: X-Request-ID và log JSON."""

import io
import json
import logging
import re

import pytest

from app.core.log import BoLocRequestId, JsonFormatter, cau_hinh_log
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

    return app


@pytest.fixture
def bat_log():
    """Gắn handler JSON vào logger "app" để đọc lại các dòng log trong test."""
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(BoLocRequestId())
    logger = logging.getLogger("app")
    cu = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    def doc_dong():
        return [json.loads(d) for d in buf.getvalue().splitlines() if d.strip()]

    yield doc_dong
    logger.removeHandler(handler)
    logger.setLevel(cu)


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
    ["ngan", "co khoang trang 12345", "a;b<script>12345678", "x" * 65, "tiếng-việt-12345".encode()],
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

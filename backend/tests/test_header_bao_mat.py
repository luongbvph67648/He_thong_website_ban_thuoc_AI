"""T8.2: header bảo mật trên mọi phản hồi, CORS chỉ cho nguồn cấu hình, không lộ stack trace."""

from app.core.middleware import HEADER_BAO_MAT

API = "/api/v1"


async def test_moi_phan_hoi_api_co_header_bao_mat_va_khong_cache(client):
    for duong in (f"{API}/health", f"{API}/khong-co-route-nay", f"{API}/noi-bo/toi"):  # thành công, 404, 401
        r = await client.get(duong)
        for ten, gia_tri in HEADER_BAO_MAT.items():
            assert r.headers[ten] == gia_tri, (duong, ten)
        assert r.headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"
        assert r.headers["cache-control"] == "no-store"


async def test_trang_tai_lieu_khong_bi_csp_khoa_chat(client):
    r = await client.get("/docs")
    assert "content-security-policy" not in r.headers and r.headers["x-content-type-options"] == "nosniff"


async def test_cors_chi_cho_nguon_cau_hinh(client):
    ok = await client.options(
        f"{API}/health", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"}
    )
    la = await client.options(
        f"{API}/health", headers={"Origin": "http://ke-xau.example", "Access-Control-Request-Method": "GET"}
    )
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in la.headers


async def test_loi_khong_ra_stack_trace(client):
    r = await client.get(f"{API}/san-pham/{'x' * 400}")
    assert "Traceback" not in r.text and 'File "' not in r.text

"""Giới hạn kích thước thân request của route nhận tệp: chặn TRƯỚC xác thực và trước khi parse multipart (QĐ-17).

Starlette đọc cả multipart vào tệp tạm trước khi chạy dependency xác thực, nên không có middleware này thì một người
chưa đăng nhập vẫn ghi được hàng trăm MB vào đĩa của máy chủ chỉ bằng một request.
"""

import json
from collections.abc import AsyncIterator

from app.core import luu_tru
from app.main import QUY_TAC_THAN_REQUEST, TOI_DA_THAN_JSON_BYTE, create_app

URL = "/api/v1/noi-bo/san-pham/1/anh"
THAM_SO = {"phien_ban": "a" * 16}
JPEG = b"\xff\xd8\xff\xe0"


async def test_tep_vuot_gioi_han_bi_tu_choi_413_truoc_khi_xac_thuc(client):
    lon = JPEG + b"0" * (luu_tru.TOI_DA_ANH_BYTE + 100 * 1024)
    phan_hoi = await client.post(URL, params=THAM_SO, files={"tep": ("a.jpg", lon, "image/jpeg")})  # không có token
    assert phan_hoi.status_code == 413, phan_hoi.text
    assert phan_hoi.json()["ma_loi"] == "TEP_QUA_LON"
    assert phan_hoi.headers["x-request-id"]


async def test_than_gui_theo_tung_manh_khong_co_content_length_cung_bi_chan(client):
    async def manh() -> AsyncIterator[bytes]:
        yield b'--b\r\nContent-Disposition: form-data; name="tep"; filename="a.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'
        for _ in range(8):
            yield b"0" * (1024 * 1024)
        yield b"\r\n--b--\r\n"

    phan_hoi = await client.post(
        URL, params=THAM_SO, content=manh(), headers={"content-type": "multipart/form-data; boundary=b"}
    )
    assert phan_hoi.status_code == 413, phan_hoi.text
    assert phan_hoi.json()["ma_loi"] == "TEP_QUA_LON"


async def test_trong_gioi_han_van_di_tiep_toi_xac_thuc_va_cac_route_khac_khong_bi_anh_huong(client):
    nho = JPEG + b"0" * 1024
    phan_hoi = await client.post(URL, params=THAM_SO, files={"tep": ("a.jpg", nho, "image/jpeg")})
    assert phan_hoi.status_code == 401  # chưa đăng nhập: đến được dependency xác thực
    khac = await client.post("/api/v1/noi-bo/auth/dang-nhap", json={"email": "a@b.c", "mat_khau": "x" * (60 * 1024)})
    assert khac.status_code != 413  # JSON cỡ vừa không bị chặn bởi trần chung


async def test_than_json_qua_lon_bi_chan_413_truoc_xac_thuc_voi_moi_phuong_thuc_ghi(client):
    lon = "x" * (TOI_DA_THAN_JSON_BYTE + 1024)
    for phuong_thuc, duong in (
        ("POST", "/api/v1/noi-bo/chuyen-mon/san-pham/1"),  # có xác thực: không token thì vẫn 413 chứ không phải 401
        ("PUT", "/api/v1/noi-bo/tuong-tac/1/2"),
        ("PATCH", "/api/v1/noi-bo/san-pham/1"),
        ("DELETE", "/api/v1/noi-bo/san-pham/1"),
        ("POST", "/api/v1/tai-khoan/dang-ky"),  # route công khai cũng bị trần (đỡ phải nạp thân khổng lồ vào RAM)
    ):
        phan_hoi = await client.request(phuong_thuc, duong, content=lon, headers={"content-type": "application/json"})
        assert phan_hoi.status_code == 413, (phuong_thuc, duong, phan_hoi.status_code)
        assert phan_hoi.json()["ma_loi"] == "THAN_QUA_LON"


async def test_than_json_gui_theo_manh_khong_content_length_cung_bi_chan(client):
    async def manh() -> AsyncIterator[bytes]:
        for _ in range(3):
            yield b" " * (1024 * 1024)

    phan_hoi = await client.post(
        "/api/v1/noi-bo/chuyen-mon/san-pham/1", content=manh(), headers={"content-type": "application/json"}
    )
    assert phan_hoi.status_code == 413 and phan_hoi.json()["ma_loi"] == "THAN_QUA_LON"


async def test_noi_dung_chuyen_mon_dai_nhat_cho_phep_van_nam_trong_tran(client):
    """10 trường x 20.000 ký tự tiếng Việt (3 byte mỗi ký tự trong UTF-8) phải nhỏ hơn trần chung."""
    toi_da = {"x": "ệ" * 20_000}
    assert len(json.dumps([toi_da] * 10, ensure_ascii=False).encode()) < TOI_DA_THAN_JSON_BYTE


def test_moi_route_nhan_tep_deu_co_quy_tac_gioi_han():
    """Thêm route multipart mới (banner, bài viết, đổi trả...) mà quên khai quy tắc thì test này đỏ."""
    app = create_app()
    chua_co = []
    for duong, cac_phuong_thuc in app.openapi()["paths"].items():
        for phuong_thuc, thao_tac in cac_phuong_thuc.items():
            la_multipart = "multipart/form-data" in thao_tac.get("requestBody", {}).get("content", {})
            co_quy_tac = any(
                q.phuong_thuc == phuong_thuc.upper() and q.mau_duong_dan.fullmatch(duong.replace("{san_pham_id}", "1"))
                for q in QUY_TAC_THAN_REQUEST
            )
            if la_multipart and not co_quy_tac:
                chua_co.append((phuong_thuc.upper(), duong))
    assert chua_co == []

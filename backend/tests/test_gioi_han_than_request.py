"""Giới hạn kích thước thân request của route nhận tệp: chặn TRƯỚC xác thực và trước khi parse multipart (QĐ-17).

Starlette đọc cả multipart vào tệp tạm trước khi chạy dependency xác thực, nên không có middleware này thì một người
chưa đăng nhập vẫn ghi được hàng trăm MB vào đĩa của máy chủ chỉ bằng một request.
"""

from collections.abc import AsyncIterator

from app.core import luu_tru
from app.main import QUY_TAC_THAN_REQUEST, create_app

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
    khac = await client.post(
        "/api/v1/noi-bo/auth/dang-nhap", json={"email": "a@b.c", "mat_khau": "x" * (6 * 1024 * 1024)}
    )
    assert khac.status_code != 413  # chỉ route nhận tệp có giới hạn riêng


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

"""HTTP ra ngoài của các adapter tích hợp: một chỗ chọn đường đi.

Địa chỉ ở máy chủ mô phỏng (`mo-phong.local`, chế độ `mo_phong`; route nằm trong chính ứng dụng, dưới
`/api/v1/mo-phong`) được gọi TRONG TIẾN TRÌNH qua ASGI: không cần mở cổng,
chạy được cả trong test, nhưng adapter vẫn dựng yêu cầu HTTP đầy đủ (URL, tiêu đề, JSON, chữ ký) y như gọi cổng thật.
Địa chỉ khác (sandbox, production) đi qua mạng bằng `httpx` như bình thường.
"""

from typing import Any

import httpx

MAY_CHU_MO_PHONG = "mo-phong.local"
GOC_MO_PHONG = f"http://{MAY_CHU_MO_PHONG}/api/v1/mo-phong"


def la_mo_phong(url: str) -> bool:
    return httpx.URL(url).host == MAY_CHU_MO_PHONG


def tao_client(url: str, **tuy_chon: Any) -> httpx.AsyncClient:
    """Client cho `url`: ASGI nội bộ nếu là máy chủ mô phỏng, ngược lại đi qua mạng."""
    if la_mo_phong(url):
        from app.tich_hop.mo_phong import ung_dung_chinh

        return httpx.AsyncClient(transport=httpx.ASGITransport(app=ung_dung_chinh()), **tuy_chon)
    return httpx.AsyncClient(**tuy_chon)

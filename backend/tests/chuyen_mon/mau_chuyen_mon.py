"""Hàm dùng chung của test DS10: nội dung chuyên môn, tương tác hoạt chất, duyệt bài viết."""

GOC_NOI_DUNG = "/api/v1/noi-bo/chuyen-mon"
GOC_TUONG_TAC = "/api/v1/noi-bo/tuong-tac"
GOC_BAI_VIET = "/api/v1/noi-bo/bai-viet-cho-duyet"


def la_loi(phan_hoi, status: int, ma_loi: str) -> bool:
    return phan_hoi.status_code == status and phan_hoi.json()["ma_loi"] == ma_loi


def noi_dung(co_so: int | None, **ghi_de) -> dict:
    """Thân `POST /chuyen-mon/san-pham/{id}` hợp lệ; `co_so` là phiên bản mới nhất người soạn đã thấy."""
    than = {"phien_ban_co_so": co_so, "chi_dinh": "Giảm đau, hạ sốt", "lieu_dung_tham_khao": "500 mg mỗi 6 giờ"}
    than.update(ghi_de)
    return than


async def soan(client, san_pham_id: int, co_so: int | None, **ghi_de) -> dict:
    phan_hoi = await client.post(f"{GOC_NOI_DUNG}/san-pham/{san_pham_id}", json=noi_dung(co_so, **ghi_de))
    assert phan_hoi.status_code == 201, phan_hoi.text
    return phan_hoi.json()

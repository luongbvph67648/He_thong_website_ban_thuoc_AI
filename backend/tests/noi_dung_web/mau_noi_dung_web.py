"""Hàm dùng chung của test nội dung website (AD07, KVL11)."""

GOC_BANNER = "/api/v1/noi-bo/banner"
GOC_BAI_VIET = "/api/v1/noi-bo/bai-viet"
GOC_CONG_KHAI = "/api/v1/bai-viet"
GOC_CHO_DUYET = "/api/v1/noi-bo/bai-viet-cho-duyet"
JPEG = b"\xff\xd8\xff\xe0" + b"0" * 64


def la_loi(phan_hoi, status: int, ma_loi: str) -> bool:
    return phan_hoi.status_code == status and phan_hoi.json()["ma_loi"] == ma_loi


def than_banner(**ghi_de) -> dict:
    than = {"anh_url": "/api/v1/tep/banner/a.jpg", "vi_tri": "trang_chu_chinh", "tieu_de": "Khuyến mãi"}
    than.update(ghi_de)
    return than


async def tao_banner(admin, **ghi_de) -> dict:
    phan_hoi = await admin.post(GOC_BANNER, json=than_banner(**ghi_de))
    assert phan_hoi.status_code == 201, phan_hoi.text
    return phan_hoi.json()


def than_bai(**ghi_de) -> dict:
    than = {"loai": "bai_viet", "tieu_de": "Cách phòng cảm cúm", "noi_dung": "## Rửa tay\n\nRửa tay thường xuyên."}
    than.update(ghi_de)
    return than


async def tao_bai(admin, **ghi_de) -> dict:
    phan_hoi = await admin.post(GOC_BAI_VIET, json=than_bai(**ghi_de))
    assert phan_hoi.status_code == 201, phan_hoi.text
    return phan_hoi.json()


async def duyet_bai(duoc_si, bai: dict) -> dict:
    """Dược sĩ đọc rồi duyệt đúng phiên bản đã đọc."""
    phien_ban = (await duoc_si.get(f"{GOC_CHO_DUYET}/{bai['id']}")).json()["phien_ban"]
    phan_hoi = await duoc_si.post(f"{GOC_CHO_DUYET}/{bai['id']}/duyet", json={"phien_ban": phien_ban})
    assert phan_hoi.status_code == 200, phan_hoi.text
    return phan_hoi.json()

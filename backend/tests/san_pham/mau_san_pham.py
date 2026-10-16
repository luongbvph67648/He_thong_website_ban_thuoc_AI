"""Hàm dùng chung của test sản phẩm (AD04): thân yêu cầu hợp lệ, gọi API, ảnh mẫu."""

import itertools

GOC = "/api/v1/noi-bo/san-pham"
_dem = itertools.count(1)

# Chỉ cần byte đầu đúng kiểu: hệ thống nhận dạng ảnh theo magic bytes.
ANH_JPEG = b"\xff\xd8\xff\xe0" + b"jpeg" * 64
ANH_PNG = b"\x89PNG\r\n\x1a\n" + b"png" * 64
ANH_WEBP = b"RIFF\x24\x00\x00\x00WEBP" + b"webp" * 16


def la_loi(phan_hoi, status, ma_loi):
    return phan_hoi.status_code == status and phan_hoi.json()["ma_loi"] == ma_loi


def than_tao(danh_muc_id: int, **ghi_de) -> dict:
    """Thân `POST /san-pham` hợp lệ: đơn vị cơ sở "Viên" và đơn vị mặc định "Hộp" (100 viên)."""
    n = next(_dem)
    than = {
        "sku": f"sp-{n:04d}",
        "ten": f"Sản phẩm thử {n}",
        "loai_san_pham": "thuoc_khong_ke_don",
        "danh_muc_id": danh_muc_id,
        "don_vi": [
            {"ten_don_vi": "Viên", "he_so": 1, "gia_ban": "1000"},
            {"ten_don_vi": "Hộp", "he_so": 100, "gia_ban": "90000", "la_mac_dinh": True},
        ],
    }
    than.update(ghi_de)
    return than


async def tao_sp(admin, danh_muc_id: int, **ghi_de) -> dict:
    phan_hoi = await admin.post(GOC, json=than_tao(danh_muc_id, **ghi_de))
    assert phan_hoi.status_code == 201, phan_hoi.text
    return phan_hoi.json()


async def doc_sp(admin, san_pham_id: int) -> dict:
    phan_hoi = await admin.get(f"{GOC}/{san_pham_id}")
    assert phan_hoi.status_code == 200, phan_hoi.text
    return phan_hoi.json()


async def tai_anh(admin, sp: dict, noi_dung: bytes = ANH_JPEG, ten: str = "a.jpg", kieu: str = "image/jpeg"):
    """Tải ảnh lên sản phẩm `sp` (dùng `phien_ban` trong `sp`); trả phản hồi thô."""
    return await admin.post(
        f"{GOC}/{sp['id']}/anh", params={"phien_ban": sp["phien_ban"]}, files={"tep": (ten, noi_dung, kieu)}
    )

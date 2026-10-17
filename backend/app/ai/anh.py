"""Chuẩn bị ảnh gửi Claude (AI05, AI06; spec 07 mục 2): thu nhỏ cạnh dài, JPEG chất lượng 85, bỏ EXIF/ICC."""

import base64
import io
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

CANH_DAI_TOI_DA = 1568
CHAT_LUONG_JPEG = 85
TOI_DA_DIEM_ANH = 12_000_000
"""Chặn "bom giải nén": ảnh nhỏ byte nhưng hàng trăm triệu điểm ảnh sẽ ăn hết bộ nhớ khi mở."""


class AnhKhongDoc(ValueError):
    """Byte không phải ảnh mở được (hỏng, quá lớn về điểm ảnh)."""


def chuan_bi_anh(noi_dung: bytes) -> str:
    """Trả base64 của JPEG đã thu nhỏ. Nền trong suốt đổi sang trắng; xoay theo EXIF rồi bỏ EXIF."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            anh = Image.open(io.BytesIO(noi_dung))
            if anh.width * anh.height > TOI_DA_DIEM_ANH:
                raise AnhKhongDoc("Ảnh quá lớn")
            anh.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as e:
        raise AnhKhongDoc("Không đọc được ảnh") from e
    anh = ImageOps.exif_transpose(anh)
    if anh.mode in ("RGBA", "LA", "P"):
        nen = Image.new("RGB", anh.size, (255, 255, 255))
        anh = anh.convert("RGBA")
        nen.paste(anh, mask=anh.getchannel("A"))
        anh = nen
    else:
        anh = anh.convert("RGB")
    anh.thumbnail((CANH_DAI_TOI_DA, CANH_DAI_TOI_DA))
    ra = io.BytesIO()
    anh.save(ra, format="JPEG", quality=CHAT_LUONG_JPEG)
    return base64.standard_b64encode(ra.getvalue()).decode("ascii")


def khoi_anh(anh_b64: str) -> dict:
    """Khối ảnh của Messages API; đặt TRƯỚC khối chữ."""
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": anh_b64}}

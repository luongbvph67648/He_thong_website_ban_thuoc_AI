"""core/luu_tru.py: nhận dạng ảnh theo nội dung, khóa file an toàn, ghi/đọc/xóa trong vùng công khai."""

import asyncio

import pytest

from app.core import luu_tru

JPEG = b"\xff\xd8\xff\xdb" + b"0" * 20
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 20
WEBP = b"RIFF\x10\x00\x00\x00WEBPVP8 " + b"0" * 20


@pytest.mark.parametrize(
    ("noi_dung", "kieu"),
    [
        (JPEG, "image/jpeg"),
        (PNG, "image/png"),
        (WEBP, "image/webp"),
        (b"", None),
        (b"\xff\xd8", None),
        (b"GIF89a....", None),
        (b"RIFF\x10\x00\x00\x00WAVEfmt ", None),
        (b"<svg/>", None),
        (b"\x89PNG\r\n", None),  # cụt
    ],
)
def test_nhan_dang_anh_theo_noi_dung(noi_dung, kieu):
    assert luu_tru.nhan_dang_anh(noi_dung) == kieu


@pytest.mark.parametrize(
    ("khoa", "hop_le"),
    [
        ("san-pham/0123abcd.jpg", True),
        ("san-pham/0123abcd.png", True),
        ("banner/trang-chu/a1.webp", True),
        ("san-pham/a.gif", False),
        ("san-pham/a.JPG", False),
        ("San-Pham/a.jpg", False),
        ("../a.jpg", False),
        ("san-pham/../a.jpg", False),
        ("/san-pham/a.jpg", False),
        ("san-pham//a.jpg", False),
        ("san_pham/a.jpg", False),
        ("san-pham/a.jpg\x00", False),
        ("san-pham/a.jpg\n", False),
        ("san-pham/a b.jpg", False),
        ("san-pham/.jpg", False),
        ("a.jpg", True),
        ("", False),
        ("san-pham/" + "a" * 200 + ".jpg", False),
    ],
)
def test_khoa_file_chi_gom_ky_tu_an_toan(khoa, hop_le):
    assert luu_tru.khoa_hop_le(khoa) is hop_le


def test_url_cong_khai_va_nguoc_lai():
    khoa = "san-pham/abc123.jpg"
    assert luu_tru.url_cong_khai(khoa) == "/api/v1/tep/san-pham/abc123.jpg"
    assert luu_tru.khoa_tu_url_cong_khai(luu_tru.url_cong_khai(khoa)) == khoa
    for url in ("/api/v1/tep/../x.jpg", "https://evil.example/api/v1/tep/a.jpg", "/khac/a.jpg", "/api/v1/tep/a.exe"):
        assert luu_tru.khoa_tu_url_cong_khai(url) is None


async def test_ghi_doc_xoa_dung_vung_cong_khai_va_ten_uuid():
    kho = luu_tru.luu_tru()
    khoa = await kho.luu("san-pham", PNG, "image/png")
    assert luu_tru.khoa_hop_le(khoa) and khoa.startswith("san-pham/") and khoa.endswith(".png")
    assert (kho.goc / "cong_khai" / khoa).read_bytes() == PNG  # vùng riêng tư là thư mục khác, chưa dùng ở đây
    assert await kho.doc(khoa) == PNG
    await kho.xoa(khoa)
    assert await kho.doc(khoa) is None
    await kho.xoa(khoa)  # xóa file không còn không báo lỗi


async def test_khong_cho_doc_hay_xoa_khoa_ngoai_thu_muc_luu_tru():
    kho = luu_tru.luu_tru()
    for khoa in ("../x.jpg", "/etc/passwd", "san-pham/../../x.jpg"):
        with pytest.raises(ValueError):
            await kho.doc(khoa)
        with pytest.raises(ValueError):
            await kho.xoa(khoa)


async def test_hai_lan_luu_cung_noi_dung_cho_hai_khoa_khac_nhau():
    kho = luu_tru.luu_tru()
    khoa_a, khoa_b = await asyncio.gather(
        kho.luu("san-pham", JPEG, "image/jpeg"), kho.luu("san-pham", JPEG, "image/jpeg")
    )
    assert khoa_a != khoa_b


def test_thu_muc_luu_tuong_doi_tinh_tu_backend_khong_phu_thuoc_thu_muc_dang_chay(monkeypatch, tmp_path):
    monkeypatch.setattr(luu_tru.settings, "LUU_TRU_THU_MUC", "./storage")
    assert luu_tru.luu_tru().goc == (luu_tru.BACKEND_DIR / "storage").resolve()
    monkeypatch.setattr(luu_tru.settings, "LUU_TRU_THU_MUC", str(tmp_path))
    assert luu_tru.luu_tru().goc == tmp_path.resolve()

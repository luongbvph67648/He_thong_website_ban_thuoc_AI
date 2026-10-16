"""core/luu_tru.py: nhận dạng ảnh theo nội dung, khóa file an toàn, ghi/đọc/xóa trong vùng công khai."""

import asyncio
import logging
from pathlib import Path

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


async def test_symlink_tu_vung_cong_khai_tro_sang_vung_khac_khong_duoc_doc(tmp_path):
    """`cong_khai/.../lien-ket.jpg` -> `rieng_tu/bi-mat.jpg`: vẫn nằm trong thư mục lưu trữ nhưng NGOÀI vùng công khai."""
    kho = luu_tru.LuuTruCucBo(tmp_path)
    (tmp_path / "rieng_tu").mkdir()
    (tmp_path / "rieng_tu" / "bi-mat.jpg").write_bytes(JPEG)
    (tmp_path / "cong_khai" / "san-pham").mkdir(parents=True)
    (tmp_path / "cong_khai" / "san-pham" / "lien-ket.jpg").symlink_to(tmp_path / "rieng_tu" / "bi-mat.jpg")
    with pytest.raises(ValueError):
        await kho.doc("san-pham/lien-ket.jpg")


async def test_route_cong_khai_tra_404_cho_symlink_ra_ngoai_vung_cong_khai(client, tmp_path):
    kho = luu_tru.luu_tru()
    (kho.goc / "rieng_tu").mkdir(parents=True, exist_ok=True)
    (kho.goc / "rieng_tu" / "bi-mat.jpg").write_bytes(JPEG)
    (kho.goc / "cong_khai" / "san-pham").mkdir(parents=True, exist_ok=True)
    (kho.goc / "cong_khai" / "san-pham" / "lien-ket.jpg").symlink_to(kho.goc / "rieng_tu" / "bi-mat.jpg")
    phan_hoi = await client.get("/api/v1/tep/san-pham/lien-ket.jpg")
    assert phan_hoi.status_code == 404 and phan_hoi.json()["ma_loi"] == "KHONG_TIM_THAY"


async def test_doc_file_vua_bi_xoa_giua_luc_kiem_tra_va_doc_tra_none_khong_loi(monkeypatch):
    kho = luu_tru.luu_tru()
    khoa = await kho.luu("san-pham", JPEG, "image/jpeg")

    def vua_bi_xoa(_self):
        raise FileNotFoundError

    monkeypatch.setattr(Path, "read_bytes", vua_bi_xoa)
    assert await kho.doc(khoa) is None


def test_xoa_file_sau_commit_that_bai_thi_ghi_canh_bao_khong_nem_loi(monkeypatch, caplog):
    def khong_xoa_duoc(_self, missing_ok=False):
        raise PermissionError("không có quyền")

    monkeypatch.setattr(Path, "unlink", khong_xoa_duoc)
    with caplog.at_level(logging.WARNING, logger="app.core.luu_tru"):
        luu_tru._xoa_dong_bo("san-pham/abcdef.jpg")
    assert any("san-pham/abcdef.jpg" in str(getattr(b, "khoa", "")) or "tệp" in b.getMessage() for b in caplog.records)

"""Các lỗi do rà soát độc lập T2.6 tìm ra (M1–M3, L1–L3): mỗi test tái hiện lỗi trước khi sửa."""

import time

import pytest

from app.modules.noi_dung_web.cong_khai import tom_tat
from tests.nhan_vien.dung_chung import nhat_ky
from tests.noi_dung_web.mau_noi_dung_web import (
    GOC_BAI_VIET,
    GOC_BANNER,
    GOC_CONG_KHAI,
    la_loi,
    tao_bai,
    tao_banner,
    than_banner,
)

# --- M1: regex tóm tắt không được chạy bậc hai trên nội dung dài ----------------------------------------------------


@pytest.mark.parametrize(
    "noi_dung",
    ["[" * 100_000, "![" * 50_000, "\n" * 99_990 + "x", "- " * 50_000, "`" * 100_000],
    ids=["mo-ngoac", "mo-anh", "xuong-dong", "gach-dau-dong", "dau-huyen"],
)
def test_tom_tat_noi_dung_ac_y_chay_nhanh(noi_dung):
    bat_dau = time.perf_counter()
    tom_tat(noi_dung)
    assert time.perf_counter() - bat_dau < 0.5


def test_tom_tat_van_dung_voi_bai_binh_thuong():
    assert tom_tat("## Tiêu đề\n\nĐọc [liên kết](http://x.vn) và **in đậm**.") == "Tiêu đề Đọc liên kết và in đậm."


async def test_chinh_sach_noi_dung_ac_y_van_tra_danh_sach_cong_khai_nhanh(dang_nhap_admin, client):
    await tao_bai(dang_nhap_admin, loai="chinh_sach", tieu_de="Chính sách lạ", noi_dung="[" * 100_000)
    bat_dau = time.perf_counter()
    phan_hoi = await client.get(GOC_CONG_KHAI, params={"loai": "chinh_sach"})
    assert phan_hoi.status_code == 200 and time.perf_counter() - bat_dau < 3
    assert len(phan_hoi.json()["du_lieu"]) == 1


# --- M2: sửa nội dung cùng độ dài phải được lưu ---------------------------------------------------------------------


async def test_sua_noi_dung_cung_do_dai_van_luu_ghi_nhat_ky_va_doi_phien_ban(dang_nhap_admin, client, db):
    admin = dang_nhap_admin
    bai = await tao_bai(admin, loai="faq", tieu_de="Gọi đâu", noi_dung="Goi 0901234567")
    sua = await admin.patch(
        f"{GOC_BAI_VIET}/{bai['id']}", json={"phien_ban": bai["phien_ban"], "noi_dung": "Goi 0907654321"}
    )
    assert sua.status_code == 200
    assert sua.json()["noi_dung"] == "Goi 0907654321" and sua.json()["phien_ban"] != bai["phien_ban"]
    cong_khai = await client.get(f"{GOC_CONG_KHAI}/{bai['slug']}")
    assert cong_khai.json()["noi_dung"] == "Goi 0907654321"
    ghi = await nhat_ky(db, admin.tai_khoan.id, "sua")
    assert len(ghi) == 1 and "0907654321" not in str(ghi[0].gia_tri_moi) and "0901234567" not in str(ghi[0].gia_tri_cu)


# --- M3, L2: thời điểm banner ----------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ghi_de",
    [
        {"bat_dau": "0001-01-01T00:00:00Z"},
        {"bat_dau": "0001-01-01T00:00:00+07:00"},
        {"ket_thuc": "9999-12-31T23:59:59-07:00"},
        {"ket_thuc": "9999-12-31T23:59:59Z"},
        {"bat_dau": "1999-12-31T23:59:59Z"},
        {"ket_thuc": "2101-01-01T00:00:00Z"},
    ],
)
async def test_banner_thoi_diem_ngoai_mien_la_400_va_danh_sach_van_xem_duoc(dang_nhap_admin, ghi_de):
    phan_hoi = await dang_nhap_admin.post(GOC_BANNER, json=than_banner(**ghi_de))
    assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE"), phan_hoi.text
    assert (await dang_nhap_admin.get(GOC_BANNER)).status_code == 200


async def test_sua_banner_thoi_diem_ngoai_mien_la_400(dang_nhap_admin):
    b = await tao_banner(dang_nhap_admin)
    phan_hoi = await dang_nhap_admin.patch(
        f"{GOC_BANNER}/{b['id']}", json={"phien_ban": b["phien_ban"], "bat_dau": "0001-01-01T00:00:00Z"}
    )
    assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE")


async def test_phien_ban_banner_khong_phu_thuoc_mui_gio_client_gui(dang_nhap_admin):
    b = await tao_banner(dang_nhap_admin, bat_dau="2026-10-01T08:00:00+07:00")
    ds = {x["id"]: x for x in (await dang_nhap_admin.get(GOC_BANNER)).json()}
    assert b["phien_ban"] == ds[b["id"]]["phien_ban"]
    sua = await dang_nhap_admin.patch(
        f"{GOC_BANNER}/{b['id']}", json={"phien_ban": b["phien_ban"], "bat_dau": "2026-10-01T01:00:00Z"}
    )
    assert sua.status_code == 200  # cùng một thời điểm viết ở múi giờ khác: không phải thay đổi


# --- L1: ký tự điều khiển trong nội dung và tiêu đề ------------------------------------------------------------------


# Giá trị JSON đã thoát: httpx không mã hóa được surrogate lẻ nên gửi thẳng thân JSON thô.
@pytest.mark.parametrize(
    ("truong", "gia_tri"),
    [
        ("noi_dung", "a\\u0000b"),
        ("noi_dung", "a\\ud800b"),
        ("noi_dung", "a\\u202eb"),
        ("tieu_de", "a\\ud800b"),
        ("tieu_de", "a\\u200bb"),
        ("tieu_de", "a\\u0000b"),
    ],
)
async def test_bai_viet_ky_tu_dieu_khien_hoac_vo_hinh_la_400_chu_khong_500(dang_nhap_admin, truong, gia_tri):
    tieu_de, noi_dung = ("Tiêu đề", gia_tri) if truong == "noi_dung" else (gia_tri, "Nội dung")
    thuong = {"content-type": "application/json"}
    tao = await dang_nhap_admin.post(
        GOC_BAI_VIET,
        content=f'{{"loai":"bai_viet","tieu_de":"{tieu_de}","noi_dung":"{noi_dung}"}}'.encode(),
        headers=thuong,
    )
    assert la_loi(tao, 400, "DU_LIEU_KHONG_HOP_LE"), tao.text
    bai = await tao_bai(dang_nhap_admin)
    sua = await dang_nhap_admin.patch(
        f"{GOC_BAI_VIET}/{bai['id']}",
        content=f'{{"phien_ban":"{bai["phien_ban"]}","{truong}":"{gia_tri}"}}'.encode(),
        headers=thuong,
    )
    assert la_loi(sua, 400, "DU_LIEU_KHONG_HOP_LE"), sua.text


async def test_noi_dung_van_cho_phep_xuong_dong_va_tab(dang_nhap_admin):
    bai = await tao_bai(dang_nhap_admin, noi_dung="Dòng 1\r\n\tDòng 2\n\nDòng 3")
    assert "Dòng 2" in bai["noi_dung"]


# --- L3: danh sách công khai không kéo toàn văn bài --------------------------------------------------------------------


async def test_danh_sach_cong_khai_chinh_sach_khong_tra_toan_van_va_tom_tat_van_dung(dang_nhap_admin, client):
    dai = "Chữ " * 20_000
    await tao_bai(dang_nhap_admin, loai="chinh_sach", tieu_de="Dài", noi_dung=dai)
    dong = (await client.get(GOC_CONG_KHAI, params={"loai": "chinh_sach"})).json()["du_lieu"][0]
    assert dong["noi_dung"] is None and 0 < len(dong["tom_tat"]) <= 201


async def test_kem_noi_dung_gioi_han_50_dong_moi_trang(client):
    phan_hoi = await client.get(GOC_CONG_KHAI, params={"loai": "faq", "kem_noi_dung": "true", "kich_thuoc": 51})
    assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE")
    assert (
        await client.get(GOC_CONG_KHAI, params={"loai": "faq", "kem_noi_dung": "true", "kich_thuoc": 50})
    ).status_code == 200

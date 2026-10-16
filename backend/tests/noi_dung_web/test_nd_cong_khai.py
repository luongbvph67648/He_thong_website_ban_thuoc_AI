"""KVL11: bài viết sức khỏe, chính sách, FAQ công khai (/api/v1/bai-viet) và tải ảnh (banner, bìa bài viết)."""

from datetime import timedelta
from pathlib import Path

import pytest

from app.core import luu_tru
from app.core.config import settings
from app.core.thoi_gian import bay_gio_utc
from app.models.he_thong import BaiViet
from app.modules.noi_dung_web.cong_khai import tom_tat
from tests.nhan_vien.dung_chung import nhat_ky
from tests.noi_dung_web.mau_noi_dung_web import (
    GOC_BAI_VIET,
    GOC_BANNER,
    GOC_CONG_KHAI,
    JPEG,
    duyet_bai,
    la_loi,
    tao_bai,
)

# --- Danh sách và chi tiết ---------------------------------------------------------------------------------------------


async def dang_bai(clients, **ghi_de):
    return await duyet_bai(clients["PHARMACIST"], await tao_bai(clients["ADMIN"], **ghi_de))


async def test_danh_sach_chi_gom_bai_da_duyet_moi_dang_truoc_khong_lo_nguoi_soan(clients_theo_vai_tro, client, db):
    cu = await dang_bai(clients_theo_vai_tro, tieu_de="Bài cũ")
    await tao_bai(clients_theo_vai_tro["ADMIN"], tieu_de="Bài nháp")  # chưa duyệt
    moi = await dang_bai(clients_theo_vai_tro, tieu_de="Bài mới", anh_bia_url="/api/v1/tep/bai-viet/a.jpg")
    da_go = await dang_bai(clients_theo_vai_tro, tieu_de="Bài đã gỡ")
    admin = clients_theo_vai_tro["ADMIN"]
    await admin.post(
        f"{GOC_BAI_VIET}/{da_go['id']}/go",
        json={"phien_ban": (await admin.get(f"{GOC_BAI_VIET}/{da_go['id']}")).json()["phien_ban"]},
    )
    phan_hoi = await client.get(GOC_CONG_KHAI)
    assert phan_hoi.status_code == 200
    ds = phan_hoi.json()
    assert [b["tieu_de"] for b in ds["du_lieu"]] == ["Bài mới", "Bài cũ"] and ds["tong"] == 2
    b = ds["du_lieu"][0]
    assert set(b) == {"id", "tieu_de", "slug", "loai", "anh_bia_url", "tom_tat", "ngay_dang", "noi_dung"}
    assert b["noi_dung"] is None and b["anh_bia_url"] == "/api/v1/tep/bai-viet/a.jpg" and b["id"] == moi["id"]
    assert cu["id"] != moi["id"]
    mo_ta = phan_hoi.text
    for lo in ("tac_gia", "duoc_si_duyet", "dua_vao_ai", "trang_thai", dang_bai.__name__):
        assert lo not in mo_ta, lo


async def test_loai_mac_dinh_la_bai_viet_chinh_sach_va_faq_theo_thu_tu_tao_va_tim_theo_tieu_de(
    clients_theo_vai_tro, client, db
):
    admin = clients_theo_vai_tro["ADMIN"]
    await dang_bai(clients_theo_vai_tro, tieu_de="Bài sức khỏe")
    for ten in ("Chính sách bảo mật", "Chính sách đổi trả"):
        await tao_bai(admin, loai="chinh_sach", tieu_de=ten)
    for ten in ("Câu hỏi hai", "Câu hỏi một"):
        await tao_bai(admin, loai="faq", tieu_de=ten, noi_dung=f"Trả lời cho {ten}")
    assert [b["tieu_de"] for b in (await client.get(GOC_CONG_KHAI)).json()["du_lieu"]] == ["Bài sức khỏe"]
    cs = (await client.get(GOC_CONG_KHAI, params={"loai": "chinh_sach"})).json()["du_lieu"]
    assert [b["tieu_de"] for b in cs] == ["Chính sách bảo mật", "Chính sách đổi trả"]  # theo thứ tự tạo
    assert [
        b["tieu_de"]
        for b in (await client.get(GOC_CONG_KHAI, params={"loai": "chinh_sach", "q": "DOI TRA"})).json()["du_lieu"]
    ] == ["Chính sách đổi trả"]
    faq = (await client.get(GOC_CONG_KHAI, params={"loai": "faq", "kem_noi_dung": "true"})).json()["du_lieu"]
    assert [(b["tieu_de"], b["noi_dung"]) for b in faq] == [
        ("Câu hỏi hai", "Trả lời cho Câu hỏi hai"),
        ("Câu hỏi một", "Trả lời cho Câu hỏi một"),
    ]
    assert all(b["noi_dung"] is None for b in cs)


async def test_kem_noi_dung_chi_cho_faq_va_tham_so_sai_la_400(client, db):
    for tham in (
        {"loai": "bai_viet", "kem_noi_dung": "true"},
        {"loai": "chinh_sach", "kem_noi_dung": "true"},
        {"loai": "tin"},
        {"q": "a\x00b"},
        {"kich_thuoc": 101},
    ):
        assert la_loi(await client.get(GOC_CONG_KHAI, params=tham), 400, "DU_LIEU_KHONG_HOP_LE"), tham


async def test_phan_trang_on_dinh(clients_theo_vai_tro, client, db):
    for i in range(5):
        await tao_bai(clients_theo_vai_tro["ADMIN"], loai="chinh_sach", tieu_de=f"Chính sách {i}")
    thay = []
    for trang in (1, 2, 3):
        phan_hoi = await client.get(GOC_CONG_KHAI, params={"loai": "chinh_sach", "kich_thuoc": 2, "trang": trang})
        assert phan_hoi.json()["tong"] == 5
        thay += [b["tieu_de"] for b in phan_hoi.json()["du_lieu"]]
    assert thay == [f"Chính sách {i}" for i in range(5)]


async def test_chi_tiet_theo_slug_day_du_va_chi_bai_da_dang(clients_theo_vai_tro, client, db):
    bai = await dang_bai(clients_theo_vai_tro, tieu_de="Phòng cảm cúm", noi_dung="## Rửa tay\n\nThường xuyên.")
    phan_hoi = await client.get(f"{GOC_CONG_KHAI}/{bai['slug']}")
    assert phan_hoi.status_code == 200
    ct = phan_hoi.json()
    assert ct["noi_dung"] == "## Rửa tay\n\nThường xuyên." and ct["loai"] == "bai_viet" and ct["ngay_dang"]
    assert set(ct) == {"id", "tieu_de", "slug", "loai", "anh_bia_url", "noi_dung", "ngay_dang"}
    nhap = await tao_bai(clients_theo_vai_tro["ADMIN"], tieu_de="Bản nháp")
    assert la_loi(await client.get(f"{GOC_CONG_KHAI}/{nhap['slug']}"), 404, "KHONG_TIM_THAY")
    assert la_loi(await client.get(f"{GOC_CONG_KHAI}/khong-co"), 404, "KHONG_TIM_THAY")
    assert la_loi(await client.get(f"{GOC_CONG_KHAI}/Sai_Dinh_Dang"), 400, "DU_LIEU_KHONG_HOP_LE")


async def test_ngay_dang_la_ngay_duyet_khi_co(clients_theo_vai_tro, client, db):
    bai = await dang_bai(clients_theo_vai_tro)
    from sqlalchemy import select

    bv = (await db.execute(select(BaiViet).where(BaiViet.id == bai["id"]))).scalar_one()
    bv.ngay_duyet = bay_gio_utc() - timedelta(days=3)
    await db.flush()
    ngay = (await client.get(f"{GOC_CONG_KHAI}/{bai['slug']}")).json()["ngay_dang"]
    assert ngay.startswith(bv.ngay_duyet.isoformat()[:16])


@pytest.mark.parametrize(
    ("markdown", "mong_doi"),
    [
        ("# Tiêu đề\n\nĐoạn **đậm** và `mã`.", "Tiêu đề Đoạn đậm và mã."),
        ("[Liên kết](https://x.vn) và ![ảnh](a.png) hết", "Liên kết và hết"),
        ("- ý một\n- ý hai\n\n> trích dẫn", "ý một ý hai trích dẫn"),
        ("```\ncode bỏ\n```\nchữ thật", "chữ thật"),
        ("   \n\n ", ""),
    ],
)
def test_tom_tat_bo_ky_hieu_markdown(markdown, mong_doi):
    assert tom_tat(markdown) == mong_doi


def test_tom_tat_cat_o_200_ky_tu_tai_ranh_gioi_tu():
    ket = tom_tat("chữ " * 100)
    assert ket.endswith("…") and len(ket) <= 201 and not ket[:-1].endswith(" ")


# --- Tải ảnh -----------------------------------------------------------------------------------------------------------


def cac_tep() -> list[Path]:
    return sorted(p for p in (Path(settings.LUU_TRU_THU_MUC) / "cong_khai").rglob("*") if p.is_file())


@pytest.mark.parametrize(("duong", "thu_muc"), [(f"{GOC_BANNER}/anh", "banner"), (f"{GOC_BAI_VIET}/anh", "bai-viet")])
async def test_admin_tai_anh_len_vung_cong_khai_va_lay_lai_duoc(dang_nhap_admin, client, db, duong, thu_muc):
    phan_hoi = await dang_nhap_admin.post(duong, files={"tep": ("a.jpg", JPEG, "image/jpeg")})
    assert phan_hoi.status_code == 201, phan_hoi.text
    url = phan_hoi.json()["url"]
    assert url.startswith(f"/api/v1/tep/{thu_muc}/") and url.endswith(".jpg")
    tai = await client.get(url)
    assert tai.status_code == 200 and tai.content == JPEG and tai.headers["content-type"] == "image/jpeg"
    assert len(cac_tep()) == 1
    ghi = await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "tao")
    assert ghi[0].bang == "tep_cong_khai" and ghi[0].gia_tri_moi == {"url": url}


@pytest.mark.parametrize("duong", [f"{GOC_BANNER}/anh", f"{GOC_BAI_VIET}/anh"])
async def test_tai_anh_sai_hoac_khong_du_quyen_khong_ghi_tep(clients_theo_vai_tro, client, db, duong):
    admin = clients_theo_vai_tro["ADMIN"]
    for noi_dung, ten in ((b"khong phai anh", "a.jpg"), (b"<svg onload=alert(1)>", "a.svg"), (b"", "rong.jpg")):
        phan_hoi = await admin.post(duong, files={"tep": (ten, noi_dung, "image/jpeg")})
        assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE"), (ten, phan_hoi.text)
    for vai_tro in ("PHARMACIST", "WAREHOUSE"):
        phan_hoi = await clients_theo_vai_tro[vai_tro].post(duong, files={"tep": ("a.jpg", JPEG, "image/jpeg")})
        assert la_loi(phan_hoi, 403, "KHONG_CO_QUYEN")
    assert (await client.post(duong, files={"tep": ("a.jpg", JPEG, "image/jpeg")})).status_code == 401
    assert cac_tep() == []


@pytest.mark.parametrize("duong", [f"{GOC_BANNER}/anh", f"{GOC_BAI_VIET}/anh"])
async def test_anh_qua_5mb_bi_413_truoc_xac_thuc(client, duong):
    lon = JPEG + b"0" * (luu_tru.TOI_DA_ANH_BYTE + 100 * 1024)
    phan_hoi = await client.post(duong, files={"tep": ("a.jpg", lon, "image/jpeg")})  # không có token
    assert la_loi(phan_hoi, 413, "TEP_QUA_LON")
    assert cac_tep() == []

"""AD07: soạn, sửa, gỡ, đăng lại bài viết, chính sách, FAQ (/api/v1/noi-bo/bai-viet) và liên hệ với dược sĩ duyệt."""

import pytest
from sqlalchemy import func, select

from app.models.enums import TrangThaiNoiDung
from app.models.he_thong import BaiViet
from tests.nhan_vien.dung_chung import nhat_ky
from tests.noi_dung_web.mau_noi_dung_web import (
    GOC_BAI_VIET,
    GOC_CHO_DUYET,
    GOC_CONG_KHAI,
    duyet_bai,
    la_loi,
    tao_bai,
    than_bai,
)

# --- Tạo ---------------------------------------------------------------------------------------------------------------


async def test_bai_suc_khoe_tao_o_nhap_chua_cong_khai_chinh_sach_va_faq_dang_ngay(dang_nhap_admin, client, db):
    bai = await tao_bai(dang_nhap_admin, tieu_de="Phòng cảm cúm", dua_vao_ai=True)
    assert bai["trang_thai"] == "nhap" and bai["loai"] == "bai_viet" and bai["slug"] == "phong-cam-cum"
    assert bai["ngay_duyet"] is None and bai["duoc_si_duyet"] is None and bai["dua_vao_ai"] is True
    assert bai["tac_gia"] == dang_nhap_admin.tai_khoan.ho_ten and len(bai["phien_ban"]) == 16
    cs = await tao_bai(dang_nhap_admin, loai="chinh_sach", tieu_de="Chính sách đổi trả")
    faq = await tao_bai(dang_nhap_admin, loai="faq", tieu_de="Giao hàng mất bao lâu?")
    for b in (cs, faq):
        assert b["trang_thai"] == "da_duyet" and b["ngay_duyet"] is not None and b["duoc_si_duyet"] is None
    assert (await client.get(f"{GOC_CONG_KHAI}/{bai['slug']}")).status_code == 404  # bài sức khỏe chưa duyệt
    assert (await client.get(f"{GOC_CONG_KHAI}/{cs['slug']}")).status_code == 200  # chính sách đăng ngay
    ghi = await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "tao")
    assert len(ghi) == 3 and "noi_dung" not in ghi[0].gia_tri_moi and ghi[0].gia_tri_moi["do_dai_noi_dung"] > 0


async def test_slug_trung_them_hau_to_va_slug_khong_doi_khi_sua_tieu_de(dang_nhap_admin, db):
    a = await tao_bai(dang_nhap_admin, tieu_de="Cảm cúm")
    b = await tao_bai(dang_nhap_admin, tieu_de="Cảm  cúm")
    c = await tao_bai(dang_nhap_admin, tieu_de="CẢM CÚM", loai="faq")
    assert (a["slug"], b["slug"], c["slug"]) == ("cam-cum", "cam-cum-2", "cam-cum-3")
    sua = await dang_nhap_admin.patch(
        f"{GOC_BAI_VIET}/{a['id']}", json={"phien_ban": a["phien_ban"], "tieu_de": "Tên khác hẳn"}
    )
    assert sua.json()["tieu_de"] == "Tên khác hẳn" and sua.json()["slug"] == "cam-cum"  # đường dẫn công khai ổn định


@pytest.mark.parametrize(
    ("ten_ca", "ghi_de"),
    [
        ("tiêu đề rỗng", {"tieu_de": "   "}),
        ("tiêu đề chỉ ký hiệu", {"tieu_de": "!!! ???"}),
        ("tiêu đề quá dài", {"tieu_de": "x" * 256}),
        ("nội dung rỗng", {"noi_dung": "  \n "}),
        ("nội dung quá dài", {"noi_dung": "x" * 100_001}),
        ("loại lạ", {"loai": "tin_tuc"}),
        ("ảnh bìa nguy hiểm", {"anh_bia_url": "javascript:alert(1)"}),
        ("tự đặt trạng thái", {"trang_thai": "da_duyet"}),
        ("tự đặt người duyệt", {"duoc_si_duyet_id": 1}),
        ("tự đặt slug", {"slug": "tuy-y"}),
        ("dua_vao_ai không phải bool", {"dua_vao_ai": "co"}),
        ("ký tự NUL trong tiêu đề", {"tieu_de": "a\u0000b"}),
    ],
)
async def test_bai_sai_la_400_va_khong_tao_gi(dang_nhap_admin, db, ten_ca, ghi_de):
    phan_hoi = await dang_nhap_admin.post(GOC_BAI_VIET, json=than_bai(**ghi_de))
    assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE"), (ten_ca, phan_hoi.text)
    assert (await db.scalar(select(func.count()).select_from(BaiViet))) == 0


async def test_noi_dung_markdown_giu_nguyen_ky_tu_xuong_dong_va_html_khong_bi_sua(dang_nhap_admin, db):
    nd = "# Tiêu đề\n\n- ý 1\n- ý 2\n\n<script>alert(1)</script>\n\n[liên kết](javascript:alert(1))"
    bai = await tao_bai(dang_nhap_admin, noi_dung=nd)
    assert bai["noi_dung"] == nd  # lưu nguyên văn; làm sạch là việc của lúc hiển thị (frontend không render HTML thô)


# --- Danh sách, chi tiết ------------------------------------------------------------------------------------------------


async def test_danh_sach_loc_theo_loai_trang_thai_va_tieu_de_khong_dau(dang_nhap_admin, db):
    a = await tao_bai(dang_nhap_admin, tieu_de="Thuốc ho cho trẻ")
    await tao_bai(dang_nhap_admin, loai="faq", tieu_de="Hỏi về thuốc")
    await tao_bai(dang_nhap_admin, loai="chinh_sach", tieu_de="Chính sách bảo mật")
    tat_ca = (await dang_nhap_admin.get(GOC_BAI_VIET)).json()
    assert tat_ca["tong"] == 3
    assert set(tat_ca["du_lieu"][0]) == {
        "id", "tieu_de", "slug", "loai", "trang_thai", "dua_vao_ai", "tac_gia", "created_at", "updated_at", "ngay_duyet",
    }  # fmt: skip
    for tham, mong in (
        ({"loai": "faq"}, 1),
        ({"trang_thai": "nhap"}, 1),
        ({"trang_thai": "da_duyet"}, 2),
        ({"q": "THUOC"}, 2),
        ({"q": "%"}, 0),
        ({"loai": "bai_viet", "q": "tre"}, 1),
    ):
        assert (await dang_nhap_admin.get(GOC_BAI_VIET, params=tham)).json()["tong"] == mong, tham
    chi_tiet = (await dang_nhap_admin.get(f"{GOC_BAI_VIET}/{a['id']}")).json()
    assert chi_tiet["noi_dung"] == a["noi_dung"] and chi_tiet["phien_ban"] == a["phien_ban"]
    assert la_loi(await dang_nhap_admin.get(f"{GOC_BAI_VIET}/2000000000"), 404, "KHONG_TIM_THAY")
    assert (await dang_nhap_admin.get(GOC_BAI_VIET, params={"loai": "tin"})).status_code == 400


# --- Sửa ---------------------------------------------------------------------------------------------------------------


async def test_sua_bai_da_duyet_ve_cho_duyet_bo_dau_duyet_cu_va_phai_duyet_lai(clients_theo_vai_tro, client, db):
    admin, duoc_si = clients_theo_vai_tro["ADMIN"], clients_theo_vai_tro["PHARMACIST"]
    bai = await tao_bai(admin)
    da_duyet = await duyet_bai(duoc_si, bai)
    assert da_duyet["trang_thai"] == "da_duyet" and da_duyet["duoc_si_duyet"]
    assert (await client.get(f"{GOC_CONG_KHAI}/{bai['slug']}")).status_code == 200
    xem = (await admin.get(f"{GOC_BAI_VIET}/{bai['id']}")).json()
    sua = await admin.patch(
        f"{GOC_BAI_VIET}/{bai['id']}", json={"phien_ban": xem["phien_ban"], "noi_dung": "Nội dung đã sửa"}
    )
    assert sua.status_code == 200, sua.text
    moi = sua.json()
    assert moi["trang_thai"] == "nhap" and moi["duoc_si_duyet"] is None and moi["ngay_duyet"] is None
    assert (await client.get(f"{GOC_CONG_KHAI}/{bai['slug']}")).status_code == 404  # bản chưa duyệt không công khai
    cho = (await duoc_si.get(GOC_CHO_DUYET)).json()
    assert [b["id"] for b in cho["du_lieu"]] == [bai["id"]]
    assert (await duyet_bai(duoc_si, bai))["trang_thai"] == "da_duyet"


async def test_chi_doi_dua_vao_ai_khong_phai_duyet_lai_con_chinh_sach_sua_van_dang(clients_theo_vai_tro, client, db):
    admin, duoc_si = clients_theo_vai_tro["ADMIN"], clients_theo_vai_tro["PHARMACIST"]
    bai = await duyet_bai(duoc_si, await tao_bai(admin))
    sua = await admin.patch(f"{GOC_BAI_VIET}/{bai['id']}", json={"phien_ban": bai["phien_ban"], "dua_vao_ai": True})
    assert sua.json()["trang_thai"] == "da_duyet" and sua.json()["dua_vao_ai"] is True
    cs = await tao_bai(admin, loai="chinh_sach", tieu_de="Chính sách giao hàng")
    sua_cs = await admin.patch(f"{GOC_BAI_VIET}/{cs['id']}", json={"phien_ban": cs["phien_ban"], "noi_dung": "Mới"})
    assert sua_cs.json()["trang_thai"] == "da_duyet"
    assert (await client.get(f"{GOC_CONG_KHAI}/{cs['slug']}")).json()["noi_dung"] == "Mới"


async def test_sua_bai_nhap_giu_nhap_khong_doi_loai_va_xoa_anh_bia_bang_null(dang_nhap_admin, db):
    bai = await tao_bai(dang_nhap_admin, anh_bia_url="/api/v1/tep/bai-viet/a.jpg")
    sua = await dang_nhap_admin.patch(
        f"{GOC_BAI_VIET}/{bai['id']}", json={"phien_ban": bai["phien_ban"], "anh_bia_url": None}
    )
    assert sua.json()["anh_bia_url"] is None and sua.json()["trang_thai"] == "nhap"
    doi_loai = await dang_nhap_admin.patch(
        f"{GOC_BAI_VIET}/{bai['id']}", json={"phien_ban": sua.json()["phien_ban"], "loai": "faq"}
    )
    assert la_loi(doi_loai, 400, "DU_LIEU_KHONG_HOP_LE")  # đổi loại là cách vòng qua dược sĩ duyệt
    for ghi_de in ({"tieu_de": None}, {"noi_dung": None}, {"dua_vao_ai": None}, {"trang_thai": "da_duyet"}):
        phan_hoi = await dang_nhap_admin.patch(
            f"{GOC_BAI_VIET}/{bai['id']}", json={"phien_ban": sua.json()["phien_ban"], **ghi_de}
        )
        assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE"), ghi_de


async def test_sua_khong_thay_doi_khong_ghi_nhat_ky_va_nhat_ky_khong_chua_toan_van(dang_nhap_admin, db):
    bai = await tao_bai(dang_nhap_admin)
    await dang_nhap_admin.patch(
        f"{GOC_BAI_VIET}/{bai['id']}", json={"phien_ban": bai["phien_ban"], "tieu_de": bai["tieu_de"]}
    )
    assert await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "sua") == []
    sua = await dang_nhap_admin.patch(
        f"{GOC_BAI_VIET}/{bai['id']}", json={"phien_ban": bai["phien_ban"], "noi_dung": "Khác hẳn"}
    )
    assert sua.status_code == 200
    ghi = await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "sua")
    assert (
        len(ghi) == 1 and set(ghi[0].gia_tri_moi) == {"do_dai_noi_dung"} and "Khác hẳn" not in str(ghi[0].gia_tri_moi)
    )


async def test_phien_ban_cu_la_409_o_moi_thao_tac_ghi(dang_nhap_admin, db):
    bai = await tao_bai(dang_nhap_admin)
    assert (
        await dang_nhap_admin.patch(
            f"{GOC_BAI_VIET}/{bai['id']}", json={"phien_ban": bai["phien_ban"], "tieu_de": "Mới"}
        )
    ).status_code == 200
    cu = {"phien_ban": bai["phien_ban"]}
    for duong, than in (
        (f"{GOC_BAI_VIET}/{bai['id']}", None),
        (f"{GOC_BAI_VIET}/{bai['id']}/go", cu),
        (f"{GOC_BAI_VIET}/{bai['id']}/dang", cu),
    ):
        phan_hoi = (
            await dang_nhap_admin.patch(duong, json={**cu, "noi_dung": "Ghi đè"})
            if than is None
            else await dang_nhap_admin.post(duong, json=than)
        )
        assert la_loi(phan_hoi, 409, "DU_LIEU_DA_THAY_DOI"), duong
        assert phan_hoi.json()["chi_tiet"]["phien_ban_hien_tai"] != bai["phien_ban"]
    assert (await dang_nhap_admin.get(f"{GOC_BAI_VIET}/{bai['id']}")).json()["noi_dung"] == bai["noi_dung"]


# --- Gỡ và đăng lại ----------------------------------------------------------------------------------------------------


async def test_go_bai_khoi_website_va_hang_cho_duyet_roi_dang_lai(clients_theo_vai_tro, client, db):
    admin, duoc_si = clients_theo_vai_tro["ADMIN"], clients_theo_vai_tro["PHARMACIST"]
    bai = await duyet_bai(duoc_si, await tao_bai(admin))
    go = await admin.post(f"{GOC_BAI_VIET}/{bai['id']}/go", json={"phien_ban": bai["phien_ban"]})
    assert go.json()["trang_thai"] == "luu_tru"
    assert (await client.get(f"{GOC_CONG_KHAI}/{bai['slug']}")).status_code == 404
    assert la_loi(
        await admin.post(f"{GOC_BAI_VIET}/{bai['id']}/go", json={"phien_ban": go.json()["phien_ban"]}),
        409,
        "DU_LIEU_DA_THAY_DOI",
    )
    dang = await admin.post(f"{GOC_BAI_VIET}/{bai['id']}/dang", json={"phien_ban": go.json()["phien_ban"]})
    assert dang.json()["trang_thai"] == "nhap" and dang.json()["duoc_si_duyet"] is None  # bài sức khỏe phải duyệt lại
    assert (await client.get(f"{GOC_CONG_KHAI}/{bai['slug']}")).status_code == 404
    assert la_loi(
        await admin.post(f"{GOC_BAI_VIET}/{bai['id']}/dang", json={"phien_ban": dang.json()["phien_ban"]}),
        409,
        "DU_LIEU_DA_THAY_DOI",
    )


async def test_go_bai_nhap_khoi_hang_cho_duyet_va_dang_lai_chinh_sach_len_thang(clients_theo_vai_tro, client, db):
    admin, duoc_si = clients_theo_vai_tro["ADMIN"], clients_theo_vai_tro["PHARMACIST"]
    nhap = await tao_bai(admin)
    go = await admin.post(f"{GOC_BAI_VIET}/{nhap['id']}/go", json={"phien_ban": nhap["phien_ban"]})
    assert go.status_code == 200 and (await duoc_si.get(GOC_CHO_DUYET)).json()["tong"] == 0
    cs = await tao_bai(admin, loai="chinh_sach", tieu_de="Chính sách")
    go_cs = await admin.post(f"{GOC_BAI_VIET}/{cs['id']}/go", json={"phien_ban": cs["phien_ban"]})
    assert (await client.get(f"{GOC_CONG_KHAI}/{cs['slug']}")).status_code == 404
    dang = await admin.post(f"{GOC_BAI_VIET}/{cs['id']}/dang", json={"phien_ban": go_cs.json()["phien_ban"]})
    assert dang.json()["trang_thai"] == "da_duyet" and dang.json()["ngay_duyet"] is not None
    assert (await client.get(f"{GOC_CONG_KHAI}/{cs['slug']}")).status_code == 200


# --- Quyền và tách nhiệm vụ -------------------------------------------------------------------------------------------


async def test_chi_admin_soan_duoc_si_va_kho_bi_chan_admin_khong_tu_duyet(clients_theo_vai_tro, client, db):
    admin = clients_theo_vai_tro["ADMIN"]
    bai = await tao_bai(admin)
    for vai_tro in ("PHARMACIST", "WAREHOUSE"):
        c = clients_theo_vai_tro[vai_tro]
        assert la_loi(await c.get(GOC_BAI_VIET), 403, "KHONG_CO_QUYEN"), vai_tro
        assert la_loi(await c.post(GOC_BAI_VIET, json=than_bai()), 403, "KHONG_CO_QUYEN"), vai_tro
        sua = await c.patch(f"{GOC_BAI_VIET}/{bai['id']}", json={"phien_ban": bai["phien_ban"], "tieu_de": "x"})
        assert la_loi(sua, 403, "KHONG_CO_QUYEN"), vai_tro
        for hanh_dong in ("go", "dang"):
            phan_hoi = await c.post(f"{GOC_BAI_VIET}/{bai['id']}/{hanh_dong}", json={"phien_ban": bai["phien_ban"]})
            assert la_loi(phan_hoi, 403, "KHONG_CO_QUYEN"), (vai_tro, hanh_dong)
    assert (await client.post(GOC_BAI_VIET, json=than_bai())).status_code == 401
    tu_duyet = await admin.post(f"{GOC_CHO_DUYET}/{bai['id']}/duyet", json={"phien_ban": bai["phien_ban"]})
    assert la_loi(tu_duyet, 403, "KHONG_CO_QUYEN")  # Admin soạn nhưng không duyệt được bài của mình
    assert (await admin.get(f"{GOC_BAI_VIET}/{bai['id']}")).json()["trang_thai"] == TrangThaiNoiDung.nhap


async def test_service_tu_choi_nguoi_thuc_hien_khong_phai_admin(db):
    from app.core.loi import LoiNghiepVu
    from app.modules.noi_dung_web import bai_viet as dich_vu
    from app.modules.noi_dung_web.schemas import BaiVietVao
    from tests.factories import tao_nhan_vien

    duoc_si = await tao_nhan_vien(db, "PHARMACIST")
    with pytest.raises(LoiNghiepVu) as loi:
        await dich_vu.tao(db, duoc_si, BaiVietVao(**than_bai()), ip="127.0.0.1")
    assert loi.value.ma_loi == "KHONG_CO_QUYEN"
    assert (await db.scalar(select(func.count()).select_from(BaiViet))) == 0

"""AD03: Admin quản lý cây danh mục tối đa 3 cấp (/api/v1/noi-bo/danh-muc)."""

import asyncio

import pytest
from sqlalchemy import func, select

from app.core import phan_quyen
from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc
from app.models.he_thong import NhanVien, NhatKyHeThong, Quyen, VaiTro, VaiTroQuyen
from app.models.san_pham import DanhMuc
from app.modules.san_pham import danh_muc as dich_vu
from tests.factories import tao_danh_muc, tao_nhan_vien, tao_san_pham
from tests.nhan_vien.dung_chung import nhat_ky

GOC = "/api/v1/noi-bo/danh-muc"


def la_loi(phan_hoi, status, ma_loi):
    return phan_hoi.status_code == status and phan_hoi.json()["ma_loi"] == ma_loi


def phang(cay: list[dict]) -> dict[int, dict]:
    """Cây lồng nhau thành bảng id -> nút."""
    ket: dict[int, dict] = {}
    for nut in cay:
        ket[nut["id"]] = nut
        ket.update(phang(nut["con"]))
    return ket


async def doc_cay(admin) -> list[dict]:
    phan_hoi = await admin.get(GOC)
    assert phan_hoi.status_code == 200, phan_hoi.text
    return phan_hoi.json()


async def tao(admin, ten, cha=None, **them):
    return await admin.post(GOC, json={"ten": ten, "danh_muc_cha_id": cha, **them})


async def dat_vi_tri(admin, id_, cha, vi_tri):
    return await admin.put(f"{GOC}/{id_}/vi-tri", json={"danh_muc_cha_id": cha, "vi_tri": vi_tri})


async def tao_cay_ba_cap(db):
    """Thuốc > Giảm đau > Paracetamol; Thuốc > Ho. Trả (thuoc, giam_dau, para, ho)."""
    thuoc = await tao_danh_muc(db, "Thuốc", thu_tu=0)
    giam_dau = await tao_danh_muc(db, "Giảm đau", thuoc, thu_tu=0)
    para = await tao_danh_muc(db, "Paracetamol", giam_dau, thu_tu=0)
    ho = await tao_danh_muc(db, "Ho", thuoc, thu_tu=1)
    return thuoc, giam_dau, para, ho


def thu_tu_con(cay, id_cha) -> list[int]:
    nut = phang(cay)
    con = nut[id_cha]["con"] if id_cha is not None else cay
    return [c["id"] for c in con]


# --- Đọc cây -----------------------------------------------------------------------------------------------------------


async def test_cay_long_nhau_xep_theo_thu_tu_roi_id_kem_cap_va_so_san_pham(dang_nhap_admin, db):
    thuoc, giam_dau, para, ho = await tao_cay_ba_cap(db)
    khac = await tao_danh_muc(db, "Khác", thu_tu=0)  # cùng thu_tu với Thuốc: id nhỏ hơn đứng trước
    await tao_san_pham(db, danh_muc_id=para.id)
    await tao_san_pham(db, danh_muc_id=para.id)
    da_xoa = await tao_san_pham(db, danh_muc_id=para.id)
    da_xoa.deleted_at = bay_gio_utc()
    await db.flush()
    cay = await doc_cay(dang_nhap_admin)
    assert [n["id"] for n in cay if n["id"] in (thuoc.id, khac.id)] == [thuoc.id, khac.id]
    nut = phang(cay)
    assert [nut[d.id]["cap"] for d in (thuoc, giam_dau, para)] == [1, 2, 3]
    assert [c["id"] for c in nut[thuoc.id]["con"]] == [giam_dau.id, ho.id]  # thu_tu 0 rồi 1
    assert nut[para.id]["so_san_pham"] == 2 and nut[giam_dau.id]["so_san_pham"] == 0  # trực tiếp, bỏ sản phẩm đã xóa
    assert nut[para.id]["con"] == [] and nut[para.id]["danh_muc_cha_id"] == giam_dau.id
    assert set(nut[thuoc.id]) == {
        "id",
        "ten",
        "slug",
        "danh_muc_cha_id",
        "anh_url",
        "thu_tu",
        "dang_hien_thi",
        "cap",
        "so_san_pham",
        "con",
    }


async def test_cay_co_danh_muc_dang_an_nhung_khong_co_danh_muc_da_xoa(dang_nhap_admin, db):
    thuoc, giam_dau, _, ho = await tao_cay_ba_cap(db)
    ho.dang_hien_thi = False
    giam_dau.deleted_at = bay_gio_utc()
    await db.flush()
    nut = phang(await doc_cay(dang_nhap_admin))
    assert nut[ho.id]["dang_hien_thi"] is False
    assert giam_dau.id not in nut
    assert [c["id"] for c in nut[thuoc.id]["con"]] == [ho.id]


# --- Tạo -----------------------------------------------------------------------------------------------------------------


async def test_tao_goc_sinh_slug_khong_dau_cap_1_xep_cuoi_va_ghi_nhat_ky(dang_nhap_admin, db):
    a = (await tao(dang_nhap_admin, "Thuốc ho Bổ phế")).json()
    b = (await tao(dang_nhap_admin, "Đường & sữa!")).json()
    assert (a["slug"], a["cap"], a["danh_muc_cha_id"], a["dang_hien_thi"], a["con"]) == (
        "thuoc-ho-bo-phe",
        1,
        None,
        True,
        [],
    )
    assert b["slug"] == "duong-sua" and b["thu_tu"] > a["thu_tu"]  # xếp sau anh em hiện có
    phan_hoi = await tao(dang_nhap_admin, "  Có   khoảng  trắng ", anh_url="/storage/a.png", dang_hien_thi=False)
    assert phan_hoi.status_code == 201
    than = phan_hoi.json()
    assert than["ten"] == "Có khoảng trắng" and than["dang_hien_thi"] is False and than["anh_url"] == "/storage/a.png"
    dong = (await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "tao"))[-1]
    assert (dong.bang, dong.ban_ghi_id) == ("danh_muc", str(than["id"]))
    assert dong.gia_tri_moi["ten"] == "Có khoảng trắng" and dong.gia_tri_cu is None


async def test_slug_trung_thi_them_hau_to_ke_ca_voi_danh_muc_da_xoa(dang_nhap_admin, db):
    a = (await tao(dang_nhap_admin, "Vitamin")).json()
    cu = await tao_danh_muc(db, "Vitamin cũ", slug="vitamin-2", deleted_at=bay_gio_utc())  # đã xóa vẫn giữ chỗ slug
    nhom = (await tao(dang_nhap_admin, "Nhóm")).json()
    b = (await tao(dang_nhap_admin, "Vitamin", nhom["id"])).json()  # khác cha nên tên không trùng, nhưng slug thì có
    c = (
        await tao(dang_nhap_admin, "VITAMIN!")
    ).json()  # khác "Vitamin" ở dấu chấm than: tên không trùng, slug lại trùng
    assert (a["slug"], cu.slug, b["slug"], c["slug"]) == ("vitamin", "vitamin-2", "vitamin-3", "vitamin-4")


@pytest.mark.parametrize("ten", ["???", "---", "   ", ""])
async def test_ten_khong_tao_duoc_slug_hoac_rong_la_400(dang_nhap_admin, ten):
    assert la_loi(await tao(dang_nhap_admin, ten), 400, "DU_LIEU_KHONG_HOP_LE")


async def test_ten_qua_dai_va_anh_url_la_scheme_la_bi_tu_choi(dang_nhap_admin):
    assert la_loi(await tao(dang_nhap_admin, "a" * 151), 400, "DU_LIEU_KHONG_HOP_LE")
    for url in (
        "javascript:alert(1)",
        "data:text/html;base64,AAA",
        "ftp://x/y.png",
        "a.png",
        "//evil.com/x.png",
        "https://" + "a" * 600,
    ):
        assert la_loi(await tao(dang_nhap_admin, "Có ảnh", anh_url=url), 400, "DU_LIEU_KHONG_HOP_LE"), url
    for url in ("/storage/x.png", "https://cdn.example.com/x.png", "http://localhost/x.png", None):
        phan_hoi = await tao(dang_nhap_admin, f"Ảnh {url}", anh_url=url)
        assert phan_hoi.status_code == 201, (url, phan_hoi.text)


async def test_toi_da_ba_cap_cap_4_bi_tu_choi_va_cha_khong_hop_le(dang_nhap_admin, db):
    thuoc, giam_dau, para, _ = await tao_cay_ba_cap(db)
    cap3 = await tao(dang_nhap_admin, "Cấp 3 mới", giam_dau.id)
    assert cap3.status_code == 201 and cap3.json()["cap"] == 3
    phan_hoi = await tao(dang_nhap_admin, "Cấp 4", para.id)
    assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE")
    assert (
        phan_hoi.json()["chi_tiet"][0]["truong"] == "danh_muc_cha_id"
        and "3 cấp" in phan_hoi.json()["chi_tiet"][0]["loi"]
    )
    da_xoa = await tao_danh_muc(db, "Đã xóa", deleted_at=bay_gio_utc())
    for cha in (2_000_000_000, da_xoa.id):
        phan_hoi = await tao(dang_nhap_admin, "Con của cha lạ", cha)
        assert (
            la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE")
            and phan_hoi.json()["chi_tiet"][0]["truong"] == "danh_muc_cha_id"
        )
    assert la_loi(await tao(dang_nhap_admin, "Cha vượt int32", 2_147_483_648), 400, "DU_LIEU_KHONG_HOP_LE")


async def test_trung_ten_anh_em_la_409_khong_phan_biet_dau_hoa_thuong_nhung_khac_cha_thi_duoc(dang_nhap_admin, db):
    thuoc, giam_dau, _, ho = await tao_cay_ba_cap(db)
    assert la_loi(await tao(dang_nhap_admin, "HO", thuoc.id), 409, "TRUNG_DU_LIEU")
    assert la_loi(await tao(dang_nhap_admin, "giam dau", thuoc.id), 409, "TRUNG_DU_LIEU")
    phan_hoi = await tao(dang_nhap_admin, "Ho", giam_dau.id)  # khác cha
    assert phan_hoi.status_code == 201


# --- Sửa -----------------------------------------------------------------------------------------------------------------


async def test_doi_ten_giu_nguyen_slug_va_ghi_nhat_ky_cu_moi(dang_nhap_admin, db):
    dm = (await tao(dang_nhap_admin, "Thuốc ho")).json()
    phan_hoi = await dang_nhap_admin.patch(
        f"{GOC}/{dm['id']}", json={"ten": "Thuốc ho người lớn", "anh_url": "/a.png", "dang_hien_thi": False}
    )
    assert phan_hoi.status_code == 200
    than = phan_hoi.json()
    assert (than["ten"], than["slug"], than["anh_url"], than["dang_hien_thi"]) == (
        "Thuốc ho người lớn",
        "thuoc-ho",
        "/a.png",
        False,
    )
    dong = (await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "sua"))[-1]
    assert dong.gia_tri_cu == {"ten": "Thuốc ho", "anh_url": None, "dang_hien_thi": True}
    assert dong.gia_tri_moi == {"ten": "Thuốc ho người lớn", "anh_url": "/a.png", "dang_hien_thi": False}


async def test_sua_khong_doi_gi_thi_khong_ghi_nhat_ky_va_bo_anh_bang_null(dang_nhap_admin, db):
    dm = (await tao(dang_nhap_admin, "Thuốc ho", anh_url="/a.png")).json()
    truoc = len(await nhat_ky(db, dang_nhap_admin.tai_khoan.id))
    assert (
        await dang_nhap_admin.patch(f"{GOC}/{dm['id']}", json={"ten": "Thuốc ho", "dang_hien_thi": True})
    ).status_code == 200
    assert len(await nhat_ky(db, dang_nhap_admin.tai_khoan.id)) == truoc
    phan_hoi = await dang_nhap_admin.patch(f"{GOC}/{dm['id']}", json={"anh_url": None})
    assert phan_hoi.status_code == 200 and phan_hoi.json()["anh_url"] is None


@pytest.mark.parametrize(
    "than",
    [
        {"danh_muc_cha_id": 1},
        {"thu_tu": 3},
        {"slug": "x"},
        {"deleted_at": "2020-01-01T00:00:00Z"},
        {"ten": None},
        {"dang_hien_thi": None},
    ],
)
async def test_sua_truong_khong_duoc_phep_la_400(dang_nhap_admin, db, than):
    dm = await tao_danh_muc(db, "Thuốc ho")
    assert la_loi(await dang_nhap_admin.patch(f"{GOC}/{dm.id}", json=than), 400, "DU_LIEU_KHONG_HOP_LE")


async def test_doi_ten_trung_anh_em_la_409_nhung_giu_ten_cu_hoac_doi_hoa_thuong_cua_chinh_no_thi_duoc(
    dang_nhap_admin, db
):
    thuoc, giam_dau, _, ho = await tao_cay_ba_cap(db)
    assert la_loi(await dang_nhap_admin.patch(f"{GOC}/{ho.id}", json={"ten": "giảm ĐAU"}), 409, "TRUNG_DU_LIEU")
    assert (
        await dang_nhap_admin.patch(f"{GOC}/{ho.id}", json={"ten": "HO"})
    ).status_code == 200  # chỉ đổi hoa thường của chính nó


@pytest.mark.parametrize(
    "them",
    [
        {"slug": "tu-dat"},
        {"id": 5},
        {"thu_tu": 3},
        {"deleted_at": "2020-01-01T00:00:00Z"},
        {"cap": 2},
        {"so_san_pham": 9},
    ],
)
async def test_tao_voi_truong_khong_duoc_phep_la_400_va_khong_tao_gi(dang_nhap_admin, db, them):
    phan_hoi = await tao(dang_nhap_admin, "Có trường lạ", **them)
    assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE"), phan_hoi.text
    assert (await db.execute(select(func.count()).select_from(DanhMuc))).scalar_one() == 0


async def test_sua_xoa_danh_muc_khong_co_hoac_da_xoa_la_404(dang_nhap_admin, db):
    da_xoa = await tao_danh_muc(db, "Đã xóa", deleted_at=bay_gio_utc())
    for id_ in (da_xoa.id, 2_000_000_000):
        assert la_loi(await dang_nhap_admin.patch(f"{GOC}/{id_}", json={"ten": "X"}), 404, "KHONG_TIM_THAY")
        assert la_loi(await dang_nhap_admin.delete(f"{GOC}/{id_}"), 404, "KHONG_TIM_THAY")
        assert la_loi(await dat_vi_tri(dang_nhap_admin, id_, None, 0), 404, "KHONG_TIM_THAY")
    for id_ in (0, -1, 2_147_483_648):
        assert la_loi(await dang_nhap_admin.delete(f"{GOC}/{id_}"), 400, "DU_LIEU_KHONG_HOP_LE")


# --- Sắp xếp và chuyển (kéo thả) ---------------------------------------------------------------------------------------------


async def test_sap_xep_lai_trong_cung_cha_danh_lai_thu_tu_lien_tuc(dang_nhap_admin, db):
    a = await tao_danh_muc(db, "A", thu_tu=10)
    b = await tao_danh_muc(db, "B", thu_tu=20)
    c = await tao_danh_muc(db, "C", thu_tu=30)
    phan_hoi = await dat_vi_tri(dang_nhap_admin, c.id, None, 0)
    assert phan_hoi.status_code == 200
    cay = phan_hoi.json()
    assert thu_tu_con(cay, None) == [c.id, a.id, b.id]
    assert [phang(cay)[d.id]["thu_tu"] for d in (c, a, b)] == [0, 1, 2]
    cay = (await dat_vi_tri(dang_nhap_admin, c.id, None, 2)).json()  # xuống cuối
    assert thu_tu_con(cay, None) == [a.id, b.id, c.id]
    cay = (await dat_vi_tri(dang_nhap_admin, a.id, None, 99)).json()  # quá số anh em: đặt cuối
    assert thu_tu_con(cay, None) == [b.id, c.id, a.id]


async def test_chuyen_sang_cha_khac_danh_lai_thu_tu_ca_cha_cu_lan_cha_moi(dang_nhap_admin, db):
    thuoc, giam_dau, para, ho = await tao_cay_ba_cap(db)
    khac = await tao_danh_muc(db, "Khác", thu_tu=5)
    con1 = await tao_danh_muc(db, "Con 1", khac, thu_tu=7)
    con2 = await tao_danh_muc(db, "Con 2", khac, thu_tu=9)
    cay = (await dat_vi_tri(dang_nhap_admin, ho.id, khac.id, 1)).json()  # Ho từ Thuốc sang giữa Con 1 và Con 2
    assert thu_tu_con(cay, khac.id) == [con1.id, ho.id, con2.id]
    nut = phang(cay)
    assert [nut[i]["thu_tu"] for i in (con1.id, ho.id, con2.id)] == [0, 1, 2]
    assert thu_tu_con(cay, thuoc.id) == [giam_dau.id] and nut[giam_dau.id]["thu_tu"] == 0
    assert nut[ho.id]["danh_muc_cha_id"] == khac.id and nut[ho.id]["cap"] == 2
    dong = (await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "sua"))[-1]
    assert (dong.bang, dong.ban_ghi_id) == ("danh_muc", str(ho.id))
    assert dong.gia_tri_cu["danh_muc_cha_id"] == thuoc.id and dong.gia_tri_moi["danh_muc_cha_id"] == khac.id


async def test_chuyen_len_goc_va_cap_cua_ca_cay_con_cap_nhat(dang_nhap_admin, db):
    thuoc, giam_dau, para, _ = await tao_cay_ba_cap(db)
    cay = (await dat_vi_tri(dang_nhap_admin, giam_dau.id, None, 0)).json()
    nut = phang(cay)
    assert (nut[giam_dau.id]["cap"], nut[para.id]["cap"]) == (1, 2)
    assert nut[giam_dau.id]["danh_muc_cha_id"] is None and thu_tu_con(cay, giam_dau.id) == [para.id]


async def test_dat_dung_vi_tri_hien_tai_khong_ghi_nhat_ky(dang_nhap_admin, db):
    a = await tao_danh_muc(db, "A", thu_tu=0)
    b = await tao_danh_muc(db, "B", thu_tu=1)
    truoc = len(await nhat_ky(db, dang_nhap_admin.tai_khoan.id))
    assert (await dat_vi_tri(dang_nhap_admin, b.id, None, 1)).status_code == 200
    assert (await dat_vi_tri(dang_nhap_admin, b.id, None, 99)).status_code == 200  # quá cuối bị kẹp về cuối = chỗ cũ
    assert len(await nhat_ky(db, dang_nhap_admin.tai_khoan.id)) == truoc
    # Chỉ số quá lớn mà thực sự đổi chỗ thì nhật ký ghi chỉ số đã kẹp, không phải số client gửi.
    assert (await dat_vi_tri(dang_nhap_admin, a.id, None, 99)).status_code == 200
    ghi = [g for g in await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "sua") if g.ban_ghi_id == str(a.id)]
    assert len(ghi) == 1 and ghi[0].gia_tri_moi["vi_tri"] == 1 and ghi[0].gia_tri_cu["vi_tri"] == 0


async def test_khong_duoc_chuyen_vao_chinh_no_hoac_danh_muc_con_chau(dang_nhap_admin, db):
    thuoc, giam_dau, para, _ = await tao_cay_ba_cap(db)
    for cha in (thuoc.id, giam_dau.id, para.id):
        phan_hoi = await dat_vi_tri(dang_nhap_admin, thuoc.id, cha, 0)
        assert (
            la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE")
            and phan_hoi.json()["chi_tiet"][0]["truong"] == "danh_muc_cha_id"
        ), cha
        # Phải là lỗi "vào chính nó/con của nó", không phải lỗi quá 3 cấp (cả hai cùng đúng nhưng chỉ một nói đúng lý do).
        assert "danh mục con của nó" in phan_hoi.json()["chi_tiet"][0]["loi"], (cha, phan_hoi.json())
    assert la_loi(await dat_vi_tri(dang_nhap_admin, giam_dau.id, giam_dau.id, 0), 400, "DU_LIEU_KHONG_HOP_LE")
    assert la_loi(await dat_vi_tri(dang_nhap_admin, giam_dau.id, para.id, 0), 400, "DU_LIEU_KHONG_HOP_LE")


async def test_chuyen_khong_duoc_lam_vuot_ba_cap_ke_ca_cay_con_mang_theo(dang_nhap_admin, db):
    thuoc, giam_dau, para, ho = await tao_cay_ba_cap(db)
    khac = await tao_danh_muc(db, "Khác")
    con_khac = await tao_danh_muc(db, "Con của Khác", khac)
    # Giảm đau mang theo Paracetamol (cây cao 2): đặt dưới cấp 2 thì Paracetamol thành cấp 4.
    assert la_loi(await dat_vi_tri(dang_nhap_admin, giam_dau.id, con_khac.id, 0), 400, "DU_LIEU_KHONG_HOP_LE")
    assert la_loi(await dat_vi_tri(dang_nhap_admin, giam_dau.id, para.id, 0), 400, "DU_LIEU_KHONG_HOP_LE")
    # Thuốc (cây cao 3) không đặt được dưới bất kỳ danh mục nào.
    assert la_loi(await dat_vi_tri(dang_nhap_admin, thuoc.id, khac.id, 0), 400, "DU_LIEU_KHONG_HOP_LE")
    # Đặt Giảm đau dưới cấp 1 thì Paracetamol xuống cấp 3: được.
    assert (await dat_vi_tri(dang_nhap_admin, giam_dau.id, khac.id, 0)).status_code == 200
    # Lá cấp 3 đặt dưới cấp 2 vẫn cấp 3: được.
    assert (await dat_vi_tri(dang_nhap_admin, para.id, con_khac.id, 0)).status_code == 200


async def test_chuyen_trung_ten_anh_em_o_cha_moi_la_409_va_cha_khong_ton_tai_la_400(dang_nhap_admin, db):
    thuoc, giam_dau, _, ho = await tao_cay_ba_cap(db)
    khac = await tao_danh_muc(db, "Khác")
    await tao_danh_muc(db, "Ho", khac)  # đã có "Ho" dưới Khác
    assert la_loi(await dat_vi_tri(dang_nhap_admin, ho.id, khac.id, 0), 409, "TRUNG_DU_LIEU")
    assert la_loi(await dat_vi_tri(dang_nhap_admin, ho.id, 2_000_000_000, 0), 400, "DU_LIEU_KHONG_HOP_LE")
    for sai in (
        {"danh_muc_cha_id": None, "vi_tri": -1},
        {"danh_muc_cha_id": None},
        {"vi_tri": 0},
        {"danh_muc_cha_id": None, "vi_tri": 1.5},
    ):
        assert la_loi(await dang_nhap_admin.put(f"{GOC}/{ho.id}/vi-tri", json=sai), 400, "DU_LIEU_KHONG_HOP_LE"), sai


# --- Xóa mềm -------------------------------------------------------------------------------------------------------------


async def test_xoa_mem_la_danh_muc_khong_co_san_pham_giu_slug_va_ghi_nhat_ky(dang_nhap_admin, db):
    dm = (await tao(dang_nhap_admin, "Thuốc ho")).json()
    phan_hoi = await dang_nhap_admin.delete(f"{GOC}/{dm['id']}")
    assert phan_hoi.status_code == 204 and phan_hoi.content == b""
    assert dm["id"] not in phang(await doc_cay(dang_nhap_admin))
    luu = await db.get(DanhMuc, dm["id"])
    await db.refresh(luu)
    assert luu.deleted_at is not None and luu.slug == "thuoc-ho"  # còn trong bảng, giữ chỗ slug
    assert (await tao(dang_nhap_admin, "Thuốc ho")).json()["slug"] == "thuoc-ho-2"
    dong = (await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "xoa"))[-1]
    assert (dong.bang, dong.ban_ghi_id) == ("danh_muc", str(dm["id"]))


async def test_con_san_pham_chua_xoa_thi_khong_xoa_duoc_san_pham_da_xoa_thi_khong_chan(dang_nhap_admin, db):
    dm = await tao_danh_muc(db, "Có hàng")
    sp = await tao_san_pham(db, danh_muc_id=dm.id)
    phan_hoi = await dang_nhap_admin.delete(f"{GOC}/{dm.id}")
    assert la_loi(phan_hoi, 409, "DANH_MUC_CON_SAN_PHAM")
    await db.refresh(dm)
    assert dm.deleted_at is None and await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "xoa") == []
    sp.deleted_at = bay_gio_utc()
    await db.flush()
    assert (await dang_nhap_admin.delete(f"{GOC}/{dm.id}")).status_code == 204


async def test_con_danh_muc_con_chua_xoa_thi_khong_xoa_duoc_xoa_tu_la_len(dang_nhap_admin, db):
    thuoc, giam_dau, para, ho = await tao_cay_ba_cap(db)
    for cha in (thuoc, giam_dau):
        assert la_loi(await dang_nhap_admin.delete(f"{GOC}/{cha.id}"), 409, "DANH_MUC_CON_DANH_MUC")
    for id_ in (para.id, giam_dau.id, ho.id, thuoc.id):  # từ lá lên
        assert (await dang_nhap_admin.delete(f"{GOC}/{id_}")).status_code == 204, id_
    assert await doc_cay(dang_nhap_admin) == []


async def test_xoa_danh_muc_chi_con_danh_muc_con_da_xoa_van_xoa_duoc(dang_nhap_admin, db):
    thuoc = await tao_danh_muc(db, "Thuốc")
    await tao_danh_muc(db, "Con đã xóa", thuoc, deleted_at=bay_gio_utc())
    assert (await dang_nhap_admin.delete(f"{GOC}/{thuoc.id}")).status_code == 204


# --- Phân quyền --------------------------------------------------------------------------------------------------------------


async def test_chi_admin_dung_duoc_va_token_khach_bi_tu_choi(clients_theo_vai_tro, dang_nhap_khach, client, db):
    dm = await tao_danh_muc(db, "A")
    cac_goi = [
        ("get", GOC, None),
        ("post", GOC, {"ten": "X"}),
        ("patch", f"{GOC}/{dm.id}", {"ten": "Y"}),
        ("put", f"{GOC}/{dm.id}/vi-tri", {"danh_muc_cha_id": None, "vi_tri": 0}),
        ("delete", f"{GOC}/{dm.id}", None),
    ]
    for vai_tro in ("PHARMACIST", "WAREHOUSE"):
        c = clients_theo_vai_tro[vai_tro]
        for phuong_thuc, duong, than in cac_goi:
            phan_hoi = await getattr(c, phuong_thuc)(duong, **({"json": than} if than is not None else {}))
            assert la_loi(phan_hoi, 403, "KHONG_CO_QUYEN"), (vai_tro, phuong_thuc, duong)
    assert (await client.get(GOC)).status_code == 401 and (await dang_nhap_khach.get(GOC)).status_code == 401
    await db.refresh(dm)
    assert dm.ten == "A" and dm.deleted_at is None


async def test_category_manage_cap_ngoai_ad18_van_khong_cho_phep_ghi(clients_theo_vai_tro, db):
    """Lớp phòng thủ thứ hai (QĐ-13): dược sĩ giữ `category.manage` do cấu hình sai vẫn không sửa được cây danh mục."""
    duoc_si = clients_theo_vai_tro["PHARMACIST"]
    quyen_id = (await db.execute(select(Quyen.id).where(Quyen.ma == "category.manage"))).scalar_one()
    vai_tro_id = (await db.execute(select(VaiTro.id).where(VaiTro.ma == "PHARMACIST"))).scalar_one()
    db.add(VaiTroQuyen(vai_tro_id=vai_tro_id, quyen_id=quyen_id, gioi_han=None))
    await db.flush()
    phan_quyen.xoa_cache_quyen()
    dm = await tao_danh_muc(db, "A")
    so_nhat_ky = (await db.execute(select(func.count()).select_from(NhatKyHeThong))).scalar_one()
    assert (await duoc_si.get(GOC)).status_code == 200  # đọc đi qua guard theo mã quyền
    for phuong_thuc, duong, than in (
        ("post", GOC, {"ten": "X"}),
        ("patch", f"{GOC}/{dm.id}", {"ten": "Y"}),
        ("put", f"{GOC}/{dm.id}/vi-tri", {"danh_muc_cha_id": None, "vi_tri": 0}),
        ("delete", f"{GOC}/{dm.id}", None),
    ):
        phan_hoi = await getattr(duoc_si, phuong_thuc)(duong, **({"json": than} if than is not None else {}))
        assert la_loi(phan_hoi, 403, "KHONG_CO_QUYEN"), phuong_thuc
    await db.refresh(dm)
    assert dm.ten == "A" and dm.deleted_at is None
    assert (await db.execute(select(func.count()).select_from(NhatKyHeThong))).scalar_one() == so_nhat_ky


# --- Đồng thời ---------------------------------------------------------------------------------------------------------------


async def test_hai_admin_chuyen_hai_danh_muc_vao_nhau_cung_luc_khong_bao_gio_tao_vong(db_that):
    async with db_that() as s, s.begin():
        admin_id = (await tao_nhan_vien(s, "ADMIN")).id
        a = (await tao_danh_muc(s, "A")).id
        b = (await tao_danh_muc(s, "B")).id

    async def chuyen(id_, vao):
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, admin_id)
            await dich_vu.dat_vi_tri(s, actor, id_, vao, 0, ip="127.0.0.1")
            await asyncio.sleep(0.3)  # giữ giao dịch mở để bên kia phải chờ khóa cây

    ket_qua = await asyncio.wait_for(asyncio.gather(chuyen(a, b), chuyen(b, a), return_exceptions=True), timeout=20)
    thanh_cong = [k for k in ket_qua if k is None]
    that_bai = [k for k in ket_qua if k is not None]
    assert len(thanh_cong) == 1 and len(that_bai) == 1, ket_qua
    assert isinstance(that_bai[0], LoiNghiepVu) and that_bai[0].ma_loi == "DU_LIEU_KHONG_HOP_LE"
    async with db_that() as s:
        cha = {d.id: d.danh_muc_cha_id for d in (await s.execute(select(DanhMuc))).scalars()}
    assert sorted(v is None for v in cha.values()) == [False, True]  # đúng một gốc, không có vòng


async def test_xoa_danh_muc_cho_giao_dich_dang_them_san_pham_vao_no_roi_thay_san_pham_va_tu_choi(db_that):
    """Tạo sản phẩm giữ khóa FK trên dòng danh mục: xóa (khóa dòng `FOR UPDATE` trước khi đếm) phải chờ rồi thấy sản phẩm."""
    async with db_that() as s, s.begin():
        admin_id = (await tao_nhan_vien(s, "ADMIN")).id
        dm_id = (await tao_danh_muc(s, "Sắp có hàng")).id
    dang_them = asyncio.Event()

    async def them_san_pham():
        async with db_that() as s, s.begin():
            await tao_san_pham(s, danh_muc_id=dm_id)
            dang_them.set()
            await asyncio.sleep(0.4)  # chưa commit

    async def xoa():
        await dang_them.wait()
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, admin_id)
            await dich_vu.xoa(s, actor, dm_id, ip="127.0.0.1")

    ket_qua = await asyncio.wait_for(asyncio.gather(them_san_pham(), xoa(), return_exceptions=True), timeout=20)
    assert ket_qua[0] is None
    assert isinstance(ket_qua[1], LoiNghiepVu) and ket_qua[1].ma_loi == "DANH_MUC_CON_SAN_PHAM", ket_qua
    async with db_that() as s:
        assert (await s.get(DanhMuc, dm_id)).deleted_at is None


async def test_hai_admin_tao_cung_ten_cung_cha_cung_luc_chi_mot_ben_thanh_cong(db_that):
    async with db_that() as s, s.begin():
        admin_id = (await tao_nhan_vien(s, "ADMIN")).id

    async def tao_moi():
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, admin_id)
            await dich_vu.tao(s, actor, dich_vu.DanhMucTao(ten="Trùng tên"), ip="127.0.0.1")
            await asyncio.sleep(0.3)

    ket_qua = await asyncio.wait_for(asyncio.gather(tao_moi(), tao_moi(), return_exceptions=True), timeout=20)
    loi = [k for k in ket_qua if k is not None]
    assert len(loi) == 1 and isinstance(loi[0], LoiNghiepVu) and loi[0].ma_loi == "TRUNG_DU_LIEU", ket_qua
    async with db_that() as s:
        assert (await s.execute(select(func.count()).select_from(DanhMuc))).scalar_one() == 1

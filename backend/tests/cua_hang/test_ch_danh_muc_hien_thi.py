"""KVL01: cây danh mục, banner và quy tắc "hiển thị với khách" (QĐ-16: ẩn danh mục là ẩn cả cây con và sản phẩm)."""

from datetime import timedelta

from app.core.thoi_gian import bay_gio_utc
from app.models.enums import TrangThaiKinhDoanh
from tests.cua_hang.mau_cua_hang import GOC, sp_ban_duoc, tao_banner, ten_the
from tests.factories import tao_danh_muc

# --- Cây danh mục ----------------------------------------------------------------------------------------------------


async def test_cay_danh_muc_bo_nhanh_an_va_nhanh_da_xoa_sap_xep_theo_thu_tu(client, db):
    goc = await tao_danh_muc(db, "Thuốc", thu_tu=2)
    con = await tao_danh_muc(db, "Giảm đau", cha=goc, thu_tu=1)
    chau = await tao_danh_muc(db, "Hạ sốt", cha=con)
    an = await tao_danh_muc(db, "Ẩn", thu_tu=1, dang_hien_thi=False)
    await tao_danh_muc(db, "Con của ẩn", cha=an)
    await tao_danh_muc(db, "Đã xóa", thu_tu=3, deleted_at=bay_gio_utc())
    khac = await tao_danh_muc(db, "Chăm sóc", thu_tu=0)
    phan_hoi = await client.get(f"{GOC}/danh-muc")
    assert phan_hoi.status_code == 200, phan_hoi.text
    cay = phan_hoi.json()
    assert [d["ten"] for d in cay] == ["Chăm sóc", "Thuốc"]  # đúng theo thu_tu, không có nhánh ẩn hay đã xóa
    assert cay[0]["id"] == khac.id and cay[0]["con"] == []
    thuoc = cay[1]
    assert [c["ten"] for c in thuoc["con"]] == ["Giảm đau"]
    assert thuoc["con"][0]["con"][0]["id"] == chau.id
    assert set(thuoc) == {"id", "ten", "slug", "anh_url", "con"}


async def test_danh_muc_con_cua_cha_da_xoa_hoac_an_giua_chung_khong_hien(client, db):
    goc = await tao_danh_muc(db, "Gốc")
    giua = await tao_danh_muc(db, "Giữa", cha=goc)
    la = await tao_danh_muc(db, "Lá", cha=giua)
    giua.dang_hien_thi = False
    await db.flush()
    cay = (await client.get(f"{GOC}/danh-muc")).json()
    assert [d["ten"] for d in cay] == ["Gốc"] and cay[0]["con"] == []
    assert (await client.get(f"{GOC}/danh-muc/{la.slug}")).status_code == 404  # lá vẫn bật nhưng tổ tiên ẩn
    giua.dang_hien_thi, giua.deleted_at = True, bay_gio_utc()
    await db.flush()
    assert (await client.get(f"{GOC}/danh-muc/{la.slug}")).status_code == 404  # tổ tiên đã xóa


async def test_chi_tiet_danh_muc_co_duong_dan_tu_goc_va_danh_muc_con(client, db):
    goc = await tao_danh_muc(db, "Thuốc")
    con = await tao_danh_muc(db, "Giảm đau", cha=goc)
    chau = await tao_danh_muc(db, "Hạ sốt", cha=con)
    phan_hoi = await client.get(f"{GOC}/danh-muc/{con.slug}")
    assert phan_hoi.status_code == 200
    d = phan_hoi.json()
    assert d["ten"] == "Giảm đau"
    assert d["duong_dan"] == [{"ten": "Thuốc", "slug": goc.slug}, {"ten": "Giảm đau", "slug": con.slug}]
    assert [c["id"] for c in d["con"]] == [chau.id]


async def test_slug_danh_muc_sai_dinh_dang_la_400_khong_co_la_404(client, db):
    assert (await client.get(f"{GOC}/danh-muc/khong-co-danh-muc-nay")).status_code == 404
    assert (await client.get(f"{GOC}/danh-muc/Sai_Dinh_Dang")).status_code == 400
    assert (await client.get(f"{GOC}/san-pham", params={"danh_muc": "SAI SLUG"})).status_code == 400


# --- Sản phẩm trong nhánh ẩn -----------------------------------------------------------------------------------------


async def test_san_pham_trong_danh_muc_an_hoac_tong_tien_an_khong_xuat_hien_o_dau_ca(client, db):
    goc = await tao_danh_muc(db, "Gốc")
    con = await tao_danh_muc(db, "Con", cha=goc)
    ban = await sp_ban_duoc(db, "Hiện", danh_muc_id=con.id, la_noi_bat=True)
    assert "Hiện" in ten_the(await client.get(f"{GOC}/san-pham"))

    goc.dang_hien_thi = False  # ẩn tổ tiên: sản phẩm ở danh mục con vẫn bật cũng phải biến mất
    await db.flush()
    assert ten_the(await client.get(f"{GOC}/san-pham")) == []
    assert (await client.get(f"{GOC}/san-pham/{ban.slug}")).status_code == 404
    assert (await client.get(f"{GOC}/trang-chu")).json()["noi_bat"] == []
    assert (await client.get(f"{GOC}/san-pham", params={"danh_muc": con.slug})).status_code == 404
    bo_loc = (await client.get(f"{GOC}/bo-loc-san-pham")).json()
    assert bo_loc["thuong_hieu"] == [] and bo_loc["gia_thap_nhat"] is None

    goc.dang_hien_thi = True
    await db.flush()
    assert ten_the(await client.get(f"{GOC}/san-pham")) == ["Hiện"]  # bật lại thì hiện lại, không mất gì


async def test_san_pham_da_xoa_hoac_ngung_kinh_doanh_khong_hien(client, db):
    sp_ban = await sp_ban_duoc(db, "Đang bán")
    ngung = await sp_ban_duoc(db, "Ngừng", trang_thai=TrangThaiKinhDoanh.ngung_kinh_doanh)
    xoa = await sp_ban_duoc(db, "Đã xóa", ton=0, deleted_at=bay_gio_utc())
    assert ten_the(await client.get(f"{GOC}/san-pham")) == ["Đang bán"]
    for sp in (ngung, xoa):
        assert (await client.get(f"{GOC}/san-pham/{sp.slug}")).status_code == 404
    assert (await client.get(f"{GOC}/san-pham/{sp_ban.slug}")).status_code == 200


# --- Banner ------------------------------------------------------------------------------------------------------------


async def test_banner_chi_lay_banner_dang_hien_trong_khoang_hieu_luc_theo_thu_tu(client, db):
    bay_gio = bay_gio_utc()
    hai = await tao_banner(db, tieu_de="Hai", thu_tu=2)
    mot = await tao_banner(
        db, tieu_de="Một", thu_tu=1, bat_dau=bay_gio - timedelta(days=1), ket_thuc=bay_gio + timedelta(days=1)
    )
    await tao_banner(db, tieu_de="Tắt", dang_hien=False)
    await tao_banner(db, tieu_de="Chưa tới", bat_dau=bay_gio + timedelta(hours=1))
    await tao_banner(db, tieu_de="Hết hạn", ket_thuc=bay_gio - timedelta(seconds=1))
    phu = await tao_banner(db, "trang_chu_phu", tieu_de="Phụ", thu_tu=3)
    tat_ca = (await client.get(f"{GOC}/banner")).json()
    assert [b["tieu_de"] for b in tat_ca] == ["Một", "Hai", "Phụ"]
    assert set(tat_ca[0]) == {"id", "tieu_de", "anh_url", "lien_ket", "vi_tri"}
    chinh = (await client.get(f"{GOC}/banner", params={"vi_tri": "trang_chu_chinh"})).json()
    assert [b["id"] for b in chinh] == [mot.id, hai.id]
    trang_chu = (await client.get(f"{GOC}/trang-chu")).json()
    assert [b["id"] for b in trang_chu["banner_chinh"]] == [mot.id, hai.id]
    assert [b["id"] for b in trang_chu["banner_phu"]] == [phu.id]
    assert (await client.get(f"{GOC}/banner", params={"vi_tri": "Sai Chuoi"})).status_code == 400

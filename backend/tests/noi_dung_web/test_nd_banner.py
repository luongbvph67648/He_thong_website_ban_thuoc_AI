"""AD07: quản lý banner (/api/v1/noi-bo/banner) và banner công khai."""

from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.core.thoi_gian import bay_gio_utc
from app.models.he_thong import Banner
from tests.nhan_vien.dung_chung import nhat_ky
from tests.noi_dung_web.mau_noi_dung_web import GOC_BANNER, la_loi, tao_banner, than_banner

# --- Tạo ---------------------------------------------------------------------------------------------------------------


async def test_tao_banner_tra_201_day_du_tinh_trang_va_ghi_nhat_ky(dang_nhap_admin, db):
    admin = dang_nhap_admin
    b = await tao_banner(admin, tieu_de="  Giảm   giá  ", lien_ket="/danh-muc/thuoc", thu_tu=3)
    assert b["tieu_de"] == "Giảm giá" and b["lien_ket"] == "/danh-muc/thuoc" and b["thu_tu"] == 3
    assert b["dang_hien"] is True and b["tinh_trang"] == "dang_hien" and b["vi_tri"] == "trang_chu_chinh"
    assert len(b["phien_ban"]) == 16
    ghi = await nhat_ky(db, admin.tai_khoan.id, "tao")
    assert len(ghi) == 1 and ghi[0].bang == "banner" and ghi[0].gia_tri_moi["anh_url"] == b["anh_url"]


async def test_tinh_trang_theo_thoi_gian_va_cong_tat(clients_theo_vai_tro, db):
    admin = clients_theo_vai_tro["ADMIN"]
    bg = bay_gio_utc()
    chua = await tao_banner(admin, bat_dau=(bg + timedelta(days=1)).isoformat())
    het = await tao_banner(
        admin, ket_thuc=(bg - timedelta(days=1)).isoformat(), bat_dau=(bg - timedelta(days=3)).isoformat()
    )
    tat = await tao_banner(admin, dang_hien=False)
    trong = await tao_banner(
        admin, bat_dau=(bg - timedelta(days=1)).isoformat(), ket_thuc=(bg + timedelta(days=1)).isoformat()
    )
    ds = {b["id"]: b["tinh_trang"] for b in (await admin.get(GOC_BANNER)).json()}
    assert ds == {
        chua["id"]: "chua_den_gio",
        het["id"]: "het_han",
        tat["id"]: "da_tat",
        trong["id"]: "dang_hien",
    }


@pytest.mark.parametrize(
    ("ten_ca", "ghi_de"),
    [
        ("thiếu ảnh", {"anh_url": None}),
        ("ảnh nguy hiểm", {"anh_url": "javascript:alert(1)"}),
        ("liên kết giao thức tương đối", {"lien_ket": "//evil.example"}),
        ("liên kết data", {"lien_ket": "data:text/html,x"}),
        ("vị trí lạ", {"vi_tri": "footer"}),
        ("thứ tự âm", {"thu_tu": -1}),
        ("thứ tự quá lớn", {"thu_tu": 10_000}),
        ("thứ tự chuỗi", {"thu_tu": "1"}),
        ("giờ không múi giờ", {"bat_dau": "2026-01-01T00:00:00"}),
        ("kết thúc trước bắt đầu", {"bat_dau": "2026-02-01T00:00:00+00:00", "ket_thuc": "2026-01-01T00:00:00+00:00"}),
        ("kết thúc bằng bắt đầu", {"bat_dau": "2026-02-01T00:00:00+00:00", "ket_thuc": "2026-02-01T00:00:00+00:00"}),
        ("tiêu đề quá dài", {"tieu_de": "x" * 201}),
        ("ký tự điều khiển", {"tieu_de": "a\u0000b"}),
        ("trường lạ", {"id": 5}),
        ("dang_hien không phải bool", {"dang_hien": "có"}),
    ],
)
async def test_banner_sai_la_400_va_khong_tao_gi(clients_theo_vai_tro, db, ten_ca, ghi_de):
    phan_hoi = await clients_theo_vai_tro["ADMIN"].post(GOC_BANNER, json=than_banner(**ghi_de))
    assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE"), (ten_ca, phan_hoi.text)
    assert (await db.scalar(select(func.count()).select_from(Banner))) == 0


# --- Sửa, xóa ----------------------------------------------------------------------------------------------------------


async def test_sua_tung_phan_xoa_gia_tri_bang_null_va_chi_ghi_truong_doi(dang_nhap_admin, db):
    admin = dang_nhap_admin
    b = await tao_banner(admin, lien_ket="/a", bat_dau="2026-01-01T00:00:00+00:00")
    phan_hoi = await admin.patch(
        f"{GOC_BANNER}/{b['id']}",
        json={"phien_ban": b["phien_ban"], "tieu_de": None, "lien_ket": None, "bat_dau": None, "thu_tu": 7},
    )
    assert phan_hoi.status_code == 200, phan_hoi.text
    moi = phan_hoi.json()
    assert (moi["tieu_de"], moi["lien_ket"], moi["bat_dau"], moi["thu_tu"]) == (None, None, None, 7)
    assert moi["anh_url"] == b["anh_url"] and moi["phien_ban"] != b["phien_ban"]
    ghi = await nhat_ky(db, admin.tai_khoan.id, "sua")
    assert len(ghi) == 1 and set(ghi[0].gia_tri_moi) == {"tieu_de", "lien_ket", "bat_dau", "thu_tu"}
    assert ghi[0].gia_tri_cu["thu_tu"] == 0 and "anh_url" not in ghi[0].gia_tri_moi


async def test_sua_khong_thay_doi_gi_khong_ghi_nhat_ky(dang_nhap_admin, db):
    admin = dang_nhap_admin
    b = await tao_banner(admin)
    phan_hoi = await admin.patch(f"{GOC_BANNER}/{b['id']}", json={"phien_ban": b["phien_ban"], "thu_tu": 0})
    assert phan_hoi.status_code == 200 and phan_hoi.json()["phien_ban"] == b["phien_ban"]
    assert await nhat_ky(db, admin.tai_khoan.id, "sua") == []


@pytest.mark.parametrize(
    "ghi_de", [{"anh_url": None}, {"vi_tri": None}, {"thu_tu": None}, {"dang_hien": None}, {"vi_tri": "x"}]
)
async def test_sua_truong_bat_buoc_thanh_null_hoac_sai_la_400(clients_theo_vai_tro, db, ghi_de):
    admin = clients_theo_vai_tro["ADMIN"]
    b = await tao_banner(admin)
    phan_hoi = await admin.patch(f"{GOC_BANNER}/{b['id']}", json={"phien_ban": b["phien_ban"], **ghi_de})
    assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE")


async def test_sua_ket_thuc_truoc_bat_dau_da_co_la_400_va_khong_luu(clients_theo_vai_tro, db):
    admin = clients_theo_vai_tro["ADMIN"]
    b = await tao_banner(admin, bat_dau="2026-05-01T00:00:00+00:00")
    phan_hoi = await admin.patch(
        f"{GOC_BANNER}/{b['id']}", json={"phien_ban": b["phien_ban"], "ket_thuc": "2026-04-01T00:00:00+00:00"}
    )
    assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE")
    assert (await admin.get(GOC_BANNER)).json()[0]["ket_thuc"] is None


async def test_phien_ban_cu_la_409_kem_phien_ban_hien_tai_va_khong_ghi_de(clients_theo_vai_tro, db):
    admin = clients_theo_vai_tro["ADMIN"]
    b = await tao_banner(admin)
    assert (
        await admin.patch(f"{GOC_BANNER}/{b['id']}", json={"phien_ban": b["phien_ban"], "thu_tu": 5})
    ).status_code == 200
    cu = await admin.patch(f"{GOC_BANNER}/{b['id']}", json={"phien_ban": b["phien_ban"], "tieu_de": "Ghi đè"})
    assert la_loi(cu, 409, "DU_LIEU_DA_THAY_DOI")
    assert cu.json()["chi_tiet"]["phien_ban_hien_tai"] != b["phien_ban"]
    assert (await admin.get(GOC_BANNER)).json()[0]["tieu_de"] == "Khuyến mãi"
    xoa = await admin.delete(f"{GOC_BANNER}/{b['id']}", params={"phien_ban": b["phien_ban"]})
    assert la_loi(xoa, 409, "DU_LIEU_DA_THAY_DOI")


async def test_xoa_banner_xoa_han_ghi_nhat_ky_gia_tri_cu(dang_nhap_admin, db):
    admin = dang_nhap_admin
    b = await tao_banner(admin)
    phan_hoi = await admin.delete(f"{GOC_BANNER}/{b['id']}", params={"phien_ban": b["phien_ban"]})
    assert phan_hoi.status_code == 204
    assert (await admin.get(GOC_BANNER)).json() == []
    ghi = await nhat_ky(db, admin.tai_khoan.id, "xoa")
    assert len(ghi) == 1 and ghi[0].gia_tri_cu["anh_url"] == b["anh_url"]
    assert la_loi(
        await admin.delete(f"{GOC_BANNER}/{b['id']}", params={"phien_ban": b["phien_ban"]}), 404, "KHONG_TIM_THAY"
    )


async def test_phien_ban_sai_dinh_dang_la_400_id_la_404(clients_theo_vai_tro, db):
    admin = clients_theo_vai_tro["ADMIN"]
    b = await tao_banner(admin)
    assert la_loi(
        await admin.delete(f"{GOC_BANNER}/{b['id']}", params={"phien_ban": "xyz"}), 400, "DU_LIEU_KHONG_HOP_LE"
    )
    assert la_loi(await admin.delete(f"{GOC_BANNER}/{b['id']}"), 400, "DU_LIEU_KHONG_HOP_LE")
    moi = await admin.patch(f"{GOC_BANNER}/2000000000", json={"phien_ban": "0" * 16, "thu_tu": 1})
    assert la_loi(moi, 404, "KHONG_TIM_THAY")
    assert la_loi(
        await admin.patch(f"{GOC_BANNER}/2147483648", json={"phien_ban": "0" * 16}), 400, "DU_LIEU_KHONG_HOP_LE"
    )


# --- Quyền -------------------------------------------------------------------------------------------------------------


async def test_chi_admin_vao_quan_ly_banner_duoc_si_kho_va_khach_deu_bi_chan(
    clients_theo_vai_tro, dang_nhap_khach, client, db
):
    admin = clients_theo_vai_tro["ADMIN"]
    b = await tao_banner(admin)
    for vai_tro in ("PHARMACIST", "WAREHOUSE"):
        c = clients_theo_vai_tro[vai_tro]
        assert la_loi(await c.get(GOC_BANNER), 403, "KHONG_CO_QUYEN"), vai_tro
        assert la_loi(await c.post(GOC_BANNER, json=than_banner()), 403, "KHONG_CO_QUYEN"), vai_tro
        phan_hoi = await c.patch(f"{GOC_BANNER}/{b['id']}", json={"phien_ban": b["phien_ban"], "thu_tu": 9})
        assert la_loi(phan_hoi, 403, "KHONG_CO_QUYEN"), vai_tro
        assert la_loi(
            await c.delete(f"{GOC_BANNER}/{b['id']}", params={"phien_ban": b["phien_ban"]}), 403, "KHONG_CO_QUYEN"
        )
    assert (await dang_nhap_khach.get(GOC_BANNER)).status_code == 401  # token khách không phải token nội bộ
    assert (await client.get(GOC_BANNER)).status_code == 401
    assert (await admin.get(GOC_BANNER)).json()[0]["thu_tu"] == 0  # không ai đổi được


async def test_service_tu_choi_nguoi_thuc_hien_khong_phai_admin_du_co_di_qua_route(db):
    """Lớp thứ hai (`dam_bao_la_admin`) nằm trong service, không chỉ ở mã quyền của route."""
    from app.core.loi import LoiNghiepVu
    from app.modules.noi_dung_web import banner as dich_vu
    from app.modules.noi_dung_web.schemas import BannerVao
    from tests.factories import tao_nhan_vien

    duoc_si = await tao_nhan_vien(db, "PHARMACIST")
    with pytest.raises(LoiNghiepVu) as loi:
        await dich_vu.tao(db, duoc_si, BannerVao(**than_banner()), ip="127.0.0.1")
    assert loi.value.ma_loi == "KHONG_CO_QUYEN"
    assert (await db.scalar(select(func.count()).select_from(Banner))) == 0


# --- Công khai ---------------------------------------------------------------------------------------------------------


async def test_banner_moi_hien_o_trang_chu_cong_khai_va_tat_di_thi_het_hien(clients_theo_vai_tro, client, db):
    admin = clients_theo_vai_tro["ADMIN"]
    b = await tao_banner(admin, tieu_de="Hè rực rỡ", lien_ket="/danh-muc/thuoc")
    assert [x["tieu_de"] for x in (await client.get("/api/v1/trang-chu")).json()["banner_chinh"]] == ["Hè rực rỡ"]
    assert (
        await admin.patch(f"{GOC_BANNER}/{b['id']}", json={"phien_ban": b["phien_ban"], "dang_hien": False})
    ).status_code == 200
    assert (await client.get("/api/v1/trang-chu")).json()["banner_chinh"] == []

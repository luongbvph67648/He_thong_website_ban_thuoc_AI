"""AD15: Admin tra cứu nhật ký hệ thống (/api/v1/noi-bo/nhat-ky), kèm việc không để lộ dữ liệu sức khỏe qua nhật ký."""

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.core.nhat_ky import DA_CHE, che_du_lieu_nhay_cam, ghi_nhat_ky
from app.models.he_thong import NhatKyHeThong
from tests.factories import tao_nhan_vien

GOC = "/api/v1/noi-bo/nhat-ky"


def la_loi(phan_hoi, status, ma_loi):
    return phan_hoi.status_code == status and phan_hoi.json()["ma_loi"] == ma_loi


async def them(db, *, luc: datetime | None = None, **truong) -> NhatKyHeThong:
    """Chèn thẳng một dòng nhật ký (kể cả dòng "cũ" có giá trị mà `ghi_nhat_ky` hiện nay sẽ không cho ghi)."""
    dong = NhatKyHeThong(**{"hanh_dong": "sua", "bang": "san_pham", **truong})
    if luc is not None:
        dong.created_at = luc
    db.add(dong)
    await db.flush()
    return dong


def utc(nam, thang, ngay, gio=0, phut=0, giay=0):
    return datetime(nam, thang, ngay, gio, phut, giay, tzinfo=UTC)


async def ids(admin, **tham_so) -> list[int]:
    phan_hoi = await admin.get(GOC, params=tham_so)
    assert phan_hoi.status_code == 200, phan_hoi.text
    return [d["id"] for d in phan_hoi.json()["du_lieu"]]


# --- Đọc và lọc ----------------------------------------------------------------------------------------------------------


async def test_danh_sach_moi_nhat_truoc_kem_nguoi_thuc_hien_khong_lo_email(dang_nhap_admin, db):
    nv = await tao_nhan_vien(db, "WAREHOUSE", ho_ten="Trần Văn Kho", email="kho.bi.mat@example.com")
    cu = await them(
        db,
        nhan_vien_id=nv.id,
        bang="lo_thuoc",
        ban_ghi_id="7",
        gia_tri_cu={"gia": "1"},
        gia_tri_moi={"gia": "2"},
        ip="10.0.0.9",
        luc=utc(2026, 10, 1),
    )
    moi = await them(db, nhan_vien_id=None, hanh_dong="dang_nhap_that_bai", bang="nhan_vien", luc=utc(2026, 10, 2))
    phan_hoi = await dang_nhap_admin.get(GOC)
    assert phan_hoi.status_code == 200
    than = phan_hoi.json()
    assert set(than) == {"du_lieu", "tong", "trang", "kich_thuoc"}
    assert [d["id"] for d in than["du_lieu"]][:2] == [moi.id, cu.id]
    dong_moi, dong_cu = than["du_lieu"][:2]
    assert dong_moi["nhan_vien"] is None  # hệ thống hoặc người chưa xác định
    assert dong_cu["nhan_vien"] == {"id": nv.id, "ma_nhan_vien": nv.ma_nhan_vien, "ho_ten": "Trần Văn Kho"}
    assert (dong_cu["bang"], dong_cu["ban_ghi_id"], dong_cu["ip"]) == ("lo_thuoc", "7", "10.0.0.9")
    assert (dong_cu["gia_tri_cu"], dong_cu["gia_tri_moi"]) == ({"gia": "1"}, {"gia": "2"})
    assert set(dong_cu) == {
        "id",
        "created_at",
        "nhan_vien",
        "hanh_dong",
        "bang",
        "ban_ghi_id",
        "gia_tri_cu",
        "gia_tri_moi",
        "ip",
    }
    assert "kho.bi.mat@example.com" not in json.dumps(than)


async def test_loc_theo_bang_ban_ghi_nhan_vien_hanh_dong_va_ket_hop_bang_and(dang_nhap_admin, db):
    a = await tao_nhan_vien(db, "PHARMACIST")
    b = await tao_nhan_vien(db, "WAREHOUSE")
    d1 = await them(db, nhan_vien_id=a.id, bang="san_pham", ban_ghi_id="1", hanh_dong="sua")
    d2 = await them(db, nhan_vien_id=a.id, bang="san_pham", ban_ghi_id="2", hanh_dong="xoa")
    d3 = await them(db, nhan_vien_id=b.id, bang="lo_thuoc", ban_ghi_id="1", hanh_dong="sua")
    assert set(await ids(dang_nhap_admin, bang="san_pham")) == {d1.id, d2.id}
    assert set(await ids(dang_nhap_admin, ban_ghi_id="1")) == {d1.id, d3.id}
    assert set(await ids(dang_nhap_admin, nhan_vien_id=a.id)) == {d1.id, d2.id}
    assert set(await ids(dang_nhap_admin, hanh_dong="sua")) >= {d1.id, d3.id} and d2.id not in await ids(
        dang_nhap_admin, hanh_dong="sua"
    )
    assert await ids(dang_nhap_admin, bang="san_pham", ban_ghi_id="1", nhan_vien_id=a.id, hanh_dong="sua") == [d1.id]
    assert await ids(dang_nhap_admin, bang="san_pham", nhan_vien_id=b.id) == []
    assert await ids(dang_nhap_admin, bang="SAN_PHAM") == []  # khớp chính xác, phân biệt hoa thường


async def test_loc_khoang_ngay_theo_gio_viet_nam_gom_ca_hai_dau(dang_nhap_admin, db):
    """Ngày 15/10 giờ Việt Nam là [2026-10-14T17:00Z, 2026-10-15T17:00Z)."""
    truoc = await them(db, luc=utc(2026, 10, 14, 16, 59, 59))  # 23:59:59 ngày 14
    dau = await them(db, luc=utc(2026, 10, 14, 17, 0, 0))  # 00:00:00 ngày 15
    cuoi = await them(db, luc=utc(2026, 10, 15, 16, 59, 59))  # 23:59:59 ngày 15
    sau = await them(db, luc=utc(2026, 10, 15, 17, 0, 0))  # 00:00:00 ngày 16
    assert set(await ids(dang_nhap_admin, tu_ngay="2026-10-15", den_ngay="2026-10-15")) == {dau.id, cuoi.id}
    assert set(await ids(dang_nhap_admin, tu_ngay="2026-10-15")) >= {
        dau.id,
        cuoi.id,
        sau.id,
    } and truoc.id not in await ids(dang_nhap_admin, tu_ngay="2026-10-15")
    assert truoc.id in await ids(dang_nhap_admin, den_ngay="2026-10-14") and dau.id not in await ids(
        dang_nhap_admin, den_ngay="2026-10-14"
    )


@pytest.mark.parametrize(
    "tham_so",
    [
        {"tu_ngay": "2026-10-16", "den_ngay": "2026-10-15"},
        {"tu_ngay": "khong-phai-ngay"},
        {"den_ngay": "2026-13-45"},
        {"nhan_vien_id": 0},
        {"nhan_vien_id": 2_147_483_648},
        {"nhan_vien_id": "abc"},
        {"bang": "a" * 61},
        {"tu_ngay": "0001-01-01"},  # theo giờ VN rơi vào năm 0 khi đổi sang UTC: asyncpg từ chối nếu lọt tới DB
        {"den_ngay": "9999-12-31"},  # cộng thêm một ngày sẽ tràn
        {"tu_ngay": "1999-12-31"},
        {"den_ngay": "2101-01-01"},
        {"bang": "a\x00b"},  # byte NUL làm PostgreSQL báo lỗi: phải là 400, không phải 500
        {"ban_ghi_id": "\x00"},
        {"hanh_dong": "tao\x00"},
        {"hanh_dong": "a" * 31},
        {"ban_ghi_id": "a" * 61},
        {"trang": 0},
        {"kich_thuoc": 101},
    ],
)
async def test_tham_so_sai_la_400_khong_phai_500(dang_nhap_admin, tham_so):
    assert la_loi(await dang_nhap_admin.get(GOC, params=tham_so), 400, "DU_LIEU_KHONG_HOP_LE")


@pytest.mark.parametrize(
    "tham_so",
    [{"tu_ngay": "2000-01-01"}, {"den_ngay": "2100-12-31"}, {"tu_ngay": "2000-01-01", "den_ngay": "2100-12-31"}],
)
async def test_hai_dau_cua_mien_ngay_cho_phep_van_chay_binh_thuong(dang_nhap_admin, tham_so):
    assert (await dang_nhap_admin.get(GOC, params=tham_so)).status_code == 200


async def test_phan_trang_on_dinh_voi_dong_cung_thoi_diem(dang_nhap_admin, db):
    luc = utc(2026, 9, 1)
    tao = [await them(db, bang="trang_thu", luc=luc) for _ in range(5)]
    tong = {d.id for d in tao}
    trang1 = (await dang_nhap_admin.get(GOC, params={"bang": "trang_thu", "kich_thuoc": 2, "trang": 1})).json()
    trang2 = (await dang_nhap_admin.get(GOC, params={"bang": "trang_thu", "kich_thuoc": 2, "trang": 2})).json()
    trang3 = (await dang_nhap_admin.get(GOC, params={"bang": "trang_thu", "kich_thuoc": 2, "trang": 3})).json()
    thay = [d["id"] for t in (trang1, trang2, trang3) for d in t["du_lieu"]]
    assert trang1["tong"] == 5 and sorted(thay) == sorted(tong) and len(set(thay)) == 5  # không trùng, không sót
    assert thay == sorted(thay, reverse=True)  # cùng created_at thì id giảm dần


async def test_gia_tri_loc_liet_ke_bang_va_hanh_dong_dang_co(dang_nhap_admin, db):
    await them(db, bang="bang_b", hanh_dong="duyet")
    await them(db, bang="bang_a", hanh_dong="tao")
    await them(db, bang="bang_a", hanh_dong="duyet")
    than = (await dang_nhap_admin.get(f"{GOC}/gia-tri-loc")).json()
    assert set(than) == {"bang", "hanh_dong"}
    assert than["bang"] == sorted(set(than["bang"])) and {"bang_a", "bang_b"} <= set(than["bang"])
    assert than["hanh_dong"] == sorted(set(than["hanh_dong"])) and {"tao", "duyet"} <= set(than["hanh_dong"])


# --- Dữ liệu sức khỏe và bí mật không bao giờ ra khỏi nhật ký ---------------------------------------------------------------


@pytest.mark.parametrize("bang", ["ho_so_suc_khoe", "di_ung"])
async def test_nhat_ky_du_lieu_suc_khoe_khong_tra_gia_tri_ke_ca_dong_cu_co_sot(dang_nhap_admin, db, bang):
    """Spec 03 mục 5.1: chỉ ghi bảng và id bản ghi. Dòng cũ lỡ có giá trị (ghi trước khi có quy tắc) cũng không được hiện."""
    dong = await them(
        db, bang=bang, ban_ghi_id="42", hanh_dong="doc_suc_khoe",
        gia_tri_cu={"benh_nen": "Tiểu đường tuýp hai"}, gia_tri_moi={"ghi_chu": "Sốc phản vệ", "hoat_chat": "Amoxicillin"},
    )  # fmt: skip
    phan_hoi = await dang_nhap_admin.get(GOC, params={"bang": bang})
    (d,) = [x for x in phan_hoi.json()["du_lieu"] if x["id"] == dong.id]
    assert d["gia_tri_cu"] is None and d["gia_tri_moi"] is None and (d["bang"], d["ban_ghi_id"]) == (bang, "42")
    van_ban = phan_hoi.text
    assert not any(t in van_ban for t in ("Tiểu đường", "Sốc phản vệ", "Amoxicillin"))


async def test_khoa_nhay_cam_bi_che_khi_doc_du_dong_cu_co_sot(dang_nhap_admin, db):
    dong = await them(
        db, bang="nhan_vien",
        gia_tri_cu={"mat_khau_hash": "$argon2id$x", "ten": "A", "long_nhau": [{"otp": "123456", "ok": 1}]},
        gia_tri_moi={"dang_mang_thai": True, "nam_sinh": 1990, "thong_tin_nhan_hoan": "STK 0123456789", "token_truy_cap": "abc"},
    )  # fmt: skip
    d = next(x for x in (await dang_nhap_admin.get(GOC)).json()["du_lieu"] if x["id"] == dong.id)
    assert d["gia_tri_cu"] == {"mat_khau_hash": DA_CHE, "ten": "A", "long_nhau": [{"otp": DA_CHE, "ok": 1}]}
    assert d["gia_tri_moi"] == {
        "dang_mang_thai": DA_CHE,
        "nam_sinh": DA_CHE,
        "thong_tin_nhan_hoan": DA_CHE,
        "token_truy_cap": DA_CHE,
    }


@pytest.mark.parametrize("bang", ["ho_so_suc_khoe", "di_ung"])
async def test_ghi_nhat_ky_bo_gia_tri_cua_bang_suc_khoe_ngay_luc_ghi(db, bang):
    dong = await ghi_nhat_ky(
        db,
        nhan_vien_id=None,
        hanh_dong="sua",
        bang=bang,
        ban_ghi_id=5,
        gia_tri_cu={"benh_nen": "x"},
        gia_tri_moi={"ghi_chu": "y"},
    )
    luu = (await db.execute(select(NhatKyHeThong).where(NhatKyHeThong.id == dong.id))).scalar_one()
    assert luu.gia_tri_cu is None and luu.gia_tri_moi is None and (luu.bang, luu.ban_ghi_id) == (bang, "5")


@pytest.mark.parametrize("khoa", ["dang_mang_thai", "dang_cho_con_bu", "nam_sinh", "thong_tin_nhan_hoan", "NAM_SINH"])
def test_them_khoa_suc_khoe_va_hoan_tien_vao_danh_sach_che(khoa):
    assert che_du_lieu_nhay_cam({khoa: "x", "ten": "A"}) == {khoa: DA_CHE, "ten": "A"}


# --- Quyền và chỉ đọc --------------------------------------------------------------------------------------------------------


async def test_chi_admin_xem_duoc_va_khong_co_route_sua_xoa(
    clients_theo_vai_tro, dang_nhap_admin, dang_nhap_khach, client
):
    for vai_tro in ("PHARMACIST", "WAREHOUSE"):
        c = clients_theo_vai_tro[vai_tro]
        assert la_loi(await c.get(GOC), 403, "KHONG_CO_QUYEN")
        assert la_loi(await c.get(f"{GOC}/gia-tri-loc"), 403, "KHONG_CO_QUYEN")
    assert (await client.get(GOC)).status_code == 401 and (await dang_nhap_khach.get(GOC)).status_code == 401
    for phuong_thuc in ("POST", "PUT", "PATCH", "DELETE"):  # nhật ký chỉ INSERT: không có đường sửa hay xóa
        for duong in (GOC, f"{GOC}/1", f"{GOC}/gia-tri-loc"):
            phan_hoi = await dang_nhap_admin.request(
                phuong_thuc, duong, **({"json": {}} if phuong_thuc != "DELETE" else {})
            )
            assert phan_hoi.status_code in (404, 405), (phuong_thuc, duong)


async def test_tra_cuu_duoc_thay_doi_cau_hinh_vua_thuc_hien(dang_nhap_admin, db):
    """Nối AD08 với AD15: sửa cấu hình xong thì tra cứu ra đúng giá trị cũ và mới, đúng người."""
    muc = next(
        m for m in (await dang_nhap_admin.get("/api/v1/noi-bo/cau-hinh")).json() if m["khoa"] == "nguong_can_han_ngay"
    )
    await dang_nhap_admin.put(
        "/api/v1/noi-bo/cau-hinh/nguong_can_han_ngay", json={"gia_tri": 45, "phien_ban": muc["phien_ban"]}
    )
    phan_hoi = await dang_nhap_admin.get(GOC, params={"bang": "cau_hinh", "ban_ghi_id": "nguong_can_han_ngay"})
    (d,) = phan_hoi.json()["du_lieu"]
    assert (d["gia_tri_cu"], d["gia_tri_moi"], d["hanh_dong"]) == (90, 45, "sua")
    assert d["nhan_vien"]["id"] == dang_nhap_admin.tai_khoan.id

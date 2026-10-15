"""T0.5: seed cơ bản (vai trò, quyền, cấu hình, Admin) và dữ liệu mẫu (`--mau`)."""

import json
import re
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
import pytest_asyncio
import yaml
from sqlalchemy import text

from app.core.bao_mat import kiem_tra_mat_khau
from app.core.thoi_gian import bay_gio_utc, hom_nay_vn
from app.seed.co_ban import QUYEN_YAML, TaiKhoanAdmin, seed_co_ban
from app.seed.du_lieu_mau import MAT_KHAU_MAU, seed_mau, trang_thai_lo

SPEC_DATABASE = Path(__file__).resolve().parents[2] / "docs" / "spec" / "02-database.md"
ADMIN = TaiKhoanAdmin(email="admin@example.com", mat_khau="Mat-khau-thu-123")


@pytest_asyncio.fixture
async def db(db_chua_seed):
    """Test seed chạy trên database CHƯA seed (ghi đè fixture `db` mặc định)."""
    return db_chua_seed


async def dem(db, bang: str) -> int:
    return (await db.execute(text(f"SELECT count(*) FROM {bang}"))).scalar_one()  # noqa: S608 - tên bảng từ hằng trong test


async def hang(db, truy_van: str, **tham_so) -> list:
    return list((await db.execute(text(truy_van), tham_so)).all())


# --- Seed cơ bản ----------------------------------------------------------------------------------------------------


def doc_quyen_yaml() -> dict:
    return yaml.safe_load(QUYEN_YAML.read_text(encoding="utf-8"))


async def test_tao_3_vai_tro(db):
    await seed_co_ban(db)
    ma = {r[0] for r in await hang(db, "SELECT ma FROM vai_tro")}
    assert ma == {"PHARMACIST", "WAREHOUSE", "ADMIN"}


async def test_so_dong_vai_tro_quyen_bang_so_cap_trong_yaml(db):
    """Tiêu chí T0.5: số dòng `vai_tro_quyen` sau seed bằng số cặp (vai trò, quyền) trong quyen.yaml."""
    du_lieu = doc_quyen_yaml()
    cap = {(vt, q["ma"]): muc for q in du_lieu["quyen"] for vt, muc in q["vai_tro"].items()}
    assert len(cap) > 50  # đề phòng file rỗng làm test đúng một cách vô nghĩa

    await seed_co_ban(db)

    assert await dem(db, "quyen") == len(du_lieu["quyen"])
    assert await dem(db, "vai_tro_quyen") == len(cap)
    trong_db = {
        (r[0], r[1]): r[2]
        for r in await hang(
            db,
            "SELECT v.ma, q.ma, vq.gioi_han FROM vai_tro_quyen vq "
            "JOIN vai_tro v ON v.id = vq.vai_tro_id JOIN quyen q ON q.id = vq.quyen_id",
        )
    }
    # day_du lưu NULL, chi_xem lưu 'chi_xem' (spec 02 mục 6)
    assert trong_db == {k: (None if muc == "day_du" else "chi_xem") for k, muc in cap.items()}


async def test_quyen_luu_nhom_va_mo_ta(db):
    await seed_co_ban(db)
    (nhom, mo_ta) = (await hang(db, "SELECT nhom, mo_ta FROM quyen WHERE ma = 'order.confirm'"))[0]
    assert nhom == "order" and "Xác nhận đơn hàng" in mo_ta


def doc_bang_cau_hinh_tu_spec() -> dict:
    """Đọc bảng `cau_hinh` ở spec 02 mục 6: spec là nguồn sự thật nên seed phải khớp từng khóa."""
    noi_dung = SPEC_DATABASE.read_text(encoding="utf-8")
    phan = noi_dung.split("- **`cau_hinh`:**", 1)[1].split("- **Dữ liệu mẫu", 1)[0]
    ket_qua: dict = {}
    for dong in phan.splitlines():
        o = [c.strip() for c in dong.strip().strip("|").split("|")]
        khoa = re.fullmatch(r"`([a-z_]+)`", o[0]) if len(o) >= 3 else None
        if not khoa:
            continue
        if khoa.group(1) == "ai_dau_hieu_nguy_hiem":
            danh_sach = o[1].split(":", 1)[1]
            ket_qua[khoa.group(1)] = [c.strip() for c in danh_sach.split(",") if c.strip()]
        else:
            ket_qua[khoa.group(1)] = json.loads(o[1].strip("`"))
    return ket_qua


async def test_cau_hinh_mac_dinh_khop_bang_trong_spec(db):
    mong_doi = doc_bang_cau_hinh_tu_spec()
    assert len(mong_doi) == 19
    assert mong_doi["gioi_han_otp"] == {"moi_sdt_moi_gio": 5, "moi_ip_moi_gio": 20}  # kiểm tra bộ đọc đọc đúng
    assert len(mong_doi["ai_dau_hieu_nguy_hiem"]) == 13

    await seed_co_ban(db)

    trong_db = {r[0]: r[1] for r in await hang(db, "SELECT khoa, gia_tri FROM cau_hinh")}
    assert trong_db == mong_doi


async def test_tao_admin_dau_tien(db):
    ket_qua = await seed_co_ban(db, admin=ADMIN)
    (nv,) = await hang(
        db,
        "SELECT n.ma_nhan_vien, n.email, n.mat_khau_hash, n.phai_doi_mat_khau, n.trang_thai::text, v.ma "
        "FROM nhan_vien n JOIN vai_tro v ON v.id = n.vai_tro_id",
    )
    assert re.fullmatch(r"NV\d{4}", nv[0])
    assert nv[1] == "admin@example.com"
    assert nv[2] != ADMIN.mat_khau and kiem_tra_mat_khau(ADMIN.mat_khau, nv[2])
    assert nv[3] is True  # buộc đổi mật khẩu ở lần đăng nhập đầu
    assert (nv[4], nv[5]) == ("hoat_dong", "ADMIN")
    assert ket_qua["admin"] == "da_tao"


async def test_khong_co_thong_tin_admin_thi_bo_qua_admin(db):
    ket_qua = await seed_co_ban(db)
    assert await dem(db, "nhan_vien") == 0
    assert ket_qua["admin"] == "bo_qua"


@pytest.mark.parametrize(
    ("email", "mat_khau", "thong_diep"),
    [
        ("", "Mat-khau-thu-123", "email"),
        ("khong-co-a-cong", "Mat-khau-thu-123", "email"),
        ("admin@example.com", "", "mật khẩu"),
        ("admin@example.com", "abcdefgh", "mật khẩu"),  # thiếu số
        ("admin@example.com", "abc123", "mật khẩu"),  # quá ngắn
        ("admin@example.com", "abcd1234", "mật khẩu"),  # đủ chuẩn chung (8 ký tự) nhưng Admin cần tối thiểu 12
        ("admin@example.com", "doi-mat-khau-nay-123", "giá trị mẫu"),  # nguyên văn .env.example
    ],
)
async def test_thong_tin_admin_khong_hop_le_bi_tu_choi(db, email, mat_khau, thong_diep):
    with pytest.raises(ValueError, match=thong_diep):
        await seed_co_ban(db, admin=TaiKhoanAdmin(email=email, mat_khau=mat_khau))
    assert await dem(db, "nhan_vien") == 0


async def test_chay_lai_khong_nhan_ban_du_lieu(db):
    """Tiêu chí T0.5: chạy lại nhiều lần không nhân bản."""
    bang = ["vai_tro", "quyen", "vai_tro_quyen", "cau_hinh", "nhan_vien"]
    await seed_co_ban(db, admin=ADMIN)
    lan_1 = {b: await dem(db, b) for b in bang}
    await seed_co_ban(db, admin=ADMIN)
    await seed_co_ban(db, admin=ADMIN)
    assert {b: await dem(db, b) for b in bang} == lan_1
    assert lan_1["nhan_vien"] == 1


async def test_email_admin_trung_nhan_vien_khac_vai_tro_bi_tu_choi(db):
    """Không báo "đã có sẵn" khi email đó là của dược sĩ: hệ thống vẫn chưa có Admin."""
    await seed_co_ban(db)
    await db.execute(
        text(
            "INSERT INTO nhan_vien (ma_nhan_vien, ho_ten, email, mat_khau_hash, vai_tro_id) "
            "SELECT 'NV9999', 'Dược sĩ', 'admin@example.com', 'x', id FROM vai_tro WHERE ma = 'PHARMACIST'"
        )
    )
    with pytest.raises(ValueError, match="không phải Admin"):
        await seed_co_ban(db, admin=ADMIN)


async def test_chay_lai_khong_dat_lai_mat_khau_admin(db):
    await seed_co_ban(db, admin=ADMIN)
    await db.execute(text("UPDATE nhan_vien SET mat_khau_hash = 'da-doi', phai_doi_mat_khau = false"))
    ket_qua = await seed_co_ban(db, admin=ADMIN)
    (nv,) = await hang(db, "SELECT mat_khau_hash, phai_doi_mat_khau FROM nhan_vien")
    assert tuple(nv) == ("da-doi", False)
    assert ket_qua["admin"] == "da_co"


async def test_chay_lai_khong_ghi_de_cau_hinh_da_sua(db):
    await seed_co_ban(db)
    await db.execute(text("UPDATE cau_hinh SET gia_tri = '60' WHERE khoa = 'nguong_can_han_ngay'"))
    await seed_co_ban(db)
    (gia_tri,) = (await hang(db, "SELECT gia_tri FROM cau_hinh WHERE khoa = 'nguong_can_han_ngay'"))[0]
    assert gia_tri == 60


async def test_chay_lai_them_khoa_cau_hinh_moi_con_thieu(db):
    await seed_co_ban(db)
    await db.execute(text("DELETE FROM cau_hinh WHERE khoa = 'phi_ship_mac_dinh'"))
    await seed_co_ban(db)
    (gia_tri,) = (await hang(db, "SELECT gia_tri FROM cau_hinh WHERE khoa = 'phi_ship_mac_dinh'"))[0]
    assert gia_tri == 30000


async def cap_vai_tro_quyen(db) -> set[tuple[str, str]]:
    ket_qua = await hang(
        db,
        "SELECT v.ma, q.ma FROM vai_tro_quyen vq JOIN vai_tro v ON v.id = vq.vai_tro_id "
        "JOIN quyen q ON q.id = vq.quyen_id",
    )
    return {(v, q) for v, q in ket_qua}


async def test_chay_lai_khong_hoan_tac_chinh_sua_phan_quyen_cua_admin(db):
    """AD18: Admin gán/bỏ quyền cho vai trò lúc chạy. Triển khai lại rồi seed không được trả về mặc định."""
    await seed_co_ban(db)
    await db.execute(
        text(
            "DELETE FROM vai_tro_quyen WHERE quyen_id = (SELECT id FROM quyen WHERE ma = 'order.view') "
            "AND vai_tro_id = (SELECT id FROM vai_tro WHERE ma = 'PHARMACIST')"
        )
    )
    await db.execute(
        text(
            "INSERT INTO vai_tro_quyen (vai_tro_id, quyen_id) SELECT v.id, q.id FROM vai_tro v, quyen q "
            "WHERE v.ma = 'WAREHOUSE' AND q.ma = 'order.confirm'"
        )
    )
    await db.execute(text("UPDATE vai_tro SET ten = 'Dược sĩ (tên do Admin đặt)' WHERE ma = 'PHARMACIST'"))
    truoc = await cap_vai_tro_quyen(db)
    await seed_co_ban(db)
    assert await cap_vai_tro_quyen(db) == truoc
    assert ("PHARMACIST", "order.view") not in truoc and ("WAREHOUSE", "order.confirm") in truoc
    (ten,) = (await hang(db, "SELECT ten FROM vai_tro WHERE ma = 'PHARMACIST'"))[0]
    assert ten == "Dược sĩ (tên do Admin đặt)"


async def test_quyen_moi_trong_yaml_duoc_cap_mac_dinh_con_quyen_bi_go_thi_xoa(db, tmp_path):
    """Phát hành thêm quyền mới: chỉ quyền mới được cấp mặc định; quyền đã bỏ khỏi yaml bị gỡ cùng các cặp của nó."""
    du_lieu = doc_quyen_yaml()
    await seed_co_ban(db)
    bi_bo = du_lieu["quyen"].pop()["ma"]
    du_lieu["quyen"].append(
        {"ma": "thu.moi", "nhom": "thu", "mo_ta": "Quyền thử", "chuc_nang": ["X"], "vai_tro": {"WAREHOUSE": "chi_xem"}}
    )
    yaml_moi = tmp_path / "quyen.yaml"
    yaml_moi.write_text(yaml.safe_dump(du_lieu, allow_unicode=True), encoding="utf-8")

    ket_qua = await seed_co_ban(db, duong_dan_quyen=yaml_moi)

    cap = await cap_vai_tro_quyen(db)
    assert ("WAREHOUSE", "thu.moi") in cap
    assert (
        await hang(
            db, "SELECT gioi_han FROM vai_tro_quyen vq JOIN quyen q ON q.id = vq.quyen_id WHERE q.ma = 'thu.moi'"
        )
    )[0][0] == "chi_xem"
    assert not any(q == bi_bo for _, q in cap) and await dem(db, f"quyen WHERE ma = '{bi_bo}'") == 0
    assert ket_qua["quyen_moi"] == 1


async def test_yaml_co_cap_quyen_sai_bi_tu_choi_va_khong_ghi_gi(db, tmp_path):
    du_lieu = doc_quyen_yaml()
    du_lieu["quyen"][0]["vai_tro"]["PHARMACIST"] = "toan_quyen"
    yaml_hong = tmp_path / "quyen.yaml"
    yaml_hong.write_text(yaml.safe_dump(du_lieu, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ValueError, match="quyen.yaml"):
        await seed_co_ban(db, duong_dan_quyen=yaml_hong)
    assert await dem(db, "vai_tro") == 0


async def test_seed_mau_chay_song_song_cho_nhau_va_khong_loi(db_that):
    """Hai tiến trình `--mau` cùng lúc: `seed_mau` kiểm tra rồi mới chèn nên nếu không tuần tự hóa, tiến trình sau
    không thấy dữ liệu chưa commit của tiến trình trước và vi phạm unique."""
    import asyncio

    async with db_that() as s, s.begin():
        await seed_co_ban(s)
    async with db_that() as a, db_that() as b:
        await a.begin()
        await b.begin()
        moi_a = await seed_mau(a)  # a giữ khóa seed, chưa commit
        viec_b = asyncio.create_task(seed_mau(b))
        await asyncio.sleep(0.5)
        assert not viec_b.done(), "seed thứ hai phải chờ seed thứ nhất"
        await a.commit()
        moi_b = await asyncio.wait_for(viec_b, timeout=20)
        await b.commit()
    assert moi_a["san_pham"] == 42 and moi_b == {}
    async with db_that() as s:
        assert await dem(s, "san_pham") == 42


# --- Dữ liệu mẫu ----------------------------------------------------------------------------------------------------


@pytest_asyncio.fixture
async def co_mau(db):
    await seed_co_ban(db)
    await seed_mau(db)
    return db


def trang_thai_lo_mong_doi(han_su_dung, hom_nay, nguong=90) -> str:
    """Spec 04 mục 1.4: hết hạn khi không còn `han_su_dung > hôm nay`; cận hạn khi còn dưới ngưỡng."""
    if han_su_dung <= hom_nay:
        return "het_han"
    return "can_han" if (han_su_dung - hom_nay).days < nguong else "dang_ban"


async def test_mau_can_co_seed_co_ban_truoc(db):
    with pytest.raises(RuntimeError, match="seed_co_ban"):
        await seed_mau(db)


async def test_mau_danh_muc_3_cap(co_mau):
    cay = {r[0]: r[1] for r in await hang(co_mau, "SELECT id, danh_muc_cha_id FROM danh_muc")}

    def do_sau(id_):
        n = 1
        while cay[id_] is not None:
            id_ = cay[id_]
            n += 1
        return n

    do_sau_cac_nut = [do_sau(i) for i in cay]
    assert max(do_sau_cac_nut) == 3  # đúng 3 cấp, không sâu hơn (spec 02: tối đa 3 cấp)
    assert do_sau_cac_nut.count(1) >= 4  # có nhiều danh mục gốc


async def test_mau_khoang_40_san_pham_phu_du_5_loai(co_mau):
    so_luong = await dem(co_mau, "san_pham")
    assert 38 <= so_luong <= 46
    loai = {r[0]: r[1] for r in await hang(co_mau, "SELECT loai_san_pham::text, count(*) FROM san_pham GROUP BY 1")}
    assert set(loai) == {"thuoc_ke_don", "thuoc_khong_ke_don", "thuc_pham_chuc_nang", "duoc_my_pham", "thiet_bi_y_te"}
    assert loai["thuoc_ke_don"] >= 3
    assert all(n >= 3 for n in loai.values())


async def test_mau_moi_san_pham_dung_1_don_vi_co_so_va_1_don_vi_mac_dinh(co_mau):
    sai = await hang(
        co_mau,
        "SELECT sp.sku FROM san_pham sp LEFT JOIN don_vi_quy_doi d ON d.san_pham_id = sp.id "
        "GROUP BY sp.id HAVING count(*) FILTER (WHERE d.he_so = 1) <> 1 OR count(*) FILTER (WHERE d.la_mac_dinh) <> 1",
    )
    assert sai == []


async def test_mau_don_vi_quy_doi_hop_vi_vien(co_mau):
    ten = {
        r[0]: (r[1], r[2])
        for r in await hang(
            co_mau,
            "SELECT sp.sku, array_agg(d.ten_don_vi ORDER BY d.he_so), array_agg(d.he_so ORDER BY d.he_so) "
            "FROM san_pham sp JOIN don_vi_quy_doi d ON d.san_pham_id = sp.id GROUP BY sp.sku",
        )
    }
    ba_cap = [sku for sku, (t, _) in ten.items() if t == ["Viên", "Vỉ", "Hộp"]]
    assert len(ba_cap) >= 8
    for sku in ba_cap:
        he_so = ten[sku][1]
        assert he_so[0] == 1 and he_so[2] % he_so[1] == 0  # hộp là bội của vỉ


async def test_mau_gia_ban_hop_ly(co_mau):
    gia = await hang(
        co_mau,
        "SELECT sp.sku, d.ten_don_vi, d.he_so, d.gia_ban FROM san_pham sp JOIN don_vi_quy_doi d ON d.san_pham_id = sp.id",
    )
    for sku, _, _, gia_ban in gia:
        assert gia_ban == gia_ban.to_integral_value(), f"{sku}: giá phải là số đồng nguyên"
        assert gia_ban > 0
    # Đơn vị lớn đắt hơn đơn vị nhỏ trong cùng sản phẩm
    theo_sp: dict = {}
    for sku, _, he_so, gia_ban in gia:
        theo_sp.setdefault(sku, []).append((he_so, gia_ban))
    for sku, ds in theo_sp.items():
        ds.sort()
        assert [g for _, g in ds] == sorted(g for _, g in ds), sku


async def test_mau_hoat_chat_thanh_phan_va_tuong_tac(co_mau):
    thieu = await hang(
        co_mau,
        "SELECT sp.sku FROM san_pham sp WHERE sp.loai_san_pham IN ('thuoc_ke_don', 'thuoc_khong_ke_don') "
        "AND NOT EXISTS (SELECT 1 FROM thanh_phan t WHERE t.san_pham_id = sp.id)",
    )
    assert thieu == []
    assert await dem(co_mau, "hoat_chat") >= 15
    cap = await hang(co_mau, "SELECT hoat_chat_a_id, hoat_chat_b_id, muc_do::text FROM tuong_tac_hoat_chat")
    assert len(cap) >= 4
    assert all(a < b for a, b, _ in cap)
    assert {m for _, _, m in cap} >= {"nghiem_trong", "trung_binh"}


async def test_mau_nha_cung_cap_thuong_hieu_nha_san_xuat(co_mau):
    assert await dem(co_mau, "nha_cung_cap") >= 3
    assert await dem(co_mau, "thuong_hieu") >= 5
    assert await dem(co_mau, "nha_san_xuat") >= 3


async def test_mau_lo_co_han_su_dung_da_dang_va_trang_thai_dung(co_mau):
    hom_nay = hom_nay_vn()
    lo = await hang(co_mau, "SELECT so_lo, han_su_dung, trang_thai::text, so_luong_ton FROM lo_thuoc")
    assert len(lo) >= 60
    for so_lo, han, trang_thai, _ in lo:
        assert trang_thai == trang_thai_lo_mong_doi(han, hom_nay), f"lô {so_lo}"
    assert {t for _, _, t, _ in lo} >= {"dang_ban", "can_han", "het_han"}
    assert any(t == "het_han" and ton > 0 for _, _, t, ton in lo)  # lô hết hạn còn hàng, chờ phiếu hủy
    # Có hạn xa (còn hơn 1 năm) lẫn rất gần (dưới 30 ngày)
    ngay_con_lai = [(han - hom_nay).days for _, han, _, _ in lo]
    assert max(ngay_con_lai) > 365 and any(0 < n < 30 for n in ngay_con_lai)


async def test_mau_ton_kho_da_dang_het_hang_ngung_kinh_doanh_chi_con_can_han(co_mau):
    het_hang = await hang(
        co_mau,
        "SELECT sp.sku FROM san_pham sp WHERE sp.trang_thai = 'dang_kinh_doanh' AND NOT EXISTS ("
        " SELECT 1 FROM lo_thuoc l WHERE l.san_pham_id = sp.id AND l.trang_thai = 'dang_ban' AND l.so_luong_ton > 0)",
    )
    assert len(het_hang) >= 2  # không có lô, hoặc chỉ còn lô cận hạn/hết hạn: online không bán được
    assert await dem(co_mau, "san_pham WHERE trang_thai = 'ngung_kinh_doanh'") >= 1
    chi_can_han = await hang(
        co_mau,
        "SELECT sp.sku FROM san_pham sp WHERE EXISTS (SELECT 1 FROM lo_thuoc l WHERE l.san_pham_id = sp.id AND l.trang_thai = 'can_han' AND l.so_luong_ton > 0) "
        "AND NOT EXISTS (SELECT 1 FROM lo_thuoc l WHERE l.san_pham_id = sp.id AND l.trang_thai = 'dang_ban')",
    )
    assert len(chi_can_han) >= 1  # chỉ bán được tại quầy


async def test_mau_bat_bien_ton_kho_khop_the_kho(co_mau):
    """Tiêu chí T0.5 + spec 04 mục 3.2: tồn của lô bằng tổng thẻ kho; không giữ hàng; không biệt trữ."""
    lech = await hang(
        co_mau,
        "SELECT l.id FROM lo_thuoc l LEFT JOIN ("
        " SELECT lo_id, sum(so_luong) FILTER (WHERE khu = 'kho_ban') AS ban, sum(so_luong) FILTER (WHERE khu = 'biet_tru') AS bt"
        " FROM bien_dong_kho GROUP BY lo_id) b ON b.lo_id = l.id "
        "WHERE l.so_luong_ton <> coalesce(b.ban, 0) OR l.so_luong_biet_tru <> coalesce(b.bt, 0) OR l.so_luong_giu <> 0",
    )
    assert lech == []
    # Thẻ kho cuối cùng của mỗi lô có ton_sau bằng tồn hiện tại
    sai_ton_sau = await hang(
        co_mau,
        "SELECT l.id FROM lo_thuoc l JOIN LATERAL ("
        " SELECT ton_sau FROM bien_dong_kho WHERE lo_id = l.id AND khu = 'kho_ban' ORDER BY id DESC LIMIT 1) t ON true "
        "WHERE t.ton_sau <> l.so_luong_ton",
    )
    assert sai_ton_sau == []


async def test_mau_moi_lo_deu_co_phieu_nhap_va_the_kho_nhap(co_mau):
    khong_phieu = await hang(
        co_mau, "SELECT id FROM lo_thuoc l WHERE NOT EXISTS (SELECT 1 FROM ct_phieu_nhap c WHERE c.lo_id = l.id)"
    )
    assert khong_phieu == []
    sai_the = await hang(
        co_mau,
        "SELECT b.id FROM bien_dong_kho b WHERE b.loai <> 'nhap_kho' OR b.chung_tu_loai <> 'phieu_nhap' "
        "OR NOT EXISTS (SELECT 1 FROM phieu_nhap p WHERE p.id = b.chung_tu_id)",
    )
    assert sai_the == []


async def test_mau_phieu_nhap_quy_doi_dung_va_tong_tien_khop(co_mau):
    sai_quy_doi = await hang(
        co_mau,
        "SELECT c.id FROM ct_phieu_nhap c JOIN don_vi_quy_doi d ON d.id = c.don_vi_id JOIN lo_thuoc l ON l.id = c.lo_id "
        "WHERE c.so_luong_co_so <> c.so_luong * d.he_so OR d.san_pham_id <> l.san_pham_id",
    )
    assert sai_quy_doi == []
    sai_tong = await hang(
        co_mau,
        "SELECT p.id FROM phieu_nhap p WHERE p.tong_tien <> (SELECT sum(c.so_luong * c.gia_nhap) FROM ct_phieu_nhap c WHERE c.phieu_nhap_id = p.id)",
    )
    assert sai_tong == []
    # Giá nhập của lô (theo đơn vị cơ sở) = giá nhập dòng phiếu / hệ số
    sai_gia = await hang(
        co_mau,
        "SELECT l.id FROM ct_phieu_nhap c JOIN lo_thuoc l ON l.id = c.lo_id JOIN don_vi_quy_doi d ON d.id = c.don_vi_id "
        "WHERE round(c.gia_nhap / d.he_so) <> l.gia_nhap",
    )
    assert sai_gia == []
    ma = [r[0] for r in await hang(co_mau, "SELECT ma_phieu FROM phieu_nhap")]
    assert ma and all(re.fullmatch(r"PN\d{8}", m) for m in ma)


async def test_mau_tai_khoan(co_mau):
    nv = {
        r[0]: r
        for r in await hang(
            co_mau,
            "SELECT v.ma, n.email, n.mat_khau_hash, n.phai_doi_mat_khau, n.ma_nhan_vien FROM nhan_vien n JOIN vai_tro v ON v.id = n.vai_tro_id",
        )
    }
    assert set(nv) == {
        "PHARMACIST",
        "WAREHOUSE",
    }  # admin do seed_co_ban tạo từ biến môi trường, không thuộc dữ liệu mẫu
    assert all(kiem_tra_mat_khau(MAT_KHAU_MAU, r[2]) for r in nv.values())
    assert all(re.fullmatch(r"NV\d{4}", r[4]) for r in nv.values())

    kh = await hang(co_mau, "SELECT id, so_dien_thoai, mat_khau_hash, email FROM khach_hang ORDER BY id")
    assert len(kh) == 2
    assert all(re.fullmatch(r"0\d{9}", k[1]) for k in kh)
    assert all(kiem_tra_mat_khau(MAT_KHAU_MAU, k[2]) for k in kh)
    mac_dinh = await hang(
        co_mau, "SELECT khach_hang_id, count(*) FILTER (WHERE la_mac_dinh) FROM dia_chi GROUP BY khach_hang_id"
    )
    assert len(mac_dinh) == 2 and all(n == 1 for _, n in mac_dinh)  # mỗi khách đúng 1 địa chỉ mặc định


async def test_mau_ma_giam_gia(co_mau):
    bay_gio = bay_gio_utc()
    km = await hang(
        co_mau,
        "SELECT km.id, km.loai_giam::text, km.gia_tri, km.bat_dau, km.ket_thuc, km.dang_hoat_dong, km.pham_vi::text, array_agg(m.ma) FROM khuyen_mai km JOIN ma_giam_gia m ON m.khuyen_mai_id = km.id GROUP BY km.id",
    )
    con_hieu_luc = [k for k in km if k[5] and k[3] <= bay_gio <= k[4]]
    het_han = [k for k in km if k[4] < bay_gio]
    assert len(con_hieu_luc) >= 2 and len(het_han) >= 1
    assert {k[1] for k in con_hieu_luc} == {"phan_tram", "so_tien"}
    ma = [m for k in km for m in k[7]]
    assert len(ma) == len(set(ma)) and all(re.fullmatch(r"[A-Z0-9]{4,30}", m) for m in ma)
    assert all(k[2] > 0 for k in km) and all(k[2] <= 100 for k in km if k[1] == "phan_tram")
    # Khoảng thời gian hiệu lực hợp lý để demo
    assert all(timedelta(days=1) <= k[4] - k[3] <= timedelta(days=400) for k in km)


async def test_mau_chay_lai_khong_nhan_ban(co_mau):
    bang = [
        "danh_muc", "thuong_hieu", "nha_san_xuat", "hoat_chat", "san_pham", "thanh_phan", "don_vi_quy_doi",
        "tuong_tac_hoat_chat", "nha_cung_cap", "phieu_nhap", "ct_phieu_nhap", "lo_thuoc", "bien_dong_kho",
        "nhan_vien", "khach_hang", "dia_chi", "khuyen_mai", "ma_giam_gia",
    ]  # fmt: skip
    lan_1 = {b: await dem(co_mau, b) for b in bang}
    assert all(n > 0 for n in lan_1.values()), lan_1
    assert await seed_mau(co_mau) == {}  # lần chạy lại không tạo thêm gì
    assert await seed_mau(co_mau) == {}
    assert {b: await dem(co_mau, b) for b in bang} == lan_1
    ton = (await hang(co_mau, "SELECT sum(so_luong_ton) FROM lo_thuoc"))[0][0]
    assert ton > 0 and isinstance(ton, int | Decimal)


def test_trang_thai_lo_dung_tai_cac_ranh_gioi():
    """Spec 04 mục 1.4 và 3.1: HSD bằng hôm nay là hết hạn (FEFO chỉ lấy HSD > hôm nay); cận hạn khi còn DƯỚI ngưỡng."""
    from datetime import date, timedelta

    hom_nay = date(2026, 6, 15)
    ngay = lambda n: hom_nay + timedelta(days=n)  # noqa: E731
    assert trang_thai_lo(ngay(-1), hom_nay, 90) == "het_han"
    assert trang_thai_lo(ngay(0), hom_nay, 90) == "het_han"
    assert trang_thai_lo(ngay(1), hom_nay, 90) == "can_han"
    assert trang_thai_lo(ngay(89), hom_nay, 90) == "can_han"
    assert trang_thai_lo(ngay(90), hom_nay, 90) == "dang_ban"
    assert trang_thai_lo(ngay(91), hom_nay, 90) == "dang_ban"
    assert trang_thai_lo(ngay(30), hom_nay, 30) == "dang_ban"  # ngưỡng lấy từ cấu hình, không cố định 90


async def test_mau_sku_co_tien_to_rieng_va_khong_dung_vao_san_pham_that(db_chua_seed):
    from tests.factories import tao_san_pham

    await seed_co_ban(db_chua_seed)
    that = await tao_san_pham(db_chua_seed, sku="SP0008", ten="Sản phẩm thật của nhà thuốc")
    await seed_mau(db_chua_seed)
    assert all(
        r[0].startswith("MAU-SP")
        for r in await hang(db_chua_seed, "SELECT sku FROM san_pham WHERE id <> :i", i=that.id)
    )
    assert (
        await dem(db_chua_seed, f"lo_thuoc WHERE san_pham_id = {that.id}") == 0
    )  # seed không gắn tồn giả vào hàng thật


async def test_mau_chay_lai_sang_ngay_hoac_nam_moi_khong_nhan_ban_lo(co_mau):
    """Số lô không chứa năm, nên chạy lại vào ngày khác (kể cả sang năm) vẫn nhận ra lô cũ."""
    from datetime import date

    lan_dau = {b: await dem(co_mau, b) for b in ("lo_thuoc", "phieu_nhap", "ct_phieu_nhap", "bien_dong_kho")}
    tong_ton = (await hang(co_mau, "SELECT sum(so_luong_ton) FROM lo_thuoc"))[0][0]
    tong_tien = (await hang(co_mau, "SELECT sum(tong_tien) FROM phieu_nhap"))[0][0]
    assert await seed_mau(co_mau, hom_nay=date(hom_nay_vn().year + 1, 1, 1)) == {}
    assert {b: await dem(co_mau, b) for b in lan_dau} == lan_dau
    assert (await hang(co_mau, "SELECT sum(so_luong_ton) FROM lo_thuoc"))[0][0] == tong_ton
    assert (await hang(co_mau, "SELECT sum(tong_tien) FROM phieu_nhap"))[0][0] == tong_tien


async def test_mau_ngay_san_xuat_khong_o_tuong_lai_va_truoc_han_su_dung(co_mau):
    sai = await hang(
        co_mau, "SELECT so_lo FROM lo_thuoc WHERE ngay_san_xuat > current_date OR ngay_san_xuat >= han_su_dung"
    )
    assert sai == []


async def test_mau_the_kho_nhap_cung_ngay_voi_phieu_nhap(co_mau):
    lech = await hang(
        co_mau,
        "SELECT b.id FROM bien_dong_kho b JOIN phieu_nhap p ON p.id = b.chung_tu_id "
        "WHERE b.chung_tu_loai = 'phieu_nhap' AND b.created_at <> p.ngay_nhap",
    )
    assert lech == []


async def test_mau_chay_lai_sau_khi_khach_sua_dia_chi_va_nha_san_xuat_khong_loi(co_mau):
    await co_mau.execute(
        text("UPDATE dia_chi SET dia_chi_chi_tiet = '12A Nguyễn Huệ' WHERE dia_chi_chi_tiet = '12 Nguyễn Huệ'")
    )
    await co_mau.execute(text("UPDATE nha_san_xuat SET quoc_gia = 'Thái Lan' WHERE quoc_gia = 'Ấn Độ'"))
    truoc = {b: await dem(co_mau, b) for b in ("dia_chi", "nha_san_xuat")}
    assert await seed_mau(co_mau) == {}
    assert {b: await dem(co_mau, b) for b in truoc} == truoc

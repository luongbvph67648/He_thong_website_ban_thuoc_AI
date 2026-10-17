"""T0.6: hạ tầng test hoạt động đúng như spec 10 mục 2 mô tả (cô lập, rollback, đăng nhập, factories)."""

from decimal import Decimal

import jwt
import pytest
from sqlalchemy import func, select, text

from app.core.bao_mat import giai_ma_access_token, kiem_tra_mat_khau
from app.core.db import Db
from app.core.loi import LoiNghiepVu
from app.models.ban_hang import CtDonHang
from app.models.he_thong import NhanVien
from app.models.khach_hang import KhachHang
from app.models.kho import BienDongKho
from app.seed.co_ban import TaiKhoanAdmin  # noqa: F401 - kiểm tra import được từ test
from tests.factories import (
    MAT_KHAU_TEST,
    tao_don,
    tao_khach,
    tao_lo,
    tao_nhan_vien,
    tao_san_pham,
)
from tests.ha_tang import tao_lai_database

SDT_RO_RI = "0999999991"


async def dem(db, model) -> int:
    return (await db.execute(select(func.count()).select_from(model))).scalar_one()


# --- Database test --------------------------------------------------------------------------------------------------


async def test_database_test_dung_tu_migration_va_da_seed(db):
    assert (await db.execute(text("SELECT version_num FROM alembic_version"))).scalar_one() == "0003"
    assert (await db.execute(text("SELECT count(*) FROM vai_tro"))).scalar_one() == 3
    assert (await db.execute(text("SELECT count(*) FROM cau_hinh"))).scalar_one() == 19
    assert await dem(db, KhachHang) == 0  # không seed dữ liệu mẫu


async def test_db_chua_seed_khong_co_vai_tro(db_chua_seed):
    assert (await db_chua_seed.execute(text("SELECT count(*) FROM vai_tro"))).scalar_one() == 0


async def test_rollback_1_ghi_du_lieu_trong_test(db):
    await tao_khach(db, so_dien_thoai=SDT_RO_RI)
    await db.commit()  # commit trong code được test chỉ giải phóng savepoint
    assert await dem(db, KhachHang) == 1


async def test_rollback_2_test_sau_khong_thay_du_lieu_cua_test_truoc(db):
    """Phụ thuộc thứ tự chạy trong file: nếu rollback hỏng, test trước để lại khách ở đây."""
    assert await dem(db, KhachHang) == 0


# --- Session của request ----------------------------------------------------------------------------------------------


async def test_health_qua_app_dung_database_test(client):
    phan_hoi = await client.get("/api/v1/health")
    assert phan_hoi.status_code == 200 and phan_hoi.json() == {"trang_thai": "ok", "db": "ok"}


def them_route_thu(app):
    """Route chỉ có trong test, dùng `Db` như route thật để kiểm tra ngữ nghĩa commit/rollback của request."""

    @app.post("/thu/khach")
    async def tao(db: Db, loi: bool = False):
        db.add(
            KhachHang(ho_ten="Từ request", so_dien_thoai=SDT_RO_RI, mat_khau_hash="x", dong_y_chinh_sach_luc=func.now())
        )
        await db.flush()
        if loi:
            raise LoiNghiepVu("TRUNG_DU_LIEU", "Lỗi giả sau khi đã ghi")
        return {"ok": True}

    @app.get("/thu/dem-khach")
    async def dem_khach(db: Db):
        return {"so_khach": await dem(db, KhachHang)}

    return app


async def test_request_thanh_cong_giu_du_lieu_trong_test_va_thay_duoc_tu_db(app, client, db):
    them_route_thu(app)
    assert (await client.post("/thu/khach")).status_code == 200
    assert (await client.get("/thu/dem-khach")).json() == {"so_khach": 1}
    assert await dem(db, KhachHang) == 1  # session của test thấy dữ liệu do request ghi (cùng transaction ngoài)


async def test_request_loi_hoan_tac_phan_da_ghi_cua_request_do(app, client, db):
    """Giống production: ngoại lệ sau khi ghi thì get_db rollback, dữ liệu của request đó không còn."""
    them_route_thu(app)
    await tao_khach(db)  # dữ liệu có từ trước request phải còn nguyên
    phan_hoi = await client.post("/thu/khach", params={"loi": "true"})
    assert phan_hoi.status_code == 409 and phan_hoi.json()["ma_loi"] == "TRUNG_DU_LIEU"
    assert await dem(db, KhachHang) == 1


async def test_request_thay_du_lieu_factory_chua_commit(app, client, db):
    them_route_thu(app)
    for _ in range(3):
        await tao_khach(db)
    assert (await client.get("/thu/dem-khach")).json() == {"so_khach": 3}


async def test_request_khong_the_commit_tay(app, client):
    @app.get("/thu/commit-tay")
    async def commit_tay(db: Db):
        await db.commit()

    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as c:
        assert (await c.get("/thu/commit-tay")).status_code == 500  # PhienRequest chặn commit()


# --- Fixture đăng nhập ----------------------------------------------------------------------------------------------


async def test_dang_nhap_khach(dang_nhap_khach):
    tieu_de = dang_nhap_khach.headers["Authorization"]
    claim = giai_ma_access_token(tieu_de.removeprefix("Bearer "), "khach")
    assert claim["sub"] == str(dang_nhap_khach.tai_khoan.id)
    assert isinstance(dang_nhap_khach.tai_khoan, KhachHang)
    with pytest.raises(jwt.InvalidAudienceError):  # token khách không dùng được cho khu nội bộ
        giai_ma_access_token(tieu_de.removeprefix("Bearer "), "noi_bo")


async def kiem_tra_dang_nhap_noi_bo(db, c, vai_tro):
    claim = giai_ma_access_token(c.headers["Authorization"].removeprefix("Bearer "), "noi_bo")
    assert claim["sub"] == str(c.tai_khoan.id)
    ma = (
        await db.execute(
            text("SELECT v.ma FROM nhan_vien n JOIN vai_tro v ON v.id = n.vai_tro_id WHERE n.id = :i"),
            {"i": c.tai_khoan.id},
        )
    ).scalar_one()
    assert ma == vai_tro
    with pytest.raises(jwt.InvalidAudienceError):  # token nội bộ không dùng được cho khu khách
        giai_ma_access_token(c.headers["Authorization"].removeprefix("Bearer "), "khach")


async def test_dang_nhap_duoc_si(db, dang_nhap_duoc_si):
    await kiem_tra_dang_nhap_noi_bo(db, dang_nhap_duoc_si, "PHARMACIST")


async def test_dang_nhap_kho(db, dang_nhap_kho):
    await kiem_tra_dang_nhap_noi_bo(db, dang_nhap_kho, "WAREHOUSE")


async def test_dang_nhap_admin(db, dang_nhap_admin):
    await kiem_tra_dang_nhap_noi_bo(db, dang_nhap_admin, "ADMIN")


async def test_hai_dang_nhap_trong_mot_test_la_hai_client_khac_nhau(dang_nhap_khach, dang_nhap_admin):
    assert dang_nhap_khach.headers["Authorization"] != dang_nhap_admin.headers["Authorization"]
    assert dang_nhap_khach.tai_khoan is not dang_nhap_admin.tai_khoan


# --- db_that (commit thật) ------------------------------------------------------------------------------------------


async def test_db_that_1_commit_that_thay_duoc_tu_session_khac(db_that):
    async with db_that() as s, s.begin():
        await tao_khach(s, so_dien_thoai=SDT_RO_RI)
        await tao_nhan_vien(s, "ADMIN")
    async with db_that() as s:  # session mới thấy vì đã commit thật
        assert await dem(s, KhachHang) == 1 and await dem(s, NhanVien) == 1


async def test_db_that_2_sau_test_don_sach_nhung_giu_seed(db_that):
    async with db_that() as s:
        assert await dem(s, KhachHang) == 0 and await dem(s, NhanVien) == 0
        assert (await s.execute(text("SELECT count(*) FROM vai_tro"))).scalar_one() == 3
        assert (await s.execute(text("SELECT count(*) FROM vai_tro_quyen"))).scalar_one() > 50
        assert (await s.execute(text("SELECT count(*) FROM cau_hinh"))).scalar_one() == 19
        # RESTART IDENTITY: id bắt đầu lại từ 1
    async with db_that() as s, s.begin():
        assert (await tao_khach(s)).id == 1


async def test_db_that_3_sua_phan_quyen_that_phai_duoc_khoi_phuc_ve_mac_dinh_sau_test(db_that):
    """AD18 commit thật vào `vai_tro_quyen`; seed không ghi đè phân quyền đã có nên dọn dẹp phải tự khôi phục, nếu
    không test sau thấy ma trận quyền bị lệch (từng khiến test AD18 viết sau bị lỗi giả)."""
    mac_dinh = "SELECT count(*), count(*) FILTER (WHERE gioi_han IS NULL) FROM vai_tro_quyen"
    async with db_that() as s:
        so_mac_dinh = (await s.execute(text(mac_dinh))).one()
    async with db_that() as s, s.begin():
        await s.execute(
            text("DELETE FROM vai_tro_quyen WHERE quyen_id = (SELECT id FROM quyen WHERE ma = 'order.pick')")
        )
        await s.execute(text("UPDATE vai_tro_quyen SET gioi_han = 'chi_xem' WHERE gioi_han IS NULL"))
    async with db_that() as s:
        assert (await s.execute(text(mac_dinh))).one() != so_mac_dinh  # đã bị sửa thật


async def test_db_that_4_phan_quyen_ve_dung_mac_dinh_cua_quyen_yaml(db_that):
    from tests.nhan_vien.test_nv_ho_so import quyen_theo_yaml

    async with db_that() as s:
        thuc_te = {
            (vt, q): "day_du" if g is None else "chi_xem"
            for vt, q, g in (
                await s.execute(
                    text(
                        "SELECT v.ma, q.ma, vq.gioi_han FROM vai_tro_quyen vq "
                        "JOIN vai_tro v ON v.id = vq.vai_tro_id JOIN quyen q ON q.id = vq.quyen_id"
                    )
                )
            ).all()
        }
    mong_doi = {(vt, q): m for vt in ("PHARMACIST", "WAREHOUSE", "ADMIN") for q, m in quyen_theo_yaml(vt).items()}
    assert thuc_te == mong_doi


# --- An toàn khi tạo lại database ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ten",
    ["nha_thuoc", "postgres", "production", 'nha_thuoc_test"; DROP DATABASE x; --', ""],
)
async def test_tao_lai_database_tu_choi_ten_khong_co_chu_test(ten):
    """Chặn trước khi kết nối: biến môi trường trỏ nhầm vào DB dev không bao giờ bị xóa."""
    with pytest.raises(ValueError, match="Từ chối"):
        await tao_lai_database(f"postgresql+asyncpg://postgres:postgres@localhost:1/{ten}")


# --- Factories ------------------------------------------------------------------------------------------------------


async def test_tao_khach_gia_tri_mac_dinh_hop_le_va_khong_trung(db):
    a, b = await tao_khach(db), await tao_khach(db)
    assert a.so_dien_thoai != b.so_dien_thoai and a.email != b.email
    assert kiem_tra_mat_khau(MAT_KHAU_TEST, a.mat_khau_hash)
    c = await tao_khach(db, ho_ten="Tên riêng")
    assert c.ho_ten == "Tên riêng"


async def test_tao_nhan_vien_theo_vai_tro_va_loi_neu_chua_seed(db, db_chua_seed):
    nv = await tao_nhan_vien(db, "WAREHOUSE")
    assert nv.phai_doi_mat_khau is False and nv.ma_nhan_vien.startswith("NV")
    with pytest.raises(LookupError, match="seed_co_ban"):
        await tao_nhan_vien(db_chua_seed)


async def test_tao_san_pham_mac_dinh_va_nhieu_don_vi(db):
    mac_dinh = await tao_san_pham(db)
    assert list(mac_dinh.don_vi_theo_ten) == ["viên"]
    sp = await tao_san_pham(
        db,
        loai="thuoc_ke_don",
        don_vi=[
            {"ten_don_vi": "viên", "he_so": 1, "gia_ban": 500},
            {"ten_don_vi": "hộp", "he_so": 100, "gia_ban": 45000, "la_mac_dinh": True},
        ],
    )
    assert sp.loai_san_pham == "thuoc_ke_don"
    assert sp.don_vi_theo_ten["hộp"].he_so == 100 and sp.don_vi_theo_ten["viên"].la_mac_dinh is False


async def test_tao_lo_voi_so_luong_ghi_the_kho_khop_ton(db):
    lo = await tao_lo(db, so_luong=120)
    the = (await db.execute(select(BienDongKho).where(BienDongKho.lo_id == lo.id))).scalars().all()
    assert lo.so_luong_ton == 120 and [t.so_luong for t in the] == [120]
    assert lo.trang_thai == "dang_ban"


async def test_tao_lo_trang_thai_theo_han_su_dung(db):
    from datetime import timedelta

    from app.core.thoi_gian import hom_nay_vn

    sp = await tao_san_pham(db)
    cac_lo = {
        "can_han": await tao_lo(db, sp, han_su_dung=hom_nay_vn() + timedelta(days=30)),
        "het_han": await tao_lo(db, sp, han_su_dung=hom_nay_vn() - timedelta(days=1)),
    }
    assert {k: lo.trang_thai for k, lo in cac_lo.items()} == {"can_han": "can_han", "het_han": "het_han"}
    ghi_de = await tao_lo(db, sp, trang_thai="khoa")
    assert ghi_de.trang_thai == "khoa"


async def test_tao_don_tong_tien_khop_cong_thuc_va_qua_duoc_check(db):
    khach = await tao_khach(db)
    sp = await tao_san_pham(
        db,
        don_vi=[
            {"ten_don_vi": "viên", "he_so": 1, "gia_ban": 500},
            {"ten_don_vi": "hộp", "he_so": 10, "gia_ban": 4500, "la_mac_dinh": True},
        ],
    )
    don = await tao_don(
        db,
        khach,
        dong=[{"san_pham": sp, "so_luong": 2}, {"san_pham": sp, "so_luong": 3, "don_vi": "viên"}],
        giam_gia=500,
        phi_van_chuyen=30000,
    )
    assert don.tam_tinh == Decimal(2 * 4500 + 3 * 500)
    assert don.tong_tien == don.tam_tinh - 500 + 30000  # ràng buộc ck_don_hang_tong_tien_dung đã chấp nhận
    chi_tiet = (
        (await db.execute(select(CtDonHang).where(CtDonHang.don_hang_id == don.id).order_by(CtDonHang.id)))
        .scalars()
        .all()
    )
    assert [(c.ten_don_vi, c.so_luong, c.thanh_tien) for c in chi_tiet] == [
        ("hộp", 2, Decimal(9000)),
        ("viên", 3, Decimal(1500)),
    ]


async def test_tao_don_o_trang_thai_cho_khach_xac_nhan_khong_can_phuong_thuc_tt(db):
    don = await tao_don(db, trang_thai="cho_khach_xac_nhan", phuong_thuc_tt=None)
    assert don.trang_thai == "cho_khach_xac_nhan" and don.khach_hang_id is None

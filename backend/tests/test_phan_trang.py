"""core/phan_trang.py: tham số trang/kich_thuoc và phản hồi {du_lieu, tong, trang, kich_thuoc}."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.phan_trang import PhanTrang, ThamSoPhanTrang, Trang, dem_tong, lay_trang, tao_trang
from app.main import create_app


def test_offset_va_limit():
    tp = ThamSoPhanTrang(trang=3, kich_thuoc=20)
    assert (tp.offset, tp.limit) == (40, 20)
    assert ThamSoPhanTrang(trang=1, kich_thuoc=100).offset == 0


def test_tao_trang_co_dung_bon_khoa():
    trang = tao_trang(["a", "b"], tong=45, tham_so=ThamSoPhanTrang(trang=3, kich_thuoc=20))
    assert trang.model_dump() == {"du_lieu": ["a", "b"], "tong": 45, "trang": 3, "kich_thuoc": 20}


@pytest.fixture
def app_ds():
    app = create_app()

    @app.get("/thu/ds", response_model=Trang[int])
    async def ds(tp: PhanTrang):
        return tao_trang([tp.trang, tp.kich_thuoc], tong=45, tham_so=tp)

    return app


async def test_mac_dinh_trang_1_kich_thuoc_20(app_ds, mo_client):
    async with mo_client(app_ds) as c:
        resp = await c.get("/thu/ds")
    assert resp.status_code == 200
    assert resp.json() == {"du_lieu": [1, 20], "tong": 45, "trang": 1, "kich_thuoc": 20}


async def test_nhan_tham_so_tu_query(app_ds, mo_client):
    async with mo_client(app_ds) as c:
        resp = await c.get("/thu/ds?trang=3&kich_thuoc=100")
    assert resp.json() == {"du_lieu": [3, 100], "tong": 45, "trang": 3, "kich_thuoc": 100}


@pytest.mark.parametrize(
    ("query", "truong"),
    [
        ("trang=0", "trang"),
        ("trang=-1", "trang"),
        ("trang=1000001", "trang"),
        ("trang=99999999999999999999", "trang"),  # vượt int64 sẽ làm OFFSET lỗi ở DB
        ("kich_thuoc=0", "kich_thuoc"),
        ("kich_thuoc=101", "kich_thuoc"),
    ],
)
async def test_tu_choi_tham_so_ngoai_gioi_han(app_ds, mo_client, query, truong):
    async with mo_client(app_ds) as c:
        resp = await c.get(f"/thu/ds?{query}")
    assert resp.status_code == 400
    body = resp.json()
    assert body["ma_loi"] == "DU_LIEU_KHONG_HOP_LE"
    assert [e["truong"] for e in body["chi_tiet"]] == [truong]


async def test_trang_toi_da_van_hop_le(app_ds, mo_client):
    async with mo_client(app_ds) as c:
        resp = await c.get("/thu/ds?trang=1000000&kich_thuoc=100")
    assert resp.status_code == 200


async def test_tham_so_khong_phai_so(app_ds, mo_client):
    async with mo_client(app_ds) as c:
        resp = await c.get("/thu/ds?trang=abc")
    assert resp.status_code == 400
    assert resp.json()["chi_tiet"] == [{"truong": "trang", "loi": "Phải là số nguyên"}]


def _truy_van_45_dong():
    n = func.generate_series(1, 45).column_valued("n")
    return select(n).order_by(n)


async def test_lay_trang_tren_csdl_that(engine_tam):
    async with AsyncSession(engine_tam) as db:
        stmt = _truy_van_45_dong()
        assert await dem_tong(db, stmt) == 45

        dong, tong = await lay_trang(db, stmt, ThamSoPhanTrang(trang=1, kich_thuoc=20))
        assert (list(dong), tong) == (list(range(1, 21)), 45)

        dong, tong = await lay_trang(db, stmt, ThamSoPhanTrang(trang=3, kich_thuoc=20))
        assert (list(dong), tong) == (list(range(41, 46)), 45)  # trang cuối chỉ còn 5 dòng

        dong, tong = await lay_trang(db, stmt, ThamSoPhanTrang(trang=4, kich_thuoc=20))
        assert (list(dong), tong) == ([], 45)  # vượt trang cuối: rỗng nhưng vẫn báo đúng tổng


async def test_lay_trang_nhieu_cot_tra_tung_dong_la_row(engine_tam):
    async with AsyncSession(engine_tam) as db:
        n = func.generate_series(1, 5).column_valued("n")
        stmt = select(n, (n * 10).label("gap_muc")).order_by(n)
        dong, tong = await lay_trang(db, stmt, ThamSoPhanTrang(trang=2, kich_thuoc=2), nhieu_cot=True)
        assert ([tuple(d) for d in dong], tong) == ([(3, 30), (4, 40)], 5)
        mot_cot, _ = await lay_trang(db, stmt, ThamSoPhanTrang(trang=2, kich_thuoc=2))  # mặc định: cột đầu
        assert list(mot_cot) == [3, 4]


def test_openapi_cho_trang_va_tien_dung_de_sinh_client_typescript():
    """T0.7 sinh client từ OpenAPI: Tien phải là string, Trang[...] phải thành schema riêng."""
    from pydantic import BaseModel

    from app.core.tien import Tien

    class Muc(BaseModel):
        ten: str
        gia: Tien

    app = create_app()

    @app.get("/thu/ds", response_model=Trang[Muc])
    async def ds(tp: PhanTrang):
        return tao_trang([], 0, tp)

    schemas = app.openapi()["components"]["schemas"]
    assert schemas["Muc"]["properties"]["gia"]["type"] == "string"
    assert "Trang_Muc_" in schemas


# --- Sắp xếp (spec 06 mục 5): `sap_xep=-created_at`, chỉ nhận trường nằm trong danh sách cho phép ---------------------


async def test_sap_xep_tang_giam_va_khoa_phu_on_dinh(db):
    from app.core.phan_trang import sap_xep_theo
    from app.models.he_thong import NhanVien
    from tests.factories import tao_nhan_vien

    cho_phep = {"ho_ten": NhanVien.ho_ten}
    for ten in ("Bình", "An", "An", "Cường"):  # hai dòng trùng tên: khóa phụ `id` quyết định thứ tự
        await tao_nhan_vien(db, ho_ten=ten)

    async def doc(sap_xep):
        stmt = sap_xep_theo(select(NhanVien), sap_xep, cho_phep, mac_dinh="ho_ten", khoa_phu=NhanVien.id)
        return [
            (n.ho_ten, n.id) for n in (await db.scalars(stmt.where(NhanVien.ho_ten.in_(["An", "Bình", "Cường"])))).all()
        ]

    tang = await doc("ho_ten")
    giam = await doc("-ho_ten")
    assert [t for t, _ in tang] == ["An", "An", "Bình", "Cường"]
    assert [t for t, _ in giam] == ["Cường", "Bình", "An", "An"]
    assert [i for t, i in tang if t == "An"] == sorted(i for t, i in tang if t == "An")
    assert [i for t, i in giam if t == "An"] == sorted((i for t, i in giam if t == "An"), reverse=True)
    assert await doc(None) == tang  # không gửi thì theo mặc định


@pytest.mark.parametrize(
    "sap_xep", ["mat_khau_hash", "-mat_khau_hash", "id; drop table nhan_vien", "", "--ho_ten", "ho_ten,-id"]
)
def test_sap_xep_truong_ngoai_danh_sach_bi_tu_choi(sap_xep):
    from app.core.loi import LoiNghiepVu
    from app.core.phan_trang import sap_xep_theo
    from app.models.he_thong import NhanVien

    with pytest.raises(LoiNghiepVu) as loi:
        sap_xep_theo(select(NhanVien), sap_xep, {"ho_ten": NhanVien.ho_ten}, mac_dinh="ho_ten", khoa_phu=NhanVien.id)
    assert loi.value.ma_loi == "DU_LIEU_KHONG_HOP_LE"
    assert loi.value.chi_tiet[0]["truong"] == "sap_xep"


def test_sap_xep_mac_dinh_phai_nam_trong_danh_sach_cho_phep():
    from app.core.phan_trang import sap_xep_theo
    from app.models.he_thong import NhanVien

    with pytest.raises(ValueError, match="mac_dinh"):
        sap_xep_theo(select(NhanVien), None, {"ho_ten": NhanVien.ho_ten}, mac_dinh="created_at", khoa_phu=NhanVien.id)

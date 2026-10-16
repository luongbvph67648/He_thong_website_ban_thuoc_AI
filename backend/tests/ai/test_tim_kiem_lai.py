"""T7.2: tìm kiếm lai (từ khóa + vector, RRF) và quay về từ khóa khi AI lỗi/tắt."""

from sqlalchemy import select

from app.models.ai import LichSuTimKiem
from app.models.san_pham import ThongTinChuyenMon
from app.modules.ai_quan_tri import tri_thuc
from app.modules.cua_hang import tim_kiem_lai
from tests.factories import tao_san_pham

TK = "/api/v1/tim-kiem"


async def _co_noi_dung(db, sp, chi_dinh):
    db.add(ThongTinChuyenMon(san_pham_id=sp.id, phien_ban=1, trang_thai="da_duyet", chi_dinh=chi_dinh))
    await db.flush()


def test_rrf_cong_diem_hai_danh_sach():
    d = tim_kiem_lai.ghep_rrf([1, 2, 3], [3, 1])
    assert d[1] == 1 / 61 + 1 / 62 and d[3] == 1 / 63 + 1 / 61 and d[2] == 1 / 62
    assert sorted(d, key=lambda i: -d[i]) == [1, 3, 2]


async def test_tim_theo_trieu_chung_ma_ten_khong_chua(client, db):
    paracetamol = await tao_san_pham(db, "thuoc_khong_ke_don", ten="Panadol Extra")
    kem = await tao_san_pham(db, "thuoc_khong_ke_don", ten="Kem dưỡng ẩm Cetaphil")
    await _co_noi_dung(db, paracetamol, "Giảm đau đầu, hạ sốt, đau cơ.")
    await _co_noi_dung(db, kem, "Dưỡng ẩm cho da khô.")
    await tri_thuc.dong_bo(db)
    r = await client.get(TK, params={"q": "đau đầu"})
    assert r.status_code == 200, r.text
    ten = [x["ten"] for x in r.json()["du_lieu"]]
    assert ten[0] == "Panadol Extra" and "Kem dưỡng ẩm Cetaphil" not in ten
    ls = (await db.execute(select(LichSuTimKiem).order_by(LichSuTimKiem.id.desc()))).scalars().first()
    assert ls.che_do == "hybrid" and ls.so_ket_qua == r.json()["tong"]


async def test_tu_khoa_trung_ten_van_len_dau_khi_ghep(client, db):
    a = await tao_san_pham(db, "thuoc_khong_ke_don", ten="Vitamin C 500mg")
    b = await tao_san_pham(db, "thuoc_khong_ke_don", ten="Thuốc bổ sung")
    await _co_noi_dung(db, a, "Bổ sung vitamin C.")
    await _co_noi_dung(db, b, "Bổ sung vitamin C và khoáng chất cho cơ thể mệt mỏi.")
    await tri_thuc.dong_bo(db)
    ten = [x["ten"] for x in (await client.get(TK, params={"q": "vitamin c"})).json()["du_lieu"]]
    assert ten[0] == "Vitamin C 500mg"


async def test_ai_loi_quay_ve_tu_khoa(client, db, monkeypatch):
    sp = await tao_san_pham(db, "thuoc_khong_ke_don", ten="Panadol Extra")
    await _co_noi_dung(db, sp, "Giảm đau đầu.")
    await tri_thuc.dong_bo(db)

    async def hong(ds):
        raise RuntimeError("mô hình lỗi")

    monkeypatch.setattr(tim_kiem_lai.embedding, "embed", hong)
    r = await client.get(TK, params={"q": "panadol"})
    assert r.status_code == 200 and [x["ten"] for x in r.json()["du_lieu"]] == ["Panadol Extra"]
    ls = (await db.execute(select(LichSuTimKiem).order_by(LichSuTimKiem.id.desc()))).scalars().first()
    assert ls.che_do == "tu_khoa"
    # theo triệu chứng thì không có kết quả khi AI lỗi (từ khóa không khớp)
    assert (await client.get(TK, params={"q": "đau đầu"})).json()["tong"] == 0


async def test_tat_module_tim_kiem_chi_dung_tu_khoa(client, dang_nhap_admin, db):
    sp = await tao_san_pham(db, "thuoc_khong_ke_don", ten="Panadol Extra")
    await _co_noi_dung(db, sp, "Giảm đau đầu.")
    await tri_thuc.dong_bo(db)
    d = (await dang_nhap_admin.get("/api/v1/noi-bo/cau-hinh-ai")).json()
    await dang_nhap_admin.put(
        "/api/v1/noi-bo/cau-hinh-ai",
        json={"phien_ban": d["phien_ban"], "ai_module": {**d["ai_module"], "tim_kiem": False}},
    )
    assert (await client.get(TK, params={"q": "đau đầu"})).json()["tong"] == 0


async def test_san_pham_khong_hien_thi_bi_loai_va_ke_don_van_hien_o_trang_tim_kiem(client, db):
    ke_don = await tao_san_pham(db, "thuoc_ke_don", ten="Amoxicillin 500mg")
    an = await tao_san_pham(db, "thuoc_khong_ke_don", ten="Thuốc đã ngừng")
    await _co_noi_dung(db, ke_don, "Điều trị nhiễm khuẩn hô hấp.")
    await _co_noi_dung(db, an, "Điều trị nhiễm khuẩn hô hấp nhẹ.")
    await tri_thuc.dong_bo(db)
    an.trang_thai = "ngung_kinh_doanh"
    await db.flush()
    ten = [x["ten"] for x in (await client.get(TK, params={"q": "nhiễm khuẩn hô hấp"})).json()["du_lieu"]]
    assert ten == ["Amoxicillin 500mg"]  # trang tìm kiếm vẫn hiện thuốc kê đơn (có nhãn can_tu_van)


async def test_loc_ke_don_cho_chatbot(db):
    ke_don = await tao_san_pham(db, "thuoc_ke_don", ten="Amoxicillin 500mg")
    thuong = await tao_san_pham(db, "thuoc_khong_ke_don", ten="Efferalgan")
    await _co_noi_dung(db, ke_don, "Điều trị nhiễm khuẩn hô hấp.")
    await _co_noi_dung(db, thuong, "Điều trị nhiễm khuẩn hô hấp nhẹ.")
    await tri_thuc.dong_bo(db)
    tat_ca = await tim_kiem_lai.id_ngu_nghia(db, "nhiễm khuẩn hô hấp")
    assert {ke_don.id, thuong.id} <= set(tat_ca)
    assert await tim_kiem_lai.id_ngu_nghia(db, "nhiễm khuẩn hô hấp", chi_khong_ke_don=True) == [thuong.id]

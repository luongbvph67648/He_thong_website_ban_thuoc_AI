"""T7.1: AD10 đồng bộ kho tri thức, AD09 cấu hình AI."""

from sqlalchemy import select

from app.ai import embedding
from app.models.ai import TaiLieuTriThuc
from app.models.he_thong import BaiViet
from app.models.san_pham import ThongTinChuyenMon
from app.modules.ai_quan_tri import tri_thuc
from tests.factories import tao_nhan_vien, tao_san_pham

TT = "/api/v1/noi-bo/tri-thuc"
CH = "/api/v1/noi-bo/cau-hinh-ai"


async def _noi_dung(db, sp, **truong):
    t = ThongTinChuyenMon(san_pham_id=sp.id, phien_ban=1, trang_thai="da_duyet", **truong)
    db.add(t)
    await db.flush()
    return t


async def _bai(db, loai="bai_viet", ai=True, trang_thai="da_duyet", noi_dung="Nội dung bài"):
    nv = await tao_nhan_vien(db, "PHARMACIST")
    b = BaiViet(
        tieu_de="Tiêu đề",
        slug=f"bai-{loai}-{ai}-{trang_thai}-{len(noi_dung)}",
        noi_dung=noi_dung,
        loai=loai,
        tac_gia_id=nv.id,
        trang_thai=trang_thai,
        dua_vao_ai=ai,
    )
    db.add(b)
    await db.flush()
    return b


def test_chia_doan_chong_lan_va_giu_ngan():
    assert tri_thuc.chia_doan("ngắn") == ["ngắn"] and tri_thuc.chia_doan("   ") == []
    dai = "a" * 2000
    ds = tri_thuc.chia_doan(dai)
    assert [len(d) for d in ds] == [800, 800, 600] and all(len(d) <= 800 for d in ds)
    assert ds[0][:700] + ds[1][:700] + ds[2] == dai  # chồng 100 ký tự


async def test_dong_bo_tao_doan_tong_quan_chuyen_mon_va_bai_viet(dang_nhap_admin, db):
    sp = await tao_san_pham(db, "thuoc_khong_ke_don")
    ke_don = await tao_san_pham(db, "thuoc_ke_don")
    await _noi_dung(db, sp, chi_dinh="Hạ sốt, giảm đau. Dùng khi sốt.", than_trong="x" * 1000)
    await _bai(db, "bai_viet", True)
    await _bai(db, "bai_viet", False, noi_dung="Không đưa vào AI")
    await _bai(db, "chinh_sach", False, noi_dung="Chính sách đổi trả")
    await _bai(db, "faq", False, trang_thai="nhap", noi_dung="Nháp không vào")
    r = await dang_nhap_admin.post(f"{TT}/dong-bo")
    assert r.status_code == 200, r.text
    kq = r.json()
    assert (
        kq["xoa"] == 0
        and kq["sua"] == 0
        and kq["them"] == kq["tong_doan"]
        and kq["mo_hinh"] == embedding.TEN_MO_HINH_GIA
    )
    ds = (await db.execute(select(TaiLieuTriThuc))).scalars().all()
    tong_quan = [d for d in ds if d.truong == "tong_quan"]
    assert {d.san_pham_id for d in tong_quan} >= {sp.id, ke_don.id}
    mot = next(d for d in tong_quan if d.san_pham_id == ke_don.id)
    assert (
        mot.metadata_["can_ke_don"] is True
        and next(d for d in tong_quan if d.san_pham_id == sp.id).metadata_["can_ke_don"] is False
    )
    assert "Chỉ định: Hạ sốt, giảm đau." in next(d for d in tong_quan if d.san_pham_id == sp.id).noi_dung
    chuyen_mon = [d for d in ds if d.san_pham_id == sp.id and d.truong != "tong_quan"]
    assert {d.truong for d in chuyen_mon} == {"chi_dinh", "than_trong"} and len(
        [d for d in chuyen_mon if d.truong == "than_trong"]
    ) == 2
    assert all(
        d.noi_dung.startswith("Sản phẩm: ") and d.embedding is not None and len(d.embedding) == 1024 for d in chuyen_mon
    )
    assert all("giá" not in d.noi_dung.lower() for d in ds if d.san_pham_id)
    loai = {d.nguon_loai.value for d in ds}
    assert {"bai_viet", "chinh_sach"} <= loai and "faq" not in loai
    assert sum(1 for d in ds if d.nguon_loai.value == "bai_viet") == 1


async def test_dong_bo_lan_hai_bo_qua_doan_khong_doi_va_xoa_nguon_da_go(dang_nhap_admin, db):
    sp = await tao_san_pham(db, "thuoc_khong_ke_don")
    t = await _noi_dung(db, sp, chi_dinh="Chỉ định A")
    b = await _bai(db, "bai_viet", True)
    ban_dau = (await dang_nhap_admin.post(f"{TT}/dong-bo")).json()
    lai = (await dang_nhap_admin.post(f"{TT}/dong-bo")).json()
    assert (lai["them"], lai["sua"], lai["xoa"], lai["bo_qua"]) == (0, 0, 0, ban_dau["tong_doan"])
    t.chi_dinh = "Chỉ định B khác hẳn"
    b.dua_vao_ai = False
    await db.flush()
    kq = (await dang_nhap_admin.post(f"{TT}/dong-bo")).json()
    assert kq["sua"] >= 2 and kq["xoa"] == 1  # tổng quan + chỉ định đổi; bài bị gỡ
    sp.trang_thai = "ngung_kinh_doanh"
    await db.flush()
    kq = (await dang_nhap_admin.post(f"{TT}/dong-bo")).json()
    assert kq["xoa"] >= 2
    assert (await db.execute(select(TaiLieuTriThuc).where(TaiLieuTriThuc.san_pham_id == sp.id))).first() is None


async def test_doi_mo_hinh_tao_lai_vector_va_thong_ke(dang_nhap_admin, db, monkeypatch):
    sp = await tao_san_pham(db, "thuoc_khong_ke_don")
    await _noi_dung(db, sp, chi_dinh="Chỉ định")
    await dang_nhap_admin.post(f"{TT}/dong-bo")
    tk = (await dang_nhap_admin.get(TT)).json()
    assert tk["tong_doan"] >= 2 and tk["can_dong_bo_lai_vector"] is False and tk["theo_nguon"]["san_pham"] >= 2
    monkeypatch.setattr(embedding, "ten_mo_hinh", lambda: "mo-hinh-khac")
    assert (await dang_nhap_admin.get(TT)).json()["can_dong_bo_lai_vector"] is True
    kq = (await dang_nhap_admin.post(f"{TT}/dong-bo")).json()
    assert kq["sua"] == tk["tong_doan"] and kq["bo_qua"] == 0 and kq["mo_hinh"] == "mo-hinh-khac"


async def test_chi_admin_dong_bo(clients_theo_vai_tro):
    for v in ("PHARMACIST", "WAREHOUSE"):
        c = clients_theo_vai_tro[v]
        assert (await c.get(TT)).status_code == 403 and (await c.post(f"{TT}/dong-bo")).status_code == 403


# --- AD09 ---


async def test_cau_hinh_ai_doc_mac_dinh_sua_co_phien_ban_va_nhat_ky(dang_nhap_admin, db):
    d = (await dang_nhap_admin.get(CH)).json()
    assert (
        d["ai_module"]["chat"] is True
        and d["ai_nguong_chuyen_duoc_si"] == 0.6
        and "đau ngực" in d["ai_dau_hieu_nguy_hiem"]
    )
    moi = {**d["ai_module"], "chat": False}
    r = await dang_nhap_admin.put(
        CH,
        json={
            "phien_ban": d["phien_ban"],
            "ai_module": moi,
            "ai_nguong_chuyen_duoc_si": 0.7,
            "ai_dau_hieu_nguy_hiem": ["đau ngực", " đau ngực ", "ngộ độc"],
        },
    )
    assert r.status_code == 200, r.text
    c = r.json()
    assert (
        c["ai_module"]["chat"] is False
        and c["ai_nguong_chuyen_duoc_si"] == 0.7
        and c["ai_dau_hieu_nguy_hiem"] == ["đau ngực", "ngộ độc"]
    )
    assert c["phien_ban"] != d["phien_ban"] and c["ai_loi_nhac_bo_sung"] == d["ai_loi_nhac_bo_sung"]
    cu = await dang_nhap_admin.put(CH, json={"phien_ban": d["phien_ban"], "ai_loi_nhac_bo_sung": "Nhắc thêm"})
    assert cu.status_code == 409 and cu.json()["ma_loi"] == "DU_LIEU_DA_THAY_DOI"
    from app.modules.ai_quan_tri import cau_hinh_ai

    assert await cau_hinh_ai.module_bat(db, "chat") is False and await cau_hinh_ai.module_bat(db, "tim_kiem") is True


async def test_cau_hinh_ai_dau_vao_sai(dang_nhap_admin):
    d = (await dang_nhap_admin.get(CH)).json()
    for body in (
        {"ai_nguong_chuyen_duoc_si": 0},
        {"ai_nguong_chuyen_duoc_si": 1.5},
        {"ai_module": {"chat": True}},
        {"ai_dau_hieu_nguy_hiem": ["a"]},
        {"ai_loi_nhac_bo_sung": "x" * 2001},
        {"ai_la": 1},
    ):
        assert (await dang_nhap_admin.put(CH, json={"phien_ban": d["phien_ban"], **body})).status_code == 400, body


async def test_chi_admin_sua_cau_hinh_ai(clients_theo_vai_tro):
    for v in ("PHARMACIST", "WAREHOUSE"):
        c = clients_theo_vai_tro[v]
        assert (await c.get(CH)).status_code == 403 and (await c.put(CH, json={"phien_ban": "x"})).status_code == 403

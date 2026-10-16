"""KTV10, KTV15, DS11: đánh giá, hỏi đáp và kiểm duyệt (T6.4)."""

from sqlalchemy import select

from app.core import luu_tru
from app.models.khach_hang import DanhGia, HoiDap, ThongBao
from tests.conftest import _dang_nhap
from tests.doi_tra.test_doi_tra import PNG, _don_da_giao
from tests.factories import tao_khach

DG = "/api/v1/toi/danh-gia"
KD = "/api/v1/noi-bo/kiem-duyet"


async def _gui(c, ct, so_sao=5, **kw):
    return await c.post(DG, data={"ct_don_hang_id": ct.id, "so_sao": so_sao, **kw})


async def test_danh_gia_dong_don_da_giao_mot_lan_co_anh(dang_nhap_khach, db):
    khach = dang_nhap_khach.tai_khoan
    don, ct, sp = await _don_da_giao(db, khach)
    cho = (await dang_nhap_khach.get(f"{DG}/cho")).json()
    assert [d["ct_don_hang_id"] for d in cho] == [ct.id] and cho[0]["ma_don"] == don.ma_don
    r = await dang_nhap_khach.post(
        DG,
        data={"ct_don_hang_id": ct.id, "so_sao": 4, "noi_dung": "  Dùng tốt  "},
        files=[("tep", ("a.png", PNG, "image/png"))],
    )
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["so_sao"] == 4 and d["noi_dung"] == "Dùng tốt" and d["dang_hien"] is True and len(d["anh"]) == 1
    dg = (await db.execute(select(DanhGia))).scalars().one()
    assert dg.khach_hang_id == khach.id and dg.san_pham_id == sp.id and dg.anh[0].startswith("danh-gia/")
    assert await luu_tru.luu_tru().doc(dg.anh[0]) == PNG
    assert (await dang_nhap_khach.get(f"{DG}/cho")).json() == []
    assert [x["id"] for x in (await dang_nhap_khach.get(DG)).json()] == [dg.id]
    lai = await dang_nhap_khach.post(DG, data={"ct_don_hang_id": ct.id, "so_sao": 5})
    assert lai.status_code == 409 and lai.json()["ma_loi"] == "TRUNG_DU_LIEU"


async def test_danh_gia_dieu_kien_va_dau_vao(dang_nhap_khach, app, db):
    khach = dang_nhap_khach.tai_khoan
    don, ct, _ = await _don_da_giao(db, khach)
    for sai in (0, 6):
        assert (await dang_nhap_khach.post(DG, data={"ct_don_hang_id": ct.id, "so_sao": sai})).status_code == 400
    xau = await dang_nhap_khach.post(
        DG, data={"ct_don_hang_id": ct.id, "so_sao": 3}, files=[("tep", ("x.png", b"khong-phai-anh" * 4, "image/png"))]
    )
    assert xau.status_code == 400
    nhieu = await dang_nhap_khach.post(
        DG, data={"ct_don_hang_id": ct.id, "so_sao": 3}, files=[("tep", ("a.png", PNG, "image/png"))] * 4
    )
    assert nhieu.status_code == 400
    don.trang_thai = "dang_giao"
    await db.flush()
    chua = await dang_nhap_khach.post(DG, data={"ct_don_hang_id": ct.id, "so_sao": 5})
    assert chua.status_code == 409
    async for khac in _dang_nhap(app, await tao_khach(db), "khach"):
        assert (await khac.post(DG, data={"ct_don_hang_id": ct.id, "so_sao": 5})).status_code == 404
    assert (await db.execute(select(DanhGia))).first() is None


async def test_danh_gia_hien_tren_trang_san_pham_va_bi_an(dang_nhap_khach, dang_nhap_duoc_si, db):
    khach = dang_nhap_khach.tai_khoan
    _, ct, sp = await _don_da_giao(db, khach)
    dg_id = (await _gui(dang_nhap_khach, ct, 5, noi_dung="Rất tốt")).json()["id"]
    trang = (await dang_nhap_khach.get(f"/api/v1/san-pham/{sp.slug}")).json()
    assert trang["danh_gia"]["so_luong"] == 1 and trang["danh_gia"]["moi_nhat"][0]["noi_dung"] == "Rất tốt"
    r = await dang_nhap_duoc_si.put(f"{KD}/danh-gia/{dg_id}/hien-thi", json={"dang_hien": False})
    assert r.status_code == 200 and r.json()["dang_hien"] is False
    trang = (await dang_nhap_khach.get(f"/api/v1/san-pham/{sp.slug}")).json()
    assert trang["danh_gia"]["so_luong"] == 0
    assert (
        await dang_nhap_duoc_si.put(f"{KD}/danh-gia/{dg_id}/phan-hoi", json={"phan_hoi": "Cảm ơn bạn"})
    ).status_code == 200
    ds = (await dang_nhap_duoc_si.get(f"{KD}/danh-gia", params={"dang_hien": "false"})).json()
    assert ds["tong"] == 1 and ds["du_lieu"][0]["phan_hoi"] == "Cảm ơn bạn"
    assert (await dang_nhap_duoc_si.get(f"{KD}/danh-gia", params={"dang_hien": "true"})).json()["tong"] == 0
    assert (await dang_nhap_duoc_si.put(f"{KD}/danh-gia/999999/hien-thi", json={"dang_hien": True})).status_code == 404


async def test_hoi_dap_dat_cau_hoi_can_dang_nhap_va_tra_loi_co_thong_bao(
    dang_nhap_khach, dang_nhap_duoc_si, client, db
):
    khach = dang_nhap_khach.tai_khoan
    _, _, sp = await _don_da_giao(db, khach)
    url = f"/api/v1/san-pham/{sp.slug}/hoi-dap"
    assert (await client.post(url, json={"cau_hoi": "Dùng cho trẻ em được không?"})).status_code == 401
    assert (await dang_nhap_khach.post(url, json={"cau_hoi": "ngắn"})).status_code == 400
    r = await dang_nhap_khach.post(url, json={"cau_hoi": "  Dùng cho trẻ em được không?  "})
    assert r.status_code == 201, r.text
    hoi_id = r.json()["id"]
    cong_khai = (await client.get(url)).json()
    assert cong_khai["tong"] == 1 and cong_khai["du_lieu"][0]["tra_loi"] is None
    assert "ten_khach" not in cong_khai["du_lieu"][0] and cong_khai["du_lieu"][0]["ten_hien_thi"]
    chua = (await dang_nhap_duoc_si.get(f"{KD}/hoi-dap", params={"chua_tra_loi": "true"})).json()
    assert [h["id"] for h in chua["du_lieu"]] == [hoi_id]
    t = await dang_nhap_duoc_si.post(f"{KD}/hoi-dap/{hoi_id}/tra-loi", json={"tra_loi": "Trẻ trên 6 tuổi dùng được."})
    assert t.status_code == 200, t.text
    h = await db.get(HoiDap, hoi_id, populate_existing=True)
    assert h.tra_loi == "Trẻ trên 6 tuổi dùng được." and h.tra_loi_luc is not None and h.nhan_vien_tra_loi_id
    tb = (await db.execute(select(ThongBao).where(ThongBao.khach_hang_id == khach.id))).scalars().all()
    assert len(tb) == 1 and tb[0].loai == "hoi_dap" and tb[0].lien_ket == f"/san-pham/{sp.slug}"
    assert "Trẻ trên" not in (tb[0].noi_dung or "") + tb[0].tieu_de
    # Trả lời lần hai là sửa câu trả lời, không báo khách lần nữa.
    await dang_nhap_duoc_si.post(f"{KD}/hoi-dap/{hoi_id}/tra-loi", json={"tra_loi": "Trẻ trên 6 tuổi, 1 viên."})
    assert len((await db.execute(select(ThongBao).where(ThongBao.khach_hang_id == khach.id))).scalars().all()) == 1
    # Ẩn câu hỏi vi phạm.
    assert (
        await dang_nhap_duoc_si.put(f"{KD}/hoi-dap/{hoi_id}/hien-thi", json={"dang_hien": False})
    ).status_code == 200
    assert (await client.get(url)).json()["tong"] == 0


async def test_sua_xoa_cau_hoi_chi_khi_chua_tra_loi_va_cua_minh(dang_nhap_khach, dang_nhap_duoc_si, app, db):
    khach = dang_nhap_khach.tai_khoan
    _, _, sp = await _don_da_giao(db, khach)
    url = f"/api/v1/san-pham/{sp.slug}/hoi-dap"
    a = (await dang_nhap_khach.post(url, json={"cau_hoi": "Câu hỏi thứ nhất của tôi"})).json()["id"]
    b = (await dang_nhap_khach.post(url, json={"cau_hoi": "Câu hỏi thứ hai của tôi"})).json()["id"]
    async for khac in _dang_nhap(app, await tao_khach(db), "khach"):
        assert (await khac.put(f"/api/v1/toi/hoi-dap/{a}", json={"cau_hoi": "Đã bị sửa trộm"})).status_code == 404
        assert (await khac.delete(f"/api/v1/toi/hoi-dap/{a}")).status_code == 404
        assert (await khac.get("/api/v1/toi/hoi-dap")).json() == []
    s = await dang_nhap_khach.put(f"/api/v1/toi/hoi-dap/{a}", json={"cau_hoi": "Câu hỏi đã sửa lại"})
    assert s.status_code == 200 and s.json()["cau_hoi"] == "Câu hỏi đã sửa lại"
    await dang_nhap_duoc_si.post(f"{KD}/hoi-dap/{b}/tra-loi", json={"tra_loi": "Đã trả lời rồi"})
    assert (
        await dang_nhap_khach.put(f"/api/v1/toi/hoi-dap/{b}", json={"cau_hoi": "Sửa sau khi trả lời"})
    ).status_code == 409
    assert (await dang_nhap_khach.delete(f"/api/v1/toi/hoi-dap/{b}")).status_code == 409
    assert (await dang_nhap_khach.delete(f"/api/v1/toi/hoi-dap/{a}")).status_code == 204
    assert [h["id"] for h in (await dang_nhap_khach.get("/api/v1/toi/hoi-dap")).json()] == [b]


async def test_gioi_han_cau_hoi_moi_ngay_va_san_pham_la(dang_nhap_khach, client, db):
    _, _, sp = await _don_da_giao(db, dang_nhap_khach.tai_khoan)
    url = f"/api/v1/san-pham/{sp.slug}/hoi-dap"
    for i in range(10):
        assert (await dang_nhap_khach.post(url, json={"cau_hoi": f"Câu hỏi số {i} về sản phẩm"})).status_code == 201
    r = await dang_nhap_khach.post(url, json={"cau_hoi": "Câu hỏi thứ mười một"})
    assert r.status_code == 429 and r.json()["ma_loi"] == "QUA_GIOI_HAN"
    assert (await client.get("/api/v1/san-pham/khong-co-san-pham-nay/hoi-dap")).status_code == 404
    assert (
        await dang_nhap_khach.post("/api/v1/san-pham/khong-co/hoi-dap", json={"cau_hoi": "Hỏi sản phẩm lạ"})
    ).status_code == 404


async def test_chi_duoc_si_kiem_duyet(dang_nhap_khach, clients_theo_vai_tro, db):
    _, ct, _ = await _don_da_giao(db, dang_nhap_khach.tai_khoan)
    dg_id = (await _gui(dang_nhap_khach, ct, 2)).json()["id"]
    for vai_tro in ("WAREHOUSE", "ADMIN"):
        c = clients_theo_vai_tro[vai_tro]
        assert (await c.get(f"{KD}/danh-gia")).status_code in (401, 403)
        assert (await c.put(f"{KD}/danh-gia/{dg_id}/hien-thi", json={"dang_hien": False})).status_code in (401, 403)
        assert (await c.get(f"{KD}/hoi-dap")).status_code in (401, 403)
    assert (await clients_theo_vai_tro["PHARMACIST"].get(f"{KD}/danh-gia")).status_code == 200

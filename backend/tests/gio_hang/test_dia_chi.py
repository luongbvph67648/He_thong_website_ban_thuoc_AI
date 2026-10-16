"""KTV01: sổ địa chỉ. Đúng một địa chỉ mặc định; mã tỉnh/xã theo danh mục; dữ liệu của khách khác là 404."""

from sqlalchemy import select

from app.core.bao_mat import tao_access_token
from app.models.khach_hang import DiaChi
from tests.factories import tao_khach

DC = "/api/v1/toi/dia-chi"


def moi(**kw):
    return {
        "ten_nguoi_nhan": "Nguyễn Văn A",
        "so_dien_thoai": "0912345678",
        "dia_chi_chi_tiet": "12 Phố Huế",
        "ma_tinh": "201",
        "ma_phuong_xa": "2010101",
        **kw,
    }


async def so_mac_dinh(c):
    return [d["id"] for d in (await c.get(DC)).json() if d["la_mac_dinh"]]


async def test_dia_chi_dau_tien_tu_la_mac_dinh_va_ten_lay_tu_danh_muc(dang_nhap_khach):
    c = dang_nhap_khach
    r = await c.post(DC, json=moi())
    assert r.status_code == 201
    d = r.json()
    assert d["la_mac_dinh"] is True and d["ten_tinh"] == "Hà Nội" and d["ten_phuong_xa"] == "Phường Hoàn Kiếm"
    d2 = (await c.post(DC, json=moi(ma_tinh="202", ma_phuong_xa="2020101"))).json()
    assert d2["la_mac_dinh"] is False and await so_mac_dinh(c) == [d["id"]]


async def test_dat_mac_dinh_moi_bo_mac_dinh_cu_va_xoa_mac_dinh_thi_chuyen(dang_nhap_khach):
    c = dang_nhap_khach
    a = (await c.post(DC, json=moi())).json()["id"]
    b = (await c.post(DC, json=moi(la_mac_dinh=True))).json()["id"]
    assert await so_mac_dinh(c) == [b]
    assert (await c.post(f"{DC}/{a}/mac-dinh")).status_code == 200 and await so_mac_dinh(c) == [a]
    d = (await c.post(DC, json=moi())).json()["id"]
    assert (await c.delete(f"{DC}/{a}")).status_code == 204
    assert await so_mac_dinh(c) == [b]  # cũ nhất còn lại
    for i in (b, d):
        await c.delete(f"{DC}/{i}")
    assert (await c.get(DC)).json() == []


async def test_sua_dia_chi_cap_nhat_ten_theo_ma_moi(dang_nhap_khach):
    c = dang_nhap_khach
    a = (await c.post(DC, json=moi())).json()["id"]
    r = (await c.put(f"{DC}/{a}", json=moi(ma_tinh="203", ma_phuong_xa="2030102", ten_nguoi_nhan="  Trần  B "))).json()
    assert r["ten_tinh"] == "Đà Nẵng" and r["ten_phuong_xa"] == "Phường Thanh Khê" and r["ten_nguoi_nhan"] == "Trần B"
    assert r["la_mac_dinh"] is True


async def test_ma_tinh_xa_sai_va_du_lieu_khong_hop_le_la_400(dang_nhap_khach):
    c = dang_nhap_khach
    r = await c.post(DC, json=moi(ma_tinh="999"))
    assert r.status_code == 400 and r.json()["chi_tiet"][0]["truong"] == "ma_tinh"
    r = await c.post(DC, json=moi(ma_phuong_xa="2020101"))  # xã của tỉnh khác
    assert r.status_code == 400 and r.json()["chi_tiet"][0]["truong"] == "ma_phuong_xa"
    assert (await c.post(DC, json=moi(so_dien_thoai="123"))).status_code == 400
    assert (await c.post(DC, json=moi(dia_chi_chi_tiet="a"))).status_code == 400
    assert (await c.post(DC, json={**moi(), "ten_tinh": "Giả"})).status_code == 400  # không nhận tên từ client
    assert (await c.post(DC, json={**moi(), "khach_hang_id": 1})).status_code == 400


async def test_toi_da_10_dia_chi(dang_nhap_khach):
    c = dang_nhap_khach
    for _ in range(10):
        assert (await c.post(DC, json=moi())).status_code == 201
    assert (await c.post(DC, json=moi())).status_code == 400


async def test_khach_khac_khong_thay_hay_sua_duoc_la_404(client, dang_nhap_khach, db):
    a = (await dang_nhap_khach.post(DC, json=moi())).json()["id"]
    h = {"Authorization": f"Bearer {tao_access_token((await tao_khach(db)).id, 'khach')}"}
    assert (await client.get(DC, headers=h)).json() == []
    assert (await client.put(f"{DC}/{a}", json=moi(), headers=h)).status_code == 404
    assert (await client.post(f"{DC}/{a}/mac-dinh", headers=h)).status_code == 404
    assert (await client.delete(f"{DC}/{a}", headers=h)).status_code == 404
    assert (await client.get(DC)).status_code == 401
    assert len((await db.execute(select(DiaChi))).scalars().all()) == 1


async def test_danh_muc_dia_gioi_cong_khai(client):
    tinh = (await client.get("/api/v1/dia-gioi/tinh")).json()
    assert {"ma": "201", "ten": "Hà Nội"} in tinh
    xa = (await client.get("/api/v1/dia-gioi/tinh/201/xa")).json()
    assert {"ma": "2010101", "ten": "Phường Hoàn Kiếm"} in xa
    assert (await client.get("/api/v1/dia-gioi/tinh/000/xa")).status_code == 404

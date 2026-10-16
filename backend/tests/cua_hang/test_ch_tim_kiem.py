"""KVL04 (T2.5): tìm kiếm từ khóa không dấu, gõ sai, theo tiền tố, theo hoạt chất; gợi ý; xếp hạng; lịch sử tìm kiếm."""

from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.core.gioi_han import GioiHanCuaSoTruot, lay_bo_gioi_han_tim_kiem
from app.core.thoi_gian import bay_gio_utc
from app.models.ai import LichSuTimKiem
from app.models.san_pham import HoatChat, ThanhPhan
from app.modules.cua_hang import router as router_cua_hang
from app.modules.cua_hang.tim_kiem import chuan_hoa_tu_khoa
from tests.cua_hang.mau_cua_hang import GOC, dat_ban_chay, sp_ban_duoc, ten_the
from tests.factories import tao_danh_muc


async def tim(client, q, **tham_so):
    return await client.get(f"{GOC}/tim-kiem", params={"q": q, **tham_so})


async def goi_y(client, q):
    return await client.get(f"{GOC}/tim-kiem/goi-y", params={"q": q})


async def hoat_chat(db, ten, ten_khac=None) -> HoatChat:
    hc = HoatChat(ten=ten, ten_khac=ten_khac)
    db.add(hc)
    await db.flush()
    return hc


# --- Khớp -------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("q", "ten_mong_doi"),
    [
        ("para", "Paracetamol 500mg"),  # tiền tố
        ("paracetmol", "Paracetamol 500mg"),  # gõ sai
        ("PARACETAMOL", "Paracetamol 500mg"),  # hoa
        ("  paracetamol   500  ", "Paracetamol 500mg"),  # khoảng trắng thừa
        ("bo phe", "Thuốc ho Bổ phế"),  # không dấu
        ("Bổ phế", "Thuốc ho Bổ phế"),  # có dấu
        ("thuoc ho", "Thuốc ho Bổ phế"),
    ],
)
async def test_tim_khong_dau_sai_chinh_ta_theo_tien_to(client, db, q, ten_mong_doi):
    await sp_ban_duoc(db, "Paracetamol 500mg")
    await sp_ban_duoc(db, "Thuốc ho Bổ phế")
    await sp_ban_duoc(db, "Vitamin C 1000mg")
    phan_hoi = await tim(client, q)
    assert phan_hoi.status_code == 200, phan_hoi.text
    assert ten_mong_doi in ten_the(phan_hoi), ten_the(phan_hoi)
    assert "Vitamin C 1000mg" not in ten_the(phan_hoi)


async def test_tim_theo_hoat_chat_va_ten_khac(client, db):
    para = await hoat_chat(db, "Paracetamol", "Acetaminophen, APAP")
    panadol = await sp_ban_duoc(db, "Panadol Extra")  # tên thương mại không chứa chữ "paracetamol"
    db.add(ThanhPhan(san_pham_id=panadol.id, hoat_chat_id=para.id, ham_luong="500mg"))
    await sp_ban_duoc(db, "Vitamin C")
    await db.flush()
    for q in ("paracetamol", "paracetmol", "acetaminophen", "Acetaminofen"):
        assert ten_the(await tim(client, q)) == ["Panadol Extra"], q


async def test_khong_co_ket_qua_khong_khop_linh_tinh(client, db):
    await sp_ban_duoc(db, "Paracetamol 500mg")
    phan_hoi = await tim(client, "zzzzqqq")
    assert phan_hoi.json() == {"du_lieu": [], "tong": 0, "trang": 1, "kich_thuoc": 20}


@pytest.mark.parametrize("q", ["%", "_", "\\", "%%%", "a%", "' OR 1=1 --", "para%", "<script>", "(", ")", "&|!:*"])
async def test_ky_tu_dac_biet_khong_gay_loi_va_khong_khop_het(client, db, q):
    await sp_ban_duoc(db, "Paracetamol 500mg")
    phan_hoi = await tim(client, q)
    assert phan_hoi.status_code == 200, (q, phan_hoi.text)
    assert (
        "Paracetamol 500mg" not in ten_the(phan_hoi) or q == "para%"
    )  # "%" là ký tự thường, không phải ký tự thay thế
    assert (await goi_y(client, q)).status_code == 200


async def test_tu_khoa_ngan_hoac_rong_tra_rong_va_khong_ghi_lich_su(client, db):
    await sp_ban_duoc(db, "Paracetamol 500mg")
    for q in ("", " ", "p", " p "):
        phan_hoi = await tim(client, q, **{})
        assert phan_hoi.status_code == 200 and phan_hoi.json()["tong"] == 0, repr(q)
        assert (await goi_y(client, q)).json() == []
    assert (await db.scalar(select(func.count()).select_from(LichSuTimKiem))) == 0


async def test_tham_so_sai_la_400(client, db):
    for sai in ({"q": "a\x00b"}, {"q": "a" * 301}, {"q": "para", "trang": 0}, {"q": "para", "kich_thuoc": 101}):
        phan_hoi = await client.get(f"{GOC}/tim-kiem", params=sai)
        assert phan_hoi.status_code == 400 and phan_hoi.json()["ma_loi"] == "DU_LIEU_KHONG_HOP_LE", sai
    assert (await client.get(f"{GOC}/tim-kiem/goi-y", params={"q": "a\x00b"})).status_code == 400


def test_chuan_hoa_tu_khoa():
    assert chuan_hoa_tu_khoa("  Para \t cetamol\n 500  ") == "Para cetamol 500"
    assert chuan_hoa_tu_khoa(None) == "" and chuan_hoa_tu_khoa("   ") == ""
    assert len(chuan_hoa_tu_khoa("a" * 250)) == 100


# --- Phạm vi hiển thị -----------------------------------------------------------------------------------------------


async def test_khong_tim_thay_san_pham_an_da_xoa_ngung_hoac_trong_nhanh_an(client, db):
    an = await tao_danh_muc(db, "Ẩn", dang_hien_thi=False)
    con_an = await tao_danh_muc(db, "Con của ẩn", cha=an)
    await sp_ban_duoc(db, "Aspirin hiện")
    await sp_ban_duoc(db, "Aspirin ngừng", trang_thai="ngung_kinh_doanh")
    await sp_ban_duoc(db, "Aspirin xóa", ton=0, deleted_at=bay_gio_utc())
    await sp_ban_duoc(db, "Aspirin ở danh mục ẩn", danh_muc_id=an.id)
    await sp_ban_duoc(db, "Aspirin ở danh mục con của ẩn", danh_muc_id=con_an.id)
    assert ten_the(await tim(client, "aspirin")) == ["Aspirin hiện"]
    assert [g["ten"] for g in (await goi_y(client, "aspirin")).json()] == ["Aspirin hiện"]


async def test_thuoc_ke_don_van_co_trong_ket_qua_kem_can_tu_van(client, db):
    await sp_ban_duoc(db, "Amoxicillin 500mg", loai="thuoc_ke_don")
    the = (await tim(client, "amoxicillin")).json()["du_lieu"][0]
    assert the["can_tu_van"] is True and the["loai_san_pham"] == "thuoc_ke_don"
    gy = (await goi_y(client, "amoxicillin")).json()[0]
    assert gy["can_tu_van"] is True and gy["kieu"] == "san_pham"


# --- Xếp hạng --------------------------------------------------------------------------------------------------------


async def test_xep_hang_do_khop_roi_con_hang_roi_ban_chay(client, db):
    khop_kem = await sp_ban_duoc(db, "Paracetamol 500mg viên nén bao phim dài dòng")  # cùng điểm mức 1,0
    het = await sp_ban_duoc(db, "Paracetamol 650mg", ton=0)
    con_it = await sp_ban_duoc(db, "Paracetamol 500mg")
    con_nhieu = await sp_ban_duoc(db, "Paracetamol 250mg")
    await dat_ban_chay(db, con_nhieu, 3)
    await dat_ban_chay(db, het, 9)  # bán chạy nhất nhưng hết hàng: vẫn xếp sau mọi sản phẩm còn hàng cùng độ khớp
    await dat_ban_chay(db, con_it, 1)
    ten = ten_the(await tim(client, "paracetamol"))
    assert ten.index("Paracetamol 250mg") < ten.index("Paracetamol 500mg")  # cùng còn hàng: bán chạy trước
    assert ten.index("Paracetamol 500mg") < ten.index("Paracetamol 650mg")  # còn hàng trước hết hàng
    assert ten[-1] == "Paracetamol 650mg"
    assert khop_kem.ten in ten


async def test_do_khop_cao_xep_truoc_du_het_hang_va_it_ban(client, db):
    gan_dung = await sp_ban_duoc(db, "Loratadin 10mg", ton=0)  # khớp 1,0 nhưng hết hàng
    await sp_ban_duoc(db, "Loratadine Plus Extra Strength Forte")  # khớp thấp hơn nhưng còn hàng
    ten = ten_the(await tim(client, "loratadin"))
    assert ten[0] == gan_dung.ten, ten


async def test_phan_trang_on_dinh_va_tong(client, db):
    for i in range(7):
        await sp_ban_duoc(db, f"Vitamin C {i}")
    thay = []
    for trang in (1, 2, 3):
        phan_hoi = await tim(client, "vitamin", trang=trang, kich_thuoc=3)
        assert phan_hoi.json()["tong"] == 7 and phan_hoi.json()["trang"] == trang
        thay += ten_the(phan_hoi)
    assert len(thay) == 7 and len(set(thay)) == 7


async def test_ket_qua_co_gia_va_con_hang_nhu_danh_sach(client, db):
    sp = await sp_ban_duoc(
        db, "Kẽm gluconat", don_vi=[{"ten_don_vi": "lọ", "he_so": 1, "gia_ban": 45000, "la_mac_dinh": True}]
    )
    the = (await tim(client, "kem")).json()["du_lieu"][0]
    assert (the["id"], the["gia"], the["ten_don_vi_gia"], the["con_hang"]) == (sp.id, "45000.00", "lọ", True)
    assert sp.id


# --- Gợi ý ------------------------------------------------------------------------------------------------------------


async def test_goi_y_toi_da_8_san_pham_truoc_hoat_chat_sau(client, db):
    para = await hoat_chat(db, "Paracetamol")
    para_codein = await hoat_chat(db, "Paracetamol codein")
    sp_dau = await sp_ban_duoc(db, "Paracetamol 0")
    for i in range(1, 12):
        sp = await sp_ban_duoc(db, f"Paracetamol {i}")
        db.add(ThanhPhan(san_pham_id=sp.id, hoat_chat_id=para.id))
    db.add(ThanhPhan(san_pham_id=sp_dau.id, hoat_chat_id=para.id))
    db.add(ThanhPhan(san_pham_id=sp_dau.id, hoat_chat_id=para_codein.id))
    await db.flush()
    gy = (await goi_y(client, "parac")).json()
    assert len(gy) == 8
    assert [g["kieu"] for g in gy] == ["san_pham"] * 6 + ["hoat_chat"] * 2
    assert gy[-2] == {
        "kieu": "hoat_chat",
        "ten": "Paracetamol",
        "slug": None,
        "loai_san_pham": None,
        "can_tu_van": False,
    }
    assert gy[-1]["ten"] == "Paracetamol codein"
    assert all(g["slug"] for g in gy[:6])


async def test_goi_y_hoat_chat_chi_khi_co_san_pham_hien_thi(client, db):
    mo_coi = await hoat_chat(db, "Ibuprofen")  # không sản phẩm nào chứa
    an = await sp_ban_duoc(db, "Nurofen", trang_thai="ngung_kinh_doanh")
    db.add(ThanhPhan(san_pham_id=an.id, hoat_chat_id=mo_coi.id))
    await db.flush()
    assert (await goi_y(client, "ibuprofen")).json() == []


# --- Lịch sử tìm kiếm -----------------------------------------------------------------------------------------------


async def lich_su(db):
    return list((await db.execute(select(LichSuTimKiem).order_by(LichSuTimKiem.id))).scalars())


async def test_ghi_lich_su_theo_ma_phien_che_do_tu_khoa_va_so_ket_qua(client, db):
    await sp_ban_duoc(db, "Paracetamol 500mg")
    phan_hoi = await client.get(f"{GOC}/tim-kiem", params={"q": "  Para  "}, headers={"X-Ma-Phien": "phien-tim-001"})
    assert phan_hoi.status_code == 200
    dong = await lich_su(db)
    assert len(dong) == 1
    assert (dong[0].tu_khoa, dong[0].che_do, dong[0].so_ket_qua) == ("Para", "tu_khoa", 1)
    assert (dong[0].ma_phien, dong[0].khach_hang_id) == ("phien-tim-001", None)
    await client.get(f"{GOC}/tim-kiem", params={"q": "khong-co-gi-ca"}, headers={"X-Ma-Phien": "phien-tim-001"})
    assert [(d.tu_khoa, d.so_ket_qua) for d in await lich_su(db)] == [("Para", 1), ("khong-co-gi-ca", 0)]


async def test_khach_dang_nhap_ghi_theo_token_bo_qua_ma_phien_gia(dang_nhap_khach, db):
    await sp_ban_duoc(db, "Paracetamol 500mg")
    await dang_nhap_khach.get(f"{GOC}/tim-kiem", params={"q": "para"}, headers={"X-Ma-Phien": "phien-cua-nguoi-khac"})
    dong = await lich_su(db)
    assert len(dong) == 1 and dong[0].khach_hang_id == dang_nhap_khach.tai_khoan.id and dong[0].ma_phien is None


async def test_khong_co_ma_phien_van_ghi_de_thong_ke_nhung_khong_gan_nguoi(client, db):
    await sp_ban_duoc(db, "Paracetamol 500mg")
    await tim(client, "para")
    dong = await lich_su(db)
    assert len(dong) == 1 and dong[0].khach_hang_id is None and dong[0].ma_phien is None


async def test_chi_ghi_o_trang_1_va_cung_tu_khoa_trong_30_phut_chi_mot_dong(client, db):
    for i in range(5):
        await sp_ban_duoc(db, f"Vitamin C {i}")
    dau = {"X-Ma-Phien": "phien-tim-002"}
    await client.get(f"{GOC}/tim-kiem", params={"q": "vitamin", "kich_thuoc": 2, "trang": 2}, headers=dau)
    assert await lich_su(db) == []  # đổi trang không phải tìm mới
    for q in ("vitamin", "VITAMIN", "vitamin"):
        await client.get(f"{GOC}/tim-kiem", params={"q": q}, headers=dau)
    assert len(await lich_su(db)) == 1
    await client.get(f"{GOC}/tim-kiem", params={"q": "vitamin"}, headers={"X-Ma-Phien": "phien-tim-khac"})
    assert len(await lich_su(db)) == 2  # người khác: dòng riêng
    for d in await lich_su(db):
        d.created_at = bay_gio_utc() - timedelta(minutes=31)
    await db.flush()
    await client.get(f"{GOC}/tim-kiem", params={"q": "vitamin"}, headers=dau)
    assert len(await lich_su(db)) == 3


async def test_goi_y_khong_ghi_lich_su(client, db):
    await sp_ban_duoc(db, "Paracetamol 500mg")
    assert len((await goi_y(client, "paracetamol")).json()) == 1
    assert await lich_su(db) == []


async def test_vuot_gioi_han_ghi_van_tra_ket_qua_nhung_khong_ghi(client, app, db):
    await sp_ban_duoc(db, "Paracetamol 500mg")
    bo = GioiHanCuaSoTruot()
    app.dependency_overrides[lay_bo_gioi_han_tim_kiem] = lambda: bo
    toi_da = router_cua_hang.GHI_TIM_TOI_DA_MOI_IP
    for i in range(toi_da + 5):
        phan_hoi = await tim(client, f"para {i:04d}")
        assert phan_hoi.status_code == 200
    assert len(await lich_su(db)) == toi_da


async def test_tim_kiem_la_cong_khai_khong_lo_truong_noi_bo(client, db):
    sp = await sp_ban_duoc(db, "Paracetamol 500mg", ton_toi_thieu=5)
    the = (await tim(client, "para")).json()["du_lieu"][0]
    assert the["id"] == sp.id
    for noi_bo in ("sku", "ton_toi_thieu", "trang_thai", "deleted_at"):
        assert noi_bo not in the

"""T7.7: AI07 (tương tự, dành cho bạn) và AI08 (luật mua kèm). Bộ lọc an toàn: không thuốc kê đơn, không hoạt chất dị ứng."""

import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select

from app.ai import embedding
from app.core.thoi_gian import bay_gio_utc
from app.jobs.__main__ import LICH_TUAN
from app.jobs.cong_viec import ai08_luat_mua_kem
from app.models.ai import LichSuXem, LuatMuaKem, TaiLieuTriThuc
from app.models.he_thong import CauHinh
from app.models.khach_hang import DiUng, HoSoSucKhoe
from app.models.san_pham import HoatChat, ThanhPhan
from app.modules.cua_hang import goi_y
from tests.cua_hang.mau_cua_hang import GOC, dat_ban_chay, sp_ban_duoc
from tests.factories import tao_danh_muc, tao_don, tao_khach

DANH_CHO_BAN = f"{GOC}/goi-y/danh-cho-ban"


async def hoat_chat(db, ten="HC"):
    h = HoatChat(ten=f"{ten}-{uuid.uuid4().hex[:6]}")
    db.add(h)
    await db.flush()
    return h


async def gan(db, sp, *hc):
    db.add_all([ThanhPhan(san_pham_id=sp.id, hoat_chat_id=h.id) for h in hc])
    await db.flush()


async def tat_goi_y(db):
    gia_tri = dict.fromkeys(("tim_kiem", "chat", "tra_anh", "doc_don_thuoc", "du_bao"), True) | {"goi_y": False}
    cu = await db.get(CauHinh, "ai_module")
    if cu is None:
        db.add(CauHinh(khoa="ai_module", gia_tri=gia_tri))
    else:
        cu.gia_tri = gia_tri
    await db.flush()


async def vector_tong_quan(db, sp, van_ban, *, ke_don=False):
    (vec,) = await embedding.embed([van_ban])
    db.add(
        TaiLieuTriThuc(
            nguon_loai="san_pham", nguon_id=sp.id, san_pham_id=sp.id, truong="tong_quan", noi_dung=van_ban,
            metadata_={"can_ke_don": ke_don, "san_pham_id": sp.id}, embedding=vec,
            mo_hinh_embedding=embedding.ten_mo_hinh(), hash_noi_dung=uuid.uuid4().hex,
        )
    )  # fmt: skip
    await db.flush()


async def ten(db, sp, khach=None, hc_ids=()):
    return [t.ten for t in await goi_y.san_pham_tuong_tu(db, sp, list(hc_ids), khach)]


# --- AI07: tương tự ---


async def test_tuong_tu_theo_tang_cung_tap_hoat_chat_roi_danh_muc_roi_vector(db):
    h1, h2 = await hoat_chat(db), await hoat_chat(db)
    dm = await tao_danh_muc(db, "Cùng")
    goc = await sp_ban_duoc(db, "Gốc", danh_muc_id=dm.id)
    await gan(db, goc, h1, h2)
    cung_tap = await sp_ban_duoc(db, "CùngTập")
    await gan(db, cung_tap, h1, h2)
    chi_chung_mot = await sp_ban_duoc(db, "ChungMột")
    await gan(db, chi_chung_mot, h1)
    thua = await sp_ban_duoc(db, "ThừaHoạtChất")  # có cả h1, h2 và thêm h3: không phải CÙNG TẬP
    await gan(db, thua, h1, h2, await hoat_chat(db))
    await sp_ban_duoc(db, "CùngDanhMục", danh_muc_id=dm.id)
    gan_vector = await sp_ban_duoc(db, "GầnVector")
    xa_vector = await sp_ban_duoc(db, "XaVector")
    await vector_tong_quan(db, goc, "Gốc giảm đau hạ sốt paracetamol viên nén")
    await vector_tong_quan(db, gan_vector, "Gần giảm đau hạ sốt paracetamol viên nén")
    await vector_tong_quan(db, xa_vector, "kem dưỡng da chống nắng mỹ phẩm trắng sáng")
    ds = await ten(db, goc, hc_ids=[h1.id, h2.id])
    assert ds[:3] == ["CùngTập", "CùngDanhMục", "GầnVector"]
    assert "XaVector" not in ds and "ChungMột" not in ds and "ThừaHoạtChất" not in ds and "Gốc" not in ds


async def test_trong_tang_xep_ban_chay_truoc(db):
    dm = await tao_danh_muc(db, "Cùng")
    goc = await sp_ban_duoc(db, "Gốc", danh_muc_id=dm.id)
    it, nhieu = await sp_ban_duoc(db, "Ít", danh_muc_id=dm.id), await sp_ban_duoc(db, "Nhiều", danh_muc_id=dm.id)
    await dat_ban_chay(db, it, 1)
    await dat_ban_chay(db, nhieu, 3)
    assert await ten(db, goc) == ["Nhiều", "Ít"]


async def test_tuong_tu_khong_bao_gio_co_thuoc_ke_don_ke_ca_qua_vector(db):
    h = await hoat_chat(db)
    dm = await tao_danh_muc(db, "Cùng")
    goc = await sp_ban_duoc(db, "Gốc", danh_muc_id=dm.id)
    await gan(db, goc, h)
    ke_don = await sp_ban_duoc(db, "KêĐơn", loai="thuoc_ke_don", danh_muc_id=dm.id)
    await gan(db, ke_don, h)
    ke_don2 = await sp_ban_duoc(db, "KêĐơnVector", loai="thuoc_ke_don")
    await vector_tong_quan(db, goc, "giảm đau hạ sốt paracetamol")
    await vector_tong_quan(
        db, ke_don2, "giảm đau hạ sốt paracetamol", ke_don=False
    )  # cờ metadata sai vẫn bị chặn ở SQL
    assert await ten(db, goc, hc_ids=[h.id]) == []


async def test_tuong_tu_loai_hoat_chat_di_ung_khi_khach_dong_y(db):
    di_ung = await hoat_chat(db, "DiUng")
    dm = await tao_danh_muc(db, "Cùng")
    goc = await sp_ban_duoc(db, "Gốc", danh_muc_id=dm.id)
    an_toan = await sp_ban_duoc(db, "AnToàn", danh_muc_id=dm.id)
    nguy_co = await sp_ban_duoc(db, "NguyCơ", danh_muc_id=dm.id)
    gan_vec = await sp_ban_duoc(db, "NguyCơVector")
    await gan(db, nguy_co, di_ung)
    await gan(db, gan_vec, di_ung)
    await vector_tong_quan(db, goc, "thuốc giảm đau hạ sốt")
    await vector_tong_quan(db, gan_vec, "thuốc giảm đau hạ sốt")
    khach = await tao_khach(db)
    db.add(HoSoSucKhoe(khach_hang_id=khach.id, dong_y_su_dung=True))
    db.add(DiUng(khach_hang_id=khach.id, hoat_chat_id=di_ung.id))
    await db.flush()
    assert await ten(db, goc, khach) == ["AnToàn"]
    assert set(await ten(db, goc, None)) == {"AnToàn", "NguyCơ", "NguyCơVector"}  # vãng lai: không có dữ liệu để lọc
    khach2 = await tao_khach(db)  # có dị ứng nhưng KHÔNG đồng ý dùng hồ sơ: không dùng dữ liệu đó
    db.add(HoSoSucKhoe(khach_hang_id=khach2.id, dong_y_su_dung=False))
    await db.flush()
    assert "NguyCơ" in await ten(db, goc, khach2) and an_toan.id


async def test_module_goi_y_tat_bo_tang_vector_nhung_van_co_goi_y_co_ban(db):
    dm = await tao_danh_muc(db, "Cùng")
    goc = await sp_ban_duoc(db, "Gốc", danh_muc_id=dm.id)
    cung = await sp_ban_duoc(db, "CùngDanhMục", danh_muc_id=dm.id)
    gan_vec = await sp_ban_duoc(db, "GầnVector")
    await vector_tong_quan(db, goc, "thuốc ho thảo dược")
    await vector_tong_quan(db, gan_vec, "thuốc ho thảo dược")
    assert await ten(db, goc) == ["CùngDanhMục", "GầnVector"]
    await tat_goi_y(db)
    assert await ten(db, goc) == ["CùngDanhMục"] and cung.id


async def test_chi_tiet_san_pham_tra_tuong_tu_theo_khach_dang_nhap(dang_nhap_khach, db):
    di_ung = await hoat_chat(db, "DiUng")
    dm = await tao_danh_muc(db, "Cùng")
    goc = await sp_ban_duoc(db, "Gốc", danh_muc_id=dm.id)
    nguy_co = await sp_ban_duoc(db, "NguyCơ", danh_muc_id=dm.id)
    await sp_ban_duoc(db, "AnToàn", danh_muc_id=dm.id)
    await gan(db, nguy_co, di_ung)
    khach = dang_nhap_khach.tai_khoan
    db.add(HoSoSucKhoe(khach_hang_id=khach.id, dong_y_su_dung=True))
    db.add(DiUng(khach_hang_id=khach.id, hoat_chat_id=di_ung.id))
    await db.flush()
    r = await dang_nhap_khach.get(f"{GOC}/san-pham/{goc.slug}")
    assert [t["ten"] for t in r.json()["tuong_tu"]] == ["AnToàn"]


# --- AI07: dành cho bạn ---


async def xem(db, sp, *, khach=None, ma_phien=None, ngay=1):
    db.add(
        LichSuXem(
            khach_hang_id=None if khach is None else khach.id, ma_phien=ma_phien, san_pham_id=sp.id,
            created_at=bay_gio_utc() - timedelta(days=ngay),
        )
    )  # fmt: skip
    await db.flush()


async def test_danh_cho_ban_theo_danh_muc_da_xem_ban_chay_chua_mua(dang_nhap_khach, db):
    khach = dang_nhap_khach.tai_khoan
    dm_xem, dm_khac, dm_cu = [await tao_danh_muc(db, t) for t in ("Đã xem", "Khác", "Xem cũ")]
    da_xem = await sp_ban_duoc(db, "ĐãXem", danh_muc_id=dm_xem.id)
    ban_chay = await sp_ban_duoc(db, "BánChạy", danh_muc_id=dm_xem.id)
    it_ban = await sp_ban_duoc(db, "ÍtBán", danh_muc_id=dm_xem.id)
    da_mua = await sp_ban_duoc(db, "ĐãMua", danh_muc_id=dm_xem.id)
    ke_don = await sp_ban_duoc(db, "KêĐơn", loai="thuoc_ke_don", danh_muc_id=dm_xem.id)
    ngoai = await sp_ban_duoc(db, "NgoàiDanhMục", danh_muc_id=dm_khac.id)
    cu = await sp_ban_duoc(db, "DanhMụcXemCũ", danh_muc_id=dm_cu.id)
    sp_cu = await sp_ban_duoc(db, "ĐãXemCũ", danh_muc_id=dm_cu.id)
    await dat_ban_chay(db, ban_chay, 3)
    await dat_ban_chay(db, it_ban, 1)
    await dat_ban_chay(db, ngoai, 9)
    await dat_ban_chay(db, ke_don, 9)
    await tao_don(db, khach, "hoan_tat", dong=[{"san_pham": da_mua, "so_luong": 1}])
    await tao_don(db, khach, "da_huy", dong=[{"san_pham": it_ban, "so_luong": 1}])  # đơn hủy không tính là đã mua
    await xem(db, da_xem, khach=khach)
    await xem(db, sp_cu, khach=khach, ngay=45)  # quá 30 ngày
    ten_ds = [t["ten"] for t in (await dang_nhap_khach.get(DANH_CHO_BAN)).json()]
    assert ten_ds == ["BánChạy", "ĐãXem", "ÍtBán"] or ten_ds == ["BánChạy", "ÍtBán", "ĐãXem"]
    assert not {"ĐãMua", "KêĐơn", "NgoàiDanhMục", "DanhMụcXemCũ", "ĐãXemCũ"} & set(ten_ds) and cu.id


async def test_danh_cho_ban_khach_vang_lai_theo_ma_phien_va_khong_ro_ri_cua_nguoi_khac(client, dang_nhap_khach, db):
    dm = await tao_danh_muc(db, "A")
    a = await sp_ban_duoc(db, "A1", danh_muc_id=dm.id)
    b = await sp_ban_duoc(db, "A2", danh_muc_id=dm.id)
    await xem(db, a, ma_phien="phien-cua-toi-123")
    ten_ds = lambda r: sorted(t["ten"] for t in r.json())  # noqa: E731
    r = await client.get(DANH_CHO_BAN, headers={"X-Ma-Phien": "phien-cua-toi-123"})
    assert ten_ds(r) == ["A1", "A2"]
    assert (await client.get(DANH_CHO_BAN, headers={"X-Ma-Phien": "phien-nguoi-khac-9"})).json() == []
    assert (await client.get(DANH_CHO_BAN)).json() == []  # không có định danh
    assert (await client.get(DANH_CHO_BAN, headers={"X-Ma-Phien": "x"})).json() == []  # mã phiên sai định dạng
    assert (
        await dang_nhap_khach.get(DANH_CHO_BAN)
    ).json() == []  # thành viên khác: lịch sử của phiên kia không phải của họ
    assert b.id


async def test_danh_cho_ban_loc_di_ung_va_tat_module(dang_nhap_khach, db):
    khach = dang_nhap_khach.tai_khoan
    di_ung = await hoat_chat(db, "DiUng")
    dm = await tao_danh_muc(db, "A")
    an_toan = await sp_ban_duoc(db, "AnToàn", danh_muc_id=dm.id)
    nguy_co = await sp_ban_duoc(db, "NguyCơ", danh_muc_id=dm.id)
    await gan(db, nguy_co, di_ung)
    db.add(HoSoSucKhoe(khach_hang_id=khach.id, dong_y_su_dung=True))
    db.add(DiUng(khach_hang_id=khach.id, hoat_chat_id=di_ung.id))
    await xem(db, an_toan, khach=khach)
    assert [t["ten"] for t in (await dang_nhap_khach.get(DANH_CHO_BAN)).json()] == ["AnToàn"]
    await tat_goi_y(db)
    assert (await dang_nhap_khach.get(DANH_CHO_BAN)).json() == []


# --- AI08: luật mua kèm ---


async def don_hoan_tat(db, khach, *sp, ngay=1, trang_thai="hoan_tat"):
    return await tao_don(
        db,
        khach,
        trang_thai,
        dong=[{"san_pham": s, "so_luong": 1} for s in sp],
        created_at=bay_gio_utc() - timedelta(days=ngay),
    )


async def luat(db, a, b):
    return (
        await db.execute(select(LuatMuaKem).where(LuatMuaKem.san_pham_a_id == a.id, LuatMuaKem.san_pham_b_id == b.id))
    ).scalar_one_or_none()


async def test_luat_mua_kem_cong_thuc_nguong_va_ghi_de(db):
    khach = await tao_khach(db)
    a, b, e, ke_don = [await sp_ban_duoc(db, t) for t in ("A", "B", "E", "KêĐơn")]
    ke_don.loai_san_pham = "thuoc_ke_don"
    c, x, y = [await sp_ban_duoc(db, t) for t in ("C", "X", "Y")]
    db.add(
        LuatMuaKem(
            san_pham_a_id=x.id, san_pham_b_id=y.id, support=Decimal("0.5"), confidence=Decimal("0.5"), lift=Decimal(2)
        )
    )
    await db.flush()
    for _ in range(4):  # A+B+E
        await don_hoan_tat(db, khach, a, b, e, ke_don)
    for _ in range(3):  # A+E (E có mặt ở mọi đơn nên lift = 1)
        await don_hoan_tat(db, khach, a, e, e)  # dòng lặp của cùng sản phẩm chỉ đếm một lần
    for _ in range(3):  # đơn chỉ có E
        await don_hoan_tat(db, khach, e)
    for _ in range(5):  # bị loại: đơn hủy, và đơn hoàn tất quá 180 ngày
        await don_hoan_tat(db, khach, a, c, trang_thai="da_huy")
        await don_hoan_tat(db, khach, a, c, ngay=200)
    kq = await ai08_luat_mua_kem(db)
    assert kq.bo_qua is False and kq.so_luat >= 2
    ab, ba = await luat(db, a, b), await luat(db, b, a)
    # N = 10 đơn trong cửa sổ (không tính đơn có đơn khác trong test khác vì mỗi test rollback); A: 7 đơn, B: 4 đơn, A+B: 4
    assert ab is not None and ba is not None
    assert (ab.support, ab.confidence, ab.lift) == (Decimal("0.400000"), Decimal("0.571429"), Decimal("1.4286"))
    assert (ba.confidence, ba.lift) == (Decimal("1.000000"), Decimal("1.4286"))
    assert await luat(db, a, e) is None and await luat(db, e, a) is None  # lift = 1: bỏ
    assert await luat(db, a, c) is None and await luat(db, c, a) is None  # đơn hủy / quá hạn
    assert await luat(db, a, ke_don) is None and await luat(db, ke_don, a) is None  # thuốc kê đơn không vào luật
    assert await luat(db, x, y) is None  # luật cũ bị ghi đè


async def test_luat_mua_kem_tat_module_giu_nguyen_luat_cu(db):
    x, y = await sp_ban_duoc(db, "X"), await sp_ban_duoc(db, "Y")
    db.add(
        LuatMuaKem(
            san_pham_a_id=x.id, san_pham_b_id=y.id, support=Decimal("0.5"), confidence=Decimal("0.5"), lift=Decimal(2)
        )
    )
    await db.flush()
    await tat_goi_y(db)
    kq = await ai08_luat_mua_kem(db)
    assert kq.bo_qua is True and await luat(db, x, y) is not None


async def test_cong_thuc_do_tin_cay_bang_khong_khi_khong_co_don(db):
    kq = await ai08_luat_mua_kem(db)  # không có đơn hoàn tất nào trong cửa sổ cũng không lỗi chia cho 0
    assert kq.so_luat >= 0


def test_lich_tuan_co_ai08_chu_nhat():
    assert ("ai08_luat_mua_kem", "sun") in [(t, thu) for t, _, thu, *_ in LICH_TUAN]

"""AD04: đơn vị quy đổi và thành phần của sản phẩm (PUT /san-pham/{id}/don-vi, /thanh-phan)."""

import asyncio

import pytest
from sqlalchemy import func, select

from app.core.loi import LoiNghiepVu
from app.models.ban_hang import CtGioHang, GioHang
from app.models.he_thong import NhanVien
from app.models.san_pham import DonViQuyDoi, HoatChat, SanPham, ThanhPhan
from app.modules.san_pham import san_pham as dich_vu
from app.modules.san_pham import san_pham_don_vi
from app.modules.san_pham.schemas_san_pham import SanPhamTao, ThayDonVi
from tests.factories import tao_danh_muc, tao_don, tao_khach, tao_lo, tao_nhan_vien
from tests.nhan_vien.dung_chung import nhat_ky
from tests.san_pham.mau_san_pham import GOC, doc_sp, la_loi, tao_sp, than_tao


def don_vi_vao(sp: dict, **sua_theo_ten) -> list[dict]:
    """Danh sách `don_vi` của `PUT` giữ nguyên `sp`; `sua_theo_ten` = {tên đơn vị: {trường: giá trị}} để đổi một số trường."""
    ket_qua = []
    for d in sp["don_vi"]:
        vao = {k: d[k] for k in ("id", "ten_don_vi", "he_so", "gia_ban", "ban_online", "la_mac_dinh", "ma_vach")}
        vao.update(sua_theo_ten.get(d["ten_don_vi"], {}))
        ket_qua.append(vao)
    return ket_qua


async def thay(admin, sp: dict, don_vi: list[dict], phien_ban: str | None = None):
    return await admin.put(
        f"{GOC}/{sp['id']}/don-vi", json={"phien_ban": phien_ban or sp["phien_ban"], "don_vi": don_vi}
    )


async def sp_moi(admin, db, **ghi_de) -> dict:
    return await tao_sp(admin, (await tao_danh_muc(db, f"DM {ghi_de.get('sku', 'x')}")).id, **ghi_de)


def tom_tat(sp: dict):
    return [(d["ten_don_vi"], d["he_so"], d["gia_ban"], d["la_mac_dinh"]) for d in sp["don_vi"]]


# --- Đơn vị quy đổi --------------------------------------------------------------------------------------------------------


async def test_thay_danh_sach_sua_gia_them_don_vi_va_ghi_nhat_ky(dang_nhap_admin, db):
    sp = await sp_moi(dang_nhap_admin, db)
    don_vi = don_vi_vao(sp, Hộp={"gia_ban": "95000"}) + [
        {"ten_don_vi": "Vỉ", "he_so": 10, "gia_ban": "9500", "ban_online": False, "ma_vach": "ABC123"}
    ]
    phan_hoi = await thay(dang_nhap_admin, sp, don_vi)
    assert phan_hoi.status_code == 200, phan_hoi.text
    moi = phan_hoi.json()
    assert tom_tat(moi) == [
        ("Viên", 1, "1000.00", False),
        ("Vỉ", 10, "9500.00", False),
        ("Hộp", 100, "95000.00", True),
    ]
    vi = next(d for d in moi["don_vi"] if d["ten_don_vi"] == "Vỉ")
    assert vi["ban_online"] is False and vi["ma_vach"] == "ABC123"
    cu_hop = next(d for d in sp["don_vi"] if d["ten_don_vi"] == "Hộp")
    assert next(d for d in moi["don_vi"] if d["ten_don_vi"] == "Hộp")["id"] == cu_hop["id"]  # sửa tại chỗ, giữ id
    assert moi["phien_ban"] != sp["phien_ban"] and moi["don_vi_co_so"] == "Viên"
    ghi = [g for g in await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "sua") if g.bang == "don_vi_quy_doi"]
    assert len(ghi) == 1 and ghi[0].gia_tri_cu["don_vi"][1]["gia_ban"] != ghi[0].gia_tri_moi["don_vi"][2]["gia_ban"]


async def test_xoa_don_vi_bo_di_chuyen_co_mac_dinh_va_doi_ten_don_vi_co_so(dang_nhap_admin, db):
    sp = await sp_moi(dang_nhap_admin, db)
    don_vi = [
        {"ten_don_vi": "Viên", "he_so": 1, "gia_ban": "1000", "la_mac_dinh": True},  # mặc định chuyển sang đơn vị cơ sở
        {"ten_don_vi": "Vỉ", "he_so": 10, "gia_ban": "9500"},
    ]
    # `Viên` có id: giữ id để thành "sửa"; `Hộp` không có trong danh sách: bị xóa; `Vỉ` mới.
    don_vi[0]["id"] = next(d["id"] for d in sp["don_vi"] if d["ten_don_vi"] == "Viên")
    phan_hoi = await thay(dang_nhap_admin, sp, don_vi)
    assert phan_hoi.status_code == 200, phan_hoi.text
    assert tom_tat(phan_hoi.json()) == [("Viên", 1, "1000.00", True), ("Vỉ", 10, "9500.00", False)]
    # Đổi tên đơn vị cơ sở: `don_vi_co_so` của sản phẩm đi theo.
    moi = phan_hoi.json()
    doi_ten = await thay(dang_nhap_admin, moi, don_vi_vao(moi, Viên={"ten_don_vi": "Viên nén"}))
    assert doi_ten.status_code == 200 and doi_ten.json()["don_vi_co_so"] == "Viên nén"
    assert (await doc_sp(dang_nhap_admin, sp["id"]))["don_vi_co_so"] == "Viên nén"


async def test_hoan_doi_ten_hai_don_vi_va_chuyen_co_mac_dinh_khong_va_rang_buoc_duy_nhat(dang_nhap_admin, db):
    """DB kiểm tên đơn vị, đơn vị cơ sở và đơn vị mặc định ngay từng dòng: đổi chỗ phải áp theo pha."""
    sp = await sp_moi(dang_nhap_admin, db)
    don_vi = don_vi_vao(
        sp, Viên={"ten_don_vi": "Hộp", "la_mac_dinh": True}, Hộp={"ten_don_vi": "Viên", "la_mac_dinh": False}
    )
    phan_hoi = await thay(dang_nhap_admin, sp, don_vi)
    assert phan_hoi.status_code == 200, phan_hoi.text
    # Cùng id nhưng tên đã hoán đổi: đơn vị id 1 (hệ số 1) giờ tên "Hộp"; id 2 (hệ số 100) giờ tên "Viên".
    assert tom_tat(phan_hoi.json()) == [("Hộp", 1, "1000.00", True), ("Viên", 100, "90000.00", False)]
    assert phan_hoi.json()["don_vi_co_so"] == "Hộp"


async def test_doi_don_vi_co_so_sang_don_vi_khac_khi_chua_ai_dung(dang_nhap_admin, db):
    sp = await sp_moi(dang_nhap_admin, db)
    id_vien = next(d["id"] for d in sp["don_vi"] if d["ten_don_vi"] == "Viên")
    id_hop = next(d["id"] for d in sp["don_vi"] if d["ten_don_vi"] == "Hộp")
    don_vi = [
        {"id": id_vien, "ten_don_vi": "Viên", "he_so": 10, "gia_ban": "1000"},
        {"id": id_hop, "ten_don_vi": "Hộp", "he_so": 1, "gia_ban": "90000", "la_mac_dinh": True},
    ]
    phan_hoi = await thay(dang_nhap_admin, sp, don_vi)
    assert phan_hoi.status_code == 200, phan_hoi.text
    assert phan_hoi.json()["don_vi_co_so"] == "Hộp" and tom_tat(phan_hoi.json())[0][:2] == ("Hộp", 1)


async def test_khong_co_gi_thay_doi_thi_giu_phien_ban_va_khong_ghi_nhat_ky(dang_nhap_admin, db):
    sp = await sp_moi(dang_nhap_admin, db)
    truoc = len(await nhat_ky(db, dang_nhap_admin.tai_khoan.id))
    phan_hoi = await thay(dang_nhap_admin, sp, don_vi_vao(sp))
    assert phan_hoi.status_code == 200 and phan_hoi.json()["phien_ban"] == sp["phien_ban"]
    assert phan_hoi.json()["updated_at"] == sp["updated_at"]
    assert len(await nhat_ky(db, dang_nhap_admin.tai_khoan.id)) == truoc


@pytest.mark.parametrize(
    ("ten_ca", "tao_danh_sach"),
    [
        ("rỗng", lambda sp: []),
        ("bỏ đơn vị cơ sở", lambda sp: [d for d in don_vi_vao(sp) if d["he_so"] != 1]),
        ("hai đơn vị cơ sở", lambda sp: don_vi_vao(sp, Hộp={"he_so": 1})),
        ("hai đơn vị mặc định", lambda sp: don_vi_vao(sp, Viên={"la_mac_dinh": True})),
        ("trùng tên", lambda sp: don_vi_vao(sp, Hộp={"ten_don_vi": "viên"})),
        ("giá lẻ", lambda sp: don_vi_vao(sp, Hộp={"gia_ban": "1.5"})),
        ("giá âm", lambda sp: don_vi_vao(sp, Hộp={"gia_ban": "-5"})),
        ("hệ số 0", lambda sp: don_vi_vao(sp, Hộp={"he_so": 0})),
        ("trùng id", lambda sp: [*don_vi_vao(sp), don_vi_vao(sp)[0]]),
        ("trường lạ", lambda sp: [{**d, "ton": 1} for d in don_vi_vao(sp)]),
    ],
)
async def test_thay_danh_sach_sai_la_400_va_khong_doi_gi(dang_nhap_admin, db, ten_ca, tao_danh_sach):
    sp = await sp_moi(dang_nhap_admin, db)
    phan_hoi = await thay(dang_nhap_admin, sp, tao_danh_sach(sp))
    assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE"), (ten_ca, phan_hoi.text)
    assert (await doc_sp(dang_nhap_admin, sp["id"]))["phien_ban"] == sp["phien_ban"]


async def test_don_vi_cua_san_pham_khac_hoac_khong_co_la_400(dang_nhap_admin, db):
    a = await sp_moi(dang_nhap_admin, db, sku="a")
    b = await sp_moi(dang_nhap_admin, db, sku="b")
    cua_b = b["don_vi"][0]["id"]
    for id_la in (cua_b, 2_000_000_000):
        don_vi = don_vi_vao(a)
        don_vi[1]["id"] = id_la
        phan_hoi = await thay(dang_nhap_admin, a, don_vi)
        assert (
            la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE") and phan_hoi.json()["chi_tiet"][0]["truong"] == "don_vi.1.id"
        )
    assert len((await doc_sp(dang_nhap_admin, b["id"]))["don_vi"]) == 2  # đơn vị của sản phẩm kia nguyên vẹn


async def test_ma_vach_khong_trung_voi_san_pham_khac_nhung_giu_ma_vach_cua_chinh_no_thi_duoc(dang_nhap_admin, db):
    a = await sp_moi(
        dang_nhap_admin, db, sku="a", don_vi=[{"ten_don_vi": "Viên", "he_so": 1, "gia_ban": "1", "ma_vach": "111"}]
    )
    b = await sp_moi(dang_nhap_admin, db, sku="b")
    trung = don_vi_vao(b, Viên={"ma_vach": "111"})
    phan_hoi = await thay(dang_nhap_admin, b, trung)
    assert la_loi(phan_hoi, 409, "TRUNG_DU_LIEU") and phan_hoi.json()["chi_tiet"] == {"truong": "don_vi.0.ma_vach"}
    gia_moi = await thay(dang_nhap_admin, a, don_vi_vao(a, Viên={"gia_ban": "2"}))  # vẫn giữ mã vạch 111 của chính nó
    assert gia_moi.status_code == 200 and gia_moi.json()["don_vi"][0]["ma_vach"] == "111"
    sang_b = await thay(dang_nhap_admin, b, don_vi_vao(b, Viên={"ma_vach": "222"}))
    assert sang_b.status_code == 200


async def test_phien_ban_cu_la_409(dang_nhap_admin, db):
    sp = await sp_moi(dang_nhap_admin, db)
    dau = await thay(dang_nhap_admin, sp, don_vi_vao(sp, Hộp={"gia_ban": "91000"}))
    assert dau.status_code == 200
    cu = await thay(dang_nhap_admin, sp, don_vi_vao(sp, Hộp={"gia_ban": "92000"}))  # dựa trên bản đã cũ
    assert la_loi(cu, 409, "DU_LIEU_DA_THAY_DOI")
    assert (
        next(d for d in (await doc_sp(dang_nhap_admin, sp["id"]))["don_vi"] if d["ten_don_vi"] == "Hộp")["gia_ban"]
        == "91000.00"
    )


async def test_don_vi_dang_duoc_dung_khong_xoa_duoc_va_khong_doi_he_so_nhung_van_sua_gia(dang_nhap_admin, db):
    sp = await sp_moi(dang_nhap_admin, db)
    goc = await db.get(SanPham, sp["id"])
    goc.don_vi_theo_ten = {
        d.ten_don_vi: d
        for d in (await db.execute(select(DonViQuyDoi).where(DonViQuyDoi.san_pham_id == goc.id))).scalars()
    }
    khach = await tao_khach(db)
    await tao_don(db, khach, dong=[{"san_pham": goc, "so_luong": 1, "don_vi": "Hộp"}])  # đơn hàng dùng đơn vị Hộp
    # Xóa Hộp: bị từ chối, các đơn vị khác nguyên vẹn (savepoint không làm hỏng giao dịch).
    bo_hop = [d for d in don_vi_vao(sp) if d["ten_don_vi"] != "Hộp"]
    bo_hop[0]["la_mac_dinh"] = True
    phan_hoi = await thay(dang_nhap_admin, sp, bo_hop)
    assert la_loi(phan_hoi, 409, "DU_LIEU_DANG_DUOC_SU_DUNG"), phan_hoi.text
    assert tom_tat(await doc_sp(dang_nhap_admin, sp["id"])) == tom_tat(sp)
    # Đổi hệ số của Hộp: bị từ chối.
    doi_he_so = await thay(dang_nhap_admin, sp, don_vi_vao(sp, Hộp={"he_so": 50}))
    assert la_loi(doi_he_so, 409, "DU_LIEU_DANG_DUOC_SU_DUNG")
    # Sửa giá, tên, mã vạch và thêm đơn vị mới thì được.
    ok = await thay(
        dang_nhap_admin,
        sp,
        [
            *don_vi_vao(sp, Hộp={"gia_ban": "99000", "ma_vach": "999"}),
            {"ten_don_vi": "Thùng", "he_so": 1000, "gia_ban": "800000"},
        ],
    )
    assert ok.status_code == 200, ok.text
    assert next(d for d in ok.json()["don_vi"] if d["ten_don_vi"] == "Hộp")["gia_ban"] == "99000.00"


async def test_don_vi_trong_gio_hang_cung_khong_xoa_duoc(dang_nhap_admin, db):
    sp = await sp_moi(dang_nhap_admin, db)
    khach = await tao_khach(db)
    gio = GioHang(khach_hang_id=khach.id)
    db.add(gio)
    await db.flush()
    id_hop = next(d["id"] for d in sp["don_vi"] if d["ten_don_vi"] == "Hộp")
    db.add(CtGioHang(gio_hang_id=gio.id, san_pham_id=sp["id"], don_vi_id=id_hop, so_luong=2))
    await db.flush()
    bo_hop = [d for d in don_vi_vao(sp) if d["ten_don_vi"] != "Hộp"]
    phan_hoi = await thay(dang_nhap_admin, sp, bo_hop)
    assert la_loi(phan_hoi, 409, "DU_LIEU_DANG_DUOC_SU_DUNG")
    assert (
        await db.execute(select(func.count()).select_from(DonViQuyDoi).where(DonViQuyDoi.san_pham_id == sp["id"]))
    ).scalar_one() == 2


async def test_san_pham_da_co_lo_khong_doi_he_so_don_vi_nao_nhung_sua_gia_va_them_don_vi_duoc(dang_nhap_admin, db):
    sp = await sp_moi(dang_nhap_admin, db)
    await tao_lo(db, await db.get(SanPham, sp["id"]), so_luong_ton=10)
    doi_he_so = await thay(dang_nhap_admin, sp, don_vi_vao(sp, Hộp={"he_so": 120}))
    assert la_loi(doi_he_so, 409, "DU_LIEU_DANG_DUOC_SU_DUNG")
    doi_co_so = await thay(dang_nhap_admin, sp, don_vi_vao(sp, Viên={"he_so": 2}, Hộp={"he_so": 1}))
    assert la_loi(doi_co_so, 409, "DU_LIEU_DANG_DUOC_SU_DUNG")
    ok = await thay(
        dang_nhap_admin,
        sp,
        [*don_vi_vao(sp, Viên={"gia_ban": "1100"}), {"ten_don_vi": "Vỉ", "he_so": 10, "gia_ban": "9500"}],
    )
    assert ok.status_code == 200
    bo_hop = await thay(dang_nhap_admin, ok.json(), [d for d in don_vi_vao(ok.json()) if d["ten_don_vi"] != "Hộp"])
    assert bo_hop.status_code == 200  # Hộp chưa ai dùng: xóa được dù sản phẩm đã có lô


async def test_dong_thoi_hai_lan_thay_don_vi_cung_phien_ban_chi_mot_ben_thanh_cong(db_that):
    async with db_that() as s, s.begin():
        admin_id = (await tao_nhan_vien(s, "ADMIN")).id
        dm = await tao_danh_muc(s, "A")
        actor = await s.get(NhanVien, admin_id)
        sp = await dich_vu.tao(s, actor, SanPhamTao.model_validate(than_tao(dm.id)), ip="127.0.0.1")
        sp_id, phien_ban = sp.id, sp.phien_ban
        id_hop = next(d.id for d in sp.don_vi if d.ten_don_vi == "Hộp")
        id_vien = next(d.id for d in sp.don_vi if d.ten_don_vi == "Viên")

    async def thay_gia(gia):
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, admin_id)
            du_lieu = ThayDonVi.model_validate(
                {
                    "phien_ban": phien_ban,
                    "don_vi": [
                        {"id": id_vien, "ten_don_vi": "Viên", "he_so": 1, "gia_ban": "1000"},
                        {"id": id_hop, "ten_don_vi": "Hộp", "he_so": 100, "gia_ban": gia, "la_mac_dinh": True},
                    ],
                }
            )
            await san_pham_don_vi.thay_don_vi(s, actor, sp_id, du_lieu, ip="127.0.0.1")
            await asyncio.sleep(0.3)

    ket_qua = await asyncio.wait_for(
        asyncio.gather(thay_gia("91000"), thay_gia("92000"), return_exceptions=True), timeout=20
    )
    loi = [k for k in ket_qua if k is not None]
    assert len(loi) == 1 and isinstance(loi[0], LoiNghiepVu) and loi[0].ma_loi == "DU_LIEU_DA_THAY_DOI", ket_qua


async def test_hoan_doi_don_vi_co_so_giua_hai_don_vi_chua_ai_dung_thanh_cong(dang_nhap_admin, db):
    """Hệ số 1 chỉ được một dòng giữ tại mọi thời điểm: đổi chỗ Viên (1) và Hộp (100) phải qua giá trị tạm."""
    sp = await sp_moi(dang_nhap_admin, db)
    doi = don_vi_vao(sp, Viên={"he_so": 100, "la_mac_dinh": True}, Hộp={"he_so": 1, "la_mac_dinh": False})
    # Dòng sắp vào hệ số 1 đứng TRƯỚC dòng đang giữ hệ số 1: áp theo thứ tự gửi lên thì có lúc hai dòng cùng hệ số 1.
    phan_hoi = await thay(dang_nhap_admin, sp, sorted(doi, key=lambda d: d["he_so"] != 1))
    assert phan_hoi.status_code == 200, phan_hoi.text
    moi = phan_hoi.json()
    assert [(d["ten_don_vi"], d["he_so"]) for d in moi["don_vi"]] == [("Hộp", 1), ("Viên", 100)]
    assert (await db.get(SanPham, sp["id"])).don_vi_co_so == "Hộp"


async def test_san_pham_da_co_lo_khong_thay_don_vi_co_so_bang_don_vi_moi(dang_nhap_admin, db):
    """Thay đơn vị cơ sở (bỏ Viên, thêm đơn vị mới hệ số 1) làm số lượng tồn đã ghi đổi nghĩa nên bị từ chối."""
    sp = await sp_moi(dang_nhap_admin, db)
    await tao_lo(db, await db.get(SanPham, sp["id"]), so_luong_ton=10)
    don_vi = [d for d in don_vi_vao(sp) if d["ten_don_vi"] != "Viên"]
    don_vi.append({"ten_don_vi": "Cái", "he_so": 1, "gia_ban": "1500"})
    phan_hoi = await thay(dang_nhap_admin, sp, don_vi)
    assert la_loi(phan_hoi, 409, "DU_LIEU_DANG_DUOC_SU_DUNG"), phan_hoi.text
    assert tom_tat(await doc_sp(dang_nhap_admin, sp["id"])) == tom_tat(sp)


async def test_chua_co_lo_hay_tham_chieu_thi_thay_don_vi_co_so_duoc(dang_nhap_admin, db):
    sp = await sp_moi(dang_nhap_admin, db)
    don_vi = [d for d in don_vi_vao(sp) if d["ten_don_vi"] != "Viên"]
    don_vi.append({"ten_don_vi": "Cái", "he_so": 1, "gia_ban": "1500"})
    phan_hoi = await thay(dang_nhap_admin, sp, don_vi)
    assert phan_hoi.status_code == 200, phan_hoi.text
    assert (await db.get(SanPham, sp["id"])).don_vi_co_so == "Cái"


async def test_hai_san_pham_dat_cung_ma_vach_cung_luc_chi_mot_ben_thanh_cong(db_that):
    """Mã vạch không có unique trong DB, chỉ khóa tư vấn giữ lời hứa "một mã vạch, một dòng": hai PUT song song."""
    async with db_that() as s, s.begin():
        admin_id = (await tao_nhan_vien(s, "ADMIN")).id
        dm = await tao_danh_muc(s, "A")
        actor = await s.get(NhanVien, admin_id)
        a = await dich_vu.tao(s, actor, SanPhamTao.model_validate(than_tao(dm.id)), ip="127.0.0.1")
        b = await dich_vu.tao(s, actor, SanPhamTao.model_validate(than_tao(dm.id)), ip="127.0.0.1")
        cua = [(a.id, a.phien_ban, a.don_vi), (b.id, b.phien_ban, b.don_vi)]

    async def dat_ma_vach(san_pham_id, phien_ban, don_vi):
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, admin_id)
            vao = [
                {"id": d.id, "ten_don_vi": d.ten_don_vi, "he_so": d.he_so, "gia_ban": str(d.gia_ban)} for d in don_vi
            ]
            vao[0]["ma_vach"] = "777777"
            du_lieu = ThayDonVi.model_validate({"phien_ban": phien_ban, "don_vi": vao})
            await san_pham_don_vi.thay_don_vi(s, actor, san_pham_id, du_lieu, ip="127.0.0.1")
            await asyncio.sleep(0.3)  # giữ giao dịch mở để bên kia phải chờ khóa

    ket_qua = await asyncio.wait_for(
        asyncio.gather(*(dat_ma_vach(*c) for c in cua), return_exceptions=True), timeout=20
    )
    loi = [k for k in ket_qua if k is not None]
    assert len(loi) == 1 and isinstance(loi[0], LoiNghiepVu) and loi[0].ma_loi == "TRUNG_DU_LIEU", ket_qua
    async with db_that() as s:
        assert (
            await s.execute(select(func.count()).select_from(DonViQuyDoi).where(DonViQuyDoi.ma_vach == "777777"))
        ).scalar_one() == 1


# --- Thành phần --------------------------------------------------------------------------------------------------------------


async def hoat_chat(db, *ten) -> list[int]:
    dong = [HoatChat(ten=t) for t in ten]
    db.add_all(dong)
    await db.flush()
    return [d.id for d in dong]


async def thay_tp(admin, sp: dict, thanh_phan: list[dict], phien_ban: str | None = None):
    return await admin.put(
        f"{GOC}/{sp['id']}/thanh-phan", json={"phien_ban": phien_ban or sp["phien_ban"], "thanh_phan": thanh_phan}
    )


async def test_thay_thanh_phan_them_sua_ham_luong_va_xoa_ghi_nhat_ky(dang_nhap_admin, db):
    sp = await sp_moi(dang_nhap_admin, db)
    para, cafein = await hoat_chat(db, "Paracetamol", "Cafein")
    them = await thay_tp(dang_nhap_admin, sp, [{"hoat_chat_id": para, "ham_luong": "500mg"}, {"hoat_chat_id": cafein}])
    assert them.status_code == 200, them.text
    assert [(t["ten_hoat_chat"], t["ham_luong"]) for t in them.json()["thanh_phan"]] == [
        ("Cafein", None),
        ("Paracetamol", "500mg"),
    ]
    doi = await thay_tp(dang_nhap_admin, them.json(), [{"hoat_chat_id": para, "ham_luong": " 650mg "}])
    assert [(t["ten_hoat_chat"], t["ham_luong"]) for t in doi.json()["thanh_phan"]] == [("Paracetamol", "650mg")]
    xoa = await thay_tp(dang_nhap_admin, doi.json(), [])
    assert xoa.status_code == 200 and xoa.json()["thanh_phan"] == []
    ghi = [g for g in await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "sua") if g.bang == "thanh_phan"]
    assert len(ghi) == 3
    assert (
        await db.execute(select(func.count()).select_from(ThanhPhan).where(ThanhPhan.san_pham_id == sp["id"]))
    ).scalar_one() == 0


async def test_thanh_phan_giong_het_thi_khong_doi_phien_ban_khong_ghi_nhat_ky(dang_nhap_admin, db):
    sp = await sp_moi(dang_nhap_admin, db)
    (para,) = await hoat_chat(db, "Paracetamol")
    dau = await thay_tp(dang_nhap_admin, sp, [{"hoat_chat_id": para, "ham_luong": "500mg"}])
    truoc = len(await nhat_ky(db, dang_nhap_admin.tai_khoan.id))
    lai = await thay_tp(dang_nhap_admin, dau.json(), [{"hoat_chat_id": para, "ham_luong": "500mg"}])
    assert lai.status_code == 200 and lai.json()["phien_ban"] == dau.json()["phien_ban"]
    assert len(await nhat_ky(db, dang_nhap_admin.tai_khoan.id)) == truoc


@pytest.mark.parametrize(
    "thanh_phan",
    [
        [{"hoat_chat_id": 1}, {"hoat_chat_id": 1, "ham_luong": "5mg"}],
        [{"hoat_chat_id": 0}],
        [{"hoat_chat_id": 2_147_483_648}],
        [{"hoat_chat_id": 1, "ham_luong": "x" * 51}],
        [{"hoat_chat_id": 1, "ham_luong": "a\x00"}],
        [{"hoat_chat_id": 1, "ghi_chu": "x"}],
        [{"ten": "Paracetamol"}],
    ],
)
async def test_thanh_phan_sai_la_400(dang_nhap_admin, db, thanh_phan):
    sp = await sp_moi(dang_nhap_admin, db)
    db.add(HoatChat(id=1, ten="Có sẵn"))
    await db.flush()
    phan_hoi = await thay_tp(dang_nhap_admin, sp, thanh_phan)
    assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE"), phan_hoi.text


async def test_hoat_chat_khong_ton_tai_la_400_voi_dung_truong_va_phien_ban_cu_la_409(dang_nhap_admin, db):
    sp = await sp_moi(dang_nhap_admin, db)
    (para,) = await hoat_chat(db, "Paracetamol")
    khong_co = await thay_tp(dang_nhap_admin, sp, [{"hoat_chat_id": para}, {"hoat_chat_id": 999_999}])
    assert (
        la_loi(khong_co, 400, "DU_LIEU_KHONG_HOP_LE")
        and khong_co.json()["chi_tiet"][0]["truong"] == "thanh_phan.1.hoat_chat_id"
    )
    dau = await thay_tp(dang_nhap_admin, sp, [{"hoat_chat_id": para}])
    cu = await thay_tp(dang_nhap_admin, sp, [])
    assert dau.status_code == 200 and la_loi(cu, 409, "DU_LIEU_DA_THAY_DOI")


async def test_thanh_phan_cua_san_pham_khac_va_khong_ton_tai_la_404(dang_nhap_admin, db):
    sp = await sp_moi(dang_nhap_admin, db)
    for id_ in (2_000_000_000,):
        phan_hoi = await dang_nhap_admin.put(
            f"{GOC}/{id_}/thanh-phan", json={"phien_ban": sp["phien_ban"], "thanh_phan": []}
        )
        assert la_loi(phan_hoi, 404, "KHONG_TIM_THAY")
        phan_hoi = await dang_nhap_admin.put(
            f"{GOC}/{id_}/don-vi", json={"phien_ban": sp["phien_ban"], "don_vi": don_vi_vao(sp)}
        )
        assert la_loi(phan_hoi, 404, "KHONG_TIM_THAY")

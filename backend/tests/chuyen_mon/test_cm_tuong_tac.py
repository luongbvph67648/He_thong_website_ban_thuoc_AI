"""DS10: tương tác giữa các hoạt chất (/api/v1/noi-bo/tuong-tac)."""

import asyncio

import pytest
from sqlalchemy import func, select

from app.core import phan_quyen
from app.core.loi import LoiNghiepVu
from app.models.he_thong import NhanVien, Quyen, VaiTro, VaiTroQuyen
from app.models.san_pham import HoatChat, TuongTacHoatChat
from app.modules.chuyen_mon import tuong_tac as dich_vu
from app.modules.chuyen_mon.schemas_tuong_tac import TuongTacTao
from tests.chuyen_mon.mau_chuyen_mon import GOC_TUONG_TAC, la_loi
from tests.factories import tao_nhan_vien
from tests.nhan_vien.dung_chung import nhat_ky


async def hoat_chat(db, *ten) -> list[int]:
    dong = [HoatChat(ten=t) for t in ten]
    db.add_all(dong)
    await db.flush()
    return [d.id for d in dong]


def than(a, b, **ghi_de) -> dict:
    return {
        "hoat_chat_1_id": a,
        "hoat_chat_2_id": b,
        "muc_do": "nghiem_trong",
        "khuyen_cao": "Không dùng chung",
        **ghi_de,
    }


async def them(client, a, b, **ghi_de) -> dict:
    phan_hoi = await client.post(GOC_TUONG_TAC, json=than(a, b, **ghi_de))
    assert phan_hoi.status_code == 201, phan_hoi.text
    return phan_hoi.json()


async def test_them_luu_cap_theo_thu_tu_id_tang_dan_du_gui_thu_tu_nao(dang_nhap_duoc_si, db):
    a, b = await hoat_chat(db, "Warfarin", "Aspirin")
    ban = await them(dang_nhap_duoc_si, b, a, co_che="Tăng nguy cơ chảy máu", nguon_tham_khao="  BNF  ")
    assert (ban["hoat_chat_a_id"], ban["hoat_chat_b_id"]) == (a, b)  # gửi (b, a), lưu (a, b)
    assert (ban["ten_hoat_chat_a"], ban["ten_hoat_chat_b"]) == ("Warfarin", "Aspirin")
    assert ban["muc_do"] == "nghiem_trong" and ban["nguon_tham_khao"] == "BNF"
    assert ban["nguoi_cap_nhat"] == dang_nhap_duoc_si.tai_khoan.ho_ten and ban["updated_at"] is not None
    gui_nguoc = await dang_nhap_duoc_si.get(f"{GOC_TUONG_TAC}/{b}/{a}")
    gui_xuoi = await dang_nhap_duoc_si.get(f"{GOC_TUONG_TAC}/{a}/{b}")
    assert gui_nguoc.status_code == gui_xuoi.status_code == 200 and gui_nguoc.json() == gui_xuoi.json()
    (dong,) = (await db.execute(select(TuongTacHoatChat))).scalars()
    assert dong.hoat_chat_a_id < dong.hoat_chat_b_id
    ghi = await nhat_ky(db, dang_nhap_duoc_si.tai_khoan.id, "tao")
    assert len(ghi) == 1 and ghi[0].bang == "tuong_tac_hoat_chat" and ghi[0].ban_ghi_id == f"{a}-{b}"


@pytest.mark.parametrize(
    ("ten_ca", "ghi_de"),
    [
        ("mức độ lạ", {"muc_do": "rat_nang"}),
        ("thiếu khuyến cáo", {"khuyen_cao": None}),
        ("khuyến cáo rỗng", {"khuyen_cao": "   "}),
        ("khuyến cáo quá dài", {"khuyen_cao": "x" * 2001}),
        ("ký tự điều khiển", {"co_che": "a\u0000b"}),
        ("nguồn quá dài", {"nguon_tham_khao": "x" * 256}),
        ("trường lạ", {"ghi_chu": "x"}),
    ],
)
async def test_du_lieu_sai_la_400(dang_nhap_duoc_si, db, ten_ca, ghi_de):
    a, b = await hoat_chat(db, "A1", "B1")
    phan_hoi = await dang_nhap_duoc_si.post(GOC_TUONG_TAC, json=than(a, b, **ghi_de))
    assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE"), (ten_ca, phan_hoi.text)
    assert (await db.execute(select(func.count()).select_from(TuongTacHoatChat))).scalar_one() == 0


async def test_cap_cung_mot_hoat_chat_hoac_hoat_chat_khong_ton_tai_la_400_dung_truong(dang_nhap_duoc_si, db):
    (a,) = await hoat_chat(db, "A2")
    phan_hoi = await dang_nhap_duoc_si.post(GOC_TUONG_TAC, json=than(a, a))
    assert (
        la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE") and phan_hoi.json()["chi_tiet"][0]["truong"] == "hoat_chat_2_id"
    )
    phan_hoi = await dang_nhap_duoc_si.post(GOC_TUONG_TAC, json=than(a, 2_000_000_000))
    assert (
        la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE") and phan_hoi.json()["chi_tiet"][0]["truong"] == "hoat_chat_2_id"
    )
    phan_hoi = await dang_nhap_duoc_si.post(GOC_TUONG_TAC, json=than(2_000_000_000, a))
    assert phan_hoi.json()["chi_tiet"][0]["truong"] == "hoat_chat_1_id"
    assert (await db.execute(select(func.count()).select_from(TuongTacHoatChat))).scalar_one() == 0


async def test_them_trung_cap_ke_ca_dao_thu_tu_la_409(dang_nhap_duoc_si, db):
    a, b = await hoat_chat(db, "A3", "B3")
    await them(dang_nhap_duoc_si, a, b)
    for x, y in ((a, b), (b, a)):
        assert la_loi(await dang_nhap_duoc_si.post(GOC_TUONG_TAC, json=than(x, y)), 409, "TRUNG_DU_LIEU")
    assert (await db.execute(select(func.count()).select_from(TuongTacHoatChat))).scalar_one() == 1


async def test_sua_dung_phien_ban_doi_noi_dung_ghi_nguoi_cap_nhat_va_nhat_ky(dang_nhap_duoc_si, db):
    a, b = await hoat_chat(db, "A4", "B4")
    ban = await them(dang_nhap_duoc_si, a, b)
    phan_hoi = await dang_nhap_duoc_si.put(
        f"{GOC_TUONG_TAC}/{b}/{a}",
        json={
            "phien_ban": ban["phien_ban"],
            "muc_do": "chong_chi_dinh",
            "khuyen_cao": "Cấm dùng chung",
            "co_che": "Cơ chế",
        },
    )
    assert phan_hoi.status_code == 200, phan_hoi.text
    moi = phan_hoi.json()
    assert moi["muc_do"] == "chong_chi_dinh" and moi["khuyen_cao"] == "Cấm dùng chung" and moi["co_che"] == "Cơ chế"
    assert moi["phien_ban"] != ban["phien_ban"]
    ghi = await nhat_ky(db, dang_nhap_duoc_si.tai_khoan.id, "sua")
    assert (
        len(ghi) == 1
        and ghi[0].gia_tri_cu["muc_do"] == "nghiem_trong"
        and ghi[0].gia_tri_moi["muc_do"] == "chong_chi_dinh"
    )


async def test_sua_khong_doi_gi_thi_khong_ghi_nhat_ky_va_khong_doi_phien_ban(dang_nhap_duoc_si, db):
    a, b = await hoat_chat(db, "A5", "B5")
    ban = await them(dang_nhap_duoc_si, a, b)
    phan_hoi = await dang_nhap_duoc_si.put(
        f"{GOC_TUONG_TAC}/{a}/{b}",
        json={"phien_ban": ban["phien_ban"], "muc_do": ban["muc_do"], "khuyen_cao": ban["khuyen_cao"]},
    )
    assert phan_hoi.status_code == 200 and phan_hoi.json()["phien_ban"] == ban["phien_ban"]
    assert await nhat_ky(db, dang_nhap_duoc_si.tai_khoan.id, "sua") == []


async def test_sua_va_xoa_voi_phien_ban_cu_la_409_khong_doi_gi(dang_nhap_duoc_si, db):
    a, b = await hoat_chat(db, "A6", "B6")
    ban = await them(dang_nhap_duoc_si, a, b)
    dau = await dang_nhap_duoc_si.put(
        f"{GOC_TUONG_TAC}/{a}/{b}",
        json={"phien_ban": ban["phien_ban"], "muc_do": "nhe", "khuyen_cao": "Bản của người thứ nhất"},
    )
    assert dau.status_code == 200
    cu = await dang_nhap_duoc_si.put(
        f"{GOC_TUONG_TAC}/{a}/{b}",
        json={"phien_ban": ban["phien_ban"], "muc_do": "trung_binh", "khuyen_cao": "Bản đã cũ"},
    )
    assert (
        la_loi(cu, 409, "DU_LIEU_DA_THAY_DOI")
        and cu.json()["chi_tiet"]["phien_ban_hien_tai"] == dau.json()["phien_ban"]
    )
    xoa = await dang_nhap_duoc_si.delete(f"{GOC_TUONG_TAC}/{a}/{b}", params={"phien_ban": ban["phien_ban"]})
    assert la_loi(xoa, 409, "DU_LIEU_DA_THAY_DOI")
    con = (await dang_nhap_duoc_si.get(f"{GOC_TUONG_TAC}/{a}/{b}")).json()
    assert con["khuyen_cao"] == "Bản của người thứ nhất"


async def test_xoa_dung_phien_ban_xoa_cung_ghi_nhat_ky_roi_404(dang_nhap_duoc_si, db):
    a, b = await hoat_chat(db, "A7", "B7")
    ban = await them(dang_nhap_duoc_si, a, b)
    xoa = await dang_nhap_duoc_si.delete(f"{GOC_TUONG_TAC}/{b}/{a}", params={"phien_ban": ban["phien_ban"]})
    assert xoa.status_code == 204
    assert la_loi(await dang_nhap_duoc_si.get(f"{GOC_TUONG_TAC}/{a}/{b}"), 404, "KHONG_TIM_THAY")
    assert la_loi(
        await dang_nhap_duoc_si.delete(f"{GOC_TUONG_TAC}/{a}/{b}", params={"phien_ban": ban["phien_ban"]}),
        404,
        "KHONG_TIM_THAY",
    )
    ghi = await nhat_ky(db, dang_nhap_duoc_si.tai_khoan.id, "xoa")
    assert len(ghi) == 1 and ghi[0].gia_tri_cu["khuyen_cao"] == "Không dùng chung"


async def test_phien_ban_sai_dinh_dang_la_400(dang_nhap_duoc_si, db):
    a, b = await hoat_chat(db, "A8", "B8")
    await them(dang_nhap_duoc_si, a, b)
    phan_hoi = await dang_nhap_duoc_si.delete(f"{GOC_TUONG_TAC}/{a}/{b}", params={"phien_ban": "xyz"})
    assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE")


async def test_danh_sach_nang_nhat_truoc_loc_theo_muc_do_va_tim_ten_khong_dau(dang_nhap_duoc_si, db):
    a, b, c, d = await hoat_chat(db, "Ibuprofen", "Aspirin", "Warfarin", "Gừng")
    await them(dang_nhap_duoc_si, a, b, muc_do="trung_binh")
    await them(dang_nhap_duoc_si, a, c, muc_do="chong_chi_dinh")
    await them(dang_nhap_duoc_si, b, c, muc_do="nhe")
    await them(dang_nhap_duoc_si, c, d, muc_do="nghiem_trong")
    tat_ca = (await dang_nhap_duoc_si.get(GOC_TUONG_TAC)).json()
    assert [x["muc_do"] for x in tat_ca["du_lieu"]] == ["chong_chi_dinh", "nghiem_trong", "trung_binh", "nhe"]
    assert tat_ca["tong"] == 4
    nang = (await dang_nhap_duoc_si.get(GOC_TUONG_TAC, params={"muc_do": "nghiem_trong"})).json()
    assert [(x["ten_hoat_chat_a"], x["ten_hoat_chat_b"]) for x in nang["du_lieu"]] == [("Warfarin", "Gừng")]
    tim = (await dang_nhap_duoc_si.get(GOC_TUONG_TAC, params={"q": "gung"})).json()  # không dấu, một trong hai phía
    assert tim["tong"] == 1
    assert (await dang_nhap_duoc_si.get(GOC_TUONG_TAC, params={"q": "warf"})).json()["tong"] == 3
    assert la_loi(await dang_nhap_duoc_si.get(GOC_TUONG_TAC, params={"muc_do": "x"}), 400, "DU_LIEU_KHONG_HOP_LE")
    assert la_loi(await dang_nhap_duoc_si.get(GOC_TUONG_TAC, params={"q": "a\u0000b"}), 400, "DU_LIEU_KHONG_HOP_LE")


async def test_admin_chi_xem_kho_va_khach_khong_ghi_duoc(clients_theo_vai_tro, dang_nhap_khach, client, db):
    duoc_si, admin, kho = (clients_theo_vai_tro[v] for v in ("PHARMACIST", "ADMIN", "WAREHOUSE"))
    a, b = await hoat_chat(db, "A9", "B9")
    ban = await them(duoc_si, a, b)
    assert (await admin.get(GOC_TUONG_TAC)).status_code == 200
    assert (await admin.get(f"{GOC_TUONG_TAC}/{a}/{b}")).status_code == 200
    for phuong_thuc, duong, kw in (
        ("post", GOC_TUONG_TAC, {"json": than(a, b)}),
        (
            "put",
            f"{GOC_TUONG_TAC}/{a}/{b}",
            {"json": {"phien_ban": ban["phien_ban"], "muc_do": "nhe", "khuyen_cao": "x"}},
        ),
        ("delete", f"{GOC_TUONG_TAC}/{a}/{b}", {"params": {"phien_ban": ban["phien_ban"]}}),
    ):
        assert la_loi(await getattr(admin, phuong_thuc)(duong, **kw), 403, "KHONG_CO_QUYEN"), phuong_thuc
        assert la_loi(await getattr(kho, phuong_thuc)(duong, **kw), 403, "KHONG_CO_QUYEN"), phuong_thuc
    assert la_loi(await kho.get(GOC_TUONG_TAC), 403, "KHONG_CO_QUYEN")
    assert (await client.get(GOC_TUONG_TAC)).status_code == 401
    assert (await dang_nhap_khach.get(GOC_TUONG_TAC)).status_code == 401
    assert (await db.execute(select(func.count()).select_from(TuongTacHoatChat))).scalar_one() == 1


async def test_quyen_cap_cho_vai_tro_khac_van_khong_cho_ghi_tuong_tac(clients_theo_vai_tro, db):
    duoc_si, kho = clients_theo_vai_tro["PHARMACIST"], clients_theo_vai_tro["WAREHOUSE"]
    a, b = await hoat_chat(db, "A10", "B10")
    ban = await them(duoc_si, a, b)
    vai_tro_id = (await db.execute(select(VaiTro.id).where(VaiTro.ma == "WAREHOUSE"))).scalar_one()
    quyen_id = (await db.execute(select(Quyen.id).where(Quyen.ma == "content.professional.edit"))).scalar_one()
    db.add(VaiTroQuyen(vai_tro_id=vai_tro_id, quyen_id=quyen_id, gioi_han=None))
    await db.flush()
    phan_quyen.xoa_cache_quyen()
    assert (await kho.get(GOC_TUONG_TAC)).status_code == 200
    assert la_loi(await kho.post(GOC_TUONG_TAC, json=than(a, b)), 403, "KHONG_CO_QUYEN")
    phan_hoi = await kho.delete(f"{GOC_TUONG_TAC}/{a}/{b}", params={"phien_ban": ban["phien_ban"]})
    assert la_loi(phan_hoi, 403, "KHONG_CO_QUYEN")
    assert (await db.execute(select(func.count()).select_from(TuongTacHoatChat))).scalar_one() == 1


async def test_hai_duoc_si_them_cung_mot_cap_cung_luc_ben_thua_nhan_409_khong_phai_500(db_that):
    async with db_that() as s, s.begin():
        duoc_si_id = (await tao_nhan_vien(s, "PHARMACIST")).id
        a, b = await hoat_chat(s, "AA", "BB")

    async def them_cap(muc_do):
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, duoc_si_id)
            du_lieu = TuongTacTao.model_validate(than(a, b, muc_do=muc_do))
            await dich_vu.tao(s, actor, du_lieu, ip="127.0.0.1")
            await asyncio.sleep(0.3)

    ket_qua = await asyncio.wait_for(
        asyncio.gather(them_cap("nhe"), them_cap("nghiem_trong"), return_exceptions=True), timeout=20
    )
    loi = [k for k in ket_qua if k is not None]
    assert len(loi) == 1 and isinstance(loi[0], LoiNghiepVu) and loi[0].ma_loi == "TRUNG_DU_LIEU", ket_qua
    async with db_that() as s:
        assert (await s.execute(select(func.count()).select_from(TuongTacHoatChat))).scalar_one() == 1

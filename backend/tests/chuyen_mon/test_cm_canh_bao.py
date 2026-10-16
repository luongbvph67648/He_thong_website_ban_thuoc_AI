"""DS10: `kiem_tra_tuong_tac` và `kiem_tra_di_ung`: chỉ trả cảnh báo có mức độ, không trả hồ sơ sức khỏe."""

import json

from app.models.enums import MucDoTuongTac
from app.models.khach_hang import DiUng
from app.models.san_pham import HoatChat, ThanhPhan, TuongTacHoatChat
from app.modules.chuyen_mon.canh_bao import kiem_tra_di_ung, kiem_tra_tuong_tac
from tests.factories import tao_khach, tao_san_pham


async def hoat_chat(db, *ten) -> list[int]:
    dong = [HoatChat(ten=t) for t in ten]
    db.add_all(dong)
    await db.flush()
    return [d.id for d in dong]


async def san_pham_co(db, *hoat_chat_ids, ten=None):
    sp = await tao_san_pham(db, **({"ten": ten} if ten else {}))
    for hc in hoat_chat_ids:
        db.add(ThanhPhan(san_pham_id=sp.id, hoat_chat_id=hc))
    await db.flush()
    return sp


async def cap(db, a, b, muc_do, khuyen_cao="Tránh dùng chung", co_che=None):
    a, b = min(a, b), max(a, b)
    db.add(TuongTacHoatChat(hoat_chat_a_id=a, hoat_chat_b_id=b, muc_do=muc_do, khuyen_cao=khuyen_cao, co_che=co_che))
    await db.flush()


# --- Tương tác -----------------------------------------------------------------------------------------------------------


async def test_hai_san_pham_chua_hai_hoat_chat_tuong_tac_bi_canh_bao_dung_cap_san_pham(db):
    warfarin, aspirin = await hoat_chat(db, "Warfarin", "Aspirin")
    await cap(db, warfarin, aspirin, MucDoTuongTac.nghiem_trong, "Nguy cơ chảy máu", co_che="Cộng hợp chống đông")
    sp_w = await san_pham_co(db, warfarin)
    sp_a = await san_pham_co(db, aspirin)
    kq = await kiem_tra_tuong_tac(db, [sp_a.id, sp_w.id])
    assert len(kq) == 1
    c = kq[0]
    assert c.loai == "tuong_tac" and c.muc_do == MucDoTuongTac.nghiem_trong
    assert (c.hoat_chat_a_id, c.ten_hoat_chat_a, c.san_pham_a_id) == (warfarin, "Warfarin", sp_w.id)
    assert (c.hoat_chat_b_id, c.ten_hoat_chat_b, c.san_pham_b_id) == (aspirin, "Aspirin", sp_a.id)
    assert c.khuyen_cao == "Nguy cơ chảy máu" and c.co_che == "Cộng hợp chống đông"


async def test_thu_tu_san_pham_va_id_trung_khong_doi_ket_qua(db):
    a, b = await hoat_chat(db, "A", "B")
    await cap(db, a, b, MucDoTuongTac.trung_binh)
    sp1, sp2 = await san_pham_co(db, a), await san_pham_co(db, b)
    kq1 = await kiem_tra_tuong_tac(db, [sp1.id, sp2.id])
    kq2 = await kiem_tra_tuong_tac(db, [sp2.id, sp1.id, sp1.id, sp2.id])
    assert len(kq1) == 1 and kq1 == kq2


async def test_hai_hoat_chat_trong_cung_mot_san_pham_phoi_hop_khong_bi_canh_bao(db):
    a, b = await hoat_chat(db, "A", "B")
    await cap(db, a, b, MucDoTuongTac.chong_chi_dinh)
    sp_phoi_hop = await san_pham_co(db, a, b)
    (c,) = await hoat_chat(db, "Không tương tác")
    khac = await san_pham_co(db, c)
    assert await kiem_tra_tuong_tac(db, [sp_phoi_hop.id, khac.id]) == []
    assert await kiem_tra_tuong_tac(db, [sp_phoi_hop.id]) == []


async def test_phoi_hop_tuong_tac_voi_san_pham_khac_van_bi_canh_bao_dung_san_pham(db):
    a, b, c = await hoat_chat(db, "A", "B", "C")
    await cap(db, a, c, MucDoTuongTac.nghiem_trong)
    phoi_hop = await san_pham_co(db, a, b)
    don = await san_pham_co(db, c)
    kq = await kiem_tra_tuong_tac(db, [phoi_hop.id, don.id])
    assert [(x.san_pham_a_id, x.san_pham_b_id) for x in kq] == [(phoi_hop.id, don.id)]


async def test_sap_xep_nang_nhat_truoc_roi_theo_hoat_chat(db):
    a, b, c, d = await hoat_chat(db, "A", "B", "C", "D")
    await cap(db, a, b, MucDoTuongTac.nhe)
    await cap(db, a, c, MucDoTuongTac.chong_chi_dinh)
    await cap(db, b, d, MucDoTuongTac.trung_binh)
    await cap(db, c, d, MucDoTuongTac.nghiem_trong)
    sps = [await san_pham_co(db, x) for x in (a, b, c, d)]
    kq = await kiem_tra_tuong_tac(db, [sp.id for sp in sps])
    assert [x.muc_do for x in kq] == [
        MucDoTuongTac.chong_chi_dinh,
        MucDoTuongTac.nghiem_trong,
        MucDoTuongTac.trung_binh,
        MucDoTuongTac.nhe,
    ]


async def test_khong_co_tuong_tac_khong_co_thanh_phan_hoac_id_la_tra_rong(db):
    a, b = await hoat_chat(db, "A", "B")  # không có dòng tương tác nào
    sp1, sp2 = await san_pham_co(db, a), await san_pham_co(db, b)
    assert await kiem_tra_tuong_tac(db, [sp1.id, sp2.id]) == []
    assert await kiem_tra_tuong_tac(db, []) == []
    assert await kiem_tra_tuong_tac(db, [sp1.id, 2_000_000_000]) == []
    khong_thanh_phan = await tao_san_pham(db)
    assert await kiem_tra_tuong_tac(db, [sp1.id, khong_thanh_phan.id]) == []


async def test_cung_mot_hoat_chat_o_hai_san_pham_khong_phai_la_tuong_tac(db):
    (a,) = await hoat_chat(db, "A")
    sp1, sp2 = await san_pham_co(db, a), await san_pham_co(db, a)
    assert await kiem_tra_tuong_tac(db, [sp1.id, sp2.id]) == []


# --- Dị ứng --------------------------------------------------------------------------------------------------------------


async def test_di_ung_canh_bao_san_pham_chua_hoat_chat_khach_khai_chi_cua_khach_do(db):
    amox, para = await hoat_chat(db, "Amoxicillin", "Paracetamol")
    khach, nguoi_khac = await tao_khach(db), await tao_khach(db)
    db.add(DiUng(khach_hang_id=khach.id, hoat_chat_id=amox, ghi_chu="phát ban năm 2019, đi cấp cứu"))
    db.add(DiUng(khach_hang_id=nguoi_khac.id, hoat_chat_id=para))
    await db.flush()
    sp_amox = await san_pham_co(db, amox, ten="Augmentin")
    sp_para = await san_pham_co(db, para, ten="Panadol")
    kq = await kiem_tra_di_ung(db, khach.id, [sp_amox.id, sp_para.id])
    assert len(kq) == 1
    c = kq[0]
    assert c.loai == "di_ung" and c.muc_do == MucDoTuongTac.chong_chi_dinh
    assert (c.san_pham_id, c.ten_san_pham, c.hoat_chat_id, c.ten_hoat_chat) == (
        sp_amox.id,
        "Augmentin",
        amox,
        "Amoxicillin",
    )
    # Của người khác không lẫn sang
    assert [x.san_pham_id for x in await kiem_tra_di_ung(db, nguoi_khac.id, [sp_amox.id, sp_para.id])] == [sp_para.id]


async def test_canh_bao_di_ung_khong_lo_ghi_chu_hay_ho_so_suc_khoe(db):
    (amox,) = await hoat_chat(db, "Amoxicillin")
    khach = await tao_khach(db)
    db.add(DiUng(khach_hang_id=khach.id, hoat_chat_id=amox, ghi_chu="BI-MAT-SUC-KHOE-12345"))
    await db.flush()
    sp = await san_pham_co(db, amox)
    kq = await kiem_tra_di_ung(db, khach.id, [sp.id])
    chuoi = json.dumps([x.model_dump(mode="json") for x in kq], ensure_ascii=False)
    assert "BI-MAT-SUC-KHOE" not in chuoi and "ghi_chu" not in chuoi
    assert set(kq[0].model_dump()) == {"loai", "muc_do", "san_pham_id", "ten_san_pham", "hoat_chat_id", "ten_hoat_chat"}


async def test_di_ung_khach_khong_khai_hoac_danh_sach_rong_la_tra_rong(db):
    (amox,) = await hoat_chat(db, "Amoxicillin")
    khach = await tao_khach(db)
    sp = await san_pham_co(db, amox)
    assert await kiem_tra_di_ung(db, khach.id, [sp.id]) == []
    assert await kiem_tra_di_ung(db, khach.id, []) == []
    assert await kiem_tra_di_ung(db, 2_000_000_000, [sp.id]) == []


async def test_di_ung_nhieu_hoat_chat_trong_mot_san_pham_moi_hoat_chat_mot_canh_bao(db):
    a, b, c = await hoat_chat(db, "A", "B", "C")
    khach = await tao_khach(db)
    db.add_all([DiUng(khach_hang_id=khach.id, hoat_chat_id=a), DiUng(khach_hang_id=khach.id, hoat_chat_id=b)])
    await db.flush()
    sp = await san_pham_co(db, a, b, c)
    kq = await kiem_tra_di_ung(db, khach.id, [sp.id, sp.id])
    assert [x.hoat_chat_id for x in kq] == [a, b]

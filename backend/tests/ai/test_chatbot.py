"""T7.3: chatbot tư vấn (AI02 + AI03), an toàn bằng code, SSE, lưu hội thoại. Dùng client giả, không mạng."""

import json
import uuid
from types import SimpleNamespace as NS

from sqlalchemy import select

from app.ai import claude, gia_lap
from app.models.ai import DanhGiaCauTraLoi, HoiThoai, TinNhan
from app.models.khach_hang import DiUng, HoSoSucKhoe
from app.models.san_pham import HoatChat, ThanhPhan, ThongTinChuyenMon
from app.modules.ai_quan_tri import tri_thuc
from tests.factories import tao_don, tao_khach, tao_san_pham

CHAT = "/api/v1/tu-van/chat"
PL_THUONG = {"y_dinh": "hoi_san_pham", "nguy_hiem": False, "can_chuyen_duoc_si": False, "do_tu_tin": 0.9}


def sse(text: str) -> list[tuple[str, dict]]:
    ds = []
    for khoi in text.strip().split("\n\n"):
        dong = khoi.split("\n")
        ds.append((dong[0].removeprefix("event: "), json.loads(dong[1].removeprefix("data: "))))
    return ds


def loai(ds):
    return [x[0] for x in ds]


def kich_ban(*, phan_loai=PL_THUONG, tools=(), chu="Mình gợi ý sản phẩm này.", ket_qua_tool=None):
    """AI02 trả `phan_loai`; AI03 gọi lần lượt `tools` [(tên, input)] qua thuc_thi_tool rồi nói `chu`."""
    gia_lap.KICH_BAN.goi_json = lambda **kw: dict(phan_loai)
    ket_qua_tool = ket_qua_tool if ket_qua_tool is not None else []

    async def stream(**kw):
        for i, (ten, vao) in enumerate(tools):
            kq = await kw["thuc_thi_tool"](NS(name=ten, input=vao, id=f"tu_{i}", type="tool_use"))
            ket_qua_tool.append(kq)
        yield chu

    gia_lap.KICH_BAN.stream = stream


async def hoi(client, noi_dung, ma_phien=None):
    ma = ma_phien or str(uuid.uuid4())
    r = await client.post(CHAT, json={"ma_phien": ma, "noi_dung": noi_dung})
    return r, ma


async def co_san_pham(db, loai_sp, ten, noi_dung_cm=None, hoat_chat=None):
    sp = await tao_san_pham(db, loai_sp, ten=ten)
    if noi_dung_cm:
        db.add(ThongTinChuyenMon(san_pham_id=sp.id, phien_ban=1, trang_thai="da_duyet", chi_dinh=noi_dung_cm))
    if hoat_chat:
        db.add(ThanhPhan(san_pham_id=sp.id, hoat_chat_id=hoat_chat.id))
    await db.flush()
    return sp


async def test_luot_chat_thuong_stream_luu_hoi_thoai_va_luu_y(client, db):
    kich_ban(chu="Panadol giúp hạ sốt.")
    r, ma = await hoi(client, "Thuốc hạ sốt nào tốt?")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    ds = sse(r.text)
    assert loai(ds)[0] == "van_ban" and loai(ds)[-1] == "ket_thuc"
    van_ban = "".join(d["noi_dung"] for k, d in ds if k == "van_ban")
    assert van_ban.startswith("Panadol giúp hạ sốt.") and "không thay thế tư vấn của dược sĩ/bác sĩ" in van_ban
    h = (await db.execute(select(HoiThoai).where(HoiThoai.ma_phien == uuid.UUID(ma)))).scalars().one()
    tin = (await db.execute(select(TinNhan).where(TinNhan.hoi_thoai_id == h.id).order_by(TinNhan.id))).scalars().all()
    assert (
        [t.vai_tro for t in tin] == ["khach", "ai"]
        and tin[1].y_dinh == "hoi_san_pham"
        and tin[1].id == ds[-1][1]["tin_nhan_id"]
    )
    assert tin[1].noi_dung == van_ban and h.khach_hang_id is None and h.ip_hash and len(h.ip_hash) == 64
    ls = (await client.get(f"/api/v1/tu-van/{ma}/tin-nhan")).json()
    assert [t["vai_tro"] for t in ls["tin_nhan"]] == ["khach", "ai"]


async def test_luat_dau_hieu_nguy_hiem_chan_truoc_khi_goi_claude(client, db):
    r, ma = await hoi(client, "Mình bị ĐAU NGỰC và khó thở từ sáng")
    ds = sse(r.text)
    assert loai(ds) == ["nguy_hiem", "ket_thuc"] and "115" in ds[0][1]["noi_dung"]
    assert gia_lap.KICH_BAN.so_lan_goi_json == 0 and gia_lap.KICH_BAN.so_lan_stream == 0  # chưa hề gọi client
    h = (await db.execute(select(HoiThoai).where(HoiThoai.ma_phien == uuid.UUID(ma)))).scalars().one()
    ai = (
        (await db.execute(select(TinNhan).where(TinNhan.hoi_thoai_id == h.id, TinNhan.vai_tro == "ai"))).scalars().one()
    )
    assert h.bi_gan_co is True and h.ly_do_gan_co == "dau_hieu_nguy_hiem" and ai.dau_hieu_nguy_hiem is True


async def test_dau_hieu_khong_dau_va_cum_do_admin_them(client, dang_nhap_admin):
    r, _ = await hoi(client, "toi bi dau nguc")  # không dấu vẫn khớp "đau ngực"
    assert loai(sse(r.text)) == ["nguy_hiem", "ket_thuc"]
    d = (await dang_nhap_admin.get("/api/v1/noi-bo/cau-hinh-ai")).json()
    await dang_nhap_admin.put(
        "/api/v1/noi-bo/cau-hinh-ai", json={"phien_ban": d["phien_ban"], "ai_dau_hieu_nguy_hiem": ["ngộ độc"]}
    )
    r, _ = await hoi(client, "Con mình nghi ngộ độc thuốc")
    assert loai(sse(r.text)) == ["nguy_hiem", "ket_thuc"]
    kich_ban()
    r, _ = await hoi(client, "Mình bị đau ngực nhẹ")  # cụm cũ đã bị Admin bỏ
    assert "nguy_hiem" not in loai(sse(r.text))


async def test_ai02_phat_hien_nguy_hiem_hoac_can_duoc_si_thi_khong_tra_loi(client):
    kich_ban(phan_loai={**PL_THUONG, "nguy_hiem": True})
    ds = sse((await hoi(client, "Sau khi uống thuốc mình thấy lạ lắm"))[0].text)
    assert loai(ds) == ["nguy_hiem", "ket_thuc"] and gia_lap.KICH_BAN.so_lan_stream == 0
    kich_ban(phan_loai={**PL_THUONG, "can_chuyen_duoc_si": True})
    ds = sse((await hoi(client, "Cho mình hỏi liều thuốc huyết áp"))[0].text)
    assert loai(ds) == ["chuyen_duoc_si", "ket_thuc"] and ds[0][1]["ly_do"] == "can_duoc_si"
    assert gia_lap.KICH_BAN.so_lan_stream == 0


async def test_do_tu_tin_thap_van_tra_loi_nhung_de_nghi_duoc_si(client):
    kich_ban(phan_loai={**PL_THUONG, "do_tu_tin": 0.3})
    ds = sse((await hoi(client, "Thuốc nào dùng cho trẻ?"))[0].text)
    assert "van_ban" in loai(ds) and loai(ds)[-2:] == ["chuyen_duoc_si", "ket_thuc"]
    kich_ban(tools=[("de_nghi_gap_duoc_si", {"ly_do": "Hỏi về trẻ nhỏ"})])
    ds = sse((await hoi(client, "Trẻ 2 tuổi dùng gì?"))[0].text)
    cd = next(d for k, d in ds if k == "chuyen_duoc_si")
    assert cd["ly_do"] == "Hỏi về trẻ nhỏ"


async def test_tool_loc_thuoc_ke_don_va_the_chi_gom_id_co_trong_ket_qua_tool(client, db):
    thuong = await co_san_pham(db, "thuoc_khong_ke_don", "Paracetamol Stada", "Hạ sốt giảm đau đầu")
    ke_don = await co_san_pham(db, "thuoc_ke_don", "Paracetamol kê đơn", "Hạ sốt giảm đau đầu mạnh")
    await tri_thuc.dong_bo(db)
    kq_tool: list = []
    kich_ban(
        tools=[
            ("tim_san_pham", {"tu_khoa": "hạ sốt giảm đau đầu", "so_luong": 5}),
            ("xem_san_pham", {"san_pham_id": ke_don.id}),
            ("xem_san_pham", {"san_pham_id": thuong.id}),
        ],
        ket_qua_tool=kq_tool,
    )
    ds = sse((await hoi(client, "Hạ sốt giảm đau đầu dùng gì"))[0].text)
    tim = json.loads(kq_tool[0]["content"])
    assert [x["san_pham_id"] for x in tim] == [thuong.id] and tim[0]["con_hang"] is False
    assert json.loads(kq_tool[1]["content"]) == {"can_tu_van_duoc_si": True}  # thuốc kê đơn không lộ gì
    chi_tiet = json.loads(kq_tool[2]["content"])
    assert "Hạ sốt giảm đau đầu" in chi_tiet["thong_tin_chuyen_mon"]["chi_dinh"]
    the = next(d for k, d in ds if k == "the_san_pham")["san_pham"]
    assert [t["id"] for t in the] == [thuong.id]


async def test_khong_co_tool_thi_khong_co_the_san_pham(client, db):
    await co_san_pham(db, "thuoc_khong_ke_don", "Paracetamol Stada")
    kich_ban(chu="Mình khuyên dùng Paracetamol Stada nhé.")  # nhắc tên nhưng không qua tool
    assert "the_san_pham" not in loai(sse((await hoi(client, "Hạ sốt dùng gì"))[0].text))


async def test_loc_di_ung_chi_khi_khach_dong_y_dung_ho_so(dang_nhap_khach, db):
    khach = dang_nhap_khach.tai_khoan
    hc = HoatChat(ten=f"Ibuprofen-{uuid.uuid4().hex[:4]}")
    db.add(hc)
    await db.flush()
    sp = await co_san_pham(db, "thuoc_khong_ke_don", "Ibuprofen 400", "Giảm đau chống viêm", hoat_chat=hc)
    await tri_thuc.dong_bo(db)
    db.add(DiUng(khach_hang_id=khach.id, hoat_chat_id=hc.id))
    db.add(HoSoSucKhoe(khach_hang_id=khach.id, dong_y_su_dung=False))
    await db.flush()
    kq: list = []
    kich_ban(tools=[("tim_san_pham", {"tu_khoa": "ibuprofen", "so_luong": 3})], ket_qua_tool=kq)
    await hoi(dang_nhap_khach, "Giảm đau chống viêm")
    assert [x["san_pham_id"] for x in json.loads(kq[0]["content"])] == [sp.id]  # chưa đồng ý: không dùng hồ sơ
    ho_so = await db.get(HoSoSucKhoe, khach.id, populate_existing=True)
    ho_so.dong_y_su_dung = True
    await db.flush()
    kq.clear()
    kich_ban(
        tools=[("tim_san_pham", {"tu_khoa": "ibuprofen", "so_luong": 3}), ("xem_san_pham", {"san_pham_id": sp.id})],
        ket_qua_tool=kq,
    )
    ds = sse((await hoi(dang_nhap_khach, "Giảm đau chống viêm"))[0].text)
    assert json.loads(kq[0]["content"]) == [] and json.loads(kq[1]["content"]) == {"khong_tim_thay": True}
    assert "the_san_pham" not in loai(ds)


async def test_chi_gui_phan_can_thiet_cua_ho_so_cho_claude(dang_nhap_khach, db):
    khach = dang_nhap_khach.tai_khoan
    hc = HoatChat(ten=f"Penicillin-{uuid.uuid4().hex[:4]}")
    db.add(hc)
    await db.flush()
    db.add(
        HoSoSucKhoe(
            khach_hang_id=khach.id, dong_y_su_dung=True, nam_sinh=1990, dang_mang_thai=True, benh_nen="BỆNH-NỀN-BÍ-MẬT"
        )
    )
    db.add(DiUng(khach_hang_id=khach.id, hoat_chat_id=hc.id, ghi_chu="GHI-CHÚ-BÍ-MẬT"))
    await db.flush()
    kich_ban()
    await hoi(dang_nhap_khach, "Mình bị ho")
    goi = gia_lap.KICH_BAN.lan_stream[-1]
    gui_di = json.dumps(goi["lich_su"], ensure_ascii=False) + goi["system"]
    assert "đang mang thai" in gui_di and hc.ten in gui_di
    for cam in ("BỆNH-NỀN-BÍ-MẬT", "GHI-CHÚ-BÍ-MẬT", khach.ho_ten, khach.so_dien_thoai):
        assert cam not in gui_di


async def test_ai_tu_choi_loi_hoac_tat_module_thi_chuyen_duoc_si(client, dang_nhap_admin):
    def tu_choi(**kw):
        raise claude.AiTuChoi("bio")

    gia_lap.KICH_BAN.goi_json = lambda **kw: dict(PL_THUONG)
    gia_lap.KICH_BAN.stream = tu_choi
    ds = sse((await hoi(client, "Hỏi gì đó"))[0].text)
    assert ds[-2][0] == "chuyen_duoc_si" and ds[-2][1]["ly_do"] == "ai_tu_choi"

    def hong(**kw):
        raise claude.AiLoi("hết lượt thử lại")

    gia_lap.KICH_BAN.goi_json = hong
    ds = sse((await hoi(client, "Hỏi tiếp"))[0].text)
    assert ds[-2][1]["ly_do"] == "ai_loi" and ds[-1][0] == "ket_thuc"
    gia_lap.dat_lai()
    d = (await dang_nhap_admin.get("/api/v1/noi-bo/cau-hinh-ai")).json()
    await dang_nhap_admin.put(
        "/api/v1/noi-bo/cau-hinh-ai", json={"phien_ban": d["phien_ban"], "ai_module": {**d["ai_module"], "chat": False}}
    )
    ds = sse((await hoi(client, "Chat đã tắt"))[0].text)
    assert ds[0][1]["ly_do"] == "ai_khong_kha_dung" and gia_lap.KICH_BAN.so_lan_goi_json == 0


async def test_het_ngan_sach_ngay_chuyen_duoc_si(client, db, monkeypatch):
    from app.core.config import settings

    db.add(HoiThoai(ma_phien=uuid.uuid4(), chi_phi=5))
    await db.flush()
    monkeypatch.setattr(settings, "AI_NGAN_SACH_NGAY_USD", 2)
    ds = sse((await hoi(client, "Còn trả lời không?"))[0].text)
    assert ds[0][1]["ly_do"] == "ai_khong_kha_dung" and gia_lap.KICH_BAN.so_lan_goi_json == 0


async def test_tool_input_sai_khong_chay_va_xem_don_chi_don_cua_minh(dang_nhap_khach, client, db):
    khach = dang_nhap_khach.tai_khoan
    don = await tao_don(
        db, khach, "dang_giao", [{"san_pham": await tao_san_pham(db, "thuoc_khong_ke_don"), "so_luong": 1}]
    )
    don_khac = await tao_don(
        db,
        await tao_khach(db),
        "dang_giao",
        [{"san_pham": await tao_san_pham(db, "thuoc_khong_ke_don"), "so_luong": 1}],
    )
    kq: list = []
    kich_ban(
        tools=[
            ("tim_san_pham", {"tu_khoa": "", "so_luong": 99}),
            ("xem_don_hang", {"ma_don": don.ma_don}),
            ("xem_don_hang", {"ma_don": don_khac.ma_don}),
            ("khong_co_tool", {}),
        ],
        ket_qua_tool=kq,
    )
    await hoi(dang_nhap_khach, "Đơn của mình tới đâu rồi")
    assert kq[0].get("is_error") is True and kq[0]["content"] == "Tham số không hợp lệ"
    assert (
        json.loads(kq[1]["content"])["ma_don"] == don.ma_don
        and json.loads(kq[1]["content"])["trang_thai"] == "dang_giao"
    )
    assert json.loads(kq[2]["content"]) == {"khong_tim_thay": True}
    assert kq[3].get("is_error") is True
    kq.clear()
    kich_ban(tools=[("xem_don_hang", {"ma_don": don.ma_don})], ket_qua_tool=kq)
    await hoi(client, "Đơn của mình tới đâu rồi")  # vãng lai
    assert json.loads(kq[0]["content"]) == {"can_dang_nhap": True}


async def test_lich_su_chi_gui_text_cac_luot_truoc_va_system_prompt_co_dinh(client):
    kich_ban(chu="Câu trả lời một.")
    _, ma = await hoi(client, "Câu hỏi một")
    kich_ban(chu="Câu trả lời hai.")
    await hoi(client, "Câu hỏi hai", ma)
    lich_su = gia_lap.KICH_BAN.lan_stream[-1]["lich_su"]
    assert [m["role"] for m in lich_su] == ["user", "assistant", "user"] and lich_su[-1]["content"] == "Câu hỏi hai"
    assert all(isinstance(m["content"], str) for m in lich_su) and "Câu trả lời một." in lich_su[1]["content"]
    ten_tool = [t["name"] for t in gia_lap.KICH_BAN.lan_stream[-1]["tools"]]
    assert ten_tool == [
        "tim_san_pham",
        "xem_san_pham",
        "tra_cuu_kien_thuc",
        "tra_cuu_chinh_sach",
        "xem_don_hang",
        "de_nghi_gap_duoc_si",
    ]
    assert all(
        t["strict"] is True and t["input_schema"]["additionalProperties"] is False
        for t in gia_lap.KICH_BAN.lan_stream[-1]["tools"]
    )


async def test_gioi_han_luot_theo_phien(client):
    kich_ban()
    ma = str(uuid.uuid4())
    for _ in range(20):
        assert (await client.post(CHAT, json={"ma_phien": ma, "noi_dung": "xin chào"})).status_code == 200
    r = await client.post(CHAT, json={"ma_phien": ma, "noi_dung": "xin chào"})
    assert r.status_code == 429 and r.json()["ma_loi"] == "QUA_GIOI_HAN" and "Retry-After" in r.headers


async def test_phien_cua_thanh_vien_khong_mo_duoc_boi_nguoi_khac_va_phien_dong(dang_nhap_khach, client, db):
    kich_ban()
    r, ma = await hoi(dang_nhap_khach, "Xin chào")
    assert r.status_code == 200
    assert (await hoi(client, "Tôi là ai", ma))[0].status_code == 404
    assert (await client.get(f"/api/v1/tu-van/{ma}/tin-nhan")).status_code == 404
    h = (await db.execute(select(HoiThoai).where(HoiThoai.ma_phien == uuid.UUID(ma)))).scalars().one()
    assert h.khach_hang_id == dang_nhap_khach.tai_khoan.id
    h.trang_thai = "da_dong"
    await db.flush()
    r = await hoi(dang_nhap_khach, "Còn đó không", ma)
    assert r[0].status_code == 409


async def test_bao_cau_tra_loi_sai(client, dang_nhap_khach, db):
    kich_ban()
    r, ma = await hoi(client, "Xin chào")
    tin_id = sse(r.text)[-1][1]["tin_nhan_id"]
    r = await client.post(
        "/api/v1/tu-van/danh-gia", json={"ma_phien": ma, "tin_nhan_id": tin_id, "ket_qua": "khong_huu_ich"}
    )
    assert r.status_code == 204
    await client.post("/api/v1/tu-van/danh-gia", json={"ma_phien": ma, "tin_nhan_id": tin_id, "ket_qua": "huu_ich"})
    dg = (await db.execute(select(DanhGiaCauTraLoi))).scalars().all()
    assert len(dg) == 1 and dg[0].ket_qua == "huu_ich" and dg[0].nguon == "khach" and dg[0].tin_nhan_id == tin_id
    khach_tin = (await db.execute(select(TinNhan).where(TinNhan.vai_tro == "khach"))).scalars().first()
    assert (
        await client.post(
            "/api/v1/tu-van/danh-gia", json={"ma_phien": ma, "tin_nhan_id": khach_tin.id, "ket_qua": "huu_ich"}
        )
    ).status_code == 404
    assert (
        await dang_nhap_khach.post(
            "/api/v1/tu-van/danh-gia", json={"ma_phien": ma, "tin_nhan_id": tin_id, "ket_qua": "huu_ich"}
        )
    ).status_code == 204


async def test_dau_vao_sai(client):
    for body in (
        {"ma_phien": "khong-phai-uuid", "noi_dung": "x"},
        {"ma_phien": str(uuid.uuid4()), "noi_dung": ""},
        {"ma_phien": str(uuid.uuid4()), "noi_dung": "x" * 1001},
    ):
        assert (await client.post(CHAT, json=body)).status_code == 400

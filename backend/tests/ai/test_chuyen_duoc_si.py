"""T7.4: chuyển dược sĩ (AI04, KTV12), hàng chờ và chat trực tiếp (DS06), WebSocket, HT08 đóng phiên."""

import asyncio
import uuid
from datetime import timedelta

from sqlalchemy import select

from app.ai import claude, gia_lap
from app.core.bao_mat import tao_access_token
from app.core.db import lay_tao_phien
from app.core.ma_hoa import ma_hoa
from app.core.thoi_gian import bay_gio_utc
from app.models.ai import HoiThoai, TinNhan
from app.models.he_thong import CauHinh, NhatKyHeThong
from app.models.khach_hang import DiUng, HoSoSucKhoe, ThongBao
from app.models.san_pham import HoatChat
from app.modules.tu_van import chuyen_duoc_si, ws
from app.modules.tu_van.hub import HUB
from tests.conftest import _dang_nhap
from tests.factories import tao_khach, tao_nhan_vien

GAP = "/api/v1/tu-van/gap-duoc-si"
NB = "/api/v1/noi-bo/tu-van"


async def mo_phien(db, khach=None, trang_thai="dang_mo", tin=("Mình bị ho lâu ngày",)):
    h = HoiThoai(ma_phien=uuid.uuid4(), khach_hang_id=khach.id if khach else None, trang_thai=trang_thai)
    db.add(h)
    await db.flush()
    for i, nd in enumerate(tin):
        db.add(TinNhan(hoi_thoai_id=h.id, vai_tro="khach" if i % 2 == 0 else "ai", noi_dung=nd))
    await db.flush()
    return h


async def dat_gio_lam_viec(db, ngay):
    gia_tri = {"bat_dau": "00:00", "ket_thuc": "23:59", "ngay_trong_tuan": ngay}
    ch = await db.get(CauHinh, "gio_lam_viec_duoc_si")
    if ch is None:
        db.add(CauHinh(khoa="gio_lam_viec_duoc_si", gia_tri=gia_tri))
    else:
        ch.gia_tri = gia_tri
    await db.flush()


async def test_chuyen_trong_gio_co_tom_tat_ai_va_bao_duoc_si(client, db, clients_theo_vai_tro):
    await dat_gio_lam_viec(db, [1, 2, 3, 4, 5, 6, 7])
    h = await mo_phien(db, tin=("Mình bị ho", "Bạn ho bao lâu rồi?", "Hơn 2 tuần"))
    gia_lap.KICH_BAN.goi_json = lambda **kw: {
        "tom_tat": "Khách ho kéo dài hơn 2 tuần.",
        "van_de_chinh": "Cần tư vấn ho kéo dài",
        "san_pham_nhac_den": [],
    }
    r = await client.post(GAP, json={"ma_phien": str(h.ma_phien)})
    assert r.status_code == 200, r.text
    assert r.json()["trang_thai"] == "cho_duoc_si" and r.json()["trong_gio"] is True
    await db.refresh(h)
    assert h.trang_thai == "cho_duoc_si" and "ho kéo dài" in h.tom_tat and "Cần tư vấn ho kéo dài" in h.tom_tat
    assert (await db.execute(select(ThongBao).where(ThongBao.loai == "chat_cho_duoc_si"))).scalars().first() is not None
    lai = await client.post(GAP, json={"ma_phien": str(h.ma_phien)})  # bấm lại không tạo thêm
    assert lai.json()["trang_thai"] == "cho_duoc_si"
    nd = (
        (await db.execute(select(TinNhan).where(TinNhan.hoi_thoai_id == h.id, TinNhan.vai_tro == "he_thong")))
        .scalars()
        .all()
    )
    assert len(nd) == 1


async def test_tom_tat_du_phong_khi_ai_loi(client, db):
    await dat_gio_lam_viec(db, [1, 2, 3, 4, 5, 6, 7])
    h = await mo_phien(db, tin=("Câu hỏi đầu tiên của tôi", "Trả lời", "Câu hỏi thứ hai"))

    def hong(**kw):
        raise claude.AiLoi("lỗi")

    gia_lap.KICH_BAN.goi_json = hong
    assert (await client.post(GAP, json={"ma_phien": str(h.ma_phien)})).status_code == 200
    await db.refresh(h)
    assert h.tom_tat.startswith("Khách hỏi:") and "Câu hỏi thứ hai" in h.tom_tat


async def test_ngoai_gio_cho_goi_lai_can_so_dien_thoai(client, dang_nhap_khach, db):
    await dat_gio_lam_viec(db, [])  # không ngày nào làm việc
    h = await mo_phien(db)
    thieu = await client.post(GAP, json={"ma_phien": str(h.ma_phien)})
    assert thieu.status_code == 400 and thieu.json()["chi_tiet"][0]["truong"] == "so_dien_thoai"
    sai = await client.post(GAP, json={"ma_phien": str(h.ma_phien), "so_dien_thoai": "123"})
    assert sai.status_code == 400
    ok = await client.post(GAP, json={"ma_phien": str(h.ma_phien), "so_dien_thoai": "0912 345 678"})
    assert ok.json() == {
        "trang_thai": "cho_goi_lai",
        "trong_gio": False,
        "thong_diep": chuyen_duoc_si.THONG_DIEP_NGOAI_GIO,
    }
    await db.refresh(h)
    assert h.trang_thai == "cho_goi_lai" and h.so_dien_thoai_goi_lai == "0912345678"
    # thành viên không cần nhập: dùng số trong tài khoản
    h2 = await mo_phien(db, dang_nhap_khach.tai_khoan)
    assert (await dang_nhap_khach.post(GAP, json={"ma_phien": str(h2.ma_phien)})).status_code == 200
    await db.refresh(h2)
    assert h2.so_dien_thoai_goi_lai == dang_nhap_khach.tai_khoan.so_dien_thoai


async def test_phien_nguoi_khac_hoac_khong_co_thi_404(client, dang_nhap_khach, db):
    h = await mo_phien(db, dang_nhap_khach.tai_khoan)
    assert (await client.post(GAP, json={"ma_phien": str(h.ma_phien)})).status_code == 404
    assert (await client.post(GAP, json={"ma_phien": str(uuid.uuid4())})).status_code == 404


async def test_hang_cho_nhan_phien_va_hai_duoc_si_tranh_nhau(app, db, clients_theo_vai_tro):
    await dat_gio_lam_viec(db, [1, 2, 3, 4, 5, 6, 7])
    ds1 = clients_theo_vai_tro["PHARMACIST"]
    nv2 = await tao_nhan_vien(db, "PHARMACIST")
    h = await mo_phien(db)
    h.trang_thai, h.tom_tat = "cho_duoc_si", "Tóm tắt thử"
    await db.flush()
    async for ds2 in _dang_nhap(app, nv2, "noi_bo"):
        q = (await ds1.get(NB)).json()
        assert [x["id"] for x in q] == [h.id] and q[0]["tom_tat"] == "Tóm tắt thử"
        ok = await ds1.post(f"{NB}/{h.id}/nhan")
        assert (
            ok.status_code == 200
            and ok.json()["trang_thai"] == "duoc_si_dang_xu_ly"
            and ok.json()["duoc_si_cua_toi"] is True
        )
        assert (await ds2.post(f"{NB}/{h.id}/nhan")).status_code == 409
        assert (
            await ds2.get(f"{NB}/{h.id}")
        ).status_code == 403  # dược sĩ khác không xem phiên đang do người khác xử lý
        assert (await ds2.get(NB)).json() == []
        await db.refresh(h)
        assert h.loai == "duoc_si" and h.duoc_si_id is not None
        ds_khac = await ds2.post(f"{NB}/{h.id}/dong")
        assert ds_khac.status_code == 409


async def test_chi_tiet_chi_co_ho_so_khi_dong_y_va_dang_xu_ly_ghi_nhat_ky(app, db, clients_theo_vai_tro):
    ds = clients_theo_vai_tro["PHARMACIST"]
    khach = await tao_khach(db)
    hc = HoatChat(ten=f"Aspirin-{uuid.uuid4().hex[:4]}")
    db.add(hc)
    await db.flush()
    db.add(
        HoSoSucKhoe(
            khach_hang_id=khach.id, dong_y_su_dung=True, nam_sinh=1985, dang_mang_thai=False, benh_nen=ma_hoa("BÍ MẬT")
        )
    )
    db.add(DiUng(khach_hang_id=khach.id, hoat_chat_id=hc.id))
    h = await mo_phien(db, khach)
    h.trang_thai = "cho_duoc_si"
    await db.flush()
    cho = (await ds.get(f"{NB}/{h.id}")).json()
    assert cho["ho_so_suc_khoe"] is None  # chưa nhận phiên: chưa được đọc hồ sơ
    nhan = (await ds.post(f"{NB}/{h.id}/nhan")).json()
    assert nhan["ho_so_suc_khoe"]["nam_sinh"] == 1985 and nhan["ho_so_suc_khoe"]["di_ung"] == [hc.ten]
    assert "benh_nen" not in nhan["ho_so_suc_khoe"] and "BÍ MẬT" not in str(nhan)
    nk = (await db.execute(select(NhatKyHeThong).where(NhatKyHeThong.hanh_dong == "doc_suc_khoe"))).scalars().all()
    assert len(nk) >= 1
    # chưa đồng ý -> không có hồ sơ
    khach2 = await tao_khach(db)
    db.add(HoSoSucKhoe(khach_hang_id=khach2.id, dong_y_su_dung=False))
    h2 = await mo_phien(db, khach2)
    h2.trang_thai = "cho_duoc_si"
    await db.flush()
    assert (await ds.post(f"{NB}/{h2.id}/nhan")).json()["ho_so_suc_khoe"] is None


async def test_chi_duoc_si_va_phien_dang_mo_khong_vao_hang_cho(clients_theo_vai_tro, db):
    h = await mo_phien(db)  # còn đang chat với AI
    ds = clients_theo_vai_tro["PHARMACIST"]
    assert (await ds.get(f"{NB}/{h.id}")).status_code == 404 and (await ds.post(f"{NB}/{h.id}/nhan")).status_code == 404
    for v in ("WAREHOUSE", "ADMIN"):
        assert (await clients_theo_vai_tro[v].get(NB)).status_code == 403


async def test_dong_phien_cho_goi_lai_va_tin_nhan_rest(app, db, clients_theo_vai_tro):
    ds = clients_theo_vai_tro["PHARMACIST"]
    h = await mo_phien(db)
    h.trang_thai = "cho_goi_lai"
    await db.flush()
    r = await ds.post(f"{NB}/{h.id}/dong")
    assert r.status_code == 200 and r.json()["trang_thai"] == "da_dong"
    await db.refresh(h)
    assert h.dong_luc is not None
    h2 = await mo_phien(db)
    h2.trang_thai = "cho_duoc_si"
    await db.flush()
    assert (
        await ds.post(f"{NB}/{h2.id}/tin-nhan", json={"noi_dung": "Chào bạn"})
    ).status_code == 403  # chưa nhận phiên
    await ds.post(f"{NB}/{h2.id}/nhan")
    ok = await ds.post(f"{NB}/{h2.id}/tin-nhan", json={"noi_dung": "Chào bạn, mình là dược sĩ"})
    assert ok.status_code == 201 and ok.json()["vai_tro"] == "duoc_si"
    ls = (await ds.get(f"{NB}/{h2.id}")).json()["tin_nhan"]
    assert ls[-1]["noi_dung"] == "Chào bạn, mình là dược sĩ" and ls[-1]["vai_tro"] == "duoc_si"


# --- WebSocket (điều khiển bằng đối tượng giả trong cùng event loop vì DB test dùng một kết nối) ---


class WsGia:
    def __init__(self, *gui):
        self.vao: asyncio.Queue = asyncio.Queue()
        self.ra: list = []
        self.dong_voi: int | None = None
        for g in gui:
            self.vao.put_nowait(g)

    async def accept(self):
        pass

    async def receive_json(self):
        g = await self.vao.get()
        if g is None:
            from fastapi import WebSocketDisconnect

            raise WebSocketDisconnect()
        return g

    async def send_json(self, d):
        self.ra.append(d)

    async def close(self, code=1000):
        self.dong_voi = code


async def chay(app, ws_gia, ma_phien):
    tao = app.dependency_overrides[lay_tao_phien]()
    return asyncio.create_task(ws.phuc_vu(ws_gia, ma_phien, tao))


async def cho_den(dieu_kien, giay=3):
    for _ in range(int(giay / 0.02)):
        if dieu_kien():
            return
        await asyncio.sleep(0.02)
    raise AssertionError("hết giờ chờ")


async def test_websocket_khach_va_duoc_si_trao_doi(app, db, clients_theo_vai_tro, dang_nhap_khach):
    ds = clients_theo_vai_tro["PHARMACIST"]
    h = await mo_phien(db)
    h.trang_thai = "cho_duoc_si"
    await db.flush()
    nhan = (await ds.post(f"{NB}/{h.id}/nhan")).json()
    assert nhan["trang_thai"] == "duoc_si_dang_xu_ly"
    token_ds = ds.headers["Authorization"].removeprefix("Bearer ")
    k = WsGia({"loai": "xac_thuc", "vai_tro": "khach"})
    d = WsGia({"loai": "xac_thuc", "vai_tro": "duoc_si", "token": token_ds})
    tk = await chay(app, k, h.ma_phien)
    await cho_den(lambda: k.ra)  # DB test dùng chung một kết nối: xác thực lần lượt, không song song
    td = await chay(app, d, h.ma_phien)
    await cho_den(lambda: k.ra and d.ra)
    await k.vao.put({"loai": "tin_nhan", "noi_dung": "Thuốc này dùng sao?"})
    await cho_den(lambda: any(x.get("loai") == "tin_nhan" for x in d.ra))
    await d.vao.put({"loai": "tin_nhan", "noi_dung": "Bạn uống sau ăn nhé"})
    await cho_den(lambda: any(x.get("vai_tro") == "duoc_si" for x in k.ra))
    await k.vao.put({"loai": "dang_go"})
    await cho_den(lambda: any(x.get("loai") == "dang_go" for x in d.ra))
    assert not any(x.get("loai") == "dang_go" for x in k.ra)  # không dội lại cho người gõ
    luu = (
        (
            await db.execute(
                select(TinNhan)
                .where(TinNhan.hoi_thoai_id == h.id, TinNhan.vai_tro.in_(("khach", "duoc_si")))
                .order_by(TinNhan.id)
            )
        )
        .scalars()
        .all()
    )
    assert [t.noi_dung for t in luu][-2:] == ["Thuốc này dùng sao?", "Bạn uống sau ăn nhé"] and luu[
        -1
    ].nhan_vien_id is not None
    await k.vao.put(None)
    await d.vao.put(None)
    await asyncio.gather(tk, td)
    assert HUB.so_ket_noi(str(h.ma_phien)) == 0


async def test_websocket_tu_choi_sai_xac_thuc_sai_phien_va_dong_phien(app, db, clients_theo_vai_tro, dang_nhap_khach):
    ds = clients_theo_vai_tro["PHARMACIST"]
    token_ds = ds.headers["Authorization"].removeprefix("Bearer ")
    token_kho = clients_theo_vai_tro["WAREHOUSE"].headers["Authorization"].removeprefix("Bearer ")
    h = await mo_phien(db, dang_nhap_khach.tai_khoan)
    h.trang_thai = "cho_duoc_si"
    await db.flush()
    # message đầu không phải xác thực
    w = WsGia({"loai": "tin_nhan", "noi_dung": "x"})
    await (await chay(app, w, h.ma_phien))
    assert w.dong_voi == ws.MA_DONG_CHUA_XAC_THUC
    # vãng lai không vào được phiên của thành viên
    w = WsGia({"loai": "xac_thuc", "vai_tro": "khach"})
    await (await chay(app, w, h.ma_phien))
    assert w.dong_voi == ws.MA_DONG_KHONG_TIM_THAY
    # phiên không tồn tại
    w = WsGia({"loai": "xac_thuc", "vai_tro": "khach"})
    await (await chay(app, w, uuid.uuid4()))
    assert w.dong_voi == ws.MA_DONG_KHONG_TIM_THAY
    # nhân viên kho không phải dược sĩ; dược sĩ chưa nhận phiên
    for token in (token_kho, token_ds):
        w = WsGia({"loai": "xac_thuc", "vai_tro": "duoc_si", "token": token})
        await (await chay(app, w, h.ma_phien))
        assert w.dong_voi == ws.MA_DONG_KHONG_CO_QUYEN
    # token khách giả mạo vai dược sĩ
    w = WsGia(
        {"loai": "xac_thuc", "vai_tro": "duoc_si", "token": tao_access_token(dang_nhap_khach.tai_khoan.id, "khach")}
    )
    await (await chay(app, w, h.ma_phien))
    assert w.dong_voi == ws.MA_DONG_CHUA_XAC_THUC
    # thành viên vào phiên của mình; chat xong (da_dong) thì không gửi được nữa
    w = WsGia(
        {"loai": "xac_thuc", "vai_tro": "khach", "token": tao_access_token(dang_nhap_khach.tai_khoan.id, "khach")}
    )
    t = await chay(app, w, h.ma_phien)
    await cho_den(lambda: w.ra)
    h.trang_thai = "da_dong"
    await db.flush()
    await w.vao.put({"loai": "tin_nhan", "noi_dung": "còn đó không"})
    await cho_den(lambda: any(x.get("su_kien") == "loi" for x in w.ra))
    await w.vao.put({"loai": "khong_biet"})
    await w.vao.put(None)
    await t


# --- HT08 ---


async def test_ht08_dong_phien_khong_hoat_dong(db):
    cu = bay_gio_utc() - timedelta(minutes=45)
    moi = bay_gio_utc() - timedelta(minutes=5)
    h_cu = await mo_phien(db, tin=())
    h_cu.created_at = cu
    h_moi = await mo_phien(db, tin=())
    h_moi.created_at = moi
    h_co_tin = await mo_phien(db, tin=())
    h_co_tin.created_at = cu
    db.add(TinNhan(hoi_thoai_id=h_co_tin.id, vai_tro="khach", noi_dung="vừa nhắn", created_at=moi))
    h_cho = await mo_phien(db, trang_thai="cho_duoc_si", tin=())
    h_cho.created_at = cu
    h_chat = await mo_phien(db, trang_thai="duoc_si_dang_xu_ly", tin=())
    h_chat.created_at = bay_gio_utc() - timedelta(minutes=130)
    await db.flush()
    da_dong = await chuyen_duoc_si.dong_phien_khong_hoat_dong(db)
    assert set(da_dong) == {h_cu.id, h_chat.id}
    for h in (h_cu, h_moi, h_co_tin, h_cho, h_chat):
        await db.refresh(h)
    assert (h_cu.trang_thai, h_chat.trang_thai) == ("da_dong", "da_dong") and h_cu.dong_luc is not None
    assert (h_moi.trang_thai, h_co_tin.trang_thai, h_cho.trang_thai) == ("dang_mo", "dang_mo", "cho_duoc_si")
    assert await chuyen_duoc_si.dong_phien_khong_hoat_dong(db) == []  # chạy lại không đổi gì

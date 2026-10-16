"""T7.6: AI06 đọc ảnh đơn thuốc (job) và dược sĩ chốt danh sách thuốc (DS04). AI chỉ gợi ý."""

import io
import uuid

import pytest
from PIL import Image
from sqlalchemy import select

from app.ai import claude, gia_lap
from app.ai.doc_don_thuoc import DonThuocDoc
from app.core import luu_tru
from app.jobs.cong_viec import ai06_doc_don_thuoc
from app.models.ban_hang import CtYeuCauDonThuoc, YeuCauDonThuoc
from app.models.he_thong import CauHinh
from app.models.san_pham import HoatChat, ThanhPhan
from app.modules.don_thuoc.doc_anh_ai import goi_y_san_pham
from tests.factories import tao_san_pham

BASE = "/api/v1/noi-bo/don-thuoc"


def png() -> bytes:
    b = io.BytesIO()
    Image.new("RGB", (80, 60), (240, 240, 240)).save(b, format="PNG")
    return b.getvalue()


async def yeu_cau(db, so_anh=1, trang_thai="cho_duyet", **kw):
    kho = luu_tru.luu_tru()
    khoa = [await kho.luu("don-thuoc", png(), "image/png", vung="rieng_tu") for _ in range(so_anh)]
    yc = YeuCauDonThuoc(
        ma_yeu_cau="YC" + uuid.uuid4().hex[:8].upper(), ho_ten="Nguyễn Văn A", so_dien_thoai="0912345678",
        anh_don_thuoc=khoa, hash_anh=uuid.uuid4().hex, trang_thai=trang_thai, **kw,
    )  # fmt: skip
    db.add(yc)
    await db.flush()
    return yc


def thuoc(ten, hl=None, sl="20 viên", tin_cay=0.9, cach_dung=None):
    return {
        "ten_thuoc_tren_don": ten,
        "ham_luong": hl,
        "so_luong_ke": sl,
        "cach_dung": cach_dung,
        "do_tin_cay": tin_cay,
    }


def kich_ban(*ds, ngay="2026-10-10", chu_ky=True):
    gia_lap.KICH_BAN.goi_json = lambda **kw: {"ngay_ke": ngay, "co_chu_ky_bac_si": chu_ky, "danh_sach_thuoc": list(ds)}


async def dong_cua(db, yc):
    return (
        (
            await db.execute(
                select(CtYeuCauDonThuoc).where(CtYeuCauDonThuoc.yeu_cau_id == yc.id).order_by(CtYeuCauDonThuoc.id)
            )
        )
        .scalars()
        .all()
    )


# --- chuẩn hóa kết quả AI ---


def test_ket_qua_ai_bi_cat_kep_va_ngay_sai_thanh_none():
    d = DonThuocDoc.model_validate(
        {
            "ngay_ke": "không phải ngày",
            "co_chu_ky_bac_si": True,
            "danh_sach_thuoc": [
                {
                    "ten_thuoc_tren_don": "x" * 400,
                    "ham_luong": "  ",
                    "so_luong_ke": None,
                    "cach_dung": None,
                    "do_tin_cay": 5,
                }
            ],
        }
    )
    t = d.danh_sach_thuoc[0]
    assert d.ngay_ke is None and len(t.ten_thuoc_tren_don) == 255 and t.ham_luong is None and t.do_tin_cay == 1.0


# --- job ---


async def test_job_doc_anh_ghi_ket_qua_va_dong_thuoc_kem_goi_y(db):
    hc = HoatChat(ten=f"Amoxicillin-{uuid.uuid4().hex[:5]}")
    db.add(hc)
    await db.flush()
    sp = await tao_san_pham(db, "thuoc_ke_don", ten="Augmentin Zeta")
    db.add(ThanhPhan(san_pham_id=sp.id, hoat_chat_id=hc.id, ham_luong="625 mg"))
    await db.flush()
    yc = await yeu_cau(db, so_anh=2)
    kich_ban(
        thuoc("Augmentin Zeta", "625mg", "14 viên", 0.82, "Ngày 2 lần"), thuoc("Thuốc lạ hoắc xyz", None, None, 0.3)
    )
    kq = await ai06_doc_don_thuoc(db)
    assert yc.ma_yeu_cau in kq.da_doc and not kq.loi
    await db.refresh(yc)
    assert (
        yc.ket_qua_ai["trang_thai"] == "xong"
        and yc.ket_qua_ai["ngay_ke"] == "2026-10-10"
        and yc.ket_qua_ai["co_chu_ky_bac_si"] is True
    )
    assert yc.ket_qua_ai["danh_sach_thuoc"][0]["cach_dung"] == "Ngày 2 lần"
    a, b = await dong_cua(db, yc)
    assert (a.ten_thuoc_tren_don, a.ham_luong, a.so_luong_ke) == ("Augmentin Zeta", "625mg", "14 viên")
    assert float(a.do_tin_cay_ai) == 0.82 and a.san_pham_id == sp.id and a.do_duoc_si_nhap is False
    assert b.san_pham_id is None and float(b.do_tin_cay_ai) == 0.3
    khoi = gia_lap.KICH_BAN.lan_goi_json[-1]["noi_dung"]
    assert [k["type"] for k in khoi] == ["image", "image", "text"]  # nhiều ảnh trong một lời gọi, ảnh trước chữ


async def test_job_khong_doc_lai_va_khong_ghi_de_dong_da_co(db):
    yc = await yeu_cau(db)
    db.add(CtYeuCauDonThuoc(yeu_cau_id=yc.id, ten_thuoc_tren_don="Dược sĩ nhập trước", do_duoc_si_nhap=True))
    await db.flush()
    kich_ban(thuoc("Thuốc AI"))
    await ai06_doc_don_thuoc(db)
    assert [c.ten_thuoc_tren_don for c in await dong_cua(db, yc)] == ["Dược sĩ nhập trước"]  # chỉ ghi ket_qua_ai
    await db.refresh(yc)
    assert yc.ket_qua_ai["trang_thai"] == "xong"
    so_lan = gia_lap.KICH_BAN.so_lan_goi_json
    await ai06_doc_don_thuoc(db)
    assert gia_lap.KICH_BAN.so_lan_goi_json == so_lan


async def test_job_chi_doc_yeu_cau_chua_xu_ly(db):
    for tt in ("da_tao_don", "tu_choi", "khach_huy"):
        await yeu_cau(db, trang_thai=tt)
    cho = await yeu_cau(db)
    dang = await yeu_cau(db, trang_thai="dang_tu_van")
    kich_ban(thuoc("Paracetamol"))
    kq = await ai06_doc_don_thuoc(db)
    assert set(kq.da_doc) == {cho.ma_yeu_cau, dang.ma_yeu_cau} and gia_lap.KICH_BAN.so_lan_goi_json == 2


async def test_job_loi_ai_thu_lai_toi_da_ba_lan_va_van_duyet_duoc(db):
    yc = await yeu_cau(db)

    def hong(**kw):
        raise claude.AiLoi("x")

    gia_lap.KICH_BAN.goi_json = hong
    for lan in (1, 2, 3):
        kq = await ai06_doc_don_thuoc(db)
        assert kq.loi == [yc.ma_yeu_cau]
        await db.refresh(yc)
        assert yc.ket_qua_ai == {"trang_thai": "loi", "ly_do": "ai_loi", "lan_thu": lan}
    assert (await ai06_doc_don_thuoc(db)).loi == []  # quá 3 lần thì thôi
    assert await dong_cua(db, yc) == []


async def test_job_ai_tu_choi_hoac_anh_hong_khong_thu_lai(db):
    tu_choi = await yeu_cau(db)

    def bi_chan(**kw):
        raise claude.AiTuChoi("x")

    gia_lap.KICH_BAN.goi_json = bi_chan
    await ai06_doc_don_thuoc(db)
    await db.refresh(tu_choi)
    assert tu_choi.ket_qua_ai["ly_do"] == "ai_tu_choi" and tu_choi.ket_qua_ai["lan_thu"] == 3
    hong = await yeu_cau(db)
    hong.anh_don_thuoc = ["don-thuoc/khong-ton-tai.png"]
    await db.flush()
    kich_ban(thuoc("x"))
    await ai06_doc_don_thuoc(db)
    await db.refresh(hong)
    assert hong.ket_qua_ai["ly_do"] == "anh_hong"


async def test_job_module_tat_khong_goi_ai(db):
    gia_tri = dict.fromkeys(("tim_kiem", "chat", "tra_anh", "goi_y", "du_bao"), True) | {"doc_don_thuoc": False}
    cu = await db.get(CauHinh, "ai_module")
    if cu is None:
        db.add(CauHinh(khoa="ai_module", gia_tri=gia_tri))
    else:
        cu.gia_tri = gia_tri
    await db.flush()
    yc = await yeu_cau(db)
    kq = await ai06_doc_don_thuoc(db)
    assert kq.da_doc == [] and gia_lap.KICH_BAN.so_lan_goi_json == 0
    await db.refresh(yc)
    assert yc.ket_qua_ai is None


# --- gợi ý sản phẩm ---


async def test_goi_y_uu_tien_ham_luong_va_chi_tu_tin_khi_ten_gan_nhu_trung(db):
    ten = f"Zorvex{uuid.uuid4().hex[:4]}"
    hc = HoatChat(ten=f"Zorvexin-{uuid.uuid4().hex[:5]}")
    db.add(hc)
    await db.flush()
    a = await tao_san_pham(db, ten=f"{ten} 250")
    b = await tao_san_pham(db, ten=f"{ten} 500")
    db.add_all([ThanhPhan(san_pham_id=a.id, hoat_chat_id=hc.id, ham_luong="250mg")])
    db.add_all([ThanhPhan(san_pham_id=b.id, hoat_chat_id=hc.id, ham_luong="500 mg")])
    await db.flush()
    assert await goi_y_san_pham(db, ten, "500mg") == b.id
    assert await goi_y_san_pham(db, ten, "250 MG") == a.id
    assert await goi_y_san_pham(db, "thuốc không tồn tại abcxyz", "5mg") is None
    assert await goi_y_san_pham(db, "a", None) is None


# --- DS04: màn duyệt hiện gợi ý, dược sĩ chốt ---


async def mo_phien_xu_ly(client, yc):
    return (await client.post(f"{BASE}/{yc.id}/nhan")).json()


async def test_man_duyet_co_id_do_tin_cay_va_chot_danh_sach(dang_nhap_duoc_si, db):
    yc = await yeu_cau(db)
    kich_ban(
        thuoc("Thuốc A", "5 mg", "10 viên", 0.9),
        thuoc("Thuốc B", None, "5 viên", 0.4),
        thuoc("Thuốc C", None, None, 0.7),
    )
    await ai06_doc_don_thuoc(db)
    sp = await tao_san_pham(db, ten="Sản phẩm chọn tay")
    d = await mo_phien_xu_ly(dang_nhap_duoc_si, yc)
    a, b, c = d["thuoc_tren_don"]
    assert (
        (a["do_tin_cay_ai"], a["do_duoc_si_nhap"]) == ("0.90", False)
        and a["id"]
        and d["ket_qua_ai"]["trang_thai"] == "xong"
    )
    r = await dang_nhap_duoc_si.put(
        f"{BASE}/{yc.id}/thuoc-tren-don",
        json={
            "dong": [
                {
                    "id": a["id"],
                    "ten_thuoc_tren_don": "Thuốc A",
                    "ham_luong": "5 mg",
                    "so_luong_ke": "10 viên",
                    "san_pham_id": sp.id,
                },
                {
                    "id": b["id"],
                    "ten_thuoc_tren_don": "Thuốc B (đã sửa)",
                    "ham_luong": None,
                    "so_luong_ke": "5 viên",
                    "san_pham_id": None,
                },
                {"ten_thuoc_tren_don": "Thuốc nhập tay", "so_luong_ke": "2 hộp"},
            ]
        },
    )
    assert r.status_code == 200, r.text
    moi = {x["ten_thuoc_tren_don"]: x for x in r.json()["thuoc_tren_don"]}
    assert set(moi) == {"Thuốc A", "Thuốc B (đã sửa)", "Thuốc nhập tay"}  # dòng C vắng mặt bị xóa
    assert (
        moi["Thuốc A"]["san_pham_id"] == sp.id
        and moi["Thuốc A"]["do_tin_cay_ai"] == "0.90"
        and moi["Thuốc A"]["do_duoc_si_nhap"] is False
    )
    assert moi["Thuốc B (đã sửa)"]["do_duoc_si_nhap"] is True and moi["Thuốc B (đã sửa)"]["do_tin_cay_ai"] is None
    assert moi["Thuốc nhập tay"]["do_duoc_si_nhap"] is True and moi["Thuốc nhập tay"]["id"] != c["id"]
    assert len(await dong_cua(db, yc)) == 3


async def test_chot_danh_sach_kiem_tra_dau_vao(dang_nhap_duoc_si, db):
    yc = await yeu_cau(db)
    khac = await yeu_cau(db)
    db.add(CtYeuCauDonThuoc(yeu_cau_id=khac.id, ten_thuoc_tren_don="của yêu cầu khác"))
    await db.flush()
    id_khac = (await dong_cua(db, khac))[0].id
    await mo_phien_xu_ly(dang_nhap_duoc_si, yc)
    url = f"{BASE}/{yc.id}/thuoc-tren-don"
    truong = lambda r: r.json()["chi_tiet"][0]["truong"]  # noqa: E731
    r = await dang_nhap_duoc_si.put(url, json={"dong": [{"id": id_khac, "ten_thuoc_tren_don": "x"}]})
    assert r.status_code == 400 and truong(r) == "dong.0.id"
    r = await dang_nhap_duoc_si.put(url, json={"dong": [{"ten_thuoc_tren_don": "x", "san_pham_id": 2_000_000_000}]})
    assert r.status_code == 400 and truong(r) == "dong.0.san_pham_id"
    assert (await dang_nhap_duoc_si.put(url, json={"dong": [{"ten_thuoc_tren_don": "   "}]})).status_code == 400
    assert (await dang_nhap_duoc_si.put(url, json={"dong": [{"ten_thuoc_tren_don": "x"}] * 51})).status_code == 400
    assert (await dang_nhap_duoc_si.put(url, json={"dong": [], "them": 1})).status_code == 400
    assert (await dang_nhap_duoc_si.put(url, json={"dong": []})).status_code == 200  # xóa hết cũng được


@pytest.mark.parametrize("cach", ["chua_nhan", "khoa_boi_nguoi_khac"])
async def test_chot_danh_sach_can_khoa_yeu_cau(dang_nhap_duoc_si, db, cach):
    from tests.factories import tao_nhan_vien

    khac = await tao_nhan_vien(db)
    yc = (
        await yeu_cau(db)
        if cach == "chua_nhan"
        else await yeu_cau(
            db,
            trang_thai="dang_tu_van",
            duoc_si_id=khac.id,
            khoa_luc=__import__("app.core.thoi_gian", fromlist=["x"]).bay_gio_utc(),
        )
    )
    r = await dang_nhap_duoc_si.put(f"{BASE}/{yc.id}/thuoc-tren-don", json={"dong": []})
    assert r.status_code == 403


async def test_chi_duoc_si_chot_danh_sach(clients_theo_vai_tro, db):
    yc = await yeu_cau(db)
    for v in ("WAREHOUSE", "ADMIN"):
        assert (
            await clients_theo_vai_tro[v].put(f"{BASE}/{yc.id}/thuoc-tren-don", json={"dong": []})
        ).status_code == 403

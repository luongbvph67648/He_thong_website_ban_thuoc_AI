"""T7.8: che thông tin cá nhân, đánh giá câu trả lời AI (DS12) và giám sát hội thoại AI (AD11)."""

import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.an_danh import che_thong_tin
from app.core.thoi_gian import VN_TZ, bay_gio_utc
from app.models.ai import DanhGiaCauTraLoi, HoiThoai, LichSuTimKiem, TinNhan
from app.models.he_thong import NhatKyHeThong
from tests.factories import tao_khach

DS12 = "/api/v1/noi-bo/danh-gia-ai"
AD11 = "/api/v1/noi-bo/giam-sat-ai"


# --- che thông tin ---


@pytest.mark.parametrize(
    ("goc", "mong"),
    [
        ("Gọi mình số 0912 345 678 nhé", "Gọi mình số [SĐT] nhé"),
        ("sdt +84 912-345-678 hoặc 0987654321", "sdt [SĐT] hoặc [SĐT]"),
        ("mail an.nguyen+x@gmail.com đây", "mail [email] đây"),
        ("CCCD 012345678901 của mình", "CCCD [số] của mình"),
        ("Tên tôi là Nguyễn Văn An, 35 tuổi", "Tên tôi là [tên], 35 tuổi"),
        ("tôi tên Lan bị ho", "tôi tên [tên] bị ho"),
        ("tôi tên lan bị ho", "tôi tên lan bị ho"),  # chữ thường sau "tên": không đoán
        ("Paracetamol 500 mg uống 2 viên", "Paracetamol 500 mg uống 2 viên"),
        ("giá 125000 đồng 3 hộp", "giá 125000 đồng 3 hộp"),  # số ngắn, không che
    ],
)
def test_che_thong_tin(goc, mong):
    assert che_thong_tin(goc) == mong


def test_che_ten_khach_dang_nhap_day_du_va_tung_tu_tu_3_ky_tu():
    ten = "Trần Thị Lan"
    assert che_thong_tin("Chào Trần Thị Lan, chị Lan có thể dùng", ten) == "Chào [tên], chị [tên] có thể dùng"
    assert che_thong_tin("TRẦN THỊ LAN", ten) == "[tên]"
    assert che_thong_tin("lanh lợi", ten) == "lanh lợi"  # chỉ khớp nguyên từ
    # tên có từ 2 ký tự ("An") không bị che riêng vì trùng từ thông dụng ("an toàn"); tên đầy đủ vẫn bị che
    assert che_thong_tin("Vũ An dùng thuốc an toàn", "Vũ An") == "[tên] dùng thuốc an toàn"
    assert che_thong_tin("", ten) == "" and che_thong_tin(None) == ""


# --- dữ liệu ---


async def hoi_thoai(db, khach=None, *, gan_co=False, loai="ai", ngay=0, tin=(), **kw):
    h = HoiThoai(
        ma_phien=uuid.uuid4(), khach_hang_id=None if khach is None else khach.id, bi_gan_co=gan_co, loai=loai,
        ly_do_gan_co="dau_hieu_nguy_hiem" if gan_co else None, created_at=bay_gio_utc() - timedelta(days=ngay),
        ip_hash="iphash-bi-mat", **kw,
    )  # fmt: skip
    db.add(h)
    await db.flush()
    ds = []
    for vai_tro, nd, *ph in tin:
        t = TinNhan(hoi_thoai_id=h.id, vai_tro=vai_tro, noi_dung=nd, y_dinh=ph[0] if ph else None)
        db.add(t)
        ds.append(t)
    await db.flush()
    return h, ds


async def khach_bao_sai(db, tin_nhan, khach=None):
    db.add(
        DanhGiaCauTraLoi(
            tin_nhan_id=tin_nhan.id, nguon="khach", ket_qua="khong_huu_ich", khach_hang_id=khach and khach.id
        )
    )
    await db.flush()


# --- DS12 ---


async def test_ds12_chi_hien_hoi_thoai_bi_gan_co_va_khach_bao_sai_va_che_thong_tin(clients_theo_vai_tro, db):
    ds = clients_theo_vai_tro["PHARMACIST"]
    khach = await tao_khach(db, ho_ten="Lê Văn Bình")
    sai, tin_sai = await hoi_thoai(
        db,
        khach,
        tin=[("khach", "Lê Văn Bình đây, gọi 0912345678 giúp", "hoi_san_pham"), ("ai", "Dùng 5 viên mỗi ngày")],
    )
    await khach_bao_sai(db, tin_sai[1], khach)
    nguy_hiem, _ = await hoi_thoai(db, gan_co=True, tin=[("khach", "Tôi đau ngực dữ dội"), ("ai", "Hãy gọi 115")])
    binh_thuong, _ = await hoi_thoai(db, tin=[("khach", "Panadol dùng sao"), ("ai", "Uống 1 viên")])
    r = await ds.get(DS12)
    assert r.status_code == 200
    d = r.json()
    ids = [x["id"] for x in d["du_lieu"]]
    assert sai.id in ids and nguy_hiem.id in ids and binh_thuong.id not in ids
    muc = next(x for x in d["du_lieu"] if x["id"] == sai.id)
    assert (
        muc["so_khach_bao_sai"] == 1
        and muc["so_tin_nhan"] == 2
        and "[tên]" in muc["cau_hoi_dau"]
        and "[SĐT]" in muc["cau_hoi_dau"]
    )
    thô = r.text
    assert (
        "0912345678" not in thô
        and "Bình" not in thô
        and "iphash" not in thô
        and "ma_phien" not in thô
        and "khach_hang_id" not in thô
    )


async def test_ds12_chi_tiet_che_noi_dung_va_chi_hoi_thoai_gan_co(clients_theo_vai_tro, db):
    ds = clients_theo_vai_tro["PHARMACIST"]
    khach = await tao_khach(db, ho_ten="Lê Văn Bình")
    h, tin = await hoi_thoai(
        db, khach, gan_co=True, tin=[("khach", "Em Lê Văn Bình, số 0912345678"), ("ai", "Chào Bình")]
    )
    d = (await ds.get(f"{DS12}/{h.id}")).json()
    assert [t["noi_dung"] for t in d["tin_nhan"]] == ["Em [tên], số [SĐT]", "Chào [tên]"]
    ok, _ = await hoi_thoai(db, tin=[("khach", "xin chào"), ("ai", "chào bạn")])
    assert (await ds.get(f"{DS12}/{ok.id}")).status_code == 404  # không gắn cờ: dược sĩ không có lý do đọc
    assert (await ds.get(f"{DS12}/999999999")).status_code == 404 and tin


async def test_ds12_loc_chua_danh_gia(clients_theo_vai_tro, db):
    ds = clients_theo_vai_tro["PHARMACIST"]
    a, ta = await hoi_thoai(db, gan_co=True, tin=[("khach", "q"), ("ai", "a")])
    b, _ = await hoi_thoai(db, gan_co=True, tin=[("khach", "q"), ("ai", "a")])
    assert (await ds.put(f"{DS12}/{a.id}/tin-nhan/{ta[1].id}", json={"ket_qua": "dung"})).status_code == 200
    ids = [x["id"] for x in (await ds.get(DS12, params={"chua_danh_gia": True})).json()["du_lieu"]]
    assert b.id in ids and a.id not in ids
    muc = next(x for x in (await ds.get(DS12)).json()["du_lieu"] if x["id"] == a.id)
    assert muc["so_duoc_si_danh_gia"] == 1


async def test_ds12_danh_dau_dung_sai_ghi_chu_va_sua_lai(dang_nhap_duoc_si, db):
    ds = dang_nhap_duoc_si
    h, tin = await hoi_thoai(db, gan_co=True, tin=[("khach", "Liều Paracetamol?"), ("ai", "Uống 10 viên")])
    url = f"{DS12}/{h.id}/tin-nhan/{tin[1].id}"
    thieu = await ds.put(url, json={"ket_qua": "sai"})
    assert thieu.status_code == 400 and thieu.json()["chi_tiet"][0]["truong"] == "ghi_chu"
    assert (await ds.put(url, json={"ket_qua": "sai", "ghi_chu": "ab"})).status_code == 400
    r = await ds.put(url, json={"ket_qua": "sai", "ghi_chu": "Tối đa 4 g mỗi ngày, mỗi lần 500-1000 mg"})
    assert r.status_code == 200
    dg = r.json()["tin_nhan"][1]["danh_gia"]
    assert dg == [
        {"nguon": "duoc_si", "ket_qua": "sai", "ghi_chu": "Tối đa 4 g mỗi ngày, mỗi lần 500-1000 mg", "cua_toi": True}
    ]
    r2 = await ds.put(url, json={"ket_qua": "dung"})  # sửa lại, vẫn một đánh giá
    assert (
        r2.json()["tin_nhan"][1]["danh_gia"][0]["ket_qua"] == "dung"
        and r2.json()["tin_nhan"][1]["danh_gia"][0]["ghi_chu"] is None
    )
    n = (await db.execute(select(DanhGiaCauTraLoi).where(DanhGiaCauTraLoi.tin_nhan_id == tin[1].id))).scalars().all()
    assert len(n) == 1 and n[0].nguon == "duoc_si" and n[0].nhan_vien_id == ds.tai_khoan.id
    nk = (await db.execute(select(NhatKyHeThong).where(NhatKyHeThong.hanh_dong == "danh_gia_ai"))).scalars().all()
    assert len(nk) == 2


async def test_ds12_chi_danh_gia_tin_ai_trong_hoi_thoai_gan_co(clients_theo_vai_tro, db):
    ds = clients_theo_vai_tro["PHARMACIST"]
    h, tin = await hoi_thoai(db, gan_co=True, tin=[("khach", "q"), ("ai", "a")])
    khac, tin_khac = await hoi_thoai(db, gan_co=True, tin=[("khach", "q"), ("ai", "a")])
    ok, tin_ok = await hoi_thoai(db, tin=[("khach", "q"), ("ai", "a")])
    body = {"ket_qua": "dung"}
    assert (await ds.put(f"{DS12}/{h.id}/tin-nhan/{tin[0].id}", json=body)).status_code == 404  # tin của khách
    assert (
        await ds.put(f"{DS12}/{h.id}/tin-nhan/{tin_khac[1].id}", json=body)
    ).status_code == 404  # tin của hội thoại khác
    assert (
        await ds.put(f"{DS12}/{ok.id}/tin-nhan/{tin_ok[1].id}", json=body)
    ).status_code == 404  # hội thoại không gắn cờ
    assert (await ds.put(f"{DS12}/{h.id}/tin-nhan/{tin[1].id}", json={"ket_qua": "huu_ich"})).status_code == 400
    assert khac.id


async def test_ds12_admin_chi_xem_khong_ghi_va_kho_khong_vao(clients_theo_vai_tro, db):
    h, tin = await hoi_thoai(db, gan_co=True, tin=[("khach", "q"), ("ai", "a")])
    admin, kho = clients_theo_vai_tro["ADMIN"], clients_theo_vai_tro["WAREHOUSE"]
    assert (await admin.get(DS12)).status_code == 200 and (await admin.get(f"{DS12}/{h.id}")).status_code == 200
    assert (await admin.put(f"{DS12}/{h.id}/tin-nhan/{tin[1].id}", json={"ket_qua": "dung"})).status_code == 403
    assert (await kho.get(DS12)).status_code == 403


# --- AD11 ---


async def test_ad11_thong_ke(clients_theo_vai_tro, db):
    ad = clients_theo_vai_tro["ADMIN"]
    khach = await tao_khach(db)
    base = (await ad.get(f"{AD11}/thong-ke")).json()
    h1, t1 = await hoi_thoai(
        db,
        khach,
        loai="duoc_si",
        tong_token=1000,
        chi_phi=Decimal("0.5"),
        tin=[("khach", "a", "hoi_san_pham"), ("ai", "b")],
    )
    h2, t2 = await hoi_thoai(
        db,
        gan_co=True,
        tong_token=500,
        chi_phi=Decimal("0.25"),
        tin=[("khach", "c", "hoi_san_pham"), ("khach", "d", "chinh_sach"), ("ai", "e")],
    )
    await hoi_thoai(
        db, ngay=60, tong_token=9999, chi_phi=Decimal(9), tin=[("khach", "cũ", "hoi_san_pham")]
    )  # ngoài khoảng mặc định
    await khach_bao_sai(db, t1[1])
    db.add_all(
        [
            DanhGiaCauTraLoi(tin_nhan_id=t2[2].id, nguon="khach", ket_qua="huu_ich"),
            DanhGiaCauTraLoi(tin_nhan_id=t2[2].id, nguon="duoc_si", ket_qua="sai", ghi_chu="x"),
        ]
    )
    await db.flush()
    d = (await ad.get(f"{AD11}/thong-ke")).json()
    chenh = lambda k: d[k] - base[k]  # noqa: E731
    assert chenh("tong_hoi_thoai") == 2 and chenh("so_chuyen_duoc_si") == 1 and chenh("so_gan_co") == 2
    assert chenh("tong_token") == 1500 and Decimal(d["tong_chi_phi_usd"]) - Decimal(
        base["tong_chi_phi_usd"]
    ) == Decimal("0.75")
    pb = {x["y_dinh"]: x["so_luong"] for x in d["cau_hoi_pho_bien"]}
    pb0 = {x["y_dinh"]: x["so_luong"] for x in base["cau_hoi_pho_bien"]}
    assert pb["hoi_san_pham"] - pb0.get("hoi_san_pham", 0) == 2 and pb["chinh_sach"] - pb0.get("chinh_sach", 0) == 1
    assert d["danh_gia"]["khach_khong_huu_ich"] - base["danh_gia"]["khach_khong_huu_ich"] == 1
    assert d["danh_gia"]["duoc_si_sai"] - base["danh_gia"]["duoc_si_sai"] == 1
    assert 0 <= float(d["ty_le_chuyen_duoc_si"]) <= 1 and d["tu_ngay"] and d["den_ngay"]


async def test_ad11_ty_le_chuyen_duoc_si_va_khoang_ngay(clients_theo_vai_tro, db):
    ad = clients_theo_vai_tro["ADMIN"]
    ngay = (bay_gio_utc() - timedelta(days=400)).astimezone(VN_TZ).date().isoformat()
    r = await ad.get(f"{AD11}/thong-ke", params={"tu_ngay": ngay, "den_ngay": ngay})
    assert r.json()["tong_hoi_thoai"] == 0 and r.json()["ty_le_chuyen_duoc_si"] is None  # không chia cho 0
    for _ in range(4):
        await hoi_thoai(db, ngay=400)
    await hoi_thoai(db, ngay=400, loai="duoc_si")
    d = (await ad.get(f"{AD11}/thong-ke", params={"tu_ngay": ngay, "den_ngay": ngay})).json()
    assert d["tong_hoi_thoai"] == 5 and d["ty_le_chuyen_duoc_si"] == "0.2000"
    sai = await ad.get(f"{AD11}/thong-ke", params={"tu_ngay": "2026-10-10", "den_ngay": "2026-10-01"})
    assert sai.status_code == 400 and sai.json()["chi_tiet"][0]["truong"] == "tu_ngay"


async def test_ad11_danh_sach_loc_va_an_danh(clients_theo_vai_tro, db):
    ad = clients_theo_vai_tro["ADMIN"]
    khach = await tao_khach(db, ho_ten="Phạm Quốc Cường")
    a, _ = await hoi_thoai(
        db, khach, gan_co=True, loai="duoc_si", tin=[("khach", "Tôi Phạm Quốc Cường, 0911222333 bị ho")]
    )
    b, _ = await hoi_thoai(db, tin=[("khach", "x" * 300)])
    r = await ad.get(f"{AD11}/hoi-thoai", params={"bi_gan_co": True, "da_chuyen_duoc_si": True})
    ids = [x["id"] for x in r.json()["du_lieu"]]
    assert a.id in ids and b.id not in ids
    assert "0911222333" not in r.text and "Cường" not in r.text and "ma_phien" not in r.text and "iphash" not in r.text
    ds2 = (await ad.get(f"{AD11}/hoi-thoai", params={"bi_gan_co": False})).json()["du_lieu"]
    muc_b = next(x for x in ds2 if x["id"] == b.id)
    assert len(muc_b["cau_hoi_dau"]) == 120 and muc_b["cau_hoi_dau"].endswith("…")
    ct = (await ad.get(f"{AD11}/hoi-thoai/{a.id}")).json()
    assert ct["tin_nhan"][0]["noi_dung"] == "Tôi [tên], [SĐT] bị ho"
    assert (await ad.get(f"{AD11}/hoi-thoai/987654321")).status_code == 404


async def test_ad11_tim_kiem_khong_ket_qua_gop_va_che(clients_theo_vai_tro, db):
    ad = clients_theo_vai_tro["ADMIN"]

    def moi(tk, so=0, ngay=0):
        return LichSuTimKiem(
            tu_khoa=tk, so_ket_qua=so, che_do="hybrid", created_at=bay_gio_utc() - timedelta(days=ngay)
        )

    db.add_all(
        [
            moi("Thuốc Lạ"),
            moi("thuốc lạ "),
            moi("thuốc lạ"),
            moi("có kết quả", so=3),
            moi("quá cũ", ngay=90),
            moi("gọi 0912345678"),
        ]
    )
    await db.flush()
    d = (await ad.get(f"{AD11}/tim-kiem-khong-ket-qua")).json()
    theo = {x["tu_khoa"]: x["so_lan"] for x in d}
    assert theo["thuốc lạ"] == 3 and "có kết quả" not in theo and "quá cũ" not in theo
    assert theo["gọi [SĐT]"] == 1 and "0912345678" not in str(d)


async def test_ad11_phan_quyen(clients_theo_vai_tro):
    for v in ("PHARMACIST", "WAREHOUSE"):
        for p in ("thong-ke", "hoi-thoai", "tim-kiem-khong-ket-qua"):
            assert (await clients_theo_vai_tro[v].get(f"{AD11}/{p}")).status_code == 403

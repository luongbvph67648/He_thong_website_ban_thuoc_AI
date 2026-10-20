"""KVL08, KTV07: gửi ảnh đơn thuốc, theo dõi, hủy; ảnh riêng tư qua URL ký (T5.2)."""

import time
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core import luu_tru
from app.core.thoi_gian import bay_gio_utc
from app.models.ban_hang import YeuCauDonThuoc
from tests.factories import tao_khach, tao_nhan_vien

SDT = "0912345678"
PNG = b"\x89PNG\r\n\x1a\n" + b"du-lieu-anh-don-thuoc" * 20
JPG = b"\xff\xd8\xff\xe0" + b"anh-thu-hai" * 20


def _anh(*noi_dung):
    return [("anh", (f"a{i}.png", n, "image/png")) for i, n in enumerate(noi_dung)]


async def _xin_otp(client, sdt=SDT):
    r = await client.post("/api/v1/auth/otp", json={"so_dien_thoai": sdt, "muc_dich": "don_thuoc_khach"})
    assert r.status_code == 200, r.text


async def _gui_vang_lai(client, kenh, anh=None, **data):
    await _xin_otp(client, data.get("so_dien_thoai", SDT))
    body = {"ho_ten": "Nguyễn Văn A", "so_dien_thoai": SDT, "otp": kenh.ma_otp_cuoi(), **data}
    return await client.post("/api/v1/don-thuoc", data=body, files=anh or _anh(PNG))


async def test_vang_lai_gui_don_can_otp(client, kenh_tin_nhan, db):
    r = await _gui_vang_lai(client, kenh_tin_nhan, ghi_chu="đau họng")
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["trang_thai"] == "cho_duyet" and d["ma_yeu_cau"].startswith("YC")
    yc = (await db.execute(select(YeuCauDonThuoc))).scalars().one()
    assert yc.khach_hang_id is None and yc.so_dien_thoai == SDT and yc.kenh == "online"
    assert yc.hash_anh and len(yc.anh_don_thuoc) == 1 and yc.anh_don_thuoc[0].startswith("don-thuoc/")
    # Ảnh nằm ở vùng riêng tư, không đọc được qua đường công khai.
    assert await luu_tru.luu_tru().doc(yc.anh_don_thuoc[0], "rieng_tu") == PNG
    assert (await client.get("/api/v1/tep/" + yc.anh_don_thuoc[0])).status_code == 404


async def test_vang_lai_thieu_hoac_sai_otp(client, kenh_tin_nhan, db):
    r = await client.post("/api/v1/don-thuoc", data={"ho_ten": "A", "so_dien_thoai": SDT}, files=_anh(PNG))
    assert r.status_code == 400
    await _xin_otp(client)
    r = await client.post(
        "/api/v1/don-thuoc", data={"ho_ten": "A", "so_dien_thoai": SDT, "otp": "000000"}, files=_anh(PNG)
    )
    assert r.status_code == 422 and r.json()["ma_loi"] == "OTP_SAI"
    # OTP của mục đích khác không dùng được.
    assert (await db.execute(select(YeuCauDonThuoc))).first() is None


async def test_otp_dang_ky_khong_dung_cho_don_thuoc(client, kenh_tin_nhan):
    r = await client.post("/api/v1/auth/otp", json={"so_dien_thoai": SDT, "muc_dich": "dang_ky"})
    assert r.status_code == 200
    r = await client.post(
        "/api/v1/don-thuoc",
        data={"ho_ten": "A", "so_dien_thoai": SDT, "otp": kenh_tin_nhan.ma_otp_cuoi()},
        files=_anh(PNG),
    )
    assert r.status_code == 422


@pytest.mark.parametrize(
    "files",
    [[], _anh(b"khong-phai-anh" * 10), _anh(*[PNG] * 6), _anh(PNG + b"x" * (5 * 1024 * 1024))],
    ids=["khong_anh", "sai_dinh_dang", "qua_5_anh", "qua_5mb"],
)
async def test_anh_khong_hop_le(client, kenh_tin_nhan, files):
    await _xin_otp(client)
    r = await client.post(
        "/api/v1/don-thuoc",
        data={"ho_ten": "A", "so_dien_thoai": SDT, "otp": kenh_tin_nhan.ma_otp_cuoi()},
        files=files or None,
    )
    # Thân request quá lớn bị chặn sớm ở middleware (413), còn lại do service kiểm (400).
    assert (r.status_code, r.json()["ma_loi"]) in {(400, "DU_LIEU_KHONG_HOP_LE"), (413, "THAN_QUA_LON")}


async def test_gioi_han_moi_sdt_moi_ngay(client, kenh_tin_nhan, dang_nhap_khach):
    sdt = dang_nhap_khach.tai_khoan.so_dien_thoai
    for _ in range(5):
        r = await dang_nhap_khach.post("/api/v1/don-thuoc", data={"ho_ten": "A"}, files=_anh(PNG))
        assert r.status_code == 201
    r = await _gui_vang_lai(client, kenh_tin_nhan, so_dien_thoai=sdt)
    assert r.status_code == 429 and r.json()["ma_loi"] == "QUA_GIOI_HAN"


async def test_thanh_vien_khong_gui_duoc_bang_sdt_tuy_y(dang_nhap_khach, db):
    """Thành viên luôn dùng SĐT của tài khoản: không né giới hạn theo SĐT, không gửi SMS tới số chưa xác thực."""
    r = await dang_nhap_khach.post(
        "/api/v1/don-thuoc", data={"ho_ten": "A", "so_dien_thoai": "0987654321"}, files=_anh(PNG)
    )
    assert r.status_code == 201
    yc = (await db.execute(select(YeuCauDonThuoc))).scalars().one()
    assert yc.so_dien_thoai == dang_nhap_khach.tai_khoan.so_dien_thoai != "0987654321"


async def test_thanh_vien_gui_khong_can_otp_va_xem_hai_anh(dang_nhap_khach, db):
    r = await dang_nhap_khach.post("/api/v1/don-thuoc", data={"ghi_chu": "x"}, files=_anh(PNG, JPG))
    assert r.status_code == 201, r.text
    ma = r.json()["ma_yeu_cau"]
    yc = (await db.execute(select(YeuCauDonThuoc))).scalars().one()
    assert yc.khach_hang_id == dang_nhap_khach.tai_khoan.id and len(yc.anh_don_thuoc) == 2
    ds = (await dang_nhap_khach.get("/api/v1/toi/don-thuoc")).json()
    assert [x["ma_yeu_cau"] for x in ds] == [ma] and ds[0]["so_anh"] == 2
    ct = (await dang_nhap_khach.get(f"/api/v1/toi/don-thuoc/{ma}")).json()
    assert len(ct["anh"]) == 2 and "anh_don_thuoc" not in ct
    # URL ký tải được ảnh gốc, không cần token.
    anh = await dang_nhap_khach.get(ct["anh"][0], headers={"Authorization": ""})
    assert anh.status_code == 200 and anh.content == PNG and anh.headers["cache-control"] == "private, no-store"


async def test_url_ky_sai_hoac_het_han(client, db, dang_nhap_khach):
    await dang_nhap_khach.post("/api/v1/don-thuoc", data={"ho_ten": "A"}, files=_anh(PNG))
    khoa = (await db.execute(select(YeuCauDonThuoc.anh_don_thuoc))).scalars().one()[0]
    url = luu_tru.url_ky(khoa)
    assert (await client.get(url)).status_code == 200
    ky = url.split("ky=")[1]
    assert (await client.get(f"/api/v1/tep-rieng/{khoa}?het_han={int(time.time()) + 1200}&ky={ky}")).status_code == 404
    assert (await client.get(f"/api/v1/tep-rieng/{khoa}?het_han=1&ky={ky}")).status_code == 404
    het = int(time.time()) - 5
    assert (
        await client.get(f"/api/v1/tep-rieng/{khoa}?het_han={het}&ky={luu_tru._chu_ky(khoa, het)}")
    ).status_code == 404
    # Khóa khác không dùng lại được chữ ký.
    khac = "don-thuoc/" + uuid.uuid4().hex + ".png"
    assert (await client.get(f"/api/v1/tep-rieng/{khac}?" + url.split("?")[1])).status_code == 404
    assert (await client.get(f"/api/v1/tep-rieng/{khoa}")).status_code == 400


async def test_khach_khac_khong_thay_va_khong_huy(dang_nhap_khach, app, db):
    from tests.conftest import _dang_nhap  # noqa: PLC0415

    r = await dang_nhap_khach.post("/api/v1/don-thuoc", data={"ho_ten": "A"}, files=_anh(PNG))
    ma = r.json()["ma_yeu_cau"]
    async for khac in _dang_nhap(app, await tao_khach(db), "khach"):
        assert (await khac.get("/api/v1/toi/don-thuoc")).json() == []
        assert (await khac.get(f"/api/v1/toi/don-thuoc/{ma}")).status_code == 404
        assert (await khac.post(f"/api/v1/toi/don-thuoc/{ma}/huy")).status_code == 404


async def test_huy_theo_trang_thai(dang_nhap_khach, db):
    ma = {}
    for tt in ("cho_duyet", "dang_tu_van", "da_tao_don", "tu_choi"):
        ma[tt] = (await dang_nhap_khach.post("/api/v1/don-thuoc", data={"ho_ten": "A"}, files=_anh(PNG))).json()[
            "ma_yeu_cau"
        ]
        yc = (await db.execute(select(YeuCauDonThuoc).where(YeuCauDonThuoc.ma_yeu_cau == ma[tt]))).scalars().one()
        yc.trang_thai = tt
        if tt == "dang_tu_van":
            yc.duoc_si_id = (await tao_nhan_vien(db)).id
        await db.flush()
    for tt in ("cho_duyet", "dang_tu_van"):
        r = await dang_nhap_khach.post(f"/api/v1/toi/don-thuoc/{ma[tt]}/huy")
        assert r.status_code == 200 and r.json()["trang_thai"] == "khach_huy"
    for tt in ("da_tao_don", "tu_choi"):
        r = await dang_nhap_khach.post(f"/api/v1/toi/don-thuoc/{ma[tt]}/huy")
        assert r.status_code == 409 and r.json()["ma_loi"] == "CHUYEN_TRANG_THAI_KHONG_HOP_LE"
    # Hủy lần hai cũng 409.
    assert (await dang_nhap_khach.post(f"/api/v1/toi/don-thuoc/{ma['cho_duyet']}/huy")).status_code == 409


async def test_hash_anh_giong_nhau_cho_cung_anh(dang_nhap_khach, db):
    for _ in range(2):
        await dang_nhap_khach.post("/api/v1/don-thuoc", data={"ho_ten": "A"}, files=_anh(PNG))
    await dang_nhap_khach.post("/api/v1/don-thuoc", data={"ho_ten": "A"}, files=_anh(JPG))
    h = (await db.execute(select(YeuCauDonThuoc.hash_anh).order_by(YeuCauDonThuoc.id))).scalars().all()
    assert h[0] == h[1] != h[2]


async def test_yeu_cau_cu_khong_tinh_vao_gioi_han(client, kenh_tin_nhan, db, dang_nhap_khach):
    for _ in range(5):
        assert (
            await dang_nhap_khach.post("/api/v1/don-thuoc", data={"so_dien_thoai": SDT}, files=_anh(PNG))
        ).status_code == 201
    for yc in (await db.execute(select(YeuCauDonThuoc))).scalars():
        yc.created_at = bay_gio_utc() - timedelta(days=2)
    await db.flush()
    assert (await _gui_vang_lai(client, kenh_tin_nhan)).status_code == 201


async def test_can_dang_nhap_khach_cho_api_toi(client, clients_theo_vai_tro):
    assert (await client.get("/api/v1/toi/don-thuoc")).status_code == 401
    for c in clients_theo_vai_tro.values():
        assert (await c.get("/api/v1/toi/don-thuoc")).status_code in (401, 403)

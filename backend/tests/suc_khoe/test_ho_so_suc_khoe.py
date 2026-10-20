"""KTV11: hồ sơ sức khỏe và dị ứng, hàm cổng của dược sĩ, mã hóa `benh_nen` (spec 03 mục 5.1)."""

import logging
import uuid

import pytest
from sqlalchemy import select, text

from app.core import ma_hoa
from app.core.config import settings
from app.core.thoi_gian import bay_gio_utc
from app.models.ai import HoiThoai
from app.models.ban_hang import YeuCauDonThuoc
from app.models.he_thong import NhatKyHeThong
from app.models.khach_hang import DiUng, HoSoSucKhoe
from app.models.san_pham import HoatChat
from app.modules.suc_khoe import dich_vu
from tests.factories import tao_khach, tao_nhan_vien

URL = "/api/v1/toi/ho-so-suc-khoe"
BENH = "tiểu đường típ 2 BENHNEN-BI-MAT"


async def _hoat_chat(db, ten):
    h = HoatChat(ten=f"{ten}-{uuid.uuid4().hex[:6]}")
    db.add(h)
    await db.flush()
    return h


def _vao(**kw):
    return {"dong_y_su_dung": True, "nam_sinh": 1990, "benh_nen": BENH, "di_ung": [], **kw}


async def _yeu_cau(db, khach, duoc_si, trang_thai="dang_tu_van"):
    n = uuid.uuid4().hex[:8]
    db.add(
        YeuCauDonThuoc(
            ma_yeu_cau=f"YC{n}", khach_hang_id=khach.id, ho_ten="A", so_dien_thoai="0900000000",
            anh_don_thuoc=[], trang_thai=trang_thai, duoc_si_id=duoc_si.id, khoa_luc=bay_gio_utc(),
        )
    )  # fmt: skip
    await db.flush()


async def test_chua_co_ho_so_tra_rong(dang_nhap_khach):
    r = await dang_nhap_khach.get(URL)
    assert r.status_code == 200
    assert r.json()["dong_y_su_dung"] is False and r.json()["di_ung"] == []


async def test_khong_dong_y_thi_khong_luu(dang_nhap_khach, db):
    r = await dang_nhap_khach.put(URL, json=_vao(dong_y_su_dung=False))
    assert r.status_code == 400 and r.json()["ma_loi"] == "DU_LIEU_KHONG_HOP_LE"
    assert await db.get(HoSoSucKhoe, dang_nhap_khach.tai_khoan.id) is None


async def test_luu_xem_sua_xoa(dang_nhap_khach, db):
    h1, h2 = await _hoat_chat(db, "Amoxicillin"), await _hoat_chat(db, "Aspirin")
    r = await dang_nhap_khach.put(URL, json=_vao(di_ung=[{"hoat_chat_id": h1.id, "ghi_chu": "phát ban"}]))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["dong_y_su_dung"] and d["dong_y_luc"] and d["benh_nen"] == BENH
    assert [x["hoat_chat_id"] for x in d["di_ung"]] == [h1.id]
    luc = d["dong_y_luc"]
    # Sửa: thay toàn bộ dị ứng; dong_y_luc giữ nguyên lần đồng ý đầu.
    r = await dang_nhap_khach.put(URL, json=_vao(benh_nen=None, di_ung=[{"hoat_chat_id": h2.id}]))
    d = r.json()
    assert d["benh_nen"] is None and d["dong_y_luc"] == luc
    assert [x["hoat_chat_id"] for x in d["di_ung"]] == [h2.id]
    assert (await dang_nhap_khach.get(URL)).json()["nam_sinh"] == 1990
    # Xóa cứng cả hai bảng; xóa lại vẫn 204.
    assert (await dang_nhap_khach.delete(URL)).status_code == 204
    assert (await dang_nhap_khach.delete(URL)).status_code == 204
    kid = dang_nhap_khach.tai_khoan.id
    assert await db.get(HoSoSucKhoe, kid) is None
    assert (await db.execute(select(DiUng).where(DiUng.khach_hang_id == kid))).first() is None
    assert (await dang_nhap_khach.get(URL)).json()["dong_y_su_dung"] is False


async def test_hoat_chat_khong_ton_tai_va_du_lieu_sai(dang_nhap_khach):
    r = await dang_nhap_khach.put(URL, json=_vao(di_ung=[{"hoat_chat_id": 2_000_000_000}]))
    assert r.status_code == 400
    assert (await dang_nhap_khach.put(URL, json=_vao(nam_sinh=1800))).status_code == 400
    assert (await dang_nhap_khach.put(URL, json={**_vao(), "khach_hang_id": 1})).status_code == 400


async def test_chi_doc_ho_so_cua_chinh_minh(dang_nhap_khach, db):
    khac = await tao_khach(db)
    db.add(HoSoSucKhoe(khach_hang_id=khac.id, dong_y_su_dung=True, nam_sinh=1970))
    await db.flush()
    assert (await dang_nhap_khach.get(URL)).json()["nam_sinh"] is None


async def test_benh_nen_ma_hoa_trong_db(dang_nhap_khach, db):
    await dang_nhap_khach.put(URL, json=_vao())
    goc = (
        await db.execute(
            text("select benh_nen from ho_so_suc_khoe where khach_hang_id = :k"),
            {"k": dang_nhap_khach.tai_khoan.id},
        )
    ).scalar_one()
    assert goc != BENH and "BENHNEN" not in goc
    assert ma_hoa.giai_ma(goc) == BENH


def test_khoa_thieu_hoac_sai(monkeypatch):
    from pydantic import SecretStr

    monkeypatch.setattr(settings, "KHOA_MA_HOA", SecretStr(""))
    with pytest.raises(RuntimeError):
        ma_hoa.ma_hoa("x")
    monkeypatch.setattr(settings, "KHOA_MA_HOA", SecretStr("khong-phai-khoa"))
    with pytest.raises(RuntimeError):
        ma_hoa.ma_hoa("x")
    monkeypatch.setattr(settings, "KHOA_MA_HOA", SecretStr("doi-gia-tri-nay"))
    with pytest.raises(RuntimeError):
        ma_hoa.ma_hoa("x")


def test_giai_ma_sai_khoa_khong_lo_gia_tri(monkeypatch):
    from cryptography.fernet import Fernet
    from pydantic import SecretStr

    ma = ma_hoa.ma_hoa("bí mật")
    monkeypatch.setattr(settings, "KHOA_MA_HOA", SecretStr(Fernet.generate_key().decode()))
    with pytest.raises(RuntimeError) as e:
        ma_hoa.giai_ma(ma)
    assert "bí mật" not in str(e.value) and ma not in str(e.value)


async def test_nhan_vien_khong_vao_api_khach(clients_theo_vai_tro):
    for c in clients_theo_vai_tro.values():
        for r in (await c.get(URL), await c.put(URL, json=_vao()), await c.delete(URL)):
            assert r.status_code in (401, 403)


async def test_khong_dang_nhap_401(client):
    assert (await client.get(URL)).status_code == 401


async def _khach_co_ho_so(db, dong_y=True):
    khach = await tao_khach(db)
    db.add(HoSoSucKhoe(khach_hang_id=khach.id, dong_y_su_dung=dong_y, benh_nen=ma_hoa.ma_hoa(BENH)))
    await db.flush()
    return khach


async def test_cong_dong_khi_khoa_yeu_cau_het_han_du_job_nha_khoa_chua_chay(db):
    """Khóa quá `thoi_gian_khoa_don_thuoc_phut` mất quyền đọc hồ sơ ngay, không chờ job HT08 nhả khóa."""
    from datetime import timedelta

    khach, ds = await _khach_co_ho_so(db), await tao_nhan_vien(db, "PHARMACIST")
    await _yeu_cau(db, khach, ds)
    assert await dich_vu.duoc_doc_ho_so_suc_khoe(db, ds, khach.id) is True
    yc = (await db.execute(select(YeuCauDonThuoc))).scalars().one()
    yc.khoa_luc = bay_gio_utc() - timedelta(minutes=31)  # mặc định khóa 30 phút
    await db.flush()
    assert await dich_vu.duoc_doc_ho_so_suc_khoe(db, ds, khach.id) is False


async def test_cong_duoc_si_duoc_gan_doc_duoc_va_ghi_nhat_ky(db):
    khach, ds = await _khach_co_ho_so(db), await tao_nhan_vien(db, "PHARMACIST")
    await _yeu_cau(db, khach, ds)
    assert await dich_vu.duoc_doc_ho_so_suc_khoe(db, ds, khach.id) is True
    ho_so = await dich_vu.doc_ho_so_cho_duoc_si(db, ds, khach.id)
    assert ho_so.benh_nen == BENH
    dong = (await db.execute(select(NhatKyHeThong).where(NhatKyHeThong.hanh_dong == "doc_suc_khoe"))).scalars().all()
    assert len(dong) == 2  # mỗi lần đọc một dòng
    assert all(d.nhan_vien_id == ds.id and d.bang == "ho_so_suc_khoe" and d.ban_ghi_id == str(khach.id) for d in dong)
    assert all(d.gia_tri_cu is None and d.gia_tri_moi is None for d in dong)
    assert "BENHNEN" not in str([(d.gia_tri_cu, d.gia_tri_moi, d.hanh_dong, d.bang) for d in dong])


async def test_cong_duoc_si_qua_hoi_thoai_chat(db):
    khach, ds = await _khach_co_ho_so(db), await tao_nhan_vien(db, "PHARMACIST")
    db.add(HoiThoai(ma_phien=uuid.uuid4(), khach_hang_id=khach.id, trang_thai="duoc_si_dang_xu_ly", duoc_si_id=ds.id))
    await db.flush()
    assert await dich_vu.duoc_doc_ho_so_suc_khoe(db, ds, khach.id) is True


async def test_cong_chan_cac_truong_hop_khong_hop_le(db):
    from app.core.loi import LoiNghiepVu

    khach, ds, ds_khac = await _khach_co_ho_so(db), await tao_nhan_vien(db), await tao_nhan_vien(db)
    await _yeu_cau(db, khach, ds)
    # Dược sĩ không được gán.
    assert await dich_vu.duoc_doc_ho_so_suc_khoe(db, ds_khac, khach.id) is False
    with pytest.raises(LoiNghiepVu) as e:
        await dich_vu.doc_ho_so_cho_duoc_si(db, ds_khac, khach.id)
    assert e.value.ma_loi == "KHONG_CO_QUYEN"
    # Admin và kho không đọc được, kể cả khi trùng khóa gán.
    for ma in ("ADMIN", "WAREHOUSE"):
        nv = await tao_nhan_vien(db, ma)
        await _yeu_cau(db, khach, nv)
        assert await dich_vu.duoc_doc_ho_so_suc_khoe(db, nv, khach.id) is False
    # Yêu cầu không còn đang tư vấn.
    khach2, ds2 = await _khach_co_ho_so(db), await tao_nhan_vien(db)
    await _yeu_cau(db, khach2, ds2, "da_tao_don")
    assert await dich_vu.duoc_doc_ho_so_suc_khoe(db, ds2, khach2.id) is False
    # Chưa đồng ý hoặc chưa có hồ sơ.
    khach3, ds3 = await _khach_co_ho_so(db, dong_y=False), await tao_nhan_vien(db)
    await _yeu_cau(db, khach3, ds3)
    assert await dich_vu.duoc_doc_ho_so_suc_khoe(db, ds3, khach3.id) is False
    khach4 = await tao_khach(db)
    await _yeu_cau(db, khach4, ds3)
    assert await dich_vu.duoc_doc_ho_so_suc_khoe(db, ds3, khach4.id) is False
    # Từ chối thì không ghi nhật ký đọc.
    assert (await db.execute(select(NhatKyHeThong).where(NhatKyHeThong.hanh_dong == "doc_suc_khoe"))).first() is None


async def test_log_khong_chua_gia_tri_ro(dang_nhap_khach, db, caplog):
    h = await _hoat_chat(db, "Penicillin")
    with caplog.at_level(logging.DEBUG):
        await dang_nhap_khach.put(URL, json=_vao(di_ung=[{"hoat_chat_id": h.id, "ghi_chu": "GHICHU-BI-MAT"}]))
        await dang_nhap_khach.get(URL)
        await dang_nhap_khach.delete(URL)
    toan_bo = caplog.text
    assert "BENHNEN" not in toan_bo and "GHICHU-BI-MAT" not in toan_bo
    assert (await db.execute(select(NhatKyHeThong).where(NhatKyHeThong.bang == "ho_so_suc_khoe"))).first() is None


async def test_tim_hoat_chat(dang_nhap_khach, db, client):
    h = await _hoat_chat(db, "Amoxicillin")
    r = await dang_nhap_khach.get(URL + "/hoat-chat", params={"q": "amoxicilin"[:6]})
    assert r.status_code == 200 and h.id in [x["id"] for x in r.json()]
    assert set(r.json()[0]) == {"id", "ten"}
    assert (await dang_nhap_khach.get(URL + "/hoat-chat", params={"q": "100%_"})).json() == []
    assert len((await dang_nhap_khach.get(URL + "/hoat-chat")).json()) <= 20
    assert (await client.get(URL + "/hoat-chat")).status_code == 401

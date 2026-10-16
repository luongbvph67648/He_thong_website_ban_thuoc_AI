"""KTV07: khách xác nhận/từ chối đơn từ đơn thuốc (tài khoản hoặc link mã truy cập); vòng đời yêu cầu (T5.3)."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.thoi_gian import bay_gio_utc
from app.jobs.cong_viec import ht03_huy_qua_han
from app.models.ban_hang import DonHang, YeuCauDonThuoc
from app.models.enums import TrangThaiDon
from app.models.kho import LoThuoc
from app.modules.ban_hang.trang_thai import NGUON_NGUOI_DUNG, TacNhan, chuyen_trang_thai
from tests.conftest import _dang_nhap
from tests.don_thuoc.test_duyet_don_thuoc import BASE, _dong, _tao, _thuoc, _yc
from tests.factories import tao_khach, tao_nhan_vien

DIA_CHI = {"dia_chi_chi_tiet": "12 Phố Huế", "ma_tinh": "201", "ma_phuong_xa": "2010101"}


async def _don_vang_lai(duoc_si_client, db, ton=50):
    yc = await _yc(db, None, "dang_tu_van", duoc_si_client.tai_khoan)
    sp = await _thuoc(db, ton=ton)
    r = await duoc_si_client.post(f"{BASE}/{yc.id}/tao-don", json=_tao([_dong(sp, 2)]))
    assert r.status_code == 201, r.text
    return yc, sp, r.json()["don"]["ma_don"], r.json()["lien_ket_xac_nhan"].rsplit("/", 1)[1]


async def _don_thanh_vien(duoc_si_client, db, khach, ton=50):
    yc = await _yc(db, khach, "dang_tu_van", duoc_si_client.tai_khoan)
    sp = await _thuoc(db, ton=ton)
    r = await duoc_si_client.post(f"{BASE}/{yc.id}/tao-don", json=_tao([_dong(sp, 2)]))
    assert r.status_code == 201, r.text
    return yc, sp, r.json()["don"]["ma_don"]


async def _don(db, ma):
    return (await db.execute(select(DonHang).where(DonHang.ma_don == ma))).scalars().one()


async def test_vang_lai_xem_don_qua_link(dang_nhap_duoc_si, client, db):
    _, _, ma, token = await _don_vang_lai(dang_nhap_duoc_si, db)
    r = await client.get(f"/api/v1/xac-nhan-don/{token}")
    assert r.status_code == 200
    d = r.json()
    assert d["co_the_xac_nhan"] is True and d["co_the_thanh_toan"] is False and d["don"]["ma_don"] == ma
    assert d["don"]["trang_thai"] == "cho_khach_xac_nhan" and len(d["don"]["dong"]) == 1


@pytest.mark.parametrize("token", ["", "x" * 10, "sai-token-" + "a" * 40, "a" * 200])
async def test_token_sai_la_404(client, token):
    assert (await client.get(f"/api/v1/xac-nhan-don/{token or 'x'}")).status_code == 404


async def test_vang_lai_xac_nhan_cod_giao_tan_noi(dang_nhap_duoc_si, client, db):
    yc, _, ma, token = await _don_vang_lai(dang_nhap_duoc_si, db)
    r = await client.post(
        f"/api/v1/xac-nhan-don/{token}/xac-nhan",
        json={
            "hinh_thuc_nhan": "giao_tan_noi", "phuong_thuc_tt": "cod", "dia_chi": DIA_CHI,
            "ten_nguoi_nhan": "Trần B", "sdt_nguoi_nhan": "0987654321",
        },
    )  # fmt: skip
    assert r.status_code == 200, r.text
    d = r.json()["don"]
    assert d["trang_thai"] == "da_xac_nhan" and d["phuong_thuc_tt"] == "cod"
    assert d["ten_nguoi_nhan"] == "Trần B" and "12 Phố Huế" in d["dia_chi_giao"]
    don = await _don(db, ma)
    assert don.tong_tien == don.tam_tinh - don.giam_gia + don.phi_van_chuyen
    # Sau khi xác nhận, link chỉ còn xem được; không xác nhận, từ chối hay thanh toán lại được.
    xem = (await client.get(f"/api/v1/xac-nhan-don/{token}")).json()
    assert xem["co_the_xac_nhan"] is False and xem["don"]["trang_thai"] == "da_xac_nhan"
    assert (await client.post(f"/api/v1/xac-nhan-don/{token}/tu-choi")).status_code == 409
    assert (await client.post(f"/api/v1/xac-nhan-don/{token}/thanh-toan")).status_code in (400, 409)
    await db.refresh(yc)
    assert yc.trang_thai == "da_tao_don" and yc.da_su_dung is False


async def test_nhan_tai_nha_thuoc_khong_co_phi_ship(dang_nhap_duoc_si, client, db):
    _, _, ma, token = await _don_vang_lai(dang_nhap_duoc_si, db)
    r = await client.post(
        f"/api/v1/xac-nhan-don/{token}/xac-nhan", json={"hinh_thuc_nhan": "nhan_tai_nha_thuoc", "phuong_thuc_tt": "cod"}
    )
    assert r.status_code == 200
    don = await _don(db, ma)
    assert don.phi_van_chuyen == 0 and don.hinh_thuc_nhan == "nhan_tai_nha_thuoc"


async def test_giao_tan_noi_thieu_dia_chi_bi_chan(dang_nhap_duoc_si, client, db):
    _, _, ma, token = await _don_vang_lai(dang_nhap_duoc_si, db)
    r = await client.post(
        f"/api/v1/xac-nhan-don/{token}/xac-nhan", json={"hinh_thuc_nhan": "giao_tan_noi", "phuong_thuc_tt": "cod"}
    )
    assert r.status_code == 400
    assert (await _don(db, ma)).trang_thai == "cho_khach_xac_nhan"


async def test_vang_lai_chon_online_roi_tao_thanh_toan(dang_nhap_duoc_si, client, db):
    _, _, ma, token = await _don_vang_lai(dang_nhap_duoc_si, db)
    r = await client.post(
        f"/api/v1/xac-nhan-don/{token}/xac-nhan",
        json={"hinh_thuc_nhan": "nhan_tai_nha_thuoc", "phuong_thuc_tt": "vnpay"},
    )
    d = r.json()
    assert d["don"]["trang_thai"] == "cho_thanh_toan" and d["co_the_thanh_toan"] is True and d["don"]["han_thanh_toan"]
    khoa = {"Idempotency-Key": str(uuid.uuid4())}
    tt = await client.post(f"/api/v1/xac-nhan-don/{token}/thanh-toan", headers=khoa)
    assert tt.status_code == 200 and tt.json()["url_thanh_toan"]
    lai = await client.post(f"/api/v1/xac-nhan-don/{token}/thanh-toan", headers=khoa)
    assert lai.json()["url_thanh_toan"] == tt.json()["url_thanh_toan"]
    assert (await client.get(f"/api/v1/xac-nhan-don/{token}")).status_code == 200  # còn xem được khi chờ thanh toán


async def test_vang_lai_tu_choi_tra_hang_va_cho_tao_lai_don(dang_nhap_duoc_si, client, db):
    yc, sp, ma, token = await _don_vang_lai(dang_nhap_duoc_si, db)
    r = await client.post(f"/api/v1/xac-nhan-don/{token}/tu-choi")
    assert r.status_code == 200 and r.json()["trang_thai"] == "da_huy"
    lo = (await db.execute(select(LoThuoc).where(LoThuoc.san_pham_id == sp.id))).scalars().one()
    assert lo.so_luong_giu == 0
    await db.refresh(yc)
    assert yc.trang_thai == "dang_tu_van" and yc.da_su_dung is False and yc.duoc_si_id is not None
    r = await dang_nhap_duoc_si.post(f"{BASE}/{yc.id}/tao-don", json=_tao([_dong(sp, 1)]))
    assert r.status_code == 201  # tạo lại từ cùng yêu cầu


async def test_thanh_vien_xac_nhan_va_nguoi_khac_bi_404(dang_nhap_duoc_si, dang_nhap_khach, app, db):
    yc, _, ma = await _don_thanh_vien(dang_nhap_duoc_si, db, dang_nhap_khach.tai_khoan)
    async for khac in _dang_nhap(app, await tao_khach(db), "khach"):
        assert (await khac.get(f"/api/v1/toi/don-hang/{ma}/xac-nhan")).status_code == 404
        r = await khac.post(
            f"/api/v1/toi/don-hang/{ma}/xac-nhan",
            json={"hinh_thuc_nhan": "nhan_tai_nha_thuoc", "phuong_thuc_tt": "cod"},
        )
        assert r.status_code == 404
        assert (await khac.post(f"/api/v1/toi/don-hang/{ma}/tu-choi")).status_code == 404
    xem = (await dang_nhap_khach.get(f"/api/v1/toi/don-hang/{ma}/xac-nhan")).json()
    assert xem["co_the_xac_nhan"] is True
    r = await dang_nhap_khach.post(
        f"/api/v1/toi/don-hang/{ma}/xac-nhan", json={"hinh_thuc_nhan": "nhan_tai_nha_thuoc", "phuong_thuc_tt": "momo"}
    )
    assert r.json()["don"]["trang_thai"] == "cho_thanh_toan"
    tt = await dang_nhap_khach.post(
        f"/api/v1/toi/don-hang/{ma}/thanh-toan", headers={"Idempotency-Key": str(uuid.uuid4())}
    )
    assert tt.status_code == 200


async def test_thanh_vien_dung_so_dia_chi_cua_minh(dang_nhap_duoc_si, dang_nhap_khach, app, db):
    from app.models.khach_hang import DiaChi

    khach = dang_nhap_khach.tai_khoan
    _, _, ma = await _don_thanh_vien(dang_nhap_duoc_si, db, khach)
    cua_minh = DiaChi(khach_hang_id=khach.id, ten_nguoi_nhan="A", so_dien_thoai="0912345678", dia_chi_chi_tiet="1 Phố A",
                      ma_tinh="201", ten_tinh="Hà Nội", ma_phuong_xa="2010101", ten_phuong_xa="Hoàn Kiếm")  # fmt: skip
    nguoi_khac = await tao_khach(db)
    cua_ho = DiaChi(khach_hang_id=nguoi_khac.id, ten_nguoi_nhan="B", so_dien_thoai="0912345679", dia_chi_chi_tiet="2 Phố B",
                    ma_tinh="201", ten_tinh="Hà Nội", ma_phuong_xa="2010101", ten_phuong_xa="Hoàn Kiếm")  # fmt: skip
    db.add_all([cua_minh, cua_ho])
    await db.flush()
    vao = {"hinh_thuc_nhan": "giao_tan_noi", "phuong_thuc_tt": "cod"}
    assert (
        await dang_nhap_khach.post(f"/api/v1/toi/don-hang/{ma}/xac-nhan", json={**vao, "dia_chi_id": cua_ho.id})
    ).status_code == 404
    r = await dang_nhap_khach.post(f"/api/v1/toi/don-hang/{ma}/xac-nhan", json={**vao, "dia_chi_id": cua_minh.id})
    assert r.status_code == 200 and "1 Phố A" in r.json()["don"]["dia_chi_giao"]


async def test_qua_han_xac_nhan_ht03_huy_va_tra_yeu_cau(dang_nhap_duoc_si, client, db):
    yc, _, ma, token = await _don_vang_lai(dang_nhap_duoc_si, db)
    don = await _don(db, ma)
    don.han_xac_nhan = bay_gio_utc() - timedelta(minutes=1)
    await db.flush()
    xem = (await client.get(f"/api/v1/xac-nhan-don/{token}")).json()
    assert xem["co_the_xac_nhan"] is False
    r = await client.post(
        f"/api/v1/xac-nhan-don/{token}/xac-nhan", json={"hinh_thuc_nhan": "nhan_tai_nha_thuoc", "phuong_thuc_tt": "cod"}
    )
    assert r.status_code == 409
    await ht03_huy_qua_han(db)
    await db.refresh(don)
    await db.refresh(yc)
    assert don.trang_thai == "da_huy" and yc.trang_thai == "dang_tu_van"


async def test_da_su_dung_chi_bat_khi_sang_dang_soan_hang(dang_nhap_duoc_si, client, db):
    yc, _, ma, token = await _don_vang_lai(dang_nhap_duoc_si, db)
    await client.post(
        f"/api/v1/xac-nhan-don/{token}/xac-nhan", json={"hinh_thuc_nhan": "nhan_tai_nha_thuoc", "phuong_thuc_tt": "cod"}
    )
    don = await _don(db, ma)
    await db.refresh(yc)
    assert yc.da_su_dung is False
    kho = await tao_nhan_vien(db, "WAREHOUSE")
    await chuyen_trang_thai(db, don, TrangThaiDon.dang_soan_hang, TacNhan.kho(kho.id), NGUON_NGUOI_DUNG)
    await db.refresh(yc)
    assert yc.da_su_dung is True and yc.trang_thai == "da_tao_don"
    # Hủy sau khi đã xuất kho: yêu cầu giữ nguyên "đã dùng", không quay lại tư vấn.
    ds = dang_nhap_duoc_si.tai_khoan
    await chuyen_trang_thai(db, don, TrangThaiDon.da_huy, TacNhan.duoc_si(ds.id), NGUON_NGUOI_DUNG, "Khách đổi ý")
    await db.refresh(yc)
    assert yc.da_su_dung is True and yc.trang_thai == "da_tao_don"


async def test_duoc_si_huy_don_truoc_xuat_kho_tra_yeu_cau_dang_tu_van(dang_nhap_duoc_si, dang_nhap_khach, db):
    yc, sp, ma = await _don_thanh_vien(dang_nhap_duoc_si, db, dang_nhap_khach.tai_khoan)
    await dang_nhap_khach.post(
        f"/api/v1/toi/don-hang/{ma}/xac-nhan", json={"hinh_thuc_nhan": "nhan_tai_nha_thuoc", "phuong_thuc_tt": "cod"}
    )
    r = await dang_nhap_duoc_si.post(
        f"/api/v1/noi-bo/don-hang/{(await _don(db, ma)).id}/huy", json={"ly_do": "Hết thuốc"}
    )
    assert r.status_code == 200
    await db.refresh(yc)
    assert yc.trang_thai == "dang_tu_van" and yc.da_su_dung is False
    assert (await db.execute(select(YeuCauDonThuoc).where(YeuCauDonThuoc.id == yc.id))).scalars().one().duoc_si_id

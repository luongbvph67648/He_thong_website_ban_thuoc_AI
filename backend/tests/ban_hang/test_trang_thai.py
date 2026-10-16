"""HT06: máy trạng thái đơn hàng. Bảng chuyển là dữ liệu: mọi dòng chạy được, mọi cặp ngoài bảng bị từ chối."""

import ast
import itertools
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc
from app.models.ban_hang import CtDonHang, DonHang, LichSuTrangThai, PhanBoLo
from app.models.enums import TrangThaiDon as TT
from app.modules.ban_hang import trang_thai as mt
from app.modules.ban_hang.trang_thai import BANG_CHUYEN, LoaiTacNhan, TacNhan
from app.modules.kho import ton_kho
from tests.factories import tao_don, tao_khach, tao_lo, tao_nhan_vien, tao_san_pham

_dem = itertools.count(1)
NGUON_MAC_DINH = {
    LoaiTacNhan.khach: "nguoi_dung",
    LoaiTacNhan.duoc_si: "nguoi_dung",
    LoaiTacNhan.kho: "nguoi_dung",
    LoaiTacNhan.he_thong: "he_thong",
}


async def tac_nhan_loai(db, loai, khach=None):
    if loai == LoaiTacNhan.khach:
        return TacNhan.khach(khach.id)
    if loai == LoaiTacNhan.he_thong:
        return TacNhan.he_thong()
    nv = await tao_nhan_vien(db, "PHARMACIST" if loai == LoaiTacNhan.duoc_si else "WAREHOUSE")
    return TacNhan(loai, nhan_vien_id=nv.id)


def thuoc_tinh_cho(chuyen, loai, nv_tao_id):
    """Thuộc tính đơn thỏa mọi điều kiện của dòng `chuyen` khi `loai` thực hiện."""
    t: dict = {}
    bay_gio = bay_gio_utc()
    for dk in chuyen.dieu_kien:
        if dk == "online":
            t["kenh_ban"] = "online"
        elif dk == "dien_thoai":
            t["kenh_ban"] = "dien_thoai"
        elif dk == "tai_quay":
            t["kenh_ban"] = "tai_quay"
        elif dk == "cod":
            t["phuong_thuc_tt"] = "cod"
        elif dk == "tt_online":
            t["phuong_thuc_tt"] = "vnpay"
        elif dk == "da_thanh_toan":
            t["trang_thai_tt"] = "da_thanh_toan"
        elif dk == "truoc_han_xac_nhan":
            t["han_xac_nhan"] = bay_gio + timedelta(hours=1)
        elif dk == "he_thong_qua_han_xac_nhan" and loai == LoaiTacNhan.he_thong:
            t["han_xac_nhan"] = bay_gio - timedelta(minutes=1)
        elif dk == "he_thong_qua_han_thanh_toan" and loai == LoaiTacNhan.he_thong:
            t["han_thanh_toan"] = bay_gio - timedelta(minutes=1)
        elif dk == "duoc_si_tao":
            t["nhan_vien_tao_id"] = nv_tao_id
        elif dk == "nhan_tai_nha_thuoc":
            t["hinh_thuc_nhan"] = "nhan_tai_nha_thuoc"
    return t


def dong_khong_ke_don(db):
    return tao_san_pham(db)


async def don_chua_luu(db, khach, **truong):
    """DonHang chưa có trạng thái và chưa add vào phiên, kèm một dòng hàng thường (cách các task đặt hàng dùng)."""
    sp = await tao_san_pham(db, loai=truong.pop("loai", "thuoc_khong_ke_don"))
    don = DonHang(
        ma_don=f"MT{next(_dem):08d}",
        khach_hang_id=khach.id if khach else None,
        phuong_thuc_tt=truong.pop("phuong_thuc_tt", "cod"),
        tam_tinh=Decimal(1000),
        giam_gia=Decimal(0),
        phi_van_chuyen=Decimal(0),
        tong_tien=Decimal(1000),
        **truong,
    )
    don.chi_tiet = [
        CtDonHang(
            san_pham_id=sp.id,
            don_vi_id=sp.don_vi_theo_ten["viên"].id,
            ten_san_pham=sp.ten,
            ten_don_vi="viên",
            he_so=1,
            so_luong=1,
            don_gia=Decimal(1000),
            thanh_tien=Decimal(1000),
        )
    ]
    return don


CAC_DONG = [(c, tu) for c in BANG_CHUYEN if c.tu for tu in sorted(c.tu)]
CAC_DONG_TAO = [c for c in BANG_CHUYEN if c.tu is None]


@pytest.mark.parametrize(("chuyen", "tu"), CAC_DONG, ids=lambda x: getattr(x, "so", x))
async def test_moi_dong_trong_bang_chay_duoc_voi_tac_nhan_hop_le(db, chuyen, tu):
    khach = await tao_khach(db)
    nv_tao = await tao_nhan_vien(db, "PHARMACIST")
    for loai in sorted(chuyen.tac_nhan):
        don = await tao_don(db, khach, trang_thai=tu.value, **thuoc_tinh_cho(chuyen, loai, nv_tao.id))
        tn = await tac_nhan_loai(db, loai, khach)
        nguon = next(iter(chuyen.nguon_he_thong)) if loai == LoaiTacNhan.he_thong else "nguoi_dung"
        ls = await mt.chuyen_trang_thai(db, don, chuyen.den, tn, nguon, "Lý do thử")
        assert don.trang_thai == chuyen.den
        assert (ls.tu_trang_thai, ls.den_trang_thai, ls.nguon) == (tu, chuyen.den, nguon)
        assert ls.nhan_vien_id == tn.nhan_vien_id and ls.khach_hang_id == tn.khach_hang_id


@pytest.mark.parametrize("chuyen", CAC_DONG_TAO, ids=lambda c: c.so)
async def test_moi_dong_tao_moi_chay_duoc(db, chuyen):
    khach = await tao_khach(db)
    nv = await tao_nhan_vien(db, "PHARMACIST")
    loai = sorted(chuyen.tac_nhan)[0]
    tn = TacNhan.khach(khach.id) if loai == LoaiTacNhan.khach else TacNhan.duoc_si(nv.id)
    thuoc_tinh = thuoc_tinh_cho(chuyen, loai, nv.id)
    thuoc_tinh.pop("nhan_vien_tao_id", None)
    don = await don_chua_luu(db, khach if loai == LoaiTacNhan.khach else None, **thuoc_tinh)
    if "don_thay_the" in chuyen.dieu_kien:
        goc = await tao_don(db, khach, "da_giao")
        don.don_hang_goc_id = goc.id
        don.tam_tinh = don.tong_tien = Decimal(0)
        for c in don.chi_tiet:
            c.don_gia = c.thanh_tien = Decimal(0)
    ls = await mt.khoi_tao_trang_thai(db, don, chuyen.den, tn, "nguoi_dung", so_dong=chuyen.so[0])
    assert don.id and don.trang_thai == chuyen.den and ls.tu_trang_thai is None
    assert (
        await db.scalar(select(func.count()).select_from(LichSuTrangThai).where(LichSuTrangThai.don_hang_id == don.id))
    ) == 1
    assert (don.nhan_vien_tao_id == nv.id) == (loai == LoaiTacNhan.duoc_si)


def test_moi_cap_ngoai_bang_bi_tu_choi():
    hop_le = mt.cac_cap_hop_le()
    tat_ca = [None, *TT]
    ngoai_bang = [(tu, den) for tu in tat_ca for den in TT if (tu, den) not in hop_le]
    assert len(ngoai_bang) + len(hop_le) == 13 * 12
    ket = []
    for tu, den in ngoai_bang:
        with pytest.raises(LoiNghiepVu) as e:
            mt._tim_dong(tu, den, TacNhan.he_thong(), "he_thong")
        ket.append(e.value.ma_loi)
    assert set(ket) == {"CHUYEN_TRANG_THAI_KHONG_HOP_LE"}


def test_cap_chuyen_chi_duoc_tac_nhan_khai_bao():
    """Với mỗi cặp (từ, đến), chỉ hợp các tác nhân của các dòng trùng cặp đó mới qua được; còn lại là KHONG_CO_QUYEN."""
    theo_cap: dict = {}
    for c in BANG_CHUYEN:
        for tu in c.tu or {None}:
            theo_cap.setdefault((tu, c.den), set()).update(c.tac_nhan)
    for (tu, den), duoc in theo_cap.items():
        for loai in LoaiTacNhan:
            tn = TacNhan(loai, khach_hang_id=1, nhan_vien_id=1)
            if loai in duoc:
                nguon = (
                    "webhook_van_chuyen"
                    if loai == LoaiTacNhan.he_thong
                    and any("webhook_van_chuyen" in c.nguon_he_thong for c in BANG_CHUYEN if c.den == den)
                    else NGUON_MAC_DINH[loai]
                )
                if (
                    loai == LoaiTacNhan.he_thong
                    and den in (TT.cho_xac_nhan, TT.da_xac_nhan)
                    and tu == TT.cho_thanh_toan
                ):
                    nguon = "ipn_thanh_toan"
                mt._tim_dong(tu, den, tn, nguon)
                continue
            with pytest.raises(LoiNghiepVu) as e:
                mt._tim_dong(tu, den, tn, NGUON_MAC_DINH[loai])
            assert e.value.ma_loi == "KHONG_CO_QUYEN", (tu, den, loai)


def test_nguon_phai_khop_tac_nhan():
    with pytest.raises(LoiNghiepVu) as e:
        mt._tim_dong(TT.cho_xac_nhan, TT.da_xac_nhan, TacNhan.duoc_si(1), "he_thong")
    assert e.value.ma_loi == "CHUYEN_TRANG_THAI_KHONG_HOP_LE"
    with pytest.raises(LoiNghiepVu):
        mt._tim_dong(TT.cho_lay_hang, TT.dang_giao, TacNhan.he_thong(), "he_thong")  # phải là webhook_van_chuyen
    with pytest.raises(LoiNghiepVu):
        mt._tim_dong(TT.cho_thanh_toan, TT.da_xac_nhan, TacNhan.he_thong(), "webhook_van_chuyen")  # phải là IPN
    mt._tim_dong(TT.cho_lay_hang, TT.dang_giao, TacNhan.he_thong(), "webhook_van_chuyen")


async def test_admin_va_vai_tro_khac_khong_co_dong_nao(db):
    admin = await tao_nhan_vien(db, "ADMIN")
    with pytest.raises(LoiNghiepVu) as e:
        await mt.tac_nhan_tu_nhan_vien(db, admin)
    assert e.value.ma_loi == "KHONG_CO_QUYEN"
    ds = await tao_nhan_vien(db, "PHARMACIST")
    assert (await mt.tac_nhan_tu_nhan_vien(db, ds)).loai == LoaiTacNhan.duoc_si
    kho = await tao_nhan_vien(db, "WAREHOUSE")
    assert (await mt.tac_nhan_tu_nhan_vien(db, kho)).loai == LoaiTacNhan.kho


async def test_khach_chi_dung_don_cua_minh_va_link_chi_cho_xac_nhan_tu_choi(db):
    chu, khac = await tao_khach(db), await tao_khach(db)
    don = await tao_don(db, chu, trang_thai="cho_xac_nhan")
    with pytest.raises(LoiNghiepVu) as e:
        await mt.chuyen_trang_thai(db, don, TT.da_huy, TacNhan.khach(khac.id), "nguoi_dung")
    assert e.value.ma_loi == "KHONG_TIM_THAY" and don.trang_thai == TT.cho_xac_nhan
    with pytest.raises(LoiNghiepVu) as e:
        await mt.chuyen_trang_thai(
            db, don, TT.da_huy, TacNhan.khach_qua_link(), "nguoi_dung"
        )  # link không hủy đơn thường
    assert e.value.ma_loi == "KHONG_CO_QUYEN"
    cho = await tao_don(db, None, trang_thai="cho_khach_xac_nhan", han_xac_nhan=bay_gio_utc() + timedelta(hours=1))
    await mt.chuyen_trang_thai(db, cho, TT.da_xac_nhan, TacNhan.khach_qua_link(), "nguoi_dung")
    assert cho.trang_thai == TT.da_xac_nhan


async def test_ly_do_bat_buoc_khi_duoc_si_huy_va_duoc_luu(db):
    don = await tao_don(db, await tao_khach(db), trang_thai="cho_xac_nhan")
    ds = TacNhan.duoc_si((await tao_nhan_vien(db, "PHARMACIST")).id)
    for ly_do in (None, "", "   "):
        with pytest.raises(LoiNghiepVu) as e:
            await mt.chuyen_trang_thai(db, don, TT.da_huy, ds, "nguoi_dung", ly_do)
        assert e.value.ma_loi == "DU_LIEU_KHONG_HOP_LE"
    assert don.trang_thai == TT.cho_xac_nhan
    await mt.chuyen_trang_thai(db, don, TT.da_huy, ds, "nguoi_dung", "  Khách đổi ý ")
    assert don.ly_do_huy == "Khách đổi ý"


async def test_thuoc_ke_don_khong_di_kenh_online_hay_dien_thoai_nhung_tai_quay_duoc(db):
    khach = await tao_khach(db)
    nv = await tao_nhan_vien(db, "PHARMACIST")
    don = await don_chua_luu(db, khach, loai="thuoc_ke_don", kenh_ban="online")
    with pytest.raises(LoiNghiepVu) as e:
        await mt.khoi_tao_trang_thai(db, don, TT.cho_xac_nhan, TacNhan.khach(khach.id), "nguoi_dung")
    assert e.value.ma_loi == "CHUYEN_TRANG_THAI_KHONG_HOP_LE" and "kê đơn" in e.value.thong_diep
    don = await don_chua_luu(db, None, loai="thuoc_ke_don", kenh_ban="dien_thoai")
    with pytest.raises(LoiNghiepVu):
        await mt.khoi_tao_trang_thai(db, don, TT.da_xac_nhan, TacNhan.duoc_si(nv.id), "nguoi_dung")
    don = await don_chua_luu(db, None, loai="thuoc_ke_don", kenh_ban="tai_quay", trang_thai_tt="da_thanh_toan")
    await mt.khoi_tao_trang_thai(db, don, TT.hoan_tat, TacNhan.duoc_si(nv.id), "nguoi_dung")


async def test_dieu_kien_han_xac_nhan_va_han_thanh_toan(db):
    khach = await tao_khach(db)
    het = bay_gio_utc() - timedelta(minutes=5)
    con = bay_gio_utc() + timedelta(minutes=5)
    qua_han = await tao_don(db, khach, trang_thai="cho_khach_xac_nhan", han_xac_nhan=het)
    with pytest.raises(LoiNghiepVu):  # khách xác nhận sau hạn
        await mt.chuyen_trang_thai(db, qua_han, TT.da_xac_nhan, TacNhan.khach(khach.id), "nguoi_dung")
    await mt.chuyen_trang_thai(db, qua_han, TT.da_huy, TacNhan.he_thong(), "he_thong")  # hệ thống hủy quá hạn
    chua_han = await tao_don(db, khach, trang_thai="cho_khach_xac_nhan", han_xac_nhan=con)
    with pytest.raises(LoiNghiepVu):  # hệ thống không hủy khi chưa quá hạn
        await mt.chuyen_trang_thai(db, chua_han, TT.da_huy, TacNhan.he_thong(), "he_thong")
    await mt.chuyen_trang_thai(db, chua_han, TT.da_huy, TacNhan.khach(khach.id), "nguoi_dung")  # khách từ chối thì được
    tt_chua_han = await tao_don(db, khach, trang_thai="cho_thanh_toan", phuong_thuc_tt="vnpay", han_thanh_toan=con)
    with pytest.raises(LoiNghiepVu):
        await mt.chuyen_trang_thai(db, tt_chua_han, TT.da_huy, TacNhan.he_thong(), "he_thong")
    da_tra = await tao_don(
        db, khach, trang_thai="cho_thanh_toan", phuong_thuc_tt="vnpay", trang_thai_tt="da_thanh_toan"
    )
    with pytest.raises(LoiNghiepVu):  # đã có thanh toán thành công: không hủy kiểu "chưa thanh toán"
        await mt.chuyen_trang_thai(db, da_tra, TT.da_huy, TacNhan.khach(khach.id), "nguoi_dung")


async def test_ipn_phan_biet_don_khach_tu_dat_va_don_duoc_si_tao(db):
    khach = await tao_khach(db)
    nv = await tao_nhan_vien(db, "PHARMACIST")
    tu_dat = await tao_don(db, khach, trang_thai="cho_thanh_toan", phuong_thuc_tt="vnpay")
    with pytest.raises(LoiNghiepVu):
        await mt.chuyen_trang_thai(db, tu_dat, TT.da_xac_nhan, TacNhan.he_thong(), "ipn_thanh_toan")
    await mt.chuyen_trang_thai(db, tu_dat, TT.cho_xac_nhan, TacNhan.he_thong(), "ipn_thanh_toan")
    do_ds = await tao_don(db, khach, trang_thai="cho_thanh_toan", phuong_thuc_tt="vnpay", nhan_vien_tao_id=nv.id)
    with pytest.raises(LoiNghiepVu):
        await mt.chuyen_trang_thai(db, do_ds, TT.cho_xac_nhan, TacNhan.he_thong(), "ipn_thanh_toan")
    await mt.chuyen_trang_thai(db, do_ds, TT.da_xac_nhan, TacNhan.he_thong(), "ipn_thanh_toan")


# --- Tác động kho trong cùng transaction ---


async def don_co_hang_giu(db, so_luong=4, trang_thai="cho_xac_nhan"):
    sp = await tao_san_pham(db)
    lo = await tao_lo(db, sp, so_luong=20)
    don = await tao_don(db, await tao_khach(db), trang_thai=trang_thai, dong=[{"san_pham": sp, "so_luong": so_luong}])
    ct = (await db.execute(select(CtDonHang).where(CtDonHang.don_hang_id == don.id))).scalar_one()
    await ton_kho.giu_hang(db, ct, so_luong)
    return don, lo


async def trang_thai_phan_bo(db, don):
    return (
        (
            await db.execute(
                select(PhanBoLo.trang_thai)
                .join(CtDonHang, CtDonHang.id == PhanBoLo.ct_don_hang_id)
                .where(CtDonHang.don_hang_id == don.id)
            )
        )
        .scalars()
        .all()
    )


async def test_huy_khi_moi_giu_hang_nha_giu(db):
    don, lo = await don_co_hang_giu(db)
    ds = TacNhan.duoc_si((await tao_nhan_vien(db, "PHARMACIST")).id)
    await mt.chuyen_trang_thai(db, don, TT.da_huy, ds, "nguoi_dung", "Hết nhu cầu")
    await db.refresh(lo)
    assert (lo.so_luong_giu, lo.so_luong_ton) == (0, 20)
    assert [t.value for t in await trang_thai_phan_bo(db, don)] == ["da_nha"]


async def test_bat_dau_soan_xuat_kho_roi_huy_hoan_nhap_dung_lo_va_bam_ke_nhan_ban(db):
    don, lo = await don_co_hang_giu(db, trang_thai="da_xac_nhan")
    kho = TacNhan.kho((await tao_nhan_vien(db, "WAREHOUSE")).id)
    await mt.chuyen_trang_thai(db, don, TT.dang_soan_hang, kho, "nguoi_dung")
    await db.refresh(lo)
    assert (lo.so_luong_ton, lo.so_luong_giu) == (16, 0)
    with pytest.raises(LoiNghiepVu) as e:  # bấm lần hai: không xuất kho hai lần
        await mt.chuyen_trang_thai(db, don, TT.dang_soan_hang, kho, "nguoi_dung")
    assert e.value.ma_loi == "CHUYEN_TRANG_THAI_KHONG_HOP_LE"
    await db.refresh(lo)
    assert lo.so_luong_ton == 16
    ds = TacNhan.duoc_si((await tao_nhan_vien(db, "PHARMACIST")).id)
    await mt.chuyen_trang_thai(db, don, TT.da_huy, ds, "nguoi_dung", "Khách gọi hủy")
    await db.refresh(lo)
    assert (lo.so_luong_ton, lo.so_luong_giu) == (20, 0)
    assert [t.value for t in await trang_thai_phan_bo(db, don)] == ["da_hoan_nhap"]


async def test_hook_loi_thi_ca_lan_chuyen_bi_hoan_tac(db, monkeypatch):
    don = await tao_don(db, await tao_khach(db), trang_thai="cho_xac_nhan")
    ds = TacNhan.duoc_si((await tao_nhan_vien(db, "PHARMACIST")).id)

    async def hong(db_, don_, tn_):
        raise RuntimeError("hook hỏng")

    monkeypatch.setitem(mt.HOOK_THEO_DONG, 13, [hong])
    with pytest.raises(RuntimeError):
        async with db.begin_nested():
            await mt.chuyen_trang_thai(db, don, TT.da_xac_nhan, ds, "nguoi_dung")
    await db.refresh(don)
    assert don.trang_thai == TT.cho_xac_nhan
    assert (
        await db.scalar(select(func.count()).select_from(LichSuTrangThai).where(LichSuTrangThai.don_hang_id == don.id))
    ) == 0


async def test_dang_ky_hook_cho_task_sau(db, monkeypatch):
    goi = []

    async def ghi(db_, don_, tn_):
        goi.append(don_.trang_thai)

    monkeypatch.setitem(mt.HOOK_THEO_DONG, 13, [ghi])
    don = await tao_don(db, await tao_khach(db), trang_thai="cho_xac_nhan")
    await mt.chuyen_trang_thai(
        db, don, TT.da_xac_nhan, TacNhan.duoc_si((await tao_nhan_vien(db, "PHARMACIST")).id), "nguoi_dung"
    )
    assert goi == [TT.da_xac_nhan] and don.nhan_vien_xac_nhan_id is not None


# --- Không nơi nào khác được gán trạng thái đơn ---

APP = Path(__file__).resolve().parents[2] / "app"
TRONG_PHAM_VI = {APP / "modules" / "ban_hang" / "trang_thai.py"}


def _tim_vi_pham(duong_dan: Path) -> list[str]:
    cay = ast.parse(duong_dan.read_text(encoding="utf-8"))
    ten_don = lambda n: isinstance(n, ast.Name) and n.id.startswith("don")  # noqa: E731
    vi_pham = []
    for nut in ast.walk(cay):
        muc_tieu = []
        if isinstance(nut, ast.Assign):
            muc_tieu = nut.targets
        elif isinstance(nut, (ast.AugAssign, ast.AnnAssign)):
            muc_tieu = [nut.target]
        for m in muc_tieu:
            if isinstance(m, ast.Attribute) and m.attr == "trang_thai":
                goc = m.value
                if ten_don(goc) or (isinstance(goc, ast.Attribute) and goc.attr in {"don_hang", "don"}):
                    vi_pham.append(f"{duong_dan}:{nut.lineno} gán .trang_thai của đơn")
        if isinstance(nut, ast.Call):
            ten = nut.func.id if isinstance(nut.func, ast.Name) else getattr(nut.func, "attr", "")
            if ten == "DonHang" and any(k.arg == "trang_thai" for k in nut.keywords):
                vi_pham.append(f"{duong_dan}:{nut.lineno} DonHang(trang_thai=...)")
            if ten in {"values", "update"} and any(k.arg == "trang_thai" for k in nut.keywords):
                goc = ast.unparse(nut)
                if "DonHang" in goc or "don_hang" in goc:
                    vi_pham.append(f"{duong_dan}:{nut.lineno} UPDATE don_hang SET trang_thai")
    return vi_pham


def test_khong_noi_nao_khac_gan_trang_thai_don():
    vi_pham = []
    for f in APP.rglob("*.py"):
        if f in TRONG_PHAM_VI:
            continue
        vi_pham += _tim_vi_pham(f)
        if "UPDATE don_hang" in f.read_text(encoding="utf-8") and "trang_thai" in f.read_text(encoding="utf-8"):
            vi_pham.append(f"{f}: SQL thô cập nhật don_hang")
    assert vi_pham == []


def test_bo_quet_bat_duoc_vi_pham_mau(tmp_path):
    mau = tmp_path / "x.py"
    mau.write_text("def f(don):\n    don.trang_thai = 1\n\ndef g():\n    return DonHang(trang_thai=1)\n")
    assert len(_tim_vi_pham(mau)) == 2

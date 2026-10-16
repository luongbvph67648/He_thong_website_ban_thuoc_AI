"""DS10: nội dung chuyên môn theo phiên bản (/api/v1/noi-bo/chuyen-mon)."""

import asyncio

import pytest
from sqlalchemy import func, select

from app.core import phan_quyen
from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc
from app.models.enums import TrangThaiNoiDung
from app.models.he_thong import NhanVien, Quyen, VaiTro, VaiTroQuyen
from app.models.san_pham import ThongTinChuyenMon
from app.modules.chuyen_mon import noi_dung as dich_vu
from app.modules.chuyen_mon.schemas_noi_dung import NoiDungVao
from tests.chuyen_mon.mau_chuyen_mon import GOC_NOI_DUNG, la_loi, noi_dung, soan
from tests.factories import tao_nhan_vien, tao_san_pham
from tests.nhan_vien.dung_chung import nhat_ky

# --- Tạo phiên bản -------------------------------------------------------------------------------------------------------


async def test_phien_ban_dau_tien_la_nhap_do_duoc_si_soan_khong_ai_duyet(dang_nhap_duoc_si, db):
    sp = await tao_san_pham(db)
    ban = await soan(dang_nhap_duoc_si, sp.id, None, chi_dinh="  Giảm đau\n\n  hạ sốt  ", tac_dung_phu="   ")
    assert ban["phien_ban"] == 1 and ban["trang_thai"] == "nhap" and ban["san_pham_id"] == sp.id
    assert ban["chi_dinh"] == "Giảm đau\n\n  hạ sốt"  # cắt đầu cuối, giữ xuống dòng
    assert ban["tac_dung_phu"] is None  # chỉ khoảng trắng là trống
    assert ban["nguoi_soan"]["id"] == dang_nhap_duoc_si.tai_khoan.id
    assert ban["duoc_si_duyet"] is None and ban["ngay_duyet"] is None
    ghi = await nhat_ky(db, dang_nhap_duoc_si.tai_khoan.id, "tao")
    assert len(ghi) == 1 and ghi[0].bang == "thong_tin_chuyen_mon" and ghi[0].ban_ghi_id == str(ban["id"])
    assert ghi[0].gia_tri_moi == {"san_pham_id": sp.id, "phien_ban": 1, "trang_thai": "nhap"}


async def test_moi_lan_sua_la_mot_phien_ban_moi_ban_cu_giu_nguyen(dang_nhap_duoc_si, db):
    sp = await tao_san_pham(db)
    v1 = await soan(dang_nhap_duoc_si, sp.id, None)
    v2 = await soan(dang_nhap_duoc_si, sp.id, 1, chi_dinh="Giảm đau mạnh")
    assert (v1["phien_ban"], v2["phien_ban"]) == (1, 2) and v1["id"] != v2["id"]
    tat_ca = (await dang_nhap_duoc_si.get(f"{GOC_NOI_DUNG}/san-pham/{sp.id}")).json()
    assert [b["phien_ban"] for b in tat_ca["phien_ban"]] == [2, 1]  # mới nhất trước
    assert tat_ca["phien_ban"][1]["chi_dinh"] == "Giảm đau, hạ sốt"  # bản cũ không bị sửa tại chỗ
    assert tat_ca["phien_ban_hien_thi"] is None and tat_ca["san_pham"]["sku"] == sp.sku


@pytest.mark.parametrize(
    ("ten_ca", "ghi_de"),
    [
        ("trường lạ", {"ten": "x"}),
        ("trường thương mại", {"gia_ban": "1000"}),
        ("ký tự điều khiển", {"chi_dinh": "a\u0000b"}),
        ("ký tự vô hình", {"than_trong": "a​b"}),
        ("quá dài", {"tre_em": "x" * 20_001}),
        ("không phải chuỗi", {"bao_quan": 5}),
        ("URL nguy hiểm", {"file_hdsd_url": "javascript:alert(1)"}),
        ("URL giao thức tương đối", {"file_hdsd_url": "//evil.example/x.pdf"}),
        ("phiên bản cơ sở sai kiểu", {"phien_ban_co_so": "một"}),
        ("phiên bản cơ sở bằng 0", {"phien_ban_co_so": 0}),
    ],
)
async def test_noi_dung_sai_la_400_va_khong_tao_gi(dang_nhap_duoc_si, db, ten_ca, ghi_de):
    sp = await tao_san_pham(db)
    phan_hoi = await dang_nhap_duoc_si.post(f"{GOC_NOI_DUNG}/san-pham/{sp.id}", json=noi_dung(None, **ghi_de))
    assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE"), (ten_ca, phan_hoi.text)
    assert (await db.execute(select(func.count()).select_from(ThongTinChuyenMon))).scalar_one() == 0


async def test_thieu_phien_ban_co_so_la_400_khong_the_bo_qua_kiem_tra_xung_dot(dang_nhap_duoc_si, db):
    sp = await tao_san_pham(db)
    than = noi_dung(None)
    del than["phien_ban_co_so"]
    assert la_loi(
        await dang_nhap_duoc_si.post(f"{GOC_NOI_DUNG}/san-pham/{sp.id}", json=than), 400, "DU_LIEU_KHONG_HOP_LE"
    )


async def test_phien_ban_co_so_cu_hoac_sai_la_409_khong_tao_ban_moi(dang_nhap_duoc_si, db):
    sp = await tao_san_pham(db)
    await soan(dang_nhap_duoc_si, sp.id, None)
    await soan(dang_nhap_duoc_si, sp.id, 1, chi_dinh="Bản hai")
    for co_so in (None, 1, 3):  # chưa thấy bản nào, bản đã cũ, bản chưa tồn tại
        phan_hoi = await dang_nhap_duoc_si.post(
            f"{GOC_NOI_DUNG}/san-pham/{sp.id}", json=noi_dung(co_so, chi_dinh="Bản ba")
        )
        assert la_loi(phan_hoi, 409, "DU_LIEU_DA_THAY_DOI"), co_so
    assert (await db.execute(select(func.count()).select_from(ThongTinChuyenMon))).scalar_one() == 2


async def test_noi_dung_giong_het_ban_moi_nhat_la_400(dang_nhap_duoc_si, db):
    sp = await tao_san_pham(db)
    await soan(dang_nhap_duoc_si, sp.id, None)
    phan_hoi = await dang_nhap_duoc_si.post(f"{GOC_NOI_DUNG}/san-pham/{sp.id}", json=noi_dung(1))
    assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE")
    assert "Không có thay đổi" in phan_hoi.text


async def test_soan_lai_noi_dung_cua_ban_da_bo_duoc_nhung_so_phien_ban_khong_bao_gio_dung_lai(dang_nhap_duoc_si, db):
    sp = await tao_san_pham(db)
    v1 = await soan(dang_nhap_duoc_si, sp.id, None)
    assert (await dang_nhap_duoc_si.post(f"{GOC_NOI_DUNG}/{v1['id']}/luu-tru")).status_code == 200
    assert la_loi(
        await dang_nhap_duoc_si.post(f"{GOC_NOI_DUNG}/san-pham/{sp.id}", json=noi_dung(None)),
        409,
        "DU_LIEU_DA_THAY_DOI",
    )
    v2 = await soan(dang_nhap_duoc_si, sp.id, 1)  # cùng nội dung với bản đã bỏ: được, là bản số 2
    assert v2["phien_ban"] == 2
    assert la_loi(
        await dang_nhap_duoc_si.post(f"{GOC_NOI_DUNG}/san-pham/{sp.id}", json=noi_dung(2)), 400, "DU_LIEU_KHONG_HOP_LE"
    )


async def test_san_pham_khong_co_hoac_da_xoa_la_404(dang_nhap_duoc_si, db):
    da_xoa = await tao_san_pham(db, deleted_at=bay_gio_utc())
    for san_pham_id in (da_xoa.id, 2_000_000_000):
        assert la_loi(await dang_nhap_duoc_si.get(f"{GOC_NOI_DUNG}/san-pham/{san_pham_id}"), 404, "KHONG_TIM_THAY")
        phan_hoi = await dang_nhap_duoc_si.post(f"{GOC_NOI_DUNG}/san-pham/{san_pham_id}", json=noi_dung(None))
        assert la_loi(phan_hoi, 404, "KHONG_TIM_THAY")
    assert la_loi(await dang_nhap_duoc_si.get(f"{GOC_NOI_DUNG}/san-pham/2147483648"), 400, "DU_LIEU_KHONG_HOP_LE")


# --- Duyệt và lưu trữ ----------------------------------------------------------------------------------------------------


async def test_duyet_ban_nhap_ghi_nguoi_duyet_ngay_duyet_va_thanh_ban_hien_thi(dang_nhap_duoc_si, db):
    sp = await tao_san_pham(db)
    v1 = await soan(dang_nhap_duoc_si, sp.id, None)
    phan_hoi = await dang_nhap_duoc_si.post(f"{GOC_NOI_DUNG}/{v1['id']}/duyet")
    assert phan_hoi.status_code == 200, phan_hoi.text
    ban = phan_hoi.json()
    assert ban["trang_thai"] == "da_duyet" and ban["duoc_si_duyet"]["id"] == dang_nhap_duoc_si.tai_khoan.id
    assert ban["ngay_duyet"] is not None
    tat_ca = (await dang_nhap_duoc_si.get(f"{GOC_NOI_DUNG}/san-pham/{sp.id}")).json()
    assert tat_ca["phien_ban_hien_thi"] == 1
    da_duyet = await dich_vu.noi_dung_da_duyet(db, sp.id)
    assert da_duyet is not None and da_duyet.phien_ban == 1 and da_duyet.chi_dinh == "Giảm đau, hạ sốt"
    ghi = await nhat_ky(db, dang_nhap_duoc_si.tai_khoan.id, "duyet")
    assert len(ghi) == 1 and ghi[0].gia_tri_moi == {"san_pham_id": sp.id, "phien_ban": 1, "trang_thai": "da_duyet"}


async def test_chua_duyet_thi_khong_co_noi_dung_hien_thi_ban_nhap_khong_lo_ra(dang_nhap_duoc_si, db):
    sp = await tao_san_pham(db)
    await soan(dang_nhap_duoc_si, sp.id, None)
    assert await dich_vu.noi_dung_da_duyet(db, sp.id) is None


async def test_duyet_ban_moi_dua_ban_da_duyet_cu_sang_luu_tru_luon_chi_mot_ban_hien_thi(dang_nhap_duoc_si, db):
    sp = await tao_san_pham(db)
    v1 = await soan(dang_nhap_duoc_si, sp.id, None)
    v2 = await soan(dang_nhap_duoc_si, sp.id, 1, chi_dinh="Bản hai")
    assert (await dang_nhap_duoc_si.post(f"{GOC_NOI_DUNG}/{v1['id']}/duyet")).status_code == 200
    assert (await dang_nhap_duoc_si.post(f"{GOC_NOI_DUNG}/{v2['id']}/duyet")).status_code == 200
    tat_ca = (await dang_nhap_duoc_si.get(f"{GOC_NOI_DUNG}/san-pham/{sp.id}")).json()
    assert [(b["phien_ban"], b["trang_thai"]) for b in tat_ca["phien_ban"]] == [(2, "da_duyet"), (1, "luu_tru")]
    assert tat_ca["phien_ban_hien_thi"] == 2
    assert (await dich_vu.noi_dung_da_duyet(db, sp.id)).chi_dinh == "Bản hai"


async def test_khong_duyet_lai_ban_da_duyet_hay_da_luu_tru(dang_nhap_duoc_si, db):
    sp = await tao_san_pham(db)
    v1 = await soan(dang_nhap_duoc_si, sp.id, None)
    v2 = await soan(dang_nhap_duoc_si, sp.id, 1, chi_dinh="Bản hai")
    assert (await dang_nhap_duoc_si.post(f"{GOC_NOI_DUNG}/{v1['id']}/duyet")).status_code == 200
    assert la_loi(await dang_nhap_duoc_si.post(f"{GOC_NOI_DUNG}/{v1['id']}/duyet"), 409, "DU_LIEU_DA_THAY_DOI")
    assert (await dang_nhap_duoc_si.post(f"{GOC_NOI_DUNG}/{v2['id']}/duyet")).status_code == 200
    assert la_loi(
        await dang_nhap_duoc_si.post(f"{GOC_NOI_DUNG}/{v1['id']}/duyet"), 409, "DU_LIEU_DA_THAY_DOI"
    )  # đã lưu trữ


async def test_khong_duyet_ban_nhap_cu_hon_ban_dang_hien_thi_noi_dung_khong_lui(dang_nhap_duoc_si, db):
    sp = await tao_san_pham(db)
    v1 = await soan(dang_nhap_duoc_si, sp.id, None)
    v2 = await soan(dang_nhap_duoc_si, sp.id, 1, chi_dinh="Bản hai")
    assert (await dang_nhap_duoc_si.post(f"{GOC_NOI_DUNG}/{v2['id']}/duyet")).status_code == 200
    phan_hoi = await dang_nhap_duoc_si.post(f"{GOC_NOI_DUNG}/{v1['id']}/duyet")  # v1 còn là nháp nhưng cũ hơn v2
    assert la_loi(phan_hoi, 409, "DU_LIEU_DA_THAY_DOI")
    assert (await dich_vu.noi_dung_da_duyet(db, sp.id)).phien_ban == 2


async def test_luu_tru_ban_nhap_khong_dong_toi_ban_da_duyet(dang_nhap_duoc_si, db):
    sp = await tao_san_pham(db)
    v1 = await soan(dang_nhap_duoc_si, sp.id, None)
    v2 = await soan(dang_nhap_duoc_si, sp.id, 1, chi_dinh="Bản hai")
    assert (await dang_nhap_duoc_si.post(f"{GOC_NOI_DUNG}/{v1['id']}/duyet")).status_code == 200
    bo = await dang_nhap_duoc_si.post(f"{GOC_NOI_DUNG}/{v2['id']}/luu-tru")
    assert bo.status_code == 200 and bo.json()["trang_thai"] == "luu_tru"
    assert la_loi(await dang_nhap_duoc_si.post(f"{GOC_NOI_DUNG}/{v1['id']}/luu-tru"), 409, "DU_LIEU_DA_THAY_DOI")
    assert (await dich_vu.noi_dung_da_duyet(db, sp.id)).phien_ban == 1
    assert la_loi(await dang_nhap_duoc_si.post(f"{GOC_NOI_DUNG}/{v2['id']}/duyet"), 409, "DU_LIEU_DA_THAY_DOI")  # đã bỏ
    assert len(await nhat_ky(db, dang_nhap_duoc_si.tai_khoan.id, "sua")) == 1


async def test_duyet_phien_ban_khong_co_hoac_cua_san_pham_da_xoa_la_404(dang_nhap_duoc_si, db):
    assert la_loi(await dang_nhap_duoc_si.post(f"{GOC_NOI_DUNG}/2000000000/duyet"), 404, "KHONG_TIM_THAY")
    sp = await tao_san_pham(db)
    v1 = await soan(dang_nhap_duoc_si, sp.id, None)
    sp.deleted_at = bay_gio_utc()
    await db.flush()
    assert la_loi(await dang_nhap_duoc_si.post(f"{GOC_NOI_DUNG}/{v1['id']}/duyet"), 404, "KHONG_TIM_THAY")
    assert la_loi(await dang_nhap_duoc_si.post(f"{GOC_NOI_DUNG}/{v1['id']}/luu-tru"), 404, "KHONG_TIM_THAY")


# --- Danh sách -----------------------------------------------------------------------------------------------------------


async def test_danh_sach_tinh_trang_va_bo_loc(dang_nhap_duoc_si, db):
    await tao_san_pham(db, ten="Chưa có nội dung", sku="CM-A")
    cho_duyet = await tao_san_pham(db, ten="Đang chờ duyệt", sku="CM-B")
    da_duyet = await tao_san_pham(db, ten="Đã duyệt xong", sku="CM-C")
    co_ban_moi = await tao_san_pham(db, ten="Đã duyệt có bản mới", sku="CM-D")
    await tao_san_pham(db, ten="Đã xóa", sku="CM-E", deleted_at=bay_gio_utc())
    await soan(dang_nhap_duoc_si, cho_duyet.id, None)
    v = await soan(dang_nhap_duoc_si, da_duyet.id, None)
    await dang_nhap_duoc_si.post(f"{GOC_NOI_DUNG}/{v['id']}/duyet")
    v = await soan(dang_nhap_duoc_si, co_ban_moi.id, None)
    await dang_nhap_duoc_si.post(f"{GOC_NOI_DUNG}/{v['id']}/duyet")
    await soan(dang_nhap_duoc_si, co_ban_moi.id, 1, chi_dinh="Bản hai chưa duyệt")

    async def lay(**tham):
        r = await dang_nhap_duoc_si.get(GOC_NOI_DUNG, params={"kich_thuoc": 100, **tham})
        assert r.status_code == 200, r.text
        return {d["sku"]: d for d in r.json()["du_lieu"] if d["sku"].startswith("CM-")}

    tat_ca = await lay()
    assert set(tat_ca) == {"CM-A", "CM-B", "CM-C", "CM-D"}  # không có sản phẩm đã xóa
    assert tat_ca["CM-A"]["phien_ban_da_duyet"] is None and tat_ca["CM-A"]["cho_duyet"] is False
    assert tat_ca["CM-B"]["phien_ban_da_duyet"] is None and tat_ca["CM-B"]["cho_duyet"] is True
    assert tat_ca["CM-B"]["phien_ban_nhap_moi_nhat"] == 1
    assert tat_ca["CM-C"]["phien_ban_da_duyet"] == 1 and tat_ca["CM-C"]["cho_duyet"] is False
    assert tat_ca["CM-C"]["ngay_duyet"] is not None
    assert tat_ca["CM-D"]["phien_ban_da_duyet"] == 1 and tat_ca["CM-D"]["phien_ban_nhap_moi_nhat"] == 2
    assert tat_ca["CM-D"]["cho_duyet"] is True
    assert set(await lay(loc="cho_duyet")) == {"CM-B", "CM-D"}
    assert set(await lay(loc="da_duyet")) == {"CM-C", "CM-D"}
    assert set(await lay(loc="chua_co_noi_dung")) == {"CM-A", "CM-B"}
    assert set(await lay(q="cho duyet")) == {"CM-B"}  # không phân biệt dấu
    assert set(await lay(q="cm-c")) == {"CM-C"}  # theo SKU
    assert la_loi(await dang_nhap_duoc_si.get(GOC_NOI_DUNG, params={"loc": "bay_ba"}), 400, "DU_LIEU_KHONG_HOP_LE")


# --- Phân quyền ----------------------------------------------------------------------------------------------------------


async def test_admin_chi_xem_khong_soan_khong_duyet_khong_luu_tru(clients_theo_vai_tro, db):
    duoc_si, admin = clients_theo_vai_tro["PHARMACIST"], clients_theo_vai_tro["ADMIN"]
    sp = await tao_san_pham(db)
    v1 = await soan(duoc_si, sp.id, None)
    assert (await admin.get(GOC_NOI_DUNG)).status_code == 200
    assert (await admin.get(f"{GOC_NOI_DUNG}/san-pham/{sp.id}")).status_code == 200  # Admin chỉ xem
    for phuong_thuc, duong, than in (
        ("post", f"{GOC_NOI_DUNG}/san-pham/{sp.id}", noi_dung(1, chi_dinh="Admin sửa")),
        ("post", f"{GOC_NOI_DUNG}/{v1['id']}/duyet", None),
        ("post", f"{GOC_NOI_DUNG}/{v1['id']}/luu-tru", None),
    ):
        phan_hoi = await getattr(admin, phuong_thuc)(duong, **({"json": than} if than else {}))
        assert la_loi(phan_hoi, 403, "KHONG_CO_QUYEN"), duong
    assert (await db.execute(select(func.count()).select_from(ThongTinChuyenMon))).scalar_one() == 1


async def test_nhan_vien_kho_va_khach_khong_vao_duoc(clients_theo_vai_tro, dang_nhap_khach, client, db):
    sp = await tao_san_pham(db)
    for may in (clients_theo_vai_tro["WAREHOUSE"],):
        assert la_loi(await may.get(GOC_NOI_DUNG), 403, "KHONG_CO_QUYEN")
        assert la_loi(await may.post(f"{GOC_NOI_DUNG}/san-pham/{sp.id}", json=noi_dung(None)), 403, "KHONG_CO_QUYEN")
    assert (await client.get(GOC_NOI_DUNG)).status_code == 401
    assert (await dang_nhap_khach.get(GOC_NOI_DUNG)).status_code == 401


@pytest.mark.parametrize("ma_quyen", ["content.professional.edit", "content.approve"])
async def test_quyen_chuyen_mon_cap_cho_vai_tro_khac_van_khong_cho_ghi(clients_theo_vai_tro, db, ma_quyen):
    """Lớp phòng thủ thứ hai: Admin gán `day_du` cho kho bằng cấu hình sai vẫn không sửa nội dung chuyên môn được."""
    duoc_si, kho = clients_theo_vai_tro["PHARMACIST"], clients_theo_vai_tro["WAREHOUSE"]
    sp = await tao_san_pham(db)
    v1 = await soan(duoc_si, sp.id, None)
    vai_tro_id = (await db.execute(select(VaiTro.id).where(VaiTro.ma == "WAREHOUSE"))).scalar_one()
    for ma in ("content.professional.edit", "content.approve"):
        quyen_id = (await db.execute(select(Quyen.id).where(Quyen.ma == ma))).scalar_one()
        db.add(VaiTroQuyen(vai_tro_id=vai_tro_id, quyen_id=quyen_id, gioi_han=None))
    await db.flush()
    phan_quyen.xoa_cache_quyen()
    assert (await kho.get(f"{GOC_NOI_DUNG}/san-pham/{sp.id}")).status_code == 200  # đọc qua mã quyền
    for duong, than in (
        (f"{GOC_NOI_DUNG}/san-pham/{sp.id}", noi_dung(1, chi_dinh="Kho sửa")),
        (f"{GOC_NOI_DUNG}/{v1['id']}/duyet", None),
        (f"{GOC_NOI_DUNG}/{v1['id']}/luu-tru", None),
    ):
        phan_hoi = await kho.post(duong, **({"json": than} if than else {}))
        assert la_loi(phan_hoi, 403, "KHONG_CO_QUYEN"), (ma_quyen, duong)
    assert (await db.execute(select(func.count()).select_from(ThongTinChuyenMon))).scalar_one() == 1
    assert (await db.get(ThongTinChuyenMon, v1["id"])).trang_thai == TrangThaiNoiDung.nhap


# --- Đồng thời -----------------------------------------------------------------------------------------------------------


async def _duoc_si_va_san_pham(db_that):
    async with db_that() as s, s.begin():
        duoc_si_id = (await tao_nhan_vien(s, "PHARMACIST")).id
        sp_id = (await tao_san_pham(s)).id
    return duoc_si_id, sp_id


async def test_hai_duoc_si_soan_cung_luc_tu_cung_ban_chi_mot_ben_thanh_cong(db_that):
    duoc_si_id, sp_id = await _duoc_si_va_san_pham(db_that)

    async def soan_ban(chi_dinh):
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, duoc_si_id)
            du_lieu = NoiDungVao.model_validate(noi_dung(None, chi_dinh=chi_dinh))
            await dich_vu.tao_phien_ban(s, actor, sp_id, du_lieu, ip="127.0.0.1")
            await asyncio.sleep(0.3)  # giữ giao dịch mở để bên kia phải chờ khóa sản phẩm

    ket_qua = await asyncio.wait_for(asyncio.gather(soan_ban("A"), soan_ban("B"), return_exceptions=True), timeout=20)
    loi = [k for k in ket_qua if k is not None]
    assert len(loi) == 1 and isinstance(loi[0], LoiNghiepVu) and loi[0].ma_loi == "DU_LIEU_DA_THAY_DOI", ket_qua
    async with db_that() as s:
        cac_ban = list((await s.execute(select(ThongTinChuyenMon.phien_ban))).scalars())
    assert cac_ban == [1]


async def test_duyet_hai_ban_nhap_cung_luc_luon_con_dung_mot_ban_hien_thi_va_khong_lui(db_that):
    duoc_si_id, sp_id = await _duoc_si_va_san_pham(db_that)
    async with db_that() as s, s.begin():
        actor = await s.get(NhanVien, duoc_si_id)
        v1 = await dich_vu.tao_phien_ban(s, actor, sp_id, NoiDungVao.model_validate(noi_dung(None)), ip="1.1.1.1")
        v2 = await dich_vu.tao_phien_ban(
            s, actor, sp_id, NoiDungVao.model_validate(noi_dung(1, chi_dinh="Bản hai")), ip="1.1.1.1"
        )
        id_1, id_2 = v1.id, v2.id

    async def duyet(phien_ban_id):
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, duoc_si_id)
            await dich_vu.duyet(s, actor, phien_ban_id, ip="127.0.0.1")
            await asyncio.sleep(0.3)

    ket_qua = await asyncio.wait_for(asyncio.gather(duyet(id_1), duyet(id_2), return_exceptions=True), timeout=20)
    async with db_that() as s:
        da_duyet = list(
            (
                await s.execute(
                    select(ThongTinChuyenMon.phien_ban).where(ThongTinChuyenMon.trang_thai == TrangThaiNoiDung.da_duyet)
                )
            ).scalars()
        )
    assert da_duyet == [2], (ket_qua, da_duyet)  # dù thứ tự nào, bản mới hơn thắng; không bao giờ hai bản đã duyệt
    thua = [k for k in ket_qua if k is not None]
    assert all(isinstance(k, LoiNghiepVu) and k.ma_loi == "DU_LIEU_DA_THAY_DOI" for k in thua)

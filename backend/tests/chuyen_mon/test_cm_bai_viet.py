"""DS10: duyệt bài viết sức khỏe (/api/v1/noi-bo/bai-viet-cho-duyet)."""

from sqlalchemy import select

from app.core import phan_quyen
from app.models.enums import LoaiBaiViet, TrangThaiNoiDung
from app.models.he_thong import BaiViet, Quyen, VaiTro, VaiTroQuyen
from tests.chuyen_mon.mau_chuyen_mon import GOC_BAI_VIET, la_loi
from tests.factories import tao_nhan_vien
from tests.nhan_vien.dung_chung import nhat_ky


async def bai_viet(db, tac_gia, tieu_de="Cách phòng cảm cúm", **truong) -> BaiViet:
    bv = BaiViet(
        tieu_de=tieu_de,
        slug=truong.pop("slug", tieu_de.lower().replace(" ", "-") + f"-{id(truong)}"),
        noi_dung="Nội dung bài viết sức khỏe",
        tac_gia_id=tac_gia.id,
        **truong,
    )
    db.add(bv)
    await db.flush()
    return bv


GIA = {"phien_ban": "0" * 16}  # phiên bản giả: đủ cho các ca bị chặn trước khi so phiên bản


async def test_danh_sach_chi_gom_bai_suc_khoe_dang_cho_duyet_cu_nhat_truoc(clients_theo_vai_tro, db):
    duoc_si = clients_theo_vai_tro["PHARMACIST"]
    admin = await tao_nhan_vien(db, "ADMIN", ho_ten="Admin Soạn Bài")
    cu = await bai_viet(db, admin, "Bài cũ", slug="bai-cu")
    moi = await bai_viet(db, admin, "Bài mới", slug="bai-moi")
    await bai_viet(db, admin, "Đã duyệt", slug="da-duyet", trang_thai=TrangThaiNoiDung.da_duyet)
    await bai_viet(db, admin, "Chính sách", slug="chinh-sach", loai=LoaiBaiViet.chinh_sach)
    await bai_viet(db, admin, "Câu hỏi", slug="faq", loai=LoaiBaiViet.faq)
    phan_hoi = await duoc_si.get(GOC_BAI_VIET)
    assert phan_hoi.status_code == 200, phan_hoi.text
    du_lieu = phan_hoi.json()["du_lieu"]
    assert [b["id"] for b in du_lieu] == [cu.id, moi.id]
    assert du_lieu[0]["tac_gia"] == "Admin Soạn Bài" and "noi_dung" not in du_lieu[0]
    assert [b["id"] for b in (await duoc_si.get(GOC_BAI_VIET, params={"q": "moi"})).json()["du_lieu"]] == [moi.id]


async def test_duyet_ghi_nguoi_duyet_ngay_duyet_va_nhat_ky(clients_theo_vai_tro, db):
    duoc_si = clients_theo_vai_tro["PHARMACIST"]
    admin = await tao_nhan_vien(db, "ADMIN")
    bv = await bai_viet(db, admin)
    chi_tiet = await duoc_si.get(f"{GOC_BAI_VIET}/{bv.id}")
    assert chi_tiet.status_code == 200 and chi_tiet.json()["noi_dung"] == "Nội dung bài viết sức khỏe"
    phien_ban = (await duoc_si.get(f"{GOC_BAI_VIET}/{bv.id}")).json()["phien_ban"]
    phan_hoi = await duoc_si.post(f"{GOC_BAI_VIET}/{bv.id}/duyet", json={"phien_ban": phien_ban})
    assert phan_hoi.status_code == 200, phan_hoi.text
    ket_qua = phan_hoi.json()
    assert ket_qua["trang_thai"] == "da_duyet" and ket_qua["ngay_duyet"] is not None and ket_qua["duoc_si_duyet"]
    await db.refresh(bv)
    assert bv.trang_thai == TrangThaiNoiDung.da_duyet and bv.duoc_si_duyet_id is not None
    ghi = await nhat_ky(db, bv.duoc_si_duyet_id, "duyet")
    assert len(ghi) == 1 and ghi[0].bang == "bai_viet" and ghi[0].ban_ghi_id == str(bv.id)
    assert (await duoc_si.get(GOC_BAI_VIET)).json()["tong"] == 0  # không còn trong danh sách chờ


async def test_khong_duyet_lai_va_khong_duyet_chinh_sach_hay_bai_khong_co(clients_theo_vai_tro, db):
    duoc_si = clients_theo_vai_tro["PHARMACIST"]
    admin = await tao_nhan_vien(db, "ADMIN")
    bv = await bai_viet(db, admin)
    chinh_sach = await bai_viet(db, admin, "Chính sách đổi trả", slug="cs", loai=LoaiBaiViet.chinh_sach)
    phien_ban = (await duoc_si.get(f"{GOC_BAI_VIET}/{bv.id}")).json()["phien_ban"]
    assert (await duoc_si.post(f"{GOC_BAI_VIET}/{bv.id}/duyet", json={"phien_ban": phien_ban})).status_code == 200
    assert la_loi(await duoc_si.post(f"{GOC_BAI_VIET}/{bv.id}/duyet", json=GIA), 409, "DU_LIEU_DA_THAY_DOI")
    for bai_id in (chinh_sach.id, 2_000_000_000):
        assert la_loi(await duoc_si.get(f"{GOC_BAI_VIET}/{bai_id}"), 404, "KHONG_TIM_THAY")
        assert la_loi(await duoc_si.post(f"{GOC_BAI_VIET}/{bai_id}/duyet", json=GIA), 404, "KHONG_TIM_THAY")
    await db.refresh(chinh_sach)
    assert chinh_sach.trang_thai == TrangThaiNoiDung.nhap  # chính sách không qua dược sĩ


async def test_admin_chi_xem_khong_tu_duyet_bai_cua_minh_kho_va_khach_khong_vao(
    clients_theo_vai_tro, dang_nhap_khach, client, db
):
    admin, kho = clients_theo_vai_tro["ADMIN"], clients_theo_vai_tro["WAREHOUSE"]
    tac_gia = await tao_nhan_vien(db, "ADMIN")
    bv = await bai_viet(db, tac_gia)
    assert (await admin.get(GOC_BAI_VIET)).status_code == 200  # Admin chỉ xem
    assert (await admin.get(f"{GOC_BAI_VIET}/{bv.id}")).status_code == 200
    assert la_loi(await admin.post(f"{GOC_BAI_VIET}/{bv.id}/duyet", json=GIA), 403, "KHONG_CO_QUYEN")
    assert la_loi(await kho.get(GOC_BAI_VIET), 403, "KHONG_CO_QUYEN")
    assert la_loi(await kho.post(f"{GOC_BAI_VIET}/{bv.id}/duyet", json=GIA), 403, "KHONG_CO_QUYEN")
    assert (await client.get(GOC_BAI_VIET)).status_code == 401
    assert (await dang_nhap_khach.get(GOC_BAI_VIET)).status_code == 401
    await db.refresh(bv)
    assert bv.trang_thai == TrangThaiNoiDung.nhap and bv.duoc_si_duyet_id is None


async def test_quyen_duyet_cap_cho_kho_van_khong_cho_duyet(clients_theo_vai_tro, db):
    kho = clients_theo_vai_tro["WAREHOUSE"]
    tac_gia = await tao_nhan_vien(db, "ADMIN")
    bv = await bai_viet(db, tac_gia)
    vai_tro_id = (await db.execute(select(VaiTro.id).where(VaiTro.ma == "WAREHOUSE"))).scalar_one()
    quyen_id = (await db.execute(select(Quyen.id).where(Quyen.ma == "content.approve"))).scalar_one()
    db.add(VaiTroQuyen(vai_tro_id=vai_tro_id, quyen_id=quyen_id, gioi_han=None))
    await db.flush()
    phan_quyen.xoa_cache_quyen()
    assert (await kho.get(GOC_BAI_VIET)).status_code == 200
    assert la_loi(await kho.post(f"{GOC_BAI_VIET}/{bv.id}/duyet", json=GIA), 403, "KHONG_CO_QUYEN")
    await db.refresh(bv)
    assert bv.trang_thai == TrangThaiNoiDung.nhap


async def test_duyet_dung_ban_da_doc_admin_sua_giua_chung_thi_409_va_bai_van_cho_duyet(clients_theo_vai_tro, db):
    duoc_si = clients_theo_vai_tro["PHARMACIST"]
    admin = await tao_nhan_vien(db, "ADMIN")
    bv = await bai_viet(db, admin)
    phien_ban = (await duoc_si.get(f"{GOC_BAI_VIET}/{bv.id}")).json()["phien_ban"]
    bv.noi_dung = "Nội dung Admin vừa sửa mà dược sĩ chưa đọc"
    await db.flush()
    phan_hoi = await duoc_si.post(f"{GOC_BAI_VIET}/{bv.id}/duyet", json={"phien_ban": phien_ban})
    assert la_loi(phan_hoi, 409, "DU_LIEU_DA_THAY_DOI")
    moi = phan_hoi.json()["chi_tiet"]["phien_ban_hien_tai"]
    assert moi != phien_ban
    await db.refresh(bv)
    assert bv.trang_thai == TrangThaiNoiDung.nhap and bv.duoc_si_duyet_id is None
    assert (
        await duoc_si.post(f"{GOC_BAI_VIET}/{bv.id}/duyet", json={"phien_ban": moi})
    ).status_code == 200  # đọc lại rồi duyệt


async def test_duyet_thieu_hoac_sai_phien_ban_la_400(clients_theo_vai_tro, db):
    duoc_si = clients_theo_vai_tro["PHARMACIST"]
    bv = await bai_viet(db, await tao_nhan_vien(db, "ADMIN"))
    for than in ({}, {"phien_ban": "xyz"}, {"phien_ban": "0" * 16, "them": 1}):
        assert la_loi(await duoc_si.post(f"{GOC_BAI_VIET}/{bv.id}/duyet", json=than), 400, "DU_LIEU_KHONG_HOP_LE")
    await db.refresh(bv)
    assert bv.trang_thai == TrangThaiNoiDung.nhap

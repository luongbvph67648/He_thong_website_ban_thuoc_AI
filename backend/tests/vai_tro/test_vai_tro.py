"""AD18: vai trò và phân quyền (/api/v1/noi-bo/vai-tro)."""

import asyncio

import pytest
from sqlalchemy import select

from app.core import phan_quyen
from app.models.he_thong import NhanVien, Quyen, VaiTro, VaiTroQuyen
from app.modules.vai_tro import service
from tests.factories import tao_nhan_vien
from tests.nhan_vien.dung_chung import URL_TOI, nhat_ky
from tests.nhan_vien.test_nv_ho_so import quyen_theo_yaml

GOC = "/api/v1/noi-bo/vai-tro"


def la_loi(phan_hoi, status, ma_loi):
    return phan_hoi.status_code == status and phan_hoi.json()["ma_loi"] == ma_loi


def hien_co(chi_tiet: dict) -> dict[str, str]:
    return {q["ma"]: q["muc"] for q in chi_tiet["quyen"] if q["muc"] is not None}


async def quyen_hien_tai(admin, ma="PHARMACIST") -> dict[str, str]:
    return hien_co((await admin.get(f"{GOC}/{ma}")).json())


async def test_danh_sach_vai_tro_kem_so_nhan_vien_va_so_quyen(dang_nhap_admin, db):
    await tao_nhan_vien(db, "WAREHOUSE")
    da_xoa = await tao_nhan_vien(db, "WAREHOUSE")
    da_xoa.deleted_at = da_xoa.created_at
    await db.flush()
    phan_hoi = await dang_nhap_admin.get(GOC)
    assert phan_hoi.status_code == 200
    theo_ma = {v["ma"]: v for v in phan_hoi.json()}
    assert set(theo_ma) == {"PHARMACIST", "WAREHOUSE", "ADMIN"}
    assert theo_ma["WAREHOUSE"]["so_nhan_vien"] == 1  # không tính tài khoản đã xóa mềm
    assert theo_ma["ADMIN"]["so_nhan_vien"] == 1 and theo_ma["PHARMACIST"]["so_nhan_vien"] == 0
    for ma in theo_ma:
        assert theo_ma[ma]["so_quyen"] == len(quyen_theo_yaml(ma))
    assert [theo_ma[m]["chinh_sua_duoc"] for m in ("PHARMACIST", "WAREHOUSE", "ADMIN")] == [True, True, False]


@pytest.mark.parametrize("ma", ["PHARMACIST", "WAREHOUSE", "ADMIN"])
async def test_chi_tiet_co_du_51_ma_quyen_va_khop_quyen_yaml(dang_nhap_admin, ma):
    phan_hoi = await dang_nhap_admin.get(f"{GOC}/{ma}")
    assert phan_hoi.status_code == 200
    than = phan_hoi.json()
    assert than["ma"] == ma and len(than["quyen"]) == 51
    assert hien_co(than) == quyen_theo_yaml(ma)
    assert than["chinh_sua_duoc"] is (ma != "ADMIN")
    theo_quyen = {q["ma"]: q for q in than["quyen"]}
    assert theo_quyen["profile.self"]["bat_buoc"] is True and theo_quyen["order.view"]["bat_buoc"] is False
    assert theo_quyen["content.approve"]["chi_cho_vai_tro"] == "PHARMACIST"
    assert all(q["nhom"] for q in than["quyen"]) and all(q["mo_ta"] for q in than["quyen"])


@pytest.mark.parametrize(
    ("ma", "trang_thai"), [("KHONG_CO", 404), ("pharmacist", 400), ("A" * 31, 400), ("DROP;--", 400)]
)
async def test_vai_tro_khong_ton_tai_hoac_ma_sai_dinh_dang(dang_nhap_admin, ma, trang_thai):
    assert (await dang_nhap_admin.get(f"{GOC}/{ma}")).status_code == trang_thai
    assert (
        await dang_nhap_admin.put(f"{GOC}/{ma}/quyen", json={"quyen": {"profile.self": "day_du"}})
    ).status_code == trang_thai


# --- Cập nhật quyền -------------------------------------------------------------------------------------------------


async def test_gan_bo_va_doi_muc_quyen_co_hieu_luc_ngay_cho_nhan_vien_dang_dung(dang_nhap_admin, clients_theo_vai_tro):
    duoc_si = clients_theo_vai_tro["PHARMACIST"]
    truoc = (await duoc_si.get(URL_TOI)).json()["quyen"]  # nạp cache quyền của vai trò
    assert "pos.sell" in truoc and "stock.import" not in truoc and truoc["stock.view"] == "chi_xem"

    moi = {k: v for k, v in (await quyen_hien_tai(dang_nhap_admin)).items() if k != "pos.sell"}
    moi["stock.import"] = "chi_xem"  # gán mới
    moi["stock.view"] = "day_du"  # đổi mức
    phan_hoi = await dang_nhap_admin.put(f"{GOC}/PHARMACIST/quyen", json={"quyen": moi})
    assert phan_hoi.status_code == 200 and hien_co(phan_hoi.json()) == moi

    sau = (await duoc_si.get(URL_TOI)).json()["quyen"]  # cache đã bị xóa: thấy ngay
    assert sau == moi and "pos.sell" not in sau


async def test_nhat_ky_ghi_phan_chenh_lech_theo_dang_danh_sach(dang_nhap_admin, db):
    moi = {k: v for k, v in (await quyen_hien_tai(dang_nhap_admin, "WAREHOUSE")).items() if k != "order.pick"}
    moi["return.review"] = "chi_xem"
    moi["stock.view"] = "chi_xem"  # kho đang day_du -> chi_xem
    assert (await dang_nhap_admin.put(f"{GOC}/WAREHOUSE/quyen", json={"quyen": moi})).status_code == 200
    (dong,) = await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "sua")
    assert (dong.bang, dong.ban_ghi_id) == ("vai_tro_quyen", "WAREHOUSE")
    assert dong.gia_tri_moi == {"them": ["return.review:chi_xem"]}
    assert dong.gia_tri_cu == {"bo": ["order.pick:day_du"], "doi_muc": ["stock.view:day_du->chi_xem"]}


async def test_dat_dung_nhu_hien_tai_thi_khong_ghi_nhat_ky(dang_nhap_admin, db):
    hien = await quyen_hien_tai(dang_nhap_admin)
    assert (await dang_nhap_admin.put(f"{GOC}/PHARMACIST/quyen", json={"quyen": hien})).status_code == 200
    assert await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "sua") == []


async def test_vai_tro_admin_khong_sua_duoc_du_chi_la_gui_lai_y_nguyen(dang_nhap_admin, db):
    truoc = await quyen_hien_tai(dang_nhap_admin, "ADMIN")
    for than in (
        {"quyen": truoc},  # y nguyên
        {"quyen": {"profile.self": "day_du"}},  # bỏ gần hết
        {"quyen": {**truoc, "order.confirm": "day_du"}},  # thêm quyền thao tác đơn
    ):
        phan_hoi = await dang_nhap_admin.put(f"{GOC}/ADMIN/quyen", json=than)
        assert la_loi(phan_hoi, 409, "PHAI_CON_ADMIN")
    assert await quyen_hien_tai(dang_nhap_admin, "ADMIN") == truoc == quyen_theo_yaml("ADMIN")
    assert await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "sua") == []


async def test_ma_quyen_khong_ton_tai_va_muc_khong_hop_le_tra_400_va_khong_doi_gi(dang_nhap_admin, db):
    truoc = await quyen_hien_tai(dang_nhap_admin)
    phan_hoi = await dang_nhap_admin.put(
        f"{GOC}/PHARMACIST/quyen", json={"quyen": {**truoc, "quyen.khong.co": "day_du"}}
    )
    assert phan_hoi.status_code == 400
    assert phan_hoi.json()["chi_tiet"] == [{"truong": "quyen.quyen.khong.co", "loi": "Mã quyền không tồn tại"}]
    sai_muc = await dang_nhap_admin.put(
        f"{GOC}/PHARMACIST/quyen", json={"quyen": {**truoc, "order.view": "toan_quyen"}}
    )
    assert sai_muc.status_code == 400
    assert await quyen_hien_tai(dang_nhap_admin) == truoc
    assert await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "sua") == []


@pytest.mark.parametrize("quyen_profile", [None, "chi_xem"])
async def test_profile_self_bat_buoc_o_muc_day_du(dang_nhap_admin, quyen_profile):
    """Gỡ hoặc hạ `profile.self` làm nhân viên không đổi được mật khẩu bắt buộc: bị chặn."""
    moi = {k: v for k, v in (await quyen_hien_tai(dang_nhap_admin, "WAREHOUSE")).items() if k != "profile.self"}
    if quyen_profile:
        moi["profile.self"] = quyen_profile
    phan_hoi = await dang_nhap_admin.put(f"{GOC}/WAREHOUSE/quyen", json={"quyen": moi})
    assert phan_hoi.status_code == 400
    assert phan_hoi.json()["chi_tiet"][0]["truong"] == "quyen.profile.self"
    assert (await quyen_hien_tai(dang_nhap_admin, "WAREHOUSE"))["profile.self"] == "day_du"


@pytest.mark.parametrize("ma_quyen", ["content.professional.edit", "content.approve"])
async def test_quyen_noi_dung_chuyen_mon_chi_cap_duoc_cho_duoc_si(dang_nhap_admin, ma_quyen):
    """Spec 03 mục 7: Admin không sửa nội dung chuyên môn, quyền này chỉ PHARMACIST có."""
    kho = {**(await quyen_hien_tai(dang_nhap_admin, "WAREHOUSE")), ma_quyen: "day_du"}
    phan_hoi = await dang_nhap_admin.put(f"{GOC}/WAREHOUSE/quyen", json={"quyen": kho})
    assert phan_hoi.status_code == 400 and "PHARMACIST" in phan_hoi.json()["chi_tiet"][0]["loi"]
    assert ma_quyen not in await quyen_hien_tai(dang_nhap_admin, "WAREHOUSE")
    duoc_si = {**(await quyen_hien_tai(dang_nhap_admin, "PHARMACIST")), ma_quyen: "chi_xem"}
    assert (await dang_nhap_admin.put(f"{GOC}/PHARMACIST/quyen", json={"quyen": duoc_si})).status_code == 200


async def test_loi_nhieu_cho_cung_luc_tra_het_trong_mot_lan(dang_nhap_admin):
    phan_hoi = await dang_nhap_admin.put(
        f"{GOC}/WAREHOUSE/quyen", json={"quyen": {"khong.co": "day_du", "content.approve": "day_du"}}
    )
    truong = {c["truong"] for c in phan_hoi.json()["chi_tiet"]}
    assert truong == {"quyen.khong.co", "quyen.content.approve", "quyen.profile.self"}


async def test_thieu_truong_quyen_tra_400(dang_nhap_admin):
    assert (await dang_nhap_admin.put(f"{GOC}/WAREHOUSE/quyen", json={})).status_code == 400


async def test_cap_nhat_quyen_can_quyen_role_manage(clients_theo_vai_tro, client):
    for vai_tro in ("PHARMACIST", "WAREHOUSE"):
        c = clients_theo_vai_tro[vai_tro]
        assert la_loi(await c.get(GOC), 403, "KHONG_CO_QUYEN")
        assert la_loi(
            await c.put(f"{GOC}/WAREHOUSE/quyen", json={"quyen": {"profile.self": "day_du"}}), 403, "KHONG_CO_QUYEN"
        )
    assert (await client.get(GOC)).status_code == 401


async def test_nhan_vien_khong_tu_nang_quyen_bang_cach_cap_cho_vai_tro_cua_minh(clients_theo_vai_tro):
    """Dược sĩ không có `role.manage` nên không tự gán thêm quyền cho vai trò của chính mình."""
    duoc_si = clients_theo_vai_tro["PHARMACIST"]
    phan_hoi = await duoc_si.put(
        f"{GOC}/PHARMACIST/quyen", json={"quyen": {"profile.self": "day_du", "staff.manage": "day_du"}}
    )
    assert la_loi(phan_hoi, 403, "KHONG_CO_QUYEN")
    assert "staff.manage" not in (await duoc_si.get(URL_TOI)).json()["quyen"]


# --- Đồng thời và cache ---------------------------------------------------------------------------------------------


async def test_hai_admin_sua_cung_vai_tro_cung_luc_khong_loi_va_khong_tron_lan(db_that):
    async with db_that() as s, s.begin():
        admin_id = (await tao_nhan_vien(s, "ADMIN")).id
        hien = {
            q.ma: ("day_du" if vq.gioi_han is None else "chi_xem")
            for q, vq in (
                await s.execute(
                    select(Quyen, VaiTroQuyen)
                    .join(VaiTroQuyen, VaiTroQuyen.quyen_id == Quyen.id)
                    .join(VaiTro, VaiTro.id == VaiTroQuyen.vai_tro_id)
                    .where(VaiTro.ma == "WAREHOUSE")
                )
            ).all()
        }
    muon_a = {**hien, "stock_doc.view": "chi_xem", "report.shift": "chi_xem"}
    muon_b = {**hien, "stock_doc.view": "day_du"}

    async def sua(muon):
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, admin_id)
            await service.cap_nhat_quyen(s, actor, "WAREHOUSE", muon, ip="127.0.0.1")
            await asyncio.sleep(0.3)  # giữ giao dịch mở để bên kia phải chờ khóa dòng vai trò

    ket_qua = await asyncio.wait_for(asyncio.gather(sua(muon_a), sua(muon_b), return_exceptions=True), timeout=20)
    assert ket_qua == [None, None], ket_qua  # không bên nào dính IntegrityError (khóa dòng vai trò làm hai bên tuần tự)
    async with db_that() as s:
        ket = await service.chi_tiet(s, "WAREHOUSE")
    cuoi = hien_co(ket.model_dump())
    assert cuoi in (muon_a, muon_b)  # đúng bằng một trong hai yêu cầu, không trộn lẫn


async def test_cache_xoa_lai_sau_commit_khong_giu_lai_ban_cu_do_request_khac_nap_giua_chung(db_that):
    """Request khác nạp cache bằng dữ liệu cũ GIỮA lúc service xóa cache và lúc commit: sau commit cache vẫn phải sạch."""
    async with db_that() as s, s.begin():
        admin_id = (await tao_nhan_vien(s, "ADMIN")).id
        kho_id = (await s.execute(select(VaiTro.id).where(VaiTro.ma == "WAREHOUSE"))).scalar_one()
        hien = {
            ma: ("day_du" if g is None else "chi_xem")
            for ma, g in (
                await s.execute(
                    select(Quyen.ma, VaiTroQuyen.gioi_han)
                    .join(VaiTroQuyen, VaiTroQuyen.quyen_id == Quyen.id)
                    .where(VaiTroQuyen.vai_tro_id == kho_id)
                )
            ).all()
        }
    moi = {k: v for k, v in hien.items() if k != "order.pick"}
    phan_quyen.xoa_cache_quyen()

    async with db_that() as s, s.begin():
        actor = await s.get(NhanVien, admin_id)
        await service.cap_nhat_quyen(s, actor, "WAREHOUSE", moi, ip="127.0.0.1")  # đã xóa cache, CHƯA commit
        async with db_that() as khac:  # request khác đọc dữ liệu ĐÃ commit (bản cũ) và cache lại
            assert "order.pick" in await phan_quyen.quyen_cua_vai_tro(khac, kho_id)
    # Sau commit của service: cache phải bị xóa lần nữa, nếu không bản cũ sống thêm 60 giây.
    async with db_that() as s:
        assert "order.pick" not in await phan_quyen.quyen_cua_vai_tro(s, kho_id)


async def test_quyen_gan_cho_vai_tro_lam_route_that_chap_nhan_nguoi_moi(dang_nhap_admin, clients_theo_vai_tro):
    """Kết nối AD18 với guard: cấp `staff.manage` cho PHARMACIST thì dược sĩ gọi được AD01, thu lại thì bị chặn."""
    duoc_si = clients_theo_vai_tro["PHARMACIST"]
    assert (await duoc_si.get("/api/v1/noi-bo/nhan-vien")).status_code == 403
    hien = await quyen_hien_tai(dang_nhap_admin)
    await dang_nhap_admin.put(f"{GOC}/PHARMACIST/quyen", json={"quyen": {**hien, "staff.manage": "chi_xem"}})
    assert (await duoc_si.get("/api/v1/noi-bo/nhan-vien")).status_code == 200  # chi_xem đủ cho GET
    assert (
        await duoc_si.post(
            "/api/v1/noi-bo/nhan-vien", json={"ho_ten": "X", "email": "x@example.com", "vai_tro": "WAREHOUSE"}
        )
    ).status_code == 403
    await dang_nhap_admin.put(f"{GOC}/PHARMACIST/quyen", json={"quyen": hien})
    assert (await duoc_si.get("/api/v1/noi-bo/nhan-vien")).status_code == 403

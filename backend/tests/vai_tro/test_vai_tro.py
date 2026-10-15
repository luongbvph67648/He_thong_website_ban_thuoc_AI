"""AD18: vai trò và phân quyền (/api/v1/noi-bo/vai-tro)."""

import asyncio

import pytest
import yaml
from sqlalchemy import func, select

from app.core import phan_quyen
from app.core.danh_muc_quyen import QUYEN_YAML
from app.core.loi import LoiNghiepVu
from app.models.enums import TrangThaiTaiKhoan
from app.models.he_thong import NhanVien, NhatKyHeThong, Quyen, VaiTro, VaiTroQuyen
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


async def dat_quyen(admin, ma, quyen, *, phien_ban=None):
    """PUT như giao diện: gửi kèm `phien_ban` vừa đọc (khóa lạc quan), trừ khi test chủ động truyền bản khác."""
    if phien_ban is None:
        phien_ban = (await admin.get(f"{GOC}/{ma}")).json()["phien_ban"]
    return await admin.put(f"{GOC}/{ma}/quyen", json={"quyen": quyen, "phien_ban": phien_ban})


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
        await dang_nhap_admin.put(
            f"{GOC}/{ma}/quyen", json={"quyen": {"profile.self": "day_du"}, "phien_ban": "0" * 16}
        )
    ).status_code == trang_thai


# --- Cập nhật quyền -------------------------------------------------------------------------------------------------


async def test_gan_bo_va_doi_muc_quyen_co_hieu_luc_ngay_cho_nhan_vien_dang_dung(dang_nhap_admin, clients_theo_vai_tro):
    duoc_si = clients_theo_vai_tro["PHARMACIST"]
    truoc = (await duoc_si.get(URL_TOI)).json()["quyen"]  # nạp cache quyền của vai trò
    assert "pos.sell" in truoc and "stock.import" not in truoc and truoc["stock.view"] == "chi_xem"

    moi = {k: v for k, v in (await quyen_hien_tai(dang_nhap_admin)).items() if k != "pos.sell"}
    moi["stock.import"] = "chi_xem"  # gán mới
    moi["stock.view"] = "day_du"  # đổi mức
    phan_hoi = await dat_quyen(dang_nhap_admin, "PHARMACIST", moi)
    assert phan_hoi.status_code == 200 and hien_co(phan_hoi.json()) == moi

    sau = (await duoc_si.get(URL_TOI)).json()["quyen"]  # cache đã bị xóa: thấy ngay
    assert sau == moi and "pos.sell" not in sau


async def test_nhat_ky_ghi_phan_chenh_lech_theo_dang_danh_sach(dang_nhap_admin, db):
    moi = {k: v for k, v in (await quyen_hien_tai(dang_nhap_admin, "WAREHOUSE")).items() if k != "order.pick"}
    moi["return.review"] = "chi_xem"
    moi["stock.view"] = "chi_xem"  # kho đang day_du -> chi_xem
    assert (await dat_quyen(dang_nhap_admin, "WAREHOUSE", moi)).status_code == 200
    (dong,) = await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "sua")
    assert (dong.bang, dong.ban_ghi_id) == ("vai_tro_quyen", "WAREHOUSE")
    assert dong.gia_tri_moi == {"them": ["return.review:chi_xem"]}
    assert dong.gia_tri_cu == {"bo": ["order.pick:day_du"], "doi_muc": ["stock.view:day_du->chi_xem"]}


async def test_dat_dung_nhu_hien_tai_thi_khong_ghi_nhat_ky(dang_nhap_admin, db):
    hien = await quyen_hien_tai(dang_nhap_admin)
    assert (await dat_quyen(dang_nhap_admin, "PHARMACIST", hien)).status_code == 200
    assert await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "sua") == []


async def test_vai_tro_admin_khong_sua_duoc_du_chi_la_gui_lai_y_nguyen(dang_nhap_admin, db):
    truoc = await quyen_hien_tai(dang_nhap_admin, "ADMIN")
    for quyen in (
        truoc,  # y nguyên
        {"profile.self": "day_du"},  # bỏ gần hết
        {**truoc, "order.confirm": "day_du"},  # thêm quyền thao tác đơn
    ):
        phan_hoi = await dat_quyen(dang_nhap_admin, "ADMIN", quyen)
        assert la_loi(phan_hoi, 409, "PHAI_CON_ADMIN")
    assert await quyen_hien_tai(dang_nhap_admin, "ADMIN") == truoc == quyen_theo_yaml("ADMIN")
    assert await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "sua") == []


async def test_ma_quyen_khong_ton_tai_va_muc_khong_hop_le_tra_400_va_khong_doi_gi(dang_nhap_admin, db):
    truoc = await quyen_hien_tai(dang_nhap_admin)
    phan_hoi = await dat_quyen(dang_nhap_admin, "PHARMACIST", {**truoc, "quyen.khong.co": "day_du"})
    assert phan_hoi.status_code == 400
    assert phan_hoi.json()["chi_tiet"] == [{"truong": "quyen.quyen.khong.co", "loi": "Mã quyền không tồn tại"}]
    sai_muc = await dat_quyen(dang_nhap_admin, "PHARMACIST", {**truoc, "order.view": "toan_quyen"})
    assert sai_muc.status_code == 400
    assert await quyen_hien_tai(dang_nhap_admin) == truoc
    assert await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "sua") == []


@pytest.mark.parametrize("quyen_profile", [None, "chi_xem"])
async def test_profile_self_bat_buoc_o_muc_day_du(dang_nhap_admin, quyen_profile):
    """Gỡ hoặc hạ `profile.self` làm nhân viên không đổi được mật khẩu bắt buộc: bị chặn."""
    moi = {k: v for k, v in (await quyen_hien_tai(dang_nhap_admin, "WAREHOUSE")).items() if k != "profile.self"}
    if quyen_profile:
        moi["profile.self"] = quyen_profile
    phan_hoi = await dat_quyen(dang_nhap_admin, "WAREHOUSE", moi)
    assert phan_hoi.status_code == 400
    assert phan_hoi.json()["chi_tiet"][0]["truong"] == "quyen.profile.self"
    assert (await quyen_hien_tai(dang_nhap_admin, "WAREHOUSE"))["profile.self"] == "day_du"


@pytest.mark.parametrize("ma_quyen", ["content.professional.edit", "content.approve"])
async def test_quyen_noi_dung_chuyen_mon_chi_cap_duoc_cho_duoc_si(dang_nhap_admin, ma_quyen):
    """Spec 03 mục 7: Admin không sửa nội dung chuyên môn, quyền này chỉ PHARMACIST có."""
    kho = {**(await quyen_hien_tai(dang_nhap_admin, "WAREHOUSE")), ma_quyen: "day_du"}
    phan_hoi = await dat_quyen(dang_nhap_admin, "WAREHOUSE", kho)
    assert phan_hoi.status_code == 400 and "PHARMACIST" in phan_hoi.json()["chi_tiet"][0]["loi"]
    assert ma_quyen not in await quyen_hien_tai(dang_nhap_admin, "WAREHOUSE")
    duoc_si = {**(await quyen_hien_tai(dang_nhap_admin, "PHARMACIST")), ma_quyen: "chi_xem"}
    assert (await dat_quyen(dang_nhap_admin, "PHARMACIST", duoc_si)).status_code == 200


async def test_loi_nhieu_cho_cung_luc_tra_het_trong_mot_lan(dang_nhap_admin):
    phan_hoi = await dat_quyen(dang_nhap_admin, "WAREHOUSE", {"khong.co": "day_du", "content.approve": "day_du"})
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


async def test_hai_admin_sua_cung_vai_tro_cung_luc_dung_mot_ben_thanh_cong_ben_kia_nhan_409(db_that):
    """Cùng đọc một `phien_ban` rồi cùng lưu: khóa dòng vai trò làm hai bên tuần tự, bên đến sau thấy bản đã đổi."""
    async with db_that() as s, s.begin():
        admin_id = (await tao_nhan_vien(s, "ADMIN")).id
        goc = await service.chi_tiet(s, "WAREHOUSE")
    hien = hien_co(goc.model_dump())
    muon_a = {**hien, "stock.view": "chi_xem", "forecast.view": "chi_xem"}
    muon_b = {**hien, "report.inventory": "chi_xem"}

    async def sua(muon):
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, admin_id)
            await service.cap_nhat_quyen(s, actor, "WAREHOUSE", muon, goc.phien_ban, ip="127.0.0.1")
            await asyncio.sleep(0.3)  # giữ giao dịch mở để bên kia phải chờ khóa dòng vai trò

    ket_qua = await asyncio.wait_for(asyncio.gather(sua(muon_a), sua(muon_b), return_exceptions=True), timeout=20)
    thanh_cong = [k for k in ket_qua if k is None]
    that_bai = [k for k in ket_qua if k is not None]
    assert len(thanh_cong) == 1 and len(that_bai) == 1, ket_qua  # không có IntegrityError hay deadlock
    assert isinstance(that_bai[0], LoiNghiepVu) and that_bai[0].ma_loi == "DU_LIEU_DA_THAY_DOI"
    async with db_that() as s:
        cuoi = hien_co((await service.chi_tiet(s, "WAREHOUSE")).model_dump())
    assert cuoi == (muon_a if ket_qua[0] is None else muon_b)  # đúng bằng yêu cầu của bên thắng, không trộn lẫn


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
        phien_ban = (await service.chi_tiet(s, "WAREHOUSE")).phien_ban
        await service.cap_nhat_quyen(s, actor, "WAREHOUSE", moi, phien_ban, ip="127.0.0.1")  # đã xóa cache, CHƯA commit
        async with db_that() as khac:  # request khác đọc dữ liệu ĐÃ commit (bản cũ) và cache lại
            assert "order.pick" in await phan_quyen.quyen_cua_vai_tro(khac, kho_id)
    # Sau commit của service: cache phải bị xóa lần nữa, nếu không bản cũ sống thêm 60 giây.
    async with db_that() as s:
        assert "order.pick" not in await phan_quyen.quyen_cua_vai_tro(s, kho_id)


# --- Quyền quản trị chỉ ADMIN (rà soát T1.4: M1, M2) ----------------------------------------------------------------


def quyen_chi_admin_theo_yaml() -> list[str]:
    """Mã quyền mà ma trận spec 03 chỉ cấp cho ADMIN, đọc độc lập với code (không dùng helper của ứng dụng)."""
    du_lieu = yaml.safe_load(QUYEN_YAML.read_text(encoding="utf-8"))
    return sorted(q["ma"] for q in du_lieu["quyen"] if set(q["vai_tro"]) == {"ADMIN"})


def test_danh_sach_quyen_chi_admin_co_du_cac_quyen_nhay_cam():
    chi_admin = quyen_chi_admin_theo_yaml()
    assert len(chi_admin) == 18
    # Hai nhóm bắt buộc: quyền quản trị tài khoản/phân quyền (leo thang đặc quyền) và quyền duyệt (tách nhiệm vụ).
    assert {"staff.manage", "role.manage", "stock_doc.approve", "refund.confirm", "audit.view"} <= set(chi_admin)


@pytest.mark.parametrize("vai_tro", ["PHARMACIST", "WAREHOUSE"])
@pytest.mark.parametrize("ma_quyen", quyen_chi_admin_theo_yaml())
async def test_quyen_chi_admin_khong_gan_duoc_cho_vai_tro_khac(dang_nhap_admin, db, vai_tro, ma_quyen):
    """`staff.manage`/`role.manage` mà gán được thì người nhận tự tạo Admin hay tự cấp thêm quyền; `refund.confirm`,
    `stock_doc.approve` mà gán được thì một người vừa lập vừa duyệt (tách nhiệm vụ, CLAUDE.md quy tắc 8)."""
    truoc = await quyen_hien_tai(dang_nhap_admin, vai_tro)
    for muc in ("chi_xem", "day_du"):
        phan_hoi = await dat_quyen(dang_nhap_admin, vai_tro, {**truoc, ma_quyen: muc})
        assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE")
        assert phan_hoi.json()["chi_tiet"] == [
            {"truong": f"quyen.{ma_quyen}", "loi": "Quyền này chỉ dành cho vai trò ADMIN"}
        ]
    assert await quyen_hien_tai(dang_nhap_admin, vai_tro) == truoc
    assert await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "sua") == []


async def test_chi_tiet_danh_dau_quyen_chi_admin_va_quyen_chuyen_mon(dang_nhap_admin):
    theo_quyen = {q["ma"]: q for q in (await dang_nhap_admin.get(f"{GOC}/WAREHOUSE")).json()["quyen"]}
    for ma_quyen in quyen_chi_admin_theo_yaml():
        assert theo_quyen[ma_quyen]["chi_cho_vai_tro"] == "ADMIN" and theo_quyen[ma_quyen]["muc"] is None
    assert theo_quyen["content.approve"]["chi_cho_vai_tro"] == "PHARMACIST"
    assert theo_quyen["order.view"]["chi_cho_vai_tro"] is None


async def test_vai_tro_da_co_quyen_chi_admin_trong_csdl_bi_go_khi_luu_lai(dang_nhap_admin, db):
    """Dữ liệu cấu hình sai từ trước (gán ngoài AD18): gửi bản không có quyền đó thì gỡ được, không bị kẹt."""
    quyen_id = (await db.execute(select(Quyen.id).where(Quyen.ma == "refund.confirm"))).scalar_one()
    vai_tro_id = (await db.execute(select(VaiTro.id).where(VaiTro.ma == "PHARMACIST"))).scalar_one()
    db.add(VaiTroQuyen(vai_tro_id=vai_tro_id, quyen_id=quyen_id, gioi_han=None))
    await db.flush()
    phan_quyen.xoa_cache_quyen()
    hien = await quyen_hien_tai(dang_nhap_admin)
    assert hien["refund.confirm"] == "day_du"
    phan_hoi = await dat_quyen(dang_nhap_admin, "PHARMACIST", {k: v for k, v in hien.items() if k != "refund.confirm"})
    assert phan_hoi.status_code == 200 and "refund.confirm" not in hien_co(phan_hoi.json())


@pytest.mark.parametrize("ma_quyen", ["staff.manage", "role.manage"])
async def test_quyen_quan_tri_cap_ngoai_ad18_van_khong_cho_phep_thao_tac_ghi(
    dang_nhap_admin, clients_theo_vai_tro, db, ma_quyen
):
    """Lớp phòng thủ thứ hai: dù cấu hình sai khiến dược sĩ giữ `staff.manage`/`role.manage` ở mức đầy đủ (gán thẳng
    vào DB, không qua AD18), mọi thao tác ghi của AD01 và AD18 vẫn đòi người thực hiện là ADMIN."""
    duoc_si = clients_theo_vai_tro["PHARMACIST"]
    quyen_id = (await db.execute(select(Quyen.id).where(Quyen.ma == ma_quyen))).scalar_one()
    vai_tro_id = (await db.execute(select(VaiTro.id).where(VaiTro.ma == "PHARMACIST"))).scalar_one()
    db.add(VaiTroQuyen(vai_tro_id=vai_tro_id, quyen_id=quyen_id, gioi_han=None))
    await db.flush()
    phan_quyen.xoa_cache_quyen()
    assert ma_quyen in (await duoc_si.get(URL_TOI)).json()["quyen"]  # cấu hình sai đã có hiệu lực ở lớp guard

    kho = await tao_nhan_vien(db, "WAREHOUSE")
    admin = dang_nhap_admin.tai_khoan
    so_nv = len((await db.execute(select(NhanVien.id))).all())
    so_nhat_ky = (await db.execute(select(func.count()).select_from(NhatKyHeThong))).scalar_one()
    phien_ban = (await dang_nhap_admin.get(f"{GOC}/WAREHOUSE")).json()["phien_ban"]
    cac_loi_goi = [
        duoc_si.post("/api/v1/noi-bo/nhan-vien", json={"ho_ten": "X", "email": "x@example.com", "vai_tro": "ADMIN"}),
        duoc_si.patch(f"/api/v1/noi-bo/nhan-vien/{kho.id}", json={"vai_tro": "ADMIN"}),
        duoc_si.post(f"/api/v1/noi-bo/nhan-vien/{admin.id}/khoa"),
        duoc_si.post(f"/api/v1/noi-bo/nhan-vien/{admin.id}/mo-khoa"),
        duoc_si.post(f"/api/v1/noi-bo/nhan-vien/{admin.id}/dat-lai-mat-khau"),
        duoc_si.delete(f"/api/v1/noi-bo/nhan-vien/{kho.id}"),
        duoc_si.put(
            f"{GOC}/WAREHOUSE/quyen",
            json={"quyen": {"profile.self": "day_du", "order.pick": "day_du"}, "phien_ban": phien_ban},
        ),
    ]
    for cuoc_goi in cac_loi_goi:
        assert la_loi(await cuoc_goi, 403, "KHONG_CO_QUYEN")
    assert len((await db.execute(select(NhanVien.id))).all()) == so_nv  # không tạo thêm ai
    assert (await db.get(NhanVien, admin.id)).trang_thai == TrangThaiTaiKhoan.hoat_dong
    assert (await db.get(NhanVien, kho.id)).deleted_at is None
    assert (await db.get(NhanVien, kho.id)).vai_tro_id != vai_tro_id
    assert (await db.execute(select(func.count()).select_from(NhatKyHeThong))).scalar_one() == so_nhat_ky
    # Đọc vẫn đi qua guard theo mã quyền (chỉ xem là đủ cho GET), không bị chặn oan.
    assert (await duoc_si.get("/api/v1/noi-bo/nhan-vien")).status_code == (200 if ma_quyen == "staff.manage" else 403)


# --- Khóa lạc quan `phien_ban` (rà soát T1.4: M3) --------------------------------------------------------------------


async def test_chi_tiet_co_phien_ban_doi_khi_quyen_doi_va_khong_doi_khi_khong_doi(dang_nhap_admin):
    a = (await dang_nhap_admin.get(f"{GOC}/WAREHOUSE")).json()["phien_ban"]
    assert (await dang_nhap_admin.get(f"{GOC}/WAREHOUSE")).json()["phien_ban"] == a
    assert (await dang_nhap_admin.get(f"{GOC}/PHARMACIST")).json()["phien_ban"] != a  # vai trò khác, quyền khác
    hien = await quyen_hien_tai(dang_nhap_admin, "WAREHOUSE")
    assert (await dat_quyen(dang_nhap_admin, "WAREHOUSE", hien)).json()["phien_ban"] == a  # không đổi gì
    moi = (await dat_quyen(dang_nhap_admin, "WAREHOUSE", {**hien, "report.shift": "chi_xem"})).json()["phien_ban"]
    assert moi != a
    ve_lai = (await dat_quyen(dang_nhap_admin, "WAREHOUSE", hien)).json()["phien_ban"]
    assert ve_lai == a  # phiên bản chỉ phụ thuộc nội dung quyền, không phụ thuộc số lần lưu


async def test_trang_cu_khong_the_khoi_phuc_quyen_vua_bi_admin_khac_thu_hoi(dang_nhap_admin, db):
    """Admin A mở ma trận, Admin B gỡ quyền X, A bật thêm quyền Y rồi lưu với bản cũ: bị từ chối, X KHÔNG quay lại."""
    hien = await quyen_hien_tai(dang_nhap_admin, "WAREHOUSE")
    ban_cu = (await dang_nhap_admin.get(f"{GOC}/WAREHOUSE")).json()["phien_ban"]  # A đọc lúc này
    assert (
        await dat_quyen(dang_nhap_admin, "WAREHOUSE", {k: v for k, v in hien.items() if k != "order.pick"})
    ).status_code == 200  # B
    cua_a = {**hien, "report.shift": "chi_xem"}  # A vẫn thấy order.pick
    phan_hoi = await dat_quyen(dang_nhap_admin, "WAREHOUSE", cua_a, phien_ban=ban_cu)
    assert la_loi(phan_hoi, 409, "DU_LIEU_DA_THAY_DOI")
    sau = await quyen_hien_tai(dang_nhap_admin, "WAREHOUSE")
    assert "order.pick" not in sau and "report.shift" not in sau  # không có gì của A được áp dụng
    (dong,) = await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "sua")  # chỉ lần lưu của B
    assert dong.gia_tri_cu == {"bo": ["order.pick:day_du"], "doi_muc": []}


@pytest.mark.parametrize("phien_ban", [None, "", "x" * 16, "0" * 15, "G" * 16])
async def test_phien_ban_thieu_hoac_sai_dinh_dang_la_400(dang_nhap_admin, phien_ban):
    than = {"quyen": await quyen_hien_tai(dang_nhap_admin, "WAREHOUSE")}
    if phien_ban is not None:
        than["phien_ban"] = phien_ban
    phan_hoi = await dang_nhap_admin.put(f"{GOC}/WAREHOUSE/quyen", json=than)
    assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE")


async def test_admin_van_nhan_409_phai_con_admin_truoc_khi_xet_phien_ban(dang_nhap_admin):
    phan_hoi = await dat_quyen(dang_nhap_admin, "ADMIN", {"profile.self": "day_du"}, phien_ban="0" * 16)
    assert la_loi(phan_hoi, 409, "PHAI_CON_ADMIN")

"""AD04: ảnh sản phẩm (POST/PUT/DELETE /san-pham/{id}/anh) và phục vụ file công khai (GET /tep/...)."""

import asyncio
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.models.he_thong import NhanVien
from app.models.san_pham import AnhSanPham
from app.modules.san_pham import san_pham as dich_vu
from app.modules.san_pham import san_pham_anh
from app.modules.san_pham.schemas_san_pham import SanPhamTao
from tests.factories import tao_danh_muc, tao_nhan_vien
from tests.nhan_vien.dung_chung import nhat_ky
from tests.san_pham.mau_san_pham import ANH_JPEG, ANH_PNG, ANH_WEBP, GOC, doc_sp, la_loi, tai_anh, tao_sp, than_tao


def thu_muc_luu() -> Path:
    return Path(settings.LUU_TRU_THU_MUC) / "cong_khai"


def cac_tep() -> list[Path]:
    return sorted(p for p in thu_muc_luu().rglob("*") if p.is_file())


async def sp_moi(admin, db) -> dict:
    return await tao_sp(admin, (await tao_danh_muc(db, "A")).id)


async def tai_nhieu(admin, sp: dict, so_luong: int) -> dict:
    for i in range(so_luong):
        phan_hoi = await tai_anh(admin, sp, ANH_JPEG + bytes([i]), f"{i}.jpg")
        assert phan_hoi.status_code == 201, phan_hoi.text
        sp = phan_hoi.json()
    return sp


# --- Upload --------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("noi_dung", "ten", "kieu", "duoi"),
    [
        (ANH_JPEG, "a.jpg", "image/jpeg", ".jpg"),
        (ANH_PNG, "a.png", "image/png", ".png"),
        (ANH_WEBP, "a.webp", "image/webp", ".webp"),
    ],
)
async def test_tai_anh_hop_le_luu_file_uuid_theo_noi_dung_that_va_ghi_nhat_ky(
    dang_nhap_admin, db, noi_dung, ten, kieu, duoi
):
    sp = await sp_moi(dang_nhap_admin, db)
    # Tên file và Content-Type do client nói đều bị bỏ qua: đuôi lấy theo nội dung thật.
    phan_hoi = await tai_anh(dang_nhap_admin, sp, noi_dung, "ten-do-client.gif", "image/gif")
    assert phan_hoi.status_code == 201, phan_hoi.text
    moi = phan_hoi.json()
    anh = moi["anh"][0]
    assert anh["url"].startswith("/api/v1/tep/san-pham/") and anh["url"].endswith(duoi)
    assert "ten-do-client" not in anh["url"] and anh["la_anh_chinh"] is True and anh["thu_tu"] == 0
    assert moi["phien_ban"] != sp["phien_ban"]
    assert [p.suffix for p in cac_tep()] == [duoi] and cac_tep()[0].read_bytes() == noi_dung
    ghi = [g for g in await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "tao") if g.bang == "anh_san_pham"]
    assert len(ghi) == 1 and ghi[0].gia_tri_moi["url"] == anh["url"]


@pytest.mark.parametrize(
    ("noi_dung", "ten", "kieu"),
    [
        (b"<?php echo 1; ?>", "shell.jpg", "image/jpeg"),  # đuôi và kiểu nói là ảnh nhưng nội dung thì không
        (b"GIF89a" + b"x" * 50, "a.gif", "image/gif"),
        (b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>", "a.svg", "image/svg+xml"),
        (b"MZ" + b"\x00" * 100, "a.exe", "application/octet-stream"),
        (b"%PDF-1.4 ...", "a.pdf", "application/pdf"),
        (b"RIFF\x00\x00\x00\x00WAVE", "a.webp", "image/webp"),  # RIFF nhưng không phải WEBP
        (b"\xff\xd8", "a.jpg", "image/jpeg"),  # ngắn hơn magic bytes của JPEG (3 byte)
    ],
)
async def test_file_khong_phai_anh_theo_noi_dung_la_400_va_khong_ghi_file(dang_nhap_admin, db, noi_dung, ten, kieu):
    sp = await sp_moi(dang_nhap_admin, db)
    phan_hoi = await tai_anh(dang_nhap_admin, sp, noi_dung, ten, kieu)
    assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE") and phan_hoi.json()["chi_tiet"][0]["truong"] == "tep"
    assert cac_tep() == [] and (await doc_sp(dang_nhap_admin, sp["id"]))["anh"] == []


async def test_file_rong_hoac_thieu_truong_tep_la_400(dang_nhap_admin, db):
    sp = await sp_moi(dang_nhap_admin, db)
    rong = await tai_anh(dang_nhap_admin, sp, b"", "a.jpg")
    assert la_loi(rong, 400, "DU_LIEU_KHONG_HOP_LE")
    thieu = await dang_nhap_admin.post(
        f"{GOC}/{sp['id']}/anh",
        params={"phien_ban": sp["phien_ban"]},
        files={"khac": ("a.jpg", ANH_JPEG, "image/jpeg")},
    )
    assert la_loi(thieu, 400, "DU_LIEU_KHONG_HOP_LE")
    khong_phai_multipart = await dang_nhap_admin.post(
        f"{GOC}/{sp['id']}/anh", params={"phien_ban": sp["phien_ban"]}, json={"tep": "x"}
    )
    assert la_loi(khong_phai_multipart, 400, "DU_LIEU_KHONG_HOP_LE")
    assert cac_tep() == []


async def test_anh_qua_5mb_la_413_va_dung_5mb_thi_duoc(dang_nhap_admin, db):
    sp = await sp_moi(dang_nhap_admin, db)
    qua_lon = await tai_anh(dang_nhap_admin, sp, ANH_JPEG + b"0" * (5 * 1024 * 1024), "lon.jpg")
    assert la_loi(qua_lon, 413, "TEP_QUA_LON") and cac_tep() == []
    vua_du = await tai_anh(dang_nhap_admin, sp, ANH_JPEG + b"0" * (5 * 1024 * 1024 - len(ANH_JPEG)), "vua.jpg")
    assert vua_du.status_code == 201, vua_du.text[:200]


async def test_toi_da_20_anh_moi_san_pham(dang_nhap_admin, db):
    sp = await tai_nhieu(dang_nhap_admin, await sp_moi(dang_nhap_admin, db), 20)
    assert len(sp["anh"]) == 20
    them = await tai_anh(dang_nhap_admin, sp, ANH_PNG, "hai-muoi-mot.png", "image/png")
    assert la_loi(them, 400, "DU_LIEU_KHONG_HOP_LE") and len(cac_tep()) == 20  # ảnh thứ 21 không để lại file mồ côi


async def test_anh_dau_tien_la_anh_chinh_cac_anh_sau_thu_tu_tang_dan(dang_nhap_admin, db):
    sp = await tai_nhieu(dang_nhap_admin, await sp_moi(dang_nhap_admin, db), 3)
    assert [(a["thu_tu"], a["la_anh_chinh"]) for a in sp["anh"]] == [(0, True), (1, False), (2, False)]
    lst = (await dang_nhap_admin.get(GOC)).json()["du_lieu"][0]
    assert lst["anh_chinh_url"] == sp["anh"][0]["url"]


async def test_tai_anh_phien_ban_cu_la_409_va_khong_ghi_file(dang_nhap_admin, db):
    sp = await sp_moi(dang_nhap_admin, db)
    dau = await tai_anh(dang_nhap_admin, sp, ANH_JPEG, "a.jpg")
    assert dau.status_code == 201
    cu = await tai_anh(dang_nhap_admin, sp, ANH_PNG, "b.png", "image/png")  # dựa trên bản trước khi có ảnh
    assert la_loi(cu, 409, "DU_LIEU_DA_THAY_DOI") and len(cac_tep()) == 1
    thieu = await dang_nhap_admin.post(f"{GOC}/{sp['id']}/anh", files={"tep": ("a.jpg", ANH_JPEG, "image/jpeg")})
    assert la_loi(thieu, 400, "DU_LIEU_KHONG_HOP_LE")


async def test_giao_dich_bi_huy_sau_khi_ghi_file_thi_file_mo_coi_duoc_don(db_that):
    async with db_that() as s, s.begin():
        admin_id = (await tao_nhan_vien(s, "ADMIN")).id
        dm = await tao_danh_muc(s, "A")
        actor = await s.get(NhanVien, admin_id)
        sp = await dich_vu.tao(s, actor, SanPhamTao.model_validate(than_tao(dm.id)), ip="127.0.0.1")
        sp_id, phien_ban = sp.id, sp.phien_ban
    with pytest.raises(RuntimeError, match="hủy"):
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, admin_id)
            await san_pham_anh.them_anh(s, actor, sp_id, phien_ban, ANH_JPEG, ip="127.0.0.1")
            assert len(cac_tep()) == 1  # file đã ghi trước khi giao dịch xong
            raise RuntimeError("hủy giao dịch")
    assert cac_tep() == []
    async with db_that() as s:
        assert (await s.execute(select(func.count()).select_from(AnhSanPham))).scalar_one() == 0


# --- Ảnh chính, thứ tự, xóa ------------------------------------------------------------------------------------------------


async def test_dat_anh_chinh_dung_mot_anh_chinh_va_dat_lai_chinh_no_thi_khong_doi(dang_nhap_admin, db):
    sp = await tai_nhieu(dang_nhap_admin, await sp_moi(dang_nhap_admin, db), 3)
    anh_2 = sp["anh"][2]["id"]
    phan_hoi = await dang_nhap_admin.put(f"{GOC}/{sp['id']}/anh/{anh_2}/chinh", json={"phien_ban": sp["phien_ban"]})
    assert phan_hoi.status_code == 200, phan_hoi.text
    moi = phan_hoi.json()
    assert [a["id"] for a in moi["anh"] if a["la_anh_chinh"]] == [anh_2]
    assert [a["id"] for a in moi["anh"]] == [a["id"] for a in sp["anh"]]  # đặt ảnh chính không đổi thứ tự
    truoc = len(await nhat_ky(db, dang_nhap_admin.tai_khoan.id))
    lai = await dang_nhap_admin.put(f"{GOC}/{sp['id']}/anh/{anh_2}/chinh", json={"phien_ban": moi["phien_ban"]})
    assert lai.status_code == 200 and lai.json()["phien_ban"] == moi["phien_ban"]
    assert len(await nhat_ky(db, dang_nhap_admin.tai_khoan.id)) == truoc


async def test_dat_anh_chinh_anh_cua_san_pham_khac_hoac_khong_co_la_404(dang_nhap_admin, db):
    a = await tai_nhieu(dang_nhap_admin, await sp_moi(dang_nhap_admin, db), 1)
    b = await tai_nhieu(dang_nhap_admin, await tao_sp(dang_nhap_admin, (await tao_danh_muc(db, "B")).id), 1)
    for anh_id in (b["anh"][0]["id"], 2_000_000_000):
        phan_hoi = await dang_nhap_admin.put(f"{GOC}/{a['id']}/anh/{anh_id}/chinh", json={"phien_ban": a["phien_ban"]})
        assert la_loi(phan_hoi, 404, "KHONG_TIM_THAY")
        xoa = await dang_nhap_admin.delete(f"{GOC}/{a['id']}/anh/{anh_id}", params={"phien_ban": a["phien_ban"]})
        assert la_loi(xoa, 404, "KHONG_TIM_THAY")
    assert len(cac_tep()) == 2  # file của sản phẩm kia không bị đụng tới


async def test_sap_xep_anh_phai_dung_va_du_cac_anh_hien_co(dang_nhap_admin, db):
    sp = await tai_nhieu(dang_nhap_admin, await sp_moi(dang_nhap_admin, db), 3)
    ids = [a["id"] for a in sp["anh"]]
    phan_hoi = await dang_nhap_admin.put(
        f"{GOC}/{sp['id']}/anh/thu-tu", json={"phien_ban": sp["phien_ban"], "ids": [ids[2], ids[0], ids[1]]}
    )
    assert phan_hoi.status_code == 200, phan_hoi.text
    assert [(a["id"], a["thu_tu"]) for a in phan_hoi.json()["anh"]] == [(ids[2], 0), (ids[0], 1), (ids[1], 2)]
    assert [a["id"] for a in phan_hoi.json()["anh"] if a["la_anh_chinh"]] == [ids[0]]  # ảnh chính giữ nguyên
    moi = phan_hoi.json()
    for sai in ([ids[0]], [ids[0], ids[0], ids[1]], [*ids, 999_999], [], [ids[0], ids[1], 999_999]):
        loi = await dang_nhap_admin.put(
            f"{GOC}/{sp['id']}/anh/thu-tu", json={"phien_ban": moi["phien_ban"], "ids": sai}
        )
        assert la_loi(loi, 400, "DU_LIEU_KHONG_HOP_LE"), sai
    truoc = len(await nhat_ky(db, dang_nhap_admin.tai_khoan.id))
    giu = await dang_nhap_admin.put(
        f"{GOC}/{sp['id']}/anh/thu-tu", json={"phien_ban": moi["phien_ban"], "ids": [a["id"] for a in moi["anh"]]}
    )
    assert giu.status_code == 200 and giu.json()["phien_ban"] == moi["phien_ban"]
    assert len(await nhat_ky(db, dang_nhap_admin.tai_khoan.id)) == truoc


async def test_xoa_anh_chinh_thi_anh_dau_danh_sach_thanh_chinh_thu_tu_lien_tuc_va_file_bi_xoa(db_that):
    async with db_that() as s, s.begin():
        admin_id = (await tao_nhan_vien(s, "ADMIN")).id
        dm = await tao_danh_muc(s, "A")
        actor = await s.get(NhanVien, admin_id)
        sp = await dich_vu.tao(s, actor, SanPhamTao.model_validate(than_tao(dm.id)), ip="127.0.0.1")
    for i in range(3):
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, admin_id)
            hien_tai = await dich_vu.lay(s, sp.id)
            sp = await san_pham_anh.them_anh(s, actor, sp.id, hien_tai.phien_ban, ANH_JPEG + bytes([i]), ip="127.0.0.1")
    assert len(cac_tep()) == 3
    anh_chinh = next(a for a in sp.anh if a.la_anh_chinh)
    async with db_that() as s, s.begin():
        actor = await s.get(NhanVien, admin_id)
        sau = await san_pham_anh.xoa_anh(s, actor, sp.id, anh_chinh.id, sp.phien_ban, ip="127.0.0.1")
        assert len(cac_tep()) == 3  # file chỉ bị xóa SAU khi giao dịch commit
    assert [(a.thu_tu, a.la_anh_chinh) for a in sau.anh] == [(0, True), (1, False)]
    assert anh_chinh.id not in [a.id for a in sau.anh]
    assert len(cac_tep()) == 2


async def test_xoa_anh_bi_huy_giao_dich_thi_file_con_nguyen(db_that):
    async with db_that() as s, s.begin():
        admin_id = (await tao_nhan_vien(s, "ADMIN")).id
        dm = await tao_danh_muc(s, "A")
        actor = await s.get(NhanVien, admin_id)
        sp = await dich_vu.tao(s, actor, SanPhamTao.model_validate(than_tao(dm.id)), ip="127.0.0.1")
        sp = await san_pham_anh.them_anh(s, actor, sp.id, sp.phien_ban, ANH_PNG, ip="127.0.0.1")
    with pytest.raises(RuntimeError):
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, admin_id)
            await san_pham_anh.xoa_anh(s, actor, sp.id, sp.anh[0].id, sp.phien_ban, ip="127.0.0.1")
            raise RuntimeError("hủy")
    assert len(cac_tep()) == 1
    async with db_that() as s:
        assert (await s.execute(select(func.count()).select_from(AnhSanPham))).scalar_one() == 1


async def test_xoa_anh_cuoi_cung_va_phien_ban_cu(dang_nhap_admin, db):
    sp = await tai_nhieu(dang_nhap_admin, await sp_moi(dang_nhap_admin, db), 1)
    cu = await dang_nhap_admin.delete(f"{GOC}/{sp['id']}/anh/{sp['anh'][0]['id']}", params={"phien_ban": "0" * 16})
    assert la_loi(cu, 409, "DU_LIEU_DA_THAY_DOI")
    xoa = await dang_nhap_admin.delete(
        f"{GOC}/{sp['id']}/anh/{sp['anh'][0]['id']}", params={"phien_ban": sp["phien_ban"]}
    )
    assert xoa.status_code == 200 and xoa.json()["anh"] == []
    ghi = [g for g in await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "xoa") if g.bang == "anh_san_pham"]
    assert len(ghi) == 1


# --- Phục vụ file công khai ---------------------------------------------------------------------------------------------


async def test_file_cong_khai_tai_ve_khong_can_dang_nhap_voi_header_an_toan(dang_nhap_admin, client, db):
    sp = await sp_moi(dang_nhap_admin, db)
    url = (await tai_anh(dang_nhap_admin, sp, ANH_PNG, "x.png", "image/png")).json()["anh"][0]["url"]
    phan_hoi = await client.get(url)  # client KHÔNG đăng nhập
    assert phan_hoi.status_code == 200 and phan_hoi.content == ANH_PNG
    assert phan_hoi.headers["content-type"] == "image/png"
    assert phan_hoi.headers["x-content-type-options"] == "nosniff"
    assert "immutable" in phan_hoi.headers["cache-control"] and "max-age=31536000" in phan_hoi.headers["cache-control"]


@pytest.mark.parametrize(
    "duong",
    [
        "/api/v1/tep/san-pham/khong-co.jpg",
        "/api/v1/tep/san-pham/..%2F..%2Fetc%2Fpasswd",
        "/api/v1/tep/san-pham/%2e%2e/%2e%2e/cong_khai/x.jpg",
        "/api/v1/tep/..%2Fx/a.jpg",
        "/api/v1/tep/san-pham/a.jpg%00.png",
        "/api/v1/tep/san-pham/a.php",
        "/api/v1/tep/san-pham/A.JPG",  # khóa chỉ gồm chữ thường
        "/api/v1/tep/san-pham/.jpg",
        "/api/v1/tep/%2Fetc/passwd",
        "/api/v1/tep/san-pham",
        "/api/v1/tep/",
    ],
)
async def test_khoa_file_la_hoac_khong_ton_tai_la_404_khong_doc_ra_ngoai_thu_muc_luu_tru(client, duong):
    phan_hoi = await client.get(duong)
    assert phan_hoi.status_code == 404, (duong, phan_hoi.status_code)


async def test_khong_phuc_vu_file_ngoai_vung_cong_khai_du_ton_tai_tren_dia(client):
    rieng_tu = Path(settings.LUU_TRU_THU_MUC) / "rieng_tu" / "san-pham"
    rieng_tu.mkdir(parents=True)
    (rieng_tu / "bi-mat.jpg").write_bytes(ANH_JPEG)
    assert (await client.get("/api/v1/tep/san-pham/bi-mat.jpg")).status_code == 404
    assert (await client.get("/api/v1/tep/rieng_tu/bi-mat.jpg")).status_code == 404  # `_` không nằm trong khóa hợp lệ


async def test_hai_lan_tai_len_dong_thoi_khong_va_nhau_ve_thu_tu_va_anh_chinh(db_that):
    async with db_that() as s, s.begin():
        admin_id = (await tao_nhan_vien(s, "ADMIN")).id
        dm = await tao_danh_muc(s, "A")
        actor = await s.get(NhanVien, admin_id)
        sp = await dich_vu.tao(s, actor, SanPhamTao.model_validate(than_tao(dm.id)), ip="127.0.0.1")
        sp_id, phien_ban = sp.id, sp.phien_ban

    async def tai(noi_dung):
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, admin_id)
            await san_pham_anh.them_anh(s, actor, sp_id, phien_ban, noi_dung, ip="127.0.0.1")
            await asyncio.sleep(0.3)

    ket_qua = await asyncio.wait_for(asyncio.gather(tai(ANH_JPEG), tai(ANH_PNG), return_exceptions=True), timeout=20)
    thanh_cong = [k for k in ket_qua if k is None]
    assert len(thanh_cong) == 1  # cùng `phien_ban`: bên sau thấy bản đã đổi và nhận 409
    async with db_that() as s:
        anh = (await s.execute(select(AnhSanPham))).scalars().all()
        assert len(anh) == 1 and anh[0].la_anh_chinh and len(cac_tep()) == 1

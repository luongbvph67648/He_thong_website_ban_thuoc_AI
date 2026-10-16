"""AD05: Admin quản lý thương hiệu, nhà sản xuất, hoạt chất (/api/v1/noi-bo/{thuong-hieu,nha-san-xuat,hoat-chat})."""

import asyncio

import pytest
from sqlalchemy import func, select

from app.core import phan_quyen
from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc
from app.models.enums import MucDoTuongTac
from app.models.he_thong import NhanVien, Quyen, VaiTro, VaiTroQuyen
from app.models.khach_hang import DiUng
from app.models.san_pham import HoatChat, NhaSanXuat, ThanhPhan, ThuongHieu, TuongTacHoatChat
from app.modules.san_pham import du_lieu_chung as dich_vu
from app.modules.san_pham.schemas_du_lieu_chung import (
    HoatChatDoc,
    HoatChatTao,
    NhaSanXuatDoc,
    NhaSanXuatTao,
    ThuongHieuDoc,
    ThuongHieuSua,
    ThuongHieuTao,
)
from tests.factories import tao_khach, tao_nhan_vien, tao_san_pham
from tests.nhan_vien.dung_chung import nhat_ky

URL = {
    "thuong_hieu": "/api/v1/noi-bo/thuong-hieu",
    "nha_san_xuat": "/api/v1/noi-bo/nha-san-xuat",
    "hoat_chat": "/api/v1/noi-bo/hoat-chat",
}
MO_HINH = {"thuong_hieu": ThuongHieu, "nha_san_xuat": NhaSanXuat, "hoat_chat": HoatChat}
CAC_NHOM = tuple(URL)
CAC_NHOM_XOA = ("thuong_hieu", "nha_san_xuat")  # hoạt chất không có xóa (QĐ-16)
TRUONG_DOC = {
    "thuong_hieu": {"id", "ten", "logo_url", "created_at", "so_san_pham"},
    "nha_san_xuat": {"id", "ten", "quoc_gia", "created_at", "so_san_pham"},
    "hoat_chat": {"id", "ten", "ten_khac", "mo_ta", "created_at", "so_san_pham"},
}
nhom = pytest.mark.parametrize("bang", CAC_NHOM)


def la_loi(phan_hoi, status, ma_loi):
    return phan_hoi.status_code == status and phan_hoi.json()["ma_loi"] == ma_loi


async def tao(admin, bang, ten, **them):
    return await admin.post(URL[bang], json={"ten": ten, **them})


async def chen(db, bang, ten, **truong):
    dong = MO_HINH[bang](ten=ten, **truong)
    db.add(dong)
    await db.flush()
    return dong


def cot_lien_ket(bang):
    return {"thuong_hieu": "thuong_hieu_id", "nha_san_xuat": "nha_san_xuat_id"}[bang]


# --- Tạo ---------------------------------------------------------------------------------------------------------------


@nhom
async def test_tao_tra_201_dung_truong_gon_ten_va_ghi_nhat_ky(dang_nhap_admin, db, bang):
    phan_hoi = await tao(dang_nhap_admin, bang, "  Sanofi   Việt  Nam ")
    assert phan_hoi.status_code == 201, phan_hoi.text
    doc = phan_hoi.json()
    assert set(doc) == TRUONG_DOC[bang]
    assert doc["ten"] == "Sanofi Việt Nam" and doc["so_san_pham"] == 0
    dong = await db.get(MO_HINH[bang], doc["id"])
    assert dong.ten == "Sanofi Việt Nam"
    ghi = [g for g in await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "tao") if g.bang == bang]
    assert len(ghi) == 1 and ghi[0].ban_ghi_id == str(doc["id"])
    assert ghi[0].gia_tri_moi["ten"] == "Sanofi Việt Nam"


async def test_tao_voi_truong_tuy_chon_va_chuoi_trong_la_null(dang_nhap_admin, db):
    th = (await tao(dang_nhap_admin, "thuong_hieu", "A", logo_url="  /anh/a.png ")).json()
    assert th["logo_url"] == "/anh/a.png"
    th2 = (await tao(dang_nhap_admin, "thuong_hieu", "B", logo_url="   ")).json()
    assert th2["logo_url"] is None
    nsx = (await tao(dang_nhap_admin, "nha_san_xuat", "C", quoc_gia="  Hoa   Kỳ ")).json()
    assert nsx["quoc_gia"] == "Hoa Kỳ"
    hc = (await tao(dang_nhap_admin, "hoat_chat", "D", ten_khac=" Acetaminophen ", mo_ta="Dòng 1\n\nDòng 2 ")).json()
    assert hc["ten_khac"] == "Acetaminophen" and hc["mo_ta"] == "Dòng 1\n\nDòng 2"
    hc2 = (await tao(dang_nhap_admin, "hoat_chat", "E", ten_khac="", mo_ta="  \n ")).json()
    assert hc2["ten_khac"] is None and hc2["mo_ta"] is None


@pytest.mark.parametrize(
    ("bang", "than"),
    [
        ("thuong_hieu", {}),
        ("thuong_hieu", {"ten": ""}),
        ("thuong_hieu", {"ten": "   "}),
        ("thuong_hieu", {"ten": None}),
        ("thuong_hieu", {"ten": 5}),
        ("thuong_hieu", {"ten": "x" * 151}),
        ("nha_san_xuat", {"ten": "x" * 201}),
        ("hoat_chat", {"ten": "x" * 201}),
        ("thuong_hieu", {"ten": "Ok", "id": 5}),
        ("thuong_hieu", {"ten": "Ok", "created_at": "2020-01-01T00:00:00Z"}),
        ("thuong_hieu", {"ten": "Ok", "logo_url": "javascript:alert(1)"}),
        ("thuong_hieu", {"ten": "Ok", "logo_url": "data:image/png;base64,AAAA"}),
        ("thuong_hieu", {"ten": "Ok", "logo_url": "//evil.example/a.png"}),
        ("thuong_hieu", {"ten": "Ok", "logo_url": "/a b.png"}),
        ("thuong_hieu", {"ten": "Ok", "logo_url": "/" + "a" * 500}),
        ("thuong_hieu", {"ten": "Ok", "logo_url": 5}),
        ("thuong_hieu", {"ten": "Ok\x00"}),
        ("thuong_hieu", {"ten": "Ok", "logo_url": "/a\x00.png"}),
        ("nha_san_xuat", {"ten": "Ok", "quoc_gia": "x" * 101}),
        ("nha_san_xuat", {"ten": "Ok", "quoc_gia": "VN\x00"}),
        ("hoat_chat", {"ten": "Ok", "ten_khac": "x" * 1001}),
        ("hoat_chat", {"ten": "Ok", "mo_ta": "x" * 2001}),
        ("hoat_chat", {"ten": "Ok", "mo_ta": "a\x00b"}),
        ("hoat_chat", {"ten": "Ok", "mo_ta": "a\x07b"}),
        ("hoat_chat", {"ten": "Ok", "logo_url": "/x.png"}),
        # Ký tự định dạng vô hình: hai tên trông giống hệt nhau mà không bị coi là trùng.
        ("thuong_hieu", {"ten": "San\u200bofi"}),
        ("thuong_hieu", {"ten": "\ufeffSanofi"}),
        ("nha_san_xuat", {"ten": "Ok", "quoc_gia": "Vi\u200ft Nam"}),
        ("hoat_chat", {"ten": "Ok", "ten_khac": "\u202eabc"}),
        ("hoat_chat", {"ten": "Ok", "mo_ta": "a\u200bb"}),
        ("thuong_hieu", {"ten": "Ok", "logo_url": "/a\u200b.png"}),
        # `/\host` được trình duyệt hiểu như `//host`.
        ("thuong_hieu", {"ten": "Ok", "logo_url": "/\\evil.example/a.png"}),
        ("thuong_hieu", {"ten": "Ok", "logo_url": "/\\\\evil.example/a.png"}),
    ],
)
async def test_tao_du_lieu_sai_la_400_va_khong_tao_gi(dang_nhap_admin, db, bang, than):
    phan_hoi = await dang_nhap_admin.post(URL[bang], json=than)
    assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE"), phan_hoi.text
    assert (await db.execute(select(func.count()).select_from(MO_HINH[bang]))).scalar_one() == 0


@pytest.mark.parametrize(
    ("bang", "json_tho"),
    [
        ("thuong_hieu", '{"ten":"\\ud800"}'),
        ("thuong_hieu", '{"ten":"abc\\udfff"}'),
        ("thuong_hieu", '{"ten":"Ok","logo_url":"/a\\ud800"}'),
        ("nha_san_xuat", '{"ten":"Ok","quoc_gia":"VN\\ud83d"}'),  # nửa đầu của một cặp surrogate, thiếu nửa sau
        ("hoat_chat", '{"ten":"Ok","ten_khac":"x\\ud800"}'),
        ("hoat_chat", '{"ten":"Ok","mo_ta":"a\\ud800b"}'),
    ],
)
async def test_surrogate_don_le_trong_json_la_400_chu_khong_phai_500(dang_nhap_admin, db, bang, json_tho):
    """`json.loads` chấp nhận `"\\ud800"` nhưng chuỗi đó không mã hóa được UTF-8 nên asyncpg báo lỗi (rà soát T2.1)."""
    phan_hoi = await dang_nhap_admin.post(URL[bang], content=json_tho, headers={"Content-Type": "application/json"})
    assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE"), phan_hoi.text
    assert (await db.execute(select(func.count()).select_from(MO_HINH[bang]))).scalar_one() == 0
    dong = await chen(db, bang, "Có sẵn")
    sua = await dang_nhap_admin.patch(
        f"{URL[bang]}/{dong.id}", content=json_tho, headers={"Content-Type": "application/json"}
    )
    assert la_loi(sua, 400, "DU_LIEU_KHONG_HOP_LE"), sua.text


async def test_cap_surrogate_hop_le_la_emoji_va_van_luu_duoc(dang_nhap_admin):
    phan_hoi = await dang_nhap_admin.post(
        URL["hoat_chat"],
        content='{"ten":"Ok","mo_ta":"Dễ chịu \\ud83d\\ude00"}',
        headers={"Content-Type": "application/json"},
    )
    assert phan_hoi.status_code == 201 and phan_hoi.json()["mo_ta"] == "Dễ chịu \U0001f600"


@nhom
async def test_ten_rong_hoac_qua_dai_bao_loi_bang_tieng_viet(dang_nhap_admin, bang):
    for ten in ("", "x" * 201):
        phan_hoi = await tao(dang_nhap_admin, bang, ten)
        loi = phan_hoi.json()["chi_tiet"][0]["loi"]
        assert phan_hoi.status_code == 400 and loi in ("Quá dài", "Quá ngắn"), (ten[:3], phan_hoi.text)


async def test_logo_duong_dan_hop_le_duoc_chap_nhan(dang_nhap_admin):
    for i, url in enumerate(("/anh/a.png", "https://cdn.example.com/a.png?x=1", "http://localhost:9000/a")):
        assert (await tao(dang_nhap_admin, "thuong_hieu", f"T{i}", logo_url=url)).status_code == 201, url
    dai_nhat = "/" + "a" * 499
    assert (await tao(dang_nhap_admin, "thuong_hieu", "Dài", logo_url=dai_nhat)).status_code == 201


async def test_ten_dai_nhat_cho_phep_duoc_chap_nhan(dang_nhap_admin):
    assert (await tao(dang_nhap_admin, "thuong_hieu", "x" * 150)).status_code == 201
    assert (await tao(dang_nhap_admin, "nha_san_xuat", "x" * 200)).status_code == 201
    assert (await tao(dang_nhap_admin, "hoat_chat", "x" * 200)).status_code == 201


# --- Trùng ---------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("bang", ["thuong_hieu", "hoat_chat"])
async def test_trung_ten_khong_phan_biet_hoa_thuong_va_dau_la_409(dang_nhap_admin, db, bang):
    await chen(db, bang, "Bổ phế")
    for ten in ("bổ phế", "BO PHE", "  Bo   Phe "):
        phan_hoi = await tao(dang_nhap_admin, bang, ten)
        assert la_loi(phan_hoi, 409, "TRUNG_DU_LIEU"), ten
        assert phan_hoi.json()["chi_tiet"] == {"truong": "ten"}
    assert (await tao(dang_nhap_admin, bang, "Bổ phế nhỏ")).status_code == 201
    assert (await db.execute(select(func.count()).select_from(MO_HINH[bang]))).scalar_one() == 2


async def test_nha_san_xuat_trung_theo_cap_ten_quoc_gia_va_quoc_gia_trong_la_mot_gia_tri(dang_nhap_admin, db):
    nsx = "nha_san_xuat"
    assert (await tao(dang_nhap_admin, nsx, "Pymepharco")).status_code == 201  # không quốc gia
    assert la_loi(await tao(dang_nhap_admin, nsx, "PYMEPHARCO"), 409, "TRUNG_DU_LIEU")  # NULL = NULL
    assert la_loi(await tao(dang_nhap_admin, nsx, "Pymepharco", quoc_gia="  "), 409, "TRUNG_DU_LIEU")
    assert (await tao(dang_nhap_admin, nsx, "Pymepharco", quoc_gia="Việt Nam")).status_code == 201
    assert la_loi(await tao(dang_nhap_admin, nsx, "pymepharco", quoc_gia="VIỆT NAM"), 409, "TRUNG_DU_LIEU")
    assert la_loi(await tao(dang_nhap_admin, nsx, "Pymepharco", quoc_gia="viet nam"), 409, "TRUNG_DU_LIEU")
    assert (await tao(dang_nhap_admin, nsx, "Pymepharco", quoc_gia="Pháp")).status_code == 201
    assert (await db.execute(select(func.count()).select_from(NhaSanXuat))).scalar_one() == 3


# --- Sửa ---------------------------------------------------------------------------------------------------------------


async def test_sua_chi_doi_truong_gui_len_null_la_xoa_gia_tri_tuy_chon(dang_nhap_admin, db):
    th = await chen(db, "thuong_hieu", "Cũ", logo_url="/a.png")
    phan_hoi = await dang_nhap_admin.patch(f"{URL['thuong_hieu']}/{th.id}", json={"ten": "Mới"})
    assert phan_hoi.status_code == 200 and phan_hoi.json()["ten"] == "Mới" and phan_hoi.json()["logo_url"] == "/a.png"
    phan_hoi = await dang_nhap_admin.patch(f"{URL['thuong_hieu']}/{th.id}", json={"logo_url": None})
    assert phan_hoi.json()["logo_url"] is None and phan_hoi.json()["ten"] == "Mới"
    hc = await chen(db, "hoat_chat", "HC", ten_khac="Tên khác", mo_ta="Mô tả")
    phan_hoi = await dang_nhap_admin.patch(f"{URL['hoat_chat']}/{hc.id}", json={"mo_ta": ""})
    assert phan_hoi.json()["mo_ta"] is None and phan_hoi.json()["ten_khac"] == "Tên khác"
    ghi = [g for g in await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "sua") if g.bang == "thuong_hieu"]
    assert {(tuple(g.gia_tri_cu.items()), tuple(g.gia_tri_moi.items())) for g in ghi} == {
        ((("ten", "Cũ"),), (("ten", "Mới"),)),
        ((("logo_url", "/a.png"),), (("logo_url", None),)),
    }


@pytest.mark.parametrize(
    ("bang", "than"),
    [
        ("thuong_hieu", {"ten": None}),
        ("thuong_hieu", {"ten": ""}),
        ("thuong_hieu", {"ten": "x" * 151}),
        ("thuong_hieu", {"id": 9}),
        ("thuong_hieu", {"so_san_pham": 9}),
        ("thuong_hieu", {"logo_url": "javascript:alert(1)"}),
        ("nha_san_xuat", {"ten": None}),
        ("nha_san_xuat", {"quoc_gia": "x" * 101}),
        ("hoat_chat", {"ten": None}),
        ("hoat_chat", {"mo_ta": "x" * 2001}),
        ("hoat_chat", {"quoc_gia": "VN"}),
    ],
)
async def test_sua_du_lieu_sai_la_400_va_khong_doi_gi(dang_nhap_admin, db, bang, than):
    dong = await chen(db, bang, "Giữ nguyên")
    phan_hoi = await dang_nhap_admin.patch(f"{URL[bang]}/{dong.id}", json=than)
    assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE"), phan_hoi.text
    await db.refresh(dong)
    assert dong.ten == "Giữ nguyên"


@nhom
async def test_doi_ten_trung_la_409_con_doi_hoa_thuong_cua_chinh_no_hay_gui_lai_ten_cu_thi_duoc(
    dang_nhap_admin, db, bang
):
    a = await chen(db, bang, "Alpha")
    b = await chen(db, bang, "Beta")
    url = f"{URL[bang]}/{b.id}"
    assert la_loi(await dang_nhap_admin.patch(url, json={"ten": "ALPHA"}), 409, "TRUNG_DU_LIEU")
    assert (await dang_nhap_admin.patch(url, json={"ten": "BETA"})).status_code == 200  # chỉ đổi hoa thường
    truoc = len(await nhat_ky(db, dang_nhap_admin.tai_khoan.id))
    assert (await dang_nhap_admin.patch(url, json={"ten": "BETA"})).status_code == 200  # không đổi gì
    assert (await dang_nhap_admin.patch(url, json={})).status_code == 200
    assert len(await nhat_ky(db, dang_nhap_admin.tai_khoan.id)) == truoc
    await db.refresh(a)
    assert a.ten == "Alpha"


async def test_nha_san_xuat_doi_quoc_gia_thanh_trung_cap_ten_quoc_gia_la_409(dang_nhap_admin, db):
    await chen(db, "nha_san_xuat", "Sanofi", quoc_gia="Pháp")
    khong_qg = await chen(db, "nha_san_xuat", "Sanofi")
    url = f"{URL['nha_san_xuat']}/{khong_qg.id}"
    assert la_loi(await dang_nhap_admin.patch(url, json={"quoc_gia": "pháp"}), 409, "TRUNG_DU_LIEU")
    assert (await dang_nhap_admin.patch(url, json={"quoc_gia": "Đức"})).json()["quoc_gia"] == "Đức"
    assert (await dang_nhap_admin.patch(url, json={"quoc_gia": None})).json()["quoc_gia"] is None
    # Đổi tên sang tên đã có cùng quốc gia (cùng NULL) cũng là trùng.
    khac = await chen(db, "nha_san_xuat", "Roche")
    assert la_loi(
        await dang_nhap_admin.patch(f"{URL['nha_san_xuat']}/{khac.id}", json={"ten": "sanofi"}), 409, "TRUNG_DU_LIEU"
    )


@nhom
async def test_sua_xoa_xem_khong_ton_tai_la_404_id_ngoai_khoang_la_400(dang_nhap_admin, bang):
    for id_ in (999_999, 2_000_000_000):
        assert la_loi(await dang_nhap_admin.get(f"{URL[bang]}/{id_}"), 404, "KHONG_TIM_THAY")
        assert la_loi(await dang_nhap_admin.patch(f"{URL[bang]}/{id_}", json={"ten": "X"}), 404, "KHONG_TIM_THAY")
        if bang in CAC_NHOM_XOA:
            assert la_loi(await dang_nhap_admin.delete(f"{URL[bang]}/{id_}"), 404, "KHONG_TIM_THAY")
    for id_ in (0, -1, 2_147_483_648):
        assert la_loi(await dang_nhap_admin.get(f"{URL[bang]}/{id_}"), 400, "DU_LIEU_KHONG_HOP_LE")
        if bang in CAC_NHOM_XOA:
            assert la_loi(await dang_nhap_admin.delete(f"{URL[bang]}/{id_}"), 400, "DU_LIEU_KHONG_HOP_LE")


# --- Danh sách -------------------------------------------------------------------------------------------------------------


@nhom
async def test_danh_sach_mac_dinh_theo_ten_khong_phan_biet_dau_va_phan_trang(dang_nhap_admin, db, bang):
    for ten in ("Đông", "Bắc", "an", "Ân", "Zeta"):
        await chen(db, bang, ten)
    phan_hoi = await dang_nhap_admin.get(URL[bang], params={"kich_thuoc": 2})
    assert phan_hoi.status_code == 200, phan_hoi.text
    goi = phan_hoi.json()
    assert goi["tong"] == 5 and goi["kich_thuoc"] == 2 and len(goi["du_lieu"]) == 2
    assert set(goi["du_lieu"][0]) == TRUONG_DOC[bang]
    ten_theo_trang = []
    for trang in (1, 2, 3):
        goi_trang = await dang_nhap_admin.get(URL[bang], params={"kich_thuoc": 2, "trang": trang})
        ten_theo_trang += [d["ten"] for d in goi_trang.json()["du_lieu"]]
    # "an" và "Ân" bằng nhau khi bỏ dấu: khóa phụ là id (thứ tự tạo).
    assert ten_theo_trang == ["an", "Ân", "Bắc", "Đông", "Zeta"]


@nhom
async def test_tim_kiem_khong_phan_biet_dau_va_hoa_thuong_va_ky_tu_dac_biet_la_chu_thuong(dang_nhap_admin, db, bang):
    await chen(db, bang, "Bổ Phế Viên")
    await chen(db, bang, "Phế quản")
    await chen(db, bang, "100% Sạch")
    await chen(db, bang, "Tên_gạch")
    await chen(db, bang, "TenXgach")

    async def tim(q):
        return sorted(d["ten"] for d in (await dang_nhap_admin.get(URL[bang], params={"q": q})).json()["du_lieu"])

    assert await tim("bo phe") == ["Bổ Phế Viên"]
    assert await tim("PHẾ") == ["Bổ Phế Viên", "Phế quản"]
    assert await tim("%") == ["100% Sạch"]  # % là chữ thường, không phải ký tự thay thế
    assert await tim("n_g") == ["Tên_gạch"]  # _ cũng vậy
    assert len(await tim("   ")) == 5 and len(await tim("")) == 5  # trống/khoảng trắng = không lọc
    assert await tim("không có") == []
    assert la_loi(await dang_nhap_admin.get(URL[bang], params={"q": "x" * 101}), 400, "DU_LIEU_KHONG_HOP_LE")


async def test_tim_hoat_chat_theo_ten_khac_nhung_thuong_hieu_va_nha_san_xuat_chi_theo_ten(dang_nhap_admin, db):
    await chen(db, "hoat_chat", "Paracetamol", ten_khac="Acetaminophen; N-acetyl-p-aminophenol")
    hoat = (await dang_nhap_admin.get(URL["hoat_chat"], params={"q": "ACETAMINOPHEN"})).json()
    assert [d["ten"] for d in hoat["du_lieu"]] == ["Paracetamol"]
    await chen(db, "nha_san_xuat", "Sanofi", quoc_gia="Pháp")
    assert (await dang_nhap_admin.get(URL["nha_san_xuat"], params={"q": "phap"})).json()["tong"] == 0


@nhom
async def test_sap_xep_theo_ten_ngay_tao_va_so_san_pham_va_ten_truong_la_se_400(dang_nhap_admin, db, bang):
    ca = await chen(db, bang, "Cá")
    an = await chen(db, bang, "An")
    be = await chen(db, bang, "Bê")

    async def thu_tu(sap_xep):
        phan_hoi = await dang_nhap_admin.get(URL[bang], params={"sap_xep": sap_xep})
        assert phan_hoi.status_code == 200, (sap_xep, phan_hoi.text)
        return [d["id"] for d in phan_hoi.json()["du_lieu"]]

    assert await thu_tu("ten") == [an.id, be.id, ca.id]
    assert await thu_tu("-ten") == [ca.id, be.id, an.id]
    assert await thu_tu("created_at") == sorted([ca.id, an.id, be.id], key=lambda i: i)  # tạo theo id tăng
    assert await thu_tu("-created_at") == sorted([ca.id, an.id, be.id], reverse=True)
    assert len(await thu_tu("so_san_pham")) == 3
    for sai in ("id", "mo_ta; DROP TABLE x", "ten,created_at", "password", "-"):
        assert (await dang_nhap_admin.get(URL[bang], params={"sap_xep": sai})).status_code == 400, sai


async def test_so_san_pham_dem_ca_san_pham_da_xoa_mem_va_hoat_chat_dem_dong_thanh_phan(dang_nhap_admin, db):
    th = await chen(db, "thuong_hieu", "Có hàng")
    await chen(db, "thuong_hieu", "Chưa dùng")
    nsx = await chen(db, "nha_san_xuat", "NSX có hàng", quoc_gia="Việt Nam")
    hc = await chen(db, "hoat_chat", "Hoạt chất dùng")
    sp1 = await tao_san_pham(db, thuong_hieu_id=th.id, nha_san_xuat_id=nsx.id)
    sp2 = await tao_san_pham(db, thuong_hieu_id=th.id, nha_san_xuat_id=nsx.id, deleted_at=bay_gio_utc())
    db.add_all([ThanhPhan(san_pham_id=sp1.id, hoat_chat_id=hc.id, ham_luong="500mg")])
    db.add(ThanhPhan(san_pham_id=sp2.id, hoat_chat_id=hc.id))
    await db.flush()

    def so(goi, ten):
        return {d["ten"]: d["so_san_pham"] for d in goi.json()["du_lieu"]}[ten]

    assert so(await dang_nhap_admin.get(URL["thuong_hieu"]), "Có hàng") == 2
    assert so(await dang_nhap_admin.get(URL["thuong_hieu"]), "Chưa dùng") == 0
    assert so(await dang_nhap_admin.get(URL["nha_san_xuat"]), "NSX có hàng") == 2
    assert so(await dang_nhap_admin.get(URL["hoat_chat"]), "Hoạt chất dùng") == 2
    assert (await dang_nhap_admin.get(f"{URL['thuong_hieu']}/{th.id}")).json()["so_san_pham"] == 2
    theo = await dang_nhap_admin.get(URL["thuong_hieu"], params={"sap_xep": "-so_san_pham"})
    assert [d["ten"] for d in theo.json()["du_lieu"]] == ["Có hàng", "Chưa dùng"]
    theo = await dang_nhap_admin.get(URL["thuong_hieu"], params={"sap_xep": "so_san_pham"})
    assert [d["ten"] for d in theo.json()["du_lieu"]] == ["Chưa dùng", "Có hàng"]


@nhom
async def test_ky_tu_nul_trong_tim_kiem_la_400_chu_khong_phai_500(dang_nhap_admin, bang):
    phan_hoi = await dang_nhap_admin.get(URL[bang], params={"q": "a\x00b"})
    assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE"), phan_hoi.text


async def test_phan_hoi_hoat_chat_khong_co_so_lieu_di_ung(dang_nhap_admin, db):
    hc = await chen(db, "hoat_chat", "Penicillin")
    khach = await tao_khach(db)
    db.add(DiUng(khach_hang_id=khach.id, hoat_chat_id=hc.id, ghi_chu="Nổi mề đay"))
    await db.flush()
    goi = await dang_nhap_admin.get(f"{URL['hoat_chat']}/{hc.id}")
    assert set(goi.json()) == TRUONG_DOC["hoat_chat"] and goi.json()["so_san_pham"] == 0
    lst = await dang_nhap_admin.get(URL["hoat_chat"])
    assert set(lst.json()["du_lieu"][0]) == TRUONG_DOC["hoat_chat"]
    assert "Nổi mề đay" not in goi.text + lst.text and str(khach.so_dien_thoai) not in goi.text + lst.text


# --- Xóa ---------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("bang", CAC_NHOM_XOA)
async def test_xoa_ban_ghi_chua_dung_la_xoa_cung_204_va_ghi_nhat_ky(dang_nhap_admin, db, bang):
    dong = await chen(db, bang, "Sắp xóa")
    phan_hoi = await dang_nhap_admin.delete(f"{URL[bang]}/{dong.id}")
    assert phan_hoi.status_code == 204 and phan_hoi.content == b""
    assert (await db.execute(select(func.count()).select_from(MO_HINH[bang]))).scalar_one() == 0
    ghi = [g for g in await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "xoa") if g.bang == bang]
    assert len(ghi) == 1 and ghi[0].ban_ghi_id == str(dong.id) and ghi[0].gia_tri_cu["ten"] == "Sắp xóa"
    assert la_loi(await dang_nhap_admin.delete(f"{URL[bang]}/{dong.id}"), 404, "KHONG_TIM_THAY")


@pytest.mark.parametrize("bang", CAC_NHOM_XOA)
async def test_ban_ghi_dang_gan_voi_san_pham_ke_ca_da_xoa_mem_khong_xoa_duoc(dang_nhap_admin, db, bang):
    dong = await chen(db, bang, "Đang dùng")
    await tao_san_pham(db, **{cot_lien_ket(bang): dong.id, "deleted_at": bay_gio_utc()})  # chỉ còn sản phẩm đã xóa mềm
    truoc = len(await nhat_ky(db, dang_nhap_admin.tai_khoan.id))
    phan_hoi = await dang_nhap_admin.delete(f"{URL[bang]}/{dong.id}")
    assert la_loi(phan_hoi, 409, "DU_LIEU_DANG_DUOC_SU_DUNG"), phan_hoi.text
    assert (await dang_nhap_admin.get(f"{URL[bang]}/{dong.id}")).status_code == 200  # còn nguyên, phiên vẫn dùng được
    assert len(await nhat_ky(db, dang_nhap_admin.tai_khoan.id)) == truoc


async def test_hoat_chat_khong_co_xoa_nen_khong_do_duoc_hoat_chat_nao_nam_trong_di_ung(
    dang_nhap_admin, db, clients_theo_vai_tro
):
    """Nếu có DELETE thì 204/409 cho Admin biết khách nào đó dị ứng hoạt chất đó, và tạo hoạt chất mồi rồi thử xóa là dò
    được từng hoạt chất (rà soát T2.1). Không có DELETE: phản hồi giống hệt nhau cho mọi hoạt chất và không ghi gì."""
    sp = await tao_san_pham(db)
    tu_do = await chen(db, "hoat_chat", "Tự do")
    trong_thanh_phan = await chen(db, "hoat_chat", "Trong thành phần")
    trong_tuong_tac = await chen(db, "hoat_chat", "Trong tương tác")
    doi_tac = await chen(db, "hoat_chat", "Đối tác tương tác")
    trong_di_ung = await chen(db, "hoat_chat", "Trong dị ứng của khách")
    db.add(ThanhPhan(san_pham_id=sp.id, hoat_chat_id=trong_thanh_phan.id))
    a, b = sorted([trong_tuong_tac.id, doi_tac.id])
    db.add(TuongTacHoatChat(hoat_chat_a_id=a, hoat_chat_b_id=b, muc_do=MucDoTuongTac.nhe, khuyen_cao="Thận trọng"))
    khach = await tao_khach(db)
    db.add(DiUng(khach_hang_id=khach.id, hoat_chat_id=trong_di_ung.id))
    await db.flush()
    truoc = len(await nhat_ky(db, dang_nhap_admin.tai_khoan.id))
    phan_hoi = []
    for hc in (tu_do, trong_thanh_phan, trong_tuong_tac, doi_tac, trong_di_ung):
        for c in (dang_nhap_admin, clients_theo_vai_tro["PHARMACIST"]):
            r = await c.delete(f"{URL['hoat_chat']}/{hc.id}")
            assert la_loi(r, 405, "PHUONG_THUC_KHONG_DUOC_PHEP"), (hc.ten, r.status_code, r.text)
            phan_hoi.append(r.json())
    assert all(p == phan_hoi[0] for p in phan_hoi)  # giống hệt nhau, kể cả chi_tiet
    assert (await db.execute(select(func.count()).select_from(HoatChat))).scalar_one() == 5
    assert len(await nhat_ky(db, dang_nhap_admin.tai_khoan.id)) == truoc


async def test_service_tu_choi_xoa_nhom_khong_cho_xoa(db):
    admin = await tao_nhan_vien(db, "ADMIN")
    hc = await chen(db, "hoat_chat", "Không xóa")
    with pytest.raises(RuntimeError):
        await dich_vu.xoa(db, admin, dich_vu.HOAT_CHAT, hc.id, ip="127.0.0.1")


async def test_xoa_that_bai_vi_dang_dung_khong_lam_hong_transaction_cua_request_khac(db_that):
    """Vi phạm khóa ngoại xảy ra trong savepoint nên service vẫn dùng được session sau đó."""
    async with db_that() as s, s.begin():
        admin = await tao_nhan_vien(s, "ADMIN")
        admin_id = admin.id
        th = await chen(s, "thuong_hieu", "Đang dùng")
        await tao_san_pham(s, thuong_hieu_id=th.id)
        trong = await chen(s, "thuong_hieu", "Chưa dùng")
        dang_dung_id, trong_id = th.id, trong.id
    async with db_that() as s, s.begin():
        actor = await s.get(NhanVien, admin_id)
        with pytest.raises(LoiNghiepVu) as loi:
            await dich_vu.xoa(s, actor, dich_vu.THUONG_HIEU, dang_dung_id, ip="127.0.0.1")
        assert loi.value.ma_loi == "DU_LIEU_DANG_DUOC_SU_DUNG"
        await dich_vu.xoa(s, actor, dich_vu.THUONG_HIEU, trong_id, ip="127.0.0.1")  # cùng session vẫn chạy được
    async with db_that() as s:
        assert [t.ten for t in (await s.execute(select(ThuongHieu))).scalars()] == ["Đang dùng"]


# --- Quyền ---------------------------------------------------------------------------------------------------------------


@nhom
async def test_duoc_si_chi_doc_kho_va_khach_khong_vao_duoc(clients_theo_vai_tro, dang_nhap_khach, client, db, bang):
    dong = await chen(db, bang, "Có sẵn")
    duoc_si, kho = clients_theo_vai_tro["PHARMACIST"], clients_theo_vai_tro["WAREHOUSE"]
    assert (await duoc_si.get(URL[bang])).status_code == 200
    assert (await duoc_si.get(f"{URL[bang]}/{dong.id}")).status_code == 200
    for c in (duoc_si, kho):
        ghi = [
            ("post", URL[bang], {"ten": "Mới"}),
            ("patch", f"{URL[bang]}/{dong.id}", {"ten": "Đổi"}),
            *([("delete", f"{URL[bang]}/{dong.id}", None)] if bang in CAC_NHOM_XOA else []),
        ]
        for phuong_thuc, duong, than in ghi:
            phan_hoi = await getattr(c, phuong_thuc)(duong, **({"json": than} if than is not None else {}))
            assert la_loi(phan_hoi, 403, "KHONG_CO_QUYEN"), (phuong_thuc, duong)
    assert la_loi(await kho.get(URL[bang]), 403, "KHONG_CO_QUYEN")
    assert (await client.get(URL[bang])).status_code == 401 and (
        await dang_nhap_khach.get(URL[bang])
    ).status_code == 401
    await db.refresh(dong)
    assert dong.ten == "Có sẵn"


async def test_master_data_manage_khong_chi_admin_nen_uy_quyen_ghi_cho_duoc_si_van_hoat_dong(clients_theo_vai_tro, db):
    """Khác với `category.manage`: quyền này AD18 ủy quyền được và không có chốt `dam_bao_la_admin` (spec 06 mục 3.10)."""
    duoc_si = clients_theo_vai_tro["PHARMACIST"]
    quyen_id = (await db.execute(select(Quyen.id).where(Quyen.ma == "master_data.manage"))).scalar_one()
    vai_tro_id = (await db.execute(select(VaiTro.id).where(VaiTro.ma == "PHARMACIST"))).scalar_one()
    dong = (
        await db.execute(
            select(VaiTroQuyen).where(VaiTroQuyen.vai_tro_id == vai_tro_id, VaiTroQuyen.quyen_id == quyen_id)
        )
    ).scalar_one()
    dong.gioi_han = None  # chi_xem -> day_du
    await db.flush()
    phan_quyen.xoa_cache_quyen()
    phan_hoi = await tao(duoc_si, "thuong_hieu", "Do dược sĩ tạo")
    assert phan_hoi.status_code == 201, phan_hoi.text


# --- Đồng thời ---------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("nhom_dich_vu", "du_lieu_a", "du_lieu_b"),
    [
        (dich_vu.THUONG_HIEU, ("Sanofi",), ("SANOFI",)),
        (dich_vu.HOAT_CHAT, ("Bổ phế",), ("bo phe",)),
        (dich_vu.NHA_SAN_XUAT, ("Pymepharco",), ("PYMEPHARCO",)),  # cùng quốc gia NULL: DB không chặn được
    ],
)
async def test_hai_admin_tao_ten_trung_nhau_cung_luc_chi_mot_ben_thanh_cong(
    db_that, nhom_dich_vu, du_lieu_a, du_lieu_b
):
    async with db_that() as s, s.begin():
        admin_id = (await tao_nhan_vien(s, "ADMIN")).id
    tao_schema = {"thuong_hieu": ThuongHieuTao, "hoat_chat": HoatChatTao, "nha_san_xuat": NhaSanXuatTao}[
        nhom_dich_vu.bang
    ]
    doc = {"thuong_hieu": ThuongHieuDoc, "hoat_chat": HoatChatDoc, "nha_san_xuat": NhaSanXuatDoc}[nhom_dich_vu.bang]

    async def tao_moi(ten):
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, admin_id)
            await dich_vu.tao(s, actor, nhom_dich_vu, doc, tao_schema(ten=ten), ip="127.0.0.1")
            await asyncio.sleep(0.3)  # giữ transaction mở để bên kia phải chờ khóa

    ket_qua = await asyncio.wait_for(
        asyncio.gather(tao_moi(du_lieu_a[0]), tao_moi(du_lieu_b[0]), return_exceptions=True), timeout=20
    )
    loi = [k for k in ket_qua if k is not None]
    assert len(loi) == 1 and isinstance(loi[0], LoiNghiepVu) and loi[0].ma_loi == "TRUNG_DU_LIEU", ket_qua
    async with db_that() as s:
        assert (await s.execute(select(func.count()).select_from(nhom_dich_vu.mo_hinh))).scalar_one() == 1


async def test_hai_admin_doi_ten_hai_ban_ghi_thanh_cung_mot_ten_cung_luc_chi_mot_ben_thanh_cong(db_that):
    """Đổi tên cũng phải qua khóa tư vấn của nhóm: nếu không, hai bên cùng thấy tên còn trống và bên chậm hơn đụng
    ràng buộc unique của DB (500) hoặc, với tên khác hoa thường, lọt cả hai."""
    async with db_that() as s, s.begin():
        admin_id = (await tao_nhan_vien(s, "ADMIN")).id
        a_id = (await chen(s, "thuong_hieu", "Alpha")).id
        b_id = (await chen(s, "thuong_hieu", "Beta")).id

    async def doi_ten(ban_ghi_id, ten):
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, admin_id)
            await dich_vu.sua(
                s, actor, dich_vu.THUONG_HIEU, ThuongHieuDoc, ban_ghi_id, ThuongHieuSua(ten=ten), ip="127.0.0.1"
            )
            await asyncio.sleep(0.3)  # giữ transaction mở để bên kia phải chờ khóa

    ket_qua = await asyncio.wait_for(
        asyncio.gather(doi_ten(a_id, "Gamma"), doi_ten(b_id, "GAMMA"), return_exceptions=True), timeout=20
    )
    loi = [k for k in ket_qua if k is not None]
    assert len(loi) == 1 and isinstance(loi[0], LoiNghiepVu) and loi[0].ma_loi == "TRUNG_DU_LIEU", ket_qua
    async with db_that() as s:
        ten = sorted(t.ten for t in (await s.execute(select(ThuongHieu))).scalars())
        assert ten in (["Beta", "Gamma"], ["Alpha", "GAMMA"]), ten


async def test_xoa_thuong_hieu_cho_giao_dich_dang_gan_san_pham_vao_no_roi_bi_tu_choi(db_that):
    async with db_that() as s, s.begin():
        admin_id = (await tao_nhan_vien(s, "ADMIN")).id
        th_id = (await chen(s, "thuong_hieu", "Sắp có hàng")).id
    dang_them = asyncio.Event()

    async def gan_san_pham():
        async with db_that() as s, s.begin():
            await tao_san_pham(s, thuong_hieu_id=th_id)
            dang_them.set()
            await asyncio.sleep(0.4)  # chưa commit

    async def xoa():
        await dang_them.wait()
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, admin_id)
            await dich_vu.xoa(s, actor, dich_vu.THUONG_HIEU, th_id, ip="127.0.0.1")

    ket_qua = await asyncio.wait_for(asyncio.gather(gan_san_pham(), xoa(), return_exceptions=True), timeout=20)
    assert ket_qua[0] is None
    assert isinstance(ket_qua[1], LoiNghiepVu) and ket_qua[1].ma_loi == "DU_LIEU_DANG_DUOC_SU_DUNG", ket_qua
    async with db_that() as s:
        assert (await s.get(ThuongHieu, th_id)) is not None

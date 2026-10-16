"""AD04: Admin quản lý sản phẩm, thông tin thương mại (/api/v1/noi-bo/san-pham)."""

import asyncio
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.core import phan_quyen
from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc
from app.models.he_thong import NhanVien, NhatKyHeThong, Quyen, VaiTro, VaiTroQuyen
from app.models.kho import LoThuoc
from app.models.san_pham import DanhMuc, HoatChat, NhaSanXuat, SanPham, ThuongHieu
from app.modules.san_pham import san_pham as dich_vu
from app.modules.san_pham.schemas_san_pham import SanPhamSua, SanPhamTao
from tests.factories import tao_danh_muc, tao_lo, tao_nhan_vien, tao_san_pham
from tests.nhan_vien.dung_chung import nhat_ky
from tests.san_pham.mau_san_pham import GOC, doc_sp, la_loi, tao_sp, than_tao

DON_VI_HOP_LE = {"ten_don_vi": "Viên", "he_so": 1, "gia_ban": "1000"}

# --- Tạo ---------------------------------------------------------------------------------------------------------------


async def test_tao_day_du_tra_201_chi_tiet_dung_va_ghi_nhat_ky(dang_nhap_admin, db):
    dm = await tao_danh_muc(db, "Giảm đau")
    hc = HoatChat(ten="Paracetamol")
    db.add(hc)
    await db.flush()
    phan_hoi = await dang_nhap_admin.post(
        GOC,
        json=than_tao(
            dm.id,
            sku="  para-500 ",
            ten="  Paracetamol   500mg ",
            loai_san_pham="thuoc_khong_ke_don",
            so_dang_ky="VD-1234-20",
            dang_bao_che="Viên nén",
            quy_cach="Hộp 10 vỉ x 10 viên",
            doi_tuong_su_dung="Người lớn",
            ton_toi_thieu=50,
            dung_dinh_ky=True,
            so_ngay_dung_moi_don_vi="3.50",
            so_luong_toi_da_moi_don=20,
            la_noi_bat=True,
            thanh_phan=[{"hoat_chat_id": hc.id, "ham_luong": " 500mg "}],
        ),
    )
    assert phan_hoi.status_code == 201, phan_hoi.text
    sp = phan_hoi.json()
    assert sp["sku"] == "PARA-500" and sp["ten"] == "Paracetamol 500mg" and sp["slug"] == "paracetamol-500mg"
    assert sp["don_vi_co_so"] == "Viên" and sp["ten_danh_muc"] == "Giảm đau"
    assert (sp["ton_toi_thieu"], sp["so_luong_toi_da_moi_don"], sp["la_noi_bat"]) == (50, 20, True)
    assert sp["dung_dinh_ky"] is True and sp["so_ngay_dung_moi_don_vi"] == "3.50"
    assert [(d["ten_don_vi"], d["he_so"], d["gia_ban"], d["la_mac_dinh"]) for d in sp["don_vi"]] == [
        ("Viên", 1, "1000.00", False),
        ("Hộp", 100, "90000.00", True),
    ]
    assert sp["thanh_phan"] == [{"hoat_chat_id": hc.id, "ten_hoat_chat": "Paracetamol", "ham_luong": "500mg"}]
    assert sp["anh"] == [] and len(sp["phien_ban"]) == 16
    ghi = [g for g in await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "tao") if g.bang == "san_pham"]
    assert len(ghi) == 1 and ghi[0].ban_ghi_id == str(sp["id"]) and ghi[0].gia_tri_moi["sku"] == "PARA-500"
    gia = ghi[0].gia_tri_moi["don_vi"][1]["gia_ban"]
    assert isinstance(gia, str) and Decimal(gia) == 90000  # tiền trong nhật ký là chuỗi chính xác, không phải float


async def test_chi_can_cac_truong_bat_buoc_con_lai_lay_mac_dinh(dang_nhap_admin, db):
    dm = await tao_danh_muc(db, "A")
    sp = await tao_sp(dang_nhap_admin, dm.id)
    assert (sp["ton_toi_thieu"], sp["dung_dinh_ky"], sp["la_noi_bat"], sp["trang_thai"]) == (
        0,
        False,
        False,
        "dang_kinh_doanh",
    )
    assert sp["thuong_hieu_id"] is None and sp["so_luong_toi_da_moi_don"] is None


async def test_chi_tiet_kem_ten_thuong_hieu_va_nha_san_xuat_hoac_null(dang_nhap_admin, db):
    """Form sửa cần tên để hiện ô chọn mà không phải tải thêm; không gắn thì cả id lẫn tên là null."""
    dm = await tao_danh_muc(db, "A")
    th, nsx = ThuongHieu(ten="Hậu Giang"), NhaSanXuat(ten="Pymepharco")
    db.add_all([th, nsx])
    await db.flush()
    co = await tao_sp(dang_nhap_admin, dm.id, thuong_hieu_id=th.id, nha_san_xuat_id=nsx.id)
    assert (co["ten_thuong_hieu"], co["ten_nha_san_xuat"]) == ("Hậu Giang", "Pymepharco")
    doc = await doc_sp(dang_nhap_admin, co["id"])
    assert (doc["ten_thuong_hieu"], doc["ten_nha_san_xuat"]) == ("Hậu Giang", "Pymepharco")
    khong = await tao_sp(dang_nhap_admin, dm.id)
    assert (khong["thuong_hieu_id"], khong["ten_thuong_hieu"], khong["nha_san_xuat_id"], khong["ten_nha_san_xuat"]) == (
        None,
        None,
        None,
        None,
    )


async def test_sku_trung_khong_phan_biet_hoa_thuong_ke_ca_san_pham_da_xoa_la_409(dang_nhap_admin, db):
    dm = await tao_danh_muc(db, "A")
    await tao_sp(dang_nhap_admin, dm.id, sku="abc-1")
    for sku in ("ABC-1", " abc-1 ", "Abc-1"):
        phan_hoi = await dang_nhap_admin.post(GOC, json=than_tao(dm.id, sku=sku))
        assert la_loi(phan_hoi, 409, "TRUNG_DU_LIEU") and phan_hoi.json()["chi_tiet"] == {"truong": "sku"}, sku
    da_xoa = await tao_san_pham(db, sku="CU-1", deleted_at=bay_gio_utc())  # DB vẫn cấm trùng SKU của dòng đã xóa
    phan_hoi = await dang_nhap_admin.post(GOC, json=than_tao(dm.id, sku=da_xoa.sku.lower()))
    assert la_loi(phan_hoi, 409, "TRUNG_DU_LIEU")
    assert (await db.execute(select(func.count()).select_from(SanPham))).scalar_one() == 2


async def test_sku_trung_voi_dong_luu_chu_thuong_nhap_thang_vao_db_van_la_409(dang_nhap_admin, db):
    """Dòng nhập ngoài API (seed, nhập tay) có thể mang SKU chữ thường: so sánh phải bỏ qua hoa thường ở phía DB."""
    dm = await tao_danh_muc(db, "A")
    await tao_san_pham(db, sku="legacy-low")
    them = await dang_nhap_admin.post(GOC, json=than_tao(dm.id, sku="LEGACY-LOW"))
    assert la_loi(them, 409, "TRUNG_DU_LIEU") and them.json()["chi_tiet"] == {"truong": "sku"}
    khac = await tao_sp(dang_nhap_admin, dm.id, sku="khac")
    doi = await dang_nhap_admin.patch(f"{GOC}/{khac['id']}", json={"phien_ban": khac["phien_ban"], "sku": "LEGACY-LOW"})
    assert la_loi(doi, 409, "TRUNG_DU_LIEU") and doi.json()["chi_tiet"] == {"truong": "sku"}


async def test_slug_tu_sinh_khong_dau_trung_thi_them_hau_to_ke_ca_voi_san_pham_da_xoa_va_doi_ten_giu_slug(
    dang_nhap_admin, db
):
    dm = await tao_danh_muc(db, "A")
    a = await tao_sp(dang_nhap_admin, dm.id, ten="Thuốc ho Bổ phế")
    assert a["slug"] == "thuoc-ho-bo-phe"
    await tao_san_pham(db, ten="x", slug="thuoc-ho-bo-phe-2", deleted_at=bay_gio_utc())  # slug đã xóa vẫn giữ chỗ
    b = await tao_sp(dang_nhap_admin, dm.id, ten="THUỐC HO BỔ PHẾ")
    assert b["slug"] == "thuoc-ho-bo-phe-3"
    sua = await dang_nhap_admin.patch(
        f"{GOC}/{a['id']}", json={"phien_ban": a["phien_ban"], "ten": "Tên hoàn toàn mới"}
    )
    assert sua.status_code == 200 and sua.json()["slug"] == "thuoc-ho-bo-phe"  # đổi tên không đổi slug


@pytest.mark.parametrize(
    ("ten_ca", "ghi_de"),
    [
        ("không có đơn vị", {"don_vi": []}),
        (
            "hai đơn vị cơ sở",
            {
                "don_vi": [
                    {"ten_don_vi": "A", "he_so": 1, "gia_ban": "1"},
                    {"ten_don_vi": "B", "he_so": 1, "gia_ban": "1"},
                ]
            },
        ),
        ("không có đơn vị cơ sở", {"don_vi": [{"ten_don_vi": "Hộp", "he_so": 10, "gia_ban": "1"}]}),
        (
            "hai đơn vị mặc định",
            {
                "don_vi": [
                    {"ten_don_vi": "Viên", "he_so": 1, "gia_ban": "1", "la_mac_dinh": True},
                    {"ten_don_vi": "Hộp", "he_so": 10, "gia_ban": "1", "la_mac_dinh": True},
                ]
            },
        ),
        (
            "tên đơn vị trùng (không dấu, hoa thường)",
            {
                "don_vi": [
                    {"ten_don_vi": "Hộp", "he_so": 1, "gia_ban": "1"},
                    {"ten_don_vi": "hop", "he_so": 10, "gia_ban": "1"},
                ]
            },
        ),
        ("hệ số 0", {"don_vi": [{"ten_don_vi": "A", "he_so": 0, "gia_ban": "1"}]}),
        ("hệ số thực", {"don_vi": [{"ten_don_vi": "A", "he_so": 1.5, "gia_ban": "1"}]}),
        ("hệ số chuỗi", {"don_vi": [{"ten_don_vi": "A", "he_so": "1", "gia_ban": "1"}]}),
        ("giá âm", {"don_vi": [{"ten_don_vi": "A", "he_so": 1, "gia_ban": "-1"}]}),
        ("giá lẻ đồng", {"don_vi": [{"ten_don_vi": "A", "he_so": 1, "gia_ban": "1000.5"}]}),
        ("giá không phải số", {"don_vi": [{"ten_don_vi": "A", "he_so": 1, "gia_ban": "abc"}]}),
        ("giá quá lớn", {"don_vi": [{"ten_don_vi": "A", "he_so": 1, "gia_ban": "1000000000000"}]}),
        ("giá true", {"don_vi": [{"ten_don_vi": "A", "he_so": 1, "gia_ban": True}]}),
        ("tên đơn vị rỗng", {"don_vi": [{"ten_don_vi": "  ", "he_so": 1, "gia_ban": "1"}]}),
        ("tên đơn vị quá dài", {"don_vi": [{"ten_don_vi": "x" * 31, "he_so": 1, "gia_ban": "1"}]}),
        ("mã vạch có khoảng trắng", {"don_vi": [{"ten_don_vi": "A", "he_so": 1, "gia_ban": "1", "ma_vach": "12 34"}]}),
        ("mã vạch quá dài", {"don_vi": [{"ten_don_vi": "A", "he_so": 1, "gia_ban": "1", "ma_vach": "1" * 51}]}),
        (
            "mã vạch trùng giữa hai đơn vị",
            {
                "don_vi": [
                    {"ten_don_vi": "A", "he_so": 1, "gia_ban": "1", "ma_vach": "abc"},
                    {"ten_don_vi": "B", "he_so": 2, "gia_ban": "1", "ma_vach": "ABC"},
                ]
            },
        ),
        ("đơn vị có trường lạ", {"don_vi": [{"ten_don_vi": "A", "he_so": 1, "gia_ban": "1", "ton": 5}]}),
        ("đơn vị mới có id", {"don_vi": [{"id": 5, "ten_don_vi": "A", "he_so": 1, "gia_ban": "1"}]}),
        ("trùng hoạt chất", {"thanh_phan": [{"hoat_chat_id": 1}, {"hoat_chat_id": 1}]}),
        ("hàm lượng quá dài", {"thanh_phan": [{"hoat_chat_id": 1, "ham_luong": "x" * 51}]}),
        ("SKU rỗng", {"sku": "  "}),
        ("SKU có khoảng trắng", {"sku": "AB 12"}),
        ("SKU có ký tự lạ", {"sku": "AB/12"}),
        ("SKU quá dài", {"sku": "A" * 51}),
        ("tên rỗng", {"ten": " "}),
        ("tên chỉ có ký tự đặc biệt (không tạo được slug)", {"ten": "!!!"}),
        ("tên quá dài", {"ten": "x" * 256}),
        ("tên có NUL", {"ten": "A\x00B"}),
        ("loại lạ", {"loai_san_pham": "banh_keo"}),
        ("trạng thái lạ", {"trang_thai": "xoa"}),
        ("tồn tối thiểu âm", {"ton_toi_thieu": -1}),
        ("tồn tối thiểu thực", {"ton_toi_thieu": 1.5}),
        ("giới hạn mỗi đơn bằng 0", {"so_luong_toi_da_moi_don": 0}),
        ("dùng định kỳ thiếu số ngày", {"dung_dinh_ky": True}),
        ("có số ngày mà không dùng định kỳ", {"so_ngay_dung_moi_don_vi": "3"}),
        ("số ngày 0", {"dung_dinh_ky": True, "so_ngay_dung_moi_don_vi": "0"}),
        ("số ngày quá nhiều chữ số lẻ", {"dung_dinh_ky": True, "so_ngay_dung_moi_don_vi": "1.234"}),
        ("số ngày quá lớn", {"dung_dinh_ky": True, "so_ngay_dung_moi_don_vi": "10000"}),
        ("thuốc kê đơn không được nổi bật", {"loai_san_pham": "thuoc_ke_don", "la_noi_bat": True}),
        ("trường chuyên môn bị cấm", {"chi_dinh": "Giảm đau"}),
        ("trường slug bị cấm", {"slug": "tu-dat"}),
        ("trường don_vi_co_so bị cấm", {"don_vi_co_so": "Viên"}),
        ("trường id bị cấm", {"id": 9}),
        ("số đăng ký quá dài", {"so_dang_ky": "x" * 51}),
        ("quy cách có ký tự điều khiển", {"quy_cach": "a\x07b"}),
    ],
)
async def test_tao_du_lieu_sai_la_400_va_khong_tao_gi(dang_nhap_admin, db, ten_ca, ghi_de):
    dm = await tao_danh_muc(db, "A")
    db.add(HoatChat(id=1, ten="Hoạt chất 1"))
    await db.flush()
    phan_hoi = await dang_nhap_admin.post(GOC, json=than_tao(dm.id, **ghi_de))
    assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE"), (ten_ca, phan_hoi.text)
    assert (await db.execute(select(func.count()).select_from(SanPham))).scalar_one() == 0


async def test_loi_cheo_truong_chi_dung_truong_cho_giao_dien_gan_vao_o(dang_nhap_admin, db):
    dm = await tao_danh_muc(db, "A")
    phan_hoi = await dang_nhap_admin.post(GOC, json=than_tao(dm.id, loai_san_pham="thuoc_ke_don", la_noi_bat=True))
    assert phan_hoi.json()["chi_tiet"][0]["truong"] == "la_noi_bat"
    phan_hoi = await dang_nhap_admin.post(GOC, json=than_tao(dm.id, dung_dinh_ky=True))
    assert phan_hoi.json()["chi_tiet"][0]["truong"] == "so_ngay_dung_moi_don_vi"


async def test_tham_chieu_khong_ton_tai_hoac_danh_muc_da_xoa_la_400_voi_dung_truong(dang_nhap_admin, db):
    dm = await tao_danh_muc(db, "A")
    da_xoa = await tao_danh_muc(db, "Đã xóa", deleted_at=bay_gio_utc())
    for ghi_de, truong in (
        ({"danh_muc_id": 2_000_000_000}, "danh_muc_id"),
        ({"danh_muc_id": da_xoa.id}, "danh_muc_id"),
        ({"thuong_hieu_id": 999_999}, "thuong_hieu_id"),
        ({"nha_san_xuat_id": 999_999}, "nha_san_xuat_id"),
        ({"thanh_phan": [{"hoat_chat_id": 999_999}]}, "thanh_phan.0.hoat_chat_id"),
    ):
        phan_hoi = await dang_nhap_admin.post(GOC, json={**than_tao(dm.id), **ghi_de})
        assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE"), ghi_de
        assert phan_hoi.json()["chi_tiet"][0]["truong"] == truong, (ghi_de, phan_hoi.json())


async def test_ma_vach_khong_trung_voi_don_vi_cua_san_pham_khac(dang_nhap_admin, db):
    dm = await tao_danh_muc(db, "A")
    don_vi = [{"ten_don_vi": "Viên", "he_so": 1, "gia_ban": "1000", "ma_vach": "8934563138165"}]
    await tao_sp(dang_nhap_admin, dm.id, don_vi=don_vi)
    trung = [
        {"ten_don_vi": "Viên", "he_so": 1, "gia_ban": "1"},
        {"ten_don_vi": "Hộp", "he_so": 10, "gia_ban": "9", "ma_vach": "8934563138165"},
    ]
    phan_hoi = await dang_nhap_admin.post(GOC, json=than_tao(dm.id, don_vi=trung))
    assert la_loi(phan_hoi, 409, "TRUNG_DU_LIEU") and phan_hoi.json()["chi_tiet"] == {"truong": "don_vi.1.ma_vach"}
    assert (await db.execute(select(func.count()).select_from(SanPham))).scalar_one() == 1


# --- Sửa ---------------------------------------------------------------------------------------------------------------


async def test_sua_chi_doi_truong_gui_len_null_la_xoa_gia_tri_tuy_chon_va_doi_phien_ban(dang_nhap_admin, db):
    dm = await tao_danh_muc(db, "A")
    dm2 = await tao_danh_muc(db, "B")
    sp = await tao_sp(dang_nhap_admin, dm.id, quy_cach="Hộp 10 vỉ", so_dang_ky="VD-1", so_luong_toi_da_moi_don=5)
    phan_hoi = await dang_nhap_admin.patch(
        f"{GOC}/{sp['id']}",
        json={
            "phien_ban": sp["phien_ban"],
            "ten": "Tên mới",
            "danh_muc_id": dm2.id,
            "quy_cach": None,
            "la_noi_bat": True,
        },
    )
    assert phan_hoi.status_code == 200, phan_hoi.text
    moi = phan_hoi.json()
    assert (moi["ten"], moi["danh_muc_id"], moi["ten_danh_muc"], moi["quy_cach"], moi["la_noi_bat"]) == (
        "Tên mới",
        dm2.id,
        "B",
        None,
        True,
    )
    assert moi["so_dang_ky"] == "VD-1" and moi["so_luong_toi_da_moi_don"] == 5  # không gửi thì giữ nguyên
    assert moi["phien_ban"] != sp["phien_ban"] and moi["updated_at"] is not None
    ghi = [g for g in await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "sua") if g.bang == "san_pham"]
    assert len(ghi) == 1 and set(ghi[0].gia_tri_moi) == {"ten", "danh_muc_id", "quy_cach", "la_noi_bat"}
    assert ghi[0].gia_tri_cu["quy_cach"] == "Hộp 10 vỉ"


async def test_sua_khong_co_gi_thay_doi_thi_giu_phien_ban_va_khong_ghi_nhat_ky(dang_nhap_admin, db):
    dm = await tao_danh_muc(db, "A")
    sp = await tao_sp(dang_nhap_admin, dm.id, ten="Giữ nguyên")
    truoc = len(await nhat_ky(db, dang_nhap_admin.tai_khoan.id))
    for than in ({}, {"ten": "Giữ nguyên"}, {"ten": "  Giữ   nguyên "}, {"quy_cach": None}):
        phan_hoi = await dang_nhap_admin.patch(f"{GOC}/{sp['id']}", json={"phien_ban": sp["phien_ban"], **than})
        assert phan_hoi.status_code == 200 and phan_hoi.json()["phien_ban"] == sp["phien_ban"], than
    assert len(await nhat_ky(db, dang_nhap_admin.tai_khoan.id)) == truoc


@pytest.mark.parametrize(
    "than",
    [
        {"ten": None},
        {"sku": None},
        {"loai_san_pham": None},
        {"danh_muc_id": None},
        {"trang_thai": None},
        {"la_noi_bat": None},
        {"dung_dinh_ky": None},
        {"ton_toi_thieu": None},
        {"ten": ""},
        {"sku": "A B"},
        {"trang_thai": "xoa"},
        {"don_vi": []},
        {"thanh_phan": []},
        {"anh": []},
        {"don_vi_co_so": "Hộp"},
        {"slug": "x"},
        {"id": 3},
        {"chi_dinh": "Giảm đau"},
        {"lieu_dung_tham_khao": "2 viên/ngày"},
    ],
)
async def test_sua_du_lieu_sai_la_400_va_khong_doi_gi(dang_nhap_admin, db, than):
    dm = await tao_danh_muc(db, "A")
    sp = await tao_sp(dang_nhap_admin, dm.id, ten="Giữ nguyên")
    phan_hoi = await dang_nhap_admin.patch(f"{GOC}/{sp['id']}", json={"phien_ban": sp["phien_ban"], **than})
    assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE"), phan_hoi.text
    assert (await doc_sp(dang_nhap_admin, sp["id"]))["phien_ban"] == sp["phien_ban"]


async def test_sua_thieu_hoac_sai_phien_ban_la_400_va_phien_ban_cu_la_409_voi_ban_hien_tai(dang_nhap_admin, db):
    dm = await tao_danh_muc(db, "A")
    sp = await tao_sp(dang_nhap_admin, dm.id)
    for phien_ban in (None, "", "xyz", "0" * 15, "G" * 16):
        than = {"ten": "X"} | ({} if phien_ban is None else {"phien_ban": phien_ban})
        assert la_loi(await dang_nhap_admin.patch(f"{GOC}/{sp['id']}", json=than), 400, "DU_LIEU_KHONG_HOP_LE"), (
            phien_ban
        )
    dau = await dang_nhap_admin.patch(f"{GOC}/{sp['id']}", json={"phien_ban": sp["phien_ban"], "ten": "Lần một"})
    assert dau.status_code == 200
    cu = await dang_nhap_admin.patch(f"{GOC}/{sp['id']}", json={"phien_ban": sp["phien_ban"], "ten": "Lần hai"})
    assert la_loi(cu, 409, "DU_LIEU_DA_THAY_DOI")
    assert cu.json()["chi_tiet"] == {"phien_ban_hien_tai": dau.json()["phien_ban"]}
    assert (await doc_sp(dang_nhap_admin, sp["id"]))["ten"] == "Lần một"


async def test_phien_ban_phu_thuoc_noi_dung_ca_san_pham_ke_ca_khi_doi_don_vi_thanh_phan_anh(dang_nhap_admin, db):
    """Trang cũ không được ghi đè thay đổi ở tab khác: sửa đơn vị (route riêng) cũng làm lệch `phien_ban` của PATCH."""
    dm = await tao_danh_muc(db, "A")
    sp = await tao_sp(dang_nhap_admin, dm.id)
    don_vi = [
        {
            "id": d["id"],
            "ten_don_vi": d["ten_don_vi"],
            "he_so": d["he_so"],
            "gia_ban": "1234",
            "la_mac_dinh": d["la_mac_dinh"],
        }
        for d in sp["don_vi"]
    ]
    doi = await dang_nhap_admin.put(f"{GOC}/{sp['id']}/don-vi", json={"phien_ban": sp["phien_ban"], "don_vi": don_vi})
    assert doi.status_code == 200 and doi.json()["phien_ban"] != sp["phien_ban"]
    cu = await dang_nhap_admin.patch(f"{GOC}/{sp['id']}", json={"phien_ban": sp["phien_ban"], "ten": "Ghi đè"})
    assert la_loi(cu, 409, "DU_LIEU_DA_THAY_DOI")


async def test_sua_danh_muc_sang_danh_muc_da_xoa_hoac_khong_co_la_400(dang_nhap_admin, db):
    dm = await tao_danh_muc(db, "A")
    da_xoa = await tao_danh_muc(db, "Đã xóa", deleted_at=bay_gio_utc())
    sp = await tao_sp(dang_nhap_admin, dm.id)
    for danh_muc_id in (da_xoa.id, 2_000_000_000):
        phan_hoi = await dang_nhap_admin.patch(
            f"{GOC}/{sp['id']}", json={"phien_ban": sp["phien_ban"], "danh_muc_id": danh_muc_id}
        )
        assert (
            la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE") and phan_hoi.json()["chi_tiet"][0]["truong"] == "danh_muc_id"
        )


async def test_quy_tac_cheo_khi_sua_dung_ca_gia_tri_cu(dang_nhap_admin, db):
    dm = await tao_danh_muc(db, "A")
    noi_bat = await tao_sp(dang_nhap_admin, dm.id, la_noi_bat=True)
    # Đổi loại sang thuốc kê đơn khi đang nổi bật: phải bỏ nổi bật trong cùng yêu cầu.
    phan_hoi = await dang_nhap_admin.patch(
        f"{GOC}/{noi_bat['id']}", json={"phien_ban": noi_bat["phien_ban"], "loai_san_pham": "thuoc_ke_don"}
    )
    assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE") and phan_hoi.json()["chi_tiet"][0]["truong"] == "la_noi_bat"
    ok = await dang_nhap_admin.patch(
        f"{GOC}/{noi_bat['id']}",
        json={"phien_ban": noi_bat["phien_ban"], "loai_san_pham": "thuoc_ke_don", "la_noi_bat": False},
    )
    assert ok.status_code == 200 and ok.json()["loai_san_pham"] == "thuoc_ke_don"
    # Sản phẩm kê đơn rồi thì không bật nổi bật được.
    bat = await dang_nhap_admin.patch(
        f"{GOC}/{noi_bat['id']}", json={"phien_ban": ok.json()["phien_ban"], "la_noi_bat": True}
    )
    assert la_loi(bat, 400, "DU_LIEU_KHONG_HOP_LE")
    # Dùng định kỳ: bật cần số ngày, tắt phải bỏ số ngày.
    dk = await tao_sp(dang_nhap_admin, dm.id, dung_dinh_ky=True, so_ngay_dung_moi_don_vi="7")
    tat = await dang_nhap_admin.patch(f"{GOC}/{dk['id']}", json={"phien_ban": dk["phien_ban"], "dung_dinh_ky": False})
    assert la_loi(tat, 400, "DU_LIEU_KHONG_HOP_LE")
    tat_ok = await dang_nhap_admin.patch(
        f"{GOC}/{dk['id']}", json={"phien_ban": dk["phien_ban"], "dung_dinh_ky": False, "so_ngay_dung_moi_don_vi": None}
    )
    assert tat_ok.status_code == 200 and tat_ok.json()["so_ngay_dung_moi_don_vi"] is None


async def test_doi_sku_trung_la_409_con_doi_hoa_thuong_cua_chinh_no_thi_duoc(dang_nhap_admin, db):
    dm = await tao_danh_muc(db, "A")
    a = await tao_sp(dang_nhap_admin, dm.id, sku="aaa")
    b = await tao_sp(dang_nhap_admin, dm.id, sku="bbb")
    trung = await dang_nhap_admin.patch(f"{GOC}/{b['id']}", json={"phien_ban": b["phien_ban"], "sku": "AAA"})
    assert la_loi(trung, 409, "TRUNG_DU_LIEU") and trung.json()["chi_tiet"] == {"truong": "sku"}
    ok = await dang_nhap_admin.patch(f"{GOC}/{a['id']}", json={"phien_ban": a["phien_ban"], "sku": "Aaa"})
    assert ok.status_code == 200 and ok.json()["sku"] == "AAA"


# --- Đọc, tìm, xóa ----------------------------------------------------------------------------------------------------


async def test_xem_khong_ton_tai_hoac_da_xoa_la_404_id_ngoai_khoang_la_400(dang_nhap_admin, db):
    da_xoa = await tao_san_pham(db, deleted_at=bay_gio_utc())
    for id_ in (da_xoa.id, 2_000_000_000):
        assert la_loi(await dang_nhap_admin.get(f"{GOC}/{id_}"), 404, "KHONG_TIM_THAY")
        assert la_loi(
            await dang_nhap_admin.patch(f"{GOC}/{id_}", json={"phien_ban": "0" * 16, "ten": "X"}), 404, "KHONG_TIM_THAY"
        )
        assert la_loi(
            await dang_nhap_admin.delete(f"{GOC}/{id_}", params={"phien_ban": "0" * 16}), 404, "KHONG_TIM_THAY"
        )
    for id_ in (0, -1, 2_147_483_648):
        assert la_loi(await dang_nhap_admin.get(f"{GOC}/{id_}"), 400, "DU_LIEU_KHONG_HOP_LE")


async def test_danh_sach_loc_tim_sap_xep_va_phan_trang(dang_nhap_admin, db):
    thuoc = await tao_danh_muc(db, "Thuốc", thu_tu=0)
    giam_dau = await tao_danh_muc(db, "Giảm đau", thuoc, thu_tu=0)
    tpcn = await tao_danh_muc(db, "TPCN", thu_tu=1)
    a = await tao_sp(dang_nhap_admin, giam_dau.id, sku="PARA", ten="Paracetamol 500mg")
    b = await tao_sp(dang_nhap_admin, tpcn.id, sku="VITC", ten="Vitamin C Đại Bắc", loai_san_pham="thuc_pham_chuc_nang")
    c = await tao_sp(
        dang_nhap_admin,
        thuoc.id,
        sku="AMOX",
        ten="Amoxicillin",
        loai_san_pham="thuoc_ke_don",
        trang_thai="ngung_kinh_doanh",
    )
    da_xoa = await tao_san_pham(db, ten="Paracetamol cũ", sku="CU", deleted_at=bay_gio_utc())

    async def lay(**tham):
        phan_hoi = await dang_nhap_admin.get(GOC, params=tham)
        assert phan_hoi.status_code == 200, (tham, phan_hoi.text)
        return phan_hoi.json()

    tat_ca = await lay(sap_xep="sku")
    assert [d["sku"] for d in tat_ca["du_lieu"]] == ["AMOX", "PARA", "VITC"] and tat_ca[
        "tong"
    ] == 3  # không có sản phẩm đã xóa
    assert da_xoa.sku not in {d["sku"] for d in tat_ca["du_lieu"]}
    dong = {d["sku"]: d for d in tat_ca["du_lieu"]}["PARA"]
    assert dong["ten_danh_muc"] == "Giảm đau" and dong["gia_mac_dinh"] == "90000.00" and dong["anh_chinh_url"] is None
    assert [d["sku"] for d in (await lay(q="paracetamol"))["du_lieu"]] == ["PARA"]
    assert [d["sku"] for d in (await lay(q="DAI BAC"))["du_lieu"]] == ["VITC"]  # không dấu, không phân biệt hoa thường
    assert [d["sku"] for d in (await lay(q="vitc"))["du_lieu"]] == ["VITC"]  # tìm theo SKU
    assert (await lay(q="%"))["tong"] == 0  # % là chữ thường, không phải ký tự thay thế
    assert [d["sku"] for d in (await lay(loai="thuoc_ke_don"))["du_lieu"]] == ["AMOX"]
    assert [d["sku"] for d in (await lay(trang_thai="ngung_kinh_doanh"))["du_lieu"]] == ["AMOX"]
    assert sorted(d["sku"] for d in (await lay(danh_muc_id=thuoc.id))["du_lieu"]) == [
        "AMOX",
        "PARA",
    ]  # gồm danh mục con
    assert [d["sku"] for d in (await lay(danh_muc_id=giam_dau.id))["du_lieu"]] == ["PARA"]
    assert [d["sku"] for d in (await lay(sap_xep="-ten"))["du_lieu"]] == ["VITC", "PARA", "AMOX"]
    assert [d["sku"] for d in (await lay(sap_xep="created_at"))["du_lieu"]] == [a["sku"], b["sku"], c["sku"]]
    trang_2 = await lay(sap_xep="sku", kich_thuoc=2, trang=2)
    assert [d["sku"] for d in trang_2["du_lieu"]] == ["VITC"] and trang_2["tong"] == 3
    for sai in (
        {"sap_xep": "gia"},
        {"sap_xep": "id"},
        {"loai": "banh"},
        {"trang_thai": "x"},
        {"danh_muc_id": 0},
        {"q": "a\x00b"},
        {"q": "x" * 101},
    ):
        assert (await dang_nhap_admin.get(GOC, params=sai)).status_code == 400, sai


async def test_gia_mac_dinh_la_gia_don_vi_mac_dinh_khong_co_thi_la_don_vi_co_so(dang_nhap_admin, db):
    dm = await tao_danh_muc(db, "A")
    khong_mac_dinh = [
        {"ten_don_vi": "Viên", "he_so": 1, "gia_ban": "1500"},
        {"ten_don_vi": "Hộp", "he_so": 10, "gia_ban": "14000"},
    ]
    await tao_sp(dang_nhap_admin, dm.id, sku="K1", don_vi=khong_mac_dinh)
    await tao_sp(dang_nhap_admin, dm.id, sku="K2")
    gia = {d["sku"]: d["gia_mac_dinh"] for d in (await dang_nhap_admin.get(GOC)).json()["du_lieu"]}
    assert gia == {"K1": "1500.00", "K2": "90000.00"}


async def test_xoa_mem_can_phien_ban_dung_va_ghi_nhat_ky_slug_van_duoc_giu(dang_nhap_admin, db):
    dm = await tao_danh_muc(db, "A")
    sp = await tao_sp(dang_nhap_admin, dm.id, ten="Sắp xóa")
    thieu = await dang_nhap_admin.delete(f"{GOC}/{sp['id']}")
    assert la_loi(thieu, 400, "DU_LIEU_KHONG_HOP_LE")
    cu = await dang_nhap_admin.delete(f"{GOC}/{sp['id']}", params={"phien_ban": "0" * 16})
    assert la_loi(cu, 409, "DU_LIEU_DA_THAY_DOI")
    phan_hoi = await dang_nhap_admin.delete(f"{GOC}/{sp['id']}", params={"phien_ban": sp["phien_ban"]})
    assert phan_hoi.status_code == 204 and phan_hoi.content == b""
    assert la_loi(await dang_nhap_admin.get(f"{GOC}/{sp['id']}"), 404, "KHONG_TIM_THAY")
    dong = await db.get(SanPham, sp["id"])
    await db.refresh(dong)
    assert dong.deleted_at is not None and dong.slug == sp["slug"]
    ghi = [g for g in await nhat_ky(db, dang_nhap_admin.tai_khoan.id, "xoa") if g.bang == "san_pham"]
    assert len(ghi) == 1 and ghi[0].gia_tri_cu["sku"] == sp["sku"]
    moi = await tao_sp(dang_nhap_admin, dm.id, ten="Sắp xóa")
    assert moi["slug"] == "sap-xoa-2"  # slug của sản phẩm đã xóa vẫn giữ chỗ


async def test_khong_xoa_duoc_san_pham_con_lo_co_ton_dang_giu_hoac_biet_tru(dang_nhap_admin, db):
    dm = await tao_danh_muc(db, "A")
    for truong in ({"so_luong": 5}, {"so_luong_biet_tru": 2}, {"so_luong_ton": 3, "so_luong_giu": 1}):
        sp = await tao_sp(dang_nhap_admin, dm.id)
        goc = await db.get(SanPham, sp["id"])
        await tao_lo(db, goc, **truong)
        phan_hoi = await dang_nhap_admin.delete(f"{GOC}/{sp['id']}", params={"phien_ban": sp["phien_ban"]})
        assert la_loi(phan_hoi, 409, "SAN_PHAM_CON_TON_KHO"), truong
        assert (await dang_nhap_admin.get(f"{GOC}/{sp['id']}")).status_code == 200
    het = await tao_sp(dang_nhap_admin, dm.id)
    await tao_lo(db, await db.get(SanPham, het["id"]), so_luong_ton=0)  # lô đã hết hàng không chặn
    assert (
        await dang_nhap_admin.delete(f"{GOC}/{het['id']}", params={"phien_ban": het["phien_ban"]})
    ).status_code == 204


# --- Quyền ---------------------------------------------------------------------------------------------------------------


async def test_chi_admin_dung_duoc_va_token_khach_bi_tu_choi(clients_theo_vai_tro, dang_nhap_khach, client, db):
    dm = await tao_danh_muc(db, "A")
    sp = await tao_san_pham(db, danh_muc_id=dm.id)
    cac_goi = [
        ("get", GOC, None, None),
        ("get", f"{GOC}/{sp.id}", None, None),
        ("post", GOC, than_tao(dm.id), None),
        ("patch", f"{GOC}/{sp.id}", {"phien_ban": "0" * 16, "ten": "X"}, None),
        ("delete", f"{GOC}/{sp.id}", None, {"phien_ban": "0" * 16}),
        ("put", f"{GOC}/{sp.id}/don-vi", {"phien_ban": "0" * 16, "don_vi": []}, None),
        ("put", f"{GOC}/{sp.id}/thanh-phan", {"phien_ban": "0" * 16, "thanh_phan": []}, None),
        ("put", f"{GOC}/{sp.id}/anh/thu-tu", {"phien_ban": "0" * 16, "ids": [1]}, None),
        ("put", f"{GOC}/{sp.id}/anh/1/chinh", {"phien_ban": "0" * 16}, None),
        ("delete", f"{GOC}/{sp.id}/anh/1", None, {"phien_ban": "0" * 16}),
    ]
    for vai_tro in ("PHARMACIST", "WAREHOUSE"):
        c = clients_theo_vai_tro[vai_tro]
        for phuong_thuc, duong, than, tham in cac_goi:
            phan_hoi = await getattr(c, phuong_thuc)(
                duong, **({"json": than} if than else {}), **({"params": tham} if tham else {})
            )
            assert la_loi(phan_hoi, 403, "KHONG_CO_QUYEN"), (vai_tro, phuong_thuc, duong)
    assert (await client.get(GOC)).status_code == 401 and (await dang_nhap_khach.get(GOC)).status_code == 401
    await db.refresh(sp)
    assert sp.deleted_at is None


async def test_product_commercial_manage_cap_ngoai_ad18_van_khong_cho_phep_ghi(clients_theo_vai_tro, db):
    """Lớp phòng thủ thứ hai (QĐ-13): dược sĩ giữ `product.commercial.manage` do cấu hình sai vẫn không ghi được."""
    duoc_si = clients_theo_vai_tro["PHARMACIST"]
    quyen_id = (await db.execute(select(Quyen.id).where(Quyen.ma == "product.commercial.manage"))).scalar_one()
    vai_tro_id = (await db.execute(select(VaiTro.id).where(VaiTro.ma == "PHARMACIST"))).scalar_one()
    db.add(VaiTroQuyen(vai_tro_id=vai_tro_id, quyen_id=quyen_id, gioi_han=None))
    await db.flush()
    phan_quyen.xoa_cache_quyen()
    dm = await tao_danh_muc(db, "A")
    sp = await tao_san_pham(db, danh_muc_id=dm.id)
    so_nhat_ky = (await db.execute(select(func.count()).select_from(NhatKyHeThong))).scalar_one()
    assert (await duoc_si.get(GOC)).status_code == 200  # đọc đi qua guard theo mã quyền
    for phuong_thuc, duong, than, tham in (
        ("post", GOC, than_tao(dm.id), None),
        ("patch", f"{GOC}/{sp.id}", {"phien_ban": "0" * 16, "ten": "X"}, None),
        ("delete", f"{GOC}/{sp.id}", None, {"phien_ban": "0" * 16}),
        ("put", f"{GOC}/{sp.id}/don-vi", {"phien_ban": "0" * 16, "don_vi": [DON_VI_HOP_LE]}, None),
    ):
        phan_hoi = await getattr(duoc_si, phuong_thuc)(
            duong, **({"json": than} if than else {}), **({"params": tham} if tham else {})
        )
        assert la_loi(phan_hoi, 403, "KHONG_CO_QUYEN"), phuong_thuc
    assert (await db.execute(select(func.count()).select_from(NhatKyHeThong))).scalar_one() == so_nhat_ky


# --- Đồng thời ---------------------------------------------------------------------------------------------------------------


async def _admin_va_danh_muc(db_that):
    async with db_that() as s, s.begin():
        admin_id = (await tao_nhan_vien(s, "ADMIN")).id
        dm_id = (await tao_danh_muc(s, "Danh mục")).id
    return admin_id, dm_id


def _tao_than(dm_id, **ghi_de):
    return SanPhamTao.model_validate(than_tao(dm_id, **ghi_de))


@pytest.mark.parametrize(
    ("ghi_de_a", "ghi_de_b", "truong"),
    [
        ({"sku": "dup-1"}, {"sku": "DUP-1"}, "sku"),
        (
            {"don_vi": [{"ten_don_vi": "Viên", "he_so": 1, "gia_ban": "1", "ma_vach": "123456"}]},
            {"don_vi": [{"ten_don_vi": "Viên", "he_so": 1, "gia_ban": "1", "ma_vach": "123456"}]},
            "don_vi.0.ma_vach",
        ),
    ],
)
async def test_hai_admin_tao_trung_sku_hoac_ma_vach_cung_luc_chi_mot_ben_thanh_cong(
    db_that, ghi_de_a, ghi_de_b, truong
):
    admin_id, dm_id = await _admin_va_danh_muc(db_that)

    async def tao_moi(ghi_de):
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, admin_id)
            await dich_vu.tao(s, actor, _tao_than(dm_id, **ghi_de), ip="127.0.0.1")
            await asyncio.sleep(0.3)  # giữ giao dịch mở để bên kia phải chờ khóa

    ket_qua = await asyncio.wait_for(
        asyncio.gather(tao_moi(ghi_de_a), tao_moi(ghi_de_b), return_exceptions=True), timeout=20
    )
    loi = [k for k in ket_qua if k is not None]
    assert len(loi) == 1 and isinstance(loi[0], LoiNghiepVu) and loi[0].ma_loi == "TRUNG_DU_LIEU", ket_qua
    assert loi[0].chi_tiet == {"truong": truong}
    async with db_that() as s:
        assert (await s.execute(select(func.count()).select_from(SanPham))).scalar_one() == 1


async def test_hai_admin_sua_cung_phien_ban_cung_luc_chi_mot_ben_thanh_cong_ben_kia_nhan_409(db_that):
    async with db_that() as s, s.begin():
        admin_id = (await tao_nhan_vien(s, "ADMIN")).id
        dm = await tao_danh_muc(s, "A")
        actor = await s.get(NhanVien, admin_id)
        sp = await dich_vu.tao(s, actor, _tao_than(dm.id), ip="127.0.0.1")
        sp_id, phien_ban = sp.id, sp.phien_ban

    async def sua(ten):
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, admin_id)
            await dich_vu.sua(s, actor, sp_id, SanPhamSua(phien_ban=phien_ban, ten=ten), ip="127.0.0.1")
            await asyncio.sleep(0.3)

    ket_qua = await asyncio.wait_for(asyncio.gather(sua("Bên A"), sua("Bên B"), return_exceptions=True), timeout=20)
    loi = [k for k in ket_qua if k is not None]
    assert len(loi) == 1 and isinstance(loi[0], LoiNghiepVu) and loi[0].ma_loi == "DU_LIEU_DA_THAY_DOI", ket_qua
    async with db_that() as s:
        assert (await s.get(SanPham, sp_id)).ten in ("Bên A", "Bên B")


async def test_gan_san_pham_vao_danh_muc_dang_bi_xoa_mem_thi_cho_roi_bi_tu_choi(db_that):
    """Xóa danh mục khóa dòng `FOR UPDATE`; tạo sản phẩm giữ `FOR SHARE`: bên sau phải chờ rồi thấy kết quả của bên trước."""
    from app.modules.san_pham import danh_muc as dich_vu_danh_muc

    admin_id, dm_id = await _admin_va_danh_muc(db_that)
    dang_xoa = asyncio.Event()

    async def xoa_danh_muc():
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, admin_id)
            await dich_vu_danh_muc.xoa(s, actor, dm_id, ip="127.0.0.1")
            dang_xoa.set()
            await asyncio.sleep(0.4)  # chưa commit

    async def tao_san_pham_moi():
        await dang_xoa.wait()
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, admin_id)
            await dich_vu.tao(s, actor, _tao_than(dm_id), ip="127.0.0.1")

    ket_qua = await asyncio.wait_for(
        asyncio.gather(xoa_danh_muc(), tao_san_pham_moi(), return_exceptions=True), timeout=20
    )
    assert ket_qua[0] is None
    assert isinstance(ket_qua[1], LoiNghiepVu) and ket_qua[1].ma_loi == "DU_LIEU_KHONG_HOP_LE", ket_qua
    assert ket_qua[1].chi_tiet[0]["truong"] == "danh_muc_id"
    async with db_that() as s:
        assert (await s.execute(select(func.count()).select_from(SanPham))).scalar_one() == 0
        assert (await s.get(DanhMuc, dm_id)).deleted_at is not None


async def test_xoa_danh_muc_cho_giao_dich_dang_tao_san_pham_roi_thay_san_pham_va_tu_choi(db_that):
    from app.modules.san_pham import danh_muc as dich_vu_danh_muc

    admin_id, dm_id = await _admin_va_danh_muc(db_that)
    dang_tao = asyncio.Event()

    async def tao_san_pham_moi():
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, admin_id)
            await dich_vu.tao(s, actor, _tao_than(dm_id), ip="127.0.0.1")
            dang_tao.set()
            await asyncio.sleep(0.4)  # chưa commit

    async def xoa_danh_muc():
        await dang_tao.wait()
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, admin_id)
            await dich_vu_danh_muc.xoa(s, actor, dm_id, ip="127.0.0.1")

    ket_qua = await asyncio.wait_for(
        asyncio.gather(tao_san_pham_moi(), xoa_danh_muc(), return_exceptions=True), timeout=20
    )
    assert ket_qua[0] is None
    assert isinstance(ket_qua[1], LoiNghiepVu) and ket_qua[1].ma_loi == "DANH_MUC_CON_SAN_PHAM", ket_qua
    async with db_that() as s:
        assert (await s.get(DanhMuc, dm_id)).deleted_at is None


async def test_xoa_san_pham_dua_voi_nhap_kho_vao_lo_san_co_khong_de_ton_ket_duoi_san_pham_da_xoa(db_that):
    """Xóa đọc "không còn hàng" rồi mới commit; nhập kho vào lô sẵn có (tồn 0) chen giữa phải thua chứ không để tồn mắc kẹt."""
    from app.modules.kho import ton_kho

    admin_id, dm_id = await _admin_va_danh_muc(db_that)
    async with db_that() as s, s.begin():
        actor = await s.get(NhanVien, admin_id)
        sp = await dich_vu.tao(s, actor, _tao_than(dm_id), ip="127.0.0.1")
        sp_id, phien_ban = sp.id, sp.phien_ban
        lo_id = (await tao_lo(s, await s.get(SanPham, sp_id))).id  # lô có sẵn, tồn 0
    dang_xoa = asyncio.Event()

    async def xoa():
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, admin_id)
            await dich_vu.xoa(s, actor, sp_id, phien_ban, ip="127.0.0.1")
            dang_xoa.set()
            await asyncio.sleep(0.5)  # đã đánh dấu xóa, chưa commit

    async def nhap():
        await dang_xoa.wait()
        async with db_that() as s, s.begin():
            lo = await s.get(LoThuoc, lo_id)
            await ton_kho.nhap_kho(s, lo, 100, ton_kho.ChungTu("phieu_nhap", 0))

    ket_qua = await asyncio.wait_for(asyncio.gather(xoa(), nhap(), return_exceptions=True), timeout=20)
    assert ket_qua[0] is None
    assert isinstance(ket_qua[1], LoiNghiepVu) and ket_qua[1].ma_loi == "KHONG_TIM_THAY", ket_qua
    async with db_that() as s:
        assert (await s.get(SanPham, sp_id)).deleted_at is not None
        assert (await s.get(LoThuoc, lo_id)).so_luong_ton == 0


async def test_nhap_kho_vao_lo_dang_giu_khoa_thi_xoa_san_pham_cho_roi_bi_tu_choi(db_that):
    from app.modules.kho import ton_kho

    admin_id, dm_id = await _admin_va_danh_muc(db_that)
    async with db_that() as s, s.begin():
        actor = await s.get(NhanVien, admin_id)
        sp = await dich_vu.tao(s, actor, _tao_than(dm_id), ip="127.0.0.1")
        sp_id, phien_ban = sp.id, sp.phien_ban
        lo_id = (await tao_lo(s, await s.get(SanPham, sp_id))).id
    dang_nhap = asyncio.Event()

    async def nhap():
        async with db_that() as s, s.begin():
            lo = await s.get(LoThuoc, lo_id)
            await ton_kho.nhap_kho(s, lo, 100, ton_kho.ChungTu("phieu_nhap", 0))
            dang_nhap.set()
            await asyncio.sleep(0.5)  # chưa commit

    async def xoa():
        await dang_nhap.wait()
        async with db_that() as s, s.begin():
            actor = await s.get(NhanVien, admin_id)
            await dich_vu.xoa(s, actor, sp_id, phien_ban, ip="127.0.0.1")

    ket_qua = await asyncio.wait_for(asyncio.gather(nhap(), xoa(), return_exceptions=True), timeout=20)
    assert ket_qua[0] is None
    assert isinstance(ket_qua[1], LoiNghiepVu) and ket_qua[1].ma_loi == "SAN_PHAM_CON_TON_KHO", ket_qua
    async with db_that() as s:
        assert (await s.get(SanPham, sp_id)).deleted_at is None


async def test_nhap_kho_vao_lo_cua_san_pham_da_xoa_bi_tu_choi_va_khong_ghi_the_kho(db):
    from app.models.kho import BienDongKho
    from app.modules.kho import ton_kho

    sp = await tao_san_pham(db, deleted_at=bay_gio_utc())
    lo = await tao_lo(db, sp)
    with pytest.raises(LoiNghiepVu) as loi:
        await ton_kho.nhap_kho(db, lo, 5, ton_kho.ChungTu("phieu_nhap", 0))
    assert loi.value.ma_loi == "KHONG_TIM_THAY"
    assert (
        await db.execute(select(func.count()).select_from(BienDongKho).where(BienDongKho.lo_id == lo.id))
    ).scalar_one() == 0


async def test_ma_vach_cua_san_pham_da_xoa_dung_lai_duoc_con_san_pham_dang_ban_thi_van_chan(dang_nhap_admin, db):
    dm = await tao_danh_muc(db, "A")
    vach = [{"ten_don_vi": "Viên", "he_so": 1, "gia_ban": "1", "ma_vach": "893000111"}]
    cu = await tao_sp(dang_nhap_admin, dm.id, don_vi=vach)
    xoa = await dang_nhap_admin.delete(f"{GOC}/{cu['id']}", params={"phien_ban": cu["phien_ban"]})
    assert xoa.status_code == 204
    moi = await dang_nhap_admin.post(GOC, json=than_tao(dm.id, don_vi=vach))  # xóa là cuối cùng: mã vạch được trả lại
    assert moi.status_code == 201, moi.text
    trung = await dang_nhap_admin.post(GOC, json=than_tao(dm.id, don_vi=vach))  # nhưng chủ mới thì vẫn giữ chỗ
    assert la_loi(trung, 409, "TRUNG_DU_LIEU") and trung.json()["chi_tiet"] == {"truong": "don_vi.0.ma_vach"}


async def test_tao_san_pham_dua_voi_xoa_thuong_hieu_xoa_phai_cho_roi_bi_tu_choi_khong_bao_gio_500(db_that):
    """Kiểm tra "thương hiệu tồn tại" giữ khóa `FOR SHARE`: xóa chen giữa kiểm tra và ghi không còn gây `IntegrityError`."""
    from sqlalchemy import text

    from app.modules.san_pham import du_lieu_chung

    async with db_that() as s, s.begin():
        admin_id = (await tao_nhan_vien(s, "ADMIN")).id
        dm_id = (await tao_danh_muc(s, "A")).id
        th = ThuongHieu(ten="Hãng X")
        s.add(th)
        await s.flush()
        th_id = th.id
    than = than_tao(dm_id, thuong_hieu_id=th_id)
    than["don_vi"][0]["ma_vach"] = "8930000001"  # buộc đi qua khóa tư vấn mã vạch, SAU bước kiểm tra thương hiệu
    du_lieu = SanPhamTao.model_validate(than)

    async with db_that() as giu, db_that() as a, db_that() as b:
        await giu.begin()
        await giu.execute(text("SELECT pg_advisory_xact_lock(hashtext('nha_thuoc.san_pham.ma_vach'))"))
        await a.begin()
        await b.begin()
        viec_tao = asyncio.create_task(dich_vu.tao(a, await a.get(NhanVien, admin_id), du_lieu, ip="1.1.1.1"))
        await asyncio.sleep(0.5)
        assert not viec_tao.done()  # A đã kiểm tra thương hiệu rồi dừng ở khóa mã vạch
        viec_xoa = asyncio.create_task(
            du_lieu_chung.xoa(b, await b.get(NhanVien, admin_id), du_lieu_chung.THUONG_HIEU, th_id, ip="1.1.1.1")
        )
        await asyncio.sleep(0.5)
        assert not viec_xoa.done(), "xóa phải chờ khóa FOR SHARE của giao dịch tạo sản phẩm"
        await giu.commit()
        await asyncio.wait_for(viec_tao, 5)
        await a.commit()
        with pytest.raises(LoiNghiepVu) as loi:
            await asyncio.wait_for(viec_xoa, 5)
        assert loi.value.ma_loi == "DU_LIEU_DANG_DUOC_SU_DUNG"
        await b.rollback()
    async with db_that() as s:
        assert (
            await s.execute(select(func.count()).select_from(SanPham).where(SanPham.thuong_hieu_id == th_id))
        ).scalar_one() == 1


async def test_don_vi_gia_le_trong_db_khong_lam_hong_doc_chi_tiet_va_danh_sach(dang_nhap_admin, db):
    """DB cho phép NUMERIC(14,2): dòng nhập ngoài API (1000.50) phải đọc được, chỉ đầu VÀO mới đòi số đồng nguyên."""
    from sqlalchemy import update

    from app.models.san_pham import DonViQuyDoi

    dm = await tao_danh_muc(db, "A")
    sp = await tao_sp(dang_nhap_admin, dm.id)
    await db.execute(
        update(DonViQuyDoi).where(DonViQuyDoi.id == sp["don_vi"][0]["id"]).values(gia_ban=Decimal("1000.50"))
    )
    chi_tiet = await dang_nhap_admin.get(f"{GOC}/{sp['id']}")
    assert chi_tiet.status_code == 200, chi_tiet.text
    assert chi_tiet.json()["don_vi"][0]["gia_ban"] == "1000.50"
    # Đơn vị mặc định là Hộp (90000); bỏ cờ mặc định để giá hiển thị ở danh sách là giá lẻ của đơn vị cơ sở.
    await db.execute(update(DonViQuyDoi).where(DonViQuyDoi.san_pham_id == sp["id"]).values(la_mac_dinh=False))
    ds = await dang_nhap_admin.get(GOC)
    assert ds.status_code == 200, ds.text
    assert ds.json()["du_lieu"][0]["gia_mac_dinh"] == "1000.50"


@pytest.mark.parametrize(
    ("truong", "gia_tri"),
    [
        ("don_vi", [{"ten_don_vi": f"Đơn vị {i}", "he_so": i + 1, "gia_ban": "1"} for i in range(51)]),
        ("thanh_phan", [{"hoat_chat_id": i + 1} for i in range(51)]),
    ],
)
async def test_danh_sach_don_vi_va_thanh_phan_co_gioi_han_do_dai(dang_nhap_admin, db, truong, gia_tri):
    dm = await tao_danh_muc(db, "A")
    phan_hoi = await dang_nhap_admin.post(GOC, json=than_tao(dm.id, **{truong: gia_tri}))
    assert la_loi(phan_hoi, 400, "DU_LIEU_KHONG_HOP_LE") and phan_hoi.json()["chi_tiet"][0]["truong"] == truong

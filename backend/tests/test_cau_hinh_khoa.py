"""core/cau_hinh_khoa.py: kiểu và giới hạn của từng khóa `cau_hinh` do AD08 quản lý (spec 02 mục 6)."""

import re
from pathlib import Path

import pytest

from app.core.cau_hinh_khoa import KHOA_CAU_HINH, dau_van_tay, kiem_tra_gia_tri
from app.core.loi import LoiNghiepVu
from app.seed.co_ban import CAU_HINH_MAC_DINH

KHOA_AD09 = {"ai_module", "ai_dau_hieu_nguy_hiem", "ai_nguong_chuyen_duoc_si", "ai_loi_nhac_bo_sung"}
SPEC_02 = (Path(__file__).resolve().parents[2] / "docs" / "spec" / "02-database.md").read_text(encoding="utf-8")


def loi_cua(khoa, gia_tri) -> list[dict]:
    with pytest.raises(LoiNghiepVu) as loi:
        kiem_tra_gia_tri(khoa, gia_tri)
    assert loi.value.ma_loi == "DU_LIEU_KHONG_HOP_LE"
    return loi.value.chi_tiet


def test_bang_khoa_gom_dung_cac_khoa_seed_tru_bon_khoa_ai_cua_ad09():
    khoa_seed = {k for k, _, _ in CAU_HINH_MAC_DINH}
    assert set(KHOA_CAU_HINH) == khoa_seed - KHOA_AD09
    assert khoa_seed >= KHOA_AD09 and not (KHOA_AD09 & set(KHOA_CAU_HINH))


@pytest.mark.parametrize(("khoa", "mac_dinh"), [(k, v) for k, v, _ in CAU_HINH_MAC_DINH if k not in KHOA_AD09])
def test_moi_gia_tri_mac_dinh_cua_seed_hop_le_voi_chinh_bang_khoa(khoa, mac_dinh):
    """Nếu Admin lưu lại đúng giá trị mặc định mà bị từ chối thì bảng giới hạn sai."""
    assert kiem_tra_gia_tri(khoa, mac_dinh) == (
        {**mac_dinh, "ngay_trong_tuan": sorted(mac_dinh["ngay_trong_tuan"])}
        if khoa == "gio_lam_viec_duoc_si"
        else mac_dinh
    )


def test_moi_khoa_co_nhom_nhan_va_don_vi_de_giao_dien_dung():
    for khoa, k in KHOA_CAU_HINH.items():
        assert k.khoa == khoa and k.nhom.strip() and k.nhan.strip(), khoa
        assert k.kieu in {"so", "tien", "nhom_so", "gio_lam_viec"}, khoa
        if k.kieu in {"so", "tien"}:
            assert k.toi_thieu is not None and k.toi_da is not None and k.toi_thieu <= k.toi_da, khoa
        if k.kieu == "nhom_so":
            assert k.truong and all(t.nhan.strip() and t.toi_thieu <= t.toi_da for t in k.truong), khoa


def _so(chuoi: str) -> int:
    return int(chuoi.replace(".", ""))


def test_gioi_han_trong_code_khop_bang_o_spec_02():
    """Spec là nguồn sự thật: mỗi khóa có đúng một dòng ở bảng "Kiểu và giới hạn" và các con số khớp với code."""
    phan = SPEC_02.split("| Khóa | Nhóm (chủ đề hiển thị) | Kiểu | Giới hạn |")[1].split("\n\n")[0]
    dong_spec = {m.group(1): m.group(0) for m in re.finditer(r"^\| `(\w+)` \|.*$", phan, re.MULTILINE)}
    assert set(dong_spec) == set(KHOA_CAU_HINH)
    for khoa, k in KHOA_CAU_HINH.items():
        dong = dong_spec[khoa]
        assert f"| {k.nhom} |" in dong, khoa
        so_trong_spec = [_so(m) for m in re.findall(r"(\d[\d.]*) đến (\d[\d.]*)", dong) for m in m]
        if k.kieu in {"so", "tien"}:
            assert so_trong_spec[:2] == [k.toi_thieu, k.toi_da], khoa
        elif k.kieu == "nhom_so":
            assert so_trong_spec == [x for t in k.truong for x in (t.toi_thieu, t.toi_da)], khoa
            assert all(f"`{t.ten}`" in dong for t in k.truong), khoa


# --- Số nguyên và tiền --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("khoa", [k for k, v in KHOA_CAU_HINH.items() if v.kieu in {"so", "tien"}])
def test_so_nhan_dung_hai_dau_khoang_va_tu_choi_ngoai_khoang(khoa):
    k = KHOA_CAU_HINH[khoa]
    assert kiem_tra_gia_tri(khoa, k.toi_thieu) == k.toi_thieu
    assert kiem_tra_gia_tri(khoa, k.toi_da) == k.toi_da
    for sai in (k.toi_thieu - 1, k.toi_da + 1):
        chi_tiet = loi_cua(khoa, sai)
        assert chi_tiet[0]["truong"] == "gia_tri" and str(k.toi_thieu).replace(".", "") in chi_tiet[0]["loi"].replace(
            ".", ""
        )


@pytest.mark.parametrize(
    "sai", [True, False, 5.0, 5.5, "5", "", None, [], {}, [5], {"a": 5}, float("nan"), float("inf")]
)
def test_so_chi_nhan_so_nguyen_that_khong_nhan_bool_so_thuc_chuoi_hay_null(sai):
    loi_cua("nguong_can_han_ngay", sai)


def test_so_rat_lon_khong_lam_tran_va_bi_tu_choi_dung_cach():
    loi_cua("nguong_can_han_ngay", 10**30)
    loi_cua("phi_ship_mac_dinh", -(10**30))


# --- Nhóm số (gioi_han_otp, gioi_han_ai) --------------------------------------------------------------------------------


def test_nhom_so_dung_hop_le():
    gia_tri = {"moi_sdt_moi_gio": 3, "moi_ip_moi_gio": 50}
    assert kiem_tra_gia_tri("gioi_han_otp", gia_tri) == gia_tri


def test_nhom_so_bao_loi_theo_tung_truong():
    chi_tiet = loi_cua("gioi_han_otp", {"moi_sdt_moi_gio": 0, "moi_ip_moi_gio": 9999})
    assert {c["truong"] for c in chi_tiet} == {"gia_tri.moi_sdt_moi_gio", "gia_tri.moi_ip_moi_gio"}


def test_nhom_so_thieu_va_thua_truong():
    thieu = loi_cua("gioi_han_otp", {"moi_sdt_moi_gio": 3})
    assert [c["truong"] for c in thieu] == ["gia_tri.moi_ip_moi_gio"]
    thua = loi_cua("gioi_han_otp", {"moi_sdt_moi_gio": 3, "moi_ip_moi_gio": 5, "mat_khau": "x"})
    assert [c["truong"] for c in thua] == ["gia_tri.mat_khau"]


@pytest.mark.parametrize("sai", [5, "x", None, [], [1, 2], True])
def test_nhom_so_phai_la_doi_tuong(sai):
    assert loi_cua("gioi_han_ai", sai)[0]["truong"] == "gia_tri"


def test_nhom_so_truong_sai_kieu():
    chi_tiet = loi_cua(
        "gioi_han_ai", {"chat_moi_phien": True, "chat_moi_ip_moi_ngay": 1.5, "tra_anh_moi_ip_moi_ngay": "3"}
    )
    assert len(chi_tiet) == 3


# --- Giờ làm việc ---------------------------------------------------------------------------------------------------------


def lam_viec(**sua):
    return {"bat_dau": "08:00", "ket_thuc": "21:00", "ngay_trong_tuan": [1, 2, 3, 4, 5], **sua}


def test_gio_lam_viec_hop_le_va_sap_xep_ngay():
    assert kiem_tra_gia_tri("gio_lam_viec_duoc_si", lam_viec(ngay_trong_tuan=[5, 1, 3]))["ngay_trong_tuan"] == [1, 3, 5]
    assert kiem_tra_gia_tri("gio_lam_viec_duoc_si", lam_viec(bat_dau="00:00", ket_thuc="23:59"))


# Có cả chữ số Ả Rập ở từng vị trí: `\d` của `re` nhận chúng, `[0-9]` thì không.
@pytest.mark.parametrize(
    "gio",
    ["8:00", "24:00", "08:60", "08:00:00", "0800", "", "ab:cd", "08-00", None, 8, "٠٨:٠٠", "0٨:00", "08:٥٩", "23:5٩"],
)
def test_gio_sai_dinh_dang(gio):
    assert loi_cua("gio_lam_viec_duoc_si", lam_viec(bat_dau=gio))[0]["truong"] == "gia_tri.bat_dau"
    assert loi_cua("gio_lam_viec_duoc_si", lam_viec(ket_thuc=gio))[0]["truong"] == "gia_tri.ket_thuc"


@pytest.mark.parametrize(("bat_dau", "ket_thuc"), [("21:00", "08:00"), ("08:00", "08:00")])
def test_bat_dau_phai_truoc_ket_thuc(bat_dau, ket_thuc):
    chi_tiet = loi_cua("gio_lam_viec_duoc_si", lam_viec(bat_dau=bat_dau, ket_thuc=ket_thuc))
    assert chi_tiet[0]["truong"] == "gia_tri.ket_thuc"


@pytest.mark.parametrize("ngay", [[], [0], [8], [1, 1], ["1"], [True], [1.5], "1,2", None, 3, [[1]]])
def test_ngay_trong_tuan_sai(ngay):
    assert loi_cua("gio_lam_viec_duoc_si", lam_viec(ngay_trong_tuan=ngay))[0]["truong"] == "gia_tri.ngay_trong_tuan"


def test_gio_lam_viec_thieu_va_thua_truong():
    assert [c["truong"] for c in loi_cua("gio_lam_viec_duoc_si", {"bat_dau": "08:00"})] == [
        "gia_tri.ket_thuc",
        "gia_tri.ngay_trong_tuan",
    ]
    assert "gia_tri.khac" in [c["truong"] for c in loi_cua("gio_lam_viec_duoc_si", lam_viec(khac=1))]


# --- Khóa không quản lý ---------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("khoa", ["ai_module", "ai_loi_nhac_bo_sung", "khong_co_khoa_nay", "", "NGUONG_CAN_HAN_NGAY"])
def test_khoa_ngoai_bang_la_khong_tim_thay(khoa):
    with pytest.raises(LoiNghiepVu) as loi:
        kiem_tra_gia_tri(khoa, 1)
    assert loi.value.ma_loi == "KHONG_TIM_THAY"


# --- Dấu vân tay ---------------------------------------------------------------------------------------------------------


def test_dau_van_tay_phu_thuoc_noi_dung_khong_phu_thuoc_thu_tu_khoa():
    a = dau_van_tay({"x": 1, "y": [1, 2]})
    assert a == dau_van_tay({"y": [1, 2], "x": 1}) and re.fullmatch(r"[0-9a-f]{16}", a)
    assert a != dau_van_tay({"x": 1, "y": [2, 1]}) and a != dau_van_tay({"x": 2, "y": [1, 2]})
    assert dau_van_tay(None) != dau_van_tay(0) != dau_van_tay("0") != dau_van_tay(False)

"""Kiểu, giới hạn và nhóm hiển thị của từng khóa trong `cau_hinh` do AD08 quản lý (spec 02 mục 6).

Một nguồn duy nhất cho cả giao diện (ô nhập dựng từ metadata) lẫn kiểm tra phía máy chủ: Admin sửa cấu hình lúc chạy mà
các nơi dùng (`dang_nhap`, `otp`, hạn thanh toán...) đọc thẳng giá trị và ép kiểu, nên một giá trị sai (âm, 0, chuỗi)
sẽ làm đăng nhập hay đặt hàng lỗi hàng loạt. Test đối chiếu bảng này với bảng ở spec 02 và với mọi giá trị
mặc định của seed.

Bốn khóa `ai_*` (module, dấu hiệu nguy hiểm, ngưỡng chuyển dược sĩ, lời nhắc bổ sung) thuộc AD09 (`ai.config`)
nên không có ở đây.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Literal

from app.core.loi import LoiNghiepVu

KieuCauHinh = Literal["so", "tien", "nhom_so", "gio_lam_viec"]

_GIO = re.compile(r"([01][0-9]|2[0-3]):[0-5][0-9]")  # [0-9] chứ không phải \d: \d nhận cả chữ số Ả Rập, Devanagari...


@dataclass(frozen=True)
class TruongSo:
    """Một trường số nguyên trong khóa dạng nhóm (`gioi_han_otp`, `gioi_han_ai`)."""

    ten: str
    nhan: str
    toi_thieu: int
    toi_da: int
    don_vi: str | None = None


@dataclass(frozen=True)
class KhoaCauHinh:
    khoa: str
    nhom: str
    nhan: str
    kieu: KieuCauHinh
    don_vi: str | None = None
    toi_thieu: int | None = None
    toi_da: int | None = None
    truong: tuple[TruongSo, ...] = ()


def _so(khoa: str, nhom: str, nhan: str, don_vi: str, toi_thieu: int, toi_da: int) -> KhoaCauHinh:
    return KhoaCauHinh(khoa, nhom, nhan, "so", don_vi, toi_thieu, toi_da)


def _tien(khoa: str, nhom: str, nhan: str, toi_thieu: int, toi_da: int) -> KhoaCauHinh:
    return KhoaCauHinh(khoa, nhom, nhan, "tien", "đồng", toi_thieu, toi_da)


_DANH_SACH: tuple[KhoaCauHinh, ...] = (
    _so("nguong_can_han_ngay", "Hàng và hạn dùng", "Ngưỡng cận hạn", "ngày", 1, 730),
    _so("han_su_dung_toi_thieu_nhap_ngay", "Hàng và hạn dùng", "Hạn dùng tối thiểu khi nhập kho", "ngày", 1, 1095),
    _so("thoi_han_thanh_toan_phut", "Đơn hàng và thanh toán", "Thời hạn thanh toán", "phút", 5, 1440),
    _so("thoi_han_khach_xac_nhan_gio", "Đơn hàng và thanh toán", "Thời hạn khách xác nhận đơn", "giờ", 1, 168),
    _so("thoi_han_doi_tra_ngay", "Đơn hàng và thanh toán", "Thời hạn đổi trả", "ngày", 1, 365),
    _so("thoi_han_nhan_tai_quay_ngay", "Đơn hàng và thanh toán", "Thời hạn nhận hàng tại quầy", "ngày", 1, 30),
    _so("thoi_gian_khoa_don_thuoc_phut", "Đơn thuốc", "Thời gian khóa yêu cầu đơn thuốc", "phút", 5, 240),
    _so("hieu_luc_don_thuoc_ngay", "Đơn thuốc", "Hiệu lực của đơn thuốc", "ngày", 1, 365),
    _tien("phi_ship_mac_dinh", "Vận chuyển", "Phí vận chuyển mặc định", 0, 1_000_000),
    _tien("mien_phi_ship_tu", "Vận chuyển", "Miễn phí vận chuyển từ", 0, 100_000_000),
    _so("so_lan_dang_nhap_sai_toi_da", "Bảo mật đăng nhập", "Số lần đăng nhập sai tối đa", "lần", 3, 20),
    _so(
        "thoi_gian_khoa_dang_nhap_phut",
        "Bảo mật đăng nhập",
        "Thời gian khóa tạm sau khi đăng nhập sai",
        "phút",
        1,
        1440,
    ),
    KhoaCauHinh(
        "gioi_han_otp",
        "Bảo mật đăng nhập",
        "Giới hạn gửi mã OTP",
        "nhom_so",
        truong=(
            TruongSo("moi_sdt_moi_gio", "Mỗi số điện thoại mỗi giờ", 1, 20, "lần"),
            TruongSo("moi_ip_moi_gio", "Mỗi địa chỉ IP mỗi giờ", 1, 200, "lần"),
        ),
    ),
    KhoaCauHinh(
        "gioi_han_ai",
        "Giới hạn dùng AI",
        "Giới hạn lượt dùng AI của khách",
        "nhom_so",
        truong=(
            TruongSo("chat_moi_phien", "Tin nhắn chat mỗi phiên", 1, 500, "tin"),
            TruongSo("chat_moi_ip_moi_ngay", "Tin nhắn chat mỗi IP mỗi ngày", 1, 5000, "tin"),
            TruongSo("tra_anh_moi_ip_moi_ngay", "Lượt tra cứu ảnh mỗi IP mỗi ngày", 1, 500, "lượt"),
        ),
    ),
    KhoaCauHinh("gio_lam_viec_duoc_si", "Giờ làm việc", "Giờ làm việc của dược sĩ", "gio_lam_viec"),
)

KHOA_CAU_HINH: dict[str, KhoaCauHinh] = {k.khoa: k for k in _DANH_SACH}
"""Theo đúng thứ tự hiển thị: nhóm xuất hiện lần đầu ở đâu thì đứng ở đó."""

TRUONG_GIO_LAM_VIEC = ("bat_dau", "ket_thuc", "ngay_trong_tuan")


def _khoang(toi_thieu: int, toi_da: int, don_vi: str | None) -> str:
    def dinh_dang(n: int) -> str:
        return f"{n:,}".replace(",", ".")

    them = f" {don_vi}" if don_vi else ""
    return f"Phải là số nguyên từ {dinh_dang(toi_thieu)} đến {dinh_dang(toi_da)}{them}"


def _la_so_nguyen(gia_tri: Any) -> bool:
    return type(gia_tri) is int  # loại bool (kế thừa int), số thực (kể cả 5.0) và chuỗi


def _kiem_tra_so(gia_tri: Any, toi_thieu: int, toi_da: int, don_vi: str | None, truong: str, loi: list[dict[str, str]]):
    if not _la_so_nguyen(gia_tri) or not toi_thieu <= gia_tri <= toi_da:
        loi.append({"truong": truong, "loi": _khoang(toi_thieu, toi_da, don_vi)})
        return None
    return gia_tri


def _kiem_tra_nhom_so(k: KhoaCauHinh, gia_tri: Any, loi: list[dict[str, str]]) -> dict[str, int] | None:
    if not isinstance(gia_tri, dict):
        loi.append(
            {"truong": "gia_tri", "loi": "Phải là đối tượng gồm các trường: " + ", ".join(t.ten for t in k.truong)}
        )
        return None
    ket_qua: dict[str, int] = {}
    for t in k.truong:
        if t.ten not in gia_tri:
            loi.append({"truong": f"gia_tri.{t.ten}", "loi": "Thiếu trường này"})
        elif (so := _kiem_tra_so(gia_tri[t.ten], t.toi_thieu, t.toi_da, t.don_vi, f"gia_tri.{t.ten}", loi)) is not None:
            ket_qua[t.ten] = so
    loi.extend(
        {"truong": f"gia_tri.{ten}", "loi": "Không có trường này"}
        for ten in gia_tri
        if ten not in {t.ten for t in k.truong}
    )
    return ket_qua


def _kiem_tra_gio_lam_viec(gia_tri: Any, loi: list[dict[str, str]]) -> dict[str, Any] | None:
    if not isinstance(gia_tri, dict):
        loi.append({"truong": "gia_tri", "loi": "Phải là đối tượng gồm các trường: " + ", ".join(TRUONG_GIO_LAM_VIEC)})
        return None
    ket_qua: dict[str, Any] = {}
    gio_hop_le: dict[str, str] = {}
    for ten in ("bat_dau", "ket_thuc"):
        if ten not in gia_tri:
            loi.append({"truong": f"gia_tri.{ten}", "loi": "Thiếu trường này"})
        elif not isinstance(gia_tri[ten], str) or not _GIO.fullmatch(gia_tri[ten]):
            loi.append({"truong": f"gia_tri.{ten}", "loi": "Phải có dạng HH:MM, từ 00:00 đến 23:59"})
        else:
            gio_hop_le[ten] = ket_qua[ten] = gia_tri[ten]
    if (
        len(gio_hop_le) == 2 and gio_hop_le["bat_dau"] >= gio_hop_le["ket_thuc"]
    ):  # "HH:MM" so sánh chuỗi đúng thứ tự giờ
        loi.append(
            {"truong": "gia_tri.ket_thuc", "loi": "Giờ kết thúc phải sau giờ bắt đầu (ca qua nửa đêm chưa hỗ trợ)"}
        )
    ngay = gia_tri.get("ngay_trong_tuan")
    if "ngay_trong_tuan" not in gia_tri:
        loi.append({"truong": "gia_tri.ngay_trong_tuan", "loi": "Thiếu trường này"})
    elif (
        not isinstance(ngay, list)
        or not ngay
        or not all(_la_so_nguyen(n) and 1 <= n <= 7 for n in ngay)
        or len(set(ngay)) != len(ngay)
    ):
        loi.append(
            {
                "truong": "gia_tri.ngay_trong_tuan",
                "loi": "Phải là danh sách không rỗng, không trùng, mỗi ngày từ 1 (thứ hai) đến 7 (chủ nhật)",
            }
        )
    else:
        ket_qua["ngay_trong_tuan"] = sorted(ngay)
    loi.extend(
        {"truong": f"gia_tri.{ten}", "loi": "Không có trường này"} for ten in gia_tri if ten not in TRUONG_GIO_LAM_VIEC
    )
    return ket_qua


def kiem_tra_gia_tri(khoa: str, gia_tri: Any) -> Any:
    """Giá trị đã chuẩn hóa của `khoa`, hoặc `LoiNghiepVu`: `DU_LIEU_KHONG_HOP_LE` (kèm lỗi theo từng trường) hay
    `KHONG_TIM_THAY` (khóa không do AD08 quản lý)."""
    k = KHOA_CAU_HINH.get(khoa)
    if k is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy khóa cấu hình")
    loi: list[dict[str, str]] = []
    if k.kieu in {"so", "tien"}:
        ket_qua: Any = _kiem_tra_so(gia_tri, k.toi_thieu or 0, k.toi_da or 0, k.don_vi, "gia_tri", loi)
    elif k.kieu == "nhom_so":
        ket_qua = _kiem_tra_nhom_so(k, gia_tri, loi)
    else:
        ket_qua = _kiem_tra_gio_lam_viec(gia_tri, loi)
    if loi:
        raise LoiNghiepVu("DU_LIEU_KHONG_HOP_LE", "Dữ liệu không hợp lệ", chi_tiet=loi)
    return ket_qua


def dau_van_tay(gia_tri: Any) -> str:
    """16 ký tự hex đại diện cho NỘI DUNG của một giá trị JSON (không phụ thuộc thứ tự khóa, số lần lưu hay thời điểm):
    dùng làm `phien_ban` cho khóa lạc quan, để một trang mở từ trước không ngầm ghi đè thay đổi của Admin khác."""
    chuoi = json.dumps(gia_tri, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(chuoi.encode()).hexdigest()[:16]

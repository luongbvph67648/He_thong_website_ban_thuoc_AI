"""Dữ liệu mẫu để demo: danh mục, sản phẩm, hoạt chất, tương tác, nhà cung cấp.

TOÀN BỘ LÀ DỮ LIỆU GIẢ cho đồ án: tên thương hiệu, nhà sản xuất, số đăng ký, công ty và mã số thuế đều hư cấu; thông tin
tương tác thuốc chỉ để minh họa luồng cảnh báo, chưa được dược sĩ thẩm định, không dùng cho mục đích y khoa thật.

Giá là số đồng nguyên theo đơn vị cơ sở (viên, gói, chai...). Đơn vị lớn (vỉ, hộp) rẻ hơn tổng giá lẻ một chút.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.core.tien import lam_tron_vnd


@dataclass(frozen=True)
class DonViMau:
    ten: str
    he_so: int
    gia_ban: Decimal
    la_mac_dinh: bool = False
    ban_online: bool = True


@dataclass(frozen=True)
class LoMau:
    """Một lô nhập. `han_con_lai_ngay` âm nghĩa là đã hết hạn cách đây ngần ấy ngày."""

    chu_lo: str  # hậu tố số lô, ví dụ "A"
    han_con_lai_ngay: int
    so_luong: int  # theo đơn vị mặc định của sản phẩm (thường là hộp)
    ty_le_gia_von: Decimal = Decimal("0.65")  # giá nhập / giá bán lẻ đơn vị cơ sở


@dataclass(frozen=True)
class SanPhamMau:
    ma: int  # SP0001...
    ten: str
    loai: str
    danh_muc: str  # slug danh mục lá
    dang_bao_che: str
    quy_cach: str
    don_vi_co_so: str
    thuong_hieu: str
    nha_san_xuat: str
    doi_tuong: str
    hoat_chat: tuple[tuple[str, str], ...]  # (tên hoạt chất, hàm lượng)
    don_vi: tuple[DonViMau, ...]
    lo: tuple[LoMau, ...] | None = None  # None = sinh theo mẫu chuẩn (xem `lo_mac_dinh`)
    ton_toi_thieu: int = 0
    la_noi_bat: bool = False
    dung_dinh_ky: bool = False
    so_ngay_dung_moi_don_vi: Decimal | None = None
    so_luong_toi_da_moi_don: int | None = None
    ngung_kinh_doanh: bool = False

    @property
    def sku(self) -> str:
        return f"MAU-SP{self.ma:04d}"  # tiền tố riêng: không bao giờ trùng SKU của hàng thật

    @property
    def so_dang_ky(self) -> str | None:
        return None if self.loai in ("thiet_bi_y_te", "duoc_my_pham") else f"MAU-VD-{self.ma:04d}"


def _lam_tron_tram(gia: Decimal) -> Decimal:
    return lam_tron_vnd(gia / 100) * 100


def vien_vi_hop(
    gia_vien: int, vien_moi_vi: int = 10, vi_moi_hop: int = 10, ten_nho: str = "Viên"
) -> tuple[DonViMau, ...]:
    """Viên → Vỉ → Hộp (mặc định bán theo Hộp). Vỉ giảm 5%, hộp giảm 10% so với giá lẻ."""
    gia = Decimal(gia_vien)
    if vi_moi_hop == 1:  # hộp chỉ có một vỉ: gộp, tránh hai đơn vị cùng hệ số
        return (
            DonViMau(ten_nho, 1, gia),
            DonViMau("Hộp", vien_moi_vi, _lam_tron_tram(gia * vien_moi_vi * Decimal("0.90")), True),
        )
    return (
        DonViMau(ten_nho, 1, gia),
        DonViMau("Vỉ", vien_moi_vi, _lam_tron_tram(gia * vien_moi_vi * Decimal("0.95"))),
        DonViMau(
            "Hộp", vien_moi_vi * vi_moi_hop, _lam_tron_tram(gia * vien_moi_vi * vi_moi_hop * Decimal("0.90")), True
        ),
    )


def nho_lon(ten_nho: str, gia_nho: int, ten_lon: str, he_so: int, gia_lon: int) -> tuple[DonViMau, ...]:
    """Đơn vị lẻ và một đơn vị lớn (mặc định bán theo đơn vị lớn)."""
    return (DonViMau(ten_nho, 1, Decimal(gia_nho)), DonViMau(ten_lon, he_so, Decimal(gia_lon), True))


def goi_hop(gia_goi: int, goi_moi_hop: int, ten_nho: str = "Gói") -> tuple[DonViMau, ...]:
    gia = Decimal(gia_goi)
    return (
        DonViMau(ten_nho, 1, gia),
        DonViMau("Hộp", goi_moi_hop, _lam_tron_tram(gia * goi_moi_hop * Decimal("0.92")), True),
    )


def mot_don_vi(ten: str, gia: int) -> tuple[DonViMau, ...]:
    return (DonViMau(ten, 1, Decimal(gia), True),)


# --- Danh mục 3 cấp: (slug, tên, slug cha) ---------------------------------------------------------------------------

DANH_MUC: list[tuple[str, str, str | None]] = [
    ("thuoc", "Thuốc", None),
    ("giam-dau-ha-sot", "Giảm đau - hạ sốt", "thuoc"),
    ("paracetamol", "Paracetamol", "giam-dau-ha-sot"),
    ("thuoc-chong-viem-nsaid", "Thuốc chống viêm NSAID", "giam-dau-ha-sot"),
    ("ho-hap-di-ung", "Hô hấp - dị ứng", "thuoc"),
    ("ho-long-dom", "Ho - long đờm", "ho-hap-di-ung"),
    ("di-ung-viem-mui", "Dị ứng - viêm mũi", "ho-hap-di-ung"),
    ("tieu-hoa", "Tiêu hóa", "thuoc"),
    ("da-day-trao-nguoc", "Dạ dày - trào ngược", "tieu-hoa"),
    ("tieu-chay-roi-loan-tieu-hoa", "Tiêu chảy - rối loạn tiêu hóa", "tieu-hoa"),
    ("tim-mach-chuyen-hoa", "Tim mạch - chuyển hóa", "thuoc"),
    ("huyet-ap", "Huyết áp", "tim-mach-chuyen-hoa"),
    ("tieu-duong", "Tiểu đường", "tim-mach-chuyen-hoa"),
    ("mo-mau-chong-dong", "Mỡ máu - chống đông", "tim-mach-chuyen-hoa"),
    ("khang-sinh", "Kháng sinh", "thuoc"),
    ("khang-sinh-duong-uong", "Kháng sinh đường uống", "khang-sinh"),
    ("thuc-pham-chuc-nang", "Thực phẩm chức năng", None),
    ("vitamin-khoang-chat", "Vitamin - khoáng chất", "thuc-pham-chuc-nang"),
    ("vitamin-tong-hop", "Vitamin tổng hợp", "vitamin-khoang-chat"),
    ("canxi-vitamin-d", "Canxi - Vitamin D", "vitamin-khoang-chat"),
    ("ho-tro-tieu-hoa-tpcn", "Hỗ trợ tiêu hóa", "thuc-pham-chuc-nang"),
    ("men-vi-sinh", "Men vi sinh", "ho-tro-tieu-hoa-tpcn"),
    ("duoc-my-pham", "Dược mỹ phẩm", None),
    ("cham-soc-da", "Chăm sóc da", "duoc-my-pham"),
    ("kem-chong-nang", "Kem chống nắng", "cham-soc-da"),
    ("sua-rua-mat-duong-am", "Sữa rửa mặt - dưỡng ẩm", "cham-soc-da"),
    ("cham-soc-toc-co-the", "Chăm sóc tóc - cơ thể", "duoc-my-pham"),
    ("dau-goi-sua-tam", "Dầu gội - xịt khoáng", "cham-soc-toc-co-the"),
    ("thiet-bi-y-te", "Thiết bị y tế", None),
    ("dung-cu-do", "Dụng cụ đo", "thiet-bi-y-te"),
    ("nhiet-ke-huyet-ap-duong-huyet", "Nhiệt kế - huyết áp - đường huyết", "dung-cu-do"),
    ("vat-tu-tieu-hao", "Vật tư tiêu hao", "thiet-bi-y-te"),
    ("khau-trang-gang-tay-bang-gac", "Khẩu trang - găng tay - băng gạc", "vat-tu-tieu-hao"),
]

THUONG_HIEU = ["Hà Thành Pharma", "Sao Việt", "An Bình Care", "Nam Dược", "VitaLife", "DermaClear", "MediTech"]

NHA_SAN_XUAT = [
    ("Công ty CP Dược Hà Thành (mẫu)", "Việt Nam"),
    ("Công ty TNHH Sao Việt (mẫu)", "Việt Nam"),
    ("PharmaGlobal Ltd. (mẫu)", "Ấn Độ"),
    ("MediTech Co. (mẫu)", "Đài Loan"),
    ("VitaLife Inc. (mẫu)", "Hoa Kỳ"),
]

# Tên chuẩn → (tên khác phục vụ tìm kiếm, mô tả)
HOAT_CHAT: dict[str, tuple[str, str]] = {
    "Paracetamol": ("Acetaminophen", "Giảm đau, hạ sốt"),
    "Ibuprofen": ("", "Giảm đau, hạ sốt, kháng viêm không steroid"),
    "Aspirin": ("Acid acetylsalicylic, ASA", "Giảm đau, hạ sốt; liều thấp dùng chống kết tập tiểu cầu"),
    "Loratadin": ("Loratadine", "Kháng histamin thế hệ 2"),
    "Cetirizin": ("Cetirizine", "Kháng histamin thế hệ 2"),
    "Acetylcystein": ("N-acetylcysteine, NAC", "Tiêu nhầy đường hô hấp"),
    "Tỳ bà diệp": ("Lá nhót tây", "Dược liệu trong các bài thuốc ho"),
    "Cát cánh": ("", "Dược liệu trong các bài thuốc ho"),
    "Omeprazol": ("Omeprazole", "Ức chế bơm proton"),
    "Domperidon": ("Domperidone", "Chống nôn, kích thích nhu động dạ dày"),
    "Loperamid": ("Loperamide", "Giảm nhu động ruột trong tiêu chảy cấp"),
    "Berberin": ("Berberine", "Hỗ trợ điều trị tiêu chảy do nhiễm khuẩn đường ruột"),
    "Diosmectit": ("Diosmectite", "Bảo vệ niêm mạc tiêu hóa"),
    "Glucose khan": ("Dextrose", "Thành phần dung dịch bù nước"),
    "Natri clorid": ("Muối ăn, NaCl", "Thành phần dung dịch bù nước"),
    "Amoxicillin": ("", "Kháng sinh nhóm penicillin"),
    "Azithromycin": ("", "Kháng sinh nhóm macrolid"),
    "Amlodipin": ("Amlodipine", "Chẹn kênh canxi, hạ huyết áp"),
    "Losartan": ("Losartan kali", "Chẹn thụ thể angiotensin II, hạ huyết áp"),
    "Metformin": ("", "Hạ đường huyết nhóm biguanid"),
    "Atorvastatin": ("", "Giảm cholesterol nhóm statin"),
    "Warfarin": ("Warfarin natri", "Thuốc chống đông đường uống"),
    "Acid ascorbic": ("Vitamin C", "Vitamin"),
    "Cholecalciferol": ("Vitamin D3", "Vitamin"),
    "Calci carbonat": ("Canxi", "Bổ sung canxi"),
    "Kẽm gluconat": ("Zinc gluconate", "Bổ sung kẽm"),
    "Sắt fumarat": ("Iron fumarate", "Bổ sung sắt"),
    "Acid folic": ("Vitamin B9, Folate", "Vitamin"),
    "Omega-3": ("EPA, DHA, dầu cá", "Acid béo không bão hòa"),
    "Lactobacillus": ("Men vi sinh", "Lợi khuẩn đường ruột"),
    "Vitamin tổng hợp": ("Multivitamin", "Hỗn hợp vitamin và khoáng chất"),
}

# (hoạt chất A, hoạt chất B, mức độ, cơ chế, khuyến cáo). Lưu a<b theo id khi nạp.
TUONG_TAC: list[tuple[str, str, str, str, str]] = [
    (
        "Warfarin",
        "Aspirin",
        "nghiem_trong",
        "Cộng hưởng tác dụng chống đông và ức chế tiểu cầu, tăng nguy cơ chảy máu.",
        "Không tự phối hợp. Hỏi ý kiến dược sĩ hoặc bác sĩ điều trị trước khi dùng; theo dõi dấu hiệu chảy máu.",
    ),
    (
        "Warfarin",
        "Ibuprofen",
        "nghiem_trong",
        "NSAID làm tăng nguy cơ chảy máu đường tiêu hóa ở người dùng thuốc chống đông.",
        "Tránh dùng chung. Cần giảm đau thì hỏi dược sĩ về lựa chọn thay thế.",
    ),
    (
        "Aspirin",
        "Ibuprofen",
        "trung_binh",
        "Ibuprofen có thể cản trở tác dụng chống kết tập tiểu cầu của aspirin liều thấp; tăng kích ứng dạ dày.",
        "Không dùng chung kéo dài khi chưa hỏi ý kiến dược sĩ hoặc bác sĩ.",
    ),
    (
        "Warfarin",
        "Paracetamol",
        "trung_binh",
        "Dùng paracetamol thường xuyên liều cao có thể làm tăng chỉ số INR.",
        "Chỉ dùng ngắn ngày theo hướng dẫn; báo bác sĩ nếu dùng thường xuyên để theo dõi INR.",
    ),
    (
        "Losartan",
        "Ibuprofen",
        "trung_binh",
        "NSAID có thể làm giảm tác dụng hạ huyết áp và tăng nguy cơ ảnh hưởng chức năng thận.",
        "Hỏi dược sĩ trước khi dùng NSAID kéo dài; uống đủ nước, theo dõi huyết áp.",
    ),
    (
        "Calci carbonat",
        "Sắt fumarat",
        "nhe",
        "Canxi làm giảm hấp thu sắt khi uống cùng lúc.",
        "Uống hai loại cách nhau ít nhất 2 giờ.",
    ),
]

# (tên, mã số thuế giả, địa chỉ, người liên hệ, SĐT, email)
NHA_CUNG_CAP = [
    ("Công ty Dược phẩm Hà Thành (mẫu)", "MAU0000001", "12 Đường số 1, Quận 1, TP. Hồ Chí Minh", "Anh Hùng", "02800000001", "ncc1@example.com"),
    ("Công ty TNHH Phân phối Nam Việt (mẫu)", "MAU0000002", "34 Đường số 2, Quận 3, TP. Hồ Chí Minh", "Chị Lan", "02800000002", "ncc2@example.com"),
    ("Công ty CP Thiết bị Y tế An Phát (mẫu)", "MAU0000003", "56 Đường số 3, Quận 5, TP. Hồ Chí Minh", "Anh Phát", "02800000003", "ncc3@example.com"),
]  # fmt: skip

# Hạng mục nào nhập từ nhà cung cấp nào (chỉ số trong NHA_CUNG_CAP)
NCC_THEO_LOAI = {
    "thuoc_ke_don": 0,
    "thuoc_khong_ke_don": 0,
    "thuc_pham_chuc_nang": 1,
    "duoc_my_pham": 1,
    "thiet_bi_y_te": 2,
}


def lo_mac_dinh(sp: SanPhamMau) -> tuple[LoMau, ...]:
    """Mẫu lô chuẩn, đa dạng theo mã sản phẩm để demo đủ trường hợp mà vẫn xác định (chạy lại cho kết quả cũ).

    - Mọi sản phẩm có lô chính hạn dài.
    - Cứ 3 sản phẩm có thêm lô thứ hai hạn trung bình (vẫn đang bán).
    - Cứ 5 sản phẩm có thêm một lô cận hạn (< 90 ngày: ngừng bán online, quầy vẫn bán).
    - Cứ 11 sản phẩm có thêm một lô vừa hết hạn, còn hàng (chờ phiếu hủy).
    """
    n = sp.ma
    xa = 5 * 365 if sp.loai == "thiet_bi_y_te" else 540 + 37 * (n % 7)
    lo = [LoMau("A", xa, 20 + (n * 7) % 60)]
    if n % 3 == 0:
        lo.append(LoMau("B", 110 + 9 * (n % 8), 10 + n % 15))
    if n % 5 == 1:
        lo.append(LoMau("C", 25 + 6 * (n % 9), 4 + n % 6))
    if n % 11 == 2:
        lo.append(LoMau("D", -(5 + n % 20), 2 + n % 4))
    return tuple(lo)


def _sp(ma, ten, loai, danh_muc, dang_bao_che, quy_cach, co_so, hieu, nsx, doi_tuong, hoat_chat, don_vi, **kw):
    return SanPhamMau(
        ma, ten, loai, danh_muc, dang_bao_che, quy_cach, co_so, hieu, nsx, doi_tuong, tuple(hoat_chat), don_vi, **kw
    )


HP, SV, AB, ND, VL, DC, MT = THUONG_HIEU
N_HP, N_SV, N_PG, N_MT, N_VL = (n for n, _ in NHA_SAN_XUAT)
NL, TE_NL = "Người lớn", "Trẻ em và người lớn"
KE_DON, KHONG_KE_DON, TPCN, MY_PHAM, TB_YT = (
    "thuoc_ke_don",
    "thuoc_khong_ke_don",
    "thuc_pham_chuc_nang",
    "duoc_my_pham",
    "thiet_bi_y_te",
)

SAN_PHAM: list[SanPhamMau] = [
    # --- Thuốc kê đơn (không vào giỏ hàng, không giảm giá, AI không gợi ý) ---
    _sp(1, "Amoxicillin 500mg", KE_DON, "khang-sinh-duong-uong", "Viên nang", "Hộp 10 vỉ x 10 viên", "viên", HP, N_HP, NL, [("Amoxicillin", "500mg")], vien_vi_hop(1500), ton_toi_thieu=300),
    _sp(2, "Azithromycin 250mg", KE_DON, "khang-sinh-duong-uong", "Viên nén bao phim", "Hộp 1 vỉ x 6 viên", "viên", AB, N_PG, NL, [("Azithromycin", "250mg")], vien_vi_hop(9000, 6, 1), lo=()),
    _sp(3, "Amlodipin 5mg", KE_DON, "huyet-ap", "Viên nén", "Hộp 3 vỉ x 10 viên", "viên", HP, N_HP, NL, [("Amlodipin", "5mg")], vien_vi_hop(700, 10, 3), dung_dinh_ky=True, so_ngay_dung_moi_don_vi=Decimal("1.00"), ton_toi_thieu=300),
    _sp(4, "Losartan 50mg", KE_DON, "huyet-ap", "Viên nén bao phim", "Hộp 3 vỉ x 10 viên", "viên", SV, N_SV, NL, [("Losartan", "50mg")], vien_vi_hop(1200, 10, 3), dung_dinh_ky=True, so_ngay_dung_moi_don_vi=Decimal("1.00")),
    _sp(5, "Metformin 500mg", KE_DON, "tieu-duong", "Viên nén bao phim", "Hộp 5 vỉ x 20 viên", "viên", SV, N_SV, NL, [("Metformin", "500mg")], vien_vi_hop(600, 20, 5), dung_dinh_ky=True, so_ngay_dung_moi_don_vi=Decimal("0.50")),
    _sp(6, "Atorvastatin 20mg", KE_DON, "mo-mau-chong-dong", "Viên nén bao phim", "Hộp 3 vỉ x 10 viên", "viên", HP, N_PG, NL, [("Atorvastatin", "20mg")], vien_vi_hop(2500, 10, 3), dung_dinh_ky=True, so_ngay_dung_moi_don_vi=Decimal("1.00")),
    _sp(7, "Warfarin 5mg", KE_DON, "mo-mau-chong-dong", "Viên nén", "Hộp 3 vỉ x 10 viên", "viên", AB, N_PG, NL, [("Warfarin", "5mg")], vien_vi_hop(3000, 10, 3)),
    # --- Thuốc không kê đơn ---
    _sp(8, "Paracetamol 500mg", KHONG_KE_DON, "paracetamol", "Viên nén", "Hộp 10 vỉ x 10 viên", "viên", HP, N_HP, TE_NL, [("Paracetamol", "500mg")], vien_vi_hop(600), la_noi_bat=True, ton_toi_thieu=500, so_luong_toi_da_moi_don=200,
        lo=(LoMau("A", 700, 40), LoMau("B", 150, 12), LoMau("C", 75, 6), LoMau("D", -12, 3))),
    _sp(9, "Paracetamol 500mg viên sủi", KHONG_KE_DON, "paracetamol", "Viên sủi", "Hộp 4 vỉ x 4 viên", "viên", HP, N_HP, TE_NL, [("Paracetamol", "500mg")], vien_vi_hop(2500, 4, 4), la_noi_bat=True),
    _sp(10, "Ibuprofen 400mg", KHONG_KE_DON, "thuoc-chong-viem-nsaid", "Viên nén bao phim", "Hộp 10 vỉ x 10 viên", "viên", SV, N_SV, NL, [("Ibuprofen", "400mg")], vien_vi_hop(900), so_luong_toi_da_moi_don=100),
    _sp(11, "Aspirin 81mg", KHONG_KE_DON, "thuoc-chong-viem-nsaid", "Viên nén bao tan trong ruột", "Hộp 3 vỉ x 10 viên", "viên", AB, N_PG, NL, [("Aspirin", "81mg")], vien_vi_hop(500, 10, 3)),
    _sp(12, "Loratadin 10mg", KHONG_KE_DON, "di-ung-viem-mui", "Viên nén", "Hộp 1 vỉ x 10 viên", "viên", SV, N_SV, TE_NL, [("Loratadin", "10mg")], vien_vi_hop(1500, 10, 1), la_noi_bat=True),
    _sp(13, "Cetirizin 10mg", KHONG_KE_DON, "di-ung-viem-mui", "Viên nén bao phim", "Hộp 1 vỉ x 10 viên", "viên", HP, N_HP, TE_NL, [("Cetirizin", "10mg")], vien_vi_hop(1200, 10, 1)),
    _sp(14, "Acetylcystein 200mg", KHONG_KE_DON, "ho-long-dom", "Thuốc bột pha uống", "Hộp 30 gói", "gói", AB, N_PG, TE_NL, [("Acetylcystein", "200mg")], goi_hop(3000, 30)),
    _sp(15, "Thuốc ho Bổ phế", KHONG_KE_DON, "ho-long-dom", "Siro", "Chai 90ml", "chai", ND, N_SV, TE_NL, [("Tỳ bà diệp", "2g/90ml"), ("Cát cánh", "1g/90ml")], mot_don_vi("Chai", 45000), la_noi_bat=True),
    _sp(16, "Omeprazol 20mg", KHONG_KE_DON, "da-day-trao-nguoc", "Viên nang cứng", "Hộp 2 vỉ x 14 viên", "viên", HP, N_PG, NL, [("Omeprazol", "20mg")], vien_vi_hop(1800, 14, 2)),
    _sp(17, "Domperidon 10mg", KHONG_KE_DON, "da-day-trao-nguoc", "Viên nén bao phim", "Hộp 10 vỉ x 10 viên", "viên", SV, N_SV, NL, [("Domperidon", "10mg")], vien_vi_hop(800)),
    _sp(18, "Loperamid 2mg", KHONG_KE_DON, "tieu-chay-roi-loan-tieu-hoa", "Viên nang", "Hộp 2 vỉ x 10 viên", "viên", AB, N_PG, NL, [("Loperamid", "2mg")], vien_vi_hop(700, 10, 2)),
    _sp(19, "Oresol bù nước", KHONG_KE_DON, "tieu-chay-roi-loan-tieu-hoa", "Thuốc bột pha uống", "Hộp 20 gói", "gói", ND, N_SV, TE_NL, [("Glucose khan", "20g/gói"), ("Natri clorid", "3,5g/gói")], goi_hop(4000, 20)),
    _sp(20, "Berberin 100mg", KHONG_KE_DON, "tieu-chay-roi-loan-tieu-hoa", "Viên nén bao đường", "Lọ 100 viên", "viên", ND, N_SV, NL, [("Berberin", "100mg")], nho_lon("Viên", 250, "Lọ", 100, 22000), ngung_kinh_doanh=True, lo=(LoMau("A", 300, 6),)),
    _sp(21, "Diosmectit 3g", KHONG_KE_DON, "tieu-chay-roi-loan-tieu-hoa", "Thuốc bột pha hỗn dịch uống", "Hộp 30 gói", "gói", HP, N_HP, TE_NL, [("Diosmectit", "3g/gói")], goi_hop(3500, 30), lo=(LoMau("A", -20, 5),)),
    # --- Thực phẩm chức năng ---
    _sp(22, "Vitamin C 1000mg viên sủi", TPCN, "vitamin-tong-hop", "Viên sủi", "Tuýp 20 viên", "viên", VL, N_VL, NL, [("Acid ascorbic", "1000mg")], nho_lon("Viên", 3000, "Tuýp", 20, 52000), lo=(LoMau("A", 45, 15),)),
    _sp(23, "Vitamin tổng hợp cho người lớn", TPCN, "vitamin-tong-hop", "Viên nén bao phim", "Lọ 60 viên", "viên", VL, N_VL, NL, [("Vitamin tổng hợp", "")], nho_lon("Viên", 3500, "Lọ", 60, 189000), la_noi_bat=True, dung_dinh_ky=True, so_ngay_dung_moi_don_vi=Decimal("1.00")),
    _sp(24, "Canxi + Vitamin D3", TPCN, "canxi-vitamin-d", "Viên nén", "Lọ 60 viên", "viên", VL, N_VL, NL, [("Calci carbonat", "600mg"), ("Cholecalciferol", "400IU")], nho_lon("Viên", 2800, "Lọ", 60, 152000), dung_dinh_ky=True, so_ngay_dung_moi_don_vi=Decimal("1.00")),
    _sp(25, "Vitamin D3 1000IU", TPCN, "canxi-vitamin-d", "Viên nang mềm", "Lọ 60 viên", "viên", VL, N_VL, TE_NL, [("Cholecalciferol", "1000IU")], nho_lon("Viên", 3200, "Lọ", 60, 175000)),
    _sp(26, "Omega-3 1000mg", TPCN, "vitamin-tong-hop", "Viên nang mềm", "Lọ 100 viên", "viên", VL, N_VL, NL, [("Omega-3", "1000mg")], nho_lon("Viên", 4500, "Lọ", 100, 390000), la_noi_bat=True),
    _sp(27, "Men vi sinh Lactobacillus", TPCN, "men-vi-sinh", "Bột pha uống", "Hộp 20 gói", "gói", AB, N_MT, TE_NL, [("Lactobacillus", "1 tỷ CFU/gói")], goi_hop(6000, 20)),
    _sp(28, "Kẽm gluconat 10mg", TPCN, "vitamin-tong-hop", "Viên nén", "Lọ 100 viên", "viên", VL, N_VL, TE_NL, [("Kẽm gluconat", "10mg")], nho_lon("Viên", 1200, "Lọ", 100, 110000), lo=()),
    _sp(29, "Sắt + Acid folic", TPCN, "vitamin-tong-hop", "Viên nang", "Hộp 3 vỉ x 10 viên", "viên", AB, N_MT, NL, [("Sắt fumarat", "162mg"), ("Acid folic", "0,75mg")], vien_vi_hop(2200, 10, 3)),
    # --- Dược mỹ phẩm ---
    _sp(30, "Kem chống nắng SPF50+ 50ml", MY_PHAM, "kem-chong-nang", "Kem", "Tuýp 50ml", "tuýp", DC, N_MT, "Mọi lứa tuổi", [], mot_don_vi("Tuýp", 285000), la_noi_bat=True),
    _sp(31, "Sữa rửa mặt dịu nhẹ 150ml", MY_PHAM, "sua-rua-mat-duong-am", "Gel", "Chai 150ml", "chai", DC, N_MT, "Mọi lứa tuổi", [], mot_don_vi("Chai", 165000)),
    _sp(32, "Kem dưỡng ẩm phục hồi 50g", MY_PHAM, "sua-rua-mat-duong-am", "Kem", "Hũ 50g", "hũ", DC, N_MT, "Mọi lứa tuổi", [], mot_don_vi("Hũ", 235000)),
    _sp(33, "Dầu gội trị gàu 200ml", MY_PHAM, "dau-goi-sua-tam", "Dầu gội", "Chai 200ml", "chai", DC, N_MT, NL, [], mot_don_vi("Chai", 128000)),
    _sp(34, "Xịt khoáng dịu da 150ml", MY_PHAM, "dau-goi-sua-tam", "Xịt", "Chai 150ml", "chai", DC, N_MT, "Mọi lứa tuổi", [], mot_don_vi("Chai", 98000)),
    # --- Thiết bị y tế ---
    _sp(35, "Nhiệt kế điện tử đầu mềm", TB_YT, "nhiet-ke-huyet-ap-duong-huyet", "Thiết bị", "Hộp 1 cái", "cái", MT, N_MT, "Mọi lứa tuổi", [], mot_don_vi("Cái", 89000), la_noi_bat=True),
    _sp(36, "Máy đo huyết áp bắp tay", TB_YT, "nhiet-ke-huyet-ap-duong-huyet", "Thiết bị", "Hộp 1 máy", "máy", MT, N_MT, NL, [], mot_don_vi("Máy", 850000), la_noi_bat=True),
    _sp(37, "Máy đo đường huyết", TB_YT, "nhiet-ke-huyet-ap-duong-huyet", "Thiết bị", "Hộp 1 máy + 10 que thử", "máy", MT, N_MT, NL, [], mot_don_vi("Máy", 520000)),
    _sp(38, "Que thử đường huyết", TB_YT, "nhiet-ke-huyet-ap-duong-huyet", "Que thử", "Hộp 50 que", "que", MT, N_MT, NL, [], nho_lon("Que", 9000, "Hộp", 50, 405000)),
    _sp(39, "Khẩu trang y tế 4 lớp", TB_YT, "khau-trang-gang-tay-bang-gac", "Vật tư", "Hộp 50 cái", "cái", MT, N_MT, NL, [], nho_lon("Cái", 1000, "Hộp", 50, 42000)),
    _sp(40, "Găng tay y tế không bột", TB_YT, "khau-trang-gang-tay-bang-gac", "Vật tư", "Hộp 100 chiếc", "chiếc", MT, N_MT, NL, [], nho_lon("Chiếc", 1200, "Hộp", 100, 108000)),
    _sp(41, "Băng cuộn y tế 5cm x 2m", TB_YT, "khau-trang-gang-tay-bang-gac", "Vật tư", "Gói 1 cuộn", "cuộn", MT, N_MT, NL, [], mot_don_vi("Cuộn", 6500)),
    _sp(42, "Gạc vô trùng 10cm x 10cm", TB_YT, "khau-trang-gang-tay-bang-gac", "Vật tư", "Gói 10 miếng", "miếng", MT, N_MT, NL, [], nho_lon("Miếng", 1800, "Gói", 10, 16500)),
]  # fmt: skip

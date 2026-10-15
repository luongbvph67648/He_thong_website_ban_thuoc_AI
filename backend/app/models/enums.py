"""Enum PostgreSQL native của ERD. Tên kiểu và thứ tự giá trị phải khớp docs/database/ERD_da_chinh_sua.dbml."""

from enum import StrEnum

from sqlalchemy import Enum

from app.models.base import Base


def _kieu_enum(lop: type[StrEnum], ten: str) -> Enum:
    return Enum(
        lop,
        name=ten,
        native_enum=True,
        metadata=Base.metadata,
        values_callable=lambda e: [m.value for m in e],
    )


class LoaiSanPham(StrEnum):
    thuoc_ke_don = "thuoc_ke_don"
    thuoc_khong_ke_don = "thuoc_khong_ke_don"
    thuc_pham_chuc_nang = "thuc_pham_chuc_nang"
    duoc_my_pham = "duoc_my_pham"
    thiet_bi_y_te = "thiet_bi_y_te"


KIEU_LOAI_SAN_PHAM = _kieu_enum(LoaiSanPham, "loai_san_pham")


class TrangThaiKinhDoanh(StrEnum):
    dang_kinh_doanh = "dang_kinh_doanh"
    ngung_kinh_doanh = "ngung_kinh_doanh"


KIEU_TRANG_THAI_KINH_DOANH = _kieu_enum(TrangThaiKinhDoanh, "trang_thai_kinh_doanh")


class TrangThaiNoiDung(StrEnum):
    nhap = "nhap"
    da_duyet = "da_duyet"
    luu_tru = "luu_tru"


KIEU_TRANG_THAI_NOI_DUNG = _kieu_enum(TrangThaiNoiDung, "trang_thai_noi_dung")


class TrangThaiLo(StrEnum):
    dang_ban = "dang_ban"
    can_han = "can_han"
    khoa = "khoa"
    het_han = "het_han"
    thu_hoi = "thu_hoi"


KIEU_TRANG_THAI_LO = _kieu_enum(TrangThaiLo, "trang_thai_lo")


class TrangThaiDon(StrEnum):
    cho_khach_xac_nhan = "cho_khach_xac_nhan"
    cho_thanh_toan = "cho_thanh_toan"
    cho_xac_nhan = "cho_xac_nhan"
    da_xac_nhan = "da_xac_nhan"
    dang_soan_hang = "dang_soan_hang"
    cho_lay_hang = "cho_lay_hang"
    dang_giao = "dang_giao"
    da_giao = "da_giao"
    hoan_tat = "hoan_tat"
    giao_that_bai = "giao_that_bai"
    hoan_ve_kho = "hoan_ve_kho"
    da_huy = "da_huy"


KIEU_TRANG_THAI_DON = _kieu_enum(TrangThaiDon, "trang_thai_don")


class KenhBan(StrEnum):
    online = "online"
    dien_thoai = "dien_thoai"
    tai_quay = "tai_quay"


KIEU_KENH_BAN = _kieu_enum(KenhBan, "kenh_ban")


class HinhThucNhan(StrEnum):
    giao_tan_noi = "giao_tan_noi"
    nhan_tai_nha_thuoc = "nhan_tai_nha_thuoc"


KIEU_HINH_THUC_NHAN = _kieu_enum(HinhThucNhan, "hinh_thuc_nhan")


class PhuongThucThanhToan(StrEnum):
    cod = "cod"
    vnpay = "vnpay"
    momo = "momo"
    tien_mat = "tien_mat"
    chuyen_khoan = "chuyen_khoan"


KIEU_PHUONG_THUC_THANH_TOAN = _kieu_enum(PhuongThucThanhToan, "phuong_thuc_thanh_toan")


class TrangThaiThanhToan(StrEnum):
    chua_thanh_toan = "chua_thanh_toan"
    da_thanh_toan = "da_thanh_toan"
    cho_hoan_tien = "cho_hoan_tien"
    hoan_tien_mot_phan = "hoan_tien_mot_phan"
    da_hoan_tien = "da_hoan_tien"


KIEU_TRANG_THAI_THANH_TOAN = _kieu_enum(TrangThaiThanhToan, "trang_thai_thanh_toan")


class LoaiGiaoDich(StrEnum):
    thanh_toan = "thanh_toan"
    hoan_tien = "hoan_tien"


KIEU_LOAI_GIAO_DICH = _kieu_enum(LoaiGiaoDich, "loai_giao_dich")


class TrangThaiGiaoDich(StrEnum):
    khoi_tao = "khoi_tao"
    thanh_cong = "thanh_cong"
    that_bai = "that_bai"


KIEU_TRANG_THAI_GIAO_DICH = _kieu_enum(TrangThaiGiaoDich, "trang_thai_giao_dich")


class TrangThaiPhanBo(StrEnum):
    dang_giu = "dang_giu"
    da_xuat = "da_xuat"
    da_nha = "da_nha"
    da_hoan_nhap = "da_hoan_nhap"


KIEU_TRANG_THAI_PHAN_BO = _kieu_enum(TrangThaiPhanBo, "trang_thai_phan_bo")


class KhuTon(StrEnum):
    kho_ban = "kho_ban"
    biet_tru = "biet_tru"


KIEU_KHU_TON = _kieu_enum(KhuTon, "khu_ton")


class LoaiBienDong(StrEnum):
    nhap_kho = "nhap_kho"
    xuat_ban = "xuat_ban"
    hoan_nhap = "hoan_nhap"
    nhan_tra_ve = "nhan_tra_ve"
    dieu_chinh = "dieu_chinh"
    huy_hang = "huy_hang"
    xuat_tra_ncc = "xuat_tra_ncc"


KIEU_LOAI_BIEN_DONG = _kieu_enum(LoaiBienDong, "loai_bien_dong")


class LoaiVanDon(StrEnum):
    giao_hang = "giao_hang"
    tra_hang = "tra_hang"


KIEU_LOAI_VAN_DON = _kieu_enum(LoaiVanDon, "loai_van_don")


class MucDoTuongTac(StrEnum):
    nhe = "nhe"
    trung_binh = "trung_binh"
    nghiem_trong = "nghiem_trong"
    chong_chi_dinh = "chong_chi_dinh"


KIEU_MUC_DO_TUONG_TAC = _kieu_enum(MucDoTuongTac, "muc_do_tuong_tac")


class LoaiBaiViet(StrEnum):
    bai_viet = "bai_viet"
    chinh_sach = "chinh_sach"
    faq = "faq"


KIEU_LOAI_BAI_VIET = _kieu_enum(LoaiBaiViet, "loai_bai_viet")


class TrangThaiYeuCauDonThuoc(StrEnum):
    cho_duyet = "cho_duyet"
    dang_tu_van = "dang_tu_van"
    da_tao_don = "da_tao_don"
    tu_choi = "tu_choi"
    khach_huy = "khach_huy"


KIEU_TRANG_THAI_YEU_CAU_DON_THUOC = _kieu_enum(TrangThaiYeuCauDonThuoc, "trang_thai_yeu_cau_don_thuoc")


class TrangThaiDuyet(StrEnum):
    cho_duyet = "cho_duyet"
    da_duyet = "da_duyet"
    tu_choi = "tu_choi"


KIEU_TRANG_THAI_DUYET = _kieu_enum(TrangThaiDuyet, "trang_thai_duyet")


class LyDoHuyHang(StrEnum):
    het_han = "het_han"
    hu_hong = "hu_hong"
    hang_tra_ve = "hang_tra_ve"
    thu_hoi = "thu_hoi"
    khac = "khac"


KIEU_LY_DO_HUY_HANG = _kieu_enum(LyDoHuyHang, "ly_do_huy_hang")


class LyDoDoiTra(StrEnum):
    giao_sai_san_pham = "giao_sai_san_pham"
    sai_so_luong = "sai_so_luong"
    hu_hong = "hu_hong"
    het_han_can_han = "het_han_can_han"
    khac = "khac"


KIEU_LY_DO_DOI_TRA = _kieu_enum(LyDoDoiTra, "ly_do_doi_tra")


class TrangThaiDoiTra(StrEnum):
    cho_duyet = "cho_duyet"
    da_duyet = "da_duyet"
    tu_choi = "tu_choi"
    kho_da_nhan = "kho_da_nhan"
    hoan_tat = "hoan_tat"


KIEU_TRANG_THAI_DOI_TRA = _kieu_enum(TrangThaiDoiTra, "trang_thai_doi_tra")


class HuongXuLyDoiTra(StrEnum):
    hoan_tien = "hoan_tien"
    gui_hang_thay_the = "gui_hang_thay_the"


KIEU_HUONG_XU_LY_DOI_TRA = _kieu_enum(HuongXuLyDoiTra, "huong_xu_ly_doi_tra")


class LoaiGiamGia(StrEnum):
    phan_tram = "phan_tram"
    so_tien = "so_tien"


KIEU_LOAI_GIAM_GIA = _kieu_enum(LoaiGiamGia, "loai_giam_gia")


class PhamViKhuyenMai(StrEnum):
    toan_bo = "toan_bo"
    danh_muc = "danh_muc"
    san_pham = "san_pham"


KIEU_PHAM_VI_KHUYEN_MAI = _kieu_enum(PhamViKhuyenMai, "pham_vi_khuyen_mai")


class TrangThaiTaiKhoan(StrEnum):
    hoat_dong = "hoat_dong"
    bi_khoa = "bi_khoa"


KIEU_TRANG_THAI_TAI_KHOAN = _kieu_enum(TrangThaiTaiKhoan, "trang_thai_tai_khoan")


class TrangThaiKiemKe(StrEnum):
    dang_kiem = "dang_kiem"
    da_chot = "da_chot"


KIEU_TRANG_THAI_KIEM_KE = _kieu_enum(TrangThaiKiemKe, "trang_thai_kiem_ke")


class TrangThaiThuHoi(StrEnum):
    dang_thu_hoi = "dang_thu_hoi"
    hoan_tat = "hoan_tat"


KIEU_TRANG_THAI_THU_HOI = _kieu_enum(TrangThaiThuHoi, "trang_thai_thu_hoi")


class KetQuaLienHeThuHoi(StrEnum):
    chua_lien_he = "chua_lien_he"
    da_lien_he = "da_lien_he"
    da_hen_tra_hang = "da_hen_tra_hang"
    da_thu_ve = "da_thu_ve"
    khong_lien_lac_duoc = "khong_lien_lac_duoc"


KIEU_KET_QUA_LIEN_HE_THU_HOI = _kieu_enum(KetQuaLienHeThuHoi, "ket_qua_lien_he_thu_hoi")


class LoaiHoiThoai(StrEnum):
    ai = "ai"
    duoc_si = "duoc_si"


KIEU_LOAI_HOI_THOAI = _kieu_enum(LoaiHoiThoai, "loai_hoi_thoai")


class TrangThaiHoiThoai(StrEnum):
    dang_mo = "dang_mo"
    cho_duoc_si = "cho_duoc_si"
    duoc_si_dang_xu_ly = "duoc_si_dang_xu_ly"
    cho_goi_lai = "cho_goi_lai"
    da_dong = "da_dong"


KIEU_TRANG_THAI_HOI_THOAI = _kieu_enum(TrangThaiHoiThoai, "trang_thai_hoi_thoai")


class VaiTroTinNhan(StrEnum):
    khach = "khach"
    ai = "ai"
    duoc_si = "duoc_si"
    he_thong = "he_thong"


KIEU_VAI_TRO_TIN_NHAN = _kieu_enum(VaiTroTinNhan, "vai_tro_tin_nhan")


class NguonTriThuc(StrEnum):
    san_pham = "san_pham"
    bai_viet = "bai_viet"
    chinh_sach = "chinh_sach"
    faq = "faq"


KIEU_NGUON_TRI_THUC = _kieu_enum(NguonTriThuc, "nguon_tri_thuc")

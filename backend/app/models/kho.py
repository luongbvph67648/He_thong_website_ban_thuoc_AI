"""Nhóm kho: các bảng theo docs/database/ERD_da_chinh_sua.dbml."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import (
    KIEU_KET_QUA_LIEN_HE_THU_HOI,
    KIEU_KHU_TON,
    KIEU_LOAI_BIEN_DONG,
    KIEU_LY_DO_HUY_HANG,
    KIEU_TRANG_THAI_DUYET,
    KIEU_TRANG_THAI_KIEM_KE,
    KIEU_TRANG_THAI_LO,
    KIEU_TRANG_THAI_THU_HOI,
    KetQuaLienHeThuHoi,
    KhuTon,
    LoaiBienDong,
    LyDoHuyHang,
    TrangThaiDuyet,
    TrangThaiKiemKe,
    TrangThaiLo,
    TrangThaiThuHoi,
)

if TYPE_CHECKING:
    from app.models.ban_hang import DonHang
    from app.models.he_thong import NhanVien
    from app.models.khach_hang import KhachHang
    from app.models.san_pham import DanhMuc, DonViQuyDoi, SanPham


class NhaCungCap(Base):
    """Bảng `nha_cung_cap`."""

    __tablename__ = "nha_cung_cap"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ten: Mapped[str] = mapped_column(String(200))
    ma_so_thue: Mapped[str | None] = mapped_column(String(20), unique=True)
    dia_chi: Mapped[str | None] = mapped_column(String(500))
    nguoi_lien_he: Mapped[str | None] = mapped_column(String(150))
    so_dien_thoai: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(150))
    dang_hop_tac: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LoThuoc(Base):
    """Bảng `lo_thuoc`.

    CHECK (so_luong_ton >= 0), CHECK (so_luong_giu >= 0), CHECK (so_luong_giu <= so_luong_ton), CHECK
    (so_luong_biet_tru >= 0). Mọi cập nhật tồn dùng SELECT ... FOR UPDATE và ghi bien_dong_kho
    """

    __tablename__ = "lo_thuoc"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    san_pham_id: Mapped[int] = mapped_column(Integer, ForeignKey("san_pham.id"))
    # Số lô của nhà sản xuất
    so_lo: Mapped[str] = mapped_column(String(50))
    ngay_san_xuat: Mapped[date | None] = mapped_column(Date)
    han_su_dung: Mapped[date] = mapped_column(Date)
    # Giá vốn trên 1 đơn vị cơ sở
    gia_nhap: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    # Đơn vị cơ sở
    so_luong_ton: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    # Đang giữ cho đơn chưa xuất kho
    so_luong_giu: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    # [DB02] Hàng trả về/hư hỏng đang ở khu biệt trữ, không bán. Chỉ giảm qua phiếu hủy hoặc phiếu xuất trả
    so_luong_biet_tru: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    trang_thai: Mapped[TrangThaiLo] = mapped_column(KIEU_TRANG_THAI_LO, server_default="dang_ban")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    san_pham: Mapped[SanPham] = relationship("SanPham", foreign_keys="LoThuoc.san_pham_id", lazy="raise", uselist=False)

    __table_args__ = (
        Index("uq_lo_thuoc__san_pham_id_so_lo_han_su_dung", "san_pham_id", "so_lo", "han_su_dung", unique=True),
        Index("ix_lo_thuoc__san_pham_id_trang_thai_han_su_dung", "san_pham_id", "trang_thai", "han_su_dung"),
        Index("ix_lo_thuoc__han_su_dung", "han_su_dung"),
    )


class BienDongKho(Base):
    """Bảng `bien_dong_kho`.

    Chỉ INSERT. Tồn đầu kỳ = tổng so_luong trước ngày bắt đầu kỳ
    """

    __tablename__ = "bien_dong_kho"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    lo_id: Mapped[int] = mapped_column(Integer, ForeignKey("lo_thuoc.id"))
    loai: Mapped[LoaiBienDong] = mapped_column(KIEU_LOAI_BIEN_DONG)
    khu: Mapped[KhuTon] = mapped_column(KIEU_KHU_TON, server_default="kho_ban")
    # Dương = tăng, âm = giảm (đơn vị cơ sở)
    so_luong: Mapped[int] = mapped_column(Integer)
    # Tồn của lô tại khu này sau biến động
    ton_sau: Mapped[int] = mapped_column(Integer)
    # phieu_nhap, don_hang, phieu_dieu_chinh, phieu_huy, phieu_xuat_tra, yeu_cau_doi_tra
    chung_tu_loai: Mapped[str] = mapped_column(String(30))
    chung_tu_id: Mapped[int] = mapped_column(Integer)
    # Null = hệ thống tự động
    nhan_vien_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lo: Mapped[LoThuoc] = relationship("LoThuoc", foreign_keys="BienDongKho.lo_id", lazy="raise", uselist=False)
    nhan_vien: Mapped[NhanVien | None] = relationship(
        "NhanVien", foreign_keys="BienDongKho.nhan_vien_id", lazy="raise", uselist=False
    )

    __table_args__ = (
        Index("ix_bien_dong_kho__lo_id_created_at", "lo_id", "created_at"),
        Index("ix_bien_dong_kho__chung_tu_loai_chung_tu_id", "chung_tu_loai", "chung_tu_id"),
        Index("ix_bien_dong_kho__created_at", "created_at"),
    )


class PhieuNhap(Base):
    """Bảng `phieu_nhap`."""

    __tablename__ = "phieu_nhap"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_phieu: Mapped[str] = mapped_column(String(30), unique=True)
    nha_cung_cap_id: Mapped[int] = mapped_column(Integer, ForeignKey("nha_cung_cap.id"))
    so_hoa_don_ncc: Mapped[str | None] = mapped_column(String(50))
    nhan_vien_id: Mapped[int] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    ngay_nhap: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    tong_tien: Mapped[Decimal] = mapped_column(Numeric(16, 2), server_default=text("0"))
    ghi_chu: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    nha_cung_cap: Mapped[NhaCungCap] = relationship(
        "NhaCungCap", foreign_keys="PhieuNhap.nha_cung_cap_id", lazy="raise", uselist=False
    )
    nhan_vien: Mapped[NhanVien] = relationship(
        "NhanVien", foreign_keys="PhieuNhap.nhan_vien_id", lazy="raise", uselist=False
    )
    chi_tiet: Mapped[list[CtPhieuNhap]] = relationship(
        "CtPhieuNhap", foreign_keys="CtPhieuNhap.phieu_nhap_id", lazy="raise", uselist=True, back_populates="phieu_nhap"
    )

    __table_args__ = (Index("ix_phieu_nhap__nha_cung_cap_id_ngay_nhap", "nha_cung_cap_id", "ngay_nhap"),)


class CtPhieuNhap(Base):
    """Bảng `ct_phieu_nhap`.

    Service kiểm tra lo_thuoc.san_pham_id = don_vi_quy_doi.san_pham_id. Cộng vào lô cũ: gia_nhap của lô tính lại bình
    quân gia quyền
    """

    __tablename__ = "ct_phieu_nhap"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    phieu_nhap_id: Mapped[int] = mapped_column(Integer, ForeignKey("phieu_nhap.id"))
    lo_id: Mapped[int] = mapped_column(Integer, ForeignKey("lo_thuoc.id"))
    # Đơn vị nhập, VD: hộp
    don_vi_id: Mapped[int] = mapped_column(Integer, ForeignKey("don_vi_quy_doi.id"))
    # Theo đơn vị nhập
    so_luong: Mapped[int] = mapped_column(Integer)
    # so_luong x he_so
    so_luong_co_so: Mapped[int] = mapped_column(Integer)
    # Theo đơn vị nhập
    gia_nhap: Mapped[Decimal] = mapped_column(Numeric(14, 2))

    phieu_nhap: Mapped[PhieuNhap] = relationship(
        "PhieuNhap", foreign_keys="CtPhieuNhap.phieu_nhap_id", lazy="raise", uselist=False, back_populates="chi_tiet"
    )
    lo: Mapped[LoThuoc] = relationship("LoThuoc", foreign_keys="CtPhieuNhap.lo_id", lazy="raise", uselist=False)
    don_vi: Mapped[DonViQuyDoi] = relationship(
        "DonViQuyDoi", foreign_keys="CtPhieuNhap.don_vi_id", lazy="raise", uselist=False
    )

    __table_args__ = (
        Index("ix_ct_phieu_nhap__phieu_nhap_id", "phieu_nhap_id"),
        Index("ix_ct_phieu_nhap__lo_id", "lo_id"),
    )


class PhieuKiemKe(Base):
    """Bảng `phieu_kiem_ke`."""

    __tablename__ = "phieu_kiem_ke"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_phieu: Mapped[str] = mapped_column(String(30), unique=True)
    # Null = kiểm kê toàn kho
    danh_muc_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("danh_muc.id"))
    nhan_vien_id: Mapped[int] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    trang_thai: Mapped[TrangThaiKiemKe] = mapped_column(KIEU_TRANG_THAI_KIEM_KE, server_default="dang_kiem")
    thoi_diem_chup_ton: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    chot_luc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    danh_muc: Mapped[DanhMuc | None] = relationship(
        "DanhMuc", foreign_keys="PhieuKiemKe.danh_muc_id", lazy="raise", uselist=False
    )
    nhan_vien: Mapped[NhanVien] = relationship(
        "NhanVien", foreign_keys="PhieuKiemKe.nhan_vien_id", lazy="raise", uselist=False
    )
    chi_tiet: Mapped[list[CtKiemKe]] = relationship(
        "CtKiemKe", foreign_keys="CtKiemKe.phieu_kiem_ke_id", lazy="raise", uselist=True, back_populates="phieu_kiem_ke"
    )


class CtKiemKe(Base):
    """Bảng `ct_kiem_ke`."""

    __tablename__ = "ct_kiem_ke"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    phieu_kiem_ke_id: Mapped[int] = mapped_column(Integer, ForeignKey("phieu_kiem_ke.id"))
    lo_id: Mapped[int] = mapped_column(Integer, ForeignKey("lo_thuoc.id"))
    so_luong_so_sach: Mapped[int] = mapped_column(Integer)
    so_luong_thuc_te: Mapped[int | None] = mapped_column(Integer)
    # thuc_te - so_sach
    chenh_lech: Mapped[int | None] = mapped_column(Integer)

    phieu_kiem_ke: Mapped[PhieuKiemKe] = relationship(
        "PhieuKiemKe", foreign_keys="CtKiemKe.phieu_kiem_ke_id", lazy="raise", uselist=False, back_populates="chi_tiet"
    )
    lo: Mapped[LoThuoc] = relationship("LoThuoc", foreign_keys="CtKiemKe.lo_id", lazy="raise", uselist=False)

    __table_args__ = (
        Index("uq_ct_kiem_ke__phieu_kiem_ke_id_lo_id", "phieu_kiem_ke_id", "lo_id", unique=True),
        Index("ix_ct_kiem_ke__lo_id", "lo_id"),
    )


class PhieuDieuChinh(Base):
    """Bảng `phieu_dieu_chinh`.

    CHECK (nguoi_duyet_id <> nguoi_lap_id). Tồn chỉ thay đổi khi da_duyet
    """

    __tablename__ = "phieu_dieu_chinh"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_phieu: Mapped[str] = mapped_column(String(30), unique=True)
    phieu_kiem_ke_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("phieu_kiem_ke.id"))
    ly_do: Mapped[str] = mapped_column(Text)
    trang_thai_duyet: Mapped[TrangThaiDuyet] = mapped_column(KIEU_TRANG_THAI_DUYET, server_default="cho_duyet")
    nguoi_lap_id: Mapped[int] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    nguoi_duyet_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    ly_do_tu_choi: Mapped[str | None] = mapped_column(Text)
    duyet_luc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    phieu_kiem_ke: Mapped[PhieuKiemKe | None] = relationship(
        "PhieuKiemKe", foreign_keys="PhieuDieuChinh.phieu_kiem_ke_id", lazy="raise", uselist=False
    )
    nguoi_lap: Mapped[NhanVien] = relationship(
        "NhanVien", foreign_keys="PhieuDieuChinh.nguoi_lap_id", lazy="raise", uselist=False
    )
    nguoi_duyet: Mapped[NhanVien | None] = relationship(
        "NhanVien", foreign_keys="PhieuDieuChinh.nguoi_duyet_id", lazy="raise", uselist=False
    )
    chi_tiet: Mapped[list[CtPhieuDieuChinh]] = relationship(
        "CtPhieuDieuChinh",
        foreign_keys="CtPhieuDieuChinh.phieu_dieu_chinh_id",
        lazy="raise",
        uselist=True,
        back_populates="phieu_dieu_chinh",
    )


class CtPhieuDieuChinh(Base):
    """Bảng `ct_phieu_dieu_chinh`."""

    __tablename__ = "ct_phieu_dieu_chinh"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    phieu_dieu_chinh_id: Mapped[int] = mapped_column(Integer, ForeignKey("phieu_dieu_chinh.id"))
    lo_id: Mapped[int] = mapped_column(Integer, ForeignKey("lo_thuoc.id"))
    # Dương = tăng, âm = giảm (đơn vị cơ sở)
    so_luong_thay_doi: Mapped[int] = mapped_column(Integer)

    phieu_dieu_chinh: Mapped[PhieuDieuChinh] = relationship(
        "PhieuDieuChinh",
        foreign_keys="CtPhieuDieuChinh.phieu_dieu_chinh_id",
        lazy="raise",
        uselist=False,
        back_populates="chi_tiet",
    )
    lo: Mapped[LoThuoc] = relationship("LoThuoc", foreign_keys="CtPhieuDieuChinh.lo_id", lazy="raise", uselist=False)

    __table_args__ = (Index("ix_ct_phieu_dieu_chinh__phieu_dieu_chinh_id", "phieu_dieu_chinh_id"),)


class PhieuHuy(Base):
    """Bảng `phieu_huy`.

    CHECK (nguoi_duyet_id <> nguoi_lap_id)
    """

    __tablename__ = "phieu_huy"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_phieu: Mapped[str] = mapped_column(String(30), unique=True)
    ly_do: Mapped[LyDoHuyHang] = mapped_column(KIEU_LY_DO_HUY_HANG)
    mo_ta: Mapped[str | None] = mapped_column(Text)
    bien_ban_url: Mapped[str | None] = mapped_column(String(500))
    trang_thai_duyet: Mapped[TrangThaiDuyet] = mapped_column(KIEU_TRANG_THAI_DUYET, server_default="cho_duyet")
    nguoi_lap_id: Mapped[int] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    nguoi_duyet_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    ly_do_tu_choi: Mapped[str | None] = mapped_column(Text)
    duyet_luc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    nguoi_lap: Mapped[NhanVien] = relationship(
        "NhanVien", foreign_keys="PhieuHuy.nguoi_lap_id", lazy="raise", uselist=False
    )
    nguoi_duyet: Mapped[NhanVien | None] = relationship(
        "NhanVien", foreign_keys="PhieuHuy.nguoi_duyet_id", lazy="raise", uselist=False
    )
    chi_tiet: Mapped[list[CtPhieuHuy]] = relationship(
        "CtPhieuHuy", foreign_keys="CtPhieuHuy.phieu_huy_id", lazy="raise", uselist=True, back_populates="phieu_huy"
    )


class CtPhieuHuy(Base):
    """Bảng `ct_phieu_huy`."""

    __tablename__ = "ct_phieu_huy"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    phieu_huy_id: Mapped[int] = mapped_column(Integer, ForeignKey("phieu_huy.id"))
    lo_id: Mapped[int] = mapped_column(Integer, ForeignKey("lo_thuoc.id"))
    # [DB02] Hủy hàng biệt trữ thì trừ so_luong_biet_tru
    tu_khu: Mapped[KhuTon] = mapped_column(KIEU_KHU_TON, server_default="kho_ban")
    # Đơn vị cơ sở
    so_luong: Mapped[int] = mapped_column(Integer)

    phieu_huy: Mapped[PhieuHuy] = relationship(
        "PhieuHuy", foreign_keys="CtPhieuHuy.phieu_huy_id", lazy="raise", uselist=False, back_populates="chi_tiet"
    )
    lo: Mapped[LoThuoc] = relationship("LoThuoc", foreign_keys="CtPhieuHuy.lo_id", lazy="raise", uselist=False)

    __table_args__ = (Index("ix_ct_phieu_huy__phieu_huy_id", "phieu_huy_id"),)


class LenhThuHoi(Base):
    """Bảng `lenh_thu_hoi`."""

    __tablename__ = "lenh_thu_hoi"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_lenh: Mapped[str] = mapped_column(String(30), unique=True)
    san_pham_id: Mapped[int] = mapped_column(Integer, ForeignKey("san_pham.id"))
    # [DB17] Null = thu hồi mọi lô của sản phẩm (VD: đình chỉ số đăng ký)
    lo_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("lo_thuoc.id"))
    # Số công văn hoặc thông báo thu hồi
    can_cu: Mapped[str] = mapped_column(String(255))
    muc_do: Mapped[str | None] = mapped_column(String(50))
    trang_thai: Mapped[TrangThaiThuHoi] = mapped_column(KIEU_TRANG_THAI_THU_HOI, server_default="dang_thu_hoi")
    nguoi_tao_id: Mapped[int] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    dong_luc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    san_pham: Mapped[SanPham] = relationship(
        "SanPham", foreign_keys="LenhThuHoi.san_pham_id", lazy="raise", uselist=False
    )
    lo: Mapped[LoThuoc | None] = relationship("LoThuoc", foreign_keys="LenhThuHoi.lo_id", lazy="raise", uselist=False)
    nguoi_tao: Mapped[NhanVien] = relationship(
        "NhanVien", foreign_keys="LenhThuHoi.nguoi_tao_id", lazy="raise", uselist=False
    )
    chi_tiet: Mapped[list[CtLenhThuHoi]] = relationship(
        "CtLenhThuHoi",
        foreign_keys="CtLenhThuHoi.lenh_thu_hoi_id",
        lazy="raise",
        uselist=True,
        back_populates="lenh_thu_hoi",
    )

    __table_args__ = (Index("ix_lenh_thu_hoi__lo_id", "lo_id"),)


class CtLenhThuHoi(Base):
    """Bảng `ct_lenh_thu_hoi`."""

    __tablename__ = "ct_lenh_thu_hoi"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    lenh_thu_hoi_id: Mapped[int] = mapped_column(Integer, ForeignKey("lenh_thu_hoi.id"))
    don_hang_id: Mapped[int] = mapped_column(Integer, ForeignKey("don_hang.id"))
    khach_hang_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("khach_hang.id"))
    # Đơn vị cơ sở, lấy từ phan_bo_lo
    so_luong_da_ban: Mapped[int] = mapped_column(Integer)
    so_luong_da_thu_ve: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    ket_qua_lien_he: Mapped[KetQuaLienHeThuHoi] = mapped_column(
        KIEU_KET_QUA_LIEN_HE_THU_HOI, server_default="chua_lien_he"
    )
    ghi_chu: Mapped[str | None] = mapped_column(Text)
    # Dược sĩ liên hệ (DS13)
    nhan_vien_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    cap_nhat_luc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    lenh_thu_hoi: Mapped[LenhThuHoi] = relationship(
        "LenhThuHoi",
        foreign_keys="CtLenhThuHoi.lenh_thu_hoi_id",
        lazy="raise",
        uselist=False,
        back_populates="chi_tiet",
    )
    don_hang: Mapped[DonHang] = relationship(
        "DonHang", foreign_keys="CtLenhThuHoi.don_hang_id", lazy="raise", uselist=False
    )
    khach_hang: Mapped[KhachHang | None] = relationship(
        "KhachHang", foreign_keys="CtLenhThuHoi.khach_hang_id", lazy="raise", uselist=False
    )
    nhan_vien: Mapped[NhanVien | None] = relationship(
        "NhanVien", foreign_keys="CtLenhThuHoi.nhan_vien_id", lazy="raise", uselist=False
    )

    __table_args__ = (
        Index("uq_ct_lenh_thu_hoi__lenh_thu_hoi_id_don_hang_id", "lenh_thu_hoi_id", "don_hang_id", unique=True),
        Index("ix_ct_lenh_thu_hoi__don_hang_id", "don_hang_id"),
    )


class PhieuXuatTra(Base):
    """Bảng `phieu_xuat_tra`.

    CHECK (nguoi_duyet_id <> nhan_vien_id). Tồn chỉ trừ khi da_duyet
    """

    __tablename__ = "phieu_xuat_tra"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_phieu: Mapped[str] = mapped_column(String(30), unique=True)
    nha_cung_cap_id: Mapped[int] = mapped_column(Integer, ForeignKey("nha_cung_cap.id"))
    lenh_thu_hoi_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("lenh_thu_hoi.id"))
    ly_do: Mapped[str] = mapped_column(Text)
    # Người lập
    nhan_vien_id: Mapped[int] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    # [DB18] Admin duyệt như phiếu hủy (AD12)
    trang_thai_duyet: Mapped[TrangThaiDuyet] = mapped_column(KIEU_TRANG_THAI_DUYET, server_default="cho_duyet")
    nguoi_duyet_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    ly_do_tu_choi: Mapped[str | None] = mapped_column(Text)
    duyet_luc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # NCC đã xác nhận nhận hàng
    da_xac_nhan: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    nha_cung_cap: Mapped[NhaCungCap] = relationship(
        "NhaCungCap", foreign_keys="PhieuXuatTra.nha_cung_cap_id", lazy="raise", uselist=False
    )
    lenh_thu_hoi: Mapped[LenhThuHoi | None] = relationship(
        "LenhThuHoi", foreign_keys="PhieuXuatTra.lenh_thu_hoi_id", lazy="raise", uselist=False
    )
    nhan_vien: Mapped[NhanVien] = relationship(
        "NhanVien", foreign_keys="PhieuXuatTra.nhan_vien_id", lazy="raise", uselist=False
    )
    nguoi_duyet: Mapped[NhanVien | None] = relationship(
        "NhanVien", foreign_keys="PhieuXuatTra.nguoi_duyet_id", lazy="raise", uselist=False
    )
    chi_tiet: Mapped[list[CtPhieuXuatTra]] = relationship(
        "CtPhieuXuatTra",
        foreign_keys="CtPhieuXuatTra.phieu_xuat_tra_id",
        lazy="raise",
        uselist=True,
        back_populates="phieu_xuat_tra",
    )


class CtPhieuXuatTra(Base):
    """Bảng `ct_phieu_xuat_tra`."""

    __tablename__ = "ct_phieu_xuat_tra"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    phieu_xuat_tra_id: Mapped[int] = mapped_column(Integer, ForeignKey("phieu_xuat_tra.id"))
    lo_id: Mapped[int] = mapped_column(Integer, ForeignKey("lo_thuoc.id"))
    # [DB02]
    tu_khu: Mapped[KhuTon] = mapped_column(KIEU_KHU_TON, server_default="kho_ban")
    # Đơn vị cơ sở
    so_luong: Mapped[int] = mapped_column(Integer)
    # [DB18] Giá trị NCC phải hoàn/cấn trừ, mặc định = lo_thuoc.gia_nhap
    don_gia: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))

    phieu_xuat_tra: Mapped[PhieuXuatTra] = relationship(
        "PhieuXuatTra",
        foreign_keys="CtPhieuXuatTra.phieu_xuat_tra_id",
        lazy="raise",
        uselist=False,
        back_populates="chi_tiet",
    )
    lo: Mapped[LoThuoc] = relationship("LoThuoc", foreign_keys="CtPhieuXuatTra.lo_id", lazy="raise", uselist=False)

    __table_args__ = (Index("ix_ct_phieu_xuat_tra__phieu_xuat_tra_id", "phieu_xuat_tra_id"),)

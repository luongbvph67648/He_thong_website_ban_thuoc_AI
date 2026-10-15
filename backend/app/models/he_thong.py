"""Nhóm nhân sự và hệ thống: các bảng theo docs/database/ERD_da_chinh_sua.dbml."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import (
    KIEU_LOAI_BAI_VIET,
    KIEU_TRANG_THAI_NOI_DUNG,
    KIEU_TRANG_THAI_TAI_KHOAN,
    LoaiBaiViet,
    TrangThaiNoiDung,
    TrangThaiTaiKhoan,
)

if TYPE_CHECKING:
    from app.models.khach_hang import KhachHang


class NhanVien(Base):
    """Bảng `nhan_vien`."""

    __tablename__ = "nhan_vien"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_nhan_vien: Mapped[str] = mapped_column(String(20), unique=True)
    ho_ten: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(150), unique=True)
    so_dien_thoai: Mapped[str | None] = mapped_column(String(20))
    mat_khau_hash: Mapped[str] = mapped_column(String(255))
    # Mỗi nhân viên 1 vai trò (đủ cho đồ án). Nếu cần kiêm nhiệm thì tách bảng nhan_vien_vai_tro
    vai_tro_id: Mapped[int] = mapped_column(Integer, ForeignKey("vai_tro.id"))
    trang_thai: Mapped[TrangThaiTaiKhoan] = mapped_column(KIEU_TRANG_THAI_TAI_KHOAN, server_default="hoat_dong")
    phai_doi_mat_khau: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    so_lan_dang_nhap_sai: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    khoa_den: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    vai_tro: Mapped[VaiTro] = relationship("VaiTro", foreign_keys="NhanVien.vai_tro_id", lazy="raise", uselist=False)


class VaiTro(Base):
    """Bảng `vai_tro`."""

    __tablename__ = "vai_tro"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    # PHARMACIST, WAREHOUSE, ADMIN
    ma: Mapped[str] = mapped_column(String(30), unique=True)
    ten: Mapped[str] = mapped_column(String(100))
    mo_ta: Mapped[str | None] = mapped_column(Text)


class Quyen(Base):
    """Bảng `quyen`."""

    __tablename__ = "quyen"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    # VD: order.confirm, rx_request.review
    ma: Mapped[str] = mapped_column(String(60), unique=True)
    nhom: Mapped[str | None] = mapped_column(String(50))
    mo_ta: Mapped[str | None] = mapped_column(String(255))


class VaiTroQuyen(Base):
    """Bảng `vai_tro_quyen`.

    Seed theo sheet Quyền (RBAC). Khách vãng lai và khách thành viên kiểm tra quyền trong code, không cần bản ghi ở
    đây
    """

    __tablename__ = "vai_tro_quyen"

    vai_tro_id: Mapped[int] = mapped_column(Integer, ForeignKey("vai_tro.id"), primary_key=True)
    quyen_id: Mapped[int] = mapped_column(Integer, ForeignKey("quyen.id"), primary_key=True)
    # Mô tả điều kiện với quyền dạng giới hạn
    gioi_han: Mapped[str | None] = mapped_column(String(255))

    vai_tro: Mapped[VaiTro] = relationship("VaiTro", foreign_keys="VaiTroQuyen.vai_tro_id", lazy="raise", uselist=False)
    quyen: Mapped[Quyen] = relationship("Quyen", foreign_keys="VaiTroQuyen.quyen_id", lazy="raise", uselist=False)


class CauHinh(Base):
    """Bảng `cau_hinh`."""

    __tablename__ = "cau_hinh"

    # VD: nguong_can_han_ngay, thoi_han_doi_tra_ngay
    khoa: Mapped[str] = mapped_column(String(80), primary_key=True)
    gia_tri: Mapped[Any] = mapped_column(JSONB)
    mo_ta: Mapped[str | None] = mapped_column(String(255))
    nhan_vien_cap_nhat_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    nhan_vien_cap_nhat: Mapped[NhanVien | None] = relationship(
        "NhanVien", foreign_keys="CauHinh.nhan_vien_cap_nhat_id", lazy="raise", uselist=False
    )


class NhatKyHeThong(Base):
    """Bảng `nhat_ky_he_thong`.

    Chỉ INSERT. Không ghi mật khẩu, OTP, dữ liệu sức khỏe dạng rõ
    """

    __tablename__ = "nhat_ky_he_thong"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    nhan_vien_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    # tao, sua, xoa, duyet, dang_nhap...
    hanh_dong: Mapped[str] = mapped_column(String(30))
    bang: Mapped[str] = mapped_column(String(60))
    ban_ghi_id: Mapped[str | None] = mapped_column(String(60))
    gia_tri_cu: Mapped[Any | None] = mapped_column(JSONB)
    gia_tri_moi: Mapped[Any | None] = mapped_column(JSONB)
    ip: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    nhan_vien: Mapped[NhanVien | None] = relationship(
        "NhanVien", foreign_keys="NhatKyHeThong.nhan_vien_id", lazy="raise", uselist=False
    )

    __table_args__ = (
        Index("ix_nhat_ky_he_thong__bang_ban_ghi_id", "bang", "ban_ghi_id"),
        Index("ix_nhat_ky_he_thong__nhan_vien_id_created_at", "nhan_vien_id", "created_at"),
    )


class PhienDangNhap(Base):
    """Bảng `phien_dang_nhap`.

    CHECK đúng một trong hai cột khach_hang_id, nhan_vien_id có giá trị. AD01/AD02 khóa tài khoản -> thu hồi mọi phiên
    còn hạn
    """

    __tablename__ = "phien_dang_nhap"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    khach_hang_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("khach_hang.id"))
    nhan_vien_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    refresh_token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    thiet_bi: Mapped[str | None] = mapped_column(String(255))
    ip: Mapped[str | None] = mapped_column(String(45))
    het_han: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Đăng xuất, đổi mật khẩu, bị khóa tài khoản
    thu_hoi_luc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    khach_hang: Mapped[KhachHang | None] = relationship(
        "KhachHang", foreign_keys="PhienDangNhap.khach_hang_id", lazy="raise", uselist=False
    )
    nhan_vien: Mapped[NhanVien | None] = relationship(
        "NhanVien", foreign_keys="PhienDangNhap.nhan_vien_id", lazy="raise", uselist=False
    )

    __table_args__ = (
        Index("ix_phien_dang_nhap__khach_hang_id", "khach_hang_id"),
        Index("ix_phien_dang_nhap__nhan_vien_id", "nhan_vien_id"),
    )


class Banner(Base):
    """Bảng `banner`."""

    __tablename__ = "banner"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    tieu_de: Mapped[str | None] = mapped_column(String(200))
    anh_url: Mapped[str] = mapped_column(String(500))
    lien_ket: Mapped[str | None] = mapped_column(String(500))
    # trang_chu_chinh, trang_chu_phu...
    vi_tri: Mapped[str] = mapped_column(String(30))
    thu_tu: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    bat_dau: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ket_thuc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dang_hien: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class BaiViet(Base):
    """Bảng `bai_viet`."""

    __tablename__ = "bai_viet"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    tieu_de: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(280), unique=True)
    noi_dung: Mapped[str] = mapped_column(Text)
    anh_bia_url: Mapped[str | None] = mapped_column(String(500))
    # [DB13] bai_viet, chinh_sach, faq
    loai: Mapped[LoaiBaiViet] = mapped_column(KIEU_LOAI_BAI_VIET, server_default="bai_viet")
    tac_gia_id: Mapped[int] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    # Bài sức khỏe phải được dược sĩ duyệt (DS10) mới hiển thị
    trang_thai: Mapped[TrangThaiNoiDung] = mapped_column(KIEU_TRANG_THAI_NOI_DUNG, server_default="nhap")
    dua_vao_ai: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    duoc_si_duyet_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    ngay_duyet: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tac_gia: Mapped[NhanVien] = relationship("NhanVien", foreign_keys="BaiViet.tac_gia_id", lazy="raise", uselist=False)
    duoc_si_duyet: Mapped[NhanVien | None] = relationship(
        "NhanVien", foreign_keys="BaiViet.duoc_si_duyet_id", lazy="raise", uselist=False
    )

"""Nhóm AI: các bảng theo docs/database/ERD_da_chinh_sua.dbml."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
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
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import (
    KIEU_LOAI_HOI_THOAI,
    KIEU_NGUON_TRI_THUC,
    KIEU_TRANG_THAI_HOI_THOAI,
    KIEU_VAI_TRO_TIN_NHAN,
    LoaiHoiThoai,
    NguonTriThuc,
    TrangThaiHoiThoai,
    VaiTroTinNhan,
)

if TYPE_CHECKING:
    from app.models.he_thong import NhanVien
    from app.models.khach_hang import KhachHang
    from app.models.san_pham import SanPham


class TaiLieuTriThuc(Base):
    """Bảng `tai_lieu_tri_thuc`.

    Migration: CREATE EXTENSION vector; CREATE INDEX ... USING hnsw (embedding vector_cosine_ops). Không lưu giá, tồn
    kho ở đây
    """

    __tablename__ = "tai_lieu_tri_thuc"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    nguon_loai: Mapped[NguonTriThuc] = mapped_column(KIEU_NGUON_TRI_THUC)
    # id của thong_tin_chuyen_mon, bai_viet... tùy nguon_loai
    nguon_id: Mapped[int | None] = mapped_column(Integer)
    san_pham_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("san_pham.id"))
    # chi_dinh, chong_chi_dinh, lieu_dung_tham_khao...
    truong: Mapped[str | None] = mapped_column(String(50))
    noi_dung: Mapped[str] = mapped_column(Text)
    # loai_san_pham, can_ke_don, danh_muc...
    metadata_: Mapped[Any | None] = mapped_column("metadata", JSONB)
    # Số chiều theo mô hình embedding đã chọn
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024))
    # [DB21] Đổi mô hình thì phải tạo lại toàn bộ vector
    mo_hinh_embedding: Mapped[str | None] = mapped_column(String(100))
    # [DB21] SHA-256 của noi_dung; AD10 bỏ qua đoạn không đổi
    hash_noi_dung: Mapped[str | None] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    san_pham: Mapped[SanPham | None] = relationship(
        "SanPham", foreign_keys="TaiLieuTriThuc.san_pham_id", lazy="raise", uselist=False
    )

    __table_args__ = (
        Index("ix_tai_lieu_tri_thuc__nguon_loai_nguon_id", "nguon_loai", "nguon_id"),
        Index("ix_tai_lieu_tri_thuc__san_pham_id", "san_pham_id"),
    )


class HoiThoai(Base):
    """Bảng `hoi_thoai`."""

    __tablename__ = "hoi_thoai"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    ma_phien: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True)
    # Null = khách vãng lai
    khach_hang_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("khach_hang.id"))
    loai: Mapped[LoaiHoiThoai] = mapped_column(KIEU_LOAI_HOI_THOAI, server_default="ai")
    trang_thai: Mapped[TrangThaiHoiThoai] = mapped_column(KIEU_TRANG_THAI_HOI_THOAI, server_default="dang_mo")
    duoc_si_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    # Tóm tắt khi chuyển dược sĩ (AI04)
    tom_tat: Mapped[str | None] = mapped_column(Text)
    so_dien_thoai_goi_lai: Mapped[str | None] = mapped_column(String(20))
    bi_gan_co: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    # khach_bao_sai, khong_chac_chan, dau_hieu_nguy_hiem
    ly_do_gan_co: Mapped[str | None] = mapped_column(String(100))
    ip_hash: Mapped[str | None] = mapped_column(String(128))
    tong_token: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    chi_phi: Mapped[Decimal] = mapped_column(Numeric(12, 6), server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    dong_luc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    khach_hang: Mapped[KhachHang | None] = relationship(
        "KhachHang", foreign_keys="HoiThoai.khach_hang_id", lazy="raise", uselist=False
    )
    duoc_si: Mapped[NhanVien | None] = relationship(
        "NhanVien", foreign_keys="HoiThoai.duoc_si_id", lazy="raise", uselist=False
    )
    tin_nhan: Mapped[list[TinNhan]] = relationship(
        "TinNhan", foreign_keys="TinNhan.hoi_thoai_id", lazy="raise", uselist=True, back_populates="hoi_thoai"
    )

    __table_args__ = (
        Index("ix_hoi_thoai__trang_thai_created_at", "trang_thai", "created_at"),
        Index("ix_hoi_thoai__bi_gan_co", "bi_gan_co"),
        Index("ix_hoi_thoai__khach_hang_id", "khach_hang_id"),
        Index("ix_hoi_thoai__duoc_si_id_trang_thai", "duoc_si_id", "trang_thai"),
    )


class TinNhan(Base):
    """Bảng `tin_nhan`."""

    __tablename__ = "tin_nhan"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    hoi_thoai_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("hoi_thoai.id"))
    vai_tro: Mapped[VaiTroTinNhan] = mapped_column(KIEU_VAI_TRO_TIN_NHAN)
    # Khi vai_tro = duoc_si
    nhan_vien_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    noi_dung: Mapped[str] = mapped_column(Text)
    # Kết quả phân loại ý định (AI02)
    y_dinh: Mapped[str | None] = mapped_column(String(50))
    # Danh sách san_pham_id hiển thị dạng thẻ
    san_pham_goi_y: Mapped[Any | None] = mapped_column(JSONB)
    dau_hieu_nguy_hiem: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    so_token: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    hoi_thoai: Mapped[HoiThoai] = relationship(
        "HoiThoai", foreign_keys="TinNhan.hoi_thoai_id", lazy="raise", uselist=False, back_populates="tin_nhan"
    )
    nhan_vien: Mapped[NhanVien | None] = relationship(
        "NhanVien", foreign_keys="TinNhan.nhan_vien_id", lazy="raise", uselist=False
    )

    __table_args__ = (Index("ix_tin_nhan__hoi_thoai_id_created_at", "hoi_thoai_id", "created_at"),)


class DanhGiaCauTraLoi(Base):
    """Bảng `danh_gia_cau_tra_loi`."""

    __tablename__ = "danh_gia_cau_tra_loi"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    tin_nhan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tin_nhan.id"))
    # khach, duoc_si
    nguon: Mapped[str] = mapped_column(String(20))
    # huu_ich, khong_huu_ich, dung, sai
    ket_qua: Mapped[str] = mapped_column(String(20))
    # Dược sĩ ghi nội dung đúng (DS12)
    ghi_chu: Mapped[str | None] = mapped_column(Text)
    khach_hang_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("khach_hang.id"))
    nhan_vien_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tin_nhan: Mapped[TinNhan] = relationship(
        "TinNhan", foreign_keys="DanhGiaCauTraLoi.tin_nhan_id", lazy="raise", uselist=False
    )
    khach_hang: Mapped[KhachHang | None] = relationship(
        "KhachHang", foreign_keys="DanhGiaCauTraLoi.khach_hang_id", lazy="raise", uselist=False
    )
    nhan_vien: Mapped[NhanVien | None] = relationship(
        "NhanVien", foreign_keys="DanhGiaCauTraLoi.nhan_vien_id", lazy="raise", uselist=False
    )

    __table_args__ = (Index("ix_danh_gia_cau_tra_loi__tin_nhan_id", "tin_nhan_id"),)


class LichSuTimKiem(Base):
    """Bảng `lich_su_tim_kiem`."""

    __tablename__ = "lich_su_tim_kiem"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    khach_hang_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("khach_hang.id"))
    ma_phien: Mapped[str | None] = mapped_column(String(64))
    tu_khoa: Mapped[str] = mapped_column(String(255))
    # tu_khoa, hybrid
    che_do: Mapped[str | None] = mapped_column(String(20))
    so_ket_qua: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    khach_hang: Mapped[KhachHang | None] = relationship(
        "KhachHang", foreign_keys="LichSuTimKiem.khach_hang_id", lazy="raise", uselist=False
    )

    __table_args__ = (
        Index("ix_lich_su_tim_kiem__so_ket_qua", "so_ket_qua"),
        Index("ix_lich_su_tim_kiem__created_at", "created_at"),
    )


class LichSuXem(Base):
    """Bảng `lich_su_xem`."""

    __tablename__ = "lich_su_xem"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    khach_hang_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("khach_hang.id"))
    ma_phien: Mapped[str | None] = mapped_column(String(64))
    san_pham_id: Mapped[int] = mapped_column(Integer, ForeignKey("san_pham.id"))
    # tim_kiem, goi_y_tuong_tu, mua_kem, danh_cho_ban, chat_ai...
    nguon: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    khach_hang: Mapped[KhachHang | None] = relationship(
        "KhachHang", foreign_keys="LichSuXem.khach_hang_id", lazy="raise", uselist=False
    )
    san_pham: Mapped[SanPham] = relationship(
        "SanPham", foreign_keys="LichSuXem.san_pham_id", lazy="raise", uselist=False
    )

    __table_args__ = (
        Index("ix_lich_su_xem__khach_hang_id_created_at", "khach_hang_id", "created_at"),
        Index("ix_lich_su_xem__san_pham_id", "san_pham_id"),
    )


class LuatMuaKem(Base):
    """Bảng `luat_mua_kem`.

    Job AI08 tính lại định kỳ từ ct_don_hang
    """

    __tablename__ = "luat_mua_kem"

    san_pham_a_id: Mapped[int] = mapped_column(Integer, ForeignKey("san_pham.id"), primary_key=True)
    san_pham_b_id: Mapped[int] = mapped_column(Integer, ForeignKey("san_pham.id"), primary_key=True)
    support: Mapped[Decimal] = mapped_column(Numeric(8, 6))
    confidence: Mapped[Decimal] = mapped_column(Numeric(8, 6))
    lift: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    san_pham_a: Mapped[SanPham] = relationship(
        "SanPham", foreign_keys="LuatMuaKem.san_pham_a_id", lazy="raise", uselist=False
    )
    san_pham_b: Mapped[SanPham] = relationship(
        "SanPham", foreign_keys="LuatMuaKem.san_pham_b_id", lazy="raise", uselist=False
    )


class DeXuatNhapHang(Base):
    """Bảng `de_xuat_nhap_hang`."""

    __tablename__ = "de_xuat_nhap_hang"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    san_pham_id: Mapped[int] = mapped_column(Integer, ForeignKey("san_pham.id"))
    ky_bat_dau: Mapped[date] = mapped_column(Date)
    ky_ket_thuc: Mapped[date] = mapped_column(Date)
    # Nhu cầu dự báo trong kỳ, đơn vị cơ sở
    so_luong_du_bao: Mapped[int] = mapped_column(Integer)
    # Bản chụp tồn khả dụng lúc tính
    ton_kha_dung: Mapped[int] = mapped_column(Integer)
    # max(0, dự báo + tồn tối thiểu - tồn khả dụng)
    so_luong_de_xuat: Mapped[int] = mapped_column(Integer)
    # VD: trung_binh_truot, holt_winters
    mo_hinh: Mapped[str | None] = mapped_column(String(50))
    sai_so_mape: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    # Kho đã lập phiếu nhập theo đề xuất
    da_xu_ly: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    san_pham: Mapped[SanPham] = relationship(
        "SanPham", foreign_keys="DeXuatNhapHang.san_pham_id", lazy="raise", uselist=False
    )

    __table_args__ = (Index("uq_de_xuat_nhap_hang__ky_bat_dau_san_pham_id", "ky_bat_dau", "san_pham_id", unique=True),)

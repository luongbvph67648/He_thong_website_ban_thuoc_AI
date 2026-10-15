"""Nhóm sản phẩm: các bảng theo docs/database/ERD_da_chinh_sua.dbml."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
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
    KIEU_LOAI_SAN_PHAM,
    KIEU_MUC_DO_TUONG_TAC,
    KIEU_TRANG_THAI_KINH_DOANH,
    KIEU_TRANG_THAI_NOI_DUNG,
    LoaiSanPham,
    MucDoTuongTac,
    TrangThaiKinhDoanh,
    TrangThaiNoiDung,
)

if TYPE_CHECKING:
    from app.models.he_thong import NhanVien


class DanhMuc(Base):
    """Bảng `danh_muc`."""

    __tablename__ = "danh_muc"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ten: Mapped[str] = mapped_column(String(150))
    slug: Mapped[str] = mapped_column(String(180), unique=True)
    # Null = danh mục gốc, tối đa 3 cấp
    danh_muc_cha_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("danh_muc.id"))
    anh_url: Mapped[str | None] = mapped_column(String(500))
    thu_tu: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    dang_hien_thi: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    danh_muc_cha: Mapped[DanhMuc | None] = relationship(
        "DanhMuc",
        foreign_keys="DanhMuc.danh_muc_cha_id",
        lazy="raise",
        uselist=False,
        remote_side="DanhMuc.id",
        back_populates="danh_muc_con",
    )
    danh_muc_con: Mapped[list[DanhMuc]] = relationship(
        "DanhMuc",
        foreign_keys="DanhMuc.danh_muc_cha_id",
        lazy="raise",
        uselist=True,
        back_populates="danh_muc_cha",
        remote_side="DanhMuc.danh_muc_cha_id",
    )

    __table_args__ = (Index("ix_danh_muc__danh_muc_cha_id", "danh_muc_cha_id"),)


class ThuongHieu(Base):
    """Bảng `thuong_hieu`."""

    __tablename__ = "thuong_hieu"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ten: Mapped[str] = mapped_column(String(150), unique=True)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NhaSanXuat(Base):
    """Bảng `nha_san_xuat`."""

    __tablename__ = "nha_san_xuat"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ten: Mapped[str] = mapped_column(String(200))
    quoc_gia: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("uq_nha_san_xuat__ten_quoc_gia", "ten", "quoc_gia", unique=True),)


class HoatChat(Base):
    """Bảng `hoat_chat`."""

    __tablename__ = "hoat_chat"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    # Tên chuẩn, VD: Paracetamol
    ten: Mapped[str] = mapped_column(String(200), unique=True)
    # Tên đồng nghĩa phục vụ tìm kiếm, VD: Acetaminophen
    ten_khac: Mapped[str | None] = mapped_column(Text)
    mo_ta: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SanPham(Base):
    """Bảng `san_pham`.

    Migration: thêm index GIN pg_trgm trên unaccent(ten) cho tìm kiếm sai chính tả, không dấu
    """

    __tablename__ = "san_pham"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    sku: Mapped[str] = mapped_column(String(50), unique=True)
    ten: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(280), unique=True)
    loai_san_pham: Mapped[LoaiSanPham] = mapped_column(KIEU_LOAI_SAN_PHAM)
    danh_muc_id: Mapped[int] = mapped_column(Integer, ForeignKey("danh_muc.id"))
    thuong_hieu_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("thuong_hieu.id"))
    nha_san_xuat_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("nha_san_xuat.id"))
    # Số đăng ký lưu hành, dùng để nhận diện ảnh hộp thuốc
    so_dang_ky: Mapped[str | None] = mapped_column(String(50))
    # Viên nén, siro, gói bột...
    dang_bao_che: Mapped[str | None] = mapped_column(String(100))
    # VD: Hộp 10 vỉ x 10 viên
    quy_cach: Mapped[str | None] = mapped_column(String(150))
    # Trẻ em, người lớn... dùng cho bộ lọc
    doi_tuong_su_dung: Mapped[str | None] = mapped_column(String(150))
    # Đơn vị nhỏ nhất: viên, gói, ống, chai
    don_vi_co_so: Mapped[str] = mapped_column(String(30))
    # Theo đơn vị cơ sở, dùng cho cảnh báo HT02
    ton_toi_thieu: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    # Dùng cho nhắc mua lại KTV14
    dung_dinh_ky: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    so_ngay_dung_moi_don_vi: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    # [DB09] Theo đơn vị cơ sở, null = không giới hạn (KVL07, KTV02)
    so_luong_toi_da_moi_don: Mapped[int | None] = mapped_column(Integer)
    # [DB09] Sản phẩm nổi bật trang chủ (KVL01)
    la_noi_bat: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    trang_thai: Mapped[TrangThaiKinhDoanh] = mapped_column(KIEU_TRANG_THAI_KINH_DOANH, server_default="dang_kinh_doanh")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    danh_muc: Mapped[DanhMuc] = relationship("DanhMuc", foreign_keys="SanPham.danh_muc_id", lazy="raise", uselist=False)
    thuong_hieu: Mapped[ThuongHieu | None] = relationship(
        "ThuongHieu", foreign_keys="SanPham.thuong_hieu_id", lazy="raise", uselist=False
    )
    nha_san_xuat: Mapped[NhaSanXuat | None] = relationship(
        "NhaSanXuat", foreign_keys="SanPham.nha_san_xuat_id", lazy="raise", uselist=False
    )
    don_vi_quy_doi: Mapped[list[DonViQuyDoi]] = relationship(
        "DonViQuyDoi", foreign_keys="DonViQuyDoi.san_pham_id", lazy="raise", uselist=True, back_populates="san_pham"
    )
    thanh_phan: Mapped[list[ThanhPhan]] = relationship(
        "ThanhPhan", foreign_keys="ThanhPhan.san_pham_id", lazy="raise", uselist=True, back_populates="san_pham"
    )
    anh_san_pham: Mapped[list[AnhSanPham]] = relationship(
        "AnhSanPham", foreign_keys="AnhSanPham.san_pham_id", lazy="raise", uselist=True, back_populates="san_pham"
    )
    thong_tin_chuyen_mon: Mapped[list[ThongTinChuyenMon]] = relationship(
        "ThongTinChuyenMon",
        foreign_keys="ThongTinChuyenMon.san_pham_id",
        lazy="raise",
        uselist=True,
        back_populates="san_pham",
    )

    __table_args__ = (
        Index("ix_san_pham__so_dang_ky", "so_dang_ky"),
        Index("ix_san_pham__danh_muc_id_trang_thai", "danh_muc_id", "trang_thai"),
        Index("ix_san_pham__loai_san_pham", "loai_san_pham"),
    )


class ThanhPhan(Base):
    """Bảng `thanh_phan`."""

    __tablename__ = "thanh_phan"

    san_pham_id: Mapped[int] = mapped_column(Integer, ForeignKey("san_pham.id"), primary_key=True)
    hoat_chat_id: Mapped[int] = mapped_column(Integer, ForeignKey("hoat_chat.id"), primary_key=True)
    # VD: 500mg
    ham_luong: Mapped[str | None] = mapped_column(String(50))

    san_pham: Mapped[SanPham] = relationship(
        "SanPham", foreign_keys="ThanhPhan.san_pham_id", lazy="raise", uselist=False, back_populates="thanh_phan"
    )
    hoat_chat: Mapped[HoatChat] = relationship(
        "HoatChat", foreign_keys="ThanhPhan.hoat_chat_id", lazy="raise", uselist=False
    )

    __table_args__ = (Index("ix_thanh_phan__hoat_chat_id", "hoat_chat_id"),)


class DonViQuyDoi(Base):
    """Bảng `don_vi_quy_doi`.

    CHECK (he_so >= 1), CHECK (gia_ban >= 0). [DB22] Mỗi sản phẩm đúng 1 dòng he_so = 1 và tối đa 1 dòng la_mac_dinh
    (partial unique)
    """

    __tablename__ = "don_vi_quy_doi"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    san_pham_id: Mapped[int] = mapped_column(Integer, ForeignKey("san_pham.id"))
    # Hộp, vỉ, viên...
    ten_don_vi: Mapped[str] = mapped_column(String(30))
    # Số đơn vị cơ sở trong 1 đơn vị này. Đơn vị cơ sở có he_so = 1
    he_so: Mapped[int] = mapped_column(Integer)
    gia_ban: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    # false = chỉ bán tại quầy
    ban_online: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    la_mac_dinh: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    ma_vach: Mapped[str | None] = mapped_column(String(50))

    san_pham: Mapped[SanPham] = relationship(
        "SanPham", foreign_keys="DonViQuyDoi.san_pham_id", lazy="raise", uselist=False, back_populates="don_vi_quy_doi"
    )

    __table_args__ = (
        Index("uq_don_vi_quy_doi__san_pham_id_ten_don_vi", "san_pham_id", "ten_don_vi", unique=True),
        Index("uq_don_vi_quy_doi__id_san_pham_id", "id", "san_pham_id", unique=True),
        Index("ix_don_vi_quy_doi__ma_vach", "ma_vach"),
    )


class ThongTinChuyenMon(Base):
    """Bảng `thong_tin_chuyen_mon`.

    Mỗi lần sửa tạo phiên bản mới. Phiên bản hiển thị = phiên bản da_duyet mới nhất (DS10)
    """

    __tablename__ = "thong_tin_chuyen_mon"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    san_pham_id: Mapped[int] = mapped_column(Integer, ForeignKey("san_pham.id"))
    phien_ban: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    chi_dinh: Mapped[str | None] = mapped_column(Text)
    chong_chi_dinh: Mapped[str | None] = mapped_column(Text)
    lieu_dung_tham_khao: Mapped[str | None] = mapped_column(Text)
    tac_dung_phu: Mapped[str | None] = mapped_column(Text)
    than_trong: Mapped[str | None] = mapped_column(Text)
    tuong_tac_thuoc: Mapped[str | None] = mapped_column(Text)
    phu_nu_co_thai_cho_con_bu: Mapped[str | None] = mapped_column(Text)
    tre_em: Mapped[str | None] = mapped_column(Text)
    qua_lieu_xu_tri: Mapped[str | None] = mapped_column(Text)
    bao_quan: Mapped[str | None] = mapped_column(Text)
    # Tờ hướng dẫn sử dụng gốc
    file_hdsd_url: Mapped[str | None] = mapped_column(String(500))
    trang_thai: Mapped[TrangThaiNoiDung] = mapped_column(KIEU_TRANG_THAI_NOI_DUNG, server_default="nhap")
    nguoi_soan_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    duoc_si_duyet_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    ngay_duyet: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    san_pham: Mapped[SanPham] = relationship(
        "SanPham",
        foreign_keys="ThongTinChuyenMon.san_pham_id",
        lazy="raise",
        uselist=False,
        back_populates="thong_tin_chuyen_mon",
    )
    nguoi_soan: Mapped[NhanVien | None] = relationship(
        "NhanVien", foreign_keys="ThongTinChuyenMon.nguoi_soan_id", lazy="raise", uselist=False
    )
    duoc_si_duyet: Mapped[NhanVien | None] = relationship(
        "NhanVien", foreign_keys="ThongTinChuyenMon.duoc_si_duyet_id", lazy="raise", uselist=False
    )

    __table_args__ = (
        Index("uq_thong_tin_chuyen_mon__san_pham_id_phien_ban", "san_pham_id", "phien_ban", unique=True),
        Index("ix_thong_tin_chuyen_mon__san_pham_id_trang_thai", "san_pham_id", "trang_thai"),
    )


class AnhSanPham(Base):
    """Bảng `anh_san_pham`."""

    __tablename__ = "anh_san_pham"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    san_pham_id: Mapped[int] = mapped_column(Integer, ForeignKey("san_pham.id"))
    url: Mapped[str] = mapped_column(String(500))
    thu_tu: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    la_anh_chinh: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))

    san_pham: Mapped[SanPham] = relationship(
        "SanPham", foreign_keys="AnhSanPham.san_pham_id", lazy="raise", uselist=False, back_populates="anh_san_pham"
    )

    __table_args__ = (Index("ix_anh_san_pham__san_pham_id", "san_pham_id"),)


class TuongTacHoatChat(Base):
    """Bảng `tuong_tac_hoat_chat`.

    CHECK (hoat_chat_a_id < hoat_chat_b_id): mỗi cặp lưu 1 lần. Dùng để cảnh báo ở DS04, DS05, DS07, DS08 và lọc gợi ý
    AI
    """

    __tablename__ = "tuong_tac_hoat_chat"

    hoat_chat_a_id: Mapped[int] = mapped_column(Integer, ForeignKey("hoat_chat.id"), primary_key=True)
    hoat_chat_b_id: Mapped[int] = mapped_column(Integer, ForeignKey("hoat_chat.id"), primary_key=True)
    muc_do: Mapped[MucDoTuongTac] = mapped_column(KIEU_MUC_DO_TUONG_TAC)
    co_che: Mapped[str | None] = mapped_column(Text)
    khuyen_cao: Mapped[str] = mapped_column(Text)
    nguon_tham_khao: Mapped[str | None] = mapped_column(String(255))
    # Dược sĩ biên soạn (DS10)
    nhan_vien_cap_nhat_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    hoat_chat_a: Mapped[HoatChat] = relationship(
        "HoatChat", foreign_keys="TuongTacHoatChat.hoat_chat_a_id", lazy="raise", uselist=False
    )
    hoat_chat_b: Mapped[HoatChat] = relationship(
        "HoatChat", foreign_keys="TuongTacHoatChat.hoat_chat_b_id", lazy="raise", uselist=False
    )
    nhan_vien_cap_nhat: Mapped[NhanVien | None] = relationship(
        "NhanVien", foreign_keys="TuongTacHoatChat.nhan_vien_cap_nhat_id", lazy="raise", uselist=False
    )

    __table_args__ = (Index("ix_tuong_tac_hoat_chat__hoat_chat_b_id", "hoat_chat_b_id"),)

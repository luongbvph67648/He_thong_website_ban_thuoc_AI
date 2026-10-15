"""Nhóm khách hàng: các bảng theo docs/database/ERD_da_chinh_sua.dbml."""

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
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import (
    KIEU_TRANG_THAI_TAI_KHOAN,
    TrangThaiTaiKhoan,
)

if TYPE_CHECKING:
    from app.models.ban_hang import CtDonHang
    from app.models.he_thong import NhanVien
    from app.models.san_pham import HoatChat, SanPham


class KhachHang(Base):
    """Bảng `khach_hang`.

    Đăng ký bằng SĐT + OTP (bắt buộc), email tùy chọn (KVL09). [DB23] Khi xóa tài khoản: ẩn danh hóa email/SĐT/họ tên
    để giải phóng ràng buộc unique và bảo vệ dữ liệu cá nhân
    """

    __tablename__ = "khach_hang"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ho_ten: Mapped[str] = mapped_column(String(150))
    email: Mapped[str | None] = mapped_column(String(150), unique=True)
    so_dien_thoai: Mapped[str] = mapped_column(String(20), unique=True)
    # bcrypt hoặc Argon2
    mat_khau_hash: Mapped[str] = mapped_column(String(255))
    gioi_tinh: Mapped[str | None] = mapped_column(String(10))
    trang_thai: Mapped[TrangThaiTaiKhoan] = mapped_column(KIEU_TRANG_THAI_TAI_KHOAN, server_default="hoat_dong")
    so_lan_dang_nhap_sai: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    khoa_den: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dong_y_chinh_sach_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    dia_chi: Mapped[list[DiaChi]] = relationship(
        "DiaChi", foreign_keys="DiaChi.khach_hang_id", lazy="raise", uselist=True, back_populates="khach_hang"
    )


class DiaChi(Base):
    """Bảng `dia_chi`.

    [DB22] Partial unique: mỗi khách tối đa 1 địa chỉ la_mac_dinh = true
    """

    __tablename__ = "dia_chi"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    khach_hang_id: Mapped[int] = mapped_column(Integer, ForeignKey("khach_hang.id"))
    ten_nguoi_nhan: Mapped[str] = mapped_column(String(150))
    so_dien_thoai: Mapped[str] = mapped_column(String(20))
    dia_chi_chi_tiet: Mapped[str] = mapped_column(String(300))
    # Mã theo danh mục của đơn vị vận chuyển
    ma_tinh: Mapped[str] = mapped_column(String(20))
    ten_tinh: Mapped[str | None] = mapped_column(String(100))
    # Có thể trống nếu đơn vị vận chuyển dùng địa chỉ 2 cấp
    ma_quan_huyen: Mapped[str | None] = mapped_column(String(20))
    ma_phuong_xa: Mapped[str] = mapped_column(String(20))
    ten_phuong_xa: Mapped[str | None] = mapped_column(String(100))
    la_mac_dinh: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))

    khach_hang: Mapped[KhachHang] = relationship(
        "KhachHang", foreign_keys="DiaChi.khach_hang_id", lazy="raise", uselist=False, back_populates="dia_chi"
    )

    __table_args__ = (Index("ix_dia_chi__khach_hang_id", "khach_hang_id"),)


class HoSoSucKhoe(Base):
    """Bảng `ho_so_suc_khoe`.

    Dữ liệu nhạy cảm: Admin không xem, dược sĩ chỉ xem khi đang xử lý yêu cầu của khách
    """

    __tablename__ = "ho_so_suc_khoe"

    khach_hang_id: Mapped[int] = mapped_column(Integer, ForeignKey("khach_hang.id"), primary_key=True)
    nam_sinh: Mapped[int | None] = mapped_column(Integer)
    # Mã hóa ở mức ứng dụng
    benh_nen: Mapped[str | None] = mapped_column(Text)
    dang_mang_thai: Mapped[bool | None] = mapped_column(Boolean)
    dang_cho_con_bu: Mapped[bool | None] = mapped_column(Boolean)
    dong_y_su_dung: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    dong_y_luc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    khach_hang: Mapped[KhachHang | None] = relationship(
        "KhachHang", foreign_keys="HoSoSucKhoe.khach_hang_id", lazy="raise", uselist=False
    )


class DiUng(Base):
    """Bảng `di_ung`."""

    __tablename__ = "di_ung"

    khach_hang_id: Mapped[int] = mapped_column(Integer, ForeignKey("khach_hang.id"), primary_key=True)
    hoat_chat_id: Mapped[int] = mapped_column(Integer, ForeignKey("hoat_chat.id"), primary_key=True)
    ghi_chu: Mapped[str | None] = mapped_column(String(255))

    khach_hang: Mapped[KhachHang] = relationship(
        "KhachHang", foreign_keys="DiUng.khach_hang_id", lazy="raise", uselist=False
    )
    hoat_chat: Mapped[HoatChat] = relationship(
        "HoatChat", foreign_keys="DiUng.hoat_chat_id", lazy="raise", uselist=False
    )


class DanhGia(Base):
    """Bảng `danh_gia`.

    CHECK (so_sao BETWEEN 1 AND 5). Chỉ tạo khi đơn của ct_don_hang ở da_giao hoặc hoan_tat
    """

    __tablename__ = "danh_gia"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    san_pham_id: Mapped[int] = mapped_column(Integer, ForeignKey("san_pham.id"))
    khach_hang_id: Mapped[int] = mapped_column(Integer, ForeignKey("khach_hang.id"))
    # Mỗi dòng đơn chỉ đánh giá 1 lần
    ct_don_hang_id: Mapped[int] = mapped_column(Integer, ForeignKey("ct_don_hang.id"), unique=True)
    so_sao: Mapped[int] = mapped_column(SmallInteger)
    noi_dung: Mapped[str | None] = mapped_column(Text)
    anh: Mapped[Any | None] = mapped_column(JSONB)
    dang_hien: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    phan_hoi: Mapped[str | None] = mapped_column(Text)
    nhan_vien_phan_hoi_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    san_pham: Mapped[SanPham] = relationship("SanPham", foreign_keys="DanhGia.san_pham_id", lazy="raise", uselist=False)
    khach_hang: Mapped[KhachHang] = relationship(
        "KhachHang", foreign_keys="DanhGia.khach_hang_id", lazy="raise", uselist=False
    )
    ct_don_hang: Mapped[CtDonHang] = relationship(
        "CtDonHang", foreign_keys="DanhGia.ct_don_hang_id", lazy="raise", uselist=False
    )
    nhan_vien_phan_hoi: Mapped[NhanVien | None] = relationship(
        "NhanVien", foreign_keys="DanhGia.nhan_vien_phan_hoi_id", lazy="raise", uselist=False
    )

    __table_args__ = (Index("ix_danh_gia__san_pham_id_dang_hien_created_at", "san_pham_id", "dang_hien", "created_at"),)


class HoiDap(Base):
    """Bảng `hoi_dap`."""

    __tablename__ = "hoi_dap"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    san_pham_id: Mapped[int] = mapped_column(Integer, ForeignKey("san_pham.id"))
    khach_hang_id: Mapped[int] = mapped_column(Integer, ForeignKey("khach_hang.id"))
    cau_hoi: Mapped[str] = mapped_column(Text)
    tra_loi: Mapped[str | None] = mapped_column(Text)
    nhan_vien_tra_loi_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    tra_loi_luc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dang_hien: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    san_pham: Mapped[SanPham] = relationship("SanPham", foreign_keys="HoiDap.san_pham_id", lazy="raise", uselist=False)
    khach_hang: Mapped[KhachHang] = relationship(
        "KhachHang", foreign_keys="HoiDap.khach_hang_id", lazy="raise", uselist=False
    )
    nhan_vien_tra_loi: Mapped[NhanVien | None] = relationship(
        "NhanVien", foreign_keys="HoiDap.nhan_vien_tra_loi_id", lazy="raise", uselist=False
    )

    __table_args__ = (
        Index("ix_hoi_dap__san_pham_id_dang_hien_created_at", "san_pham_id", "dang_hien", "created_at"),
        Index("ix_hoi_dap__tra_loi_luc", "tra_loi_luc"),
    )


class ThongBao(Base):
    """Bảng `thong_bao`.

    CHECK đúng một trong hai cột khach_hang_id, nhan_vien_id có giá trị
    """

    __tablename__ = "thong_bao"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    khach_hang_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("khach_hang.id"))
    nhan_vien_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    # don_hang, don_thuoc, thu_hoi, doi_tra, kho, nhac_mua_lai...
    loai: Mapped[str] = mapped_column(String(50))
    tieu_de: Mapped[str] = mapped_column(String(255))
    noi_dung: Mapped[str | None] = mapped_column(Text)
    lien_ket: Mapped[str | None] = mapped_column(String(500))
    da_doc: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    khach_hang: Mapped[KhachHang | None] = relationship(
        "KhachHang", foreign_keys="ThongBao.khach_hang_id", lazy="raise", uselist=False
    )
    nhan_vien: Mapped[NhanVien | None] = relationship(
        "NhanVien", foreign_keys="ThongBao.nhan_vien_id", lazy="raise", uselist=False
    )

    __table_args__ = (
        Index("ix_thong_bao__khach_hang_id_da_doc", "khach_hang_id", "da_doc"),
        Index("ix_thong_bao__nhan_vien_id_da_doc", "nhan_vien_id", "da_doc"),
    )


class MaOtp(Base):
    """Bảng `ma_otp`."""

    __tablename__ = "ma_otp"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    # SĐT hoặc email
    dich_den: Mapped[str] = mapped_column(String(150))
    ma_hash: Mapped[str] = mapped_column(String(255))
    # dang_ky, quen_mat_khau, don_thuoc_khach
    muc_dich: Mapped[str] = mapped_column(String(30))
    het_han: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    so_lan_thu: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    da_dung: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_ma_otp__dich_den_muc_dich_created_at", "dich_den", "muc_dich", "created_at"),)

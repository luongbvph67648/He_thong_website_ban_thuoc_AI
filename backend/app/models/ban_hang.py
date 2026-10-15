"""Nhóm bán hàng: các bảng theo docs/database/ERD_da_chinh_sua.dbml."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import (
    KIEU_HINH_THUC_NHAN,
    KIEU_HUONG_XU_LY_DOI_TRA,
    KIEU_KENH_BAN,
    KIEU_LOAI_GIAM_GIA,
    KIEU_LOAI_GIAO_DICH,
    KIEU_LOAI_VAN_DON,
    KIEU_LY_DO_DOI_TRA,
    KIEU_PHAM_VI_KHUYEN_MAI,
    KIEU_PHUONG_THUC_THANH_TOAN,
    KIEU_TRANG_THAI_DOI_TRA,
    KIEU_TRANG_THAI_DON,
    KIEU_TRANG_THAI_GIAO_DICH,
    KIEU_TRANG_THAI_PHAN_BO,
    KIEU_TRANG_THAI_THANH_TOAN,
    KIEU_TRANG_THAI_YEU_CAU_DON_THUOC,
    HinhThucNhan,
    HuongXuLyDoiTra,
    KenhBan,
    LoaiGiamGia,
    LoaiGiaoDich,
    LoaiVanDon,
    LyDoDoiTra,
    PhamViKhuyenMai,
    PhuongThucThanhToan,
    TrangThaiDoiTra,
    TrangThaiDon,
    TrangThaiGiaoDich,
    TrangThaiPhanBo,
    TrangThaiThanhToan,
    TrangThaiYeuCauDonThuoc,
)

if TYPE_CHECKING:
    from app.models.he_thong import NhanVien
    from app.models.khach_hang import KhachHang
    from app.models.kho import LoThuoc
    from app.models.san_pham import DanhMuc, SanPham


class GioHang(Base):
    """Bảng `gio_hang`."""

    __tablename__ = "gio_hang"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    khach_hang_id: Mapped[int] = mapped_column(Integer, ForeignKey("khach_hang.id"), unique=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    khach_hang: Mapped[KhachHang] = relationship(
        "KhachHang", foreign_keys="GioHang.khach_hang_id", lazy="raise", uselist=False
    )
    chi_tiet: Mapped[list[CtGioHang]] = relationship(
        "CtGioHang", foreign_keys="CtGioHang.gio_hang_id", lazy="raise", uselist=True, back_populates="gio_hang"
    )


class CtGioHang(Base):
    """Bảng `ct_gio_hang`.

    API phải từ chối sản phẩm loại thuoc_ke_don. Giỏ của khách vãng lai lưu localStorage, gộp vào đây khi đăng nhập
    """

    __tablename__ = "ct_gio_hang"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    gio_hang_id: Mapped[int] = mapped_column(Integer, ForeignKey("gio_hang.id"))
    san_pham_id: Mapped[int] = mapped_column(Integer, ForeignKey("san_pham.id"))
    # [DB08] Khóa ngoại kép (don_vi_id, san_pham_id), xem Ref bên dưới
    don_vi_id: Mapped[int] = mapped_column(Integer)
    so_luong: Mapped[int] = mapped_column(Integer)

    gio_hang: Mapped[GioHang] = relationship(
        "GioHang", foreign_keys="CtGioHang.gio_hang_id", lazy="raise", uselist=False, back_populates="chi_tiet"
    )
    san_pham: Mapped[SanPham] = relationship(
        "SanPham", foreign_keys="CtGioHang.san_pham_id", lazy="raise", uselist=False
    )

    __table_args__ = (
        Index(
            "uq_ct_gio_hang__gio_hang_id_san_pham_id_don_vi_id", "gio_hang_id", "san_pham_id", "don_vi_id", unique=True
        ),
        ForeignKeyConstraint(["don_vi_id", "san_pham_id"], ["don_vi_quy_doi.id", "don_vi_quy_doi.san_pham_id"]),
    )


class DonHang(Base):
    """Bảng `don_hang`.

    Chỉ service máy trạng thái (HT06) được đổi cột trang_thai. Bảng chuyển trạng thái: xem sheet Luồng nghiệp vụ
    """

    __tablename__ = "don_hang"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_don: Mapped[str] = mapped_column(String(20), unique=True)
    # Null = khách lẻ tại quầy
    khach_hang_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("khach_hang.id"))
    kenh_ban: Mapped[KenhBan] = mapped_column(KIEU_KENH_BAN, server_default="online")
    hinh_thuc_nhan: Mapped[HinhThucNhan] = mapped_column(KIEU_HINH_THUC_NHAN, server_default="giao_tan_noi")
    trang_thai: Mapped[TrangThaiDon] = mapped_column(KIEU_TRANG_THAI_DON)
    # [DB07] Null khi cho_khach_xac_nhan (khách chưa chọn); CHECK bắt buộc từ cho_thanh_toan trở đi
    phuong_thuc_tt: Mapped[PhuongThucThanhToan | None] = mapped_column(KIEU_PHUONG_THUC_THANH_TOAN)
    trang_thai_tt: Mapped[TrangThaiThanhToan] = mapped_column(
        KIEU_TRANG_THAI_THANH_TOAN, server_default="chua_thanh_toan"
    )
    # [DB07] N-1: tạo lại được đơn khi đơn trước hủy/hết hạn; partial unique 1 đơn chưa hủy / yêu cầu. Bắt buộc nếu
    # đơn có thuốc kê đơn
    yeu_cau_don_thuoc_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("yeu_cau_don_thuoc.id"))
    # [DB07] Đơn gửi hàng thay thế (DS09) trỏ về đơn gốc, tong_tien = 0
    don_hang_goc_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("don_hang.id"))
    # [DB07] Link xác nhận/thanh toán gửi SMS cho khách vãng lai (DS05), hết hạn theo han_xac_nhan
    token_truy_cap_hash: Mapped[str | None] = mapped_column(String(128))
    ma_giam_gia_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("ma_giam_gia.id"))
    tam_tinh: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    giam_gia: Mapped[Decimal] = mapped_column(Numeric(16, 2), server_default=text("0"))
    phi_van_chuyen: Mapped[Decimal] = mapped_column(Numeric(14, 2), server_default=text("0"))
    tong_tien: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    ten_nguoi_nhan: Mapped[str | None] = mapped_column(String(150))
    sdt_nguoi_nhan: Mapped[str | None] = mapped_column(String(20))
    # Bản chụp địa chỉ tại thời điểm đặt
    dia_chi_giao: Mapped[str | None] = mapped_column(String(500))
    # Mã hành chính theo đơn vị vận chuyển
    ma_tinh: Mapped[str | None] = mapped_column(String(20))
    ma_quan_huyen: Mapped[str | None] = mapped_column(String(20))
    ma_phuong_xa: Mapped[str | None] = mapped_column(String(20))
    ghi_chu: Mapped[str | None] = mapped_column(Text)
    ly_do_huy: Mapped[str | None] = mapped_column(Text)
    # Đơn tạo hộ, POS, đơn từ đơn thuốc
    nhan_vien_tao_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    nhan_vien_xac_nhan_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    # HT03 hủy đơn quá hạn
    han_thanh_toan: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Đơn từ đơn thuốc: hết hạn giữ hàng
    han_xac_nhan: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    khach_hang: Mapped[KhachHang | None] = relationship(
        "KhachHang", foreign_keys="DonHang.khach_hang_id", lazy="raise", uselist=False
    )
    yeu_cau_don_thuoc: Mapped[YeuCauDonThuoc | None] = relationship(
        "YeuCauDonThuoc", foreign_keys="DonHang.yeu_cau_don_thuoc_id", lazy="raise", uselist=False
    )
    don_hang_goc: Mapped[DonHang | None] = relationship(
        "DonHang", foreign_keys="DonHang.don_hang_goc_id", lazy="raise", uselist=False, remote_side="DonHang.id"
    )
    ma_giam_gia: Mapped[MaGiamGia | None] = relationship(
        "MaGiamGia", foreign_keys="DonHang.ma_giam_gia_id", lazy="raise", uselist=False
    )
    nhan_vien_tao: Mapped[NhanVien | None] = relationship(
        "NhanVien", foreign_keys="DonHang.nhan_vien_tao_id", lazy="raise", uselist=False
    )
    nhan_vien_xac_nhan: Mapped[NhanVien | None] = relationship(
        "NhanVien", foreign_keys="DonHang.nhan_vien_xac_nhan_id", lazy="raise", uselist=False
    )
    chi_tiet: Mapped[list[CtDonHang]] = relationship(
        "CtDonHang", foreign_keys="CtDonHang.don_hang_id", lazy="raise", uselist=True, back_populates="don_hang"
    )
    lich_su_trang_thai: Mapped[list[LichSuTrangThai]] = relationship(
        "LichSuTrangThai",
        foreign_keys="LichSuTrangThai.don_hang_id",
        lazy="raise",
        uselist=True,
        back_populates="don_hang",
    )
    thanh_toan: Mapped[list[ThanhToan]] = relationship(
        "ThanhToan", foreign_keys="ThanhToan.don_hang_id", lazy="raise", uselist=True, back_populates="don_hang"
    )
    van_don: Mapped[list[VanDon]] = relationship(
        "VanDon", foreign_keys="VanDon.don_hang_id", lazy="raise", uselist=True, back_populates="don_hang"
    )

    __table_args__ = (
        Index("ix_don_hang__trang_thai_created_at", "trang_thai", "created_at"),
        Index("ix_don_hang__khach_hang_id_created_at", "khach_hang_id", "created_at"),
        Index("ix_don_hang__sdt_nguoi_nhan", "sdt_nguoi_nhan"),
        Index("ix_don_hang__yeu_cau_don_thuoc_id", "yeu_cau_don_thuoc_id"),
    )


class CtDonHang(Base):
    """Bảng `ct_don_hang`."""

    __tablename__ = "ct_don_hang"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    don_hang_id: Mapped[int] = mapped_column(Integer, ForeignKey("don_hang.id"))
    san_pham_id: Mapped[int] = mapped_column(Integer, ForeignKey("san_pham.id"))
    # [DB08] Khóa ngoại kép (don_vi_id, san_pham_id)
    don_vi_id: Mapped[int] = mapped_column(Integer)
    # Bản chụp tại thời điểm bán
    ten_san_pham: Mapped[str] = mapped_column(String(255))
    ten_don_vi: Mapped[str] = mapped_column(String(30))
    he_so: Mapped[int] = mapped_column(Integer)
    # Theo đơn vị bán
    so_luong: Mapped[int] = mapped_column(Integer)
    # Giá tại thời điểm bán, không tham chiếu giá hiện tại
    don_gia: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    # [DB08] Phần giảm giá của mã KM phân bổ cho dòng này, để tính tiền hoàn khi trả một phần
    giam_gia_phan_bo: Mapped[Decimal] = mapped_column(Numeric(14, 2), server_default=text("0"))
    # so_luong x don_gia - giam_gia_phan_bo
    thanh_tien: Mapped[Decimal] = mapped_column(Numeric(16, 2))

    don_hang: Mapped[DonHang] = relationship(
        "DonHang", foreign_keys="CtDonHang.don_hang_id", lazy="raise", uselist=False, back_populates="chi_tiet"
    )
    san_pham: Mapped[SanPham] = relationship(
        "SanPham", foreign_keys="CtDonHang.san_pham_id", lazy="raise", uselist=False
    )
    phan_bo: Mapped[list[PhanBoLo]] = relationship(
        "PhanBoLo", foreign_keys="PhanBoLo.ct_don_hang_id", lazy="raise", uselist=True, back_populates="ct_don_hang"
    )

    __table_args__ = (
        Index("ix_ct_don_hang__don_hang_id", "don_hang_id"),
        Index("ix_ct_don_hang__san_pham_id", "san_pham_id"),
        ForeignKeyConstraint(["don_vi_id", "san_pham_id"], ["don_vi_quy_doi.id", "don_vi_quy_doi.san_pham_id"]),
    )


class PhanBoLo(Base):
    """Bảng `phan_bo_lo`.

    Chìa khóa cho FEFO, truy vết thu hồi và giá vốn theo lô
    """

    __tablename__ = "phan_bo_lo"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ct_don_hang_id: Mapped[int] = mapped_column(Integer, ForeignKey("ct_don_hang.id"))
    lo_id: Mapped[int] = mapped_column(Integer, ForeignKey("lo_thuoc.id"))
    so_luong_co_so: Mapped[int] = mapped_column(Integer)
    # Bản chụp lo_thuoc.gia_nhap, tính lợi nhuận gộp
    gia_von: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    trang_thai: Mapped[TrangThaiPhanBo] = mapped_column(KIEU_TRANG_THAI_PHAN_BO, server_default="dang_giu")
    # [DB19] Bắt buộc khi kho đổi lô khác gợi ý FEFO (KHO03)
    ly_do_doi_lo: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    ct_don_hang: Mapped[CtDonHang] = relationship(
        "CtDonHang", foreign_keys="PhanBoLo.ct_don_hang_id", lazy="raise", uselist=False, back_populates="phan_bo"
    )
    lo: Mapped[LoThuoc] = relationship("LoThuoc", foreign_keys="PhanBoLo.lo_id", lazy="raise", uselist=False)

    __table_args__ = (
        Index("ix_phan_bo_lo__lo_id", "lo_id"),
        Index("ix_phan_bo_lo__ct_don_hang_id", "ct_don_hang_id"),
    )


class LichSuTrangThai(Base):
    """Bảng `lich_su_trang_thai`."""

    __tablename__ = "lich_su_trang_thai"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    don_hang_id: Mapped[int] = mapped_column(Integer, ForeignKey("don_hang.id"))
    tu_trang_thai: Mapped[TrangThaiDon | None] = mapped_column(KIEU_TRANG_THAI_DON)
    den_trang_thai: Mapped[TrangThaiDon] = mapped_column(KIEU_TRANG_THAI_DON)
    nhan_vien_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    khach_hang_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("khach_hang.id"))
    # nguoi_dung, he_thong, webhook_van_chuyen, ipn_thanh_toan
    nguon: Mapped[str | None] = mapped_column(String(30))
    ghi_chu: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    don_hang: Mapped[DonHang] = relationship(
        "DonHang",
        foreign_keys="LichSuTrangThai.don_hang_id",
        lazy="raise",
        uselist=False,
        back_populates="lich_su_trang_thai",
    )
    nhan_vien: Mapped[NhanVien | None] = relationship(
        "NhanVien", foreign_keys="LichSuTrangThai.nhan_vien_id", lazy="raise", uselist=False
    )
    khach_hang: Mapped[KhachHang | None] = relationship(
        "KhachHang", foreign_keys="LichSuTrangThai.khach_hang_id", lazy="raise", uselist=False
    )

    __table_args__ = (Index("ix_lich_su_trang_thai__don_hang_id_created_at", "don_hang_id", "created_at"),)


class ThanhToan(Base):
    """Bảng `thanh_toan`.

    Hoàn tiền = dòng loai hoan_tien; COD ghi dòng thanh_toan khi webhook báo da_giao
    """

    __tablename__ = "thanh_toan"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    don_hang_id: Mapped[int] = mapped_column(Integer, ForeignKey("don_hang.id"))
    loai: Mapped[LoaiGiaoDich] = mapped_column(KIEU_LOAI_GIAO_DICH, server_default="thanh_toan")
    cong_thanh_toan: Mapped[PhuongThucThanhToan] = mapped_column(KIEU_PHUONG_THUC_THANH_TOAN)
    so_tien: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    # Mã giao dịch của VNPay/MoMo, chống xử lý IPN trùng
    ma_giao_dich_cong: Mapped[str | None] = mapped_column(String(100), unique=True)
    trang_thai: Mapped[TrangThaiGiaoDich] = mapped_column(KIEU_TRANG_THAI_GIAO_DICH, server_default="khoi_tao")
    du_lieu_ipn: Mapped[Any | None] = mapped_column(JSONB)
    # [DB05] Giao dịch hoàn tiền trỏ về giao dịch gốc (API hoàn tiền VNPay/MoMo cần mã gốc)
    thanh_toan_goc_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("thanh_toan.id"))
    # [DB05] Hoàn tiền do đổi trả; null = hoàn do hủy đơn
    yeu_cau_doi_tra_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("yeu_cau_doi_tra.id"))
    # [DB05] Admin xác nhận hoàn tiền (AD17) hoặc dược sĩ thu tiền tại quầy
    nhan_vien_xu_ly_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    # [DB05] Ngân hàng, số TK, chủ TK; chỉ khi hoàn thủ công (COD/tiền mặt). Ẩn danh hóa sau khi hoàn tất
    thong_tin_nhan_hoan: Mapped[Any | None] = mapped_column(JSONB)
    # [DB05] Ảnh chứng từ chuyển khoản hoàn tiền
    chung_tu_url: Mapped[str | None] = mapped_column(String(500))
    ghi_chu: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    don_hang: Mapped[DonHang] = relationship(
        "DonHang", foreign_keys="ThanhToan.don_hang_id", lazy="raise", uselist=False, back_populates="thanh_toan"
    )
    thanh_toan_goc: Mapped[ThanhToan | None] = relationship(
        "ThanhToan", foreign_keys="ThanhToan.thanh_toan_goc_id", lazy="raise", uselist=False, remote_side="ThanhToan.id"
    )
    yeu_cau_doi_tra: Mapped[YeuCauDoiTra | None] = relationship(
        "YeuCauDoiTra", foreign_keys="ThanhToan.yeu_cau_doi_tra_id", lazy="raise", uselist=False
    )
    nhan_vien_xu_ly: Mapped[NhanVien | None] = relationship(
        "NhanVien", foreign_keys="ThanhToan.nhan_vien_xu_ly_id", lazy="raise", uselist=False
    )

    __table_args__ = (Index("ix_thanh_toan__don_hang_id", "don_hang_id"),)


class VanDon(Base):
    """Bảng `van_don`."""

    __tablename__ = "van_don"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    # [DB04] 1-N: giao lần đầu, tạo lại vận đơn khi giao lại, vận đơn trả hàng
    don_hang_id: Mapped[int] = mapped_column(Integer, ForeignKey("don_hang.id"))
    loai: Mapped[LoaiVanDon] = mapped_column(KIEU_LOAI_VAN_DON, server_default="giao_hang")
    # [DB04] Chỉ có khi loai = tra_hang
    yeu_cau_doi_tra_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("yeu_cau_doi_tra.id"))
    # GHN, GHTK
    don_vi_van_chuyen: Mapped[str] = mapped_column(String(30))
    ma_van_don: Mapped[str | None] = mapped_column(String(50), unique=True)
    phi: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    khoi_luong_gram: Mapped[int | None] = mapped_column(Integer)
    trang_thai_doi_tac: Mapped[str | None] = mapped_column(String(50))
    du_lieu_webhook: Mapped[Any | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    don_hang: Mapped[DonHang] = relationship(
        "DonHang", foreign_keys="VanDon.don_hang_id", lazy="raise", uselist=False, back_populates="van_don"
    )
    yeu_cau_doi_tra: Mapped[YeuCauDoiTra | None] = relationship(
        "YeuCauDoiTra", foreign_keys="VanDon.yeu_cau_doi_tra_id", lazy="raise", uselist=False
    )

    __table_args__ = (Index("ix_van_don__don_hang_id", "don_hang_id"),)


class YeuCauDonThuoc(Base):
    """Bảng `yeu_cau_don_thuoc`."""

    __tablename__ = "yeu_cau_don_thuoc"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_yeu_cau: Mapped[str] = mapped_column(String(20), unique=True)
    # Null = khách vãng lai (KVL08)
    khach_hang_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("khach_hang.id"))
    # [DB20] tai_quay = dược sĩ nhập đơn khi bán POS (DS08)
    kenh: Mapped[KenhBan] = mapped_column(KIEU_KENH_BAN, server_default="online")
    ho_ten: Mapped[str] = mapped_column(String(150))
    so_dien_thoai: Mapped[str] = mapped_column(String(20))
    # Danh sách khóa file trong kho riêng tư
    anh_don_thuoc: Mapped[Any] = mapped_column(JSONB)
    # Phát hiện ảnh đơn trùng
    hash_anh: Mapped[str | None] = mapped_column(String(128))
    ghi_chu: Mapped[str | None] = mapped_column(Text)
    # Kết quả đọc ảnh, chỉ để gợi ý
    ket_qua_ai: Mapped[Any | None] = mapped_column(JSONB)
    trang_thai: Mapped[TrangThaiYeuCauDonThuoc] = mapped_column(
        KIEU_TRANG_THAI_YEU_CAU_DON_THUOC, server_default="cho_duyet"
    )
    # Dược sĩ đang khóa / đã xử lý
    duoc_si_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    # [DB20] Thời điểm dược sĩ nhận khóa; HT08 tự nhả nếu quá thời gian cấu hình
    khoa_luc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Kết quả checklist kiểm tra đơn (DS04)
    checklist: Mapped[Any | None] = mapped_column(JSONB)
    ly_do_tu_choi: Mapped[str | None] = mapped_column(Text)
    # Chỉ bật khi đơn liên kết chuyển sang dang_soan_hang (thuốc thực sự xuất kho)
    da_su_dung: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    khach_hang: Mapped[KhachHang | None] = relationship(
        "KhachHang", foreign_keys="YeuCauDonThuoc.khach_hang_id", lazy="raise", uselist=False
    )
    duoc_si: Mapped[NhanVien | None] = relationship(
        "NhanVien", foreign_keys="YeuCauDonThuoc.duoc_si_id", lazy="raise", uselist=False
    )
    chi_tiet: Mapped[list[CtYeuCauDonThuoc]] = relationship(
        "CtYeuCauDonThuoc",
        foreign_keys="CtYeuCauDonThuoc.yeu_cau_id",
        lazy="raise",
        uselist=True,
        back_populates="yeu_cau",
    )

    __table_args__ = (
        Index("ix_yeu_cau_don_thuoc__trang_thai_created_at", "trang_thai", "created_at"),
        Index("ix_yeu_cau_don_thuoc__hash_anh", "hash_anh"),
        Index("ix_yeu_cau_don_thuoc__khach_hang_id", "khach_hang_id"),
    )


class CtYeuCauDonThuoc(Base):
    """Bảng `ct_yeu_cau_don_thuoc`."""

    __tablename__ = "ct_yeu_cau_don_thuoc"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    yeu_cau_id: Mapped[int] = mapped_column(Integer, ForeignKey("yeu_cau_don_thuoc.id"))
    # Null = chưa khớp sản phẩm trong CSDL
    san_pham_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("san_pham.id"))
    ten_thuoc_tren_don: Mapped[str] = mapped_column(String(255))
    ham_luong: Mapped[str | None] = mapped_column(String(50))
    so_luong_ke: Mapped[str | None] = mapped_column(String(50))
    # 0 - 1, null nếu dược sĩ nhập tay
    do_tin_cay_ai: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    do_duoc_si_nhap: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))

    yeu_cau: Mapped[YeuCauDonThuoc] = relationship(
        "YeuCauDonThuoc",
        foreign_keys="CtYeuCauDonThuoc.yeu_cau_id",
        lazy="raise",
        uselist=False,
        back_populates="chi_tiet",
    )
    san_pham: Mapped[SanPham | None] = relationship(
        "SanPham", foreign_keys="CtYeuCauDonThuoc.san_pham_id", lazy="raise", uselist=False
    )

    __table_args__ = (Index("ix_ct_yeu_cau_don_thuoc__yeu_cau_id", "yeu_cau_id"),)


class YeuCauDoiTra(Base):
    """Bảng `yeu_cau_doi_tra`."""

    __tablename__ = "yeu_cau_doi_tra"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_yeu_cau: Mapped[str] = mapped_column(String(20), unique=True)
    don_hang_id: Mapped[int] = mapped_column(Integer, ForeignKey("don_hang.id"))
    khach_hang_id: Mapped[int] = mapped_column(Integer, ForeignKey("khach_hang.id"))
    ly_do: Mapped[LyDoDoiTra] = mapped_column(KIEU_LY_DO_DOI_TRA)
    mo_ta: Mapped[str | None] = mapped_column(Text)
    anh: Mapped[Any | None] = mapped_column(JSONB)
    trang_thai: Mapped[TrangThaiDoiTra] = mapped_column(KIEU_TRANG_THAI_DOI_TRA, server_default="cho_duyet")
    huong_xu_ly: Mapped[HuongXuLyDoiTra | None] = mapped_column(KIEU_HUONG_XU_LY_DOI_TRA)
    duoc_si_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    nhan_vien_kho_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("nhan_vien.id"))
    # Tính từ thanh_tien các dòng trả (đã trừ giam_gia_phan_bo)
    so_tien_hoan: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    ly_do_tu_choi: Mapped[str | None] = mapped_column(Text)
    # [DB15] Kho ghi kết quả kiểm khi nhận hàng trả (KHO10)
    ket_qua_kiem_hang: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    don_hang: Mapped[DonHang] = relationship(
        "DonHang", foreign_keys="YeuCauDoiTra.don_hang_id", lazy="raise", uselist=False
    )
    khach_hang: Mapped[KhachHang] = relationship(
        "KhachHang", foreign_keys="YeuCauDoiTra.khach_hang_id", lazy="raise", uselist=False
    )
    duoc_si: Mapped[NhanVien | None] = relationship(
        "NhanVien", foreign_keys="YeuCauDoiTra.duoc_si_id", lazy="raise", uselist=False
    )
    nhan_vien_kho: Mapped[NhanVien | None] = relationship(
        "NhanVien", foreign_keys="YeuCauDoiTra.nhan_vien_kho_id", lazy="raise", uselist=False
    )
    chi_tiet: Mapped[list[CtYeuCauDoiTra]] = relationship(
        "CtYeuCauDoiTra", foreign_keys="CtYeuCauDoiTra.yeu_cau_id", lazy="raise", uselist=True, back_populates="yeu_cau"
    )

    __table_args__ = (
        Index("ix_yeu_cau_doi_tra__don_hang_id", "don_hang_id"),
        Index("ix_yeu_cau_doi_tra__khach_hang_id_created_at", "khach_hang_id", "created_at"),
        Index("ix_yeu_cau_doi_tra__trang_thai_created_at", "trang_thai", "created_at"),
    )


class CtYeuCauDoiTra(Base):
    """Bảng `ct_yeu_cau_doi_tra`.

    Service kiểm tra tổng so_luong đã trả của một dòng đơn không vượt ct_don_hang.so_luong
    """

    __tablename__ = "ct_yeu_cau_doi_tra"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    yeu_cau_id: Mapped[int] = mapped_column(Integer, ForeignKey("yeu_cau_doi_tra.id"))
    ct_don_hang_id: Mapped[int] = mapped_column(Integer, ForeignKey("ct_don_hang.id"))
    # Khách yêu cầu trả, theo đơn vị bán
    so_luong: Mapped[int] = mapped_column(Integer)
    # [DB15] Lô thực nhận về (tra từ phan_bo_lo), để cộng so_luong_biet_tru đúng lô
    lo_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("lo_thuoc.id"))
    # [DB15] Số lượng kho thực nhận, đơn vị cơ sở
    so_luong_nhan: Mapped[int | None] = mapped_column(Integer)

    yeu_cau: Mapped[YeuCauDoiTra] = relationship(
        "YeuCauDoiTra", foreign_keys="CtYeuCauDoiTra.yeu_cau_id", lazy="raise", uselist=False, back_populates="chi_tiet"
    )
    ct_don_hang: Mapped[CtDonHang] = relationship(
        "CtDonHang", foreign_keys="CtYeuCauDoiTra.ct_don_hang_id", lazy="raise", uselist=False
    )
    lo: Mapped[LoThuoc | None] = relationship(
        "LoThuoc", foreign_keys="CtYeuCauDoiTra.lo_id", lazy="raise", uselist=False
    )

    __table_args__ = (
        Index("uq_ct_yeu_cau_doi_tra__yeu_cau_id_ct_don_hang_id", "yeu_cau_id", "ct_don_hang_id", unique=True),
        Index("ix_ct_yeu_cau_doi_tra__ct_don_hang_id", "ct_don_hang_id"),
    )


class KhuyenMai(Base):
    """Bảng `khuyen_mai`.

    Hệ thống tự loại thuốc kê đơn khỏi phạm vi giảm giá
    """

    __tablename__ = "khuyen_mai"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ten: Mapped[str] = mapped_column(String(200))
    loai_giam: Mapped[LoaiGiamGia] = mapped_column(KIEU_LOAI_GIAM_GIA)
    # % hoặc số tiền
    gia_tri: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    # Trần khi giảm theo %
    giam_toi_da: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    don_toi_thieu: Mapped[Decimal] = mapped_column(Numeric(14, 2), server_default=text("0"))
    bat_dau: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ket_thuc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    tong_luot: Mapped[int | None] = mapped_column(Integer)
    luot_moi_khach: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    pham_vi: Mapped[PhamViKhuyenMai] = mapped_column(KIEU_PHAM_VI_KHUYEN_MAI, server_default="toan_bo")
    dang_hoat_dong: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ds_pham_vi: Mapped[list[KhuyenMaiPhamVi]] = relationship(
        "KhuyenMaiPhamVi",
        foreign_keys="KhuyenMaiPhamVi.khuyen_mai_id",
        lazy="raise",
        uselist=True,
        back_populates="khuyen_mai",
    )
    ma_giam_gia: Mapped[list[MaGiamGia]] = relationship(
        "MaGiamGia", foreign_keys="MaGiamGia.khuyen_mai_id", lazy="raise", uselist=True, back_populates="khuyen_mai"
    )


class KhuyenMaiPhamVi(Base):
    """Bảng `khuyen_mai_pham_vi`.

    CHECK đúng một trong hai cột danh_muc_id, san_pham_id có giá trị
    """

    __tablename__ = "khuyen_mai_pham_vi"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    khuyen_mai_id: Mapped[int] = mapped_column(Integer, ForeignKey("khuyen_mai.id"))
    danh_muc_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("danh_muc.id"))
    san_pham_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("san_pham.id"))

    khuyen_mai: Mapped[KhuyenMai] = relationship(
        "KhuyenMai",
        foreign_keys="KhuyenMaiPhamVi.khuyen_mai_id",
        lazy="raise",
        uselist=False,
        back_populates="ds_pham_vi",
    )
    danh_muc: Mapped[DanhMuc | None] = relationship(
        "DanhMuc", foreign_keys="KhuyenMaiPhamVi.danh_muc_id", lazy="raise", uselist=False
    )
    san_pham: Mapped[SanPham | None] = relationship(
        "SanPham", foreign_keys="KhuyenMaiPhamVi.san_pham_id", lazy="raise", uselist=False
    )

    __table_args__ = (Index("ix_khuyen_mai_pham_vi__khuyen_mai_id", "khuyen_mai_id"),)


class MaGiamGia(Base):
    """Bảng `ma_giam_gia`."""

    __tablename__ = "ma_giam_gia"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    khuyen_mai_id: Mapped[int] = mapped_column(Integer, ForeignKey("khuyen_mai.id"))
    ma: Mapped[str] = mapped_column(String(30), unique=True)
    # Tăng khi tạo đơn (SELECT ... FOR UPDATE), giảm lại khi đơn bị hủy
    so_luot_da_dung: Mapped[int] = mapped_column(Integer, server_default=text("0"))

    khuyen_mai: Mapped[KhuyenMai] = relationship(
        "KhuyenMai", foreign_keys="MaGiamGia.khuyen_mai_id", lazy="raise", uselist=False, back_populates="ma_giam_gia"
    )

    __table_args__ = (Index("ix_ma_giam_gia__khuyen_mai_id", "khuyen_mai_id"),)

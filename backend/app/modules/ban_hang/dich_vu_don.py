"""Xử lý đơn: khách xem danh sách và hủy đơn (KTV06), nội bộ xem/lọc, xác nhận, hủy đơn (DS01, DS02, DS03).

Mọi đổi trạng thái đi qua `chuyen_trang_thai` (HT06): nhả giữ/hoàn nhập đúng lô, trả lượt mã và tạo giao dịch hoàn
tiền là hook của máy trạng thái nên chạy trong cùng transaction.
"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.loi import LoiNghiepVu
from app.core.phan_trang import ThamSoPhanTrang, Trang, lay_trang, tao_trang
from app.core.thoi_gian import VN_TZ
from app.models.ban_hang import CtDonHang, DonHang, LichSuTrangThai, MaGiamGia, ThanhToan
from app.models.enums import KenhBan, PhuongThucThanhToan, TrangThaiDon
from app.models.he_thong import NhanVien, VaiTro
from app.models.khach_hang import KhachHang
from app.modules.ban_hang import dat_hang
from app.modules.ban_hang.schemas import (
    DonHangRa,
    DonNoiBoChiTiet,
    DonNoiBoTomTat,
    DonTomTat,
    GiaoDichRa,
    MocTrangThaiNoiBo,
)
from app.modules.ban_hang.trang_thai import (
    NGUON_HE_THONG_HOP_LE,
    NGUON_NGUOI_DUNG,
    TacNhan,
    chuyen_trang_thai,
    tac_nhan_tu_nhan_vien,
)

TT = TrangThaiDon
TU_DA_XAC_NHAN = (
    TT.da_xac_nhan,
    TT.dang_soan_hang,
    TT.cho_lay_hang,
    TT.dang_giao,
    TT.da_giao,
    TT.hoan_tat,
    TT.giao_that_bai,
    TT.hoan_ve_kho,
)
"""Trạng thái nhân viên kho được thấy (DS01): từ "Đã xác nhận" trở đi, không tính đơn hủy trước khi xác nhận."""


def _khong_tim_thay() -> LoiNghiepVu:
    return LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy đơn hàng")


def _so_san_pham():
    return select(func.count()).where(CtDonHang.don_hang_id == DonHang.id).correlate(DonHang).scalar_subquery()


# --- Khách (KTV06) ---


async def danh_sach_cua_khach(
    db: AsyncSession, khach: KhachHang, trang_thai: TT | None, tp: ThamSoPhanTrang
) -> Trang[DonTomTat]:
    """Đơn của chính khách, mới nhất trước (`khach_hang_id` luôn từ token)."""
    stmt = select(DonHang, _so_san_pham()).where(DonHang.khach_hang_id == khach.id)
    if trang_thai is not None:
        stmt = stmt.where(DonHang.trang_thai == trang_thai)
    dong, tong = await lay_trang(db, stmt.order_by(DonHang.created_at.desc(), DonHang.id.desc()), tp, nhieu_cot=True)
    return tao_trang([_tom_tat(DonTomTat, d, n) for d, n in dong], tong, tp)


def _tom_tat[T: DonTomTat](kieu: type[T], d: DonHang, so_san_pham: int, **them) -> T:
    return kieu(
        ma_don=d.ma_don,
        trang_thai=d.trang_thai,
        trang_thai_tt=d.trang_thai_tt,
        phuong_thuc_tt=d.phuong_thuc_tt,
        tong_tien=d.tong_tien,
        so_san_pham=so_san_pham,
        created_at=d.created_at,
        **them,
    )


async def huy_cua_khach(db: AsyncSession, khach: KhachHang, ma_don: str, ly_do: str | None) -> DonHangRa:
    """Khách hủy đơn của mình trước khi sang "Đang soạn hàng" (spec 04 dòng 9, 12, 14). Đơn của người khác hoặc
    không có là 404."""
    don = await db.scalar(select(DonHang).where(DonHang.ma_don == ma_don, DonHang.khach_hang_id == khach.id))
    if don is None:
        raise _khong_tim_thay()
    await chuyen_trang_thai(db, don, TT.da_huy, TacNhan.khach(khach.id), NGUON_NGUOI_DUNG, ly_do)
    return await dat_hang.don_cua_khach(db, khach, ma_don)


# --- Nội bộ (DS01, DS02, DS03) ---


async def _ma_vai_tro(db: AsyncSession, nv: NhanVien) -> str | None:
    return await db.scalar(select(VaiTro.ma).where(VaiTro.id == nv.vai_tro_id))


def _kho_thay_duoc():
    da_tung_xac_nhan = exists().where(
        LichSuTrangThai.don_hang_id == DonHang.id, LichSuTrangThai.den_trang_thai == TT.da_xac_nhan
    )
    return or_(DonHang.trang_thai.in_(TU_DA_XAC_NHAN), and_(DonHang.trang_thai == TT.da_huy, da_tung_xac_nhan))


async def _pham_vi_nhan_vien(db: AsyncSession, nv: NhanVien):
    """Điều kiện SQL theo vai trò: kho chỉ thấy đơn từ "Đã xác nhận"; dược sĩ và Admin thấy mọi đơn."""
    return _kho_thay_duoc() if await _ma_vai_tro(db, nv) == "WAREHOUSE" else None


def _dau_ngay_vn(ngay: date) -> datetime:
    return datetime.combine(ngay, time.min, tzinfo=VN_TZ)


async def danh_sach_noi_bo(
    db: AsyncSession,
    nv: NhanVien,
    tp: ThamSoPhanTrang,
    *,
    trang_thai: TT | None = None,
    tu_ngay: date | None = None,
    den_ngay: date | None = None,
    phuong_thuc_tt: PhuongThucThanhToan | None = None,
    kenh_ban: KenhBan | None = None,
    q: str | None = None,
) -> Trang[DonNoiBoTomTat]:
    stmt = select(DonHang, _so_san_pham())
    gioi_han = await _pham_vi_nhan_vien(db, nv)
    if gioi_han is not None:
        stmt = stmt.where(gioi_han)
    if trang_thai is not None:
        stmt = stmt.where(DonHang.trang_thai == trang_thai)
    if tu_ngay is not None:
        stmt = stmt.where(DonHang.created_at >= _dau_ngay_vn(tu_ngay))
    if den_ngay is not None:
        stmt = stmt.where(DonHang.created_at < _dau_ngay_vn(den_ngay + timedelta(days=1)))
    if phuong_thuc_tt is not None:
        stmt = stmt.where(DonHang.phuong_thuc_tt == phuong_thuc_tt)
    if kenh_ban is not None:
        stmt = stmt.where(DonHang.kenh_ban == kenh_ban)
    if q and q.strip():
        mau = f"%{q.strip().replace('%', r'\%').replace('_', r'\_')}%"
        stmt = stmt.where(
            or_(
                DonHang.ma_don.ilike(mau),
                DonHang.sdt_nguoi_nhan.ilike(mau),
                DonHang.ten_nguoi_nhan.ilike(mau),
            )
        )
    dong, tong = await lay_trang(db, stmt.order_by(DonHang.created_at.desc(), DonHang.id.desc()), tp, nhieu_cot=True)
    return tao_trang(
        [
            _tom_tat(
                DonNoiBoTomTat,
                d,
                n,
                id=d.id,
                kenh_ban=d.kenh_ban,
                ten_nguoi_nhan=d.ten_nguoi_nhan,
                sdt_nguoi_nhan=d.sdt_nguoi_nhan,
            )
            for d, n in dong
        ],
        tong,
        tp,
    )


async def _lay_don(db: AsyncSession, nv: NhanVien, don_id: int) -> DonHang:
    stmt = select(DonHang).where(DonHang.id == don_id).options(selectinload(DonHang.chi_tiet))
    gioi_han = await _pham_vi_nhan_vien(db, nv)
    if gioi_han is not None:
        stmt = stmt.where(gioi_han)
    don = await db.scalar(stmt)
    if don is None:
        raise _khong_tim_thay()
    return don


async def chi_tiet_noi_bo(db: AsyncSession, nv: NhanVien, don_id: int) -> DonNoiBoChiTiet:
    don = await _lay_don(db, nv, don_id)
    kho = await _ma_vai_tro(db, nv) == "WAREHOUSE"
    ma_text = None
    if don.ma_giam_gia_id is not None:
        ma_text = await db.scalar(select(MaGiamGia.ma).where(MaGiamGia.id == don.ma_giam_gia_id))
    ra = dat_hang.don_ra(don, ma_text)
    lich_su = await _lich_su_noi_bo(db, don.id)
    giao_dich = (
        []
        if kho
        else [
            GiaoDichRa(
                id=g.id,
                loai=g.loai,
                cong_thanh_toan=g.cong_thanh_toan,
                so_tien=g.so_tien,
                trang_thai=g.trang_thai,
                created_at=g.created_at,
            )
            for g in (
                await db.execute(select(ThanhToan).where(ThanhToan.don_hang_id == don.id).order_by(ThanhToan.id))
            ).scalars()
        ]
    )
    return DonNoiBoChiTiet(
        **ra.model_dump(exclude={"lich_su"}),
        id=don.id,
        kenh_ban=don.kenh_ban,
        khach_hang_id=None if kho else don.khach_hang_id,
        lich_su=lich_su,
        giao_dich=giao_dich,
    )


async def _lich_su_noi_bo(db: AsyncSession, don_id: int) -> list[MocTrangThaiNoiBo]:
    dong = (
        await db.execute(
            select(LichSuTrangThai, NhanVien.ho_ten, KhachHang.ho_ten)
            .outerjoin(NhanVien, NhanVien.id == LichSuTrangThai.nhan_vien_id)
            .outerjoin(KhachHang, KhachHang.id == LichSuTrangThai.khach_hang_id)
            .where(LichSuTrangThai.don_hang_id == don_id)
            .order_by(LichSuTrangThai.created_at, LichSuTrangThai.id)
        )
    ).all()
    ket_qua = []
    for ls, ten_nv, ten_khach in dong:
        ten = ten_nv or ten_khach or ("Hệ thống" if ls.nguon in NGUON_HE_THONG_HOP_LE else None)
        ket_qua.append(
            MocTrangThaiNoiBo(
                tu_trang_thai=ls.tu_trang_thai,
                den_trang_thai=ls.den_trang_thai,
                thoi_diem=ls.created_at,
                ghi_chu=ls.ghi_chu,
                nguon=ls.nguon,
                nguoi_thuc_hien=ten,
            )
        )
    return ket_qua


async def xac_nhan(db: AsyncSession, nv: NhanVien, don_id: int) -> DonNoiBoChiTiet:
    """DS02: "Chờ xác nhận" sang "Đã xác nhận" để kho soạn hàng."""
    don = await _lay_don(db, nv, don_id)
    await chuyen_trang_thai(db, don, TT.da_xac_nhan, await tac_nhan_tu_nhan_vien(db, nv), NGUON_NGUOI_DUNG)
    return await chi_tiet_noi_bo(db, nv, don_id)


async def huy(db: AsyncSession, nv: NhanVien, don_id: int, ly_do: str) -> DonNoiBoChiTiet:
    """DS03: hủy kèm lý do khi hàng chưa rời kho; nhả giữ/hoàn nhập đúng lô, trả lượt mã, tạo hoàn tiền nếu đã trả."""
    don = await _lay_don(db, nv, don_id)
    await chuyen_trang_thai(db, don, TT.da_huy, await tac_nhan_tu_nhan_vien(db, nv), NGUON_NGUOI_DUNG, ly_do)
    return await chi_tiet_noi_bo(db, nv, don_id)

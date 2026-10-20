"""AD14: báo cáo thống kê tổng hợp cho Admin (doanh thu, lợi nhuận gộp, bán chạy, tồn kho, cận hạn, hiệu quả AI).

Quy ước (QĐ-51): kỳ theo ngày giờ Việt Nam, gồm cả hai đầu. Một đơn tính vào kỳ lúc nó vào `hoan_tat` (lịch sử trạng
thái; thiếu thì lấy `created_at`). Hoàn tiền trừ vào kỳ lúc giao dịch hoàn thành công. Giá vốn lấy từ `phan_bo_lo`
`da_xuat` (đơn giá vốn × số lượng cơ sở) của các đơn đó."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font
from sqlalchemy import ColumnElement, Date, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import VN_TZ, hom_nay_vn
from app.core.tien import cong, lam_tron_vnd, tru
from app.models.ban_hang import CtDonHang, DonHang, LichSuTrangThai, PhanBoLo, ThanhToan
from app.models.enums import LoaiGiaoDich, TrangThaiDon, TrangThaiGiaoDich, TrangThaiLo, TrangThaiPhanBo
from app.models.kho import LoThuoc
from app.models.san_pham import SanPham
from app.modules.bao_cao.schemas import (
    BaoCaoTongHop,
    DoanhThuNgay,
    GiaTriTonTheoTrangThai,
    LoCanHan,
    SanPhamBanChay,
)
from app.modules.giam_sat_ai import dich_vu as giam_sat

SO_NGAY_TOI_DA = 366
SO_BAN_CHAY = 10
SO_LO_CAN_HAN = 20


def khoang_ngay(tu_ngay: date, den_ngay: date) -> tuple[datetime, datetime]:
    """(đầu kỳ, cuối kỳ loại trừ) ở UTC-aware; kiểm tra thứ tự và độ dài."""
    if tu_ngay > den_ngay:
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE",
            "Dữ liệu không hợp lệ",
            chi_tiet=[{"truong": "tu_ngay", "loi": "Ngày bắt đầu phải trước hoặc bằng ngày kết thúc"}],
        )
    if (den_ngay - tu_ngay).days + 1 > SO_NGAY_TOI_DA:
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE",
            "Dữ liệu không hợp lệ",
            chi_tiet=[{"truong": "den_ngay", "loi": f"Kỳ báo cáo tối đa {SO_NGAY_TOI_DA} ngày"}],
        )
    dau = datetime(tu_ngay.year, tu_ngay.month, tu_ngay.day, tzinfo=VN_TZ)
    return dau, datetime(den_ngay.year, den_ngay.month, den_ngay.day, tzinfo=VN_TZ) + timedelta(days=1)


def moc_hoan_tat() -> ColumnElement[datetime]:
    """Thời điểm đơn vào `hoan_tat` (lần gần nhất), mặc định lúc tạo đơn."""
    moc = (
        select(func.max(LichSuTrangThai.created_at))
        .where(LichSuTrangThai.don_hang_id == DonHang.id, LichSuTrangThai.den_trang_thai == TrangThaiDon.hoan_tat)
        .correlate(DonHang)
        .scalar_subquery()
    )
    return func.coalesce(moc, DonHang.created_at)


def _don_hoan_tat_trong_ky(dau: datetime, cuoi: datetime):
    return and_(DonHang.trang_thai == TrangThaiDon.hoan_tat, moc_hoan_tat() >= dau, moc_hoan_tat() < cuoi)


async def _doanh_thu(db: AsyncSession, dau: datetime, cuoi: datetime) -> tuple[int, Decimal, Decimal, Decimal]:
    so_don, doanh_thu = (
        await db.execute(
            select(func.count(), func.coalesce(func.sum(DonHang.tong_tien), 0)).where(_don_hoan_tat_trong_ky(dau, cuoi))
        )
    ).one()
    gia_von = await db.scalar(
        select(func.coalesce(func.sum(PhanBoLo.so_luong_co_so * PhanBoLo.gia_von), 0))
        .join(CtDonHang, CtDonHang.id == PhanBoLo.ct_don_hang_id)
        .join(DonHang, DonHang.id == CtDonHang.don_hang_id)
        .where(PhanBoLo.trang_thai == TrangThaiPhanBo.da_xuat, _don_hoan_tat_trong_ky(dau, cuoi))
    )
    hoan = await db.scalar(
        select(func.coalesce(func.sum(ThanhToan.so_tien), 0)).where(
            ThanhToan.loai == LoaiGiaoDich.hoan_tien,
            ThanhToan.trang_thai == TrangThaiGiaoDich.thanh_cong,
            # Đơn đã hủy chưa từng vào doanh thu: hoàn tiền của nó trả lại khoản trả trước, không phải giảm trừ
            ThanhToan.don_hang_id.in_(select(DonHang.id).where(DonHang.trang_thai != TrangThaiDon.da_huy)),
            func.coalesce(ThanhToan.updated_at, ThanhToan.created_at) >= dau,
            func.coalesce(ThanhToan.updated_at, ThanhToan.created_at) < cuoi,
        )
    )
    return so_don, lam_tron_vnd(Decimal(doanh_thu)), lam_tron_vnd(Decimal(hoan)), lam_tron_vnd(Decimal(gia_von))


async def _theo_ngay(db: AsyncSession, dau: datetime, cuoi: datetime) -> list[DoanhThuNgay]:
    ngay = func.cast(func.timezone("Asia/Ho_Chi_Minh", moc_hoan_tat()), Date)
    dong = (
        await db.execute(
            select(ngay.label("ngay"), func.count(), func.sum(DonHang.tong_tien))
            .where(_don_hoan_tat_trong_ky(dau, cuoi))
            .group_by(ngay)
            .order_by(ngay)
        )
    ).all()
    co = {n: (c, lam_tron_vnd(Decimal(t))) for n, c, t in dong}
    ra = []
    d = dau.astimezone(VN_TZ).date()
    het = (cuoi - timedelta(days=1)).astimezone(VN_TZ).date()
    while d <= het:
        so, tien = co.get(d, (0, Decimal(0)))
        ra.append(DoanhThuNgay(ngay=d, so_don=so, doanh_thu=tien))
        d += timedelta(days=1)
    return ra


async def _ban_chay(db: AsyncSession, dau: datetime, cuoi: datetime) -> list[SanPhamBanChay]:
    so_luong = func.sum(CtDonHang.so_luong * CtDonHang.he_so)
    dong = (
        await db.execute(
            select(SanPham.id, SanPham.sku, SanPham.ten, so_luong, func.sum(CtDonHang.thanh_tien))
            .join(CtDonHang, CtDonHang.san_pham_id == SanPham.id)
            .join(DonHang, DonHang.id == CtDonHang.don_hang_id)
            .where(_don_hoan_tat_trong_ky(dau, cuoi))
            .group_by(SanPham.id, SanPham.sku, SanPham.ten)
            .order_by(so_luong.desc(), SanPham.id)
            .limit(SO_BAN_CHAY)
        )
    ).all()
    return [
        SanPhamBanChay(san_pham_id=i, sku=sku, ten=ten, so_luong_co_so=int(sl), doanh_thu=lam_tron_vnd(Decimal(tien)))
        for i, sku, ten, sl, tien in dong
    ]


async def _ton_kho(db: AsyncSession) -> tuple[Decimal, list[GiaTriTonTheoTrangThai]]:
    gia_tri = func.sum(LoThuoc.so_luong_ton * LoThuoc.gia_nhap)
    dong = (
        await db.execute(
            select(LoThuoc.trang_thai, func.sum(LoThuoc.so_luong_ton), gia_tri)
            .where(LoThuoc.so_luong_ton > 0)
            .group_by(LoThuoc.trang_thai)
            .order_by(LoThuoc.trang_thai)
        )
    ).all()
    theo = [
        GiaTriTonTheoTrangThai(trang_thai=getattr(t, "value", t), so_luong=int(sl), gia_tri=lam_tron_vnd(Decimal(gt)))
        for t, sl, gt in dong
    ]
    tong = cong(*[g.gia_tri for g in theo if g.trang_thai != TrangThaiLo.het_han.value]) if theo else Decimal(0)
    return tong, theo


async def _can_han(db: AsyncSession) -> tuple[int, list[LoCanHan]]:
    dieu_kien = [LoThuoc.trang_thai == TrangThaiLo.can_han, LoThuoc.so_luong_ton > 0]
    so_lo = await db.scalar(select(func.count()).select_from(LoThuoc).where(*dieu_kien)) or 0
    hom_nay = hom_nay_vn()
    dong = (
        await db.execute(
            select(LoThuoc, SanPham.sku, SanPham.ten)
            .join(SanPham, SanPham.id == LoThuoc.san_pham_id)
            .where(*dieu_kien)
            .order_by(LoThuoc.han_su_dung, LoThuoc.id)
            .limit(SO_LO_CAN_HAN)
        )
    ).all()
    return so_lo, [
        LoCanHan(
            lo_id=lo.id,
            sku=sku,
            ten_san_pham=ten,
            so_lo=lo.so_lo,
            han_su_dung=lo.han_su_dung,
            con_ngay=(lo.han_su_dung - hom_nay).days,
            so_luong_ton=lo.so_luong_ton,
            gia_tri=lam_tron_vnd(Decimal(lo.so_luong_ton) * lo.gia_nhap),
        )
        for lo, sku, ten in dong
    ]


async def bao_cao(db: AsyncSession, tu_ngay: date, den_ngay: date) -> BaoCaoTongHop:
    dau, cuoi = khoang_ngay(tu_ngay, den_ngay)
    so_don, doanh_thu, hoan, gia_von = await _doanh_thu(db, dau, cuoi)
    thuan = tru(doanh_thu, hoan)
    ton, ton_theo = await _ton_kho(db)
    so_lo, lo = await _can_han(db)
    return BaoCaoTongHop(
        tu_ngay=tu_ngay,
        den_ngay=den_ngay,
        so_don_hoan_tat=so_don,
        doanh_thu=doanh_thu,
        hoan_tien=hoan,
        doanh_thu_thuan=thuan,
        gia_von=gia_von,
        loi_nhuan_gop=tru(thuan, gia_von),
        doanh_thu_theo_ngay=await _theo_ngay(db, dau, cuoi),
        ban_chay=await _ban_chay(db, dau, cuoi),
        gia_tri_ton_kho=ton,
        ton_kho_theo_trang_thai=ton_theo,
        so_lo_can_han=so_lo,
        lo_can_han=lo,
        hieu_qua_ai=await giam_sat.thong_ke(db, tu_ngay=tu_ngay, den_ngay=den_ngay),
    )


def _an_toan(gia_tri: str | None) -> str | None:
    """Chuỗi bắt đầu bằng `= + - @` bị Excel hiểu là công thức: thêm dấu nháy để thành văn bản."""
    if gia_tri and gia_tri[0] in "=+-@\t\r":
        return "'" + gia_tri
    return gia_tri


def _tieu_de(ws, dong: list[str]) -> None:
    ws.append(dong)
    for o in ws[ws.max_row]:
        o.font = Font(bold=True)


async def xuat_excel(db: AsyncSession, tu_ngay: date, den_ngay: date) -> bytes:
    b = await bao_cao(db, tu_ngay, den_ngay)
    sach = Workbook()
    ws = sach.active
    ws.title = "Tổng quan"
    ws.append([f"Báo cáo tổng hợp {tu_ngay:%d/%m/%Y} - {den_ngay:%d/%m/%Y}"])
    ws["A1"].font = Font(bold=True)
    for nhan, v in (
        ("Số đơn hoàn tất", b.so_don_hoan_tat),
        ("Doanh thu", b.doanh_thu),
        ("Hoàn tiền", b.hoan_tien),
        ("Doanh thu thuần", b.doanh_thu_thuan),
        ("Giá vốn", b.gia_von),
        ("Lợi nhuận gộp", b.loi_nhuan_gop),
        ("Giá trị tồn kho", b.gia_tri_ton_kho),
        ("Số lô cận hạn", b.so_lo_can_han),
        ("Hội thoại AI", b.hieu_qua_ai.tong_hoi_thoai),
        ("Tỉ lệ chuyển dược sĩ", b.hieu_qua_ai.ty_le_chuyen_duoc_si),
        ("Chi phí AI (USD)", b.hieu_qua_ai.tong_chi_phi_usd),
    ):
        ws.append([nhan, v])
    ws2 = sach.create_sheet("Theo ngày")
    _tieu_de(ws2, ["Ngày", "Số đơn", "Doanh thu"])
    for d in b.doanh_thu_theo_ngay:
        ws2.append([d.ngay, d.so_don, d.doanh_thu])
    ws3 = sach.create_sheet("Bán chạy")
    _tieu_de(ws3, ["SKU", "Sản phẩm", "Số lượng (đơn vị cơ sở)", "Doanh thu"])
    for s in b.ban_chay:
        ws3.append([_an_toan(s.sku), _an_toan(s.ten), s.so_luong_co_so, s.doanh_thu])
    ws4 = sach.create_sheet("Cận hạn")
    _tieu_de(ws4, ["SKU", "Sản phẩm", "Số lô", "Hạn sử dụng", "Còn (ngày)", "Tồn", "Giá trị"])
    for lo in b.lo_can_han:
        ws4.append(
            [
                _an_toan(lo.sku),
                _an_toan(lo.ten_san_pham),
                _an_toan(lo.so_lo),
                lo.han_su_dung,
                lo.con_ngay,
                lo.so_luong_ton,
                lo.gia_tri,
            ]
        )
    ra = BytesIO()
    sach.save(ra)
    return ra.getvalue()

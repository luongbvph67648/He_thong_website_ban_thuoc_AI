"""AI09 (job hằng tuần) và KHO14 (xem đề xuất): dự báo nhu cầu 30 ngày theo sản phẩm từ lượng xuất kho mỗi tuần.

Nguồn: `phan_bo_lo` ở trạng thái `da_xuat` (đã trừ hoàn nhập), gom theo tuần giờ Việt Nam (thứ Hai là đầu tuần), tính
theo thời điểm xuất kho (`updated_at` lúc `xuat_theo_phan_bo`). Tuần đang diễn ra chưa đủ nên không dùng."""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import Text, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.core.phan_trang import ThamSoPhanTrang, Trang, lay_trang, tao_trang
from app.core.thoi_gian import hom_nay_vn
from app.models.ai import DeXuatNhapHang
from app.models.ban_hang import CtDonHang, PhanBoLo
from app.models.enums import TrangThaiKinhDoanh, TrangThaiPhanBo
from app.models.san_pham import SanPham
from app.modules.ai_quan_tri import cau_hinh_ai
from app.modules.cua_hang.hien_thi import ton_kha_dung
from app.modules.du_bao import mo_hinh
from app.modules.du_bao.schemas import BieuDoDeXuat, DeXuatRa, DiemTuan, KyDeXuat

SO_TUAN_LICH_SU = 52
SO_TUAN_BIEU_DO = 26
SO_NGAY_KY = 30
MO_HINH_KHONG_CO_LICH_SU = "khong_co_lich_su"


def dau_tuan(ngay: date) -> date:
    return ngay - timedelta(days=ngay.weekday())


@dataclass
class KetQuaAi09:
    bo_qua: bool = False
    ky_bat_dau: date | None = None
    so_san_pham: int = 0
    so_can_nhap: int = 0
    loi: list[int] = field(default_factory=list)


async def chuoi_xuat_theo_tuan(
    db: AsyncSession, den_tuan: date, san_pham_ids: list[int] | None = None
) -> dict[int, dict[date, int]]:
    """`{san_pham_id: {đầu tuần: số lượng cơ sở đã xuất}}` cho các tuần đủ trong `SO_TUAN_LICH_SU` tuần kết thúc trước
    `den_tuan` (đầu tuần hiện tại)."""
    tu = den_tuan - timedelta(weeks=SO_TUAN_LICH_SU)
    thoi_diem = func.coalesce(PhanBoLo.updated_at, PhanBoLo.created_at)
    tuan = func.cast(func.date_trunc("week", func.timezone("Asia/Ho_Chi_Minh", thoi_diem)), Text)
    dau = and_(
        func.timezone("Asia/Ho_Chi_Minh", thoi_diem) >= tu,
        func.timezone("Asia/Ho_Chi_Minh", thoi_diem) < den_tuan,
    )
    stmt = (
        select(CtDonHang.san_pham_id, tuan, func.sum(PhanBoLo.so_luong_co_so))
        .join(CtDonHang, CtDonHang.id == PhanBoLo.ct_don_hang_id)
        .where(PhanBoLo.trang_thai == TrangThaiPhanBo.da_xuat, dau)
        .group_by(CtDonHang.san_pham_id, tuan)
    )
    if san_pham_ids is not None:
        stmt = stmt.where(CtDonHang.san_pham_id.in_(san_pham_ids))
    ra: dict[int, dict[date, int]] = defaultdict(dict)
    for sp_id, t, so in (await db.execute(stmt)).all():
        ra[sp_id][date.fromisoformat(str(t)[:10])] = int(so)
    return ra


def chuoi_day_du(theo_tuan: dict[date, int], den_tuan: date) -> list[float]:
    """Từ tuần có bán đầu tiên đến tuần đủ cuối (trước `den_tuan`), tuần không bán là 0; rỗng nếu chưa có dữ liệu."""
    if not theo_tuan:
        return []
    dau = min(theo_tuan)
    so_tuan = (den_tuan - dau).days // 7
    return [float(theo_tuan.get(dau + timedelta(weeks=i), 0)) for i in range(so_tuan)]


async def _ton_va_toi_thieu(db: AsyncSession, ids: list[int]) -> dict[int, tuple[int, int]]:
    if not ids:
        return {}
    dong = (
        await db.execute(
            select(SanPham.id, ton_kha_dung(hom_nay_vn()), SanPham.ton_toi_thieu).where(SanPham.id.in_(ids))
        )
    ).all()
    return {sp_id: (int(ton), int(toi_thieu)) for sp_id, ton, toi_thieu in dong}


def _tinh_mot(chuoi: list[float], ton: int, toi_thieu: int) -> tuple[int, int, str, Decimal | None]:
    """(dự báo 30 ngày, đề xuất, tên mô hình, MAPE). Blocking: gọi qua `asyncio.to_thread`."""
    if not chuoi:
        return 0, mo_hinh.de_xuat_nhap(0, toi_thieu, ton), MO_HINH_KHONG_CO_LICH_SU, None
    tuan, ten = mo_hinh.du_bao_tuan(chuoi)
    du_bao = mo_hinh.tong_30_ngay(tuan)
    mape = mo_hinh.mape_4_tuan(chuoi)
    return du_bao, mo_hinh.de_xuat_nhap(du_bao, toi_thieu, ton), ten, None if mape is None else Decimal(str(mape))


async def chay_du_bao(db: AsyncSession) -> KetQuaAi09:
    """Tính kỳ của tuần hiện tại (thứ Hai đến thứ Hai + 29 ngày) cho mọi sản phẩm đang kinh doanh có lịch sử xuất hoặc
    đang dưới tồn tối thiểu. Chạy lại trong cùng tuần thì cập nhật (giữ `da_xu_ly`), không tạo dòng mới."""
    if not await cau_hinh_ai.module_bat(db, "du_bao"):
        return KetQuaAi09(bo_qua=True)
    hom_nay = hom_nay_vn()
    ky_bat_dau = dau_tuan(hom_nay)
    ky_ket_thuc = ky_bat_dau + timedelta(days=SO_NGAY_KY - 1)
    lich_su = await chuoi_xuat_theo_tuan(db, ky_bat_dau)
    ids = list(
        (
            await db.execute(
                select(SanPham.id).where(
                    SanPham.deleted_at.is_(None), SanPham.trang_thai == TrangThaiKinhDoanh.dang_kinh_doanh
                )
            )
        ).scalars()
    )
    ton = await _ton_va_toi_thieu(db, ids)
    hien_co = {
        d.san_pham_id: d
        for d in (await db.execute(select(DeXuatNhapHang).where(DeXuatNhapHang.ky_bat_dau == ky_bat_dau))).scalars()
    }
    ket_qua = KetQuaAi09(ky_bat_dau=ky_bat_dau)
    for sp_id in sorted(ids):
        chuoi = chuoi_day_du(lich_su.get(sp_id, {}), ky_bat_dau)
        ton_kd, toi_thieu = ton.get(sp_id, (0, 0))
        du_bao, de_xuat, ten, mape = await asyncio.to_thread(_tinh_mot, chuoi, ton_kd, toi_thieu)
        if not chuoi and de_xuat == 0:
            continue
        d = hien_co.get(sp_id)
        if d is None:
            d = DeXuatNhapHang(san_pham_id=sp_id, ky_bat_dau=ky_bat_dau, ky_ket_thuc=ky_ket_thuc)
            db.add(d)
        d.so_luong_du_bao, d.ton_kha_dung, d.so_luong_de_xuat, d.mo_hinh, d.sai_so_mape = (
            du_bao,
            ton_kd,
            de_xuat,
            ten,
            mape,
        )
        ket_qua.so_san_pham += 1
        ket_qua.so_can_nhap += 1 if de_xuat > 0 else 0
    await db.flush()
    return ket_qua


# --- KHO14 ---


def _ra(d: DeXuatNhapHang, sp: SanPham) -> DeXuatRa:
    return DeXuatRa(
        id=d.id,
        san_pham_id=sp.id,
        sku=sp.sku,
        ten_san_pham=sp.ten,
        don_vi_co_so=sp.don_vi_co_so,
        ky_bat_dau=d.ky_bat_dau,
        ky_ket_thuc=d.ky_ket_thuc,
        so_luong_du_bao=d.so_luong_du_bao,
        ton_kha_dung=d.ton_kha_dung,
        ton_toi_thieu=sp.ton_toi_thieu,
        so_luong_de_xuat=d.so_luong_de_xuat,
        mo_hinh=d.mo_hinh,
        sai_so_mape=d.sai_so_mape,
        da_xu_ly=d.da_xu_ly,
    )


async def cac_ky(db: AsyncSession) -> list[KyDeXuat]:
    dong = (
        await db.execute(
            select(DeXuatNhapHang.ky_bat_dau, func.max(DeXuatNhapHang.ky_ket_thuc), func.count())
            .group_by(DeXuatNhapHang.ky_bat_dau)
            .order_by(DeXuatNhapHang.ky_bat_dau.desc())
            .limit(12)
        )
    ).all()
    return [KyDeXuat(ky_bat_dau=a, ky_ket_thuc=b, so_san_pham=n) for a, b, n in dong]


async def danh_sach(
    db: AsyncSession,
    tp: ThamSoPhanTrang,
    *,
    ky: date | None,
    chi_can_nhap: bool,
    da_xu_ly: bool | None,
    q: str | None,
) -> Trang[DeXuatRa]:
    if ky is None:
        ky = await db.scalar(select(func.max(DeXuatNhapHang.ky_bat_dau)))
        if ky is None:
            return tao_trang([], 0, tp)
    stmt = (
        select(DeXuatNhapHang, SanPham)
        .join(SanPham, SanPham.id == DeXuatNhapHang.san_pham_id)
        .where(DeXuatNhapHang.ky_bat_dau == ky)
    )
    if chi_can_nhap:
        stmt = stmt.where(DeXuatNhapHang.so_luong_de_xuat > 0)
    if da_xu_ly is not None:
        stmt = stmt.where(DeXuatNhapHang.da_xu_ly.is_(da_xu_ly))
    if q and q.strip():
        mau = f"%{q.strip().replace('%', '').replace('_', '')}%"
        stmt = stmt.where(or_(SanPham.ten.ilike(mau), SanPham.sku.ilike(mau)))
    stmt = stmt.order_by(DeXuatNhapHang.da_xu_ly, DeXuatNhapHang.so_luong_de_xuat.desc(), DeXuatNhapHang.id)
    dong, tong = await lay_trang(db, stmt, tp, nhieu_cot=True)
    return tao_trang([_ra(d, sp) for d, sp in dong], tong, tp)


async def _lay(db: AsyncSession, de_xuat_id: int, *, khoa: bool = False) -> tuple[DeXuatNhapHang, SanPham]:
    stmt = (
        select(DeXuatNhapHang, SanPham)
        .join(SanPham, SanPham.id == DeXuatNhapHang.san_pham_id)
        .where(DeXuatNhapHang.id == de_xuat_id)
    )
    if khoa:
        stmt = stmt.with_for_update(of=DeXuatNhapHang)
    dong = (await db.execute(stmt)).first()
    if dong is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy đề xuất nhập hàng")
    return dong[0], dong[1]


async def danh_dau_da_xu_ly(db: AsyncSession, de_xuat_id: int, da_xu_ly: bool) -> DeXuatRa:
    d, sp = await _lay(db, de_xuat_id, khoa=True)
    d.da_xu_ly = da_xu_ly
    await db.flush()
    return _ra(d, sp)


async def bieu_do(db: AsyncSession, de_xuat_id: int) -> BieuDoDeXuat:
    """Lịch sử xuất 26 tuần đủ gần nhất (kể cả tuần 0) và dự báo 5 tuần tới tính lại bằng chính mô hình của job."""
    d, sp = await _lay(db, de_xuat_id)
    den_tuan = d.ky_bat_dau  # chuỗi chỉ gồm các tuần trước kỳ, đúng dữ liệu job đã dùng
    theo_tuan = (await chuoi_xuat_theo_tuan(db, den_tuan, [sp.id])).get(sp.id, {})
    chuoi = chuoi_day_du(theo_tuan, den_tuan)
    tuan, ten = mo_hinh.du_bao_tuan(chuoi) if chuoi else ([0.0] * mo_hinh.SO_TUAN_DU_BAO, MO_HINH_KHONG_CO_LICH_SU)
    lich_su = [
        DiemTuan(
            tuan_bat_dau=den_tuan - timedelta(weeks=i), so_luong=int(theo_tuan.get(den_tuan - timedelta(weeks=i), 0))
        )
        for i in range(SO_TUAN_BIEU_DO, 0, -1)
    ]
    return BieuDoDeXuat(
        id=d.id,
        ten_san_pham=sp.ten,
        don_vi_co_so=sp.don_vi_co_so,
        mo_hinh=d.mo_hinh or ten,
        lich_su=lich_su,
        du_bao=[DiemTuan(tuan_bat_dau=den_tuan + timedelta(weeks=i), so_luong=round(x)) for i, x in enumerate(tuan)],
    )

"""Kiểm tra và dùng mã giảm giá (KTV04, spec 04 mục 4 bước 3 và 8).

`kiem_tra_ma` chỉ ĐỌC (xem trước ở giỏ/thanh toán). `dung_ma` dành cho lúc tạo đơn (T4.4): khóa khuyến mãi `FOR UPDATE`,
kiểm tra lại, tăng `so_luot_da_dung` trong cùng transaction với việc tạo đơn. `tra_luot` trả lượt khi đơn bị hủy.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc
from app.models.ban_hang import DonHang, KhuyenMai, KhuyenMaiPhamVi, MaGiamGia
from app.models.enums import PhamViKhuyenMai, TrangThaiDon
from app.modules.khuyen_mai.tinh import DongTinh, tinh_giam


class MaLyDo(StrEnum):
    khong_ton_tai = "khong_ton_tai"
    da_tat = "da_tat"
    chua_bat_dau = "chua_bat_dau"
    het_han = "het_han"
    het_luot = "het_luot"
    het_luot_khach = "het_luot_khach"
    khong_co_san_pham = "khong_co_san_pham"
    duoi_don_toi_thieu = "duoi_don_toi_thieu"


THONG_DIEP: dict[MaLyDo, str] = {
    MaLyDo.khong_ton_tai: "Mã giảm giá không tồn tại",
    MaLyDo.da_tat: "Chương trình khuyến mãi đã dừng",
    MaLyDo.chua_bat_dau: "Mã giảm giá chưa đến thời gian áp dụng",
    MaLyDo.het_han: "Mã giảm giá đã hết hạn",
    MaLyDo.het_luot: "Mã giảm giá đã hết lượt sử dụng",
    MaLyDo.het_luot_khach: "Bạn đã dùng hết số lượt cho mã này",
    MaLyDo.khong_co_san_pham: "Giỏ hàng không có sản phẩm nào được áp dụng mã này (thuốc kê đơn không được giảm giá)",
    MaLyDo.duoi_don_toi_thieu: "Giá trị sản phẩm được giảm chưa đạt mức tối thiểu của mã",
}


def chuan_hoa_ma(ma: str) -> str:
    return ma.strip().upper()


@dataclass
class PhamVi:
    """Phạm vi của một khuyến mãi để lọc dòng: toàn bộ, theo danh mục (kể cả con cháu), theo sản phẩm."""

    loai: PhamViKhuyenMai
    danh_muc_ids: frozenset[int]
    san_pham_ids: frozenset[int]


@dataclass
class DongGio:
    """Dòng giỏ/đơn đã quy về đủ thông tin để lọc: `duong_danh_muc` là id danh mục của sản phẩm và mọi tổ tiên."""

    khoa: int
    san_pham_id: int
    duong_danh_muc: frozenset[int]
    la_ke_don: bool
    thanh_tien_goc: Decimal


def _thuoc_pham_vi(d: DongGio, pv: PhamVi) -> bool:
    if d.la_ke_don:
        return False  # thuốc kê đơn luôn bị loại khỏi phần được giảm (CLAUDE.md quy tắc 6)
    if pv.loai == PhamViKhuyenMai.toan_bo:
        return True
    if pv.loai == PhamViKhuyenMai.danh_muc:
        return bool(d.duong_danh_muc & pv.danh_muc_ids)
    return d.san_pham_id in pv.san_pham_ids


async def _pham_vi(db: AsyncSession, km: KhuyenMai) -> PhamVi:
    ds = (await db.execute(select(KhuyenMaiPhamVi).where(KhuyenMaiPhamVi.khuyen_mai_id == km.id))).scalars().all()
    return PhamVi(
        km.pham_vi,
        frozenset(p.danh_muc_id for p in ds if p.danh_muc_id is not None),
        frozenset(p.san_pham_id for p in ds if p.san_pham_id is not None),
    )


async def _luot_da_dung_tong(db: AsyncSession, km_id: int) -> int:
    return int(
        await db.scalar(
            select(func.coalesce(func.sum(MaGiamGia.so_luot_da_dung), 0)).where(MaGiamGia.khuyen_mai_id == km_id)
        )
        or 0
    )


async def _luot_cua_khach(db: AsyncSession, km_id: int, khach_hang_id: int) -> int:
    """Số đơn CHƯA HỦY của khách dùng một mã thuộc khuyến mãi này."""
    return int(
        await db.scalar(
            select(func.count())
            .select_from(DonHang)
            .join(MaGiamGia, MaGiamGia.id == DonHang.ma_giam_gia_id)
            .where(
                MaGiamGia.khuyen_mai_id == km_id,
                DonHang.khach_hang_id == khach_hang_id,
                DonHang.trang_thai != TrangThaiDon.da_huy,
            )
        )
        or 0
    )


@dataclass
class KetQuaKiemTra:
    hop_le: bool
    ma_giam_gia: MaGiamGia | None = None
    khuyen_mai: KhuyenMai | None = None
    ma_ly_do: MaLyDo | None = None
    giam: Decimal = Decimal(0)
    co_so_giam: Decimal = Decimal(0)
    phan_bo: dict[int, Decimal] | None = None

    @property
    def ly_do(self) -> str | None:
        return THONG_DIEP[self.ma_ly_do] if self.ma_ly_do else None


def _tu_choi(ma: MaGiamGia | None, km: KhuyenMai | None, ly_do: MaLyDo, co_so: Decimal = Decimal(0)) -> KetQuaKiemTra:
    return KetQuaKiemTra(False, ma, km, ly_do, co_so_giam=co_so)


async def _danh_gia(
    db: AsyncSession,
    ma: MaGiamGia | None,
    km: KhuyenMai | None,
    khach_hang_id: int,
    dong: list[DongGio],
    bay_gio: datetime,
) -> KetQuaKiemTra:
    """Bước 3 của spec 04 mục 4, theo đúng thứ tự, rồi tính số tiền giảm."""
    if ma is None or km is None:
        return _tu_choi(None, None, MaLyDo.khong_ton_tai)
    if not km.dang_hoat_dong:
        return _tu_choi(ma, km, MaLyDo.da_tat)
    if bay_gio < km.bat_dau:
        return _tu_choi(ma, km, MaLyDo.chua_bat_dau)
    if bay_gio >= km.ket_thuc:
        return _tu_choi(ma, km, MaLyDo.het_han)
    if km.tong_luot is not None and await _luot_da_dung_tong(db, km.id) >= km.tong_luot:
        return _tu_choi(ma, km, MaLyDo.het_luot)
    if await _luot_cua_khach(db, km.id, khach_hang_id) >= km.luot_moi_khach:
        return _tu_choi(ma, km, MaLyDo.het_luot_khach)
    pv = await _pham_vi(db, km)
    tinh = [DongTinh(d.khoa, d.thanh_tien_goc, _thuoc_pham_vi(d, pv)) for d in dong]
    kq = tinh_giam(tinh, km.loai_giam, km.gia_tri, km.giam_toi_da)
    if kq.co_so_giam <= 0:
        return _tu_choi(ma, km, MaLyDo.khong_co_san_pham)
    if kq.co_so_giam < km.don_toi_thieu:
        return _tu_choi(ma, km, MaLyDo.duoi_don_toi_thieu, kq.co_so_giam)
    return KetQuaKiemTra(True, ma, km, None, kq.giam, kq.co_so_giam, kq.phan_bo)


async def _tim_ma(db: AsyncSession, ma_text: str, *, khoa: bool = False) -> tuple[MaGiamGia | None, KhuyenMai | None]:
    ma = (await db.execute(select(MaGiamGia).where(MaGiamGia.ma == chuan_hoa_ma(ma_text)))).scalar_one_or_none()
    if ma is None:
        return None, None
    truy_van = select(KhuyenMai).where(KhuyenMai.id == ma.khuyen_mai_id)
    if khoa:
        truy_van = truy_van.with_for_update().execution_options(populate_existing=True)
    return ma, (await db.execute(truy_van)).scalar_one()


async def kiem_tra_ma(
    db: AsyncSession, khach_hang_id: int, ma_text: str, dong: list[DongGio], bay_gio: datetime | None = None
) -> KetQuaKiemTra:
    """Xem trước (không ghi gì): mã có áp dụng được cho các dòng này không và giảm bao nhiêu."""
    ma, km = await _tim_ma(db, ma_text)
    return await _danh_gia(db, ma, km, khach_hang_id, dong, bay_gio or bay_gio_utc())


async def dung_ma(
    db: AsyncSession, khach_hang_id: int, ma_text: str, dong: list[DongGio], bay_gio: datetime | None = None
) -> KetQuaKiemTra:
    """Dùng mã khi tạo đơn (T4.4): khóa khuyến mãi, kiểm tra lại, `so_luot_da_dung += 1`. Không hợp lệ thì ném
    `422 MA_GIAM_GIA_KHONG_HOP_LE` kèm `ma_ly_do`. Người gọi gán `don.ma_giam_gia_id` và lưu đơn cùng transaction."""
    ma, km = await _tim_ma(db, ma_text, khoa=True)
    kq = await _danh_gia(db, ma, km, khach_hang_id, dong, bay_gio or bay_gio_utc())
    if not kq.hop_le:
        assert kq.ma_ly_do is not None
        raise LoiNghiepVu("MA_GIAM_GIA_KHONG_HOP_LE", THONG_DIEP[kq.ma_ly_do], chi_tiet={"ma_ly_do": kq.ma_ly_do.value})
    assert kq.ma_giam_gia is not None
    kq.ma_giam_gia.so_luot_da_dung += 1
    await db.flush()
    return kq


async def tra_luot_khi_huy(db: AsyncSession, don: DonHang, tac_nhan: object) -> None:
    """Hook của máy trạng thái cho mọi dòng chuyển sang `da_huy`: trả lại lượt dùng mã (spec 04 mục 4 bước 8). Đơn đã
    hủy là trạng thái kết thúc nên mỗi đơn trả lượt đúng một lần."""
    if don.ma_giam_gia_id is None:
        return
    ma = (
        await db.execute(
            select(MaGiamGia)
            .where(MaGiamGia.id == don.ma_giam_gia_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    ma.so_luot_da_dung = max(ma.so_luot_da_dung - 1, 0)
    await db.flush()

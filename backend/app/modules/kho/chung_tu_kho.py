"""Màn xem gộp chứng từ kho cho Admin (AD16, T6.7): phiếu nhập, kiểm kê, điều chỉnh, hủy, xuất trả. Chỉ đọc."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.phan_trang import ThamSoPhanTrang, Trang, tao_trang
from app.models.he_thong import NhanVien
from app.models.kho import PhieuDieuChinh, PhieuHuy, PhieuKiemKe, PhieuNhap, PhieuXuatTra


class LoaiChungTu(StrEnum):
    phieu_nhap = "phieu_nhap"
    kiem_ke = "kiem_ke"
    dieu_chinh = "dieu_chinh"
    phieu_huy = "phieu_huy"
    xuat_tra = "xuat_tra"


class ChungTuKho(BaseModel):
    loai: LoaiChungTu
    id: int
    ma_phieu: str
    trang_thai: str | None
    """`trang_thai_duyet` của phiếu cần duyệt, `trang_thai` của kiểm kê; phiếu nhập không có."""
    nguoi_lap: str
    nguoi_duyet: str | None
    ghi_chu: str | None
    created_at: datetime


def _cau(loai: LoaiChungTu):
    lap = NhanVien.__table__.alias("lap")
    duyet = NhanVien.__table__.alias("duyet")
    bang = {
        LoaiChungTu.phieu_nhap: (PhieuNhap, PhieuNhap.nhan_vien_id, None, None, None),
        LoaiChungTu.kiem_ke: (PhieuKiemKe, PhieuKiemKe.nhan_vien_id, None, PhieuKiemKe.trang_thai, None),
        LoaiChungTu.dieu_chinh: (
            PhieuDieuChinh, PhieuDieuChinh.nguoi_lap_id, PhieuDieuChinh.nguoi_duyet_id,
            PhieuDieuChinh.trang_thai_duyet, PhieuDieuChinh.ly_do,
        ),
        LoaiChungTu.phieu_huy: (
            PhieuHuy, PhieuHuy.nguoi_lap_id, PhieuHuy.nguoi_duyet_id, PhieuHuy.trang_thai_duyet, PhieuHuy.ly_do,
        ),
        LoaiChungTu.xuat_tra: (
            PhieuXuatTra, PhieuXuatTra.nhan_vien_id, PhieuXuatTra.nguoi_duyet_id, PhieuXuatTra.trang_thai_duyet,
            PhieuXuatTra.ly_do,
        ),
    }  # fmt: skip
    mo_hinh, c_lap, c_duyet, c_tt, c_ghi_chu = bang[loai]
    cot_duyet = duyet.c.ho_ten if c_duyet is not None else func.cast(None, duyet.c.ho_ten.type)
    cau = select(
        mo_hinh.id,
        mo_hinh.ma_phieu,
        mo_hinh.created_at,
        lap.c.ho_ten.label("nguoi_lap"),
        cot_duyet.label("nguoi_duyet"),
        (c_tt if c_tt is not None else func.cast(None, lap.c.ho_ten.type)).label("trang_thai"),
        (c_ghi_chu if c_ghi_chu is not None else func.cast(None, lap.c.ho_ten.type)).label("ghi_chu"),
    ).join(lap, lap.c.id == c_lap)
    return mo_hinh, cau.outerjoin(duyet, duyet.c.id == (c_duyet if c_duyet is not None else -1))


async def danh_sach(db: AsyncSession, tp: ThamSoPhanTrang, loai: LoaiChungTu | None) -> Trang[ChungTuKho]:
    cac_loai = [loai] if loai else list(LoaiChungTu)
    tong = 0
    dong: list[ChungTuKho] = []
    can_lay = tp.offset + tp.limit
    for lc in cac_loai:
        mo_hinh, cau = _cau(lc)
        tong += await db.scalar(select(func.count()).select_from(mo_hinh)) or 0
        for r in (await db.execute(cau.order_by(mo_hinh.created_at.desc(), mo_hinh.id.desc()).limit(can_lay))).all():
            tt = r.trang_thai.value if hasattr(r.trang_thai, "value") else r.trang_thai
            dong.append(
                ChungTuKho(
                    loai=lc,
                    id=r.id,
                    ma_phieu=r.ma_phieu,
                    trang_thai=tt,
                    nguoi_lap=r.nguoi_lap,
                    nguoi_duyet=r.nguoi_duyet,
                    ghi_chu=r.ghi_chu,
                    created_at=r.created_at,
                )
            )
    dong.sort(key=lambda d: (d.created_at, d.id), reverse=True)
    return tao_trang(dong[tp.offset : tp.offset + tp.limit], tong, tp)

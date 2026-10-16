"""Duyệt phiếu điều chỉnh, phiếu hủy, phiếu xuất trả NCC (AD12, spec 06 mục 3.18, spec 04 mục 1.5).

Chỉ ở đây tồn kho mới đổi vì phiếu kho: khóa phiếu, kiểm tra người duyệt khác người lập và phiếu còn `cho_duyet`, khóa
mọi lô theo id tăng dần, rồi gọi `ton_kho` từng dòng (số lượng được kiểm tra lại ở đó). Lỗi nào cũng rollback cả phiếu.
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import String, cast, func, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_trang import ThamSoPhanTrang, Trang, lay_trang, tao_trang
from app.core.thoi_gian import bay_gio_utc
from app.models.enums import KhuTon, LoaiBienDong, TrangThaiDuyet
from app.models.he_thong import NhanVien
from app.models.kho import (
    CtPhieuDieuChinh,
    CtPhieuHuy,
    CtPhieuXuatTra,
    LoThuoc,
    PhieuDieuChinh,
    PhieuHuy,
    PhieuXuatTra,
)
from app.modules.kho import dieu_chinh, phieu_huy, phieu_xuat_tra, ton_kho
from app.modules.kho.phieu_kho_chung import nv_rut
from app.modules.kho.schemas_phieu_kho import LoaiPhieu, PhieuChoDuyet
from app.modules.thong_bao.service import gui_cho_nhan_vien


@dataclass(frozen=True)
class _Loai:
    bang: str
    phieu: Any
    ct: Any
    cot_phieu_ct: Any
    cot_nguoi_lap: Any
    lien_ket: str
    chi_tiet: Any


_LOAI: dict[str, _Loai] = {
    "dieu-chinh": _Loai(
        "phieu_dieu_chinh",
        PhieuDieuChinh,
        CtPhieuDieuChinh,
        CtPhieuDieuChinh.phieu_dieu_chinh_id,
        PhieuDieuChinh.nguoi_lap_id,
        "/nhan-vien/dieu-chinh",
        dieu_chinh.chi_tiet,
    ),
    "huy": _Loai(
        "phieu_huy",
        PhieuHuy,
        CtPhieuHuy,
        CtPhieuHuy.phieu_huy_id,
        PhieuHuy.nguoi_lap_id,
        "/nhan-vien/phieu-huy",
        phieu_huy.chi_tiet,
    ),
    "xuat-tra": _Loai(
        "phieu_xuat_tra",
        PhieuXuatTra,
        CtPhieuXuatTra,
        CtPhieuXuatTra.phieu_xuat_tra_id,
        PhieuXuatTra.nhan_vien_id,
        "/nhan-vien/xuat-tra",
        phieu_xuat_tra.chi_tiet,
    ),
}


def _loai(loai: str) -> _Loai:
    return _LOAI[loai]


async def chi_tiet(db: AsyncSession, loai: LoaiPhieu, phieu_id: int):
    """Chi tiết đúng dạng của loại phiếu (cho màn duyệt của Admin)."""
    return await _loai(loai).chi_tiet(db, phieu_id)


async def _khoa_phieu(db: AsyncSession, actor: NhanVien, loai: LoaiPhieu, phieu_id: int):
    """Khóa phiếu; từ chối tự duyệt và phiếu không còn chờ duyệt."""
    cfg = _loai(loai)
    phieu = (
        await db.execute(
            select(cfg.phieu)
            .where(cfg.phieu.id == phieu_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if phieu is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy phiếu")
    nguoi_lap_id = phieu.nhan_vien_id if loai == "xuat-tra" else phieu.nguoi_lap_id
    if nguoi_lap_id == actor.id:
        raise LoiNghiepVu("TU_DUYET_KHONG_DUOC", "Người lập phiếu không được tự duyệt hoặc từ chối phiếu của mình")
    if phieu.trang_thai_duyet != TrangThaiDuyet.cho_duyet:
        raise LoiNghiepVu(
            "CHUYEN_TRANG_THAI_KHONG_HOP_LE",
            f"Phiếu đang ở trạng thái {phieu.trang_thai_duyet.value}, không còn chờ duyệt",
        )
    return phieu, nguoi_lap_id


async def _ap_dung_ton(db: AsyncSession, actor: NhanVien, loai: LoaiPhieu, phieu) -> None:
    cfg = _loai(loai)
    dong = (
        (await db.execute(select(cfg.ct).where(cfg.cot_phieu_ct == phieu.id).order_by(cfg.ct.lo_id, cfg.ct.id)))
        .scalars()
        .all()
    )
    lo_thuoc = {lo.id: lo for lo in await ton_kho.khoa_cac_lo(db, [d.lo_id for d in dong])}
    chung_tu = ton_kho.ChungTu(cfg.bang, phieu.id, actor.id)
    for d in dong:
        lo: LoThuoc = lo_thuoc[d.lo_id]
        if loai == "dieu-chinh":
            await ton_kho.dieu_chinh(db, lo, d.so_luong_thay_doi, chung_tu)
        else:
            bien_dong = LoaiBienDong.huy_hang if loai == "huy" else LoaiBienDong.xuat_tra_ncc
            await ton_kho.tru_ton(db, lo, d.so_luong, KhuTon(d.tu_khu), bien_dong, chung_tu)


async def duyet(db: AsyncSession, actor: NhanVien, loai: LoaiPhieu, phieu_id: int, *, ip: str):
    """Duyệt phiếu: đổi tồn, ghi thẻ kho, rồi đánh dấu `da_duyet`."""
    phieu, nguoi_lap_id = await _khoa_phieu(db, actor, loai, phieu_id)
    await _ap_dung_ton(db, actor, loai, phieu)
    phieu.trang_thai_duyet = TrangThaiDuyet.da_duyet
    phieu.nguoi_duyet_id = actor.id
    phieu.duyet_luc = bay_gio_utc()
    await db.flush()
    await _ket_thuc(db, actor, loai, phieu, nguoi_lap_id, "duyet", None, ip)
    return await chi_tiet(db, loai, phieu_id)


async def tu_choi(db: AsyncSession, actor: NhanVien, loai: LoaiPhieu, phieu_id: int, ly_do: str, *, ip: str):
    """Từ chối phiếu (bắt buộc lý do): tồn không đổi."""
    phieu, nguoi_lap_id = await _khoa_phieu(db, actor, loai, phieu_id)
    phieu.trang_thai_duyet = TrangThaiDuyet.tu_choi
    phieu.nguoi_duyet_id = actor.id
    phieu.ly_do_tu_choi = ly_do
    phieu.duyet_luc = bay_gio_utc()
    await db.flush()
    await _ket_thuc(db, actor, loai, phieu, nguoi_lap_id, "tu_choi", ly_do, ip)
    return await chi_tiet(db, loai, phieu_id)


async def _ket_thuc(db, actor, loai, phieu, nguoi_lap_id: int, hanh_dong: str, ly_do: str | None, ip: str) -> None:
    cfg = _loai(loai)
    gia_tri: dict[str, Any] = {"ma_phieu": phieu.ma_phieu, "trang_thai_duyet": phieu.trang_thai_duyet.value}
    if ly_do is not None:
        gia_tri["ly_do_tu_choi"] = ly_do
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong=hanh_dong,
        bang=cfg.bang,
        ban_ghi_id=phieu.id,
        gia_tri_moi=gia_tri,
        ip=ip,
    )
    da_duyet = hanh_dong == "duyet"
    await gui_cho_nhan_vien(
        db,
        nguoi_lap_id,
        loai="phieu_kho_da_duyet" if da_duyet else "phieu_kho_tu_choi",
        tieu_de=f"Phiếu {phieu.ma_phieu} đã được duyệt" if da_duyet else f"Phiếu {phieu.ma_phieu} bị từ chối",
        noi_dung=None if da_duyet else ly_do,
        lien_ket=cfg.lien_ket,
    )


async def danh_sach(
    db: AsyncSession, loai: LoaiPhieu | None, trang_thai: TrangThaiDuyet | None, tp: ThamSoPhanTrang
) -> Trang[PhieuChoDuyet]:
    """Gộp ba loại phiếu, mới nhất trước."""

    def chon(ten: str, cfg: _Loai, ly_do):
        so_dong = select(func.count()).where(cfg.cot_phieu_ct == cfg.phieu.id).correlate(cfg.phieu).scalar_subquery()
        return select(
            literal(ten).label("loai"),
            cfg.phieu.id.label("id"),
            cfg.phieu.ma_phieu.label("ma_phieu"),
            ly_do.label("ly_do"),
            cfg.phieu.trang_thai_duyet.label("trang_thai_duyet"),
            cfg.cot_nguoi_lap.label("nguoi_lap_id"),
            cfg.phieu.created_at.label("created_at"),
            so_dong.label("so_dong"),
        )

    ly_do_cua = {
        "dieu-chinh": PhieuDieuChinh.ly_do,
        "huy": cast(PhieuHuy.ly_do, String),
        "xuat-tra": PhieuXuatTra.ly_do,
    }
    cac_loai = [loai] if loai else list(_LOAI)
    u = union_all(*(chon(t, _LOAI[t], ly_do_cua[t]) for t in cac_loai)).subquery()
    stmt = select(u, NhanVien).join(NhanVien, NhanVien.id == u.c.nguoi_lap_id)
    if trang_thai is not None:
        stmt = stmt.where(u.c.trang_thai_duyet == trang_thai)
    dong, tong = await lay_trang(db, stmt.order_by(u.c.created_at.desc(), u.c.id.desc()), tp, nhieu_cot=True)
    return tao_trang(
        [
            PhieuChoDuyet(
                loai=r.loai,
                id=r.id,
                ma_phieu=r.ma_phieu,
                ly_do=r.ly_do,
                trang_thai_duyet=r.trang_thai_duyet,
                nguoi_lap=nv_rut(r.NhanVien),
                created_at=r.created_at,
                so_dong=r.so_dong,
            )
            for r in dong
        ],
        tong,
        tp,
    )

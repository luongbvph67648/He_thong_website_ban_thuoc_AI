"""Lập phiếu hủy hàng (KHO09, spec 06 mục 3.18). Chỉ LẬP phiếu `cho_duyet`: tồn đổi khi Admin duyệt (`duyet_phieu`)."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.core.ma_chung_tu import ma_phieu
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_trang import ThamSoPhanTrang, Trang, lay_trang, tao_trang
from app.models.enums import TrangThaiDuyet
from app.models.he_thong import NhanVien
from app.models.kho import CtPhieuHuy, PhieuHuy
from app.modules.kho.phieu_kho_chung import kiem_tra_dong, nv_rut, thong_tin_lo
from app.modules.kho.schemas_phieu_kho import DongPhieuRa, PhieuHuyChiTiet, PhieuHuyTao, PhieuHuyTomTat

BANG = "phieu_huy"


async def tao(db: AsyncSession, actor: NhanVien, du_lieu: PhieuHuyTao, *, ip: str) -> PhieuHuyChiTiet:
    await kiem_tra_dong(db, du_lieu.dong)
    phieu = PhieuHuy(ma_phieu=await ma_phieu(db, BANG), ly_do=du_lieu.ly_do, mo_ta=du_lieu.mo_ta, nguoi_lap_id=actor.id)
    db.add(phieu)
    await db.flush()
    db.add_all(
        [CtPhieuHuy(phieu_huy_id=phieu.id, lo_id=d.lo_id, tu_khu=d.tu_khu, so_luong=d.so_luong) for d in du_lieu.dong]
    )
    await db.flush()
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="tao",
        bang=BANG,
        ban_ghi_id=phieu.id,
        gia_tri_moi={"ma_phieu": phieu.ma_phieu, "ly_do": du_lieu.ly_do.value, "so_dong": len(du_lieu.dong)},
        ip=ip,
    )
    return await chi_tiet(db, phieu.id)


async def danh_sach(db: AsyncSession, trang_thai: TrangThaiDuyet | None, tp: ThamSoPhanTrang) -> Trang[PhieuHuyTomTat]:
    so_dong = select(func.count()).where(CtPhieuHuy.phieu_huy_id == PhieuHuy.id).correlate(PhieuHuy).scalar_subquery()
    stmt = select(PhieuHuy, NhanVien, so_dong).join(NhanVien, NhanVien.id == PhieuHuy.nguoi_lap_id)
    if trang_thai is not None:
        stmt = stmt.where(PhieuHuy.trang_thai_duyet == trang_thai)
    dong, tong = await lay_trang(db, stmt.order_by(PhieuHuy.id.desc()), tp, nhieu_cot=True)
    return tao_trang(
        [
            PhieuHuyTomTat(
                id=p.id,
                ma_phieu=p.ma_phieu,
                ly_do=p.ly_do.value,
                trang_thai_duyet=p.trang_thai_duyet,
                nguoi_lap=nv_rut(nv),
                created_at=p.created_at,
                so_dong=c,
            )
            for p, nv, c in dong
        ],
        tong,
        tp,
    )


async def chi_tiet(db: AsyncSession, phieu_id: int) -> PhieuHuyChiTiet:
    p = (
        await db.execute(select(PhieuHuy).where(PhieuHuy.id == phieu_id).execution_options(populate_existing=True))
    ).scalar_one_or_none()
    if p is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy phiếu hủy")
    lap = await db.get(NhanVien, p.nguoi_lap_id)
    duyet = await db.get(NhanVien, p.nguoi_duyet_id) if p.nguoi_duyet_id else None
    ct = (
        (await db.execute(select(CtPhieuHuy).where(CtPhieuHuy.phieu_huy_id == phieu_id).order_by(CtPhieuHuy.id)))
        .scalars()
        .all()
    )
    lo = await thong_tin_lo(db, [c.lo_id for c in ct])
    return PhieuHuyChiTiet(
        id=p.id,
        ma_phieu=p.ma_phieu,
        ly_do=p.ly_do.value,
        mo_ta=p.mo_ta,
        trang_thai_duyet=p.trang_thai_duyet,
        nguoi_lap=nv_rut(lap),
        created_at=p.created_at,
        so_dong=len(ct),
        nguoi_duyet=nv_rut(duyet),
        ly_do_tu_choi=p.ly_do_tu_choi,
        duyet_luc=p.duyet_luc,
        dong=[
            DongPhieuRa(
                lo_id=c.lo_id,
                san_pham=lo[c.lo_id][1],
                so_lo=lo[c.lo_id][0].so_lo,
                han_su_dung=lo[c.lo_id][0].han_su_dung,
                tu_khu=c.tu_khu,
                so_luong=c.so_luong,
            )
            for c in ct
        ],
    )

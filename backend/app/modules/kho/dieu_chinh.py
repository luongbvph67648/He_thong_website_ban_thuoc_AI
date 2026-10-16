"""Lập phiếu điều chỉnh tồn (KHO08, spec 06 mục 3.17). Chỉ LẬP phiếu `cho_duyet`: tồn đổi khi Admin duyệt (T3.4)."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.core.ma_chung_tu import ma_phieu
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_trang import ThamSoPhanTrang, Trang, lay_trang, tao_trang
from app.models.enums import TrangThaiDuyet, TrangThaiKiemKe
from app.models.he_thong import NhanVien
from app.models.kho import CtKiemKe, CtPhieuDieuChinh, LoThuoc, PhieuDieuChinh, PhieuKiemKe
from app.models.san_pham import SanPham
from app.modules.kho.schemas_kiem_ke import (
    DieuChinhChiTiet,
    DieuChinhTao,
    DieuChinhTomTat,
    DongDieuChinhRa,
)
from app.modules.kho.schemas_phieu_nhap import NhanVienRut, SanPhamRut

BANG = "phieu_dieu_chinh"


def _nv(n: NhanVien | None) -> NhanVienRut | None:
    return None if n is None else NhanVienRut(id=n.id, ma_nhan_vien=n.ma_nhan_vien, ho_ten=n.ho_ten)


async def tao(db: AsyncSession, actor: NhanVien, du_lieu: DieuChinhTao, *, ip: str) -> DieuChinhChiTiet:
    if du_lieu.phieu_kiem_ke_id is not None:
        kk_id = du_lieu.phieu_kiem_ke_id
        kk = (
            await db.execute(
                select(PhieuKiemKe)
                .where(PhieuKiemKe.id == kk_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        if kk is None:
            raise LoiNghiepVu(
                "DU_LIEU_KHONG_HOP_LE",
                "Phiếu kiểm kê không tồn tại",
                chi_tiet=[{"truong": "phieu_kiem_ke_id", "loi": "Không tồn tại"}],
            )
        if kk.trang_thai != TrangThaiKiemKe.da_chot:
            raise LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Phiếu kiểm kê chưa chốt")
        da_co = await db.scalar(
            select(PhieuDieuChinh.ma_phieu).where(
                PhieuDieuChinh.phieu_kiem_ke_id == kk_id,
                PhieuDieuChinh.trang_thai_duyet.in_([TrangThaiDuyet.cho_duyet, TrangThaiDuyet.da_duyet]),
            )
        )
        if da_co:
            raise LoiNghiepVu(
                "TRUNG_DU_LIEU",
                f"Phiếu kiểm kê này đã có phiếu điều chỉnh {da_co}",
                chi_tiet={"truong": "phieu_kiem_ke_id"},
            )
        dong = [
            (lo_id, cl)
            for lo_id, cl in (
                await db.execute(
                    select(CtKiemKe.lo_id, CtKiemKe.chenh_lech)
                    .where(CtKiemKe.phieu_kiem_ke_id == kk_id, CtKiemKe.chenh_lech != 0)
                    .order_by(CtKiemKe.lo_id)
                )
            ).all()
        ]
        if not dong:
            raise LoiNghiepVu(
                "DU_LIEU_KHONG_HOP_LE",
                "Kiểm kê không có dòng lệch, không cần điều chỉnh",
                chi_tiet=[{"truong": "phieu_kiem_ke_id", "loi": "Không có dòng lệch"}],
            )
    else:
        dong = [(d.lo_id, d.so_luong_thay_doi) for d in (du_lieu.dong or [])]
        co = set((await db.execute(select(LoThuoc.id).where(LoThuoc.id.in_([d[0] for d in dong])))).scalars())
        for i, (lo_id, _) in enumerate(dong):
            if lo_id not in co:
                raise LoiNghiepVu(
                    "DU_LIEU_KHONG_HOP_LE",
                    "Lô không tồn tại",
                    chi_tiet=[{"truong": f"dong.{i}.lo_id", "loi": "Không tồn tại"}],
                )
    phieu = PhieuDieuChinh(
        ma_phieu=await ma_phieu(db, "phieu_dieu_chinh"),
        phieu_kiem_ke_id=du_lieu.phieu_kiem_ke_id,
        ly_do=du_lieu.ly_do,
        nguoi_lap_id=actor.id,
    )
    db.add(phieu)
    await db.flush()
    db.add_all(
        [CtPhieuDieuChinh(phieu_dieu_chinh_id=phieu.id, lo_id=lo_id, so_luong_thay_doi=sl) for lo_id, sl in dong]
    )
    await db.flush()
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="tao",
        bang=BANG,
        ban_ghi_id=phieu.id,
        gia_tri_moi={"ma_phieu": phieu.ma_phieu, "phieu_kiem_ke_id": phieu.phieu_kiem_ke_id, "so_dong": len(dong)},
        ip=ip,
    )
    return await chi_tiet(db, phieu.id)


def _tom_tat(p: PhieuDieuChinh, lap: NhanVien, ma_kk: str | None, so_dong: int) -> DieuChinhTomTat:
    return DieuChinhTomTat(
        id=p.id,
        ma_phieu=p.ma_phieu,
        phieu_kiem_ke_id=p.phieu_kiem_ke_id,
        ma_phieu_kiem_ke=ma_kk,
        ly_do=p.ly_do,
        trang_thai_duyet=p.trang_thai_duyet,
        nguoi_lap=_nv(lap),
        created_at=p.created_at,
        so_dong=so_dong,
    )


async def danh_sach(db: AsyncSession, trang_thai: TrangThaiDuyet | None, tp: ThamSoPhanTrang) -> Trang[DieuChinhTomTat]:
    so_dong = (
        select(func.count())
        .where(CtPhieuDieuChinh.phieu_dieu_chinh_id == PhieuDieuChinh.id)
        .correlate(PhieuDieuChinh)
        .scalar_subquery()
    )
    stmt = (
        select(PhieuDieuChinh, NhanVien, PhieuKiemKe.ma_phieu, so_dong)
        .join(NhanVien, NhanVien.id == PhieuDieuChinh.nguoi_lap_id)
        .outerjoin(PhieuKiemKe, PhieuKiemKe.id == PhieuDieuChinh.phieu_kiem_ke_id)
    )
    if trang_thai is not None:
        stmt = stmt.where(PhieuDieuChinh.trang_thai_duyet == trang_thai)
    dong, tong = await lay_trang(db, stmt.order_by(PhieuDieuChinh.id.desc()), tp, nhieu_cot=True)
    return tao_trang([_tom_tat(p, nv, kk, c) for p, nv, kk, c in dong], tong, tp)


async def chi_tiet(db: AsyncSession, phieu_id: int) -> DieuChinhChiTiet:
    hang = (
        await db.execute(
            select(PhieuDieuChinh, PhieuKiemKe.ma_phieu)
            .outerjoin(PhieuKiemKe, PhieuKiemKe.id == PhieuDieuChinh.phieu_kiem_ke_id)
            .where(PhieuDieuChinh.id == phieu_id)
            .execution_options(populate_existing=True)
        )
    ).first()
    if hang is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy phiếu điều chỉnh")
    p, ma_kk = hang
    lap = await db.get(NhanVien, p.nguoi_lap_id)
    duyet = await db.get(NhanVien, p.nguoi_duyet_id) if p.nguoi_duyet_id else None
    dong = (
        await db.execute(
            select(CtPhieuDieuChinh, LoThuoc, SanPham)
            .join(LoThuoc, LoThuoc.id == CtPhieuDieuChinh.lo_id)
            .join(SanPham, SanPham.id == LoThuoc.san_pham_id)
            .where(CtPhieuDieuChinh.phieu_dieu_chinh_id == phieu_id)
            .order_by(func.lower(SanPham.ten), LoThuoc.han_su_dung, LoThuoc.id)
        )
    ).all()
    return DieuChinhChiTiet(
        **_tom_tat(p, lap, ma_kk, len(dong)).model_dump(),
        nguoi_duyet=_nv(duyet),
        ly_do_tu_choi=p.ly_do_tu_choi,
        duyet_luc=p.duyet_luc,
        dong=[
            DongDieuChinhRa(
                lo_id=lo.id,
                san_pham=SanPhamRut(id=sp.id, sku=sp.sku, ten=sp.ten),
                so_lo=lo.so_lo,
                so_luong_thay_doi=ct.so_luong_thay_doi,
                so_luong_ton_hien_tai=lo.so_luong_ton,
            )
            for ct, lo, sp in dong
        ],
    )

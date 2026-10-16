"""Lập phiếu xuất trả nhà cung cấp (KHO11, spec 06 mục 3.18). Chỉ LẬP phiếu `cho_duyet`; tồn đổi khi Admin duyệt."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.core.ma_chung_tu import ma_phieu
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_trang import ThamSoPhanTrang, Trang, lay_trang, tao_trang
from app.models.enums import TrangThaiDuyet, TrangThaiThuHoi
from app.models.he_thong import NhanVien
from app.models.kho import CtPhieuXuatTra, LenhThuHoi, NhaCungCap, PhieuXuatTra
from app.modules.kho.phieu_kho_chung import kiem_tra_dong, nv_rut, thong_tin_lo
from app.modules.kho.schemas_phieu_kho import (
    DongXuatTraRa,
    NccRut,
    PhieuXuatTraChiTiet,
    PhieuXuatTraTao,
    PhieuXuatTraTomTat,
)

BANG = "phieu_xuat_tra"


async def tao(db: AsyncSession, actor: NhanVien, du_lieu: PhieuXuatTraTao, *, ip: str) -> PhieuXuatTraChiTiet:
    co_ncc = await db.scalar(
        select(NhaCungCap.id).where(NhaCungCap.id == du_lieu.nha_cung_cap_id, NhaCungCap.deleted_at.is_(None))
    )
    if co_ncc is None:
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE",
            "Nhà cung cấp không tồn tại",
            chi_tiet=[{"truong": "nha_cung_cap_id", "loi": "Không tồn tại"}],
        )
    lo_thuoc = await kiem_tra_dong(db, du_lieu.dong)
    if du_lieu.lenh_thu_hoi_id is not None:
        lenh = await db.get(LenhThuHoi, du_lieu.lenh_thu_hoi_id)
        if (
            lenh is None
            or lenh.trang_thai != TrangThaiThuHoi.dang_thu_hoi
            or any(
                lo.san_pham_id != lenh.san_pham_id or (lenh.lo_id is not None and lo.id != lenh.lo_id)
                for lo in lo_thuoc.values()
            )
        ):
            raise LoiNghiepVu(
                "DU_LIEU_KHONG_HOP_LE",
                "Dữ liệu không hợp lệ",
                chi_tiet=[{"truong": "lenh_thu_hoi_id", "loi": "Lệnh không mở hoặc lô không thuộc lệnh"}],
            )
    phieu = PhieuXuatTra(
        ma_phieu=await ma_phieu(db, BANG),
        nha_cung_cap_id=du_lieu.nha_cung_cap_id,
        ly_do=du_lieu.ly_do,
        lenh_thu_hoi_id=du_lieu.lenh_thu_hoi_id,
        nhan_vien_id=actor.id,
    )
    db.add(phieu)
    await db.flush()
    db.add_all(
        [
            CtPhieuXuatTra(
                phieu_xuat_tra_id=phieu.id,
                lo_id=d.lo_id,
                tu_khu=d.tu_khu,
                so_luong=d.so_luong,
                don_gia=d.don_gia if d.don_gia is not None else lo_thuoc[d.lo_id].gia_nhap,
            )
            for d in du_lieu.dong
        ]
    )
    await db.flush()
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="tao",
        bang=BANG,
        ban_ghi_id=phieu.id,
        gia_tri_moi={
            "ma_phieu": phieu.ma_phieu,
            "nha_cung_cap_id": phieu.nha_cung_cap_id,
            "so_dong": len(du_lieu.dong),
        },
        ip=ip,
    )
    return await chi_tiet(db, phieu.id)


async def danh_sach(
    db: AsyncSession, trang_thai: TrangThaiDuyet | None, tp: ThamSoPhanTrang
) -> Trang[PhieuXuatTraTomTat]:
    so_dong = (
        select(func.count())
        .where(CtPhieuXuatTra.phieu_xuat_tra_id == PhieuXuatTra.id)
        .correlate(PhieuXuatTra)
        .scalar_subquery()
    )
    stmt = (
        select(PhieuXuatTra, NhanVien, NhaCungCap, so_dong)
        .join(NhanVien, NhanVien.id == PhieuXuatTra.nhan_vien_id)
        .join(NhaCungCap, NhaCungCap.id == PhieuXuatTra.nha_cung_cap_id)
    )
    if trang_thai is not None:
        stmt = stmt.where(PhieuXuatTra.trang_thai_duyet == trang_thai)
    dong, tong = await lay_trang(db, stmt.order_by(PhieuXuatTra.id.desc()), tp, nhieu_cot=True)
    return tao_trang(
        [
            PhieuXuatTraTomTat(
                id=p.id,
                ma_phieu=p.ma_phieu,
                ly_do=p.ly_do,
                trang_thai_duyet=p.trang_thai_duyet,
                nguoi_lap=nv_rut(nv),
                created_at=p.created_at,
                so_dong=c,
                nha_cung_cap=NccRut(id=ncc.id, ten=ncc.ten),
            )
            for p, nv, ncc, c in dong
        ],
        tong,
        tp,
    )


async def chi_tiet(db: AsyncSession, phieu_id: int) -> PhieuXuatTraChiTiet:
    p = (
        await db.execute(
            select(PhieuXuatTra).where(PhieuXuatTra.id == phieu_id).execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if p is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy phiếu xuất trả")
    lap = await db.get(NhanVien, p.nhan_vien_id)
    duyet = await db.get(NhanVien, p.nguoi_duyet_id) if p.nguoi_duyet_id else None
    ncc = await db.get(NhaCungCap, p.nha_cung_cap_id)
    ct = (
        (
            await db.execute(
                select(CtPhieuXuatTra).where(CtPhieuXuatTra.phieu_xuat_tra_id == phieu_id).order_by(CtPhieuXuatTra.id)
            )
        )
        .scalars()
        .all()
    )
    lo = await thong_tin_lo(db, [c.lo_id for c in ct])
    return PhieuXuatTraChiTiet(
        id=p.id,
        ma_phieu=p.ma_phieu,
        ly_do=p.ly_do,
        trang_thai_duyet=p.trang_thai_duyet,
        nguoi_lap=nv_rut(lap),
        created_at=p.created_at,
        so_dong=len(ct),
        nha_cung_cap=NccRut(id=ncc.id, ten=ncc.ten),
        da_xac_nhan=p.da_xac_nhan,
        nguoi_duyet=nv_rut(duyet),
        ly_do_tu_choi=p.ly_do_tu_choi,
        duyet_luc=p.duyet_luc,
        dong=[
            DongXuatTraRa(
                lo_id=c.lo_id,
                san_pham=lo[c.lo_id][1],
                so_lo=lo[c.lo_id][0].so_lo,
                han_su_dung=lo[c.lo_id][0].han_su_dung,
                tu_khu=c.tu_khu,
                so_luong=c.so_luong,
                don_gia=c.don_gia,
            )
            for c in ct
        ],
    )

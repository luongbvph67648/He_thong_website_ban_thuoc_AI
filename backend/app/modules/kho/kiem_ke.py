"""Kiểm kê (KHO07, spec 06 mục 3.17): chụp tồn sổ sách, nhập số thực tế, chốt để có chênh lệch. Không đổi tồn."""

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.core.ma_chung_tu import ma_phieu
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_trang import ThamSoPhanTrang, Trang, lay_trang, tao_trang
from app.core.thoi_gian import bay_gio_utc
from app.models.enums import TrangThaiKiemKe
from app.models.he_thong import NhanVien
from app.models.kho import CtKiemKe, LoThuoc, PhieuDieuChinh, PhieuKiemKe
from app.models.san_pham import DanhMuc, SanPham
from app.modules.kho.schemas_kiem_ke import (
    DanhMucRut,
    DongKiemKe,
    KiemKeChiTiet,
    KiemKeTomTat,
    NhapSoLuong,
)
from app.modules.kho.schemas_phieu_nhap import NhanVienRut, SanPhamRut
from app.modules.kho.ton_kho import khoa_cac_lo
from app.modules.san_pham.san_pham import _id_danh_muc_con_chau

BANG = "phieu_kiem_ke"
SO_LO_TOI_DA = 5000


def khong_tim_thay() -> LoiNghiepVu:
    return LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy phiếu kiểm kê")


def _da_chot() -> LoiNghiepVu:
    return LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Phiếu kiểm kê đã chốt, không sửa hay xóa được")


def _loi_dau_vao(truong: str, loi: str) -> LoiNghiepVu:
    return LoiNghiepVu("DU_LIEU_KHONG_HOP_LE", loi, chi_tiet=[{"truong": truong, "loi": loi}])


async def _khoa_phieu(db: AsyncSession, phieu_id: int) -> PhieuKiemKe:
    p = (
        await db.execute(
            select(PhieuKiemKe)
            .where(PhieuKiemKe.id == phieu_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if p is None:
        raise khong_tim_thay()
    return p


async def tao(db: AsyncSession, actor: NhanVien, danh_muc_id: int | None, *, ip: str) -> KiemKeChiTiet:
    dieu_kien = [SanPham.deleted_at.is_(None), LoThuoc.so_luong_ton > 0]
    if danh_muc_id is not None:
        if await db.scalar(select(DanhMuc.id).where(DanhMuc.id == danh_muc_id, DanhMuc.deleted_at.is_(None))) is None:
            raise _loi_dau_vao("danh_muc_id", "Danh mục không tồn tại")
        dieu_kien.append(SanPham.danh_muc_id.in_(await _id_danh_muc_con_chau(db, danh_muc_id)))
    lo_thuoc = (
        (
            await db.execute(
                select(LoThuoc.id)
                .join(SanPham, SanPham.id == LoThuoc.san_pham_id)
                .where(*dieu_kien)
                .order_by(LoThuoc.id)
            )
        )
        .scalars()
        .all()
    )
    if not lo_thuoc:
        raise _loi_dau_vao("danh_muc_id", "Không có lô nào còn tồn để kiểm kê")
    if len(lo_thuoc) > SO_LO_TOI_DA:
        raise _loi_dau_vao("danh_muc_id", f"Quá {SO_LO_TOI_DA} lô, hãy kiểm kê theo từng danh mục")
    # Khóa các lô (id tăng dần) để số sổ sách chụp là một mốc nhất quán với thẻ kho.
    khoa = await khoa_cac_lo(db, lo_thuoc)
    phieu = PhieuKiemKe(ma_phieu=await ma_phieu(db, "phieu_kiem_ke"), danh_muc_id=danh_muc_id, nhan_vien_id=actor.id)
    db.add(phieu)
    await db.flush()
    db.add_all([CtKiemKe(phieu_kiem_ke_id=phieu.id, lo_id=lo.id, so_luong_so_sach=lo.so_luong_ton) for lo in khoa])
    await db.flush()
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="tao",
        bang=BANG,
        ban_ghi_id=phieu.id,
        gia_tri_moi={"ma_phieu": phieu.ma_phieu, "danh_muc_id": danh_muc_id, "so_dong": len(khoa)},
        ip=ip,
    )
    return await chi_tiet(db, phieu.id)


async def danh_sach(db: AsyncSession, trang_thai: TrangThaiKiemKe | None, tp: ThamSoPhanTrang) -> Trang[KiemKeTomTat]:
    so_dong = (
        select(func.count()).where(CtKiemKe.phieu_kiem_ke_id == PhieuKiemKe.id).correlate(PhieuKiemKe).scalar_subquery()
    )
    so_lech = (
        select(func.count())
        .where(CtKiemKe.phieu_kiem_ke_id == PhieuKiemKe.id, CtKiemKe.chenh_lech != 0)
        .correlate(PhieuKiemKe)
        .scalar_subquery()
    )
    stmt = (
        select(PhieuKiemKe, NhanVien, DanhMuc, so_dong, so_lech)
        .join(NhanVien, NhanVien.id == PhieuKiemKe.nhan_vien_id)
        .outerjoin(DanhMuc, DanhMuc.id == PhieuKiemKe.danh_muc_id)
    )
    if trang_thai is not None:
        stmt = stmt.where(PhieuKiemKe.trang_thai == trang_thai)
    dong, tong = await lay_trang(db, stmt.order_by(PhieuKiemKe.id.desc()), tp, nhieu_cot=True)
    return tao_trang([_tom_tat(p, nv, dm, c, le) for p, nv, dm, c, le in dong], tong, tp)


def _tom_tat(p: PhieuKiemKe, nv: NhanVien, dm: DanhMuc | None, so_dong: int, so_lech: int) -> KiemKeTomTat:
    return KiemKeTomTat(
        id=p.id,
        ma_phieu=p.ma_phieu,
        danh_muc=DanhMucRut(id=dm.id, ten=dm.ten) if dm else None,
        nhan_vien=NhanVienRut(id=nv.id, ma_nhan_vien=nv.ma_nhan_vien, ho_ten=nv.ho_ten),
        trang_thai=p.trang_thai,
        thoi_diem_chup_ton=p.thoi_diem_chup_ton,
        chot_luc=p.chot_luc,
        so_dong=so_dong,
        so_dong_lech=so_lech,
    )


async def chi_tiet(db: AsyncSession, phieu_id: int) -> KiemKeChiTiet:
    hang = (
        await db.execute(
            select(PhieuKiemKe, NhanVien, DanhMuc)
            .join(NhanVien, NhanVien.id == PhieuKiemKe.nhan_vien_id)
            .outerjoin(DanhMuc, DanhMuc.id == PhieuKiemKe.danh_muc_id)
            .where(PhieuKiemKe.id == phieu_id)
            .execution_options(populate_existing=True)
        )
    ).first()
    if hang is None:
        raise khong_tim_thay()
    dong = (
        await db.execute(
            select(CtKiemKe, LoThuoc, SanPham)
            .join(LoThuoc, LoThuoc.id == CtKiemKe.lo_id)
            .join(SanPham, SanPham.id == LoThuoc.san_pham_id)
            .where(CtKiemKe.phieu_kiem_ke_id == phieu_id)
            .order_by(func.lower(SanPham.ten), SanPham.id, LoThuoc.han_su_dung, LoThuoc.id)
            .execution_options(populate_existing=True)
        )
    ).all()
    tom = _tom_tat(*hang, len(dong), sum(1 for ct, _, _ in dong if ct.chenh_lech))
    return KiemKeChiTiet(
        **tom.model_dump(),
        dong=[
            DongKiemKe(
                lo_id=lo.id,
                san_pham=SanPhamRut(id=sp.id, sku=sp.sku, ten=sp.ten),
                so_lo=lo.so_lo,
                han_su_dung=lo.han_su_dung,
                so_luong_so_sach=ct.so_luong_so_sach,
                so_luong_thuc_te=ct.so_luong_thuc_te,
                chenh_lech=ct.chenh_lech,
            )
            for ct, lo, sp in dong
        ],
    )


async def nhap_so_luong(db: AsyncSession, actor: NhanVien, phieu_id: int, du_lieu: NhapSoLuong) -> KiemKeChiTiet:
    phieu = await _khoa_phieu(db, phieu_id)
    if phieu.trang_thai != TrangThaiKiemKe.dang_kiem:
        raise _da_chot()
    dong = {
        ct.lo_id: ct
        for ct in (
            await db.execute(
                select(CtKiemKe)
                .where(CtKiemKe.phieu_kiem_ke_id == phieu_id, CtKiemKe.lo_id.in_([d.lo_id for d in du_lieu.dong]))
                .execution_options(populate_existing=True)
            )
        ).scalars()
    }
    for i, d in enumerate(du_lieu.dong):
        if d.lo_id not in dong:
            raise _loi_dau_vao(f"dong.{i}.lo_id", "Lô không thuộc phiếu kiểm kê này")
    for d in du_lieu.dong:
        dong[d.lo_id].so_luong_thuc_te = d.so_luong_thuc_te
        dong[d.lo_id].chenh_lech = d.so_luong_thuc_te - dong[d.lo_id].so_luong_so_sach
    await db.flush()
    return await chi_tiet(db, phieu_id)


async def chot(db: AsyncSession, actor: NhanVien, phieu_id: int, *, ip: str) -> KiemKeChiTiet:
    phieu = await _khoa_phieu(db, phieu_id)
    if phieu.trang_thai != TrangThaiKiemKe.dang_kiem:
        raise _da_chot()
    chua = await db.scalar(
        select(func.count()).where(CtKiemKe.phieu_kiem_ke_id == phieu_id, CtKiemKe.so_luong_thuc_te.is_(None))
    )
    if chua:
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE",
            f"Còn {chua} lô chưa nhập số lượng thực tế",
            chi_tiet={"so_dong_chua_nhap": chua},
        )
    phieu.trang_thai = TrangThaiKiemKe.da_chot
    phieu.chot_luc = bay_gio_utc()
    await db.flush()
    lech = await db.scalar(select(func.count()).where(CtKiemKe.phieu_kiem_ke_id == phieu_id, CtKiemKe.chenh_lech != 0))
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="sua",
        bang=BANG,
        ban_ghi_id=phieu.id,
        gia_tri_cu={"trang_thai": "dang_kiem"},
        gia_tri_moi={"trang_thai": "da_chot", "so_dong_lech": lech},
        ip=ip,
    )
    return await chi_tiet(db, phieu_id)


async def xoa(db: AsyncSession, actor: NhanVien, phieu_id: int, *, ip: str) -> None:
    phieu = await _khoa_phieu(db, phieu_id)
    if phieu.trang_thai != TrangThaiKiemKe.dang_kiem:
        raise _da_chot()
    if await db.scalar(select(PhieuDieuChinh.id).where(PhieuDieuChinh.phieu_kiem_ke_id == phieu_id).limit(1)):
        raise _da_chot()
    ma = phieu.ma_phieu
    await db.execute(delete(CtKiemKe).where(CtKiemKe.phieu_kiem_ke_id == phieu_id))
    await db.delete(phieu)
    await db.flush()
    await ghi_nhat_ky(
        db, nhan_vien_id=actor.id, hanh_dong="xoa", bang=BANG, ban_ghi_id=phieu_id, gia_tri_cu={"ma_phieu": ma}, ip=ip
    )

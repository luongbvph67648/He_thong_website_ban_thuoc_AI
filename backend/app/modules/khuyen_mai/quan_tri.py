"""Quản lý khuyến mãi và mã giảm giá của Admin (AD06, `promotion.manage`, spec 06 mục 3.21).

Chỉ Admin ghi (`dam_bao_la_admin`). Khóa lạc quan `phien_ban` (dấu vân tay nội dung) như các màn Admin khác.
Thuốc kê đơn không được đưa vào phạm vi (nếu có cũng bị loại khi tính giảm, xem `ap_dung`).
"""

import secrets
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cau_hinh_khoa import dau_van_tay
from app.core.loi import LoiNghiepVu
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_quyen import dam_bao_la_admin
from app.core.phan_trang import ThamSoPhanTrang, Trang, lay_trang, tao_trang
from app.core.thoi_gian import bay_gio_utc
from app.models.ban_hang import DonHang, KhuyenMai, KhuyenMaiPhamVi, MaGiamGia
from app.models.enums import LoaiSanPham, PhamViKhuyenMai
from app.models.he_thong import NhanVien
from app.models.san_pham import DanhMuc, SanPham
from app.modules.khuyen_mai.ap_dung import chuan_hoa_ma
from app.modules.khuyen_mai.schemas import (
    KhuyenMaiChiTiet,
    KhuyenMaiSua,
    KhuyenMaiTomTat,
    KhuyenMaiVao,
    MaRa,
    PhamViRa,
    SinhMa,
    TrangThaiHieuLuc,
)

BANG = "khuyen_mai"
KY_TU_MA = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # bỏ ký tự dễ nhầm (0/O, 1/I)
DO_DAI_MA = 8
TRUONG = (
    "ten", "loai_giam", "gia_tri", "giam_toi_da", "don_toi_thieu", "bat_dau", "ket_thuc", "tong_luot",
    "luot_moi_khach", "pham_vi", "dang_hoat_dong",
)  # fmt: skip


def _khong_hop_le(truong: str, loi: str) -> LoiNghiepVu:
    return LoiNghiepVu("DU_LIEU_KHONG_HOP_LE", "Dữ liệu không hợp lệ", chi_tiet=[{"truong": truong, "loi": loi}])


def _gia_tri(v: Any) -> Any:
    return v.isoformat() if isinstance(v, datetime) else (str(v) if hasattr(v, "quantize") else getattr(v, "value", v))


async def _pham_vi_ids(db: AsyncSession, km_id: int) -> tuple[list[int], list[int]]:
    ds = (await db.execute(select(KhuyenMaiPhamVi).where(KhuyenMaiPhamVi.khuyen_mai_id == km_id))).scalars().all()
    return (
        sorted(p.danh_muc_id for p in ds if p.danh_muc_id is not None),
        sorted(p.san_pham_id for p in ds if p.san_pham_id is not None),
    )


async def phien_ban(db: AsyncSession, km: KhuyenMai) -> str:
    danh_muc, san_pham = await _pham_vi_ids(db, km.id)
    noi_dung = {t: _gia_tri(getattr(km, t)) for t in TRUONG} | {"danh_muc": danh_muc, "san_pham": san_pham}
    return dau_van_tay(noi_dung)


def trang_thai_hieu_luc(km: KhuyenMai, bay_gio: datetime) -> TrangThaiHieuLuc:
    if not km.dang_hoat_dong:
        return "da_tat"
    if bay_gio < km.bat_dau:
        return "sap_dien_ra"
    if bay_gio >= km.ket_thuc:
        return "het_han"
    return "dang_hieu_luc"


async def _thong_ke(db: AsyncSession, ids: list[int]) -> dict[int, tuple[int, int]]:
    if not ids:
        return {}
    dong = await db.execute(
        select(MaGiamGia.khuyen_mai_id, func.count(), func.coalesce(func.sum(MaGiamGia.so_luot_da_dung), 0))
        .where(MaGiamGia.khuyen_mai_id.in_(ids))
        .group_by(MaGiamGia.khuyen_mai_id)
    )
    return {k: (int(n), int(d)) for k, n, d in dong.all()}


def _tom_tat(km: KhuyenMai, thong_ke: tuple[int, int], bay_gio: datetime) -> dict[str, Any]:
    return {
        "id": km.id, "ten": km.ten, "loai_giam": km.loai_giam, "gia_tri": km.gia_tri, "giam_toi_da": km.giam_toi_da,
        "don_toi_thieu": km.don_toi_thieu, "bat_dau": km.bat_dau, "ket_thuc": km.ket_thuc, "tong_luot": km.tong_luot,
        "luot_moi_khach": km.luot_moi_khach, "pham_vi": km.pham_vi, "dang_hoat_dong": km.dang_hoat_dong,
        "trang_thai": trang_thai_hieu_luc(km, bay_gio), "so_ma": thong_ke[0], "da_dung": thong_ke[1],
    }  # fmt: skip


async def danh_sach(
    db: AsyncSession, tp: ThamSoPhanTrang, *, trang_thai: TrangThaiHieuLuc | None, q: str | None
) -> Trang[KhuyenMaiTomTat]:
    bay_gio = bay_gio_utc()
    stmt = select(KhuyenMai)
    if q and q.strip():
        stmt = stmt.where(KhuyenMai.ten.ilike(f"%{q.strip().replace('%', '').replace('_', '')}%"))
    if trang_thai == "da_tat":
        stmt = stmt.where(KhuyenMai.dang_hoat_dong.is_(False))
    elif trang_thai == "sap_dien_ra":
        stmt = stmt.where(KhuyenMai.dang_hoat_dong.is_(True), KhuyenMai.bat_dau > bay_gio)
    elif trang_thai == "dang_hieu_luc":
        stmt = stmt.where(
            KhuyenMai.dang_hoat_dong.is_(True), KhuyenMai.bat_dau <= bay_gio, KhuyenMai.ket_thuc > bay_gio
        )
    elif trang_thai == "het_han":
        stmt = stmt.where(KhuyenMai.dang_hoat_dong.is_(True), KhuyenMai.ket_thuc <= bay_gio)
    dong, tong = await lay_trang(db, stmt.order_by(KhuyenMai.id.desc()), tp)
    thong_ke = await _thong_ke(db, [k.id for k in dong])
    return tao_trang([KhuyenMaiTomTat(**_tom_tat(k, thong_ke.get(k.id, (0, 0)), bay_gio)) for k in dong], tong, tp)


async def _lay(db: AsyncSession, km_id: int, *, khoa: bool = False) -> KhuyenMai:
    truy_van = select(KhuyenMai).where(KhuyenMai.id == km_id)
    if khoa:
        truy_van = truy_van.with_for_update().execution_options(populate_existing=True)
    km = (await db.execute(truy_van)).scalar_one_or_none()
    if km is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy khuyến mãi")
    return km


async def chi_tiet(db: AsyncSession, km_id: int) -> KhuyenMaiChiTiet:
    km = await _lay(db, km_id)
    thong_ke = (await _thong_ke(db, [km.id])).get(km.id, (0, 0))
    dm_ids, sp_ids = await _pham_vi_ids(db, km.id)
    ten_dm = (
        dict((await db.execute(select(DanhMuc.id, DanhMuc.ten).where(DanhMuc.id.in_(dm_ids)))).all()) if dm_ids else {}
    )
    ten_sp = (
        dict((await db.execute(select(SanPham.id, SanPham.ten).where(SanPham.id.in_(sp_ids)))).all()) if sp_ids else {}
    )
    ma = (
        (await db.execute(select(MaGiamGia).where(MaGiamGia.khuyen_mai_id == km.id).order_by(MaGiamGia.id)))
        .scalars()
        .all()
    )
    return KhuyenMaiChiTiet(
        **_tom_tat(km, thong_ke, bay_gio_utc()),
        phien_ban=await phien_ban(db, km),
        danh_muc=[PhamViRa(id=i, ten=ten_dm[i]) for i in dm_ids],
        san_pham=[PhamViRa(id=i, ten=ten_sp[i]) for i in sp_ids],
        ma_giam_gia=[MaRa(id=m.id, ma=m.ma, so_luot_da_dung=m.so_luot_da_dung) for m in ma],
    )


async def _kiem_tra_pham_vi(db: AsyncSession, vao: KhuyenMaiVao) -> None:
    if vao.pham_vi == PhamViKhuyenMai.danh_muc:
        co = set(
            (
                await db.execute(
                    select(DanhMuc.id).where(DanhMuc.id.in_(vao.danh_muc_ids), DanhMuc.deleted_at.is_(None))
                )
            ).scalars()
        )
        thieu = [i for i in vao.danh_muc_ids if i not in co]
        if thieu:
            raise _khong_hop_le("danh_muc_ids", f"Danh mục không tồn tại: {thieu}")
    elif vao.pham_vi == PhamViKhuyenMai.san_pham:
        sp = {
            i: loai
            for i, loai in (
                await db.execute(
                    select(SanPham.id, SanPham.loai_san_pham).where(
                        SanPham.id.in_(vao.san_pham_ids), SanPham.deleted_at.is_(None)
                    )
                )
            ).all()
        }
        thieu = [i for i in vao.san_pham_ids if i not in sp]
        if thieu:
            raise _khong_hop_le("san_pham_ids", f"Sản phẩm không tồn tại: {thieu}")
        ke_don = [i for i, loai in sp.items() if loai == LoaiSanPham.thuoc_ke_don]
        if ke_don:
            raise _khong_hop_le("san_pham_ids", f"Thuốc kê đơn không được áp dụng khuyến mãi: {ke_don}")


async def _ghi_pham_vi(db: AsyncSession, km: KhuyenMai, vao: KhuyenMaiVao) -> None:
    await db.execute(delete(KhuyenMaiPhamVi).where(KhuyenMaiPhamVi.khuyen_mai_id == km.id))
    for i in vao.danh_muc_ids:
        db.add(KhuyenMaiPhamVi(khuyen_mai_id=km.id, danh_muc_id=i))
    for i in vao.san_pham_ids:
        db.add(KhuyenMaiPhamVi(khuyen_mai_id=km.id, san_pham_id=i))
    await db.flush()


def _gan(km: KhuyenMai, vao: KhuyenMaiVao) -> None:
    for t in TRUONG:
        setattr(km, t, getattr(vao, t))


async def tao(db: AsyncSession, nguoi: NhanVien, vao: KhuyenMaiVao, ip: str | None) -> KhuyenMaiChiTiet:
    await dam_bao_la_admin(db, nguoi)
    await _kiem_tra_pham_vi(db, vao)
    km = KhuyenMai()
    _gan(km, vao)
    db.add(km)
    await db.flush()
    await _ghi_pham_vi(db, km, vao)
    await ghi_nhat_ky(
        db, nhan_vien_id=nguoi.id, hanh_dong="tao", bang=BANG, ban_ghi_id=km.id, gia_tri_moi={"ten": km.ten}, ip=ip
    )
    return await chi_tiet(db, km.id)


async def sua(db: AsyncSession, nguoi: NhanVien, km_id: int, vao: KhuyenMaiSua, ip: str | None) -> KhuyenMaiChiTiet:
    await dam_bao_la_admin(db, nguoi)
    km = await _lay(db, km_id, khoa=True)
    if await phien_ban(db, km) != vao.phien_ban:
        raise LoiNghiepVu("DU_LIEU_DA_THAY_DOI", "Khuyến mãi đã được người khác thay đổi, hãy tải lại trước khi lưu")
    await _kiem_tra_pham_vi(db, vao)
    cu = {t: _gia_tri(getattr(km, t)) for t in TRUONG}
    _gan(km, vao)
    await db.flush()
    await _ghi_pham_vi(db, km, vao)
    await ghi_nhat_ky(
        db, nhan_vien_id=nguoi.id, hanh_dong="sua", bang=BANG, ban_ghi_id=km.id, gia_tri_cu=cu,
        gia_tri_moi={t: _gia_tri(getattr(km, t)) for t in TRUONG}, ip=ip,
    )  # fmt: skip
    return await chi_tiet(db, km.id)


async def _co_don(db: AsyncSession, ma_ids: list[int]) -> bool:
    if not ma_ids:
        return False
    return bool(await db.scalar(select(func.count()).select_from(DonHang).where(DonHang.ma_giam_gia_id.in_(ma_ids))))


async def xoa(db: AsyncSession, nguoi: NhanVien, km_id: int, ip: str | None) -> None:
    """Xóa hẳn khi chưa mã nào được dùng; ngược lại giữ lịch sử, yêu cầu tắt khuyến mãi."""
    await dam_bao_la_admin(db, nguoi)
    km = await _lay(db, km_id, khoa=True)
    ma = (await db.execute(select(MaGiamGia).where(MaGiamGia.khuyen_mai_id == km.id))).scalars().all()
    if any(m.so_luot_da_dung for m in ma) or await _co_don(db, [m.id for m in ma]):
        raise LoiNghiepVu(
            "DU_LIEU_DANG_DUOC_SU_DUNG",
            "Khuyến mãi đã có đơn dùng mã, hãy tắt thay vì xóa",
            chi_tiet={"khuyen_mai_id": km.id},
        )
    await db.execute(delete(KhuyenMaiPhamVi).where(KhuyenMaiPhamVi.khuyen_mai_id == km.id))
    await db.execute(delete(MaGiamGia).where(MaGiamGia.khuyen_mai_id == km.id))
    await db.delete(km)
    await db.flush()
    await ghi_nhat_ky(
        db, nhan_vien_id=nguoi.id, hanh_dong="xoa", bang=BANG, ban_ghi_id=km_id, gia_tri_cu={"ten": km.ten}, ip=ip
    )


def _sinh_ma() -> str:
    return "".join(secrets.choice(KY_TU_MA) for _ in range(DO_DAI_MA))


async def sinh_ma(db: AsyncSession, nguoi: NhanVien, km_id: int, vao: SinhMa, ip: str | None) -> list[MaRa]:
    await dam_bao_la_admin(db, nguoi)
    km = await _lay(db, km_id, khoa=True)
    ket: list[MaGiamGia] = []
    if vao.ma is not None:
        ma = chuan_hoa_ma(vao.ma)
        if await db.scalar(select(MaGiamGia.id).where(MaGiamGia.ma == ma)):
            raise LoiNghiepVu("TRUNG_DU_LIEU", "Mã giảm giá đã tồn tại", chi_tiet={"truong": "ma"})
        ket.append(MaGiamGia(khuyen_mai_id=km.id, ma=ma))
    else:
        da_co = set((await db.execute(select(MaGiamGia.ma))).scalars())
        while len(ket) < vao.so_luong:
            ma = _sinh_ma()
            if ma in da_co:
                continue
            da_co.add(ma)
            ket.append(MaGiamGia(khuyen_mai_id=km.id, ma=ma))
    db.add_all(ket)
    await db.flush()
    await ghi_nhat_ky(
        db,
        nhan_vien_id=nguoi.id,
        hanh_dong="sinh_ma",
        bang=BANG,
        ban_ghi_id=km.id,
        gia_tri_moi={"so_luong": len(ket)},
        ip=ip,
    )
    return [MaRa(id=m.id, ma=m.ma, so_luot_da_dung=0) for m in ket]


async def xoa_ma(db: AsyncSession, nguoi: NhanVien, km_id: int, ma_id: int, ip: str | None) -> None:
    await dam_bao_la_admin(db, nguoi)
    await _lay(db, km_id, khoa=True)
    ma = (
        await db.execute(
            select(MaGiamGia).where(MaGiamGia.id == ma_id, MaGiamGia.khuyen_mai_id == km_id).with_for_update()
        )
    ).scalar_one_or_none()
    if ma is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy mã giảm giá")
    if ma.so_luot_da_dung or await _co_don(db, [ma.id]):
        raise LoiNghiepVu(
            "DU_LIEU_DANG_DUOC_SU_DUNG", "Mã đã có đơn dùng, không xóa được", chi_tiet={"ma_giam_gia_id": ma.id}
        )
    await db.delete(ma)
    await db.flush()
    await ghi_nhat_ky(
        db, nhan_vien_id=nguoi.id, hanh_dong="xoa_ma", bang=BANG, ban_ghi_id=km_id, gia_tri_cu={"ma": ma.ma}, ip=ip
    )

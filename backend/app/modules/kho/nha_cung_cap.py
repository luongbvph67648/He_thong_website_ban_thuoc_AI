"""Quản lý nhà cung cấp (KHO01, spec 06 mục 3.15). Nhân viên kho ghi (`supplier.manage`), Admin chỉ xem.

Ngừng hợp tác = xóa mềm (`deleted_at` cùng `dang_hop_tac = false`) vì phiếu nhập cũ còn tham chiếu. Khóa lạc quan bằng
dấu vân tay các trường sửa được (kể cả `dang_hop_tac`): màn mở từ trước không ghi đè thay đổi của người khác.
"""

from typing import Any, Literal

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cau_hinh_khoa import dau_van_tay
from app.core.loi import LoiNghiepVu
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_trang import ThamSoPhanTrang, Trang, lay_trang, tao_trang
from app.core.thoi_gian import bay_gio_utc
from app.core.tim_kiem import mau_tim_like
from app.models.he_thong import NhanVien
from app.models.kho import NhaCungCap
from app.modules.kho.schemas_nha_cung_cap import NhaCungCapRa, NhaCungCapSua, NhaCungCapTao

BANG = "nha_cung_cap"
TRUONG = ("ten", "ma_so_thue", "dia_chi", "nguoi_lien_he", "so_dien_thoai", "email")
TrangThaiLoc = Literal["dang_hop_tac", "ngung", "tat_ca"]


def _noi_dung(n: NhaCungCap) -> dict[str, Any]:
    return {**{t: getattr(n, t) for t in TRUONG}, "dang_hop_tac": n.dang_hop_tac}


def phien_ban(n: NhaCungCap) -> str:
    return dau_van_tay(_noi_dung(n))


def ra(n: NhaCungCap) -> NhaCungCapRa:
    return NhaCungCapRa(
        id=n.id,
        **_noi_dung(n),
        created_at=n.created_at,
        phien_ban=phien_ban(n),
    )


def khong_tim_thay() -> LoiNghiepVu:
    return LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy nhà cung cấp")


def da_thay_doi(hien_tai: str) -> LoiNghiepVu:
    return LoiNghiepVu(
        "DU_LIEU_DA_THAY_DOI",
        "Nhà cung cấp đã được người khác thay đổi, hãy tải lại rồi sửa tiếp",
        chi_tiet={"phien_ban_hien_tai": hien_tai},
    )


async def _khoa(db: AsyncSession, nha_cung_cap_id: int) -> NhaCungCap:
    n = (
        await db.execute(
            select(NhaCungCap)
            .where(NhaCungCap.id == nha_cung_cap_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if n is None:
        raise khong_tim_thay()
    return n


async def _khoa_ma_so_thue(db: AsyncSession) -> None:
    """Mã số thuế duy nhất kể cả với nhà cung cấp đã ngừng: tuần tự hóa kiểm tra trùng cho các lần ghi đồng thời."""
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext('nha_thuoc.nha_cung_cap.ma_so_thue'))"))


async def _kiem_tra_trung_mst(db: AsyncSession, ma_so_thue: str | None, *, tru_id: int | None = None) -> None:
    if ma_so_thue is None:
        return
    dieu_kien = [NhaCungCap.ma_so_thue == ma_so_thue]
    if tru_id is not None:
        dieu_kien.append(NhaCungCap.id != tru_id)
    if (await db.execute(select(NhaCungCap.id).where(*dieu_kien).limit(1))).first() is not None:
        raise LoiNghiepVu(
            "TRUNG_DU_LIEU", "Mã số thuế này đã thuộc một nhà cung cấp khác", chi_tiet={"truong": "ma_so_thue"}
        )


async def danh_sach(
    db: AsyncSession, q: str | None, trang_thai: TrangThaiLoc, tp: ThamSoPhanTrang
) -> Trang[NhaCungCapRa]:
    truy_van = select(NhaCungCap)
    if trang_thai == "dang_hop_tac":
        truy_van = truy_van.where(NhaCungCap.deleted_at.is_(None))
    elif trang_thai == "ngung":
        truy_van = truy_van.where(NhaCungCap.deleted_at.is_not(None))
    if q and q.strip():
        mau = func.f_unaccent(func.lower(mau_tim_like(q)))
        truy_van = truy_van.where(
            or_(
                *[
                    func.f_unaccent(func.lower(func.coalesce(cot, ""))).like(mau, escape="\\")
                    for cot in (
                        NhaCungCap.ten,
                        NhaCungCap.ma_so_thue,
                        NhaCungCap.nguoi_lien_he,
                        NhaCungCap.so_dien_thoai,
                    )
                ]
            )
        )
    dong, tong = await lay_trang(db, truy_van.order_by(func.lower(NhaCungCap.ten), NhaCungCap.id), tp)
    return tao_trang([ra(n) for n in dong], tong, tp)


async def chi_tiet(db: AsyncSession, nha_cung_cap_id: int) -> NhaCungCapRa:
    n = await db.get(NhaCungCap, nha_cung_cap_id)
    if n is None:
        raise khong_tim_thay()
    return ra(n)


async def tao(db: AsyncSession, actor: NhanVien, du_lieu: NhaCungCapTao, *, ip: str) -> NhaCungCapRa:
    await _khoa_ma_so_thue(db)
    await _kiem_tra_trung_mst(db, du_lieu.ma_so_thue)
    n = NhaCungCap(**du_lieu.model_dump())
    db.add(n)
    await db.flush()
    await ghi_nhat_ky(
        db, nhan_vien_id=actor.id, hanh_dong="tao", bang=BANG, ban_ghi_id=n.id, gia_tri_moi=_noi_dung(n), ip=ip
    )
    return ra(n)


async def sua(
    db: AsyncSession, actor: NhanVien, nha_cung_cap_id: int, du_lieu: NhaCungCapSua, *, ip: str
) -> NhaCungCapRa:
    if "ma_so_thue" in du_lieu.model_fields_set:
        await _khoa_ma_so_thue(db)
    n = await _khoa(db, nha_cung_cap_id)
    if phien_ban(n) != du_lieu.phien_ban:
        raise da_thay_doi(phien_ban(n))
    cu = _noi_dung(n)
    thay_doi = {t: getattr(du_lieu, t) for t in TRUONG if t in du_lieu.model_fields_set}
    if "ma_so_thue" in thay_doi:
        await _kiem_tra_trung_mst(db, thay_doi["ma_so_thue"], tru_id=n.id)
    for t, gia_tri in thay_doi.items():
        setattr(n, t, gia_tri)
    await db.flush()
    moi = _noi_dung(n)
    if moi != cu:
        await ghi_nhat_ky(
            db,
            nhan_vien_id=actor.id,
            hanh_dong="sua",
            bang=BANG,
            ban_ghi_id=n.id,
            gia_tri_cu=cu,
            gia_tri_moi=moi,
            ip=ip,
        )
    return ra(n)


async def ngung_hop_tac(
    db: AsyncSession, actor: NhanVien, nha_cung_cap_id: int, phien_ban_dang_xem: str, *, ip: str
) -> None:
    n = await _khoa(db, nha_cung_cap_id)
    if phien_ban(n) != phien_ban_dang_xem or n.deleted_at is not None:
        raise da_thay_doi(phien_ban(n))
    cu = _noi_dung(n)
    n.deleted_at = bay_gio_utc()
    n.dang_hop_tac = False
    await db.flush()
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="xoa",
        bang=BANG,
        ban_ghi_id=n.id,
        gia_tri_cu=cu,
        gia_tri_moi=_noi_dung(n),
        ip=ip,
    )


async def hop_tac_lai(db: AsyncSession, actor: NhanVien, nha_cung_cap_id: int, *, ip: str) -> NhaCungCapRa:
    n = await _khoa(db, nha_cung_cap_id)
    if n.deleted_at is None:
        return ra(n)
    cu = _noi_dung(n)
    n.deleted_at = None
    n.dang_hop_tac = True
    await db.flush()
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="khoi_phuc",
        bang=BANG,
        ban_ghi_id=n.id,
        gia_tri_cu=cu,
        gia_tri_moi=_noi_dung(n),
        ip=ip,
    )
    return ra(n)

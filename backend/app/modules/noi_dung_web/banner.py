"""Banner trang chủ (AD07, spec 06 mục 3.14). Chỉ Admin ghi (`cms.manage` mức đầy đủ và `dam_bao_la_admin`).

Khóa lạc quan bằng dấu vân tay nội dung (`phien_ban`), như các màn Admin khác: trang mở từ trước không ghi đè thay
đổi của người khác. Không xóa mềm (bảng không có `deleted_at`): xóa là xóa hẳn, có ghi nhật ký; muốn ẩn tạm thì tắt
`dang_hien`.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cau_hinh_khoa import dau_van_tay
from app.core.loi import LoiNghiepVu
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_quyen import dam_bao_la_admin
from app.core.thoi_gian import bay_gio_utc
from app.models.he_thong import Banner, NhanVien
from app.modules.noi_dung_web.schemas import BannerRa, BannerSua, BannerVao

BANG = "banner"
TRUONG = ("tieu_de", "anh_url", "lien_ket", "vi_tri", "thu_tu", "bat_dau", "ket_thuc", "dang_hien")


def _iso(gia_tri: Any) -> Any:
    return gia_tri.isoformat() if isinstance(gia_tri, datetime) else gia_tri


def _noi_dung(b: Banner) -> dict[str, Any]:
    return {truong: _iso(getattr(b, truong)) for truong in TRUONG}


def phien_ban(b: Banner) -> str:
    return dau_van_tay(_noi_dung(b))


def _co_mui_gio(luc: datetime | None) -> datetime | None:
    """Dữ liệu cũ ngoài miền (ghi trước khi có giới hạn năm) có thể về từ CSDL không kèm múi giờ: coi là UTC."""
    return luc if luc is None or luc.tzinfo is not None else luc.replace(tzinfo=UTC)


def tinh_trang(b: Banner, bay_gio: datetime) -> str:
    bat_dau, ket_thuc = _co_mui_gio(b.bat_dau), _co_mui_gio(b.ket_thuc)
    if not b.dang_hien:
        return "da_tat"
    if bat_dau and bat_dau > bay_gio:
        return "chua_den_gio"
    if ket_thuc and ket_thuc <= bay_gio:
        return "het_han"
    return "dang_hien"


def ra(b: Banner, bay_gio: datetime) -> BannerRa:
    return BannerRa(
        id=b.id,
        tieu_de=b.tieu_de,
        anh_url=b.anh_url,
        lien_ket=b.lien_ket,
        vi_tri=b.vi_tri,
        thu_tu=b.thu_tu,
        bat_dau=b.bat_dau,
        ket_thuc=b.ket_thuc,
        dang_hien=b.dang_hien,
        tinh_trang=tinh_trang(b, bay_gio),  # type: ignore[arg-type]
        phien_ban=phien_ban(b),
    )


def _loi_truong(truong: str, loi: str) -> LoiNghiepVu:
    return LoiNghiepVu("DU_LIEU_KHONG_HOP_LE", "Dữ liệu không hợp lệ", chi_tiet=[{"truong": truong, "loi": loi}])


async def danh_sach(db: AsyncSession) -> list[BannerRa]:
    """Mọi banner (kể cả đã tắt, chưa tới giờ, hết hạn) theo vị trí rồi thứ tự."""
    bay_gio = bay_gio_utc()
    dong = (await db.execute(select(Banner).order_by(Banner.vi_tri, Banner.thu_tu, Banner.id))).scalars()
    return [ra(b, bay_gio) for b in dong]


async def _khoa(db: AsyncSession, banner_id: int, phien_ban_gui: str) -> Banner:
    b = (
        await db.execute(
            select(Banner).where(Banner.id == banner_id).with_for_update().execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if b is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy banner")
    hien_tai = phien_ban(b)
    if hien_tai != phien_ban_gui:
        raise LoiNghiepVu(
            "DU_LIEU_DA_THAY_DOI",
            "Banner đã được người khác thay đổi, hãy tải lại rồi sửa tiếp",
            chi_tiet={"phien_ban_hien_tai": hien_tai},
        )
    return b


async def tao(db: AsyncSession, actor: NhanVien, du_lieu: BannerVao, *, ip: str) -> BannerRa:
    await dam_bao_la_admin(db, actor)
    b = Banner(**du_lieu.model_dump())
    db.add(b)
    await db.flush()
    await ghi_nhat_ky(
        db, nhan_vien_id=actor.id, hanh_dong="tao", bang=BANG, ban_ghi_id=b.id, gia_tri_moi=_noi_dung(b), ip=ip
    )
    return ra(b, bay_gio_utc())


async def sua(db: AsyncSession, actor: NhanVien, banner_id: int, du_lieu: BannerSua, *, ip: str) -> BannerRa:
    await dam_bao_la_admin(db, actor)
    b = await _khoa(db, banner_id, du_lieu.phien_ban)
    cu = _noi_dung(b)
    for truong in du_lieu.model_fields_set - {"phien_ban"}:
        setattr(b, truong, getattr(du_lieu, truong))
    if b.bat_dau and b.ket_thuc and b.ket_thuc <= b.bat_dau:
        raise _loi_truong("ket_thuc", "Thời điểm kết thúc phải sau thời điểm bắt đầu")
    moi = _noi_dung(b)
    if moi != cu:
        await db.flush()
        await ghi_nhat_ky(
            db,
            nhan_vien_id=actor.id,
            hanh_dong="sua",
            bang=BANG,
            ban_ghi_id=b.id,
            gia_tri_cu={k: v for k, v in cu.items() if moi[k] != v},
            gia_tri_moi={k: v for k, v in moi.items() if cu[k] != v},
            ip=ip,
        )
    return ra(b, bay_gio_utc())


async def xoa(db: AsyncSession, actor: NhanVien, banner_id: int, phien_ban_gui: str, *, ip: str) -> None:
    await dam_bao_la_admin(db, actor)
    b = await _khoa(db, banner_id, phien_ban_gui)
    cu = _noi_dung(b)
    await db.delete(b)
    await db.flush()
    await ghi_nhat_ky(db, nhan_vien_id=actor.id, hanh_dong="xoa", bang=BANG, ban_ghi_id=banner_id, gia_tri_cu=cu, ip=ip)

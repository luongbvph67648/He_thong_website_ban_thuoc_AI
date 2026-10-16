"""Bài viết sức khỏe, chính sách, FAQ của Admin (AD07, spec 06 mục 3.14).

Vòng đời (`bai_viet.trang_thai`):
- `loai = bai_viet` (bài sức khỏe): tạo ở `nhap`, dược sĩ duyệt (DS10) mới `da_duyet` và công khai. SỬA bài đã duyệt
  đưa nó về `nhap` (nội dung đã đổi thì phải duyệt lại); chỉ đổi `dua_vao_ai` thì không.
- `chinh_sach`, `faq`: Admin đăng trực tiếp (`da_duyet` ngay khi tạo), không qua dược sĩ.
- Gỡ bài (`go`): `nhap` hoặc `da_duyet` sang `luu_tru` (không công khai, không xóa). Đăng lại (`dang`): `luu_tru` về
  `nhap` với bài sức khỏe (duyệt lại) hoặc `da_duyet` với chính sách/FAQ.
- `loai` không đổi được: đổi loại là cách vòng qua bước dược sĩ duyệt.
Chỉ Admin ghi (`cms.manage` mức đầy đủ và `dam_bao_la_admin`). Khóa lạc quan bằng `phien_ban` (dấu vân tay nội dung).
"""

from typing import Any

from sqlalchemy import Select, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from app.core.cau_hinh_khoa import dau_van_tay
from app.core.loi import LoiNghiepVu
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_quyen import dam_bao_la_admin
from app.core.phan_trang import ThamSoPhanTrang, lay_trang
from app.core.slug import tao_slug
from app.core.thoi_gian import bay_gio_utc
from app.core.tim_kiem import mau_tim_like
from app.models.enums import LoaiBaiViet, TrangThaiNoiDung
from app.models.he_thong import BaiViet, NhanVien
from app.modules.chuyen_mon.bai_viet_duyet import phien_ban_bai_viet
from app.modules.noi_dung_web.schemas import BaiVietAdmin, BaiVietSua, BaiVietTomTatAdmin, BaiVietVao

BANG = "bai_viet"
_KHOA_SLUG = "nha_thuoc.bai_viet_slug"
TRUONG_NOI_DUNG = ("tieu_de", "noi_dung", "anh_bia_url")  # đổi các trường này thì bài sức khỏe phải duyệt lại


def _khong_tim_thay() -> LoiNghiepVu:
    return LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy bài viết")


def _xung_dot(thong_diep: str, phien_ban_hien_tai: str | None = None) -> LoiNghiepVu:
    chi_tiet = {"phien_ban_hien_tai": phien_ban_hien_tai} if phien_ban_hien_tai else None
    return LoiNghiepVu("DU_LIEU_DA_THAY_DOI", thong_diep, chi_tiet=chi_tiet)


def _tom_tat(bv: BaiViet, tac_gia: str) -> dict[str, Any]:
    return {
        "id": bv.id,
        "tieu_de": bv.tieu_de,
        "slug": bv.slug,
        "loai": bv.loai,
        "trang_thai": bv.trang_thai,
        "dua_vao_ai": bv.dua_vao_ai,
        "tac_gia": tac_gia,
        "created_at": bv.created_at,
        "updated_at": bv.updated_at,
        "ngay_duyet": bv.ngay_duyet,
    }


async def _ten(db: AsyncSession, nhan_vien_id: int | None) -> str | None:
    if nhan_vien_id is None:
        return None
    return await db.scalar(select(NhanVien.ho_ten).where(NhanVien.id == nhan_vien_id))


async def _chi_tiet(db: AsyncSession, bv: BaiViet) -> BaiVietAdmin:
    await db.refresh(bv)
    return BaiVietAdmin(
        **_tom_tat(bv, await _ten(db, bv.tac_gia_id) or ""),
        noi_dung=bv.noi_dung,
        anh_bia_url=bv.anh_bia_url,
        duoc_si_duyet=await _ten(db, bv.duoc_si_duyet_id),
        phien_ban=phien_ban_bai_viet(bv),
    )


async def danh_sach(
    db: AsyncSession,
    *,
    loai: LoaiBaiViet | None,
    trang_thai: TrangThaiNoiDung | None,
    q: str | None,
    tp: ThamSoPhanTrang,
) -> tuple[list[BaiVietTomTatAdmin], int]:
    stmt: Select[Any] = (
        select(BaiViet, NhanVien.ho_ten)
        .options(defer(BaiViet.noi_dung))  # danh sách không cần toàn văn (tối đa 100.000 ký tự mỗi bài)
        .join(NhanVien, NhanVien.id == BaiViet.tac_gia_id)
    )
    if loai is not None:
        stmt = stmt.where(BaiViet.loai == loai)
    if trang_thai is not None:
        stmt = stmt.where(BaiViet.trang_thai == trang_thai)
    if q and q.strip():
        mau = mau_tim_like(q)
        stmt = stmt.where(
            func.f_unaccent(func.lower(BaiViet.tieu_de)).like(func.f_unaccent(func.lower(mau)), escape="\\")
        )
    stmt = stmt.order_by(func.coalesce(BaiViet.updated_at, BaiViet.created_at).desc(), BaiViet.id.desc())
    dong, tong = await lay_trang(db, stmt, tp, nhieu_cot=True)
    return [BaiVietTomTatAdmin(**_tom_tat(bv, tac_gia)) for bv, tac_gia in dong], tong


async def lay(db: AsyncSession, bai_viet_id: int) -> BaiVietAdmin:
    bv = (await db.execute(select(BaiViet).where(BaiViet.id == bai_viet_id))).scalar_one_or_none()
    if bv is None:
        raise _khong_tim_thay()
    return await _chi_tiet(db, bv)


async def _khoa(db: AsyncSession, bai_viet_id: int, phien_ban: str) -> BaiViet:
    bv = (
        await db.execute(
            select(BaiViet).where(BaiViet.id == bai_viet_id).with_for_update().execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if bv is None:
        raise _khong_tim_thay()
    hien_tai = phien_ban_bai_viet(bv)
    if hien_tai != phien_ban:
        raise _xung_dot("Bài viết đã được người khác thay đổi, hãy tải lại rồi sửa tiếp", hien_tai)
    return bv


async def _slug_chua_dung(db: AsyncSession, tieu_de: str) -> str:
    """Slug theo tiêu đề, thêm `-2`, `-3`... nếu trùng. Khóa tư vấn tuần tự hóa để hai bài cùng tiêu đề không đua."""
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:khoa))"), {"khoa": _KHOA_SLUG})
    try:
        goc = tao_slug(tieu_de, 250)
    except ValueError:
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE",
            "Dữ liệu không hợp lệ",
            chi_tiet=[{"truong": "tieu_de", "loi": "Tiêu đề phải có chữ hoặc số"}],
        ) from None
    da_co = set(
        (await db.execute(select(BaiViet.slug).where(BaiViet.slug.regexp_match(f"^{goc}(-[0-9]+)?$")))).scalars()
    )
    ung_vien, n = goc, 1
    while ung_vien in da_co:
        n += 1
        ung_vien = f"{goc}-{n}"
    return ung_vien


def _ghi(bv: BaiViet) -> dict[str, Any]:
    """Giá trị đưa vào nhật ký: KHÔNG kèm toàn văn `noi_dung` (có thể rất dài), chỉ độ dài và dấu vân tay (để biết nội
    dung đã đổi dù độ dài không đổi)."""
    return {
        "loai": bv.loai,
        "tieu_de": bv.tieu_de,
        "slug": bv.slug,
        "trang_thai": bv.trang_thai,
        "dua_vao_ai": bv.dua_vao_ai,
        "anh_bia_url": bv.anh_bia_url,
        "do_dai_noi_dung": len(bv.noi_dung),
        "dau_van_tay_noi_dung": dau_van_tay(bv.noi_dung),
    }


async def tao(db: AsyncSession, actor: NhanVien, du_lieu: BaiVietVao, *, ip: str) -> BaiVietAdmin:
    await dam_bao_la_admin(db, actor)
    suc_khoe = du_lieu.loai == LoaiBaiViet.bai_viet
    bv = BaiViet(
        tieu_de=du_lieu.tieu_de,
        slug=await _slug_chua_dung(db, du_lieu.tieu_de),
        noi_dung=du_lieu.noi_dung,
        anh_bia_url=du_lieu.anh_bia_url,
        loai=du_lieu.loai,
        tac_gia_id=actor.id,
        dua_vao_ai=du_lieu.dua_vao_ai,
        trang_thai=TrangThaiNoiDung.nhap if suc_khoe else TrangThaiNoiDung.da_duyet,
        ngay_duyet=None if suc_khoe else bay_gio_utc(),
    )
    db.add(bv)
    await db.flush()
    await ghi_nhat_ky(
        db, nhan_vien_id=actor.id, hanh_dong="tao", bang=BANG, ban_ghi_id=bv.id, gia_tri_moi=_ghi(bv), ip=ip
    )
    return await _chi_tiet(db, bv)


async def sua(db: AsyncSession, actor: NhanVien, bai_viet_id: int, du_lieu: BaiVietSua, *, ip: str) -> BaiVietAdmin:
    await dam_bao_la_admin(db, actor)
    bv = await _khoa(db, bai_viet_id, du_lieu.phien_ban)
    cu = _ghi(bv)
    doi_noi_dung = False
    for truong in du_lieu.model_fields_set - {"phien_ban"}:
        moi = getattr(du_lieu, truong)
        if getattr(bv, truong) != moi:
            setattr(bv, truong, moi)
            doi_noi_dung = doi_noi_dung or truong in TRUONG_NOI_DUNG
    if doi_noi_dung and bv.loai == LoaiBaiViet.bai_viet and bv.trang_thai == TrangThaiNoiDung.da_duyet:
        # Nội dung đã đổi thì bản dược sĩ từng duyệt không còn đúng: đưa về chờ duyệt, bỏ dấu duyệt cũ.
        bv.trang_thai = TrangThaiNoiDung.nhap
        bv.duoc_si_duyet_id = None
        bv.ngay_duyet = None
    moi_ghi = _ghi(bv)
    if moi_ghi != cu:
        bv.updated_at = bay_gio_utc()
    await db.flush()  # `_chi_tiet` nạp lại từ CSDL: thay đổi chưa flush sẽ bị vứt
    if moi_ghi != cu:
        await ghi_nhat_ky(
            db,
            nhan_vien_id=actor.id,
            hanh_dong="sua",
            bang=BANG,
            ban_ghi_id=bv.id,
            gia_tri_cu={k: v for k, v in cu.items() if moi_ghi[k] != v},
            gia_tri_moi={k: v for k, v in moi_ghi.items() if cu[k] != v},
            ip=ip,
        )
    return await _chi_tiet(db, bv)


async def go(db: AsyncSession, actor: NhanVien, bai_viet_id: int, phien_ban: str, *, ip: str) -> BaiVietAdmin:
    """Gỡ bài khỏi website (và khỏi hàng chờ duyệt): sang `luu_tru`."""
    await dam_bao_la_admin(db, actor)
    bv = await _khoa(db, bai_viet_id, phien_ban)
    if bv.trang_thai == TrangThaiNoiDung.luu_tru:
        raise _xung_dot("Bài viết đã được gỡ")
    cu = bv.trang_thai
    bv.trang_thai = TrangThaiNoiDung.luu_tru
    bv.updated_at = bay_gio_utc()
    await db.flush()
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="sua",
        bang=BANG,
        ban_ghi_id=bv.id,
        gia_tri_cu={"trang_thai": cu},
        gia_tri_moi={"trang_thai": bv.trang_thai},
        ip=ip,
    )
    return await _chi_tiet(db, bv)


async def dang(db: AsyncSession, actor: NhanVien, bai_viet_id: int, phien_ban: str, *, ip: str) -> BaiVietAdmin:
    """Đăng lại bài đã gỡ: bài sức khỏe về `nhap` (dược sĩ duyệt lại), chính sách/FAQ lên `da_duyet`."""
    await dam_bao_la_admin(db, actor)
    bv = await _khoa(db, bai_viet_id, phien_ban)
    if bv.trang_thai != TrangThaiNoiDung.luu_tru:
        raise _xung_dot("Chỉ đăng lại được bài đã gỡ")
    if bv.loai == LoaiBaiViet.bai_viet:
        bv.trang_thai = TrangThaiNoiDung.nhap
        bv.duoc_si_duyet_id = None
        bv.ngay_duyet = None
    else:
        bv.trang_thai = TrangThaiNoiDung.da_duyet
        bv.ngay_duyet = bay_gio_utc()
    bv.updated_at = bay_gio_utc()
    await db.flush()
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="sua",
        bang=BANG,
        ban_ghi_id=bv.id,
        gia_tri_cu={"trang_thai": "luu_tru"},
        gia_tri_moi={"trang_thai": bv.trang_thai},
        ip=ip,
    )
    return await _chi_tiet(db, bv)

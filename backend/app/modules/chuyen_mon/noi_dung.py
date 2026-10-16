"""Nội dung chuyên môn của sản phẩm (DS10): phiên bản, duyệt, lưu trữ (spec 06 mục 3.12, QĐ-18).

Quy tắc:
- Mỗi lần sửa tạo MỘT PHIÊN BẢN MỚI `nhap` (số tăng dần theo sản phẩm); bản đã có không bao giờ bị sửa tại chỗ.
- Mỗi sản phẩm có tối đa MỘT bản `da_duyet` (bản đang hiển thị). Duyệt bản mới đưa bản đã duyệt cũ sang `luu_tru`;
  không duyệt được bản cũ hơn bản đang hiển thị (nếu không nội dung hiển thị lùi về một bản cũ mà không ai quyết định).
- Mọi thao tác ghi khóa dòng sản phẩm `FOR UPDATE` trước, nên đánh số phiên bản và duyệt không đua nhau.
- Chỉ dược sĩ ghi (`dam_bao_la_duoc_si`); Admin chỉ xem qua mức `chi_xem` của `content.professional.edit`.
"""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.loi import LoiNghiepVu
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_quyen import dam_bao_la_duoc_si
from app.core.phan_trang import ThamSoPhanTrang, lay_trang
from app.core.thoi_gian import bay_gio_utc
from app.core.tim_kiem import mau_tim_like
from app.models.enums import TrangThaiNoiDung
from app.models.he_thong import NhanVien
from app.models.san_pham import SanPham, ThongTinChuyenMon
from app.modules.chuyen_mon.schemas_noi_dung import (
    TRUONG_NOI_DUNG,
    DongNoiDung,
    NguoiRut,
    NoiDungSanPham,
    NoiDungVao,
    PhienBanNoiDung,
    SanPhamRut,
)

BANG = "thong_tin_chuyen_mon"


def _khong_tim_thay() -> LoiNghiepVu:
    return LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy sản phẩm hoặc phiên bản")


def _xung_dot(thong_diep: str) -> LoiNghiepVu:
    return LoiNghiepVu("DU_LIEU_DA_THAY_DOI", thong_diep)


async def _khoa_san_pham(db: AsyncSession, san_pham_id: int) -> SanPham:
    """Khóa dòng sản phẩm chưa xóa (tuần tự hóa mọi thao tác ghi nội dung của sản phẩm này)."""
    sp = (
        await db.execute(
            select(SanPham)
            .where(SanPham.id == san_pham_id, SanPham.deleted_at.is_(None))
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if sp is None:
        raise _khong_tim_thay()
    return sp


async def _nguoi(db: AsyncSession, ids: set[int]) -> dict[int, NguoiRut]:
    if not ids:
        return {}
    dong = await db.execute(select(NhanVien.id, NhanVien.ma_nhan_vien, NhanVien.ho_ten).where(NhanVien.id.in_(ids)))
    return {i: NguoiRut(id=i, ma_nhan_vien=ma, ho_ten=ten) for i, ma, ten in dong}


def _doc_phien_ban(tt: ThongTinChuyenMon, nguoi: dict[int, NguoiRut]) -> PhienBanNoiDung:
    return PhienBanNoiDung(
        id=tt.id,
        san_pham_id=tt.san_pham_id,
        phien_ban=tt.phien_ban,
        trang_thai=tt.trang_thai,
        **{truong: getattr(tt, truong) for truong in TRUONG_NOI_DUNG},
        nguoi_soan=nguoi.get(tt.nguoi_soan_id) if tt.nguoi_soan_id else None,
        duoc_si_duyet=nguoi.get(tt.duoc_si_duyet_id) if tt.duoc_si_duyet_id else None,
        ngay_duyet=tt.ngay_duyet,
        created_at=tt.created_at,
    )


async def _doc_cac_phien_ban(db: AsyncSession, cac_ban: Sequence[ThongTinChuyenMon]) -> list[PhienBanNoiDung]:
    ids = {x for tt in cac_ban for x in (tt.nguoi_soan_id, tt.duoc_si_duyet_id) if x is not None}
    nguoi = await _nguoi(db, ids)
    return [_doc_phien_ban(tt, nguoi) for tt in cac_ban]


async def lay_theo_san_pham(db: AsyncSession, san_pham_id: int) -> NoiDungSanPham:
    """Mọi phiên bản của một sản phẩm chưa xóa, mới nhất trước."""
    sp = (
        await db.execute(select(SanPham).where(SanPham.id == san_pham_id, SanPham.deleted_at.is_(None)))
    ).scalar_one_or_none()
    if sp is None:
        raise _khong_tim_thay()
    cac_ban = (
        (
            await db.execute(
                select(ThongTinChuyenMon)
                .where(ThongTinChuyenMon.san_pham_id == san_pham_id)
                .order_by(ThongTinChuyenMon.phien_ban.desc())
            )
        )
        .scalars()
        .all()
    )
    hien_thi = next((tt.phien_ban for tt in cac_ban if tt.trang_thai == TrangThaiNoiDung.da_duyet), None)
    return NoiDungSanPham(
        san_pham=SanPhamRut(id=sp.id, sku=sp.sku, ten=sp.ten, loai_san_pham=sp.loai_san_pham),
        phien_ban_hien_thi=hien_thi,
        phien_ban=await _doc_cac_phien_ban(db, cac_ban),
    )


async def noi_dung_da_duyet(db: AsyncSession, san_pham_id: int) -> PhienBanNoiDung | None:
    """Phiên bản ĐANG HIỂN THỊ (đã duyệt) của sản phẩm chưa xóa, hoặc `None`. Khách và AI chỉ đọc từ đây.

    Sản phẩm đã xóa mềm coi như không có nội dung. Nếu dữ liệu nhập tay làm một sản phẩm có nhiều bản `da_duyet`
    (DB chưa có ràng buộc, xem "Việc phát sinh" của lộ trình) thì lấy bản mới nhất thay vì lỗi 500 ở trang của khách.
    """
    tt = (
        (
            await db.execute(
                select(ThongTinChuyenMon)
                .join(SanPham, SanPham.id == ThongTinChuyenMon.san_pham_id)
                .where(
                    ThongTinChuyenMon.san_pham_id == san_pham_id,
                    ThongTinChuyenMon.trang_thai == TrangThaiNoiDung.da_duyet,
                    SanPham.deleted_at.is_(None),
                )
                .order_by(ThongTinChuyenMon.phien_ban.desc())
                .limit(1)
            )
        )
        .scalars()
        .first()
    )
    if tt is None:
        return None
    return (await _doc_cac_phien_ban(db, [tt]))[0]


def _noi_dung_cua(tt: ThongTinChuyenMon) -> dict[str, Any]:
    return {truong: getattr(tt, truong) for truong in TRUONG_NOI_DUNG}


async def tao_phien_ban(
    db: AsyncSession, actor: NhanVien, san_pham_id: int, du_lieu: NoiDungVao, *, ip: str
) -> PhienBanNoiDung:
    """Tạo phiên bản mới (`nhap`) từ nội dung gửi lên."""
    await dam_bao_la_duoc_si(db, actor)
    await _khoa_san_pham(db, san_pham_id)
    cac_ban = (
        (
            await db.execute(
                select(ThongTinChuyenMon)
                .where(ThongTinChuyenMon.san_pham_id == san_pham_id)
                .order_by(ThongTinChuyenMon.phien_ban.desc())
            )
        )
        .scalars()
        .all()
    )
    so_moi_nhat = cac_ban[0].phien_ban if cac_ban else None  # kể cả bản đã lưu trữ: số phiên bản không bao giờ dùng lại
    if du_lieu.phien_ban_co_so != so_moi_nhat:
        raise _xung_dot("Đã có phiên bản mới hơn phiên bản bạn đang soạn. Hãy tải lại và soạn tiếp từ bản mới nhất.")
    noi_dung = du_lieu.model_dump(include=set(TRUONG_NOI_DUNG))
    if all(v is None for v in noi_dung.values()):
        # Bản trống mà được duyệt sẽ xóa sạch chống chỉ định, liều dùng... đang hiển thị cho khách và AI.
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE",
            "Dữ liệu không hợp lệ",
            chi_tiet=[{"truong": "chi_dinh", "loi": "Cần nhập ít nhất một mục nội dung chuyên môn"}],
        )
    # Chống bản trùng so với bản còn hiệu lực mới nhất (nháp hoặc đã duyệt); nội dung của bản đã bỏ thì soạn lại được.
    con_hieu_luc = next((tt for tt in cac_ban if tt.trang_thai != TrangThaiNoiDung.luu_tru), None)
    if con_hieu_luc is not None and noi_dung == _noi_dung_cua(con_hieu_luc):
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE",
            "Dữ liệu không hợp lệ",
            chi_tiet=[{"truong": "chi_dinh", "loi": "Không có thay đổi so với phiên bản mới nhất"}],
        )
    tt = ThongTinChuyenMon(
        san_pham_id=san_pham_id,
        phien_ban=(so_moi_nhat or 0) + 1,
        trang_thai=TrangThaiNoiDung.nhap,
        nguoi_soan_id=actor.id,
        **noi_dung,
    )
    db.add(tt)
    await db.flush()
    await db.refresh(tt)
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="tao",
        bang=BANG,
        ban_ghi_id=tt.id,
        gia_tri_moi={"san_pham_id": san_pham_id, "phien_ban": tt.phien_ban, "trang_thai": "nhap"},
        ip=ip,
    )
    return (await _doc_cac_phien_ban(db, [tt]))[0]


async def _khoa_phien_ban(db: AsyncSession, phien_ban_id: int) -> ThongTinChuyenMon:
    """Khóa sản phẩm TRƯỚC (cùng thứ tự với `tao_phien_ban`) rồi khóa phiên bản; sản phẩm đã xóa coi như không có."""
    san_pham_id = await db.scalar(select(ThongTinChuyenMon.san_pham_id).where(ThongTinChuyenMon.id == phien_ban_id))
    if san_pham_id is None:
        raise _khong_tim_thay()
    await _khoa_san_pham(db, san_pham_id)
    tt = (
        await db.execute(
            select(ThongTinChuyenMon)
            .where(ThongTinChuyenMon.id == phien_ban_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if tt is None:
        raise _khong_tim_thay()
    return tt


async def duyet(db: AsyncSession, actor: NhanVien, phien_ban_id: int, *, ip: str) -> PhienBanNoiDung:
    """Duyệt một bản nháp: thành bản hiển thị duy nhất, bản đã duyệt trước đó sang `luu_tru`."""
    await dam_bao_la_duoc_si(db, actor)
    tt = await _khoa_phien_ban(db, phien_ban_id)
    if tt.trang_thai != TrangThaiNoiDung.nhap:
        raise _xung_dot("Phiên bản này không còn là bản nháp (đã được duyệt hoặc đã lưu trữ)")
    cac_ban_hien_thi = (
        (
            await db.execute(
                select(ThongTinChuyenMon)
                .where(
                    ThongTinChuyenMon.san_pham_id == tt.san_pham_id,
                    ThongTinChuyenMon.trang_thai == TrangThaiNoiDung.da_duyet,
                )
                .order_by(ThongTinChuyenMon.phien_ban.desc())
                .with_for_update()
            )
        )
        .scalars()
        .all()
    )
    dang_hien_thi = cac_ban_hien_thi[0] if cac_ban_hien_thi else None  # thường chỉ có một; nhiều thì dọn hết
    if dang_hien_thi is not None and dang_hien_thi.phien_ban > tt.phien_ban:
        raise _xung_dot("Đã có phiên bản mới hơn được duyệt. Hãy soạn bản mới từ bản đang hiển thị.")
    if cac_ban_hien_thi:
        for ban_cu in cac_ban_hien_thi:
            ban_cu.trang_thai = TrangThaiNoiDung.luu_tru
        await db.flush()  # gỡ bản cũ trước khi đặt bản mới (một bản đã duyệt mỗi sản phẩm)
    tt.trang_thai = TrangThaiNoiDung.da_duyet
    tt.duoc_si_duyet_id = actor.id
    tt.ngay_duyet = bay_gio_utc()
    await db.flush()
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="duyet",
        bang=BANG,
        ban_ghi_id=tt.id,
        gia_tri_cu={
            "san_pham_id": tt.san_pham_id,
            "phien_ban_hien_thi_truoc": dang_hien_thi.phien_ban if dang_hien_thi else None,
        },
        gia_tri_moi={"san_pham_id": tt.san_pham_id, "phien_ban": tt.phien_ban, "trang_thai": "da_duyet"},
        ip=ip,
    )
    return (await _doc_cac_phien_ban(db, [tt]))[0]


async def luu_tru_ban_nhap(db: AsyncSession, actor: NhanVien, phien_ban_id: int, *, ip: str) -> PhienBanNoiDung:
    """Bỏ một bản nháp (sang `luu_tru`). Không động tới bản đã duyệt: gỡ nội dung đang hiển thị là việc khác."""
    await dam_bao_la_duoc_si(db, actor)
    tt = await _khoa_phien_ban(db, phien_ban_id)
    if tt.trang_thai != TrangThaiNoiDung.nhap:
        raise _xung_dot("Chỉ lưu trữ được bản nháp; phiên bản này đã được duyệt hoặc đã lưu trữ")
    tt.trang_thai = TrangThaiNoiDung.luu_tru
    await db.flush()
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="sua",
        bang=BANG,
        ban_ghi_id=tt.id,
        gia_tri_cu={"san_pham_id": tt.san_pham_id, "phien_ban": tt.phien_ban, "trang_thai": "nhap"},
        gia_tri_moi={"san_pham_id": tt.san_pham_id, "phien_ban": tt.phien_ban, "trang_thai": "luu_tru"},
        ip=ip,
    )
    return (await _doc_cac_phien_ban(db, [tt]))[0]


async def danh_sach(
    db: AsyncSession, *, q: str | None, loc: str | None, tp: ThamSoPhanTrang
) -> tuple[Sequence[DongNoiDung], int]:
    """Sản phẩm chưa xóa kèm tình trạng nội dung. `loc`: `cho_duyet`, `da_duyet`, `chua_co_noi_dung`."""
    duyet_ = aliased(ThongTinChuyenMon)
    nhap_moi_nhat = (
        select(ThongTinChuyenMon.san_pham_id, func.max(ThongTinChuyenMon.phien_ban).label("so"))
        .where(ThongTinChuyenMon.trang_thai == TrangThaiNoiDung.nhap)
        .group_by(ThongTinChuyenMon.san_pham_id)
        .subquery()
    )
    stmt: Select[Any] = (
        select(SanPham, duyet_.phien_ban, duyet_.ngay_duyet, nhap_moi_nhat.c.so)
        .outerjoin(duyet_, and_(duyet_.san_pham_id == SanPham.id, duyet_.trang_thai == TrangThaiNoiDung.da_duyet))
        .outerjoin(nhap_moi_nhat, nhap_moi_nhat.c.san_pham_id == SanPham.id)
        .where(SanPham.deleted_at.is_(None))
    )
    cho_duyet = and_(
        nhap_moi_nhat.c.so.is_not(None), or_(duyet_.phien_ban.is_(None), nhap_moi_nhat.c.so > duyet_.phien_ban)
    )
    if loc == "cho_duyet":
        stmt = stmt.where(cho_duyet)
    elif loc == "da_duyet":
        stmt = stmt.where(duyet_.phien_ban.is_not(None))
    elif loc == "chua_co_noi_dung":
        stmt = stmt.where(duyet_.phien_ban.is_(None))
    if q and q.strip():
        mau = mau_tim_like(q)
        stmt = stmt.where(
            or_(
                func.f_unaccent(func.lower(SanPham.ten)).like(func.f_unaccent(func.lower(mau)), escape="\\"),
                func.upper(SanPham.sku).like(func.upper(mau), escape="\\"),
            )
        )
    stmt = stmt.order_by(func.lower(SanPham.ten), SanPham.id)
    dong, tong = await lay_trang(db, stmt, tp, nhieu_cot=True)
    return [
        DongNoiDung(
            san_pham_id=sp.id,
            sku=sp.sku,
            ten=sp.ten,
            loai_san_pham=sp.loai_san_pham,
            phien_ban_da_duyet=so_duyet,
            ngay_duyet=ngay_duyet,
            phien_ban_nhap_moi_nhat=so_nhap,
            cho_duyet=so_nhap is not None and (so_duyet is None or so_nhap > so_duyet),
        )
        for sp, so_duyet, ngay_duyet, so_nhap in dong
    ], tong

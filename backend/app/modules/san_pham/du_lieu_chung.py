"""Dữ liệu dùng chung của Admin (AD05): thương hiệu, nhà sản xuất, hoạt chất.

Ba nhóm cùng một khuôn, khác nhau ở bảng, khóa trùng và cách đếm sản phẩm (`Nhom`):
- Trùng tên không phân biệt hoa thường và dấu (DB chỉ cấm trùng đúng từng ký tự, và với nhà sản xuất bỏ qua `quoc_gia`
  NULL), nên service kiểm tra và tuần tự hóa tạo/đổi tên bằng một khóa tư vấn riêng của nhóm: hai request cùng tạo
  "Sanofi" và "SANOFI" không lọt cả hai.
- Xóa là xóa cứng, dựa vào khóa ngoại: còn được tham chiếu (sản phẩm, thành phần, tương tác, dị ứng) thì DB từ chối và
  service trả `DU_LIEU_DANG_DUOC_SU_DUNG` với thông điệp chung. Không đếm trước rồi xóa vì như vậy có khe hở với giao
  dịch đang thêm tham chiếu; cũng không cho biết bản ghi nào đang dùng nó, vì hoạt chất có thể nằm trong dị ứng của
  khách (dữ liệu sức khỏe mà Admin không được đọc, CLAUDE.md quy tắc 7).
- Ghi đòi `master_data.manage` mức đầy đủ (ở router); quyền này không chỉ-ADMIN nên không có chốt thêm theo vai trò.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from sqlalchemy import ColumnElement, delete, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_trang import ThamSoPhanTrang, lay_trang, sap_xep_theo
from app.core.tim_kiem import mau_tim_like
from app.models.he_thong import NhanVien
from app.models.san_pham import HoatChat, NhaSanXuat, SanPham, ThanhPhan, ThuongHieu

MA_VI_PHAM_KHOA_NGOAI = "23503"


def _khong_dau(cot: Any) -> ColumnElement[Any]:
    return func.f_unaccent(func.lower(cot))


@dataclass(frozen=True)
class Nhom:
    bang: str
    mo_hinh: Any
    nhan: str
    """Cụm danh từ trong thông điệp, ví dụ "thương hiệu"."""
    truong: tuple[str, ...]
    """Các trường nhập được (ghi nhật ký), không gồm `id`, `created_at`."""
    cot_tim: tuple[str, ...]
    dem_san_pham: Callable[[], ColumnElement[Any]]
    """Biểu thức đếm (truy vấn con tương quan) số sản phẩm gắn với bản ghi."""
    khoa_trung: tuple[str, ...] = ("ten",)
    """Các trường tạo nên khóa trùng (không phân biệt hoa thường và dấu; trống cũng là một giá trị)."""


def _dem_theo(cot_tham_chieu: Any, mo_hinh: Any) -> Callable[[], ColumnElement[Any]]:
    return lambda: select(func.count()).where(cot_tham_chieu == mo_hinh.id).correlate(mo_hinh).scalar_subquery()


THUONG_HIEU = Nhom(
    "thuong_hieu",
    ThuongHieu,
    "thương hiệu",
    ("ten", "logo_url"),
    ("ten",),
    _dem_theo(SanPham.thuong_hieu_id, ThuongHieu),
)
NHA_SAN_XUAT = Nhom(
    "nha_san_xuat",
    NhaSanXuat,
    "nhà sản xuất",
    ("ten", "quoc_gia"),
    ("ten",),
    _dem_theo(SanPham.nha_san_xuat_id, NhaSanXuat),
    khoa_trung=("ten", "quoc_gia"),
)
HOAT_CHAT = Nhom(
    "hoat_chat",
    HoatChat,
    "hoạt chất",
    ("ten", "ten_khac", "mo_ta"),
    ("ten", "ten_khac"),
    _dem_theo(ThanhPhan.hoat_chat_id, HoatChat),
)


def _khong_tim_thay(nhom: Nhom) -> LoiNghiepVu:
    return LoiNghiepVu("KHONG_TIM_THAY", f"Không tìm thấy {nhom.nhan}")


def _trung(nhom: Nhom) -> LoiNghiepVu:
    them = " và quốc gia" if "quoc_gia" in nhom.khoa_trung else ""
    return LoiNghiepVu("TRUNG_DU_LIEU", f"Đã có {nhom.nhan} cùng tên{them}", chi_tiet={"truong": "ten"})


def _doi_sang_doc(doc: type[BaseModel], dong: Any) -> Any:
    truong = {ten: getattr(dong[0], ten) for ten in doc.model_fields if ten != "so_san_pham"}
    return doc(**truong, so_san_pham=dong[1])


def _truy_van(nhom: Nhom):
    return select(nhom.mo_hinh, nhom.dem_san_pham().label("so_san_pham"))


# --- Đọc -------------------------------------------------------------------------------------------------------------


async def danh_sach(
    db: AsyncSession, nhom: Nhom, doc: type[BaseModel], *, q: str | None, sap_xep: str | None, tp: ThamSoPhanTrang
) -> tuple[Sequence[Any], int]:
    """Mặc định theo tên. `q` tìm không phân biệt dấu và hoa thường theo tên (hoạt chất: cả tên khác)."""
    mh = nhom.mo_hinh
    stmt = _truy_van(nhom)
    if q and q.strip():
        mau = _khong_dau(mau_tim_like(q))
        stmt = stmt.where(or_(*[_khong_dau(getattr(mh, cot)).like(mau, escape="\\") for cot in nhom.cot_tim]))
    truong_sap_xep = {"ten": _khong_dau(mh.ten), "created_at": mh.created_at, "so_san_pham": nhom.dem_san_pham()}
    stmt = sap_xep_theo(stmt, sap_xep, truong_sap_xep, mac_dinh="ten", khoa_phu=mh.id)
    dong, tong = await lay_trang(db, stmt, tp, nhieu_cot=True)
    return [_doi_sang_doc(doc, d) for d in dong], tong


async def lay_mot(db: AsyncSession, nhom: Nhom, doc: type[BaseModel], ban_ghi_id: int) -> Any:
    dong = (await db.execute(_truy_van(nhom).where(nhom.mo_hinh.id == ban_ghi_id))).first()
    if dong is None:
        raise _khong_tim_thay(nhom)
    return _doi_sang_doc(doc, dong)


# --- Ghi -------------------------------------------------------------------------------------------------------------


async def _khoa_nhom(db: AsyncSession, nhom: Nhom) -> None:
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:khoa))"), {"khoa": f"nha_thuoc.{nhom.bang}.ten"})


async def _bi_trung(db: AsyncSession, nhom: Nhom, gia_tri: dict[str, Any], *, tru_id: int | None = None) -> bool:
    mh = nhom.mo_hinh
    dieu_kien = []
    for ten in nhom.khoa_trung:
        cot, v = getattr(mh, ten), gia_tri[ten]
        dieu_kien.append(cot.is_(None) if v is None else _khong_dau(cot) == _khong_dau(v))
    stmt = select(mh.id).where(*dieu_kien)
    if tru_id is not None:
        stmt = stmt.where(mh.id != tru_id)
    return (await db.execute(stmt.limit(1))).first() is not None


def _ghi_duoc(nhom: Nhom, du_lieu: BaseModel) -> dict[str, Any]:
    """Các trường người dùng đã gửi (PATCH: chỉ trường có mặt; POST: mọi trường, trường vắng lấy mặc định)."""
    return {ten: getattr(du_lieu, ten) for ten in nhom.truong if ten in du_lieu.model_fields_set}


async def tao(
    db: AsyncSession, actor: NhanVien, nhom: Nhom, doc: type[BaseModel], du_lieu: BaseModel, *, ip: str
) -> Any:
    gia_tri = {ten: getattr(du_lieu, ten) for ten in nhom.truong}
    await _khoa_nhom(db, nhom)
    if await _bi_trung(db, nhom, gia_tri):
        raise _trung(nhom)
    dong = nhom.mo_hinh(**gia_tri)
    db.add(dong)
    await db.flush()
    await ghi_nhat_ky(
        db, nhan_vien_id=actor.id, hanh_dong="tao", bang=nhom.bang, ban_ghi_id=dong.id, gia_tri_moi=gia_tri, ip=ip
    )
    return await lay_mot(db, nhom, doc, dong.id)


async def sua(
    db: AsyncSession, actor: NhanVien, nhom: Nhom, doc: type[BaseModel], ban_ghi_id: int, du_lieu: BaseModel, *, ip: str
) -> Any:
    """Chỉ đổi các trường gửi lên; không có gì đổi thì không ghi nhật ký."""
    await _khoa_nhom(db, nhom)
    dong = (
        await db.execute(
            select(nhom.mo_hinh)
            .where(nhom.mo_hinh.id == ban_ghi_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if dong is None:
        raise _khong_tim_thay(nhom)
    gui = _ghi_duoc(nhom, du_lieu)
    cu = {ten: getattr(dong, ten) for ten, v in gui.items() if getattr(dong, ten) != v}
    moi = {ten: v for ten, v in gui.items() if ten in cu}
    if not moi:
        return await lay_mot(db, nhom, doc, ban_ghi_id)
    sau = {ten: getattr(dong, ten) for ten in nhom.khoa_trung} | moi
    if any(ten in moi for ten in nhom.khoa_trung) and await _bi_trung(db, nhom, sau, tru_id=dong.id):
        raise _trung(nhom)
    for ten, v in moi.items():
        setattr(dong, ten, v)
    await db.flush()
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="sua",
        bang=nhom.bang,
        ban_ghi_id=dong.id,
        gia_tri_cu=cu,
        gia_tri_moi=moi,
        ip=ip,
    )
    return await lay_mot(db, nhom, doc, ban_ghi_id)


async def xoa(db: AsyncSession, actor: NhanVien, nhom: Nhom, ban_ghi_id: int, *, ip: str) -> None:
    """Xóa cứng bản ghi chưa ai tham chiếu; ngược lại `DU_LIEU_DANG_DUOC_SU_DUNG` (thông điệp chung, xem docstring)."""
    mh = nhom.mo_hinh
    cu = (await db.execute(select(mh).where(mh.id == ban_ghi_id))).scalar_one_or_none()
    if cu is None:
        raise _khong_tim_thay(nhom)
    gia_tri_cu = {ten: getattr(cu, ten) for ten in nhom.truong}
    try:
        async with db.begin_nested():  # savepoint: vi phạm khóa ngoại không làm hỏng transaction của request
            ket_qua = await db.execute(delete(mh).where(mh.id == ban_ghi_id))
    except IntegrityError as loi:
        if getattr(loi.orig, "sqlstate", None) != MA_VI_PHAM_KHOA_NGOAI:
            raise
        raise LoiNghiepVu(
            "DU_LIEU_DANG_DUOC_SU_DUNG", f"Không xóa được vì {nhom.nhan} này đang được sử dụng trong hệ thống"
        ) from loi
    if ket_qua.rowcount == 0:  # đã bị xóa bởi request khác ngay trước đó
        raise _khong_tim_thay(nhom)
    await ghi_nhat_ky(
        db, nhan_vien_id=actor.id, hanh_dong="xoa", bang=nhom.bang, ban_ghi_id=ban_ghi_id, gia_tri_cu=gia_tri_cu, ip=ip
    )

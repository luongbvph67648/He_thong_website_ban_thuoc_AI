"""Dữ liệu tương tác giữa các hoạt chất (DS10): CRUD do dược sĩ biên soạn (spec 06 mục 3.12, QĐ-18).

Mỗi cặp lưu MỘT lần theo thứ tự id tăng dần (CHECK `hoat_chat_a_id < hoat_chat_b_id` ở DB), nên client gửi cặp theo thứ
tự nào cũng được và server tự chuẩn hóa. Dùng lại ở DS04, DS05, DS07, DS08 và lọc gợi ý AI qua
`canh_bao.kiem_tra_tuong_tac`.
"""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.cau_hinh_khoa import dau_van_tay
from app.core.loi import LoiNghiepVu
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_quyen import dam_bao_la_duoc_si
from app.core.phan_trang import ThamSoPhanTrang, lay_trang
from app.core.thoi_gian import bay_gio_utc
from app.core.tim_kiem import mau_tim_like
from app.models.enums import MucDoTuongTac
from app.models.he_thong import NhanVien
from app.models.san_pham import HoatChat, TuongTacHoatChat
from app.modules.chuyen_mon.schemas_tuong_tac import TuongTacDoc, TuongTacSua, TuongTacTao

BANG = "tuong_tac_hoat_chat"
MA_VI_PHAM_UNIQUE = "23505"

MUC_DO_NANG_DAN = {
    MucDoTuongTac.chong_chi_dinh: 4,
    MucDoTuongTac.nghiem_trong: 3,
    MucDoTuongTac.trung_binh: 2,
    MucDoTuongTac.nhe: 1,
}
"""Thứ tự nặng của mức độ (cho sắp xếp cảnh báo, nặng nhất trước)."""


def cap_chuan(hoat_chat_1_id: int, hoat_chat_2_id: int) -> tuple[int, int]:
    """Cặp theo thứ tự id tăng dần (cách lưu trong bảng)."""
    return (min(hoat_chat_1_id, hoat_chat_2_id), max(hoat_chat_1_id, hoat_chat_2_id))


def _khong_tim_thay() -> LoiNghiepVu:
    return LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy tương tác giữa hai hoạt chất này")


def _loi_truong(truong: str, loi: str) -> LoiNghiepVu:
    return LoiNghiepVu("DU_LIEU_KHONG_HOP_LE", "Dữ liệu không hợp lệ", chi_tiet=[{"truong": truong, "loi": loi}])


def _noi_dung(tt: TuongTacHoatChat) -> dict[str, Any]:
    return {
        "muc_do": tt.muc_do.value,
        "co_che": tt.co_che,
        "khuyen_cao": tt.khuyen_cao,
        "nguon_tham_khao": tt.nguon_tham_khao,
    }


def _doc(tt: TuongTacHoatChat, ten_a: str, ten_b: str, nguoi: str | None) -> TuongTacDoc:
    return TuongTacDoc(
        hoat_chat_a_id=tt.hoat_chat_a_id,
        ten_hoat_chat_a=ten_a,
        hoat_chat_b_id=tt.hoat_chat_b_id,
        ten_hoat_chat_b=ten_b,
        nguoi_cap_nhat=nguoi,
        updated_at=tt.updated_at,
        phien_ban=dau_van_tay(_noi_dung(tt)),
        **_noi_dung(tt),
    )


async def _doc_mot(db: AsyncSession, tt: TuongTacHoatChat) -> TuongTacDoc:
    await db.refresh(tt)
    ten_a = await db.scalar(select(HoatChat.ten).where(HoatChat.id == tt.hoat_chat_a_id))
    ten_b = await db.scalar(select(HoatChat.ten).where(HoatChat.id == tt.hoat_chat_b_id))
    nguoi = (
        await db.scalar(select(NhanVien.ho_ten).where(NhanVien.id == tt.nhan_vien_cap_nhat_id))
        if tt.nhan_vien_cap_nhat_id
        else None
    )
    return _doc(tt, ten_a or "", ten_b or "", nguoi)


async def danh_sach(
    db: AsyncSession, *, q: str | None, muc_do: MucDoTuongTac | None, tp: ThamSoPhanTrang
) -> tuple[Sequence[TuongTacDoc], int]:
    """Mọi cặp, nặng nhất trước. `q` tìm tên một trong hai hoạt chất (không phân biệt hoa thường và dấu)."""
    a, b = aliased(HoatChat), aliased(HoatChat)
    stmt: Select[Any] = (
        select(TuongTacHoatChat, a.ten, b.ten, NhanVien.ho_ten)
        .join(a, a.id == TuongTacHoatChat.hoat_chat_a_id)
        .join(b, b.id == TuongTacHoatChat.hoat_chat_b_id)
        .outerjoin(NhanVien, NhanVien.id == TuongTacHoatChat.nhan_vien_cap_nhat_id)
    )
    if muc_do is not None:
        stmt = stmt.where(TuongTacHoatChat.muc_do == muc_do)
    if q and q.strip():
        mau = func.f_unaccent(func.lower(mau_tim_like(q)))
        stmt = stmt.where(
            or_(
                func.f_unaccent(func.lower(a.ten)).like(mau, escape="\\"),
                func.f_unaccent(func.lower(b.ten)).like(mau, escape="\\"),
            )
        )
    nang = case(*[(TuongTacHoatChat.muc_do == k, v) for k, v in MUC_DO_NANG_DAN.items()], else_=0)
    stmt = stmt.order_by(
        nang.desc(),
        func.lower(a.ten),
        func.lower(b.ten),
        TuongTacHoatChat.hoat_chat_a_id,
        TuongTacHoatChat.hoat_chat_b_id,
    )
    dong, tong = await lay_trang(db, stmt, tp, nhieu_cot=True)
    return [_doc(tt, ten_a, ten_b, nguoi) for tt, ten_a, ten_b, nguoi in dong], tong


async def _tim(db: AsyncSession, a_id: int, b_id: int, *, khoa: bool = False) -> TuongTacHoatChat:
    a_id, b_id = cap_chuan(a_id, b_id)
    stmt = select(TuongTacHoatChat).where(
        TuongTacHoatChat.hoat_chat_a_id == a_id, TuongTacHoatChat.hoat_chat_b_id == b_id
    )
    if khoa:
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    tt = (await db.execute(stmt)).scalar_one_or_none()
    if tt is None:
        raise _khong_tim_thay()
    return tt


async def lay(db: AsyncSession, hoat_chat_1_id: int, hoat_chat_2_id: int) -> TuongTacDoc:
    return await _doc_mot(db, await _tim(db, hoat_chat_1_id, hoat_chat_2_id))


async def tao(db: AsyncSession, actor: NhanVien, du_lieu: TuongTacTao, *, ip: str) -> TuongTacDoc:
    await dam_bao_la_duoc_si(db, actor)
    if du_lieu.hoat_chat_1_id == du_lieu.hoat_chat_2_id:
        raise _loi_truong("hoat_chat_2_id", "Hai hoạt chất của một tương tác phải khác nhau")
    a_id, b_id = cap_chuan(du_lieu.hoat_chat_1_id, du_lieu.hoat_chat_2_id)
    co = set((await db.execute(select(HoatChat.id).where(HoatChat.id.in_((a_id, b_id))))).scalars())
    for truong, hc_id in (("hoat_chat_1_id", du_lieu.hoat_chat_1_id), ("hoat_chat_2_id", du_lieu.hoat_chat_2_id)):
        if hc_id not in co:
            raise _loi_truong(truong, "Hoạt chất không tồn tại")
    tt = TuongTacHoatChat(
        hoat_chat_a_id=a_id,
        hoat_chat_b_id=b_id,
        muc_do=du_lieu.muc_do,
        co_che=du_lieu.co_che,
        khuyen_cao=du_lieu.khuyen_cao,
        nguon_tham_khao=du_lieu.nguon_tham_khao,
        nhan_vien_cap_nhat_id=actor.id,
        updated_at=bay_gio_utc(),
    )
    try:
        async with db.begin_nested():  # hai dược sĩ cùng thêm một cặp: bên thua nhận 409 chứ không phải 500
            db.add(tt)
            await db.flush()
    except IntegrityError as loi:
        if getattr(loi.orig, "sqlstate", None) != MA_VI_PHAM_UNIQUE:
            raise
        raise LoiNghiepVu("TRUNG_DU_LIEU", "Đã có tương tác cho cặp hoạt chất này, hãy sửa bản ghi đó") from loi
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="tao",
        bang=BANG,
        ban_ghi_id=f"{a_id}-{b_id}",
        gia_tri_moi=_noi_dung(tt),
        ip=ip,
    )
    return await _doc_mot(db, tt)


async def sua(
    db: AsyncSession, actor: NhanVien, hoat_chat_1_id: int, hoat_chat_2_id: int, du_lieu: TuongTacSua, *, ip: str
) -> TuongTacDoc:
    await dam_bao_la_duoc_si(db, actor)
    tt = await _tim(db, hoat_chat_1_id, hoat_chat_2_id, khoa=True)
    if dau_van_tay(_noi_dung(tt)) != du_lieu.phien_ban:
        raise LoiNghiepVu(
            "DU_LIEU_DA_THAY_DOI",
            "Tương tác này vừa được người khác thay đổi. Hãy tải lại rồi sửa tiếp.",
            chi_tiet={"phien_ban_hien_tai": dau_van_tay(_noi_dung(tt))},
        )
    cu = _noi_dung(tt)
    tt.muc_do = du_lieu.muc_do
    tt.co_che = du_lieu.co_che
    tt.khuyen_cao = du_lieu.khuyen_cao
    tt.nguon_tham_khao = du_lieu.nguon_tham_khao
    if _noi_dung(tt) != cu:  # không đổi gì thì không ghi dấu vết
        tt.nhan_vien_cap_nhat_id = actor.id
        tt.updated_at = bay_gio_utc()
        await db.flush()
        await ghi_nhat_ky(
            db,
            nhan_vien_id=actor.id,
            hanh_dong="sua",
            bang=BANG,
            ban_ghi_id=f"{tt.hoat_chat_a_id}-{tt.hoat_chat_b_id}",
            gia_tri_cu=cu,
            gia_tri_moi=_noi_dung(tt),
            ip=ip,
        )
    return await _doc_mot(db, tt)


async def xoa(
    db: AsyncSession, actor: NhanVien, hoat_chat_1_id: int, hoat_chat_2_id: int, phien_ban: str, *, ip: str
) -> None:
    await dam_bao_la_duoc_si(db, actor)
    tt = await _tim(db, hoat_chat_1_id, hoat_chat_2_id, khoa=True)
    if dau_van_tay(_noi_dung(tt)) != phien_ban:
        raise LoiNghiepVu(
            "DU_LIEU_DA_THAY_DOI",
            "Tương tác này vừa được người khác thay đổi. Hãy tải lại rồi xóa nếu vẫn cần.",
            chi_tiet={"phien_ban_hien_tai": dau_van_tay(_noi_dung(tt))},
        )
    cu = _noi_dung(tt)
    a_id, b_id = tt.hoat_chat_a_id, tt.hoat_chat_b_id
    await db.delete(tt)
    await db.flush()
    await ghi_nhat_ky(
        db, nhan_vien_id=actor.id, hanh_dong="xoa", bang=BANG, ban_ghi_id=f"{a_id}-{b_id}", gia_tri_cu=cu, ip=ip
    )

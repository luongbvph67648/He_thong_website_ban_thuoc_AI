"""Thông báo trong ứng dụng (`thong_bao`). Hiện làm cho nhân viên (NV02); thông báo của khách (KTV13) thêm ở task sau.

Mọi truy vấn lọc theo chủ thông báo ngay trong SQL; thông báo của người khác trả 404 như không tồn tại.
"""

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.core.phan_trang import ThamSoPhanTrang, lay_trang
from app.models.khach_hang import ThongBao


def kiem_tra_lien_ket(lien_ket: str | None) -> None:
    """`lien_ket` là đường dẫn nội bộ của ứng dụng (`/nhan-vien/don-hang/12`); giao diện điều hướng tới đó nên không
    được là URL ngoài (chống chuyển người dùng sang trang lạ qua thông báo)."""
    if lien_ket is None:
        return
    if not lien_ket.startswith("/") or lien_ket.startswith("//") or "\\" in lien_ket:
        raise ValueError(f"lien_ket phải là đường dẫn nội bộ bắt đầu bằng một dấu /, nhận {lien_ket!r}")


async def gui_cho_nhan_vien(
    db: AsyncSession,
    nhan_vien_id: int,
    *,
    loai: str,
    tieu_de: str,
    noi_dung: str | None = None,
    lien_ket: str | None = None,
) -> ThongBao:
    """Tạo thông báo cho một nhân viên (đơn mới, chat chuyển tới, cảnh báo kho...). Không chứa dữ liệu sức khỏe."""
    kiem_tra_lien_ket(lien_ket)
    thong_bao = ThongBao(nhan_vien_id=nhan_vien_id, loai=loai, tieu_de=tieu_de, noi_dung=noi_dung, lien_ket=lien_ket)
    db.add(thong_bao)
    await db.flush()
    await db.refresh(thong_bao)  # lấy created_at, da_doc do DB sinh
    return thong_bao


async def danh_sach_cua_nhan_vien(db: AsyncSession, nhan_vien_id: int, *, da_doc: bool | None, tp: ThamSoPhanTrang):
    """Thông báo của nhân viên, mới nhất trước. `da_doc = None` là tất cả."""
    stmt = select(ThongBao).where(ThongBao.nhan_vien_id == nhan_vien_id)
    if da_doc is not None:
        stmt = stmt.where(ThongBao.da_doc.is_(da_doc))
    return await lay_trang(db, stmt.order_by(ThongBao.created_at.desc(), ThongBao.id.desc()), tp)


async def so_chua_doc(db: AsyncSession, nhan_vien_id: int) -> int:
    dem = await db.scalar(
        select(func.count())
        .select_from(ThongBao)
        .where(ThongBao.nhan_vien_id == nhan_vien_id, ThongBao.da_doc.is_(False))
    )
    return dem or 0


async def danh_dau_da_doc(db: AsyncSession, nhan_vien_id: int, thong_bao_id: int) -> ThongBao:
    """Đánh dấu đã đọc (gọi lại vẫn thành công). Thông báo không phải của mình thì 404."""
    thong_bao = (
        await db.execute(
            select(ThongBao).where(ThongBao.id == thong_bao_id, ThongBao.nhan_vien_id == nhan_vien_id).with_for_update()
        )
    ).scalar_one_or_none()
    if thong_bao is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy thông báo")
    thong_bao.da_doc = True
    return thong_bao


async def danh_dau_tat_ca_da_doc(db: AsyncSession, nhan_vien_id: int) -> int:
    """Đánh dấu mọi thông báo chưa đọc của nhân viên; trả số thông báo vừa đổi."""
    ket_qua = await db.execute(
        update(ThongBao).where(ThongBao.nhan_vien_id == nhan_vien_id, ThongBao.da_doc.is_(False)).values(da_doc=True)
    )
    return ket_qua.rowcount

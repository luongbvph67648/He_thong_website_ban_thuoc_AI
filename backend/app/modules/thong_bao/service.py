"""Thông báo trong ứng dụng (`thong_bao`). Hiện làm cho nhân viên (NV02); thông báo của khách (KTV13) thêm ở task sau.

Mọi truy vấn lọc theo chủ thông báo ngay trong SQL; thông báo của người khác trả 404 như không tồn tại.
"""

import html
import logging

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.loi import LoiNghiepVu
from app.core.phan_trang import ThamSoPhanTrang, lay_trang
from app.core.slug import bo_dau
from app.models.khach_hang import KhachHang, ThongBao
from app.tich_hop.tin_nhan import lay_kenh_tin_nhan

logger = logging.getLogger(__name__)

KENH_THEO_LOAI: dict[str, tuple[bool, bool]] = {
    # loại thông báo -> (gửi SMS, gửi email); loại khác chỉ hiện trong ứng dụng
    "don_hang": (False, True),
    "don_thuoc": (True, True),
    "doi_tra": (False, True),
    "hoan_tien": (False, True),
    "thu_hoi": (True, True),
    "nhac_mua_lai": (False, True),
}


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


async def gui_cho_khach(
    db: AsyncSession,
    khach_hang_id: int,
    *,
    loai: str,
    tieu_de: str,
    noi_dung: str | None = None,
    lien_ket: str | None = None,
) -> ThongBao:
    """Tạo thông báo trong ứng dụng cho khách rồi gửi thêm SMS/email theo `KENH_THEO_LOAI` (KTV13, HT07). Gửi ngoài
    là cố gắng hết sức: lỗi nhà cung cấp chỉ ghi log, không làm hỏng nghiệp vụ. Không chứa dữ liệu sức khỏe."""
    kiem_tra_lien_ket(lien_ket)
    thong_bao = ThongBao(khach_hang_id=khach_hang_id, loai=loai, tieu_de=tieu_de, noi_dung=noi_dung, lien_ket=lien_ket)
    db.add(thong_bao)
    await db.flush()
    sms, email = KENH_THEO_LOAI.get(loai, (False, False))
    if sms or email:
        khach = await db.get(KhachHang, khach_hang_id)
        if khach is not None:
            await _gui_ngoai(khach, sms, email, tieu_de, noi_dung, lien_ket)
    return thong_bao


async def _gui_ngoai(
    khach: KhachHang, sms: bool, email: bool, tieu_de: str, noi_dung: str | None, lien_ket: str | None
) -> None:
    kenh = lay_kenh_tin_nhan()
    if sms and khach.so_dien_thoai:
        try:
            await kenh.gui_sms(khach.so_dien_thoai, f"Nha thuoc AI: {bo_dau(tieu_de)}"[:160])
        except Exception:  # noqa: BLE001
            logger.warning("Không gửi được SMS thông báo", exc_info=True)
    if email and khach.email:
        phan = [f"<p>{html.escape(tieu_de)}</p>"]
        if noi_dung:
            phan.append(f"<p>{html.escape(noi_dung)}</p>")
        if lien_ket:
            phan.append(
                f'<p><a href="{html.escape(settings.FRONTEND_URL.rstrip("/") + lien_ket)}">Xem chi tiết</a></p>'
            )
        try:
            await kenh.gui_email(khach.email, tieu_de, "".join(phan))
        except Exception:  # noqa: BLE001
            logger.warning("Không gửi được email thông báo", exc_info=True)


# --- Thông báo của khách (KTV13): khach_hang_id luôn lấy từ token ---


async def danh_sach_cua_khach(db: AsyncSession, khach_hang_id: int, *, da_doc: bool | None, tp: ThamSoPhanTrang):
    stmt = select(ThongBao).where(ThongBao.khach_hang_id == khach_hang_id)
    if da_doc is not None:
        stmt = stmt.where(ThongBao.da_doc.is_(da_doc))
    return await lay_trang(db, stmt.order_by(ThongBao.created_at.desc(), ThongBao.id.desc()), tp)


async def so_chua_doc_cua_khach(db: AsyncSession, khach_hang_id: int) -> int:
    return (
        await db.scalar(
            select(func.count())
            .select_from(ThongBao)
            .where(ThongBao.khach_hang_id == khach_hang_id, ThongBao.da_doc.is_(False))
        )
        or 0
    )


async def danh_dau_da_doc_cua_khach(db: AsyncSession, khach_hang_id: int, thong_bao_id: int) -> ThongBao:
    thong_bao = (
        await db.execute(
            select(ThongBao)
            .where(ThongBao.id == thong_bao_id, ThongBao.khach_hang_id == khach_hang_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if thong_bao is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy thông báo")
    thong_bao.da_doc = True
    return thong_bao


async def danh_dau_tat_ca_da_doc_cua_khach(db: AsyncSession, khach_hang_id: int) -> int:
    ket_qua = await db.execute(
        update(ThongBao).where(ThongBao.khach_hang_id == khach_hang_id, ThongBao.da_doc.is_(False)).values(da_doc=True)
    )
    return ket_qua.rowcount


async def gui_sms_khong_tai_khoan(so_dien_thoai: str, noi_dung: str) -> None:
    """SMS cho người nhận không có tài khoản (đơn vãng lai); cố gắng hết sức, lỗi chỉ ghi log."""
    try:
        await lay_kenh_tin_nhan().gui_sms(so_dien_thoai, noi_dung[:160])
    except Exception:  # noqa: BLE001
        logger.warning("Không gửi được SMS thông báo", exc_info=True)

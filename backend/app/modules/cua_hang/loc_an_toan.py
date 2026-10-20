"""Bộ lọc an toàn dùng chung cho mọi nơi gợi ý sản phẩm (chatbot, tương tự, dành cho bạn): lọc ở SQL, không ở prompt.

Sản phẩm gợi ý phải hiển thị với khách, không phải thuốc kê đơn (quy tắc 6) và không chứa hoạt chất khách dị ứng (chỉ
khi khách đã đồng ý dùng hồ sơ sức khỏe, quy tắc 7)."""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import TaiLieuTriThuc
from app.models.enums import LoaiSanPham
from app.models.khach_hang import DiUng, HoSoSucKhoe, KhachHang
from app.models.san_pham import SanPham, ThanhPhan
from app.modules.cua_hang.danh_sach import chon_the, dung_the
from app.modules.cua_hang.hien_thi import la_hien_thi, nap_cay_hien_thi
from app.modules.cua_hang.schemas import SanPhamThe


async def di_ung_cua_khach(db: AsyncSession, khach: KhachHang | None) -> list[int]:
    """Id hoạt chất khách dị ứng, CHỈ khi đã đồng ý dùng hồ sơ sức khỏe (spec 07 mục 1.4). Dùng để lọc ở SQL."""
    if khach is None:
        return []
    dong_y = await db.scalar(select(HoSoSucKhoe.dong_y_su_dung).where(HoSoSucKhoe.khach_hang_id == khach.id))
    if not dong_y:
        return []
    return list((await db.execute(select(DiUng.hoat_chat_id).where(DiUng.khach_hang_id == khach.id))).scalars())


def loc_di_ung(ids_hoat_chat: list[int]):
    """Điều kiện WHERE: sản phẩm KHÔNG chứa hoạt chất dị ứng."""
    return ~SanPham.id.in_(select(ThanhPhan.san_pham_id).where(ThanhPhan.hoat_chat_id.in_(ids_hoat_chat)))


async def the_hop_le(db: AsyncSession, ids: list[int], ids_di_ung: list[int]) -> list[SanPhamThe]:
    """Thẻ sản phẩm đã qua MỌI bộ lọc (hiển thị, không kê đơn, không dị ứng), giữ thứ tự `ids`. Dùng cho cả tool lẫn thẻ
    gửi khách: thẻ chỉ gồm id đã xuất hiện trong kết quả tool của lượt đó và vẫn phải qua bộ lọc này."""
    if not ids:
        return []
    cay = await nap_cay_hien_thi(db)
    dieu_kien = [la_hien_thi(cay.ids), SanPham.id.in_(ids), SanPham.loai_san_pham != LoaiSanPham.thuoc_ke_don]
    if ids_di_ung:
        dieu_kien.append(loc_di_ung(ids_di_ung))
    the = {t.id: t for t in await dung_the(db, (await db.execute(chon_the().where(*dieu_kien))).all())}
    return [the[i] for i in ids if i in the]


async def loc_tri_thuc_san_pham(db: AsyncSession):
    """Điều kiện WHERE cho `tai_lieu_tri_thuc`: đoạn của sản phẩm phải CÒN hợp lệ ngay lúc truy vấn.

    `metadata.can_ke_don` chỉ đúng tại lần đồng bộ gần nhất (HT AI07 chạy đêm): sản phẩm vừa đổi sang thuốc kê đơn,
    ngừng bán hay bị xóa trong ngày vẫn còn đoạn cũ, nên phải kiểm lại với bảng `san_pham` trong SQL (quy tắc 6).
    Đoạn không gắn sản phẩm (bài viết, hỏi đáp) không bị ràng buộc này."""
    cay = await nap_cay_hien_thi(db)
    hop_le = select(SanPham.id).where(la_hien_thi(cay.ids), SanPham.loai_san_pham != LoaiSanPham.thuoc_ke_don)
    return or_(TaiLieuTriThuc.san_pham_id.is_(None), TaiLieuTriThuc.san_pham_id.in_(hop_le))

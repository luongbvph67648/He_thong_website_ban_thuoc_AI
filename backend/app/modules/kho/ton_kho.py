"""Dịch vụ tồn kho: nơi DUY NHẤT được đổi `so_luong_ton`, `so_luong_giu`, `so_luong_biet_tru` (CLAUDE.md quy tắc 2).

Mọi hàm nhận `db` đang trong transaction, tự khóa các lô liên quan bằng `SELECT ... FOR UPDATE` theo id tăng dần rồi mới
tính toán, và ghi `bien_dong_kho` trong cùng transaction (spec 04 mục 3). Hiện mới có phần nhập kho; các hàm giữ hàng,
xuất, hoàn nhập, biệt trữ, trừ tồn, điều chỉnh thêm ở T3.1 và T4.x.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc
from app.models.enums import KhuTon, LoaiBienDong
from app.models.kho import BienDongKho, LoThuoc
from app.models.san_pham import SanPham


@dataclass(frozen=True)
class ChungTu:
    """Chứng từ gây ra biến động: `loai` là tên bảng (`phieu_nhap`, `don_hang`...). `nhan_vien_id` None = hệ thống."""

    loai: str
    id: int
    nhan_vien_id: int | None = None


async def khoa_cac_lo(db: AsyncSession, lo_ids: Iterable[int]) -> list[LoThuoc]:
    """Khóa các lô (FOR UPDATE) theo id tăng dần và trả về theo thứ tự đó.

    Thứ tự cố định giữa mọi giao dịch để hai giao dịch khóa chung nhiều lô không bao giờ chờ vòng tròn (deadlock).
    Các đối tượng đã nạp từ trước được làm mới theo dòng vừa khóa, nên số liệu tồn luôn là bản đã commit mới nhất.
    """
    ids = sorted(set(lo_ids))
    if not ids:
        return []
    truy_van = (
        select(LoThuoc)
        .where(LoThuoc.id.in_(ids))
        .order_by(LoThuoc.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    lo_thuoc = list((await db.execute(truy_van)).scalars())
    thieu = set(ids) - {lo.id for lo in lo_thuoc}
    if thieu:
        raise LookupError(f"Không tìm thấy lô: {sorted(thieu)}")
    return lo_thuoc


async def kiem_tra_san_pham_chua_xoa(db: AsyncSession, lo: LoThuoc) -> None:
    """Từ chối TĂNG tồn của lô thuộc sản phẩm đã xóa mềm. Gọi SAU khi đã khóa lô (`khoa_cac_lo`).

    Xóa sản phẩm khóa mọi lô của nó `FOR UPDATE` rồi mới kiểm tra "không còn hàng". Nhập kho đã khóa lô thì hoặc thắng
    (xóa chờ rồi thấy tồn > 0 và bị từ chối), hoặc chờ xóa commit rồi đọc được `deleted_at` ở đây và bị từ chối; không
    có đường thứ ba để tồn mắc kẹt dưới sản phẩm đã xóa. Mọi hàm tăng tồn từ 0 (nhập kho, hoàn nhập đổi trả, điều chỉnh
    tăng, ra khỏi biệt trữ) phải gọi hàm này; hàm chỉ giảm hay chuyển khu thì không cần vì lô đang có hàng chặn xóa.
    """
    da_xoa = await db.scalar(select(SanPham.deleted_at).where(SanPham.id == lo.san_pham_id))
    if da_xoa is not None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Sản phẩm của lô này đã bị xóa")


def _kiem_tra_so_luong(so_luong: int) -> None:
    if isinstance(so_luong, bool) or not isinstance(so_luong, int):
        raise TypeError(f"so_luong phải là số nguyên, nhận {type(so_luong).__name__}")
    if so_luong <= 0:
        raise ValueError("so_luong phải lớn hơn 0")


async def nhap_kho(
    db: AsyncSession, lo: LoThuoc, so_luong: int, chung_tu: ChungTu, luc: datetime | None = None
) -> BienDongKho:
    """Cộng `so_luong` (đơn vị cơ sở) vào tồn kho bán của lô và ghi thẻ kho `nhap_kho`.

    `luc`: thời điểm ghi thẻ kho, mặc định là bây giờ; chỉ truyền khi nhập lại dữ liệu cũ (seed, chuyển đổi) để thẻ
    kho mang ngày của chứng từ gốc, báo cáo nhập - xuất - tồn theo kỳ mới khớp.

    Hàm khóa MỘT lô. Phiếu nhập nhiều dòng phải gọi `khoa_cac_lo` với TẤT CẢ id lô trước (khóa theo id tăng dần) rồi mới
    gọi `nhap_kho` từng dòng, nếu không hai phiếu khóa các lô theo thứ tự ngược nhau có thể deadlock. Tính lại giá nhập
    bình quân gia quyền (KHO02) và kiểm tra trạng thái lô (khóa, thu hồi) thuộc dịch vụ phiếu nhập ở T3.1.
    """
    _kiem_tra_so_luong(so_luong)
    (lo_khoa,) = await khoa_cac_lo(db, [lo.id])
    await kiem_tra_san_pham_chua_xoa(db, lo_khoa)
    lo_khoa.so_luong_ton += so_luong
    lo_khoa.updated_at = bay_gio_utc()
    bien_dong = BienDongKho(
        lo_id=lo_khoa.id,
        loai=LoaiBienDong.nhap_kho,
        khu=KhuTon.kho_ban,
        so_luong=so_luong,
        ton_sau=lo_khoa.so_luong_ton,
        chung_tu_loai=chung_tu.loai,
        chung_tu_id=chung_tu.id,
        nhan_vien_id=chung_tu.nhan_vien_id,
        **({"created_at": luc} if luc is not None else {}),
    )
    db.add(bien_dong)
    await db.flush()
    return bien_dong

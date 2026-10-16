"""Thuật toán giảm giá thuần túy (spec 04 mục 4, bước 2, 4, 5): không đụng CSDL, chạy bằng Decimal, làm tròn đồng."""

from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal

from app.core.tien import lam_tron_vnd
from app.models.enums import LoaiGiamGia


@dataclass(frozen=True)
class DongTinh:
    """Một dòng giỏ/đơn. `hop_le` = không phải thuốc kê đơn VÀ thuộc phạm vi khuyến mãi."""

    khoa: int
    thanh_tien_goc: Decimal
    hop_le: bool


@dataclass(frozen=True)
class KetQuaGiam:
    co_so_giam: Decimal
    giam: Decimal
    phan_bo: dict[int, Decimal]
    """`khoa` dòng hợp lệ -> phần giảm; dòng không hợp lệ nhận 0. Tổng = `giam` đúng tuyệt đối."""


def tinh_giam(dong: list[DongTinh], loai: LoaiGiamGia, gia_tri: Decimal, giam_toi_da: Decimal | None) -> KetQuaGiam:
    """Số tiền giảm và phân bổ vào từng dòng. Gọi khi đã đạt điều kiện áp mã (đơn tối thiểu...)."""
    hop_le = [d for d in dong if d.hop_le]
    co_so = sum((d.thanh_tien_goc for d in hop_le), Decimal(0))
    if loai == LoaiGiamGia.phan_tram:
        giam = lam_tron_vnd(co_so * gia_tri / 100)
        if giam_toi_da is not None:
            giam = min(giam, giam_toi_da)
    else:
        giam = min(gia_tri, co_so)
    giam = min(giam, co_so)  # không bao giờ giảm quá phần được giảm (phòng dữ liệu cấu hình sai)
    phan_bo = {d.khoa: Decimal(0) for d in dong}
    if co_so > 0 and giam > 0:
        da_chia = Decimal(0)
        for d in hop_le[:-1]:
            phan = (giam * d.thanh_tien_goc / co_so).to_integral_value(rounding=ROUND_FLOOR)
            phan_bo[d.khoa] = phan
            da_chia += phan
        phan_bo[hop_le[-1].khoa] = giam - da_chia  # phần dư dồn vào dòng hợp lệ cuối
    return KetQuaGiam(co_so_giam=co_so, giam=giam, phan_bo=phan_bo)

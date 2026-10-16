"""Ánh xạ trạng thái của đối tác vận chuyển sang trạng thái đơn (spec 08 mục 5), thuần hàm để test.

Trạng thái đối tác theo bộ của GHN (`picked`, `delivered`...); bản giả dùng cùng bộ từ khóa.
"""

from collections import deque

from app.models.enums import TrangThaiDon

TT = TrangThaiDon

DANG_GIAO = frozenset({"picked", "storing", "transporting", "sorting", "delivering", "money_collect_delivering"})
GIAO_LAI = frozenset({"delivering", "money_collect_delivering"})
THAT_BAI = frozenset({"delivery_fail", "waiting_to_return"})
DA_GIAO = frozenset({"delivered"})
DA_HOAN = frozenset({"returned"})

# Các bước hệ thống được phép trên đường giao hàng (dòng 22 đến 26 của bảng chuyển trạng thái).
BUOC: dict[TT, tuple[TT, ...]] = {
    TT.cho_lay_hang: (TT.dang_giao,),
    TT.dang_giao: (TT.da_giao, TT.giao_that_bai),
    TT.giao_that_bai: (TT.dang_giao, TT.hoan_ve_kho),
}


def trang_thai_muc_tieu(trang_thai_doi_tac: str, hien_tai: TT) -> TT | None:
    """Trạng thái đơn mà sự kiện này hướng tới, hoặc `None` khi chỉ cần ghi nhận (hủy, trạng thái trung gian...)."""
    tt = trang_thai_doi_tac.strip().lower()
    if tt in DANG_GIAO:
        # Sau khi giao thất bại chỉ "đang giao lại" mới đưa đơn về đang giao; kho trung chuyển không phải giao lại.
        return TT.dang_giao if hien_tai != TT.giao_that_bai or tt in GIAO_LAI else None
    if tt in DA_GIAO:
        return TT.da_giao
    if tt in THAT_BAI:
        return TT.giao_that_bai
    if tt in DA_HOAN:
        return TT.hoan_ve_kho
    return None


def duong_di(hien_tai: TT, muc_tieu: TT) -> list[TT]:
    """Các trạng thái cần đi qua (không gồm `hien_tai`) để tới `muc_tieu`; rỗng nếu đã ở đó hoặc không có đường.

    Sự kiện đến muộn hoặc mất một sự kiện trước đó (đã giao mà chưa nhận "đã lấy hàng") vẫn đưa đơn tới đúng chỗ;
    sự kiện cũ so với trạng thái hiện tại (đã giao rồi mới nhận "đang giao") không có đường nên bị bỏ qua.
    """
    if hien_tai == muc_tieu:
        return []
    truoc: dict[TT, TT | None] = {hien_tai: None}
    hang = deque([hien_tai])
    while hang:
        cur = hang.popleft()
        for tiep in BUOC.get(cur, ()):
            if tiep in truoc:
                continue
            truoc[tiep] = cur
            if tiep == muc_tieu:
                lo_trinh = [tiep]
                while truoc[lo_trinh[-1]] != hien_tai:
                    lo_trinh.append(truoc[lo_trinh[-1]])  # type: ignore[arg-type]
                return lo_trinh[::-1]
            hang.append(tiep)
    return []

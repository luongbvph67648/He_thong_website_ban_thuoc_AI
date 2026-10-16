"""Quy tắc trạng thái lô theo hạn sử dụng (spec 04 mục 1.4), dùng chung cho phiếu nhập và job HT01."""

from datetime import date

from app.models.enums import TrangThaiLo


def trang_thai_theo_han(han_su_dung: date, hom_nay: date, nguong_can_han_ngay: int) -> TrangThaiLo:
    """Hết hạn khi không còn `HSD > hôm nay`, cận hạn khi còn dưới `nguong_can_han_ngay` ngày, còn lại đang bán.

    Chỉ áp cho lô đang bán/cận hạn: lô `khoa`, `thu_hoi` do Admin quyết định, không đổi theo hạn.
    """
    if han_su_dung <= hom_nay:
        return TrangThaiLo.het_han
    return TrangThaiLo.can_han if (han_su_dung - hom_nay).days < nguong_can_han_ngay else TrangThaiLo.dang_ban

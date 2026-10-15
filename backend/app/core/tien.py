"""Tiền (VND). Luôn dùng Decimal, cấm float. Làm tròn half-up về đồng (spec 02 mục 3, spec 04 mục 4)."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Annotated

from pydantic import BeforeValidator, PlainSerializer

_MOT = Decimal(1)


def _thanh_decimal(gia_tri: object) -> Decimal:
    """Chuẩn hóa int/str/Decimal thành Decimal hữu hạn. float và bool bị từ chối."""
    if isinstance(gia_tri, (bool, float)):
        raise TypeError("Tiền không được dùng float hoặc bool, hãy dùng Decimal, int hoặc str")
    if isinstance(gia_tri, Decimal):
        ket_qua = gia_tri
    elif isinstance(gia_tri, (int, str)):
        try:
            ket_qua = Decimal(gia_tri)
        except InvalidOperation:
            raise ValueError(f"Không phải số tiền hợp lệ: {gia_tri!r}") from None
    else:
        raise TypeError(f"Kiểu không hợp lệ cho tiền: {type(gia_tri).__name__}")
    if not ket_qua.is_finite():
        raise ValueError(f"Không phải số tiền hợp lệ: {gia_tri!r}")
    return ket_qua


def lam_tron_vnd(gia_tri: Decimal | int | str) -> Decimal:
    """Làm tròn về đồng nguyên theo half-up (2.5 -> 3, -2.5 -> -3), không làm tròn chẵn như ngân hàng."""
    return _thanh_decimal(gia_tri).quantize(_MOT, rounding=ROUND_HALF_UP)


def cong(*so_hang: Decimal | int | str) -> Decimal:
    """Cộng chính xác các số hạng rồi làm tròn một lần ở cuối. Cần làm tròn từng dòng thì gọi lam_tron_vnd trước."""
    return lam_tron_vnd(sum((_thanh_decimal(x) for x in so_hang), Decimal(0)))


def tru(a: Decimal | int | str, b: Decimal | int | str) -> Decimal:
    """a - b, làm tròn về đồng. Kết quả âm là hợp lệ."""
    return lam_tron_vnd(_thanh_decimal(a) - _thanh_decimal(b))


def _kiem_tra_tien(gia_tri: object) -> Decimal:
    """Validator đầu vào cho schema: chỉ nhận số đồng nguyên. JSON gửi 125000.0 vẫn hợp lệ, 125000.5 thì không."""
    if isinstance(gia_tri, float) and not isinstance(gia_tri, bool):
        gia_tri = Decimal(str(gia_tri))  # đi qua chuỗi để không dính sai số nhị phân của float
    try:
        so = _thanh_decimal(gia_tri)
    except TypeError as loi:
        raise ValueError(str(loi)) from None
    if so != so.to_integral_value():
        raise ValueError("Số tiền phải là số đồng nguyên")
    return lam_tron_vnd(so)


Tien = Annotated[
    Decimal,
    BeforeValidator(_kiem_tra_tien),
    PlainSerializer(lambda v: f"{v:.2f}", return_type=str, when_used="json"),
]
"""Kiểu tiền cho schema Pydantic: nhận số đồng nguyên, xuất JSON dạng chuỗi "125000.00" (spec 06 mục 1)."""

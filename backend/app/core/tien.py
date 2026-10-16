"""Tiền (VND). Luôn dùng Decimal, cấm float. Làm tròn half-up về đồng (spec 02 mục 3, spec 04 mục 4)."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Annotated

from pydantic import BeforeValidator, PlainSerializer

_MOT = Decimal(1)
TIEN_TOI_DA = 10**12
"""Giới hạn tuyệt đối của số tiền nhận từ bên ngoài: cột NUMERIC(14,2) chứa tối đa 12 chữ số nguyên."""


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
    try:
        ket_qua = _thanh_decimal(gia_tri).quantize(_MOT, rounding=ROUND_HALF_UP)
    except InvalidOperation:  # vượt quá độ chính xác của Decimal (28 chữ số)
        raise ValueError(f"Số tiền quá lớn: {gia_tri!r}") from None
    return ket_qua or Decimal(0)  # "-0" (từ -0.4 làm tròn) chuẩn hóa thành 0, tránh hiển thị "-0.00"


def cong(*so_hang: Decimal | int | str) -> Decimal:
    """Cộng chính xác các số hạng rồi làm tròn một lần ở cuối. Cần làm tròn từng dòng thì gọi lam_tron_vnd trước."""
    return lam_tron_vnd(sum((_thanh_decimal(x) for x in so_hang), Decimal(0)))


def tru(a: Decimal | int | str, b: Decimal | int | str) -> Decimal:
    """a - b, làm tròn về đồng. Kết quả âm là hợp lệ."""
    return lam_tron_vnd(_thanh_decimal(a) - _thanh_decimal(b))


def _kiem_tra_tien_co_dau(gia_tri: object) -> Decimal:
    """Validator đầu vào cho schema: chỉ nhận số đồng nguyên, trị tuyệt đối dưới TIEN_TOI_DA.

    JSON gửi 125000.0 vẫn hợp lệ, 125000.5 thì không. Mọi lỗi đều là ValueError để thành lỗi validate (400).
    """
    if isinstance(gia_tri, float) and not isinstance(gia_tri, bool):
        gia_tri = Decimal(str(gia_tri))  # đi qua chuỗi để không dính sai số nhị phân của float
    try:
        so = _thanh_decimal(gia_tri)
    except TypeError as loi:
        raise ValueError(str(loi)) from None
    if abs(so) >= TIEN_TOI_DA:
        raise ValueError("Số tiền vượt quá giới hạn cho phép")
    if so != so.to_integral_value():
        raise ValueError("Số tiền phải là số đồng nguyên")
    return lam_tron_vnd(so)


def _kiem_tra_tien_khong_am(gia_tri: object) -> Decimal:
    so = _kiem_tra_tien_co_dau(gia_tri)
    if so < 0:
        raise ValueError("Số tiền không được âm")
    return so


_XUAT_CHUOI = PlainSerializer(lambda v: f"{v:.2f}", return_type=str, when_used="json")

Tien = Annotated[Decimal, BeforeValidator(_kiem_tra_tien_khong_am), _XUAT_CHUOI]
"""Kiểu tiền KHÔNG ÂM cho schema Pydantic: nhận số đồng nguyên, xuất JSON dạng chuỗi "125000.00" (spec 06 mục 1)."""

TienCoDau = Annotated[Decimal, BeforeValidator(_kiem_tra_tien_co_dau), _XUAT_CHUOI]

TienDoc = Annotated[Decimal, _XUAT_CHUOI]
"""Kiểu tiền cho schema ĐỌC (phản hồi): chỉ định dạng xuất `"125000.00"`, KHÔNG kiểm tra lại. `Tien` là bộ kiểm đầu VÀO
(đồng nguyên, không âm); dùng nó ở phản hồi thì một dòng NUMERIC(14,2) có phần lẻ (nhập ngoài API) làm cả trang 500."""
"""Như Tien nhưng cho phép số âm, dùng cho chênh lệch/điều chỉnh."""

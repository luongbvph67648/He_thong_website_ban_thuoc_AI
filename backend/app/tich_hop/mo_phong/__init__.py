"""Máy chủ MÔ PHỎNG VNPay, MoMo và GHN (chế độ `mo_phong`): nói đúng giao thức của đối tác thật.

Khác cổng "giả" (`gia`, chữ ký riêng, một route chung), mô phỏng này dùng đúng URL, tham số, thuật toán ký, mã phản hồi
và định dạng IPN/webhook như tài liệu của đối tác. Adapter thật (`vnpay.py`, `momo.py`, `ghn.py`) chạy nguyên vẹn; đổi
sang sandbox/production chỉ là đổi địa chỉ và khóa trong `.env`. Chỉ phần "người dùng thao tác trên trang đối tác" là
giao diện mô phỏng của frontend. Không có tiền thật. Không dùng được ở production (`MOI_TRUONG=production` từ chối).
"""

from fastapi import FastAPI

_ung_dung_chinh: FastAPI | None = None


def dat_ung_dung_chinh(app: FastAPI) -> None:
    """`create_app()` đăng ký ứng dụng chính. Route mô phỏng nằm trong chính ứng dụng này; adapter gọi tới
    `mo-phong.local` và máy chủ mô phỏng gọi lại IPN/webhook đều đi qua ASGI vào đây (đối tác thật đi qua mạng)."""
    global _ung_dung_chinh
    _ung_dung_chinh = app


def ung_dung_chinh() -> FastAPI:
    if _ung_dung_chinh is None:
        raise RuntimeError("Ứng dụng chính chưa được đăng ký cho máy chủ mô phỏng")
    return _ung_dung_chinh

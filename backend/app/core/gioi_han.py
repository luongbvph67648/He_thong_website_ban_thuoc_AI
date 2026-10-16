"""Giới hạn tần suất cửa sổ trượt, giữ trong bộ nhớ của tiến trình (spec 01 mục 4).

Dùng cho khóa theo IP, phiên hay SĐT. Giới hạn (số lượt, độ dài cửa sổ) truyền vào mỗi lần gọi vì đọc từ `cau_hinh`
(Admin đổi được lúc chạy), nên không dùng slowapi vốn khai báo giới hạn tĩnh ở lúc import. Nhiều tiến trình/máy chủ
thì mỗi nơi đếm riêng; đủ cho quy mô một nhà thuốc, SĐT thì đã có bộ đếm chính xác trong DB (xem `otp.py`).
"""

import time
from collections import deque
from collections.abc import Callable


class GioiHanCuaSoTruot:
    def __init__(self, dong_ho: Callable[[], float] = time.monotonic, toi_da_khoa: int = 10_000) -> None:
        self._dong_ho = dong_ho
        self._toi_da_khoa = toi_da_khoa
        self._luot: dict[str, deque[float]] = {}

    def thu(self, khoa: str, toi_da: int, cua_so_giay: float) -> float | None:
        """Ghi một lượt cho `khoa`. Trả None nếu được phép; nếu đã đủ `toi_da` lượt trong `cua_so_giay` thì KHÔNG ghi và
        trả số giây phải chờ cho tới khi lượt cũ nhất hết hạn (dùng cho header `Retry-After`)."""
        if toi_da < 1 or cua_so_giay <= 0:
            raise ValueError("toi_da phải >= 1 và cua_so_giay phải > 0")
        bay_gio = self._dong_ho()
        luot = self._luot.setdefault(khoa, deque())
        while luot and bay_gio - luot[0] >= cua_so_giay:
            luot.popleft()
        if len(luot) >= toi_da:
            return max(0.0, cua_so_giay - (bay_gio - luot[-toi_da]))
        luot.append(bay_gio)
        self._don_dep(bay_gio, cua_so_giay)
        return None

    def _don_dep(self, bay_gio: float, cua_so_giay: float) -> None:
        if len(self._luot) <= self._toi_da_khoa:
            return
        for khoa in [k for k, d in self._luot.items() if not d or bay_gio - d[-1] >= cua_so_giay]:
            del self._luot[khoa]
        while len(self._luot) > self._toi_da_khoa:  # vẫn quá nhiều: bỏ khóa cũ nhất (thứ tự chèn của dict)
            del self._luot[next(iter(self._luot))]

    def so_khoa(self) -> int:
        return len(self._luot)

    def xoa(self) -> None:
        self._luot.clear()


_bo_otp_toan_cuc = GioiHanCuaSoTruot()
_bo_dang_nhap_toan_cuc = GioiHanCuaSoTruot()
_bo_lich_su_xem_toan_cuc = GioiHanCuaSoTruot()
_bo_tim_kiem_toan_cuc = GioiHanCuaSoTruot()
_bo_chat_toan_cuc = GioiHanCuaSoTruot()
_bo_goi_y_toan_cuc = GioiHanCuaSoTruot()
_bo_ma_giam_gia_toan_cuc = GioiHanCuaSoTruot()


def lay_bo_gioi_han_otp() -> GioiHanCuaSoTruot:
    """Bộ đếm theo IP cho việc xin OTP, dùng chung cả tiến trình. Là dependency để test thay bằng bộ riêng."""
    return _bo_otp_toan_cuc


def lay_bo_gioi_han_dang_nhap() -> GioiHanCuaSoTruot:
    """Bộ đếm theo IP cho các lần thử đăng nhập, làm chậm việc dò mật khẩu và dò tài khoản trên diện rộng."""
    return _bo_dang_nhap_toan_cuc


def lay_bo_gioi_han_lich_su_xem() -> GioiHanCuaSoTruot:
    """Bộ đếm theo IP cho việc GHI lịch sử xem sản phẩm (route công khai, mã phiên do client tự chọn)."""
    return _bo_lich_su_xem_toan_cuc


def lay_bo_gioi_han_tim_kiem() -> GioiHanCuaSoTruot:
    """Bộ đếm theo IP cho việc GHI lịch sử tìm kiếm (route công khai)."""
    return _bo_tim_kiem_toan_cuc


def lay_bo_gioi_han_goi_y() -> GioiHanCuaSoTruot:
    """Bộ đếm theo IP cho gợi ý khi gõ: route công khai và mỗi lượt là một truy vấn tìm kiếm."""
    return _bo_goi_y_toan_cuc


def lay_bo_gioi_han_ma_giam_gia() -> GioiHanCuaSoTruot:
    """Bộ đếm theo khách cho việc thử mã giảm giá (chống dò mã hàng loạt)."""
    return _bo_ma_giam_gia_toan_cuc


def lay_bo_gioi_han_chat() -> GioiHanCuaSoTruot:
    """Bộ đếm lượt chat AI theo IP và theo phiên (mỗi lượt tốn tiền token). Là dependency để test thay bằng bộ riêng."""
    return _bo_chat_toan_cuc

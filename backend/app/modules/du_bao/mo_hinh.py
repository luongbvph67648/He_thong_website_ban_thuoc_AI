"""AI09: mô hình dự báo nhu cầu theo tuần (spec 07 mục 7). Hàm thuần, không đụng CSDL nên test từng ca được.

Từ `SO_TUAN_HOLT_WINTERS` tuần dữ liệu trở lên dùng Holt-Winters (xu hướng cộng, không mùa vụ); ít hơn dùng trung bình
trượt có trọng số 4-3-2-1 của 4 tuần gần nhất. Holt-Winters lỗi hoặc ra giá trị vô lý thì quay về trung bình trượt."""

import math
import warnings
from collections.abc import Sequence

SO_TUAN_HOLT_WINTERS = 12
SO_TUAN_DANH_GIA = 4
SO_NGAY_DU_BAO = 30
SO_TUAN_DU_BAO = 5
"""30 ngày = 4 tuần đủ + 2/7 tuần thứ 5."""
MAPE_TOI_DA = 999.999
TRONG_SO = (1, 2, 3, 4)
"""Từ tuần cũ nhất đến mới nhất trong 4 tuần gần nhất."""

MO_HINH_TRUNG_BINH_TRUOT = "trung_binh_truot"
MO_HINH_HOLT_WINTERS = "holt_winters"


def trung_binh_truot(chuoi: Sequence[float], so_tuan: int) -> list[float]:
    """Trung bình trọng số 1-2-3-4 (cũ đến mới) của tối đa 4 tuần cuối; ít hơn 4 tuần thì tuần mới nhất vẫn nặng nhất.
    Giữ nguyên cho mọi tuần dự báo. Chuỗi rỗng thì 0."""
    if not chuoi:
        return [0.0] * so_tuan
    cuoi = list(chuoi[-4:])
    w = TRONG_SO[-len(cuoi) :]
    gia_tri = sum(x * t for x, t in zip(cuoi, w, strict=True)) / sum(w)
    return [gia_tri] * so_tuan


def _holt_winters(chuoi: Sequence[float], so_tuan: int) -> list[float] | None:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            kq = ExponentialSmoothing(list(chuoi), trend="add", seasonal=None, initialization_method="estimated").fit()
            du_bao = [float(x) for x in kq.forecast(so_tuan)]
    except Exception:  # noqa: BLE001 - thư viện có thể ném nhiều loại lỗi số học; luôn có dự phòng
        return None
    if any(not math.isfinite(x) for x in du_bao):
        return None
    return [max(0.0, x) for x in du_bao]


def du_bao_tuan(chuoi: Sequence[float], so_tuan: int = SO_TUAN_DU_BAO) -> tuple[list[float], str]:
    """(nhu cầu dự báo từng tuần tới, tên mô hình đã dùng)."""
    if len(chuoi) >= SO_TUAN_HOLT_WINTERS:
        hw = _holt_winters(chuoi, so_tuan)
        if hw is not None:
            return hw, MO_HINH_HOLT_WINTERS
    return trung_binh_truot(chuoi, so_tuan), MO_HINH_TRUNG_BINH_TRUOT


def tong_30_ngay(tuan: Sequence[float]) -> int:
    """Cộng 4 tuần đầu và 2/7 tuần thứ 5, làm tròn LÊN thành số nguyên (đơn vị cơ sở)."""
    tong = sum(tuan[:4]) + (SO_NGAY_DU_BAO - 28) / 7 * (tuan[4] if len(tuan) > 4 else 0.0)
    return math.ceil(round(tong, 9))


def mape_4_tuan(chuoi: Sequence[float]) -> float | None:
    """MAPE (%) khi dự báo lùi 1 tuần cho từng tuần trong 4 tuần cuối, mỗi lần chỉ dùng dữ liệu trước tuần đó.

    Bỏ qua tuần thực tế bằng 0 (không chia được); cần ít nhất một tuần huấn luyện trước 4 tuần đánh giá và ít nhất một
    tuần thực tế khác 0, nếu không trả `None`."""
    n = len(chuoi)
    if n <= SO_TUAN_DANH_GIA:
        return None
    loi = []
    for i in range(n - SO_TUAN_DANH_GIA, n):
        thuc_te = chuoi[i]
        if thuc_te <= 0:
            continue
        du_bao, _ = du_bao_tuan(chuoi[:i], 1)
        loi.append(abs(thuc_te - du_bao[0]) / thuc_te)
    if not loi:
        return None
    return round(min(MAPE_TOI_DA, 100 * sum(loi) / len(loi)), 3)


def de_xuat_nhap(du_bao_30_ngay: int, ton_toi_thieu: int, ton_kha_dung: int) -> int:
    """`max(0, dự báo 30 ngày + tồn tối thiểu - tồn khả dụng)` (spec 07 mục 7)."""
    return max(0, du_bao_30_ngay + ton_toi_thieu - ton_kha_dung)

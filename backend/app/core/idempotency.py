"""Idempotency-Key (spec 06 mục 6): nhớ kết quả 24 giờ trong bộ nhớ tiến trình (đồ án chạy một tiến trình).

Khóa gắn với chủ sở hữu (khách) nên hai khách trùng khóa không thấy kết quả của nhau. Nơi gọi tự bảo đảm tuần tự
hóa cùng một chủ (khóa dòng giỏ) và tự kiểm tra kết quả cũ còn hợp lệ (đơn còn tồn tại) vì bản ghi này có thể được
đặt trước khi transaction commit.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc

HAN_NHO = timedelta(hours=24)
TOI_DA_BAN_GHI = 10_000


@dataclass(frozen=True)
class BanGhi:
    dau_van_tay: str
    ket_qua: dict
    het_han: datetime


_kho: dict[tuple[str, int, str], BanGhi] = {}


def doc_khoa(gia_tri: str | None) -> str:
    """Header `Idempotency-Key` phải là UUID; thiếu hoặc sai dạng là `400 DU_LIEU_KHONG_HOP_LE`."""
    try:
        return str(uuid.UUID(gia_tri or ""))
    except ValueError:
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE",
            "Dữ liệu không hợp lệ",
            chi_tiet=[{"truong": "Idempotency-Key", "loi": "Bắt buộc, là UUID do client sinh"}],
        ) from None


def dau_van_tay(noi_dung: dict) -> str:
    return hashlib.sha256(json.dumps(noi_dung, sort_keys=True, default=str).encode()).hexdigest()


def tra_cuu(thao_tac: str, chu_id: int, khoa: str, dau_van_tay_yeu_cau: str) -> dict | None:
    """Kết quả đã nhớ của cùng khóa; cùng khóa nhưng nội dung khác là `409 TRUNG_DU_LIEU`."""
    ban_ghi = _kho.get((thao_tac, chu_id, khoa))
    if ban_ghi is None or ban_ghi.het_han <= bay_gio_utc():
        return None
    if ban_ghi.dau_van_tay != dau_van_tay_yeu_cau:
        raise LoiNghiepVu(
            "TRUNG_DU_LIEU",
            "Khóa Idempotency-Key này đã dùng cho một yêu cầu có nội dung khác",
            chi_tiet={"truong": "Idempotency-Key"},
        )
    return ban_ghi.ket_qua


def ghi_nho(thao_tac: str, chu_id: int, khoa: str, dau_van_tay_yeu_cau: str, ket_qua: dict) -> None:
    bay_gio = bay_gio_utc()
    if len(_kho) >= TOI_DA_BAN_GHI:
        for k in [k for k, v in _kho.items() if v.het_han <= bay_gio] or list(_kho)[: TOI_DA_BAN_GHI // 10]:
            _kho.pop(k, None)
    _kho[(thao_tac, chu_id, khoa)] = BanGhi(dau_van_tay_yeu_cau, ket_qua, bay_gio + HAN_NHO)


def quen_het() -> None:
    """Cho test."""
    _kho.clear()

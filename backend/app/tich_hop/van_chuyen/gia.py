"""Danh mục địa giới giả cho dev và test: file JSON nhỏ trong `du_lieu_gia/`."""

import json
from decimal import Decimal
from pathlib import Path

from app.tich_hop.van_chuyen import DiaChiGiao, DonViHanhChinh

_DUONG_DAN = Path(__file__).parent / "du_lieu_gia" / "dia_gioi.json"


class DanhMucDiaGioiGia:
    def __init__(self) -> None:
        du_lieu = json.loads(_DUONG_DAN.read_text(encoding="utf-8"))
        self._tinh = [DonViHanhChinh(**t) for t in du_lieu["tinh"]]
        self._xa = {ma: [DonViHanhChinh(**x) for x in ds] for ma, ds in du_lieu["xa"].items()}

    def danh_sach_tinh(self) -> list[DonViHanhChinh]:
        return list(self._tinh)

    def danh_sach_xa(self, ma_tinh: str) -> list[DonViHanhChinh] | None:
        ds = self._xa.get(ma_tinh)
        return None if ds is None else list(ds)


class VanChuyenGia:
    """Phí cố định để dev/test: 25.000 ₫ cho kg đầu, +5.000 ₫ mỗi kg tiếp theo (làm tròn lên), tối đa 100.000 ₫."""

    async def tinh_phi(self, dia_chi: DiaChiGiao, khoi_luong_gram: int, gia_tri: Decimal) -> Decimal:
        so_kg = max(1, -(-khoi_luong_gram // 1000))
        return Decimal(min(25_000 + 5_000 * (so_kg - 1), 100_000))

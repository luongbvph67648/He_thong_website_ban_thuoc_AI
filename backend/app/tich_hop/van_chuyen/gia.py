"""Danh mục địa giới giả cho dev và test: file JSON nhỏ trong `du_lieu_gia/`."""

import json
import secrets
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from app.tich_hop.van_chuyen import (
    DiaChiGiao,
    DonViHanhChinh,
    KetQuaVanDon,
    SuKienVanChuyen,
    WebhookKhongHopLe,
)

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
    """Bản giả, không gọi đối tác. Phí: 25.000 ₫ cho kg đầu, +5.000 ₫ mỗi kg tiếp theo (làm tròn lên), tối đa 100.000 ₫.

    Mã vận đơn giả là `GIA` + số.
    """

    ten = "GIA"

    async def tinh_phi(self, dia_chi: DiaChiGiao, khoi_luong_gram: int, gia_tri: Decimal) -> Decimal:
        so_kg = max(1, -(-khoi_luong_gram // 1000))
        return Decimal(min(25_000 + 5_000 * (so_kg - 1), 100_000))

    async def tao_van_don(self, don: Any, loai: Literal["giao_hang", "tra_hang"], khoi_luong_gram: int) -> KetQuaVanDon:
        so_kg = max(1, -(-khoi_luong_gram // 1000))
        phi = Decimal(min(25_000 + 5_000 * (so_kg - 1), 100_000))
        return KetQuaVanDon(ma_van_don=f"GIA{don.id}{secrets.randbelow(10**6):06d}", phi=phi)

    async def huy_van_don(self, ma_van_don: str) -> None:
        return None

    def xac_thuc_webhook(self, headers: dict[str, str], body: dict[str, Any]) -> SuKienVanChuyen:
        """Webhook giả không cần token (route chỉ có khi chế độ giả): `{ma_van_don, trang_thai_doi_tac}`."""
        ma, tt = body.get("ma_van_don"), body.get("trang_thai_doi_tac")
        if not isinstance(ma, str) or not isinstance(tt, str) or not ma or not tt:
            raise WebhookKhongHopLe("Thiếu ma_van_don hoặc trang_thai_doi_tac")
        return SuKienVanChuyen(ma_van_don=ma, trang_thai_doi_tac=tt, du_lieu=body)

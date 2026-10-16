"""Cổng giả: chạy offline, có trang "cổng giả" ở frontend để bấm thành công/thất bại (spec 08 mục 4)."""

import hashlib
import hmac
from decimal import Decimal
from typing import Any

from app.core.config import settings
from app.models.ban_hang import DonHang, ThanhToan
from app.tich_hop.thanh_toan import KetQuaHoan, KetQuaIpn, tham_chieu

KHOA_GIA = b"khoa-gia-chi-dung-cho-dev-va-test"
TRUONG_KY = ("tham_chieu", "so_tien", "ma_giao_dich", "thanh_cong")


def ky(tham_so: dict[str, Any]) -> str:
    chuoi = "&".join(f"{k}={tham_so.get(k)}" for k in TRUONG_KY)
    return hmac.new(KHOA_GIA, chuoi.encode(), hashlib.sha256).hexdigest()


def dung_ipn(ref: str, so_tien: Decimal, thanh_cong: bool) -> dict[str, Any]:
    """IPN đã ký bằng khóa giả, y như cổng thật sẽ gửi."""
    tham_so: dict[str, Any] = {
        "tham_chieu": ref,
        "so_tien": str(int(so_tien)),
        "ma_giao_dich": f"GIA-{ref}",
        "thanh_cong": "1" if thanh_cong else "0",
    }
    return {**tham_so, "chu_ky": ky(tham_so)}


class CongGia:
    async def tao_url_thanh_toan(self, don: DonHang, giao_dich: ThanhToan, ip: str) -> str:
        return f"{settings.FRONTEND_URL.rstrip('/')}/thanh-toan-gia?giao_dich={tham_chieu(don, giao_dich)}"

    def xac_thuc_ipn(self, tham_so: dict[str, Any]) -> KetQuaIpn:
        hop_le = hmac.compare_digest(str(tham_so.get("chu_ky", "")), ky(tham_so))
        du_lieu = {k: v for k, v in tham_so.items() if k != "chu_ky"}
        try:
            so_tien = Decimal(str(tham_so.get("so_tien")))
        except ArithmeticError:
            so_tien = None
        return KetQuaIpn(
            hop_le,
            str(tham_so.get("tham_chieu", "")),
            so_tien,
            tham_so.get("ma_giao_dich"),
            str(tham_so.get("thanh_cong")) == "1",
            du_lieu,
        )

    async def hoan_tien(self, giao_dich_goc: ThanhToan, so_tien: Decimal, ly_do: str) -> KetQuaHoan:
        return KetQuaHoan(True, f"GIA-HOAN-{giao_dich_goc.id}")

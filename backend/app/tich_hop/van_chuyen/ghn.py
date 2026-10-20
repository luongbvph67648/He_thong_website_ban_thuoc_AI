"""Adapter GHN API v2 (spec 08 mục 5). Header `Token` và `ShopId`; webhook xác thực bằng `GHN_WEBHOOK_TOKEN`.

Chưa được thử với sandbox thật: tên trường theo tài liệu GHN v2, cần đối chiếu khi chạy `VAN_CHUYEN_CHE_DO=ghn`.
"""

import hmac
from decimal import Decimal
from typing import Any, Literal

import httpx

from app.tich_hop import cau_hinh
from app.tich_hop.http import tao_client
from app.tich_hop.van_chuyen import DiaChiGiao, KetQuaVanDon, SuKienVanChuyen, WebhookKhongHopLe

THOI_GIAN_CHO_GIAY = 15.0


class LoiGhn(Exception):
    """GHN trả lỗi hoặc không phản hồi."""


class VanChuyenGhn:
    ten = "GHN"

    def _tieu_de(self) -> dict[str, str]:
        return {"Token": cau_hinh.ghn_token(), "ShopId": cau_hinh.ghn_shop_id()}

    async def _goi(self, duong_dan: str, thanh: dict[str, Any]) -> dict[str, Any]:
        try:
            async with tao_client(
                cau_hinh.ghn_url(), base_url=cau_hinh.ghn_url(), timeout=THOI_GIAN_CHO_GIAY
            ) as client:
                r = await client.post(duong_dan, json=thanh, headers=self._tieu_de())
            du_lieu = r.json()
        except (httpx.HTTPError, ValueError) as e:
            raise LoiGhn("Không gọi được GHN") from e
        if r.status_code != 200 or du_lieu.get("code") != 200:
            raise LoiGhn(f"GHN từ chối: {du_lieu.get('message', r.status_code)}")
        return du_lieu.get("data") or {}

    async def tinh_phi(self, dia_chi: DiaChiGiao, khoi_luong_gram: int, gia_tri: Decimal) -> Decimal:
        du_lieu = await self._goi(
            "/shiip/public-api/v2/shipping-order/fee",
            {
                "service_type_id": 2,
                "to_ward_code": dia_chi.ma_phuong_xa,
                "weight": khoi_luong_gram,
                "insurance_value": int(gia_tri),
            },
        )
        return Decimal(int(du_lieu["total"]))

    async def tao_van_don(self, don: Any, loai: Literal["giao_hang", "tra_hang"], khoi_luong_gram: int) -> KetQuaVanDon:
        du_lieu = await self._goi(
            "/shiip/public-api/v2/shipping-order/create",
            {
                "payment_type_id": 2,  # người nhận trả phí; phí đã nằm trong tổng tiền đơn nên thu COD gồm cả phí
                "required_note": "CHOXEMHANGKHONGTHU",
                "client_order_code": don.ma_don,
                "to_name": don.ten_nguoi_nhan,
                "to_phone": don.sdt_nguoi_nhan,
                "to_address": don.dia_chi_giao,
                "to_ward_code": don.ma_phuong_xa,
                "cod_amount": int(don.tong_tien) if don.phuong_thuc_tt == "cod" else 0,
                "weight": khoi_luong_gram,
                "service_type_id": 2,
                "items": [{"name": c.ten_san_pham, "quantity": c.so_luong} for c in don.chi_tiet],
            },
        )
        return KetQuaVanDon(ma_van_don=str(du_lieu["order_code"]), phi=Decimal(int(du_lieu.get("total_fee", 0))))

    async def huy_van_don(self, ma_van_don: str) -> None:
        """GHN trả mảng kết quả theo từng mã; đã hủy từ trước thì coi như thành công (gọi lại an toàn)."""
        du_lieu = await self._goi("/shiip/public-api/v2/switch-status/cancel", {"order_codes": [ma_van_don]})
        for ket_qua in du_lieu if isinstance(du_lieu, list) else []:
            if ket_qua.get("order_code") == ma_van_don and not ket_qua.get("result"):
                thong_diep = str(ket_qua.get("message", ""))
                da_huy_roi = "already" in thong_diep.lower() and "cancel" in thong_diep.lower()
                if not da_huy_roi:  # "Order is already cancelled" là thành công; "không cho hủy" thì không
                    raise LoiGhn(f"GHN không hủy được vận đơn: {thong_diep or 'không rõ lý do'}")

    def xac_thuc_webhook(self, headers: dict[str, str], body: dict[str, Any]) -> SuKienVanChuyen:
        mong_doi = cau_hinh.ghn_webhook_token()
        nhan = {k.lower(): v for k, v in headers.items()}.get("token", "")
        if not mong_doi or not hmac.compare_digest(nhan.encode(), mong_doi.encode()):
            raise WebhookKhongHopLe("Token webhook không đúng")
        ma, tt = body.get("OrderCode"), body.get("Status")
        if not isinstance(ma, str) or not isinstance(tt, str) or not ma or not tt:
            raise WebhookKhongHopLe("Thiếu OrderCode hoặc Status")
        return SuKienVanChuyen(ma_van_don=ma, trang_thai_doi_tac=tt, du_lieu=body)

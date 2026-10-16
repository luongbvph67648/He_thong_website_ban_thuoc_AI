"""Hub WebSocket giữ trong bộ nhớ process (đồ án chạy 1 process API; nhiều process cần Redis pub/sub, ngoài phạm vi)."""

import asyncio
import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class KetNoi(Protocol):
    async def send_json(self, data: Any) -> None: ...


class Hub:
    def __init__(self) -> None:
        self._phong: dict[str, list[tuple[KetNoi, str]]] = {}

    def vao(self, ma_phien: str, ket_noi: KetNoi, vai_tro: str) -> None:
        self._phong.setdefault(ma_phien, []).append((ket_noi, vai_tro))

    def roi(self, ma_phien: str, ket_noi: KetNoi) -> None:
        con_lai = [x for x in self._phong.get(ma_phien, []) if x[0] is not ket_noi]
        if con_lai:
            self._phong[ma_phien] = con_lai
        else:
            self._phong.pop(ma_phien, None)

    def so_ket_noi(self, ma_phien: str) -> int:
        return len(self._phong.get(ma_phien, []))

    async def phat(self, ma_phien: str, du_lieu: dict[str, Any], *, tru: KetNoi | None = None) -> None:
        """Gửi cho mọi thành viên của phòng (trừ `tru`); kết nối hỏng bị bỏ, không làm hỏng người khác."""
        for kn, _ in list(self._phong.get(ma_phien, [])):
            if kn is tru:
                continue
            try:
                await asyncio.wait_for(kn.send_json(du_lieu), timeout=5)
            except Exception:  # noqa: BLE001
                logger.info("Bỏ kết nối chat hỏng")
                self.roi(ma_phien, kn)


HUB = Hub()

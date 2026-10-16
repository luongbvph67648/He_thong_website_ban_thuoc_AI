"""Điểm duy nhất gọi Claude API (spec 07 mục 2). Không import `anthropic` ở nơi khác.

`AI_GIA_LAP=true` chuyển hết sang `ai/gia_lap.py` (không mạng, không cần khóa).
"""

import json
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import anthropic
from anthropic import AsyncAnthropic

from app.ai import gia_lap
from app.core.config import settings

logger = logging.getLogger(__name__)

_BETA_FALLBACK = "server-side-fallback-2026-07-01"
_client: AsyncAnthropic | None = None


class AiTuChoi(Exception):  # noqa: N818 - tên theo nghiệp vụ
    """Claude từ chối trả lời (`stop_reason == "refusal"`) kể cả sau fallback."""


class AiLoi(Exception):  # noqa: N818
    """Không gọi được Claude (hết lượt thử lại, chưa cấu hình khóa...). Nơi gọi chạy nhánh dự phòng không dùng AI."""


@dataclass
class SuDung:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0

    def cong(self, usage: Any) -> None:
        self.input_tokens += usage.input_tokens or 0
        self.output_tokens += usage.output_tokens or 0
        self.cache_read_input_tokens += getattr(usage, "cache_read_input_tokens", 0) or 0
        self.cache_creation_input_tokens += getattr(usage, "cache_creation_input_tokens", 0) or 0

    @property
    def tong_token(self) -> int:
        return self.input_tokens + self.output_tokens + self.cache_read_input_tokens + self.cache_creation_input_tokens

    def chi_phi_usd(self) -> Decimal:
        """Chi phí ước tính theo đơn giá ở cấu hình (USD / 1 triệu token). Ghi cache tính như input."""
        trieu = Decimal(1_000_000)
        tong = (
            Decimal(str(settings.AI_GIA_INPUT)) * (self.input_tokens + self.cache_creation_input_tokens)
            + Decimal(str(settings.AI_GIA_OUTPUT)) * self.output_tokens
            + Decimal(str(settings.AI_GIA_CACHE_READ)) * self.cache_read_input_tokens
        )
        return (tong / trieu).quantize(Decimal("0.000001"))


def _lay_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        khoa = settings.ANTHROPIC_API_KEY.get_secret_value()
        if not khoa:
            raise AiLoi("Chưa cấu hình ANTHROPIC_API_KEY")
        _client = AsyncAnthropic(api_key=khoa, timeout=60.0, max_retries=2)
    return _client


def _tham_so(effort: str) -> dict[str, Any]:
    tham_so: dict[str, Any] = {"model": settings.CLAUDE_MODEL, "output_config": {"effort": effort}}
    if not settings.CLAUDE_MODEL.startswith("claude-haiku"):  # Haiku không hỗ trợ fallback
        tham_so["betas"] = [_BETA_FALLBACK]
        tham_so["fallbacks"] = "default"
    return tham_so


def _system(van_ban: str) -> list[dict[str, Any]]:
    return [{"type": "text", "text": van_ban, "cache_control": {"type": "ephemeral"}}]


def _loi_api(e: Exception) -> AiLoi:
    # Chỉ log loại lỗi, không log nội dung prompt/response (có thể chứa dữ liệu sức khỏe)
    logger.warning("Gọi Claude lỗi: %s", type(e).__name__)
    return AiLoi(type(e).__name__)


_LOI_API = (anthropic.APIStatusError, anthropic.APIConnectionError, anthropic.APITimeoutError)


async def goi_json(
    *,
    system: str,
    noi_dung: list[dict[str, Any]],
    schema: dict[str, Any],
    effort: str = "low",
    max_tokens: int = 2000,
    su_dung: SuDung | None = None,
) -> dict[str, Any]:
    """Một lượt hỏi, trả về dict đúng JSON Schema `schema` (nơi gọi vẫn kiểm lại bằng Pydantic)."""
    if settings.AI_GIA_LAP:
        return await gia_lap.goi_json(system=system, noi_dung=noi_dung, schema=schema, su_dung=su_dung)
    tham_so = _tham_so(effort)
    tham_so["output_config"]["format"] = {"type": "json_schema", "schema": schema}
    try:
        resp = await _lay_client().beta.messages.create(
            max_tokens=max_tokens,
            system=_system(system),
            messages=[{"role": "user", "content": noi_dung}],
            **tham_so,
        )
    except _LOI_API as e:
        raise _loi_api(e) from e
    if su_dung:
        su_dung.cong(resp.usage)
    if resp.stop_reason == "refusal":
        raise AiTuChoi(getattr(getattr(resp, "stop_details", None), "category", None))
    van_ban = next((b.text for b in resp.content if b.type == "text"), None)
    if van_ban is None:
        raise AiLoi("Phản hồi không có văn bản")
    try:
        return json.loads(van_ban)
    except json.JSONDecodeError as e:
        raise AiLoi("Phản hồi không phải JSON") from e


async def stream_chat(
    *,
    system: str,
    lich_su: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    thuc_thi_tool: Callable[[Any], Awaitable[dict[str, Any]]],
    effort: str = "medium",
    max_luot_tool: int = 5,
    su_dung: SuDung | None = None,
) -> AsyncIterator[str]:
    """Trả lời có dùng tool, yield từng đoạn chữ.

    `lich_su`: text các lượt trước + câu hỏi mới. `thuc_thi_tool(block)` bắt buộc kiểm input bằng Pydantic (tool bật
    `eager_input_streaming` thì API không kiểm) rồi trả `{"type": "tool_result", "tool_use_id": ..., "content": ...}`.
    """
    if settings.AI_GIA_LAP:
        async for doan in gia_lap.stream_chat(
            system=system, lich_su=lich_su, tools=tools, thuc_thi_tool=thuc_thi_tool, su_dung=su_dung
        ):
            yield doan
        return
    messages = list(lich_su)
    for _ in range(max_luot_tool + 1):
        try:
            async with _lay_client().beta.messages.stream(
                max_tokens=8000, system=_system(system), tools=tools, messages=messages, **_tham_so(effort)
            ) as stream:
                async for doan in stream.text_stream:
                    yield doan
                msg = await stream.get_final_message()
        except _LOI_API as e:
            raise _loi_api(e) from e
        if su_dung:
            su_dung.cong(msg.usage)
        if msg.stop_reason == "refusal":
            raise AiTuChoi(getattr(getattr(msg, "stop_details", None), "category", None))
        if msg.stop_reason != "tool_use":
            return
        messages.append({"role": "assistant", "content": msg.content})  # giữ nguyên toàn bộ khối (cả thinking)
        ket_qua = [await thuc_thi_tool(b) for b in msg.content if b.type == "tool_use"]
        messages.append({"role": "user", "content": ket_qua})  # mọi tool_result trong MỘT message
    raise AiLoi("Vượt số lượt gọi tool cho phép")

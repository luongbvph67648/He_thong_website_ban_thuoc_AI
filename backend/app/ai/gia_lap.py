"""Client Claude giả cho dev và test (`AI_GIA_LAP=true`): cùng giao diện `goi_json`/`stream_chat`, không mạng.

Mặc định `goi_json` trả giá trị hợp lệ theo schema và `stream_chat` trả một câu cố định. Test cài kịch bản bằng
`KICH_BAN` (hàm nhận tham số của lời gọi, có thể ném `AiTuChoi`/`AiLoi`) và đếm lời gọi bằng `so_lan_goi_json`...
"""

import inspect
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

CAU_TRA_LOI_MAC_DINH = "Xin chào, mình là trợ lý của nhà thuốc (bản giả lập)."


@dataclass
class KichBan:
    goi_json: Callable[..., Any] | None = None
    stream: Callable[..., Any] | None = None
    so_lan_goi_json: int = 0
    so_lan_stream: int = 0
    lan_goi_json: list[dict[str, Any]] = field(default_factory=list)
    lan_stream: list[dict[str, Any]] = field(default_factory=list)


KICH_BAN = KichBan()


def dat_lai() -> None:
    """Xóa kịch bản và bộ đếm (fixture test gọi trước mỗi test)."""
    KICH_BAN.goi_json = KICH_BAN.stream = None
    KICH_BAN.so_lan_goi_json = KICH_BAN.so_lan_stream = 0
    KICH_BAN.lan_goi_json.clear()
    KICH_BAN.lan_stream.clear()


def gia_tri_theo_schema(schema: dict[str, Any]) -> Any:
    """Giá trị tối thiểu hợp lệ cho một JSON Schema đơn giản (đủ cho các schema AI02/AI04/AI05/AI06)."""
    if "enum" in schema:
        return schema["enum"][0]
    kieu = schema.get("type")
    if kieu == "object":
        return {k: gia_tri_theo_schema(v) for k, v in schema.get("properties", {}).items()}
    if kieu == "array":
        return []
    if kieu == "string":
        return ""
    if kieu == "integer":
        return 0
    if kieu == "number":
        return 0.0
    if kieu == "boolean":
        return False
    if isinstance(kieu, list):
        return None if "null" in kieu else gia_tri_theo_schema({**schema, "type": kieu[0]})
    return None


async def _ket_qua(ham: Callable[..., Any], **kw: Any) -> Any:
    kq = ham(**kw)
    return await kq if inspect.isawaitable(kq) else kq


async def goi_json(**kw: Any) -> dict[str, Any]:
    KICH_BAN.so_lan_goi_json += 1
    KICH_BAN.lan_goi_json.append(kw)
    if KICH_BAN.goi_json is not None:
        return await _ket_qua(KICH_BAN.goi_json, **kw)
    return gia_tri_theo_schema(kw["schema"])


async def stream_chat(**kw: Any) -> AsyncIterator[str]:
    KICH_BAN.so_lan_stream += 1
    KICH_BAN.lan_stream.append(kw)
    if KICH_BAN.stream is None:
        yield CAU_TRA_LOI_MAC_DINH
        return
    kq = KICH_BAN.stream(**kw)
    if inspect.isasyncgen(kq):
        async for doan in kq:
            yield doan
        return
    kq = await kq if isinstance(kq, Awaitable) else kq
    if isinstance(kq, str):
        yield kq
    else:
        for doan in kq:
            yield doan

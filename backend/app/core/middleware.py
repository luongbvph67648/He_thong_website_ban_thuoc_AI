"""Middleware ASGI thuần (không dùng BaseHTTPMiddleware để không làm hỏng contextvars và streaming)."""

import logging
import re
import time
import uuid

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.log import request_id_var

logger = logging.getLogger("app.truy_cap")

HEADER_REQUEST_ID = "X-Request-ID"
_REQUEST_ID_HOP_LE = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


class RequestIdMiddleware:
    """Gắn request_id cho mỗi request: nhận từ header nếu hợp lệ, không thì tự sinh.

    Trả lại trong header `X-Request-ID`, đưa vào mọi dòng log và ghi một dòng log truy cập.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        tu_client = Headers(scope=scope).get(HEADER_REQUEST_ID, "")
        request_id = tu_client if _REQUEST_ID_HOP_LE.match(tu_client) else uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id  # để handler lỗi 500 (nằm ngoài middleware) đọc được
        token = request_id_var.set(request_id)
        bat_dau = time.perf_counter()
        trang_thai = 500  # giữ nguyên nếu lỗi nổ ra trước khi có response

        async def gui(message: Message) -> None:
            nonlocal trang_thai
            if message["type"] == "http.response.start":
                trang_thai = message["status"]
                MutableHeaders(scope=message)[HEADER_REQUEST_ID] = request_id
            await send(message)

        try:
            await self.app(scope, receive, gui)
        finally:
            logger.info(
                "request",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],  # chỉ path, không ghi query string
                    "trang_thai": trang_thai,
                    "thoi_gian_ms": round((time.perf_counter() - bat_dau) * 1000, 1),
                },
            )
            request_id_var.reset(token)

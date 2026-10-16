"""Middleware ASGI thuần (không dùng BaseHTTPMiddleware để không làm hỏng contextvars và streaming)."""

import logging
import re
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.log import request_id_var
from app.core.loi import phan_hoi_loi_he_thong, tra_loi

logger = logging.getLogger("app.truy_cap")
logger_loi = logging.getLogger("app.loi")

HEADER_REQUEST_ID = "X-Request-ID"
_REQUEST_ID_HOP_LE = re.compile(r"[A-Za-z0-9._-]{8,64}")  # dùng fullmatch: `$` vẫn cho phép "\n" ở cuối


def mau_route(scope: Scope) -> str:
    """Mẫu route của request, ví dụ `/api/v1/toi/don/{ma_don}`. Không khớp route nào thì `<khong-khop>`.

    FastAPI chỉ cho mẫu tương đối trong router có tiền tố, nên ghép lại tiền tố từ path thật. Tiền tố do
    `include_router(prefix=...)` quyết định, không được chứa tham số (nếu có sẽ ghi nguyên giá trị).
    """
    route = scope.get("route")
    if route is None:
        return "<khong-khop>"
    try:
        da_giai = route.path_format.format(**{k: str(v) for k, v in scope.get("path_params", {}).items()})
        path = scope["path"]
        tien_to = path[: len(path) - len(da_giai)] if da_giai and path.endswith(da_giai) else ""
        return tien_to + route.path_format
    except (AttributeError, KeyError, IndexError):
        return getattr(route, "path", None) or "<khong-khop>"


class RequestIdMiddleware:
    """Gắn request_id cho mỗi request: nhận từ header nếu hợp lệ, không thì tự sinh.

    - Trả lại trong header `X-Request-ID`, đưa vào mọi dòng log.
    - Ghi một dòng log truy cập, chỉ gồm mẫu route (không có giá trị token trong path, không có query string).
    - Là nơi duy nhất xử lý lỗi không bắt được: ghi log JSON kèm request_id rồi trả 500 sạch. Không ném lại cho
      server, nếu không uvicorn sẽ in thêm một traceback dạng text không qua bộ che dữ liệu nhạy cảm.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        tu_client = Headers(scope=scope).get(HEADER_REQUEST_ID, "")
        request_id = tu_client if _REQUEST_ID_HOP_LE.fullmatch(tu_client) else uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id  # để handler lỗi đọc được qua request.state
        token = request_id_var.set(request_id)
        bat_dau = time.perf_counter()
        trang_thai = 500
        da_bat_dau_tra_loi = False

        async def gui(message: Message) -> None:
            nonlocal trang_thai, da_bat_dau_tra_loi
            if message["type"] == "http.response.start":
                da_bat_dau_tra_loi = True
                trang_thai = message["status"]
                MutableHeaders(scope=message)[HEADER_REQUEST_ID] = request_id
            await send(message)

        try:
            try:
                await self.app(scope, receive, gui)
            except Exception:
                logger_loi.error("Lỗi hệ thống không bắt được", exc_info=True)
                if da_bat_dau_tra_loi:  # đã gửi một phần response: không còn cách trả 500, để server đóng kết nối
                    raise
                await phan_hoi_loi_he_thong(request_id)(scope, receive, gui)
        finally:
            logger.info(
                "request",
                extra={
                    "method": scope["method"],
                    "path": mau_route(scope),
                    "trang_thai": trang_thai,
                    "thoi_gian_ms": round((time.perf_counter() - bat_dau) * 1000, 1),
                },
            )
            request_id_var.reset(token)


@dataclass(frozen=True)
class QuyTacThanRequest:
    """Giới hạn thân request của một route (khớp theo phương thức và toàn bộ đường dẫn)."""

    phuong_thuc: str
    mau_duong_dan: re.Pattern[str]
    toi_da_byte: int
    ma_loi: str
    thong_diep: str


class GioiHanKichThuocThan:
    """Từ chối thân request quá lớn TRƯỚC khi route chạy, nên cũng trước xác thực và trước khi parse multipart.

    Starlette đọc cả multipart vào tệp tạm trước khi chạy dependency (kể cả `yeu_cau_quyen`): không có lớp này thì người
    chưa đăng nhập vẫn ghi được hàng trăm MB vào đĩa chỉ bằng một request. Có `Content-Length` vượt mức thì trả lỗi ngay
    không đọc gì; thân gửi theo từng mảnh (không có `Content-Length`) thì đếm byte và ngắt khi vượt, route chỉ thấy
    "client ngắt kết nối" còn phản hồi lỗi của route bị bỏ để trả lỗi đúng của quy tắc.
    """

    def __init__(self, app: ASGIApp, quy_tac: Sequence[QuyTacThanRequest]) -> None:
        self.app = app
        self.quy_tac = tuple(quy_tac)

    def _tim(self, scope: Scope) -> QuyTacThanRequest | None:
        for q in self.quy_tac:
            if scope["method"] == q.phuong_thuc and q.mau_duong_dan.fullmatch(scope["path"]):
                return q
        return None

    @staticmethod
    def _phan_hoi(q: QuyTacThanRequest):
        return tra_loi(q.ma_loi, q.thong_diep, {"toi_da_byte": q.toi_da_byte})

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        quy_tac = self._tim(scope) if scope["type"] == "http" else None
        if quy_tac is None:
            await self.app(scope, receive, send)
            return
        do_dai = Headers(scope=scope).get("content-length", "")
        if do_dai.isdigit() and int(do_dai) > quy_tac.toi_da_byte:
            await self._phan_hoi(quy_tac)(scope, receive, send)
            return

        da_nhan = 0
        vuot = False

        async def nhan() -> Message:
            nonlocal da_nhan, vuot
            if vuot:
                return {"type": "http.disconnect"}
            thong_diep = await receive()
            if thong_diep["type"] == "http.request":
                da_nhan += len(thong_diep.get("body", b""))
                if da_nhan > quy_tac.toi_da_byte:
                    vuot = True
                    return {"type": "http.disconnect"}
            return thong_diep

        async def gui(thong_diep: Message) -> None:
            if not vuot:  # route phản ứng với "ngắt kết nối" bằng lỗi riêng: bỏ, ta trả lỗi của quy tắc
                await send(thong_diep)

        try:
            await self.app(scope, nhan, gui)
        except Exception:
            if not vuot:
                raise
        if vuot:
            await self._phan_hoi(quy_tac)(scope, receive, send)

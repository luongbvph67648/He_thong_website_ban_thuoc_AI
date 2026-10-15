"""Log JSON một dòng mỗi bản ghi, kèm request_id của request đang xử lý.

Quy tắc: không ghi mật khẩu, OTP, token, dữ liệu sức khỏe, và không ghi query string vào log.
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

_THUOC_TINH_CO_SAN = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime", "taskName"}


class BoLocRequestId(logging.Filter):
    """Gắn request_id hiện tại vào bản ghi log (trừ khi nơi gọi đã truyền sẵn qua `extra`)."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        du_lieu: dict[str, object] = {
            "thoi_gian": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "muc": record.levelname,
            "logger": record.name,
            "thong_diep": record.getMessage(),
        }
        for khoa, gia_tri in record.__dict__.items():
            if khoa not in _THUOC_TINH_CO_SAN:
                du_lieu[khoa] = gia_tri
        if record.exc_info:
            du_lieu["loi"] = self.formatException(record.exc_info)
        return json.dumps(du_lieu, ensure_ascii=False, default=str)


def cau_hinh_log(muc: int | str = logging.INFO) -> None:
    """Gắn handler JSON vào root logger. Gọi nhiều lần vẫn chỉ có một handler."""
    goc = logging.getLogger()
    for handler in list(goc.handlers):
        if getattr(handler, "_nha_thuoc", False):
            goc.removeHandler(handler)
    handler = logging.StreamHandler(sys.stdout)
    handler._nha_thuoc = True  # type: ignore[attr-defined]
    handler.setFormatter(JsonFormatter())
    handler.addFilter(BoLocRequestId())
    goc.addHandler(handler)
    goc.setLevel(muc)

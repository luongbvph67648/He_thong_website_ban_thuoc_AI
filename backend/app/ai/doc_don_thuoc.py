"""AI06: đọc ảnh đơn thuốc gợi ý cho dược sĩ (spec 07 mục 6). Không trích thông tin cá nhân; dược sĩ luôn xác nhận."""

from datetime import date
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, Field

from app.ai import claude
from app.ai.anh import khoi_anh
from app.ai.chatbot import doc_prompt


def _cat(n: int) -> BeforeValidator:
    return BeforeValidator(lambda v: (v.strip()[:n] or None) if isinstance(v, str) else v)


def _ngay_long(v: Any) -> Any:
    """Ngày AI đọc sai định dạng thì coi như không đọc được, không làm hỏng cả đơn."""
    if isinstance(v, str):
        try:
            return date.fromisoformat(v.strip()[:10])
        except ValueError:
            return None
    return v


def _kep(v: Any) -> Any:
    return min(1.0, max(0.0, v)) if isinstance(v, int | float) and not isinstance(v, bool) else v


DON_THUOC_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "ngay_ke": {"type": ["string", "null"]},
        "co_chu_ky_bac_si": {"type": "boolean"},
        "danh_sach_thuoc": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ten_thuoc_tren_don": {"type": "string"},
                    "ham_luong": {"type": ["string", "null"]},
                    "so_luong_ke": {"type": ["string", "null"]},
                    "cach_dung": {"type": ["string", "null"]},
                    "do_tin_cay": {"type": "number"},
                },
                "required": ["ten_thuoc_tren_don", "ham_luong", "so_luong_ke", "cach_dung", "do_tin_cay"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["ngay_ke", "co_chu_ky_bac_si", "danh_sach_thuoc"],
    "additionalProperties": False,
}


class ThuocDoc(BaseModel):
    ten_thuoc_tren_don: Annotated[str, _cat(255), Field(min_length=1)]
    ham_luong: Annotated[str | None, _cat(50)] = None
    so_luong_ke: Annotated[str | None, _cat(50)] = None
    cach_dung: Annotated[str | None, _cat(300)] = None
    do_tin_cay: Annotated[float, BeforeValidator(_kep)]


class DonThuocDoc(BaseModel):
    ngay_ke: Annotated[date | None, BeforeValidator(_ngay_long)] = None
    co_chu_ky_bac_si: bool = False
    danh_sach_thuoc: list[ThuocDoc] = Field(default_factory=list, max_length=30)


async def doc_don_thuoc(ds_anh_b64: list[str], su_dung: claude.SuDung) -> DonThuocDoc:
    """Ném `AiLoi`/`AiTuChoi`/`ValidationError` khi không có kết quả dùng được."""
    kq = await claude.goi_json(
        system=doc_prompt("doc_don_thuoc.md"),
        noi_dung=[*(khoi_anh(a) for a in ds_anh_b64), {"type": "text", "text": "Trích danh sách thuốc theo schema."}],
        schema=DON_THUOC_SCHEMA,
        effort="high",
        max_tokens=4000,
        su_dung=su_dung,
    )
    return DonThuocDoc.model_validate(kq)

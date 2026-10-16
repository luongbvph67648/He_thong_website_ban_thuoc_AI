"""AI05: đọc ảnh hộp thuốc (spec 07 mục 6). Kết quả kiểm lại bằng Pydantic; chữ trong ảnh là dữ liệu không tin cậy."""

from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, Field

from app.ai import claude
from app.ai.anh import khoi_anh
from app.ai.chatbot import doc_prompt


def _cat(n: int) -> BeforeValidator:
    return BeforeValidator(lambda v: v.strip()[:n] if isinstance(v, str) else v)


Chuoi = Annotated[str, _cat(200)]

HOP_THUOC_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "ten_san_pham": {"type": ["string", "null"]},
        "hoat_chat": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"ten": {"type": "string"}, "ham_luong": {"type": ["string", "null"]}},
                "required": ["ten", "ham_luong"],
                "additionalProperties": False,
            },
        },
        "so_dang_ky": {"type": ["string", "null"]},
        "nha_san_xuat": {"type": ["string", "null"]},
        "dang_bao_che": {"type": ["string", "null"]},
        "do_tin_cay": {"type": "number"},
    },
    "required": ["ten_san_pham", "hoat_chat", "so_dang_ky", "nha_san_xuat", "dang_bao_che", "do_tin_cay"],
    "additionalProperties": False,
}


class HoatChatDoc(BaseModel):
    ten: Chuoi
    ham_luong: Chuoi | None = None


class HopThuocDoc(BaseModel):
    ten_san_pham: Chuoi | None = None
    hoat_chat: list[HoatChatDoc] = Field(default_factory=list, max_length=15)
    so_dang_ky: Annotated[str | None, _cat(50)] = None
    nha_san_xuat: Chuoi | None = None
    dang_bao_che: Chuoi | None = None
    do_tin_cay: Annotated[float, BeforeValidator(lambda v: min(1.0, max(0.0, v)) if isinstance(v, int | float) else v)]

    def co_thong_tin(self) -> bool:
        return bool(self.ten_san_pham or self.so_dang_ky or self.hoat_chat)


async def doc_hop_thuoc(anh_b64: str, su_dung: claude.SuDung) -> HopThuocDoc:
    """Ném `AiLoi`/`AiTuChoi`/`ValidationError` khi không có kết quả dùng được (nơi gọi quyết định cách báo)."""
    kq = await claude.goi_json(
        system=doc_prompt("doc_anh_hop_thuoc.md"),
        noi_dung=[khoi_anh(anh_b64), {"type": "text", "text": "Trích thông tin trên bao bì theo schema."}],
        schema=HOP_THUOC_SCHEMA,
        effort="medium",
        max_tokens=2000,
        su_dung=su_dung,
    )
    return HopThuocDoc.model_validate(kq)

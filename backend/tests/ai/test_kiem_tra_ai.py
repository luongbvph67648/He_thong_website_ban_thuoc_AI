"""Công cụ `python -m app.ai.kiem_tra`: logic chạy đúng với client giả (không gọi Claude thật)."""

import pytest
from pydantic import SecretStr

from app.ai import claude, kiem_tra
from app.core.config import settings


@pytest.fixture(autouse=True)
def _xoa_loi():
    kiem_tra._loi.clear()


async def test_tu_choi_khi_con_ai_gia_lap(monkeypatch, capsys):
    monkeypatch.setattr(settings, "AI_GIA_LAP", True)
    assert await kiem_tra.chay(None) == 1
    assert "AI_GIA_LAP=true" in capsys.readouterr().out


async def test_bao_thieu_khoa_api(monkeypatch, capsys):
    monkeypatch.setattr(settings, "AI_GIA_LAP", False)
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", SecretStr(""))
    assert await kiem_tra.chay(None) == 1
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().out


async def test_tat_ca_dat_khi_claude_tra_loi_dung(monkeypatch, capsys):
    monkeypatch.setattr(settings, "AI_GIA_LAP", False)
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", SecretStr("sk-test"))
    monkeypatch.setattr(settings, "EMBEDDING_GIA_LAP", True)

    async def goi_json(*, schema, **_):
        return {k: None for k in schema.get("required", [])}

    class Block:
        id = "tu_1"

    async def stream_chat(*, thuc_thi_tool, **_):
        await thuc_thi_tool(Block())
        yield "Bây giờ là "
        yield "10:00."

    monkeypatch.setattr(claude, "goi_json", goi_json)
    monkeypatch.setattr(claude, "stream_chat", stream_chat)
    assert await kiem_tra.chay(None) == 0
    ra = capsys.readouterr().out
    assert ra.count("[ĐẠT]") == 6 and "[LỖI]" not in ra and "BỎ QUA" in ra


async def test_bao_loi_khi_schema_bi_api_tu_choi(monkeypatch, capsys):
    monkeypatch.setattr(settings, "AI_GIA_LAP", False)
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", SecretStr("sk-test"))

    async def hong(**_):
        raise claude.AiLoi("BadRequestError")

    async def stream_chat(**_):
        raise claude.AiLoi("AuthenticationError")
        yield ""  # pragma: no cover

    monkeypatch.setattr(claude, "goi_json", hong)
    monkeypatch.setattr(claude, "stream_chat", stream_chat)
    assert await kiem_tra.chay(None) == 1
    ra = capsys.readouterr().out
    assert "[LỖI] Schema AI02" in ra and "[LỖI] Chat có tool" in ra

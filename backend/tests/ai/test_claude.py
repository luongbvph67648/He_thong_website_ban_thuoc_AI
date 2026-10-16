"""T7.1: ai/claude.py (cả nhánh giả lập và nhánh thật với client thay thế), ai/embedding.py."""

import json
from types import SimpleNamespace as NS

import pytest

from app.ai import claude, embedding, gia_lap
from app.core.config import settings

SCHEMA = {
    "type": "object",
    "properties": {"y_dinh": {"type": "string", "enum": ["hoi_san_pham", "khac"]}, "nguy_hiem": {"type": "boolean"}},
    "required": ["y_dinh", "nguy_hiem"],
    "additionalProperties": False,
}


async def test_goi_json_gia_lap_tra_ve_dung_schema_va_dem_loi_goi():
    kq = await claude.goi_json(system="s", noi_dung=[{"type": "text", "text": "x"}], schema=SCHEMA)
    assert kq == {"y_dinh": "hoi_san_pham", "nguy_hiem": False} and gia_lap.KICH_BAN.so_lan_goi_json == 1
    gia_lap.KICH_BAN.goi_json = lambda **kw: {"y_dinh": "khac", "nguy_hiem": True}
    assert (await claude.goi_json(system="s", noi_dung=[], schema=SCHEMA))["nguy_hiem"] is True


async def test_stream_chat_gia_lap_mac_dinh_va_kich_ban():
    async def thuc_thi(b):
        raise AssertionError

    ds = [d async for d in claude.stream_chat(system="s", lich_su=[], tools=[], thuc_thi_tool=thuc_thi)]
    assert "".join(ds) == gia_lap.CAU_TRA_LOI_MAC_DINH
    gia_lap.KICH_BAN.stream = lambda **kw: ["Một ", "hai"]
    ds = [d async for d in claude.stream_chat(system="s", lich_su=[], tools=[], thuc_thi_tool=thuc_thi)]
    assert ds == ["Một ", "hai"] and gia_lap.KICH_BAN.so_lan_stream == 2


async def test_kich_ban_nem_loi_ai_tu_choi():
    def nem(**kw):
        raise claude.AiTuChoi("cyber")

    gia_lap.KICH_BAN.goi_json = nem
    with pytest.raises(claude.AiTuChoi):
        await claude.goi_json(system="s", noi_dung=[], schema=SCHEMA)


# --- nhánh thật với client thay thế (không mạng) ---


class _Usage:
    input_tokens, output_tokens, cache_read_input_tokens, cache_creation_input_tokens = 100, 50, 80, 0


class _Messages:
    def __init__(self, resp):
        self.resp, self.lan_goi = resp, []

    async def create(self, **kw):
        self.lan_goi.append(kw)
        return self.resp


@pytest.fixture
def that(monkeypatch):
    monkeypatch.setattr(settings, "AI_GIA_LAP", False)
    monkeypatch.setattr(settings, "CLAUDE_MODEL", "claude-opus-5-5")

    def dat(resp):
        m = _Messages(resp)
        monkeypatch.setattr(claude, "_lay_client", lambda: NS(beta=NS(messages=m)))
        return m

    return dat


async def test_goi_json_that_gui_dung_tham_so_va_cong_usage(that):
    m = that(
        NS(
            stop_reason="end_turn",
            usage=_Usage(),
            content=[NS(type="text", text=json.dumps({"y_dinh": "khac", "nguy_hiem": False}))],
        )
    )
    su_dung = claude.SuDung()
    kq = await claude.goi_json(
        system="Hệ thống", noi_dung=[{"type": "text", "text": "x"}], schema=SCHEMA, su_dung=su_dung
    )
    assert kq["y_dinh"] == "khac"
    goi = m.lan_goi[0]
    assert (
        goi["model"] == "claude-opus-5-5"
        and goi["betas"] == ["server-side-fallback-2026-07-01"]
        and goi["fallbacks"] == "default"
    )
    assert goi["output_config"]["effort"] == "low" and goi["output_config"]["format"]["schema"] == SCHEMA
    assert goi["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert "tool_choice" not in goi and "thinking" not in goi
    assert (su_dung.input_tokens, su_dung.output_tokens, su_dung.cache_read_input_tokens) == (100, 50, 80)
    assert su_dung.tong_token == 230 and str(su_dung.chi_phi_usd()) == "0.001416"  # (4*100 + 20*50 + 0.2*80)/1e6


async def test_goi_json_that_haiku_khong_gui_fallback(that, monkeypatch):
    monkeypatch.setattr(settings, "CLAUDE_MODEL", "claude-haiku-5-5")
    m = that(
        NS(
            stop_reason="end_turn",
            usage=_Usage(),
            content=[NS(type="text", text='{"y_dinh":"khac","nguy_hiem":false}')],
        )
    )
    await claude.goi_json(system="s", noi_dung=[], schema=SCHEMA)
    assert "betas" not in m.lan_goi[0] and "fallbacks" not in m.lan_goi[0]


async def test_goi_json_that_tu_choi_va_json_hong(that):
    that(NS(stop_reason="refusal", usage=_Usage(), content=[], stop_details=NS(category="cyber")))
    with pytest.raises(claude.AiTuChoi):
        await claude.goi_json(system="s", noi_dung=[], schema=SCHEMA)
    that(NS(stop_reason="end_turn", usage=_Usage(), content=[NS(type="text", text="không phải json")]))
    with pytest.raises(claude.AiLoi):
        await claude.goi_json(system="s", noi_dung=[], schema=SCHEMA)


async def test_thieu_khoa_api_thi_ai_loi(monkeypatch):
    monkeypatch.setattr(settings, "AI_GIA_LAP", False)
    monkeypatch.setattr(claude, "_client", None)
    with pytest.raises(claude.AiLoi):
        await claude.goi_json(system="s", noi_dung=[], schema=SCHEMA)


# --- embedding ---


async def test_embedding_gia_xac_dinh_chuan_hoa_va_gan_nhau_khi_chung_tu():
    a, b, c = await embedding.embed(
        ["Thuốc hạ sốt giảm đau paracetamol", "paracetamol hạ sốt", "kem chống nắng da mặt"]
    )
    assert len(a) == embedding.SO_CHIEU
    assert abs(sum(x * x for x in a) - 1) < 1e-9
    assert a == (await embedding.embed(["Thuốc hạ sốt giảm đau paracetamol"]))[0]
    cos = lambda x, y: sum(p * q for p, q in zip(x, y, strict=True))  # noqa: E731
    assert cos(a, b) > cos(a, c)
    assert await embedding.embed([]) == []
    assert embedding.ten_mo_hinh() == embedding.TEN_MO_HINH_GIA


class _Stream:
    def __init__(self, msg, doan):
        self.msg, self.doan = msg, doan

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    @property
    def text_stream(self):
        async def gen():
            for d in self.doan:
                yield d

        return gen()

    async def get_final_message(self):
        return self.msg


async def test_stream_chat_that_chay_tool_va_giu_nguyen_khoi_noi_dung(that, monkeypatch):
    tool_use = NS(type="tool_use", id="tu_1", name="tim_san_pham", input={"tu_khoa": "ho"})
    luot = [
        _Stream(NS(stop_reason="tool_use", usage=_Usage(), content=[NS(type="thinking"), tool_use]), ["Để mình tìm. "]),
        _Stream(NS(stop_reason="end_turn", usage=_Usage(), content=[NS(type="text", text="Xong")]), ["Xong"]),
    ]
    goi = []

    def stream(**kw):
        goi.append(kw)
        return luot[len(goi) - 1]

    monkeypatch.setattr(settings, "AI_GIA_LAP", False)
    monkeypatch.setattr(claude, "_lay_client", lambda: NS(beta=NS(messages=NS(stream=stream))))
    da_chay = []

    async def thuc_thi(b):
        da_chay.append(b.name)
        return {"type": "tool_result", "tool_use_id": b.id, "content": "[]"}

    su_dung = claude.SuDung()
    ds = [
        d
        async for d in claude.stream_chat(
            system="s", lich_su=[{"role": "user", "content": "ho"}], tools=[], thuc_thi_tool=thuc_thi, su_dung=su_dung
        )
    ]
    assert "".join(ds) == "Để mình tìm. Xong" and da_chay == ["tim_san_pham"]
    lan2 = goi[1]["messages"]
    assert lan2[1]["role"] == "assistant" and lan2[1]["content"][0].type == "thinking"  # giữ cả khối thinking
    assert lan2[2] == {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "tu_1", "content": "[]"}]}
    assert su_dung.output_tokens == 100


async def test_stream_chat_that_tu_choi(monkeypatch):
    monkeypatch.setattr(settings, "AI_GIA_LAP", False)
    msg = NS(stop_reason="refusal", usage=_Usage(), content=[], stop_details=NS(category="bio"))
    monkeypatch.setattr(claude, "_lay_client", lambda: NS(beta=NS(messages=NS(stream=lambda **kw: _Stream(msg, [])))))

    async def thuc_thi(b):
        raise AssertionError

    with pytest.raises(claude.AiTuChoi):
        [d async for d in claude.stream_chat(system="s", lich_su=[], tools=[], thuc_thi_tool=thuc_thi)]

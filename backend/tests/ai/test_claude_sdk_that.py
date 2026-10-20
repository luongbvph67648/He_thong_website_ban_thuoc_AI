"""ai/claude.py chạy với SDK `anthropic` THẬT, chỉ thay đường truyền bằng `httpx.MockTransport` (không mạng, không khóa).

Khác `test_claude.py` (client thay thế bằng đối tượng giả): ở đây SDK tự dựng yêu cầu HTTP (URL, tiêu đề beta, thân JSON
đã chuẩn hóa), tự phân tích phản hồi JSON và luồng SSE đúng định dạng của Messages API. Bắt được các lỗi lệch API mà client
giả không thấy: tham số bị SDK từ chối, sai tên tiêu đề beta, vòng lặp tool ghép sai `tool_result`, đếm token sai.
"""

import json

import httpx2 as httpx  # SDK anthropic 1.x dùng gói `httpx2` làm tầng HTTP (không nhận client của `httpx`)
import pytest
from anthropic import AsyncAnthropic

from app.ai import claude
from app.core.config import settings

SCHEMA = {
    "type": "object",
    "properties": {"y_dinh": {"type": "string", "enum": ["hoi_san_pham", "khac"]}, "nguy_hiem": {"type": "boolean"}},
    "required": ["y_dinh", "nguy_hiem"],
    "additionalProperties": False,
}


def _tin_nhan(noi_dung, stop_reason="end_turn", **them):
    return {
        "id": "msg_01",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-5-5",
        "content": noi_dung,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": 120,
            "output_tokens": 30,
            "cache_read_input_tokens": 100,
            "cache_creation_input_tokens": 0,
        },
        **them,
    }


def _sse(*su_kien: tuple[str, dict]) -> str:
    return "".join(f"event: {ten}\ndata: {json.dumps(du_lieu)}\n\n" for ten, du_lieu in su_kien)


def _luong_tool():
    """Lượt 1: vài chữ rồi gọi tool `gio_hien_tai`."""
    return _sse(
        (
            "message_start",
            {
                "type": "message_start",
                "message": {**_tin_nhan([], None), "usage": {"input_tokens": 200, "output_tokens": 1}},
            },
        ),
        (
            "content_block_start",
            {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        ),
        (
            "content_block_delta",
            {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Để tôi xem giờ. "}},
        ),
        ("content_block_stop", {"type": "content_block_stop", "index": 0}),
        (
            "content_block_start",
            {
                "type": "content_block_start",
                "index": 1,
                "content_block": {"type": "tool_use", "id": "toolu_01", "name": "gio_hien_tai", "input": {}},
            },
        ),
        (
            "content_block_delta",
            {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": "{}"}},
        ),
        ("content_block_stop", {"type": "content_block_stop", "index": 1}),
        (
            "message_delta",
            {
                "type": "message_delta",
                "delta": {"stop_reason": "tool_use", "stop_sequence": None},
                "usage": {"output_tokens": 25},
            },
        ),
        ("message_stop", {"type": "message_stop"}),
    )


def _luong_ket_thuc():
    """Lượt 2: trả lời cuối bằng kết quả tool."""
    return _sse(
        (
            "message_start",
            {
                "type": "message_start",
                "message": {**_tin_nhan([], None), "usage": {"input_tokens": 260, "output_tokens": 1}},
            },
        ),
        (
            "content_block_start",
            {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        ),
        (
            "content_block_delta",
            {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Bây giờ là "}},
        ),
        (
            "content_block_delta",
            {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "10:30."}},
        ),
        ("content_block_stop", {"type": "content_block_stop", "index": 0}),
        (
            "message_delta",
            {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                "usage": {"output_tokens": 12},
            },
        ),
        ("message_stop", {"type": "message_stop"}),
    )


@pytest.fixture
def mang(monkeypatch):
    """Cài client SDK thật đi qua `MockTransport`; trả danh sách yêu cầu đã gửi và hàm đặt bộ xử lý phản hồi."""
    yeu_cau: list[httpx.Request] = []
    xu_ly = {"ham": lambda r: httpx.Response(500)}

    def handler(request: httpx.Request) -> httpx.Response:
        yeu_cau.append(request)
        return xu_ly["ham"](request)

    client = AsyncAnthropic(
        api_key="khoa-gia", max_retries=0, http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    monkeypatch.setattr(claude, "_client", client)
    monkeypatch.setattr(settings, "AI_GIA_LAP", False)
    monkeypatch.setattr(settings, "CLAUDE_MODEL", "claude-opus-5-5")

    class Mang:
        da_gui = yeu_cau

        @staticmethod
        def dat(ham):
            xu_ly["ham"] = ham

    return Mang


async def test_goi_json_dung_sdk_that_gui_dung_yeu_cau_va_doc_json(mang):
    mang.dat(
        lambda r: httpx.Response(
            200, json=_tin_nhan([{"type": "text", "text": json.dumps({"y_dinh": "khac", "nguy_hiem": True})}])
        )
    )
    su_dung = claude.SuDung()
    kq = await claude.goi_json(
        system="Phân loại.", noi_dung=[{"type": "text", "text": "đau đầu"}], schema=SCHEMA, su_dung=su_dung
    )
    assert kq == {"y_dinh": "khac", "nguy_hiem": True}
    (r,) = mang.da_gui
    assert r.url.path == "/v1/messages" and "server-side-fallback-2026-07-01" in r.headers["anthropic-beta"]
    than = json.loads(r.content)
    assert than["model"] == "claude-opus-5-5" and than["fallbacks"] == "default"
    assert than["output_config"]["format"] == {"type": "json_schema", "schema": SCHEMA}
    assert than["output_config"]["effort"] == "low"
    assert than["system"][0]["cache_control"] == {"type": "ephemeral"}  # system prompt cố định được cache
    assert than["messages"] == [{"role": "user", "content": [{"type": "text", "text": "đau đầu"}]}]
    assert (su_dung.input_tokens, su_dung.output_tokens, su_dung.cache_read_input_tokens) == (120, 30, 100)


async def test_goi_json_refusal_va_loi_api_thanh_ngoai_le_cua_he_thong(mang):
    mang.dat(
        lambda r: httpx.Response(
            200,
            json=_tin_nhan([], "refusal", stop_details={"type": "refusal", "category": "cyber", "explanation": None}),
        )
    )
    with pytest.raises(claude.AiTuChoi):
        await claude.goi_json(system="s", noi_dung=[{"type": "text", "text": "x"}], schema=SCHEMA)
    for ma in (401, 429, 500, 529):
        mang.dat(
            lambda r, ma=ma: httpx.Response(ma, json={"type": "error", "error": {"type": "api_error", "message": "x"}})
        )
        with pytest.raises(claude.AiLoi):  # nơi gọi chạy nhánh dự phòng không dùng AI, không để lỗi SDK lọt ra ngoài
            await claude.goi_json(system="s", noi_dung=[{"type": "text", "text": "x"}], schema=SCHEMA)


async def test_goi_json_bi_cat_do_max_tokens_la_loi_khong_phai_json_hong(mang):
    mang.dat(lambda r: httpx.Response(200, json=_tin_nhan([{"type": "text", "text": '{"y_dinh": "kh'}], "max_tokens")))
    with pytest.raises(claude.AiLoi):
        await claude.goi_json(system="s", noi_dung=[{"type": "text", "text": "x"}], schema=SCHEMA)


async def test_stream_chat_vong_lap_tool_voi_sse_that(mang):
    luot = []

    def xu_ly(r: httpx.Request) -> httpx.Response:
        luot.append(json.loads(r.content))
        noi_dung = _luong_tool() if len(luot) == 1 else _luong_ket_thuc()
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=noi_dung.encode())

    mang.dat(xu_ly)
    da_goi = []

    async def thuc_thi(block):
        da_goi.append((block.name, block.input, block.id))
        return {"type": "tool_result", "tool_use_id": block.id, "content": "10:30"}

    tools = [
        {"name": "gio_hien_tai", "description": "Giờ hiện tại", "input_schema": {"type": "object", "properties": {}}}
    ]
    su_dung = claude.SuDung()
    doan = [
        d
        async for d in claude.stream_chat(
            system="Trợ lý.",
            lich_su=[{"role": "user", "content": "mấy giờ?"}],
            tools=tools,
            thuc_thi_tool=thuc_thi,
            su_dung=su_dung,
        )
    ]
    assert "".join(doan) == "Để tôi xem giờ. Bây giờ là 10:30."
    assert da_goi == [("gio_hien_tai", {}, "toolu_01")]
    assert len(luot) == 2 and luot[0]["stream"] is True
    # Lượt 2 phải mang nguyên khối assistant (chữ + tool_use) rồi MỘT message user chứa tool_result
    hai = luot[1]["messages"]
    assert [m["role"] for m in hai] == ["user", "assistant", "user"]
    assert [b["type"] for b in hai[1]["content"]] == ["text", "tool_use"]
    assert hai[2]["content"] == [{"type": "tool_result", "tool_use_id": "toolu_01", "content": "10:30"}]
    assert su_dung.input_tokens == 200 + 260 and su_dung.output_tokens == 25 + 12  # cộng dồn hai lượt


async def test_stream_chat_vuot_so_luot_tool_thi_bao_loi(mang):
    mang.dat(
        lambda r: httpx.Response(200, headers={"content-type": "text/event-stream"}, content=_luong_tool().encode())
    )

    async def thuc_thi(block):
        return {"type": "tool_result", "tool_use_id": block.id, "content": "x"}

    with pytest.raises(claude.AiLoi):
        _ = [
            d
            async for d in claude.stream_chat(
                system="s",
                lich_su=[{"role": "user", "content": "x"}],
                tools=[],
                thuc_thi_tool=thuc_thi,
                max_luot_tool=2,
            )
        ]


async def test_stream_chat_loi_api_giua_luong_thanh_ai_loi(mang):
    mang.dat(
        lambda r: httpx.Response(529, json={"type": "error", "error": {"type": "overloaded_error", "message": "x"}})
    )

    async def thuc_thi(block):
        raise AssertionError

    with pytest.raises(claude.AiLoi):
        _ = [
            d
            async for d in claude.stream_chat(
                system="s", lich_su=[{"role": "user", "content": "x"}], tools=[], thuc_thi_tool=thuc_thi
            )
        ]


async def test_haiku_khong_gui_fallback(mang, monkeypatch):
    monkeypatch.setattr(settings, "CLAUDE_MODEL", "claude-haiku-5-5")
    mang.dat(
        lambda r: httpx.Response(
            200, json=_tin_nhan([{"type": "text", "text": json.dumps({"y_dinh": "khac", "nguy_hiem": False})}])
        )
    )
    await claude.goi_json(system="s", noi_dung=[{"type": "text", "text": "x"}], schema=SCHEMA)
    (r,) = mang.da_gui
    assert "fallbacks" not in json.loads(r.content) and "anthropic-beta" not in r.headers

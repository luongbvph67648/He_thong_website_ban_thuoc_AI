"""Kiểm tra nhanh AI chạy THẬT: `uv run python -m app.ai.kiem_tra [--anh duong_dan_anh_hop_thuoc]`.

Cần `AI_GIA_LAP=false` và `ANTHROPIC_API_KEY` trong `backend/.env`. Mỗi bước in ĐẠT/LỖI, token và chi phí ước tính;
chạy cả bộ thường dưới 0,05 USD. Không in khóa API hay nội dung nhạy cảm. Mã thoát 0 khi mọi bước đạt, 1 nếu có lỗi.

Các bước:
1. Cấu hình (khóa, model, chế độ).
2. Bốn JSON Schema thật của hệ thống (phân loại chat, tóm tắt hội thoại, đọc hộp thuốc, đọc đơn thuốc) có được API
   nhận không (`output_config.format`).
3. Chat có tool: Claude gọi tool giả `gio_hien_tai` và trả lời (kiểm vòng lặp tool + streaming).
4. Embedding (chỉ khi `EMBEDDING_GIA_LAP=false`): câu cùng nghĩa phải gần nhau hơn câu khác nghĩa.
5. (Tuỳ chọn `--anh`) đọc một ảnh hộp thuốc thật bằng AI05.
"""

import argparse
import asyncio
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app.ai import claude, doc_anh, embedding
from app.ai.anh import chuan_bi_anh
from app.ai.chatbot import PHAN_LOAI_SCHEMA, doc_prompt
from app.ai.doc_don_thuoc import DON_THUOC_SCHEMA
from app.ai.tom_tat import TOM_TAT_SCHEMA
from app.core.config import settings

_loi: list[str] = []


def _in(dat: bool, ten: str, chi_tiet: str = "") -> None:
    print(f"[{'ĐẠT' if dat else 'LỖI'}] {ten}" + (f": {chi_tiet}" if chi_tiet else ""))
    if not dat:
        _loi.append(ten)


def _chi_phi(su_dung: claude.SuDung) -> str:
    return f"{su_dung.tong_token} token, ~{su_dung.chi_phi_usd()} USD"


async def _buoc_schema() -> None:
    cac_schema: list[tuple[str, str, dict[str, Any], str]] = [
        ("AI02 phân loại câu hỏi", "chat_phan_loai.md", PHAN_LOAI_SCHEMA, "Tôi bị đau đầu nhẹ, nên uống gì?"),
        (
            "AI04 tóm tắt hội thoại",
            "",
            TOM_TAT_SCHEMA,
            "Khách: Tôi muốn hỏi về thuốc ho cho bé.\nTrợ lý: Bé bao nhiêu tuổi?",
        ),
        (
            "AI05 đọc hộp thuốc",
            "doc_anh_hop_thuoc.md",
            doc_anh.HOP_THUOC_SCHEMA,
            "Không có ảnh, hãy trả giá trị rỗng/null.",
        ),
        ("AI06 đọc đơn thuốc", "doc_don_thuoc.md", DON_THUOC_SCHEMA, "Không có ảnh, hãy trả danh sách rỗng."),
    ]
    for ten, tep_prompt, schema, cau in cac_schema:
        su_dung = claude.SuDung()
        try:
            he_thong = doc_prompt(tep_prompt) if tep_prompt else "Tóm tắt ngắn gọn bằng tiếng Việt."
            kq = await claude.goi_json(
                system=he_thong,
                noi_dung=[{"type": "text", "text": cau}],
                schema=schema,
                effort="low",
                max_tokens=1000,
                su_dung=su_dung,
            )
            thieu = [k for k in schema.get("required", []) if k not in kq]
            _in(not thieu, f"Schema {ten}", _chi_phi(su_dung) + (f"; thiếu trường {thieu}" if thieu else ""))
        except claude.AiTuChoi:
            _in(False, f"Schema {ten}", "Claude từ chối trả lời (refusal)")
        except claude.AiLoi as e:
            _in(False, f"Schema {ten}", f"{e} (xem log để biết chi tiết lỗi API)")


async def _buoc_tool() -> None:
    tools = [
        {
            "name": "gio_hien_tai",
            "description": "Trả về giờ hiện tại ở Việt Nam. Dùng khi khách hỏi mấy giờ.",
            "strict": True,
            "eager_input_streaming": True,
            "input_schema": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        }
    ]
    da_goi_tool = 0

    async def thuc_thi(block: Any) -> dict[str, Any]:
        nonlocal da_goi_tool
        da_goi_tool += 1
        gio = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%H:%M")
        return {"type": "tool_result", "tool_use_id": block.id, "content": gio}

    su_dung = claude.SuDung()
    doan: list[str] = []
    try:
        async for d in claude.stream_chat(
            system="Bạn là trợ lý nhà thuốc. Cần biết giờ thì dùng tool gio_hien_tai. Trả lời ngắn, tiếng Việt.",
            lich_su=[{"role": "user", "content": "Bây giờ là mấy giờ rồi?"}],
            tools=tools,
            thuc_thi_tool=thuc_thi,
            effort="low",
            su_dung=su_dung,
        ):
            doan.append(d)
    except (claude.AiLoi, claude.AiTuChoi) as e:
        _in(False, "Chat có tool + streaming", str(e) or type(e).__name__)
        return
    van_ban = "".join(doan).strip()
    _in(
        bool(van_ban) and da_goi_tool >= 1,
        "Chat có tool + streaming",
        f"tool gọi {da_goi_tool} lần, {len(doan)} đoạn, {_chi_phi(su_dung)}",
    )
    print(f"      Claude trả lời: {van_ban[:200]}")


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True)) / (
        math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    )


async def _buoc_embedding() -> None:
    if settings.EMBEDDING_GIA_LAP:
        print("[BỎ QUA] Embedding: EMBEDDING_GIA_LAP=true (vector giả). Muốn BGE-M3 thật: xem docs/BAT_AI_THAT.md")
        return
    try:
        v = await embedding.embed(
            ["thuốc hạ sốt giảm đau", "Paracetamol 500mg giảm đau, hạ sốt", "khẩu trang y tế 4 lớp"]
        )
    except Exception as e:  # noqa: BLE001 - thiếu thư viện, tải mô hình lỗi...: in rõ cho người chạy
        _in(False, "Embedding BGE-M3", f"{type(e).__name__}: {e}")
        return
    gan, xa = _cosine(v[0], v[1]), _cosine(v[0], v[2])
    _in(
        len(v[0]) == embedding.SO_CHIEU and gan > xa,
        "Embedding BGE-M3",
        f"{len(v[0])} chiều, cosine cùng nghĩa {gan:.2f} > khác nghĩa {xa:.2f}",
    )


async def _buoc_anh(duong_dan: Path) -> None:
    su_dung = claude.SuDung()
    try:
        anh_b64 = chuan_bi_anh(duong_dan.read_bytes())
        kq = await doc_anh.doc_hop_thuoc(anh_b64, su_dung)
    except (OSError, ValueError) as e:
        _in(False, "AI05 đọc ảnh", f"không đọc được tệp ảnh: {e}")
        return
    except (claude.AiLoi, claude.AiTuChoi) as e:
        _in(False, "AI05 đọc ảnh", str(e) or type(e).__name__)
        return
    _in(True, "AI05 đọc ảnh", _chi_phi(su_dung))
    hoat_chat = [h.ten for h in kq.hoat_chat]
    print(f"      Đọc được: tên={kq.ten_san_pham!r}, hoạt chất={hoat_chat}, SĐK={kq.so_dang_ky!r}")


async def chay(duong_dan_anh: Path | None) -> int:
    co_khoa = bool(settings.ANTHROPIC_API_KEY.get_secret_value())
    khoa = "có" if co_khoa else "CHƯA ĐẶT"
    print(f"Model: {settings.CLAUDE_MODEL} | AI_GIA_LAP={settings.AI_GIA_LAP} | khóa API: {khoa}")
    if settings.AI_GIA_LAP:
        _in(False, "Cấu hình", "AI_GIA_LAP=true: đang dùng AI giả. Đặt AI_GIA_LAP=false trong backend/.env")
        return 1
    if not co_khoa:
        _in(False, "Cấu hình", "chưa đặt ANTHROPIC_API_KEY trong backend/.env")
        return 1
    _in(True, "Cấu hình")
    await _buoc_schema()
    await _buoc_tool()
    await _buoc_embedding()
    if duong_dan_anh:
        await _buoc_anh(duong_dan_anh)
    print("\nTất cả bước đạt." if not _loi else f"\nCó {len(_loi)} bước lỗi: {', '.join(_loi)}")
    return 1 if _loi else 0


def main() -> int:
    tham_so = argparse.ArgumentParser(prog="python -m app.ai.kiem_tra", description=__doc__.split("\n")[0])
    tham_so.add_argument("--anh", type=Path, help="ảnh hộp thuốc thật để thử AI05 (tuỳ chọn)")
    return asyncio.run(chay(tham_so.parse_args().anh))


if __name__ == "__main__":
    sys.exit(main())

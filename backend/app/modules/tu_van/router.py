"""Chat tư vấn AI (KVL05): `/api/v1/tu-van/*`, công khai (`khach_tuy_chon`) kèm giới hạn lượt theo IP và theo phiên."""

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, WebSocket
from fastapi.responses import StreamingResponse

from app.ai import chatbot
from app.core.db import Db, TaoPhien, lay_tao_phien
from app.core.gioi_han import GioiHanCuaSoTruot, lay_bo_gioi_han_chat
from app.core.loi import LoiNghiepVu
from app.core.phan_quyen import khach_tuy_chon
from app.models.khach_hang import KhachHang
from app.modules.tai_khoan.phien_http import dia_chi_ip
from app.modules.tu_van import chuyen_duoc_si, dich_vu, ws
from app.modules.tu_van.schemas import ChatVao, DanhGiaVao, GapDuocSiRa, GapDuocSiVao, LichSuRa

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tu-van", tags=["Tư vấn AI"])
KhachTuyChon = Annotated[KhachHang | None, Depends(khach_tuy_chon)]
TOI_DA_MOI_IP = 30
TOI_DA_MOI_PHIEN = 20
CUA_SO_GIAY = 600


def _sse(loai: str, du_lieu: dict[str, Any]) -> str:
    return f"event: {loai}\ndata: {json.dumps(du_lieu, ensure_ascii=False, default=str)}\n\n"


def _gioi_han(bo: GioiHanCuaSoTruot, ip: str, ma_phien: uuid.UUID) -> None:
    for khoa, toi_da in ((f"chat-ip:{ip}", TOI_DA_MOI_IP), (f"chat-phien:{ma_phien}", TOI_DA_MOI_PHIEN)):
        cho = bo.thu(khoa, toi_da, CUA_SO_GIAY)
        if cho is not None:
            giay = int(cho) + 1
            raise LoiNghiepVu(
                "QUA_GIOI_HAN",
                "Bạn hỏi quá nhanh, vui lòng chờ một lúc rồi hỏi tiếp",
                chi_tiet={"thu_lai_sau_giay": giay},
                headers={"Retry-After": str(giay)},
            )


async def _phat(tao_phien: TaoPhien, vao: dich_vu.DauVaoLuot, khach_id: int | None, cau_hoi: str) -> AsyncIterator[str]:
    """Stream SSE. KHÔNG giữ kết nối DB trong lúc chờ Claude: mỗi lần đọc dùng phiên ngắn (`tao_phien`), rồi một phiên
    ngắn lưu tin nhắn của AI. Khách ngắt kết nối giữa chừng thì token đã tốn vẫn được cộng vào chi phí ngày."""
    kq = chatbot.KetQuaLuot()
    da_luu = False
    try:
        async with tao_phien() as db_khach:
            khach = await db_khach.get(KhachHang, khach_id) if khach_id else None
        async for ev in chatbot.chay_luot(
            db=None,
            tao_phien=tao_phien,
            kq=kq,
            khach=khach,
            cau_hoi=cau_hoi,
            tin_truoc=vao.tin_truoc,
            ds_dau_hieu=vao.ds_dau_hieu,
            nguong_chuyen=vao.nguong_chuyen,
            loi_nhac=vao.loi_nhac,
            chat_bat=vao.chat_bat and not vao.da_chuyen_duoc_si,
            het_ngan_sach=vao.het_ngan_sach,
        ):
            if ev["loai"] != "ket_thuc":
                yield _sse(ev["loai"], {k: v for k, v in ev.items() if k != "loai"})
        async with tao_phien() as db_ghi:
            tin_id = await dich_vu.luu_tra_loi(db_ghi, vao.hoi_thoai_id, kq)
        da_luu = True
        yield _sse("ket_thuc", {"tin_nhan_id": tin_id})
    except Exception:  # noqa: BLE001  không lộ chi tiết lỗi cho khách; log không chứa nội dung hội thoại
        logger.exception("Lượt chat lỗi")
        yield _sse("loi", {"thong_diep": "Có lỗi xảy ra, vui lòng thử lại hoặc gặp dược sĩ."})
    finally:
        if not da_luu and kq.su_dung.tong_token:
            # Bị hủy (khách đóng tab) hoặc lỗi sau khi đã gọi Claude: Claude vẫn tính tiền nên phải ghi chi phí
            await asyncio.shield(_ghi_chi_phi_doi_dang(tao_phien, vao.hoi_thoai_id, kq.su_dung))


async def _ghi_chi_phi_doi_dang(tao_phien: TaoPhien, hoi_thoai_id: int, su_dung) -> None:
    try:
        async with tao_phien() as db:
            await dich_vu.cong_chi_phi(db, hoi_thoai_id, su_dung)
    except Exception:  # noqa: BLE001  ghi chi phí là cố gắng tối đa, không che lỗi gốc
        logger.exception("Không ghi được chi phí AI của lượt chat bị gián đoạn")


@router.post(
    "/chat",
    summary="Chat với trợ lý AI (SSE) (KVL05)",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def chat(
    vao: ChatVao,
    request: Request,
    db: Db,
    khach: KhachTuyChon,
    bo_gioi_han: Annotated[GioiHanCuaSoTruot, Depends(lay_bo_gioi_han_chat)],
    tao_phien: Annotated[TaoPhien, Depends(lay_tao_phien)],
):
    """Sự kiện: `van_ban`, `the_san_pham`, `chuyen_duoc_si`, `nguy_hiem`, `ket_thuc`, `loi`."""
    ip = dia_chi_ip(request)
    _gioi_han(bo_gioi_han, ip, vao.ma_phien)
    luot = await dich_vu.mo_luot(db, khach, vao.ma_phien, vao.noi_dung, ip)
    return StreamingResponse(
        _phat(tao_phien, luot, khach.id if khach else None, vao.noi_dung.strip()),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{ma_phien}/tin-nhan", response_model=LichSuRa, summary="Lịch sử một phiên tư vấn (KVL05)")
async def lich_su(ma_phien: uuid.UUID, db: Db, khach: KhachTuyChon):
    return await dich_vu.lich_su(db, khach, ma_phien)


@router.post("/danh-gia", status_code=204, summary="Báo câu trả lời hữu ích hoặc sai (KVL05)")
async def danh_gia(vao: DanhGiaVao, db: Db, khach: KhachTuyChon):
    await dich_vu.danh_gia(db, khach, vao.ma_phien, vao.tin_nhan_id, vao.ket_qua)


@router.post("/gap-duoc-si", response_model=GapDuocSiRa, summary="Chuyển cuộc trò chuyện cho dược sĩ (KTV12, AI04)")
async def gap_duoc_si(vao: GapDuocSiVao, db: Db, khach: KhachTuyChon):
    """Trong giờ làm việc: `cho_duoc_si`; ngoài giờ: `cho_goi_lai` kèm số điện thoại. Có tóm tắt AI04 cho dược sĩ."""
    return await chuyen_duoc_si.chuyen_cho_duoc_si(db, khach, vao.ma_phien, vao.so_dien_thoai)


@router.websocket("/ws")
async def chat_ws(websocket: WebSocket, ma_phien: uuid.UUID, tao_phien: Annotated[TaoPhien, Depends(lay_tao_phien)]):
    await ws.phuc_vu(websocket, ma_phien, tao_phien)

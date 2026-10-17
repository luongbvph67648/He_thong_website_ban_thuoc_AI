"""WebSocket chat dược sĩ (KTV12, DS06): `/api/v1/tu-van/ws?ma_phien=...`.

Xác thực bằng message đầu tiên `{loai: "xac_thuc", vai_tro: "khach" | "duoc_si", token?}` (token không đi trên URL để
khỏi lọt vào log), sau đó kiểm quyền vào phiên: khách vãng lai chứng minh bằng chính `ma_phien`, thành viên bằng token
`aud=khach`; dược sĩ cần token `aud=noi_bo`, quyền `chat.handle` và đúng là dược sĩ đã nhận phiên. Sau đó message JSON
`{loai: "tin_nhan", noi_dung}` hoặc `{loai: "dang_go"}`; server phát `{loai: "tin_nhan"|"dang_go"|"he_thong", ...}`.
"""

import asyncio
import logging
import time
import uuid
from collections import deque
from typing import Any, Protocol

from fastapi import WebSocketDisconnect
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from app.core.db import TaoPhien
from app.core.loi import LoiNghiepVu
from app.core.phan_quyen import MA_VAI_TRO_DUOC_SI, _khach_tu_token, _nhan_vien_tu_request, quyen_cua_vai_tro
from app.models.ai import HoiThoai
from app.models.enums import TrangThaiHoiThoai, TrangThaiTaiKhoan
from app.models.he_thong import NhanVien
from app.models.khach_hang import KhachHang
from app.modules.tu_van import chuyen_duoc_si, dich_vu
from app.modules.tu_van.hub import HUB

logger = logging.getLogger(__name__)
THOI_GIAN_XAC_THUC_GIAY = 10
MA_DONG_KHONG_HOP_LE = 4400
MA_DONG_CHUA_XAC_THUC = 4401
MA_DONG_KHONG_CO_QUYEN = 4403
MA_DONG_KHONG_TIM_THAY = 4404


class WebSocketLike(Protocol):
    async def accept(self) -> None: ...
    async def receive_json(self) -> Any: ...
    async def send_json(self, data: Any) -> None: ...
    async def close(self, code: int = 1000) -> None: ...


class XacThuc(BaseModel):
    loai: str
    vai_tro: str
    token: str | None = Field(default=None, max_length=4000)


class TinVao(BaseModel):
    loai: str
    noi_dung: str = Field(default="", max_length=1000, pattern=r"^[^\x00]*$")


async def _dinh_danh(db: Any, xt: XacThuc) -> tuple[str, KhachHang | NhanVien | None]:
    """Trả (vai_tro, tài khoản). Ném `LoiNghiepVu` khi token sai hoặc thiếu quyền."""
    if xt.vai_tro == "duoc_si":
        if not xt.token:
            raise LoiNghiepVu("CHUA_DANG_NHAP", "Bạn chưa đăng nhập")
        gia = Request({"type": "http", "method": "GET", "headers": [(b"authorization", f"Bearer {xt.token}".encode())]})
        nv = await _nhan_vien_tu_request(gia, db, ke_ca_chua_doi_mat_khau=False)
        if (await quyen_cua_vai_tro(db, nv.vai_tro_id)).get(
            "chat.handle"
        ) != "day_du" or nv.vai_tro.ma != MA_VAI_TRO_DUOC_SI:
            raise LoiNghiepVu("KHONG_CO_QUYEN", "Bạn không có quyền tư vấn trực tiếp")
        return "duoc_si", nv
    khach = await _khach_tu_token(xt.token, db) if xt.token else None
    return "khach", khach


async def _con_quyen_duoc_si(db: Any, nv_id: int) -> bool:
    """Kiểm lại MỖI tin: còn hoạt động, vẫn là dược sĩ và còn `chat.handle` đầy đủ (Admin vừa khóa hoặc gỡ quyền)."""
    nv = await db.get(NhanVien, nv_id, options=[selectinload(NhanVien.vai_tro)])
    if nv is None or nv.deleted_at is not None or nv.trang_thai != TrangThaiTaiKhoan.hoat_dong:
        return False
    if (await quyen_cua_vai_tro(db, nv.vai_tro_id)).get("chat.handle") != "day_du":
        return False
    return nv.vai_tro.ma == MA_VAI_TRO_DUOC_SI


class _CuaSoTin:
    """Tối đa `TOI_DA` tin trong `GIAY` giây trên một kết nối; vượt thì bỏ qua tin (không đóng kết nối)."""

    TOI_DA = 30
    GIAY = 60

    def __init__(self) -> None:
        self._luc: deque[float] = deque()

    def cho_phep(self) -> bool:
        bay_gio = time.monotonic()
        while self._luc and bay_gio - self._luc[0] > self.GIAY:
            self._luc.popleft()
        if len(self._luc) >= self.TOI_DA:
            return False
        self._luc.append(bay_gio)
        return True


async def phuc_vu(ws: WebSocketLike, ma_phien: uuid.UUID, tao_phien: TaoPhien) -> None:
    await ws.accept()
    try:
        xt = XacThuc.model_validate(await asyncio.wait_for(ws.receive_json(), timeout=THOI_GIAN_XAC_THUC_GIAY))
        if xt.loai != "xac_thuc" or xt.vai_tro not in ("khach", "duoc_si"):
            raise ValueError
    except (ValidationError, ValueError, TimeoutError, WebSocketDisconnect):
        await ws.close(MA_DONG_CHUA_XAC_THUC)
        return
    try:
        async with tao_phien() as db:
            vai_tro, tai_khoan = await _dinh_danh(db, xt)
            if vai_tro == "duoc_si":
                h = (await db.execute(HoiThoai.__table__.select().where(HoiThoai.ma_phien == ma_phien))).first()
                h = await db.get(HoiThoai, h.id) if h else None
                if h is None:
                    await ws.close(MA_DONG_KHONG_TIM_THAY)
                    return
                if h.duoc_si_id != tai_khoan.id or h.trang_thai != TrangThaiHoiThoai.duoc_si_dang_xu_ly:
                    await ws.close(MA_DONG_KHONG_CO_QUYEN)
                    return
            else:
                h = await dich_vu.tim_hoi_thoai(db, tai_khoan, ma_phien)  # phiên thành viên của người khác -> 404
                if h is None:
                    await ws.close(MA_DONG_KHONG_TIM_THAY)
                    return
            h_id, nv_id = h.id, tai_khoan.id if vai_tro == "duoc_si" and tai_khoan else None
    except LoiNghiepVu as loi:
        ma_dong = {"CHUA_DANG_NHAP": MA_DONG_CHUA_XAC_THUC, "TOKEN_HET_HAN": MA_DONG_CHUA_XAC_THUC}.get(
            loi.ma_loi, MA_DONG_KHONG_TIM_THAY if loi.ma_loi == "KHONG_TIM_THAY" else MA_DONG_KHONG_CO_QUYEN
        )
        await ws.close(ma_dong)
        return
    khoa = str(ma_phien)
    gioi_han = _CuaSoTin()
    HUB.vao(khoa, ws, vai_tro)
    try:
        await ws.send_json({"loai": "he_thong", "su_kien": "da_ket_noi"})
        while True:
            try:
                tin = TinVao.model_validate(await ws.receive_json())
            except ValidationError:
                await ws.send_json({"loai": "he_thong", "su_kien": "loi", "thong_diep": "Tin nhắn không hợp lệ"})
                continue
            if not gioi_han.cho_phep():
                await ws.send_json(
                    {"loai": "he_thong", "su_kien": "loi", "thong_diep": "Bạn nhắn quá nhanh, vui lòng chậm lại"}
                )
                continue
            if tin.loai == "dang_go":
                await HUB.phat(khoa, {"loai": "dang_go", "vai_tro": vai_tro}, tru=ws)
            elif tin.loai == "tin_nhan" and tin.noi_dung.strip():
                try:
                    async with tao_phien() as db:
                        if nv_id is not None and not await _con_quyen_duoc_si(db, nv_id):
                            await ws.close(MA_DONG_KHONG_CO_QUYEN)
                            return
                        su_kien = await chuyen_duoc_si.gui_tin(db, h_id, vai_tro, tin.noi_dung, nv_id)
                except LoiNghiepVu as loi:
                    await ws.send_json({"loai": "he_thong", "su_kien": "loi", "thong_diep": loi.thong_diep})
                    continue
                await HUB.phat(khoa, su_kien)
    except WebSocketDisconnect:
        pass
    finally:
        HUB.roi(khoa, ws)

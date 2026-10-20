"""Chat tư vấn AI (KVL05, T7.3): phiên, lưu tin nhắn, giới hạn ngân sách. Service nhận `db` (phiên ngắn)."""

import hashlib
import hmac
import uuid
from dataclasses import dataclass
from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import chatbot
from app.ai.claude import SuDung
from app.core.bao_mat import khoa_hmac
from app.core.config import settings
from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import VN_TZ, hom_nay_vn
from app.models.ai import DanhGiaCauTraLoi, HoiThoai, TinNhan
from app.models.enums import TrangThaiHoiThoai
from app.models.khach_hang import KhachHang
from app.modules.ai_quan_tri import cau_hinh_ai
from app.modules.tu_van.schemas import LichSuRa, TinNhanRa

TRANG_THAI_DUOC_SI = (
    TrangThaiHoiThoai.cho_duoc_si,
    TrangThaiHoiThoai.duoc_si_dang_xu_ly,
    TrangThaiHoiThoai.cho_goi_lai,
)


def _khong_thay() -> LoiNghiepVu:
    return LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy phiên tư vấn")


def bam_ip(ip: str) -> str:
    """Băm IP (HMAC) để lưu `ip_hash`: giới hạn lạm dụng mà không lưu địa chỉ rõ."""
    return hmac.new(khoa_hmac("ip_hoi_thoai"), ip.encode(), hashlib.sha256).hexdigest()


@dataclass
class DauVaoLuot:
    hoi_thoai_id: int
    tin_truoc: list[tuple[str, str]]
    ds_dau_hieu: list[str]
    nguong_chuyen: float
    loi_nhac: str
    chat_bat: bool
    het_ngan_sach: bool
    da_chuyen_duoc_si: bool


async def tim_hoi_thoai(
    db: AsyncSession, khach: KhachHang | None, ma_phien: uuid.UUID, *, khoa: bool = False
) -> HoiThoai | None:
    """Phiên theo mã. Phiên của thành viên chỉ chính họ mở được; người khác nhận 404 như không tồn tại."""
    cau = select(HoiThoai).where(HoiThoai.ma_phien == ma_phien)
    if khoa:
        cau = cau.with_for_update().execution_options(populate_existing=True)
    h = (await db.execute(cau)).scalar_one_or_none()
    if h is not None and h.khach_hang_id is not None and (khach is None or khach.id != h.khach_hang_id):
        raise _khong_thay()
    return h


async def chi_phi_hom_nay(db: AsyncSession) -> Decimal:
    dau_ngay = datetime.combine(hom_nay_vn(), time.min, tzinfo=VN_TZ)
    return await db.scalar(
        select(func.coalesce(func.sum(HoiThoai.chi_phi), 0)).where(HoiThoai.created_at >= dau_ngay)
    ) or Decimal(0)


async def mo_luot(db: AsyncSession, khach: KhachHang | None, ma_phien: uuid.UUID, noi_dung: str, ip: str) -> DauVaoLuot:
    """Tạo/nhận phiên, lưu tin nhắn của khách, đọc cấu hình AI. Gọi trong request (commit trước khi stream)."""
    h = await tim_hoi_thoai(db, khach, ma_phien, khoa=True)
    if h is None:
        h = HoiThoai(ma_phien=ma_phien, khach_hang_id=khach.id if khach else None, ip_hash=bam_ip(ip))
        db.add(h)
        await db.flush()
    elif h.trang_thai == TrangThaiHoiThoai.da_dong:
        raise LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Phiên tư vấn đã đóng, hãy bắt đầu cuộc trò chuyện mới")
    truoc = (
        await db.execute(
            select(TinNhan.vai_tro, TinNhan.noi_dung)
            .where(TinNhan.hoi_thoai_id == h.id, TinNhan.vai_tro.in_(("khach", "ai")))
            .order_by(TinNhan.id)
        )
    ).all()
    db.add(TinNhan(hoi_thoai_id=h.id, vai_tro="khach", noi_dung=noi_dung.strip()))
    await db.flush()
    cfg = await cau_hinh_ai.doc(db)
    return DauVaoLuot(
        hoi_thoai_id=h.id,
        tin_truoc=[(getattr(v, "value", v), nd) for v, nd in truoc],
        ds_dau_hieu=list(cfg["ai_dau_hieu_nguy_hiem"]),
        nguong_chuyen=float(cfg["ai_nguong_chuyen_duoc_si"]),
        loi_nhac=cfg["ai_loi_nhac_bo_sung"],
        chat_bat=bool(cfg["ai_module"].get("chat", True)),
        het_ngan_sach=await chi_phi_hom_nay(db) >= Decimal(str(settings.AI_NGAN_SACH_NGAY_USD)),
        da_chuyen_duoc_si=h.trang_thai in TRANG_THAI_DUOC_SI,
    )


async def cong_chi_phi(db: AsyncSession, hoi_thoai_id: int, su: SuDung) -> None:
    """Cộng token và chi phí của lượt bị gián đoạn (khách ngắt kết nối): không lưu tin nhắn vì khách không nhận được."""
    h = (
        await db.execute(
            select(HoiThoai)
            .where(HoiThoai.id == hoi_thoai_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    h.tong_token += su.tong_token
    h.chi_phi += su.chi_phi_usd()


async def luu_tra_loi(db: AsyncSession, hoi_thoai_id: int, kq: chatbot.KetQuaLuot) -> int:
    """Lưu tin nhắn của AI/hệ thống, cộng token và chi phí, gắn cờ khi có dấu hiệu nguy hiểm."""
    h = (
        await db.execute(
            select(HoiThoai)
            .where(HoiThoai.id == hoi_thoai_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    tin = TinNhan(
        hoi_thoai_id=h.id,
        vai_tro="ai",
        noi_dung=kq.noi_dung or "",
        y_dinh=kq.y_dinh,
        san_pham_goi_y=kq.san_pham_goi_y or None,
        dau_hieu_nguy_hiem=kq.nguy_hiem,
        so_token=kq.su_dung.tong_token or None,
    )
    db.add(tin)
    su: SuDung = kq.su_dung
    h.tong_token += su.tong_token
    h.chi_phi += su.chi_phi_usd()
    if kq.nguy_hiem:
        h.bi_gan_co, h.ly_do_gan_co = True, "dau_hieu_nguy_hiem"
    await db.flush()
    return tin.id


async def lich_su(db: AsyncSession, khach: KhachHang | None, ma_phien: uuid.UUID) -> LichSuRa:
    h = await tim_hoi_thoai(db, khach, ma_phien)
    if h is None:
        raise _khong_thay()
    ds = (
        await db.execute(
            select(TinNhan)
            .where(TinNhan.hoi_thoai_id == h.id, TinNhan.vai_tro != "he_thong")
            .order_by(TinNhan.id)
            .limit(200)
        )
    ).scalars()
    return LichSuRa(
        trang_thai=getattr(h.trang_thai, "value", h.trang_thai),
        tin_nhan=[
            TinNhanRa(
                id=t.id,
                vai_tro=getattr(t.vai_tro, "value", t.vai_tro),
                noi_dung=t.noi_dung,
                dau_hieu_nguy_hiem=t.dau_hieu_nguy_hiem,
                created_at=t.created_at,
            )
            for t in ds
        ],
    )


async def danh_gia(
    db: AsyncSession, khach: KhachHang | None, ma_phien: uuid.UUID, tin_nhan_id: int, ket_qua: str
) -> None:
    """Khách báo câu trả lời hữu ích/sai; mỗi khách (hoặc phiên vãng lai) một đánh giá cho mỗi tin."""
    h = await tim_hoi_thoai(db, khach, ma_phien)
    tin = await db.get(TinNhan, tin_nhan_id) if h else None
    if h is None or tin is None or tin.hoi_thoai_id != h.id or getattr(tin.vai_tro, "value", tin.vai_tro) != "ai":
        raise _khong_thay()
    cu = (
        (
            await db.execute(
                select(DanhGiaCauTraLoi)
                .where(DanhGiaCauTraLoi.tin_nhan_id == tin.id, DanhGiaCauTraLoi.nguon == "khach")
                .with_for_update()
            )
        )
        .scalars()
        .first()
    )
    if cu is not None:
        cu.ket_qua = ket_qua
    else:
        db.add(
            DanhGiaCauTraLoi(
                tin_nhan_id=tin.id, nguon="khach", ket_qua=ket_qua, khach_hang_id=khach.id if khach else None
            )
        )
    await db.flush()

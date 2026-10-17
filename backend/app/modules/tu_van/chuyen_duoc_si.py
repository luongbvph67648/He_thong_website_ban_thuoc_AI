"""Chuyển dược sĩ và chat trực tiếp (T7.4): AI04, KTV12, DS06. Không commit.

Trạng thái hội thoại (spec 04 mục 1.6): dang_mo -> cho_duoc_si | cho_goi_lai -> duoc_si_dang_xu_ly -> da_dong.
"""

import uuid
from datetime import datetime, time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import tom_tat
from app.ai.claude import SuDung
from app.core.dien_thoai import chuan_hoa_sdt
from app.core.loi import LoiNghiepVu
from app.core.phan_quyen import MA_VAI_TRO_DUOC_SI
from app.core.thoi_gian import VN_TZ, bay_gio_utc
from app.models.ai import HoiThoai, TinNhan
from app.models.enums import TrangThaiHoiThoai, TrangThaiTaiKhoan
from app.models.he_thong import NhanVien, VaiTro
from app.models.khach_hang import KhachHang
from app.modules.ai_quan_tri import cau_hinh_ai
from app.modules.suc_khoe import dich_vu as suc_khoe
from app.modules.thong_bao import service as thong_bao
from app.modules.tu_van import dich_vu
from app.modules.tu_van.hub import HUB
from app.modules.tu_van.schemas import (
    ChatChiTiet,
    ChatTomTat,
    GapDuocSiRa,
    HoSoTomLuoc,
    TinNhanRa,
)

TT = TrangThaiHoiThoai
TRANG_THAI_CHAT_DUOC = (TT.cho_duoc_si, TT.duoc_si_dang_xu_ly)
"""Hai trạng thái cho phép trao đổi tin nhắn giữa khách và dược sĩ."""
MAC_DINH_GIO_LAM_VIEC = {"bat_dau": "08:00", "ket_thuc": "21:00", "ngay_trong_tuan": [1, 2, 3, 4, 5, 6, 7]}
THONG_DIEP_TRONG_GIO = (
    "Đã chuyển cho dược sĩ. Bạn vui lòng chờ trong giây lát, dược sĩ sẽ trả lời ngay trong khung chat này."
)
THONG_DIEP_NGOAI_GIO = "Hiện ngoài giờ làm việc của dược sĩ. Nhà thuốc sẽ gọi lại cho bạn vào giờ làm việc tiếp theo."


def _gio(chuoi: str, mac_dinh: time) -> time:
    try:
        h, p = chuoi.split(":")
        return time(int(h), int(p))
    except (ValueError, AttributeError):
        return mac_dinh


async def trong_gio_lam_viec(db: AsyncSession, luc: datetime | None = None) -> bool:
    """Giờ VN của `luc` (mặc định bây giờ) nằm trong khung `gio_lam_viec_duoc_si` và đúng ngày làm việc."""
    from app.core.cau_hinh import doc_cau_hinh

    cfg: dict[str, Any] = await doc_cau_hinh(db, "gio_lam_viec_duoc_si", MAC_DINH_GIO_LAM_VIEC)
    gio_vn = (luc or bay_gio_utc()).astimezone(VN_TZ)
    if gio_vn.isoweekday() not in cfg.get("ngay_trong_tuan", [1, 2, 3, 4, 5, 6, 7]):
        return False
    bat_dau = _gio(cfg.get("bat_dau", "08:00"), time(8, 0))
    ket_thuc = _gio(cfg.get("ket_thuc", "21:00"), time(21, 0))
    return bat_dau <= gio_vn.time() < ket_thuc


async def _ids_duoc_si(db: AsyncSession) -> list[int]:
    return list(
        (
            await db.execute(
                select(NhanVien.id)
                .join(VaiTro, VaiTro.id == NhanVien.vai_tro_id)
                .where(
                    VaiTro.ma == MA_VAI_TRO_DUOC_SI,
                    NhanVien.trang_thai == TrangThaiTaiKhoan.hoat_dong,
                    NhanVien.deleted_at.is_(None),
                )
            )
        ).scalars()
    )


# --- KTV12 / AI04: khách bấm "Gặp dược sĩ" ---


async def chuyen_cho_duoc_si(
    db: AsyncSession, khach: KhachHang | None, ma_phien: uuid.UUID, so_dien_thoai: str | None
) -> GapDuocSiRa:
    h = await dich_vu.tim_hoi_thoai(db, khach, ma_phien, khoa=True)
    if h is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy phiên tư vấn")
    if h.trang_thai in (TT.cho_duoc_si, TT.cho_goi_lai, TT.duoc_si_dang_xu_ly):
        return GapDuocSiRa(  # bấm lại không tạo thêm: trả đúng trạng thái hiện tại
            trang_thai=TT.cho_duoc_si if h.trang_thai != TT.cho_goi_lai else TT.cho_goi_lai,
            trong_gio=h.trang_thai != TT.cho_goi_lai,
            thong_diep=THONG_DIEP_NGOAI_GIO if h.trang_thai == TT.cho_goi_lai else THONG_DIEP_TRONG_GIO,
        )
    if h.trang_thai == TT.da_dong:
        raise LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Phiên tư vấn đã đóng")
    trong_gio = await trong_gio_lam_viec(db)
    sdt = None
    if not trong_gio:
        goc = so_dien_thoai or (khach.so_dien_thoai if khach else None)
        try:
            sdt = chuan_hoa_sdt(goc)
        except ValueError as e:
            raise LoiNghiepVu(
                "DU_LIEU_KHONG_HOP_LE",
                "Dữ liệu không hợp lệ",
                chi_tiet=[
                    {"truong": "so_dien_thoai", "loi": "Ngoài giờ làm việc cần số điện thoại để dược sĩ gọi lại"}
                ],
            ) from e
    tin = [
        (getattr(v, "value", v), nd)
        for v, nd in (
            await db.execute(
                select(TinNhan.vai_tro, TinNhan.noi_dung)
                .where(TinNhan.hoi_thoai_id == h.id, TinNhan.vai_tro.in_(("khach", "ai")))
                .order_by(TinNhan.id)
            )
        ).all()
    ]
    su_dung = SuDung()
    h.tom_tat = await tom_tat.tom_tat_hoi_thoai(tin, su_dung, ai_bat=await cau_hinh_ai.module_bat(db, "chat"))
    h.tong_token += su_dung.tong_token
    h.chi_phi += su_dung.chi_phi_usd()
    h.trang_thai = TT.cho_duoc_si if trong_gio else TT.cho_goi_lai
    h.loai = (
        "duoc_si"  # từ lúc khách chuyển: dùng để thống kê tỉ lệ chuyển dược sĩ (AD11), kể cả phiên đóng sau khi gọi lại
    )
    h.so_dien_thoai_goi_lai = sdt
    db.add(
        TinNhan(
            hoi_thoai_id=h.id,
            vai_tro="he_thong",
            noi_dung=THONG_DIEP_TRONG_GIO if trong_gio else THONG_DIEP_NGOAI_GIO,
        )
    )
    await db.flush()
    for nv_id in await _ids_duoc_si(db):
        await thong_bao.gui_cho_nhan_vien(
            db,
            nv_id,
            loai="chat_cho_duoc_si" if trong_gio else "chat_cho_goi_lai",
            tieu_de="Có khách chờ tư vấn" if trong_gio else "Có khách cần gọi lại",
            noi_dung=(h.tom_tat or "")[:300] or None,
            lien_ket="/nhan-vien/tu-van",
        )
    return GapDuocSiRa(
        trang_thai=h.trang_thai.value if hasattr(h.trang_thai, "value") else h.trang_thai,
        trong_gio=trong_gio,
        thong_diep=THONG_DIEP_TRONG_GIO if trong_gio else THONG_DIEP_NGOAI_GIO,
    )


# --- DS06: dược sĩ ---


def _tt(x: Any) -> str:
    return x.value if hasattr(x, "value") else x


async def dam_bao_duoc_si(db: AsyncSession, nv: NhanVien) -> None:
    if await db.scalar(select(VaiTro.ma).where(VaiTro.id == nv.vai_tro_id)) != MA_VAI_TRO_DUOC_SI:
        raise LoiNghiepVu("KHONG_CO_QUYEN", "Chỉ dược sĩ mới tư vấn trực tiếp")


def _tom_tat(h: HoiThoai, ten: str | None, nv: NhanVien) -> ChatTomTat:
    return ChatTomTat(
        id=h.id,
        ma_phien=h.ma_phien,
        trang_thai=_tt(h.trang_thai),
        tom_tat=h.tom_tat,
        ten_khach=ten,
        so_dien_thoai_goi_lai=h.so_dien_thoai_goi_lai,
        bi_gan_co=h.bi_gan_co,
        duoc_si_cua_toi=h.duoc_si_id == nv.id,
        created_at=h.created_at,
    )


async def hang_cho(db: AsyncSession, nv: NhanVien) -> list[ChatTomTat]:
    """Phiên chờ dược sĩ và chờ gọi lại (mọi dược sĩ thấy), cộng phiên đang xử lý của chính mình."""
    await dam_bao_duoc_si(db, nv)
    ds = (
        await db.execute(
            select(HoiThoai, KhachHang.ho_ten)
            .outerjoin(KhachHang, KhachHang.id == HoiThoai.khach_hang_id)
            .where(
                (HoiThoai.trang_thai.in_((TT.cho_duoc_si, TT.cho_goi_lai)))
                | ((HoiThoai.trang_thai == TT.duoc_si_dang_xu_ly) & (HoiThoai.duoc_si_id == nv.id))
            )
            .order_by(HoiThoai.created_at, HoiThoai.id)
            .limit(200)
        )
    ).all()
    return [_tom_tat(h, ten, nv) for h, ten in ds]


async def _lay(db: AsyncSession, hoi_thoai_id: int, *, khoa: bool = False) -> HoiThoai:
    cau = select(HoiThoai).where(HoiThoai.id == hoi_thoai_id)
    if khoa:
        cau = cau.with_for_update().execution_options(populate_existing=True)
    h = (await db.execute(cau)).scalar_one_or_none()
    if h is None or h.trang_thai == TT.dang_mo:  # phiên còn đang trò chuyện với AI không thuộc hàng chờ dược sĩ
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy phiên tư vấn")
    return h


async def chi_tiet(db: AsyncSession, nv: NhanVien, hoi_thoai_id: int) -> ChatChiTiet:
    await dam_bao_duoc_si(db, nv)
    h = await _lay(db, hoi_thoai_id)
    # Chỉ đọc phiên đang chờ (để nhận), phiên của chính mình; phiên khác (kể cả đã đóng) là 404 như không tồn tại.
    # Hội thoại bị gắn cờ xem ở DS12 (đã ẩn danh), không qua đây.
    if h.trang_thai not in (TT.cho_duoc_si, TT.cho_goi_lai) and h.duoc_si_id != nv.id:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy phiên tư vấn")
    ten = await db.scalar(select(KhachHang.ho_ten).where(KhachHang.id == h.khach_hang_id)) if h.khach_hang_id else None
    tin = (
        (await db.execute(select(TinNhan).where(TinNhan.hoi_thoai_id == h.id).order_by(TinNhan.id).limit(300)))
        .scalars()
        .all()
    )
    ho_so = None
    dang_xu_ly = h.khach_hang_id is not None and h.duoc_si_id == nv.id and h.trang_thai == TT.duoc_si_dang_xu_ly
    if dang_xu_ly and await suc_khoe.duoc_doc_ho_so_suc_khoe(db, nv, h.khach_hang_id):  # hàm cổng: đồng ý + nhật ký
        r = await suc_khoe.dung_ho_so(db, h.khach_hang_id)
        ho_so = HoSoTomLuoc(
            nam_sinh=r.nam_sinh,
            dang_mang_thai=r.dang_mang_thai,
            dang_cho_con_bu=r.dang_cho_con_bu,
            di_ung=[d.ten_hoat_chat for d in r.di_ung],
        )
    return ChatChiTiet(
        **_tom_tat(h, ten, nv).model_dump(),
        tin_nhan=[
            TinNhanRa(
                id=t.id,
                vai_tro=_tt(t.vai_tro),
                noi_dung=t.noi_dung,
                dau_hieu_nguy_hiem=t.dau_hieu_nguy_hiem,
                created_at=t.created_at,
            )
            for t in tin
        ],
        ho_so_suc_khoe=ho_so,
    )


async def nhan_phien(db: AsyncSession, nv: NhanVien, hoi_thoai_id: int) -> ChatChiTiet:
    """Dòng 4: `cho_duoc_si -> duoc_si_dang_xu_ly`. Hai dược sĩ cùng bấm: người sau nhận `409`."""
    await dam_bao_duoc_si(db, nv)
    h = await _lay(db, hoi_thoai_id, khoa=True)
    if h.trang_thai != TT.cho_duoc_si:
        raise LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Phiên này không còn ở hàng chờ")
    h.trang_thai, h.duoc_si_id, h.loai = TT.duoc_si_dang_xu_ly, nv.id, "duoc_si"
    db.add(TinNhan(hoi_thoai_id=h.id, vai_tro="he_thong", noi_dung=f"Dược sĩ {nv.ho_ten} đã tham gia cuộc trò chuyện."))
    await db.flush()
    await HUB.phat(str(h.ma_phien), {"loai": "he_thong", "su_kien": "duoc_si_vao", "ten": nv.ho_ten})
    return await chi_tiet(db, nv, hoi_thoai_id)


async def dong_phien(db: AsyncSession, nv: NhanVien, hoi_thoai_id: int) -> ChatChiTiet:
    """Dòng 5: kết thúc tư vấn hoặc đã gọi lại. Chỉ dược sĩ đang xử lý, hoặc bất kỳ dược sĩ với phiên chờ gọi lại."""
    await dam_bao_duoc_si(db, nv)
    h = await _lay(db, hoi_thoai_id, khoa=True)
    hop_le = (h.trang_thai == TT.duoc_si_dang_xu_ly and h.duoc_si_id == nv.id) or h.trang_thai == TT.cho_goi_lai
    if not hop_le:
        raise LoiNghiepVu(
            "CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Chỉ đóng được phiên mình đang xử lý hoặc phiên chờ gọi lại"
        )
    h.trang_thai, h.dong_luc = TT.da_dong, bay_gio_utc()
    h.duoc_si_id = h.duoc_si_id or nv.id
    db.add(TinNhan(hoi_thoai_id=h.id, vai_tro="he_thong", noi_dung="Cuộc tư vấn đã kết thúc."))
    await db.flush()
    await HUB.phat(str(h.ma_phien), {"loai": "he_thong", "su_kien": "da_dong"})
    return await chi_tiet(db, nv, hoi_thoai_id)


# --- Tin nhắn trực tiếp (REST dự phòng và WebSocket dùng chung) ---


async def gui_tin(
    db: AsyncSession, h_id: int, vai_tro: str, noi_dung: str, nhan_vien_id: int | None = None
) -> dict[str, Any]:
    """Lưu một tin khách/dược sĩ nếu phiên đang cho phép trao đổi; trả sự kiện để phát cho phòng."""
    h = await _lay(db, h_id, khoa=True)
    if h.trang_thai not in TRANG_THAI_CHAT_DUOC:
        raise LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Phiên không ở trạng thái trò chuyện trực tiếp")
    if vai_tro == "duoc_si" and (h.trang_thai != TT.duoc_si_dang_xu_ly or h.duoc_si_id != nhan_vien_id):
        raise LoiNghiepVu("KHONG_CO_QUYEN", "Bạn không phải dược sĩ đang xử lý phiên này")
    tin = TinNhan(hoi_thoai_id=h.id, vai_tro=vai_tro, noi_dung=noi_dung.strip(), nhan_vien_id=nhan_vien_id)
    db.add(tin)
    await db.flush()
    await db.refresh(tin)
    return {
        "loai": "tin_nhan",
        "id": tin.id,
        "vai_tro": vai_tro,
        "noi_dung": tin.noi_dung,
        "luc": tin.created_at.isoformat(),
    }


# --- HT08 ---

DONG_SAU_PHUT = {TT.dang_mo: 30, TT.duoc_si_dang_xu_ly: 120}
"""Phiên không có tin nhắn mới quá ngần này phút thì đóng (dòng 6; dược sĩ quên đóng thì sau 2 giờ)."""


async def dong_phien_khong_hoat_dong(db: AsyncSession) -> list[int]:
    from datetime import timedelta

    from sqlalchemy import func

    bay_gio = bay_gio_utc()
    da_dong: list[int] = []
    for trang_thai, phut in DONG_SAU_PHUT.items():
        han = bay_gio - timedelta(minutes=phut)
        moi_nhat = func.coalesce(
            select(func.max(TinNhan.created_at))
            .where(TinNhan.hoi_thoai_id == HoiThoai.id)
            .correlate(HoiThoai)
            .scalar_subquery(),
            HoiThoai.created_at,
        )
        ids = (
            (
                await db.execute(
                    select(HoiThoai.id)
                    .where(HoiThoai.trang_thai == trang_thai, moi_nhat < han)
                    .with_for_update(skip_locked=True)
                )
            )
            .scalars()
            .all()
        )
        for h_id in ids:
            h = await db.get(HoiThoai, h_id, populate_existing=True)
            if h is None or h.trang_thai != trang_thai:
                continue
            h.trang_thai, h.dong_luc = TT.da_dong, bay_gio
            da_dong.append(h.id)
            await HUB.phat(str(h.ma_phien), {"loai": "he_thong", "su_kien": "da_dong"})
    await db.flush()
    return da_dong


async def ma_phien_cua(db: AsyncSession, hoi_thoai_id: int) -> uuid.UUID:
    return (await _lay(db, hoi_thoai_id)).ma_phien

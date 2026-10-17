"""AI06 (job nền): đọc ảnh yêu cầu đơn thuốc mới → `ket_qua_ai` và `ct_yeu_cau_don_thuoc` (chỉ gợi ý, spec 04 mục 6).

Mỗi yêu cầu chỉ ghi dòng thuốc khi CHƯA có dòng nào (dược sĩ có thể đã nhập tay). AI lỗi thì ghi dấu `loi` và thử lại
tối đa `SO_LAN_THU` lần; bị từ chối thì không thử lại. Dược sĩ vẫn duyệt bình thường khi không có kết quả AI."""

import logging
from dataclasses import dataclass, field
from decimal import Decimal

from pydantic import ValidationError
from sqlalchemy import Integer, cast, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import claude
from app.ai.anh import AnhKhongDoc, chuan_bi_anh
from app.ai.doc_don_thuoc import DonThuocDoc, doc_don_thuoc
from app.core import luu_tru
from app.core.thoi_gian import bay_gio_utc
from app.models.ban_hang import CtYeuCauDonThuoc, YeuCauDonThuoc
from app.models.enums import TrangThaiKinhDoanh, TrangThaiYeuCauDonThuoc
from app.models.san_pham import SanPham, ThanhPhan
from app.modules.ai_quan_tri import cau_hinh_ai
from app.modules.cua_hang.tim_kiem import chuan_hoa_tu_khoa, diem_khop_ten

logger = logging.getLogger(__name__)

SO_LAN_THU = 3
SO_YEU_CAU_MOI_LAN = 3
NGUONG_GOI_Y = 0.6
NGUONG_GOI_Y_KHONG_HAM_LUONG = 0.8
"""Không khớp được hàm lượng thì chỉ gợi ý khi tên gần như trùng hẳn."""
TRANG_THAI_CAN_DOC = (TrangThaiYeuCauDonThuoc.cho_duyet, TrangThaiYeuCauDonThuoc.dang_tu_van)


@dataclass
class KetQuaAi06:
    da_doc: list[str] = field(default_factory=list)
    loi: list[str] = field(default_factory=list)


def _chuan_ham_luong(v: str | None) -> str:
    return "".join((v or "").lower().split())


async def goi_y_san_pham(db: AsyncSession, ten: str, ham_luong: str | None) -> int | None:
    """Sản phẩm gợi ý cho một dòng trên đơn: ưu tiên khớp hàm lượng thành phần, không thì chỉ khi tên gần như trùng."""
    q = chuan_hoa_tu_khoa(ten)
    if len(q) < 2:
        return None
    diem = diem_khop_ten(q)
    ung_vien = (
        await db.execute(
            select(SanPham.id, diem.label("d"))
            .where(
                SanPham.deleted_at.is_(None),
                SanPham.trang_thai == TrangThaiKinhDoanh.dang_kinh_doanh,
                diem >= NGUONG_GOI_Y,
            )
            .order_by(diem.desc(), SanPham.id)
            .limit(5)
        )
    ).all()
    if not ung_vien:
        return None
    hl = _chuan_ham_luong(ham_luong)
    if hl:
        cac_ham_luong = (
            await db.execute(
                select(ThanhPhan.san_pham_id, ThanhPhan.ham_luong).where(
                    ThanhPhan.san_pham_id.in_([u.id for u in ung_vien]), ThanhPhan.ham_luong.is_not(None)
                )
            )
        ).all()
        khop = {sp for sp, v in cac_ham_luong if _chuan_ham_luong(v) == hl}
        for u in ung_vien:
            if u.id in khop:
                return u.id
    return ung_vien[0].id if ung_vien[0].d >= NGUONG_GOI_Y_KHONG_HAM_LUONG else None


async def _anh_b64(yc: YeuCauDonThuoc) -> list[str]:
    ra: list[str] = []
    kho = luu_tru.luu_tru()
    for khoa in yc.anh_don_thuoc or []:
        noi_dung = await kho.doc(khoa, "rieng_tu")
        if noi_dung is None:
            continue
        try:
            ra.append(chuan_bi_anh(noi_dung))
        except AnhKhongDoc:
            logger.warning("AI06: ảnh %s của %s không đọc được", khoa, yc.ma_yeu_cau)
    return ra


def _json_ket_qua(doc: DonThuocDoc) -> dict:
    return {
        "trang_thai": "xong",
        "doc_luc": bay_gio_utc().isoformat(),
        "ngay_ke": doc.ngay_ke.isoformat() if doc.ngay_ke else None,
        "co_chu_ky_bac_si": doc.co_chu_ky_bac_si,
        "danh_sach_thuoc": [t.model_dump() for t in doc.danh_sach_thuoc],
    }


@dataclass
class _KetQuaDoc:
    """Kết quả đọc một yêu cầu, tính XONG trước khi đụng khóa dòng nào."""

    yc_id: int
    ma: str
    doc: DonThuocDoc | None
    ly_do: str | None
    lan: int


async def _doc_ai(yc: YeuCauDonThuoc, su_dung: claude.SuDung) -> _KetQuaDoc:
    """Chỉ đọc tệp và gọi Claude, không ghi CSDL (không giữ khóa dòng trong lúc chờ AI, có thể hàng chục giây)."""
    lan = int((yc.ket_qua_ai or {}).get("lan_thu", 0)) + 1
    ds_anh = await _anh_b64(yc)
    if not ds_anh:
        return _KetQuaDoc(yc.id, yc.ma_yeu_cau, None, "anh_hong", SO_LAN_THU)
    try:
        return _KetQuaDoc(yc.id, yc.ma_yeu_cau, await doc_don_thuoc(ds_anh, su_dung), None, lan)
    except claude.AiTuChoi:
        return _KetQuaDoc(yc.id, yc.ma_yeu_cau, None, "ai_tu_choi", SO_LAN_THU)
    except (claude.AiLoi, ValidationError) as e:
        logger.warning("AI06 lỗi với %s (lần %s): %s", yc.ma_yeu_cau, lan, type(e).__name__)
        return _KetQuaDoc(yc.id, yc.ma_yeu_cau, None, "ai_loi", lan)


def _can_doc(yc: YeuCauDonThuoc) -> bool:
    kq = yc.ket_qua_ai
    chua = kq is None or (
        isinstance(kq, dict) and kq.get("trang_thai") == "loi" and int(kq.get("lan_thu", 0)) < SO_LAN_THU
    )
    return chua and yc.trang_thai in TRANG_THAI_CAN_DOC


async def _ghi(db: AsyncSession, kq: _KetQuaDoc) -> bool:
    """Ghi kết quả trong thời gian khóa ngắn; bỏ qua nếu trong lúc chờ AI yêu cầu đã đổi (dược sĩ từ chối, đã đọc)."""
    yc = (
        await db.execute(
            select(YeuCauDonThuoc)
            .where(YeuCauDonThuoc.id == kq.yc_id)
            .with_for_update(skip_locked=True)
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if yc is None or not _can_doc(yc):
        return False
    if kq.doc is None:
        yc.ket_qua_ai = {"trang_thai": "loi", "ly_do": kq.ly_do, "lan_thu": kq.lan}
        await db.flush()
        return False
    doc = kq.doc
    yc.ket_qua_ai = _json_ket_qua(doc)
    co_dong = await db.scalar(select(exists().where(CtYeuCauDonThuoc.yeu_cau_id == yc.id)))
    if not co_dong:
        for t in doc.danh_sach_thuoc:
            db.add(
                CtYeuCauDonThuoc(
                    yeu_cau_id=yc.id,
                    san_pham_id=await goi_y_san_pham(db, t.ten_thuoc_tren_don, t.ham_luong),
                    ten_thuoc_tren_don=t.ten_thuoc_tren_don,
                    ham_luong=t.ham_luong,
                    so_luong_ke=t.so_luong_ke,
                    do_tin_cay_ai=Decimal(str(round(t.do_tin_cay, 3))),
                    do_duoc_si_nhap=False,
                )
            )
    yc.updated_at = bay_gio_utc()
    await db.flush()
    return True


async def doc_don_thuoc_moi(db: AsyncSession) -> KetQuaAi06:
    """AI06: lấy tối đa `SO_YEU_CAU_MOI_LAN` yêu cầu chưa đọc. Ba pha: chọn (không khóa dòng; `chay_job` đã bảo đảm một
    tiến trình), gọi AI từng yêu cầu, rồi ghi tất cả trong thời gian khóa ngắn."""
    ket_qua = KetQuaAi06()
    if not await cau_hinh_ai.module_bat(db, "doc_don_thuoc"):
        return ket_qua
    trang_thai_ai = YeuCauDonThuoc.ket_qua_ai["trang_thai"].astext
    lan_thu = func.coalesce(cast(YeuCauDonThuoc.ket_qua_ai["lan_thu"].astext, Integer), 0)
    ds = (
        (
            await db.execute(
                select(YeuCauDonThuoc)
                .where(
                    YeuCauDonThuoc.trang_thai.in_(TRANG_THAI_CAN_DOC),
                    or_(YeuCauDonThuoc.ket_qua_ai.is_(None), (trang_thai_ai == "loi") & (lan_thu < SO_LAN_THU)),
                )
                .order_by(YeuCauDonThuoc.created_at)
                .limit(SO_YEU_CAU_MOI_LAN)
            )
        )
        .scalars()
        .all()
    )
    da_doc: list[_KetQuaDoc] = []
    for yc in ds:
        su_dung = claude.SuDung()
        da_doc.append(await _doc_ai(yc, su_dung))
        logger.info(
            "AI06 %s", yc.ma_yeu_cau, extra={"token": su_dung.tong_token, "chi_phi_usd": str(su_dung.chi_phi_usd())}
        )
    for kq in da_doc:
        ok = await _ghi(db, kq)
        (ket_qua.da_doc if ok else ket_qua.loi).append(kq.ma)
    return ket_qua

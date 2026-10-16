"""KVL06: đối chiếu thông tin AI05 đọc được với CSDL (SĐK đã chuẩn hóa trước, rồi tên theo trigram)."""

import re

from sqlalchemy import ColumnElement, Text, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.doc_anh import HopThuocDoc
from app.models.enums import LoaiSanPham, TrangThaiNoiDung
from app.models.san_pham import SanPham, ThongTinChuyenMon
from app.modules.cua_hang.danh_sach import chon_the, dung_the
from app.modules.cua_hang.hien_thi import la_hien_thi, nap_cay_hien_thi
from app.modules.tra_cuu_anh.schemas import KhopSanPham, TomTatSanPham, TraCuuAnhRa

NGUONG_TEN = 0.5
SDK_TOI_THIEU = 5
"""SĐK ngắn hơn thế (ví dụ "VD") đọc thiếu, khớp sẽ nhầm sản phẩm."""
DO_TIN_CAY_THAP = 0.5
TOI_DA_TOM_TAT = 300

CB_CHUA_XAC_MINH = (
    "Chưa xác minh: sản phẩm này không có trong hệ thống nhà thuốc. Thông tin trên chỉ là những gì đọc được từ ảnh, "
    "hãy đối chiếu với bao bì hoặc hỏi dược sĩ."
)
CB_KHONG_DOC_DUOC = (
    "Không nhận ra thông tin thuốc trong ảnh. Hãy chụp rõ mặt hộp có tên thuốc và số đăng ký, đủ sáng và không bị lóa."
)
CB_DO_TIN_CAY_THAP = "Ảnh chưa thật rõ nên kết quả có thể chưa chính xác, hãy đối chiếu với bao bì."
CB_KHOP_THEO_TEN = "Khớp theo tên (chưa đối chiếu được số đăng ký), hãy kiểm tra hàm lượng và dạng bào chế trên bao bì."
CB_KE_DON = "Đây là thuốc kê đơn: chỉ dùng khi có chỉ định của bác sĩ. Vui lòng hỏi dược sĩ trước khi dùng."


def chuan_sdk(sdk: str | None) -> str:
    """Bỏ khoảng trắng và gạch, viết hoa (spec 07 mục 6)."""
    return re.sub(r"[\s\-]", "", sdk or "").upper()


def _cot_sdk() -> ColumnElement:
    return func.upper(func.regexp_replace(SanPham.so_dang_ky, r"[\s\-]", "", "g"))


def _chuan(cot: ColumnElement) -> ColumnElement:
    return func.f_unaccent(func.lower(cot))


def _cat(van_ban: str | None) -> str | None:
    if not van_ban or not van_ban.strip():
        return None
    v = " ".join(van_ban.split())
    return v if len(v) <= TOI_DA_TOM_TAT else v[: TOI_DA_TOM_TAT - 1].rstrip() + "…"


async def _tom_tat(db: AsyncSession, san_pham_id: int) -> TomTatSanPham | None:
    ban = (
        await db.execute(
            select(ThongTinChuyenMon)
            .where(
                ThongTinChuyenMon.san_pham_id == san_pham_id, ThongTinChuyenMon.trang_thai == TrangThaiNoiDung.da_duyet
            )
            .order_by(ThongTinChuyenMon.phien_ban.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if ban is None:
        return None
    tt = TomTatSanPham(
        chi_dinh=_cat(ban.chi_dinh), chong_chi_dinh=_cat(ban.chong_chi_dinh), than_trong=_cat(ban.than_trong)
    )
    return tt if (tt.chi_dinh or tt.chong_chi_dinh or tt.than_trong) else None


async def tim_khop(db: AsyncSession, doc: HopThuocDoc) -> tuple[int, str] | None:
    """(id sản phẩm hiển thị với khách, cách khớp) hoặc `None`."""
    cay = await nap_cay_hien_thi(db)
    hien_thi = la_hien_thi(cay.ids)
    sdk = chuan_sdk(doc.so_dang_ky)
    if len(sdk) >= SDK_TOI_THIEU:
        sp_id = await db.scalar(select(SanPham.id).where(hien_thi, _cot_sdk() == sdk).order_by(SanPham.id).limit(1))
        if sp_id is not None:
            return sp_id, "so_dang_ky"
    ten = (doc.ten_san_pham or "").strip()
    if ten:
        diem = func.similarity(_chuan(SanPham.ten), _chuan(literal(ten, type_=Text)))
        hang = (
            await db.execute(
                select(SanPham.id, diem.label("d"))
                .where(hien_thi, diem >= NGUONG_TEN)
                .order_by(diem.desc(), SanPham.id)
                .limit(1)
            )
        ).first()
        if hang is not None:
            return hang.id, "ten"
    return None


async def doi_chieu(db: AsyncSession, doc: HopThuocDoc) -> TraCuuAnhRa:
    if not doc.co_thong_tin():
        return TraCuuAnhRa(doc_duoc=doc, khop=None, da_xac_minh=False, canh_bao=CB_KHONG_DOC_DUOC)
    khop = await tim_khop(db, doc)
    if khop is None:
        return TraCuuAnhRa(doc_duoc=doc, khop=None, da_xac_minh=False, canh_bao=CB_CHUA_XAC_MINH)
    sp_id, cach = khop
    dong = (await db.execute(chon_the().where(SanPham.id == sp_id))).all()
    (the,) = await dung_the(db, dong)
    ke_don = the.loai_san_pham == LoaiSanPham.thuoc_ke_don
    canh_bao = [CB_KE_DON] if ke_don else []
    if cach == "ten":
        canh_bao.append(CB_KHOP_THEO_TEN)
    if doc.do_tin_cay < DO_TIN_CAY_THAP:
        canh_bao.append(CB_DO_TIN_CAY_THAP)
    return TraCuuAnhRa(
        doc_duoc=doc,
        khop=KhopSanPham(
            cach=cach, san_pham=the, la_thuoc_ke_don=ke_don, tom_tat=None if ke_don else await _tom_tat(db, sp_id)
        ),
        da_xac_minh=True,
        canh_bao=" ".join(canh_bao) or None,
    )

"""Yêu cầu tư vấn đơn thuốc phía khách (KVL08, KTV07, T5.2). Không commit.

Ảnh đơn nằm ở vùng lưu trữ riêng tư; DB chỉ giữ khóa file (jsonb `anh_don_thuoc`). `hash_anh` là SHA-256 của ảnh
(nhiều ảnh: SHA-256 của các hash đã sắp xếp) để T5.3 cảnh báo đơn đã dùng. Dược sĩ xử lý yêu cầu ở T5.3.
"""

import hashlib
import secrets
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import luu_tru
from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc
from app.models.ban_hang import DonHang, YeuCauDonThuoc
from app.models.enums import KenhBan, TrangThaiYeuCauDonThuoc
from app.models.khach_hang import KhachHang
from app.modules.don_thuoc.schemas import YeuCauDonThuocChiTiet, YeuCauDonThuocTao, YeuCauDonThuocTom

SO_ANH_TOI_DA = 5
SO_YEU_CAU_TOI_DA_MOI_SDT_NGAY = 5
"""Giới hạn số yêu cầu mỗi SĐT trong 24 giờ để chống spam (KVL08)."""
CHO_PHEP_HUY = (TrangThaiYeuCauDonThuoc.cho_duyet, TrangThaiYeuCauDonThuoc.dang_tu_van)


def _loi_anh(thong_diep: str) -> LoiNghiepVu:
    return LoiNghiepVu("DU_LIEU_KHONG_HOP_LE", thong_diep, chi_tiet=[{"truong": "anh", "loi": thong_diep}])


def kiem_tra_anh(ds_anh: list[bytes]) -> list[str]:
    """Kiểu MIME thật của từng ảnh. Số ảnh 1..5, mỗi ảnh jpeg/png/webp tối đa 5 MB."""
    if not ds_anh:
        raise _loi_anh("Cần ít nhất một ảnh đơn thuốc")
    if len(ds_anh) > SO_ANH_TOI_DA:
        raise _loi_anh(f"Tối đa {SO_ANH_TOI_DA} ảnh")
    kieu = []
    for noi_dung in ds_anh:
        if len(noi_dung) > luu_tru.TOI_DA_ANH_BYTE:
            raise _loi_anh("Mỗi ảnh tối đa 5 MB")
        k = luu_tru.nhan_dang_anh(noi_dung)
        if k is None:
            raise _loi_anh("Chỉ nhận ảnh jpeg, png hoặc webp")
        kieu.append(k)
    return kieu


def hash_anh(ds_anh: list[bytes]) -> str:
    hashes = sorted(hashlib.sha256(a).hexdigest() for a in ds_anh)
    return hashes[0] if len(hashes) == 1 else hashlib.sha256("\n".join(hashes).encode()).hexdigest()


async def gui_yeu_cau(
    db: AsyncSession,
    *,
    khach: KhachHang | None,
    ho_ten: str,
    so_dien_thoai: str,
    ghi_chu: str | None,
    ds_anh: list[bytes],
) -> YeuCauDonThuocTao:
    """Tạo yêu cầu `cho_duyet`. Người gọi đã xác thực OTP nếu là khách vãng lai."""
    kieu = kiem_tra_anh(ds_anh)
    bay_gio = bay_gio_utc()
    da_gui = await db.scalar(
        select(func.count())
        .select_from(YeuCauDonThuoc)
        .where(
            YeuCauDonThuoc.so_dien_thoai == so_dien_thoai,
            YeuCauDonThuoc.created_at > bay_gio - timedelta(days=1),
        )
    )
    if (da_gui or 0) >= SO_YEU_CAU_TOI_DA_MOI_SDT_NGAY:
        raise LoiNghiepVu(
            "QUA_GIOI_HAN", "Số điện thoại này đã gửi quá số yêu cầu cho phép trong ngày, vui lòng thử lại sau"
        )
    khoa = []
    store = luu_tru.luu_tru()
    for noi_dung, k in zip(ds_anh, kieu, strict=True):
        f = await store.luu("don-thuoc", noi_dung, k, vung="rieng_tu")
        luu_tru.xoa_neu_hoan_tac(db, f, "rieng_tu")
        khoa.append(f)
    yc = YeuCauDonThuoc(
        ma_yeu_cau="YC" + secrets.token_hex(4).upper(),
        khach_hang_id=None if khach is None else khach.id,
        kenh=KenhBan.online,
        ho_ten=ho_ten,
        so_dien_thoai=so_dien_thoai,
        anh_don_thuoc=khoa,
        hash_anh=hash_anh(ds_anh),
        ghi_chu=ghi_chu or None,
        trang_thai=TrangThaiYeuCauDonThuoc.cho_duyet,
        created_at=bay_gio,
    )
    db.add(yc)
    await db.flush()
    return YeuCauDonThuocTao(ma_yeu_cau=yc.ma_yeu_cau, trang_thai=yc.trang_thai, created_at=yc.created_at)


async def _ma_don(db: AsyncSession, yeu_cau_id: int) -> str | None:
    return await db.scalar(
        select(DonHang.ma_don).where(DonHang.yeu_cau_don_thuoc_id == yeu_cau_id).order_by(DonHang.id.desc()).limit(1)
    )


async def _cua_khach(db: AsyncSession, khach: KhachHang, ma_yeu_cau: str, khoa: bool = False) -> YeuCauDonThuoc:
    cau = select(YeuCauDonThuoc).where(
        YeuCauDonThuoc.ma_yeu_cau == ma_yeu_cau, YeuCauDonThuoc.khach_hang_id == khach.id
    )
    yc = (await db.execute(cau.with_for_update() if khoa else cau)).scalars().first()
    if yc is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy yêu cầu đơn thuốc")
    return yc


async def danh_sach(db: AsyncSession, khach: KhachHang) -> list[YeuCauDonThuocTom]:
    ds = (
        (
            await db.execute(
                select(YeuCauDonThuoc)
                .where(YeuCauDonThuoc.khach_hang_id == khach.id)
                .order_by(YeuCauDonThuoc.created_at.desc(), YeuCauDonThuoc.id.desc())
                .limit(100)
            )
        )
        .scalars()
        .all()
    )
    return [await _tom(db, yc) for yc in ds]


async def _tom(db: AsyncSession, yc: YeuCauDonThuoc) -> YeuCauDonThuocTom:
    return YeuCauDonThuocTom(
        ma_yeu_cau=yc.ma_yeu_cau,
        trang_thai=yc.trang_thai,
        ho_ten=yc.ho_ten,
        so_anh=len(yc.anh_don_thuoc or []),
        ghi_chu=yc.ghi_chu,
        ly_do_tu_choi=yc.ly_do_tu_choi,
        ma_don=await _ma_don(db, yc.id),
        created_at=yc.created_at,
    )


async def chi_tiet(db: AsyncSession, khach: KhachHang, ma_yeu_cau: str) -> YeuCauDonThuocChiTiet:
    yc = await _cua_khach(db, khach, ma_yeu_cau)
    tom = await _tom(db, yc)
    return YeuCauDonThuocChiTiet(
        **tom.model_dump(),
        so_dien_thoai=yc.so_dien_thoai,
        anh=[luu_tru.url_ky(k) for k in yc.anh_don_thuoc or []],
    )


async def huy(db: AsyncSession, khach: KhachHang, ma_yeu_cau: str) -> YeuCauDonThuocTom:
    """Khách hủy khi còn `cho_duyet` hoặc `dang_tu_van` (spec 04 mục 1.2 dòng 7); trạng thái khác là 409."""
    yc = await _cua_khach(db, khach, ma_yeu_cau, khoa=True)
    if yc.trang_thai not in CHO_PHEP_HUY:
        raise LoiNghiepVu(
            "CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Chỉ hủy được yêu cầu đang chờ duyệt hoặc đang được dược sĩ tư vấn"
        )
    yc.trang_thai = TrangThaiYeuCauDonThuoc.khach_huy
    yc.duoc_si_id = None
    yc.khoa_luc = None
    yc.updated_at = bay_gio_utc()
    await db.flush()
    return await _tom(db, yc)

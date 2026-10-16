"""OTP (spec 06 mục 3): 6 chữ số, lưu HMAC, hiệu lực 5 phút, tối đa 5 lần thử, giới hạn gửi theo SĐT và IP.

Chống dò tài khoản: với số không hợp lệ cho mục đích đó (đăng ký mà số đã có tài khoản, lấy lại mật khẩu mà số chưa có),
API vẫn trả y hệt và vẫn tạo một dòng giữ chỗ đếm lần thử y như OTP thật (chỉ không có mã nào khớp được), nên không có
cách nào phân biệt từ bên ngoài. Chủ số nhận một tin nhắn báo tình trạng tài khoản thay cho mã.

Lần thử sai phải được ghi dù request trả lỗi: route gọi `kiem_tra_otp` rồi TRẢ VỀ lỗi bằng `core.loi.tra_loi` (không
raise) để `get_db` commit bộ đếm.
"""

import hashlib
import hmac
import math
import secrets
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bao_mat import khoa_hmac
from app.core.cau_hinh import doc_cau_hinh
from app.core.gioi_han import GioiHanCuaSoTruot
from app.core.loi import LoiNghiepVu, tra_loi
from app.core.thoi_gian import bay_gio_utc
from app.models.khach_hang import KhachHang, MaOtp
from app.tich_hop.tin_nhan import KenhTinNhan, LoiGuiTinNhan
from app.tich_hop.tin_nhan.mau.otp import email_otp, sms_chua_co_tai_khoan, sms_da_co_tai_khoan, sms_otp

HIEU_LUC_PHUT = 5
SO_LAN_THU_TOI_DA = 5
CUA_SO_GIOI_HAN = timedelta(hours=1)
GIOI_HAN_MAC_DINH = {"moi_sdt_moi_gio": 5, "moi_ip_moi_gio": 20}


class KetQuaOtp(StrEnum):
    OK = "ok"
    SAI = "sai"
    HET_HAN = "het_han"
    QUA_SO_LAN = "qua_so_lan"


@dataclass(frozen=True)
class KetQuaKiemTra:
    ket_qua: KetQuaOtp
    so_lan_con_lai: int | None = None


def bam_otp(dich_den: str, muc_dich: str, ma: str) -> str:
    """HMAC-SHA256 có khóa của (mục đích, nơi nhận, mã). Gắn với nơi nhận và mục đích để OTP của số này không dùng
    được cho số khác hay việc khác; có khóa bí mật để lộ DB không cho phép dò 10^6 mã ngoại tuyến."""
    return hmac.new(khoa_hmac("otp"), f"{muc_dich}|{dich_den}|{ma}".encode(), hashlib.sha256).hexdigest()


async def _khoa_theo_dich_den(db: AsyncSession, muc_dich: str, dich_den: str) -> None:
    """Tuần tự hóa mọi thao tác OTP của cùng một (mục đích, nơi nhận) trong transaction: đếm giới hạn gửi và vô hiệu mã
    cũ không bị hai request đồng thời đọc cùng số liệu."""
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:khoa))"), {"khoa": f"otp:{muc_dich}:{dich_den}"})


async def gui_otp(
    db: AsyncSession,
    kenh: KenhTinNhan,
    *,
    so_dien_thoai: str,
    muc_dich: str,
    ip: str,
    bo_gioi_han_ip: GioiHanCuaSoTruot,
    kenh_gui: str = "sms",
) -> None:
    """Tạo và gửi OTP qua SMS (hoặc email nếu `kenh_gui="email"` và tài khoản có email).

    Ném `QUA_GIOI_HAN` (kèm `Retry-After`) hoặc `LOI_DOI_TAC` khi không gửi được.
    """
    gioi_han = GIOI_HAN_MAC_DINH | dict(await doc_cau_hinh(db, "gioi_han_otp", {}))
    await _khoa_theo_dich_den(db, muc_dich, so_dien_thoai)

    cho_ip = bo_gioi_han_ip.thu(f"otp:{ip}", int(gioi_han["moi_ip_moi_gio"]), CUA_SO_GIOI_HAN.total_seconds())
    if cho_ip is not None:
        raise _qua_gioi_han(math.ceil(cho_ip))

    bay_gio = bay_gio_utc()
    toi_da_sdt = int(gioi_han["moi_sdt_moi_gio"])
    cac_lan_gui = list(
        (
            await db.execute(
                select(MaOtp.created_at)
                .where(
                    MaOtp.dich_den == so_dien_thoai,
                    MaOtp.muc_dich == muc_dich,
                    MaOtp.created_at > bay_gio - CUA_SO_GIOI_HAN,
                )
                .order_by(MaOtp.created_at)
            )
        ).scalars()
    )
    if len(cac_lan_gui) >= toi_da_sdt:
        het_cho = cac_lan_gui[len(cac_lan_gui) - toi_da_sdt] + CUA_SO_GIOI_HAN
        raise _qua_gioi_han(max(1, math.ceil((het_cho - bay_gio).total_seconds())))

    tai_khoan = (
        await db.execute(
            select(KhachHang.id, KhachHang.email).where(
                KhachHang.so_dien_thoai == so_dien_thoai, KhachHang.deleted_at.is_(None)
            )
        )
    ).first()
    # Đăng ký cần số CHƯA có tài khoản; lấy lại mật khẩu cần số ĐÃ có. Số không hợp lệ cho mục đích đó nhận tin báo thay
    # cho mã và một dòng giữ chỗ không khớp được.
    # Đơn thuốc của khách vãng lai: số nào cũng hợp lệ (chỉ cần chứng minh sở hữu số).
    hop_le = muc_dich == "don_thuoc_khach" or (tai_khoan is not None) == (muc_dich == "quen_mat_khau")
    ma = f"{secrets.randbelow(10**6):06d}" if hop_le else None

    # Vô hiệu mã cũ chưa dùng: chỉ mã mới nhất có hiệu lực.
    await db.execute(
        update(MaOtp)
        .where(MaOtp.dich_den == so_dien_thoai, MaOtp.muc_dich == muc_dich, MaOtp.da_dung.is_(False))
        .values(da_dung=True)
    )
    db.add(
        MaOtp(
            dich_den=so_dien_thoai,
            muc_dich=muc_dich,
            # Dòng giữ chỗ dùng "mã" ngẫu nhiên dài, không bao giờ khớp đầu vào 6 chữ số.
            ma_hash=bam_otp(so_dien_thoai, muc_dich, ma or secrets.token_hex(16)),
            het_han=bay_gio + timedelta(minutes=HIEU_LUC_PHUT),
            created_at=bay_gio,
        )
    )
    await db.flush()

    try:
        if ma is None:
            thong_bao = sms_da_co_tai_khoan() if muc_dich == "dang_ky" else sms_chua_co_tai_khoan()
            await kenh.gui_sms(so_dien_thoai, thong_bao)
        elif kenh_gui == "email" and tai_khoan is not None and tai_khoan.email:
            tieu_de, html = email_otp(ma, HIEU_LUC_PHUT)
            await kenh.gui_email(tai_khoan.email, tieu_de, html)
        else:  # SMS, hoặc xin email nhưng tài khoản chưa có email: gửi SMS để người dùng vẫn lấy được mã
            await kenh.gui_sms(so_dien_thoai, sms_otp(ma, HIEU_LUC_PHUT))
    except LoiGuiTinNhan as loi:
        # Không lộ chi tiết nhà cung cấp cho client; raise để request rollback, không để lại OTP không ai nhận được.
        raise LoiNghiepVu("LOI_DOI_TAC", "Không gửi được tin nhắn, vui lòng thử lại sau") from loi


def _qua_gioi_han(giay: int) -> LoiNghiepVu:
    return LoiNghiepVu(
        "QUA_GIOI_HAN",
        "Bạn yêu cầu mã quá nhiều lần, vui lòng thử lại sau",
        chi_tiet={"thu_lai_sau_giay": giay},
        headers={"Retry-After": str(giay)},
    )


async def kiem_tra_otp(
    db: AsyncSession, *, dich_den: str, muc_dich: str, ma: str, tieu_thu: bool = True
) -> KetQuaKiemTra:
    """Kiểm tra `ma` với OTP mới nhất chưa dùng của (`dich_den`, `muc_dich`).

    Khóa dòng OTP (FOR UPDATE) nên hai request đồng thời không thể cùng xác thực một mã. Đúng thì đánh dấu đã dùng
    (nếu `tieu_thu`); sai thì tăng bộ đếm. Hết hạn không tính là một lần thử.
    """
    otp = (
        (
            await db.execute(
                select(MaOtp)
                .where(MaOtp.dich_den == dich_den, MaOtp.muc_dich == muc_dich, MaOtp.da_dung.is_(False))
                .order_by(MaOtp.id.desc())
                .limit(1)
                .with_for_update()
            )
        )
        .scalars()
        .first()
    )
    if otp is None:
        return KetQuaKiemTra(KetQuaOtp.SAI)
    if otp.het_han <= bay_gio_utc():
        return KetQuaKiemTra(KetQuaOtp.HET_HAN)
    if otp.so_lan_thu >= SO_LAN_THU_TOI_DA:
        return KetQuaKiemTra(KetQuaOtp.QUA_SO_LAN, 0)
    if hmac.compare_digest(otp.ma_hash, bam_otp(dich_den, muc_dich, ma)):
        if tieu_thu:
            otp.da_dung = True
        return KetQuaKiemTra(KetQuaOtp.OK)
    otp.so_lan_thu += 1
    return KetQuaKiemTra(KetQuaOtp.SAI, SO_LAN_THU_TOI_DA - otp.so_lan_thu)


def loi_otp(ket_qua: KetQuaKiemTra):
    """Phản hồi lỗi (TRẢ VỀ, không raise, để bộ đếm lần thử được commit). `None` nếu OTP đúng."""
    if ket_qua.ket_qua is KetQuaOtp.OK:
        return None
    if ket_qua.ket_qua is KetQuaOtp.HET_HAN:
        return tra_loi("OTP_HET_HAN", "Mã OTP đã hết hạn, vui lòng xin mã mới")
    if ket_qua.ket_qua is KetQuaOtp.QUA_SO_LAN:
        return tra_loi(
            "OTP_SAI",
            "Bạn đã nhập sai quá số lần cho phép, vui lòng xin mã mới",
            {"so_lan_con_lai": 0},
        )
    return tra_loi("OTP_SAI", "Mã OTP không đúng", {"so_lan_con_lai": ket_qua.so_lan_con_lai})

"""Xác thực và phân quyền cho route (spec 03 mục 8).

- Khách: `khach_hien_tai`, `khach_tuy_chon`.
- Nhân viên: `nhan_vien_hien_tai` và `yeu_cau_quyen(ma, muc)`.

Trạng thái tài khoản được kiểm tra ở MỖI request (không tin access token đã ký), nên khóa tài khoản có hiệu lực ngay
chứ không chờ token hết hạn. Quyền của vai trò đọc từ DB và cache trong process 60 giây.
"""

import time
from collections.abc import Awaitable, Callable
from typing import Literal

import jwt
from fastapi import Request
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.bao_mat import giai_ma_access_token
from app.core.danh_muc_quyen import ma_quyen_hop_le
from app.core.db import Db
from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc
from app.models.enums import TrangThaiTaiKhoan
from app.models.he_thong import NhanVien, Quyen, VaiTro, VaiTroQuyen
from app.models.khach_hang import KhachHang

MA_VAI_TRO_ADMIN = "ADMIN"

_TIEN_TO = "bearer "

MucYeuCau = Literal["xem", "day_du"]
"""Mức route yêu cầu: `xem` nhận cả vai trò chỉ xem lẫn đầy đủ; `day_du` chỉ nhận đầy đủ."""
MucCuaVaiTro = Literal["day_du", "chi_xem"]
"""Mức quyền của vai trò, đúng như `quyen.yaml` và API `/noi-bo/toi`."""

PHUONG_THUC_DOC = frozenset({"GET", "HEAD", "OPTIONS"})
THOI_GIAN_CACHE_QUYEN_GIAY = 60


def _lay_token(request: Request) -> str | None:
    gia_tri = request.headers.get("Authorization", "")
    if gia_tri[: len(_TIEN_TO)].lower() != _TIEN_TO:
        return None
    return gia_tri[len(_TIEN_TO) :].strip() or None


def _id_tu_token(token: str, aud: str) -> int:
    """Giải mã access token (`aud` đúng), trả id tài khoản. Token hỏng là `CHUA_DANG_NHAP`, hết hạn có mã riêng."""
    try:
        return int(giai_ma_access_token(token, aud)["sub"])
    except jwt.ExpiredSignatureError as loi:
        raise LoiNghiepVu("TOKEN_HET_HAN", "Phiên đăng nhập đã hết hạn") from loi
    except (jwt.InvalidTokenError, ValueError, KeyError) as loi:  # chữ ký sai, sai aud, thiếu claim, sub không phải số
        raise LoiNghiepVu("CHUA_DANG_NHAP", "Bạn chưa đăng nhập") from loi


def _kiem_tra_dang_hoat_dong(tai_khoan: KhachHang | NhanVien) -> None:
    if tai_khoan.trang_thai != TrangThaiTaiKhoan.hoat_dong or (
        tai_khoan.khoa_den and tai_khoan.khoa_den > bay_gio_utc()
    ):
        raise LoiNghiepVu("TAI_KHOAN_BI_KHOA", "Tài khoản đang bị khóa")


# --- Khách -----------------------------------------------------------------------------------------------------------


async def _khach_tu_token(token: str, db: Db) -> KhachHang:
    khach_id = _id_tu_token(token, "khach")
    khach = (
        await db.execute(select(KhachHang).where(KhachHang.id == khach_id, KhachHang.deleted_at.is_(None)))
    ).scalar_one_or_none()
    if khach is None:
        raise LoiNghiepVu("CHUA_DANG_NHAP", "Bạn chưa đăng nhập")
    _kiem_tra_dang_hoat_dong(khach)
    return khach


async def khach_hien_tai(request: Request, db: Db) -> KhachHang:
    """Bắt buộc đăng nhập: access token `aud = khach`, tài khoản `hoat_dong` và không bị `khoa_den`.

    Mọi API của khách lấy `khach_hang_id` từ đây, không bao giờ nhận id khách từ client (CLAUDE.md quy tắc 3).
    """
    token = _lay_token(request)
    if token is None:
        raise LoiNghiepVu("CHUA_DANG_NHAP", "Bạn chưa đăng nhập")
    return await _khach_tu_token(token, db)


async def khach_tuy_chon(request: Request, db: Db) -> KhachHang | None:
    """Cho route công khai cần biết khách nếu có. Không có token hoặc token vô nghĩa thì coi là khách vãng lai.

    Token hết hạn thì trả 401 `TOKEN_HET_HAN` để client làm mới rồi gọi lại; tài khoản bị khóa cũng coi như vãng lai.
    """
    token = _lay_token(request)
    if token is None:
        return None
    try:
        return await _khach_tu_token(token, db)
    except LoiNghiepVu as loi:
        if loi.ma_loi == "TOKEN_HET_HAN":
            raise
        return None


# --- Nhân viên -------------------------------------------------------------------------------------------------------


async def _nhan_vien_tu_request(request: Request, db: Db, *, ke_ca_chua_doi_mat_khau: bool) -> NhanVien:
    token = _lay_token(request)
    if token is None:
        raise LoiNghiepVu("CHUA_DANG_NHAP", "Bạn chưa đăng nhập")
    nhan_vien_id = _id_tu_token(token, "noi_bo")
    nhan_vien = (
        await db.execute(
            select(NhanVien)
            .options(selectinload(NhanVien.vai_tro))
            .where(NhanVien.id == nhan_vien_id, NhanVien.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if nhan_vien is None:
        raise LoiNghiepVu("CHUA_DANG_NHAP", "Bạn chưa đăng nhập")
    _kiem_tra_dang_hoat_dong(nhan_vien)
    if nhan_vien.phai_doi_mat_khau and not ke_ca_chua_doi_mat_khau:
        raise LoiNghiepVu("PHAI_DOI_MAT_KHAU", "Bạn cần đổi mật khẩu trước khi tiếp tục")
    return nhan_vien


async def nhan_vien_hien_tai(request: Request, db: Db) -> NhanVien:
    """Bắt buộc đăng nhập nội bộ: `aud = noi_bo`, tài khoản hoạt động và đã đổi mật khẩu lần đầu.

    Chưa kiểm tra quyền cụ thể: route nghiệp vụ dùng `yeu_cau_quyen`. Route nội bộ nào cũng PHẢI dùng `yeu_cau_quyen`
    (test registry kiểm tra), trừ ba route xác thực công khai.
    """
    return await _nhan_vien_tu_request(request, db, ke_ca_chua_doi_mat_khau=False)


# Cache quyền theo vai trò: {vai_tro_id: (thời điểm nạp, {mã quyền: mức})}. Dùng đồng hồ đơn điệu, không dùng giờ máy.
_cache_quyen: dict[int, tuple[float, dict[str, MucCuaVaiTro]]] = {}


def xoa_cache_quyen_sau_commit(db) -> None:
    """Xóa cache quyền ngay và LẦN NỮA sau khi transaction của `db` commit.

    Chỉ xóa trước commit thì một request khác chạy giữa lúc xóa và lúc commit sẽ đọc dữ liệu cũ rồi cache lại 60 giây.
    """
    xoa_cache_quyen()
    event.listen(db.sync_session, "after_commit", lambda _phien: xoa_cache_quyen(), once=True)


async def dam_bao_la_admin(db: AsyncSession, nguoi_thuc_hien: NhanVien) -> None:
    """Lớp phòng thủ thứ hai cho thao tác chỉ Admin được làm (quản trị tài khoản AD01, phân quyền AD18).

    `staff.manage`/`role.manage` không gán được cho vai trò khác qua AD18, nhưng dữ liệu cấu hình sai (gán thẳng vào DB)
    không được biến thành quyền tạo Admin hay tự cấp quyền. Dùng ở đầu mọi hàm GHI của hai chức năng đó.
    """
    ma_vai_tro = await db.scalar(select(VaiTro.ma).where(VaiTro.id == nguoi_thuc_hien.vai_tro_id))
    if ma_vai_tro != MA_VAI_TRO_ADMIN:
        raise LoiNghiepVu("KHONG_CO_QUYEN", "Chỉ Admin mới được thực hiện thao tác này")


def xoa_cache_quyen() -> None:
    """Bỏ cache quyền (AD18 gọi sau khi Admin đổi phân quyền để có hiệu lực ngay trong process này)."""
    _cache_quyen.clear()


async def quyen_cua_vai_tro(db: Db, vai_tro_id: int) -> dict[str, MucCuaVaiTro]:
    """Quyền của vai trò: `{mã quyền: "day_du" | "chi_xem"}`, cache 60 giây.

    `gioi_han` NULL là đầy đủ; mọi giá trị khác (`chi_xem` hoặc giá trị lạ) coi là chỉ xem (đặc quyền tối thiểu).
    """
    bay_gio = time.monotonic()
    da_co = _cache_quyen.get(vai_tro_id)
    if da_co is not None and bay_gio - da_co[0] < THOI_GIAN_CACHE_QUYEN_GIAY:
        return da_co[1]
    dong = (
        await db.execute(
            select(Quyen.ma, VaiTroQuyen.gioi_han)
            .join(VaiTroQuyen, VaiTroQuyen.quyen_id == Quyen.id)
            .where(VaiTroQuyen.vai_tro_id == vai_tro_id)
        )
    ).all()
    quyen: dict[str, MucCuaVaiTro] = {ma: ("day_du" if gioi_han is None else "chi_xem") for ma, gioi_han in dong}
    _cache_quyen[vai_tro_id] = (bay_gio, quyen)
    return quyen


def yeu_cau_quyen(
    ma: str, muc: MucYeuCau = "day_du", *, ke_ca_chua_doi_mat_khau: bool = False
) -> Callable[..., Awaitable[NhanVien]]:
    """Dependency trả `NhanVien` đã qua: đăng nhập nội bộ, tài khoản hoạt động, đã đổi mật khẩu, có quyền `ma`.

    - `muc="xem"` (chỉ nên dùng cho GET): vai trò có quyền ở mức chỉ xem hoặc đầy đủ đều qua.
    - `muc="day_du"` (mặc định): chỉ vai trò có quyền đầy đủ.
    - Thao tác ghi (POST/PUT/PATCH/DELETE) LUÔN cần mức đầy đủ, kể cả khi khai báo nhầm `muc="xem"` (spec 03 mục 2).
    - `ke_ca_chua_doi_mat_khau=True` chỉ cho `GET /noi-bo/toi` và đổi mật khẩu, để người bị bắt đổi mật khẩu dùng được.
    - Thiếu quyền: 403 `KHONG_CO_QUYEN`. `ma` phải có trong `quyen.yaml` (sai thì lỗi ngay khi dựng route).
    """
    hop_le = ma_quyen_hop_le()
    if hop_le is not None and ma not in hop_le:
        raise ValueError(f"Mã quyền {ma!r} không có trong docs/spec/data/quyen.yaml")
    if muc not in ("xem", "day_du"):
        raise ValueError(f"muc phải là 'xem' hoặc 'day_du', nhận {muc!r}")

    async def kiem_tra_quyen(request: Request, db: Db) -> NhanVien:
        nhan_vien = await _nhan_vien_tu_request(request, db, ke_ca_chua_doi_mat_khau=ke_ca_chua_doi_mat_khau)
        can_muc = muc if request.method in PHUONG_THUC_DOC else "day_du"
        co_muc = (await quyen_cua_vai_tro(db, nhan_vien.vai_tro_id)).get(ma)
        if co_muc is None or (can_muc == "day_du" and co_muc != "day_du"):
            raise LoiNghiepVu("KHONG_CO_QUYEN", "Bạn không có quyền thực hiện thao tác này")
        return nhan_vien

    # Để test registry đối chiếu khai báo của từng route với bảng ma trận.
    kiem_tra_quyen.ma_quyen = ma  # type: ignore[attr-defined]
    kiem_tra_quyen.muc = muc  # type: ignore[attr-defined]
    kiem_tra_quyen.ke_ca_chua_doi_mat_khau = ke_ca_chua_doi_mat_khau  # type: ignore[attr-defined]
    return kiem_tra_quyen

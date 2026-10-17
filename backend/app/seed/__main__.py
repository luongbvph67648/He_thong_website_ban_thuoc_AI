"""CLI seed.

    uv run python -m app.seed          # vai trò, quyền, cấu hình mặc định, Admin đầu tiên (ADMIN_EMAIL, ADMIN_MAT_KHAU)
    uv run python -m app.seed --mau    # thêm dữ liệu mẫu để demo (tài khoản mẫu có mật khẩu công khai, chỉ dùng cục bộ)

Chạy lại nhiều lần an toàn. ADMIN_EMAIL và ADMIN_MAT_KHAU bắt buộc ở lần chạy đầu (khi hệ thống chưa có Admin nào); các
lần sau có thể bỏ trống. `--mau` chỉ chạy với CSDL ở máy cục bộ trừ khi thêm `--cho-phep-may-chu-khac`.
Mã thoát: 0 thành công, 2 sai cấu hình hoặc tham số.
"""

import argparse
import asyncio
import sys

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import tao_engine
from app.seed.co_ban import TaiKhoanAdmin, co_admin_hoat_dong, kiem_tra_admin, seed_co_ban
from app.seed.du_lieu_mau import MAT_KHAU_MAU, seed_mau

MAY_CHU_CUC_BO = {"localhost", "127.0.0.1", "::1", "db"}  # "db" là tên service trong docker-compose.yml
TAI_KHOAN_MAU = [
    ("Dược sĩ", "duocsi@example.com"),
    ("Nhân viên kho", "kho@example.com"),
    ("Khách hàng", "0900000001 hoặc 0900000002"),
]


class LoiCauHinh(Exception):
    """Sai cấu hình: thông điệp in cho người chạy, thoát mã 2."""


def _thong_tin_admin() -> TaiKhoanAdmin | None:
    email, mat_khau = settings.ADMIN_EMAIL.strip(), settings.ADMIN_MAT_KHAU.get_secret_value()
    return TaiKhoanAdmin(email=email, mat_khau=mat_khau) if email or mat_khau else None


def kiem_tra_duoc_nap_mau(url: str, cho_phep_may_chu_khac: bool) -> None:
    """Tài khoản mẫu có mật khẩu công khai nên chỉ nạp vào CSDL ở máy cục bộ, trừ khi người chạy nói rõ."""
    if settings.MOI_TRUONG == "production":
        raise LoiCauHinh("Từ chối nạp dữ liệu mẫu khi MOI_TRUONG=production: tài khoản mẫu có mật khẩu công khai.")
    may_chu = make_url(url).host or "localhost"
    if may_chu not in MAY_CHU_CUC_BO and not cho_phep_may_chu_khac:
        raise LoiCauHinh(
            f"Từ chối nạp dữ liệu mẫu vào máy chủ CSDL {may_chu!r}: tài khoản mẫu có mật khẩu công khai. "
            "Nếu chắc chắn đây là môi trường thử, thêm --cho-phep-may-chu-khac."
        )


async def chay(mau: bool, cho_phep_may_chu_khac: bool = False, demo: bool = False) -> int:
    mau = mau or demo
    try:
        admin = _thong_tin_admin()
        if admin is not None:
            kiem_tra_admin(admin)
        if mau:
            kiem_tra_duoc_nap_mau(settings.DATABASE_URL, cho_phep_may_chu_khac)
    except ValueError as loi:  # thông điệp nêu lý do, không chứa mật khẩu
        print(f"{loi} (sửa ADMIN_EMAIL, ADMIN_MAT_KHAU trong backend/.env)", file=sys.stderr)
        return 2
    except LoiCauHinh as loi:
        print(loi, file=sys.stderr)
        return 2

    engine = tao_engine(settings.DATABASE_URL)
    try:
        async with AsyncSession(engine) as db, db.begin():
            ket_qua = await seed_co_ban(db, admin=admin)
            if admin is None and not await co_admin_hoat_dong(db):
                raise LoiCauHinh("Hệ thống chưa có Admin: đặt ADMIN_EMAIL và ADMIN_MAT_KHAU trong backend/.env")
        print(
            f"Đã đồng bộ {ket_qua['vai_tro']} vai trò, {ket_qua['quyen']} quyền ({ket_qua['quyen_moi']} mới cấp mặc "
            f"định), {ket_qua['vai_tro_quyen']} cặp vai trò-quyền; thêm {ket_qua['cau_hinh_moi']} khóa cấu hình mới."
        )
        email_admin = admin.email if admin else ""
        trang_thai_admin = {
            "da_tao": f"Tài khoản Admin {email_admin}: đã tạo (phải đổi mật khẩu ở lần đăng nhập đầu).",
            "da_co": f"Tài khoản Admin {email_admin}: đã có sẵn, giữ nguyên.",
            "bo_qua": "Không tạo Admin (đã có Admin hoạt động, ADMIN_EMAIL để trống).",
        }
        print(trang_thai_admin[ket_qua["admin"]])
        if mau:
            async with AsyncSession(engine) as db, db.begin():
                moi = await seed_mau(db)
            print("Dữ liệu mẫu mới tạo:", ", ".join(f"{k}={v}" for k, v in sorted(moi.items())) or "không có (đã đủ)")
            print(f"Tài khoản mẫu (mật khẩu chung công khai: {MAT_KHAU_MAU}), CHỈ DÙNG CỤC BỘ:")
            for vai_tro, dang_nhap in TAI_KHOAN_MAU:
                print(f"  {vai_tro}: {dang_nhap}")
        if demo:
            from app.main import create_app
            from app.seed.demo import LoiDemo, seed_demo

            try:
                async with AsyncSession(engine) as db:
                    moi = await seed_demo(create_app(), db)
            except LoiDemo as loi:
                raise LoiCauHinh(str(loi)) from loi
            print(
                "Dữ liệu demo mới tạo:", ", ".join(f"{k}={v}" for k, v in sorted(moi.items())) or "không có (đã có đơn)"
            )
        return 0
    except LoiCauHinh as loi:
        print(loi, file=sys.stderr)
        return 2
    finally:
        await engine.dispose()


def main() -> int:
    tham_so = argparse.ArgumentParser(prog="python -m app.seed", description=__doc__.split("\n")[0])
    tham_so.add_argument("--mau", action="store_true", help="nạp thêm dữ liệu mẫu để demo")
    tham_so.add_argument(
        "--demo", action="store_true", help="như --mau, thêm đơn hàng nhiều trạng thái và 3 tháng doanh thu"
    )
    tham_so.add_argument(
        "--cho-phep-may-chu-khac", action="store_true", help="cho --mau chạy với CSDL không ở máy cục bộ"
    )
    args = tham_so.parse_args()
    return asyncio.run(chay(args.mau, args.cho_phep_may_chu_khac, args.demo))


if __name__ == "__main__":
    sys.exit(main())

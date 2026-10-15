"""CLI seed.

    uv run python -m app.seed          # vai trò, quyền, cấu hình mặc định, Admin đầu tiên (ADMIN_EMAIL, ADMIN_MAT_KHAU)
    uv run python -m app.seed --mau    # thêm dữ liệu mẫu để demo (tài khoản mẫu có mật khẩu công khai, chỉ dùng cục bộ)

Chạy lại nhiều lần an toàn. Mã thoát: 0 thành công, 2 sai cấu hình/tham số.
"""

import argparse
import asyncio
import sys

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import tao_engine
from app.seed.co_ban import TaiKhoanAdmin, kiem_tra_admin, seed_co_ban
from app.seed.du_lieu_mau import MAT_KHAU_MAU, seed_mau

TAI_KHOAN_MAU = [
    ("Dược sĩ", "duocsi@example.com"),
    ("Nhân viên kho", "kho@example.com"),
    ("Khách hàng", "0900000001 hoặc 0900000002"),
]


def _thong_tin_admin() -> TaiKhoanAdmin | None:
    email, mat_khau = settings.ADMIN_EMAIL.strip(), settings.ADMIN_MAT_KHAU.get_secret_value()
    return TaiKhoanAdmin(email=email, mat_khau=mat_khau) if email or mat_khau else None


async def chay(mau: bool) -> int:
    admin = _thong_tin_admin()
    if admin is None:
        print("Thiếu ADMIN_EMAIL và ADMIN_MAT_KHAU trong backend/.env (xem backend/.env.example).", file=sys.stderr)
        return 2
    try:
        kiem_tra_admin(admin)
    except ValueError as loi:  # thông điệp nêu lý do, không chứa mật khẩu
        print(f"{loi} (sửa ADMIN_EMAIL, ADMIN_MAT_KHAU trong backend/.env)", file=sys.stderr)
        return 2
    engine = tao_engine(settings.DATABASE_URL)
    try:
        async with AsyncSession(engine) as db, db.begin():
            ket_qua = await seed_co_ban(db, admin=admin)
        print(
            f"Đã đồng bộ {ket_qua['vai_tro']} vai trò, {ket_qua['quyen']} quyền, {ket_qua['vai_tro_quyen']} cặp "
            f"vai trò-quyền; thêm {ket_qua['cau_hinh_moi']} khóa cấu hình mới."
        )
        trang_thai_admin = {"da_tao": "đã tạo", "da_co": "đã có sẵn, giữ nguyên"}[ket_qua["admin"]]
        print(f"Tài khoản Admin {admin.email}: {trang_thai_admin}.")
        if mau:
            async with AsyncSession(engine) as db, db.begin():
                moi = await seed_mau(db)
            print("Dữ liệu mẫu mới tạo:", ", ".join(f"{k}={v}" for k, v in sorted(moi.items())) or "không có (đã đủ)")
            print(f"Tài khoản mẫu (mật khẩu chung: {MAT_KHAU_MAU}), CHỈ DÙNG CỤC BỘ:")
            for vai_tro, dang_nhap in TAI_KHOAN_MAU:
                print(f"  {vai_tro}: {dang_nhap}")
        return 0
    finally:
        await engine.dispose()


def main() -> int:
    tham_so = argparse.ArgumentParser(prog="python -m app.seed", description=__doc__.split("\n")[0])
    tham_so.add_argument("--mau", action="store_true", help="nạp thêm dữ liệu mẫu để demo")
    return asyncio.run(chay(tham_so.parse_args().mau))


if __name__ == "__main__":
    sys.exit(main())

"""CLI `python -m app.seed`: chạy như người dùng thật, qua tiến trình riêng và biến môi trường."""

import asyncio
import os
import subprocess
import sys

import pytest
from sqlalchemy import text

from app.core.config import BACKEND_DIR
from scripts.so_sanh_schema import chay_alembic

MAT_KHAU_ADMIN = "Mat-khau-thu-123"


async def chay_cli(engine, *doi_so, email="admin@example.com", mat_khau=MAT_KHAU_ADMIN) -> subprocess.CompletedProcess:
    moi_truong = {
        **os.environ,
        "DATABASE_URL": engine.url.render_as_string(hide_password=False),
        "ADMIN_EMAIL": email,
        "ADMIN_MAT_KHAU": mat_khau,
    }
    return await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-m", "app.seed", *doi_so],
        cwd=BACKEND_DIR,
        env=moi_truong,
        capture_output=True,
        text=True,
        timeout=120,
    )


async def dem(engine, bang: str) -> int:
    async with engine.connect() as conn:
        return (await conn.execute(text(f"SELECT count(*) FROM {bang}"))).scalar_one()


@pytest.fixture
async def engine_moi(engine_tam):
    await chay_alembic(engine_tam, "upgrade", "head")
    return engine_tam


async def test_seed_co_ban_roi_chay_lai(engine_moi):
    lan_1 = await chay_cli(engine_moi)
    assert lan_1.returncode == 0, lan_1.stderr
    assert "Tài khoản Admin admin@example.com: đã tạo" in lan_1.stdout
    so_quyen = await dem(engine_moi, "vai_tro_quyen")
    assert await dem(engine_moi, "vai_tro") == 3 and so_quyen > 50
    assert await dem(engine_moi, "cau_hinh") == 19 and await dem(engine_moi, "nhan_vien") == 1

    lan_2 = await chay_cli(engine_moi)
    assert lan_2.returncode == 0, lan_2.stderr
    assert "đã có sẵn, giữ nguyên" in lan_2.stdout
    assert await dem(engine_moi, "vai_tro_quyen") == so_quyen and await dem(engine_moi, "nhan_vien") == 1
    assert await dem(engine_moi, "san_pham") == 0  # không có --mau thì không có dữ liệu mẫu


async def test_seed_mau_va_chay_lai(engine_moi):
    lan_1 = await chay_cli(engine_moi, "--mau")
    assert lan_1.returncode == 0, lan_1.stderr
    assert "san_pham=42" in lan_1.stdout and "duocsi@example.com" in lan_1.stdout
    so_lieu = {
        b: await dem(engine_moi, b) for b in ("san_pham", "lo_thuoc", "bien_dong_kho", "khach_hang", "nhan_vien")
    }
    assert so_lieu["san_pham"] == 42 and so_lieu["nhan_vien"] == 3 and so_lieu["khach_hang"] == 2

    lan_2 = await chay_cli(engine_moi, "--mau")
    assert lan_2.returncode == 0, lan_2.stderr
    assert "không có (đã đủ)" in lan_2.stdout
    assert {b: await dem(engine_moi, b) for b in so_lieu} == so_lieu


async def test_thieu_thong_tin_admin_thoat_ma_2_va_khong_ghi_gi(engine_moi):
    ket_qua = await chay_cli(engine_moi, email="", mat_khau="")
    assert ket_qua.returncode == 2
    assert "ADMIN_EMAIL" in ket_qua.stderr
    assert await dem(engine_moi, "vai_tro") == 0


@pytest.mark.parametrize(
    ("email", "mat_khau", "tu_khoa"),
    [("khong-hop-le", MAT_KHAU_ADMIN, "email"), ("admin@example.com", "yeu", "mật khẩu")],
)
async def test_thong_tin_admin_sai_thoat_ma_2_khong_ghi_gi_va_khong_lo_mat_khau(engine_moi, email, mat_khau, tu_khoa):
    ket_qua = await chay_cli(engine_moi, email=email, mat_khau=mat_khau)
    assert ket_qua.returncode == 2
    assert tu_khoa in ket_qua.stderr
    assert mat_khau not in ket_qua.stdout + ket_qua.stderr
    assert await dem(engine_moi, "vai_tro") == 0


async def test_thanh_cong_khong_in_mat_khau_admin(engine_moi):
    ket_qua = await chay_cli(engine_moi, "--mau")
    assert MAT_KHAU_ADMIN not in ket_qua.stdout + ket_qua.stderr


async def test_tu_choi_nap_mau_vao_may_chu_khong_phai_cuc_bo_truoc_khi_ket_noi(engine_moi):
    """Chặn trước mọi kết nối: máy chủ ".invalid" không phân giải được, nên nếu chặn muộn thì lỗi kết nối chứ không phải mã 2."""
    moi_truong = {
        **os.environ,
        "DATABASE_URL": "postgresql+asyncpg://postgres:x@csdl-that.invalid:5432/nha_thuoc",
        "ADMIN_EMAIL": "admin@example.com",
        "ADMIN_MAT_KHAU": MAT_KHAU_ADMIN,
    }
    ket_qua = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-m", "app.seed", "--mau"],
        cwd=BACKEND_DIR,
        env=moi_truong,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert ket_qua.returncode == 2
    assert "csdl-that.invalid" in ket_qua.stderr and "--cho-phep-may-chu-khac" in ket_qua.stderr


async def test_lan_dau_bat_buoc_co_admin_nhung_lan_sau_co_the_bo_trong(engine_moi):
    chua_co = await chay_cli(engine_moi, email="", mat_khau="")
    assert chua_co.returncode == 2 and "chưa có Admin" in chua_co.stderr
    assert await dem(engine_moi, "vai_tro") == 0  # lỗi thì hoàn tác cả seed, không để dở dang

    assert (await chay_cli(engine_moi)).returncode == 0
    lan_sau = await chay_cli(engine_moi, email="", mat_khau="")
    assert lan_sau.returncode == 0, lan_sau.stderr
    assert "đã có Admin hoạt động" in lan_sau.stdout
    assert await dem(engine_moi, "nhan_vien") == 1


async def test_mat_khau_admin_la_gia_tri_mau_bi_tu_choi(engine_moi):
    ket_qua = await chay_cli(engine_moi, mat_khau="doi-mat-khau-nay-123")
    assert ket_qua.returncode == 2 and "giá trị mẫu" in ket_qua.stderr
    assert await dem(engine_moi, "nhan_vien") == 0

"""T0.4: migration Alembic dựng đúng schema của ERD và đi/về được."""

import logging

from alembic.script import ScriptDirectory
from sqlalchemy import text

from app.core.config import settings
from scripts.so_sanh_schema import (
    cau_hinh_alembic,
    cau_truc_tu_migration,
    chay_alembic,
    db_tam,
    lay_cau_truc,
    so_sanh,
    so_sanh_migration_voi_erd,
)


async def dem(engine, truy_van: str) -> int:
    async with engine.connect() as conn:
        return (await conn.execute(text(truy_van))).scalar_one()


async def trang_thai(engine) -> dict[str, int]:
    """Số đối tượng do migration tạo ra, để so sánh trước/sau upgrade/downgrade."""
    truy_van = {
        "bang": "SELECT count(*) FROM pg_tables WHERE schemaname = 'public'",
        "enum": "SELECT count(DISTINCT enumtypid) FROM pg_enum",
        "check": "SELECT count(*) FROM pg_constraint WHERE contype = 'c' AND conrelid <> 0",
        "index": "SELECT count(*) FROM pg_indexes WHERE schemaname = 'public'",
        "sequence": "SELECT count(*) FROM pg_class WHERE relkind = 'S' AND relnamespace = 'public'::regnamespace "
        "AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = pg_class.oid AND d.deptype IN ('a', 'i'))",
        "ham": "SELECT count(*) FROM pg_proc WHERE proname = 'f_unaccent'",
    }
    return {ten: await dem(engine, sql) for ten, sql in truy_van.items()}


def test_chi_co_mot_head_va_chuoi_tuyen_tinh():
    kich_ban = ScriptDirectory.from_config(cau_hinh_alembic(settings.DATABASE_URL))
    assert kich_ban.get_heads() == ["0003"]
    assert [r.revision for r in reversed(list(kich_ban.walk_revisions()))] == ["0001", "0002", "0003"]


async def test_upgrade_tao_du_doi_tuong(engine_tam):
    assert (await trang_thai(engine_tam))["bang"] == 0
    await chay_alembic(engine_tam, "upgrade", "head")
    assert await trang_thai(engine_tam) == {
        "bang": 66,  # 65 bảng của ERD + alembic_version
        "enum": 33,
        "check": 42,
        "index": await dem(engine_tam, "SELECT count(*) FROM pg_indexes WHERE schemaname = 'public'"),
        "sequence": 7,
        "ham": 1,
    }
    for extension in ("vector", "unaccent", "pg_trgm"):
        assert await dem(engine_tam, f"SELECT count(*) FROM pg_extension WHERE extname = '{extension}'") == 1


async def test_upgrade_downgrade_upgrade_check(engine_tam):
    """Tiêu chí T0.4: đi, về hết, đi lại đều thành công; sau đó model và migration không còn lệch."""
    await chay_alembic(engine_tam, "upgrade", "head")
    sau_upgrade = await trang_thai(engine_tam)

    await chay_alembic(engine_tam, "downgrade", "base")
    sau_downgrade = await trang_thai(engine_tam)
    assert sau_downgrade == {
        "bang": 1,
        "enum": 0,
        "check": 0,
        "index": 1,
        "sequence": 0,
        "ham": 0,
    }  # còn alembic_version
    assert await dem(engine_tam, "SELECT count(*) FROM alembic_version") == 0

    await chay_alembic(engine_tam, "upgrade", "head")
    assert await trang_thai(engine_tam) == sau_upgrade

    await chay_alembic(engine_tam, "check")  # raise CommandError nếu model còn khác DB


async def test_downgrade_tung_buoc_ve_0001_chi_go_phan_0002(engine_tam):
    await chay_alembic(engine_tam, "upgrade", "head")
    await chay_alembic(engine_tam, "downgrade", "0001")
    dang = await trang_thai(engine_tam)
    assert dang["bang"] == 66 and dang["enum"] == 33
    assert dang["check"] == 0 and dang["sequence"] == 0 and dang["ham"] == 0
    # Các index đặc biệt của 0002 đã bị gỡ, index thường của 0001 còn.
    assert await dem(engine_tam, "SELECT count(*) FROM pg_indexes WHERE indexname = 'san_pham_ten_trgm'") == 0
    assert await dem(engine_tam, "SELECT count(*) FROM pg_indexes WHERE indexname = 'ix_san_pham__loai_san_pham'") == 1


async def test_migration_khop_ddl_cua_erd():
    """Tiêu chí T0.4: sau `alembic upgrade head`, cấu trúc (bảng, cột, khóa ngoại, index, enum) khớp DDL của ERD."""
    assert await so_sanh_migration_voi_erd(settings.DATABASE_URL) == []


async def test_so_sanh_ket_qua_migration_van_bat_duoc_khac_biet():
    """Bộ lọc bỏ index đặc biệt không được nuốt mất lỗi thật."""
    async with db_tam(settings.DATABASE_URL, "kt_migr") as engine:
        goc = await cau_truc_tu_migration(engine)
        assert so_sanh(goc, goc) == []
        async with engine.begin() as conn:
            await conn.execute(text("DROP INDEX ix_san_pham__loai_san_pham"))
            await conn.execute(text("ALTER TABLE don_hang ALTER COLUMN ghi_chu TYPE varchar(10)"))
            await conn.execute(text("CREATE INDEX them_btree ON san_pham (ten)"))  # btree thường: phải bị thấy
            await conn.execute(text("CREATE INDEX them_phan ON san_pham (ten) WHERE la_noi_bat"))  # một phần: bị bỏ qua
        sau = await lay_cau_truc(engine, ket_qua_migration=True)
    khac = "\n".join(so_sanh(goc, sau, "goc", "sau"))
    assert "ix_san_pham__loai_san_pham" in khac or "'loai_san_pham'" in khac
    assert "cột don_hang.ghi_chu: kieu khác" in khac
    assert "('san_pham', ('ten',), False, False, False, False)" in khac  # them_btree
    assert khac.count("chỉ có ở sau") == 1  # chỉ them_btree; index một phần them_phan bị bỏ qua
    assert "them_phan" not in khac


async def test_alembic_khong_ghi_de_cau_hinh_log_cua_tien_trinh(engine_tam):
    """env.py chỉ gọi fileConfig khi không có cờ configure_logger=False; nếu gọi, nó thay handler của root logger
    bằng cấu hình trong alembic.ini và làm mất log JSON của ứng dụng."""
    root = logging.getLogger()
    mau = logging.NullHandler()
    root.addHandler(mau)
    try:
        truoc = root.handlers[:]
        await chay_alembic(engine_tam, "upgrade", "head")
        await chay_alembic(engine_tam, "downgrade", "base")
        assert root.handlers == truoc
    finally:
        root.removeHandler(mau)

"""So sánh cấu trúc hai database PostgreSQL.

So sánh: bảng, cột (kiểu, nullable, default, identity), khóa ngoại, index/unique, enum.
Dùng để chứng minh model (T0.3) và migration (T0.4) khớp đúng DDL của ERD (`docs/database/ERD_da_chinh_sua.sql`).
Bỏ qua: tên ràng buộc/index, comment, thuộc tính DEFERRABLE của khóa ngoại.

    uv run python scripts/so_sanh_schema.py            # so sánh create_all() từ model với DDL của ERD
"""

import asyncio
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

GOC_REPO = Path(__file__).resolve().parents[2]
ERD_SQL = GOC_REPO / "docs" / "database" / "ERD_da_chinh_sua.sql"

_TRUY_VAN_COT = """
SELECT c.relname, a.attname, format_type(a.atttypid, a.atttypmod), a.attnotnull,
       pg_get_expr(d.adbin, d.adrelid), a.attidentity <> ''
FROM pg_attribute a
JOIN pg_class c ON c.oid = a.attrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
WHERE n.nspname = 'public' AND c.relkind = 'r' AND a.attnum > 0 AND NOT a.attisdropped
"""

_TRUY_VAN_FK = """
SELECT c.conrelid::regclass::text,
       (SELECT array_agg(a.attname ORDER BY k.ord) FROM unnest(c.conkey) WITH ORDINALITY k(num, ord)
         JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.num),
       c.confrelid::regclass::text,
       (SELECT array_agg(a.attname ORDER BY k.ord) FROM unnest(c.confkey) WITH ORDINALITY k(num, ord)
         JOIN pg_attribute a ON a.attrelid = c.confrelid AND a.attnum = k.num)
FROM pg_constraint c
JOIN pg_namespace n ON n.oid = c.connamespace
WHERE c.contype = 'f' AND n.nspname = 'public'
"""

_TRUY_VAN_INDEX = """
SELECT i.indrelid::regclass::text,
       (SELECT array_agg(a.attname ORDER BY k.ord) FROM unnest(i.indkey::int2[]) WITH ORDINALITY k(num, ord)
         JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = k.num),
       i.indisunique, i.indisprimary, i.indpred IS NOT NULL, i.indexprs IS NOT NULL
FROM pg_index i
JOIN pg_class c ON c.oid = i.indrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
"""

_TRUY_VAN_ENUM = """
SELECT t.typname, array_agg(e.enumlabel ORDER BY e.enumsortorder)
FROM pg_type t
JOIN pg_enum e ON e.enumtypid = t.oid
JOIN pg_namespace n ON n.oid = t.typnamespace
WHERE n.nspname = 'public'
GROUP BY t.typname
"""


async def lay_cau_truc(engine: AsyncEngine) -> dict:
    """Đọc cấu trúc của database mà engine trỏ tới thành các tập/từ điển dễ so sánh."""
    async with engine.connect() as conn:
        cot = {
            (r[0], r[1]): {"kieu": r[2], "bat_buoc": r[3], "mac_dinh": r[4], "identity": r[5]}
            for r in (await conn.execute(text(_TRUY_VAN_COT))).all()
        }
        fk = {(r[0], tuple(r[1]), r[2], tuple(r[3])) for r in (await conn.execute(text(_TRUY_VAN_FK))).all()}
        index = {
            (r[0], tuple(r[1] or ()), r[2], r[3], r[4], r[5])
            for r in (await conn.execute(text(_TRUY_VAN_INDEX))).all()
        }
        enum = {r[0]: tuple(r[1]) for r in (await conn.execute(text(_TRUY_VAN_ENUM))).all()}
    return {"cot": cot, "fk": fk, "index": index, "enum": enum, "bang": {b for b, _ in cot}}


def so_sanh(a: dict, b: dict, ten_a: str = "A", ten_b: str = "B") -> list[str]:
    """Trả danh sách khác biệt dạng chữ. Danh sách rỗng nghĩa là hai cấu trúc khớp nhau."""
    loi: list[str] = []

    def hieu(ten, x, y, nhan_x, nhan_y):
        for muc in sorted(x - y, key=str):
            loi.append(f"{ten}: chỉ có ở {nhan_x}: {muc}")
        for muc in sorted(y - x, key=str):
            loi.append(f"{ten}: chỉ có ở {nhan_y}: {muc}")

    hieu("bảng", a["bang"], b["bang"], ten_a, ten_b)
    hieu("cột", set(a["cot"]), set(b["cot"]), ten_a, ten_b)
    for khoa in sorted(set(a["cot"]) & set(b["cot"])):
        ca, cb = a["cot"][khoa], b["cot"][khoa]
        for truong in ("kieu", "bat_buoc", "mac_dinh", "identity"):
            if ca[truong] != cb[truong]:
                loi.append(f"cột {khoa[0]}.{khoa[1]}: {truong} khác ({ten_a}={ca[truong]!r}, {ten_b}={cb[truong]!r})")
    hieu("khóa ngoại", a["fk"], b["fk"], ten_a, ten_b)
    hieu("index (bảng, cột, unique, pk, từng phần, biểu thức)", a["index"], b["index"], ten_a, ten_b)
    hieu("enum (tên)", set(a["enum"]), set(b["enum"]), ten_a, ten_b)
    for ten in sorted(set(a["enum"]) & set(b["enum"])):
        if a["enum"][ten] != b["enum"][ten]:
            loi.append(f"enum {ten}: giá trị/thứ tự khác ({ten_a}={a['enum'][ten]}, {ten_b}={b['enum'][ten]})")
    return loi


@asynccontextmanager
async def db_tam(url_goc: str, tien_to: str = "so_sanh"):
    """Tạo một database tạm (đã cài extension vector), trả engine, xóa khi xong."""
    goc = make_url(url_goc)
    ten = f"{tien_to}_{uuid.uuid4().hex[:12]}"
    admin = create_async_engine(goc.set(database="postgres"), isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{ten}"'))
    from app.core.db import tao_engine  # cùng cấu hình với engine production

    engine = tao_engine(goc.set(database=ten))
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        yield engine
    finally:
        await engine.dispose()
        async with admin.connect() as conn:
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{ten}" WITH (FORCE)'))
        await admin.dispose()


async def nap_ddl_erd(engine: AsyncEngine) -> None:
    """Nạp `ERD_da_chinh_sua.sql` (nhiều câu lệnh) vào database."""
    async with engine.connect() as conn:
        raw = await conn.get_raw_connection()
        await raw.driver_connection.execute(ERD_SQL.read_text(encoding="utf-8"))  # asyncpg: giao thức đơn giản
        await conn.commit()


async def cau_truc_tu_model(engine: AsyncEngine) -> dict:
    """`create_all()` từ model vào database rồi đọc cấu trúc."""
    from app.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return await lay_cau_truc(engine)


async def cau_truc_tu_erd(engine: AsyncEngine) -> dict:
    await nap_ddl_erd(engine)
    return await lay_cau_truc(engine)


async def so_sanh_model_voi_erd(url_goc: str) -> list[str]:
    async with db_tam(url_goc, "so_sanh_model") as e_model, db_tam(url_goc, "so_sanh_erd") as e_erd:
        tu_model = await cau_truc_tu_model(e_model)
        tu_erd = await cau_truc_tu_erd(e_erd)
    return so_sanh(tu_model, tu_erd, "model", "ERD")


async def _main() -> int:
    sys.path.insert(0, str(GOC_REPO / "backend"))
    from app.core.config import settings

    loi = await so_sanh_model_voi_erd(settings.DATABASE_URL)
    for dong in loi:
        print(dong)
    print(f"{len(loi)} khác biệt" if loi else "0 khác biệt: model khớp DDL của ERD")
    return 1 if loi else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))

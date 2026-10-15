import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Column, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.models import Base

config = context.config

# Khi gọi alembic từ trong tiến trình khác (test), đặt cfg.attributes["configure_logger"] = False để không ghi đè
# cấu hình log JSON của ứng dụng.
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _url() -> str:
    """URL ưu tiên: do nơi gọi đặt (test, -x), sau đó mới tới DATABASE_URL trong cấu hình ứng dụng."""
    return config.get_main_option("sqlalchemy.url") or settings.DATABASE_URL


def include_object(obj, name, type_, reflected, compare_to) -> bool:
    """Bỏ qua index đặc biệt khi so sánh model với DB (`alembic check`, autogenerate).

    DBML/model không biểu diễn được index một phần (WHERE), index biểu thức (f_unaccent(...)) và index không phải
    btree (GIN, HNSW). Chúng được tạo bằng SQL trong migration 0002 và liệt kê ở docs/spec/02-database.md mục 4.
    """
    if type_ == "index" and reflected:
        pg = obj.dialect_options["postgresql"]
        la_mot_phan = pg.get("where") is not None
        la_bieu_thuc = any(not isinstance(e, Column) for e in obj.expressions)
        khong_phai_btree = pg.get("using") not in (None, "btree")
        if la_mot_phan or la_bieu_thuc or khong_phai_btree:
            return False
    return True


def _cau_hinh(**tham_so) -> None:
    context.configure(
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
        **tham_so,
    )


def run_migrations_offline() -> None:
    """Sinh SQL ra màn hình mà không kết nối DB (`alembic upgrade head --sql`)."""
    _cau_hinh(url=_url(), literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    _cau_hinh(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = create_async_engine(_url(), poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

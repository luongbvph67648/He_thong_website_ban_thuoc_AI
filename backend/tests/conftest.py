"""Fixture dùng chung (spec 10 mục 2).

Toàn bộ test chạy trong một event loop duy nhất của cả phiên (`asyncio_default_*_loop_scope = "session"` trong
pyproject), nên fixture phạm vi phiên được dùng chung với mọi test.

Database:
- `engine_test`: database ở `DATABASE_URL_TEST`, tạo mới bằng `alembic upgrade head` rồi `seed_co_ban` MỘT lần mỗi phiên.
- `db` / `ket_noi`: mỗi test một transaction ngoài, rollback sau test; session dùng savepoint nên `commit()` trong code
  không ghi thật. Dùng cho hầu hết test.
- `db_that`: cho test cần commit thật (tranh chấp nhiều session); dọn bằng TRUNCATE sau test.
- `engine_migration`, `db_chua_seed`: database tạm đã migrate nhưng CHƯA seed, cho test về migration/seed.
- `engine_tam`, `engine_co_bang`: database tạm riêng cho một test.

HTTP: `app` (ứng dụng thật, request dùng chung transaction của test), `client`, `client_https` (giữ cookie refresh
`Secure`), `clients_theo_vai_tro` (ba client nhân viên một lúc), `dang_nhap_khach`,
`dang_nhap_duoc_si`, `dang_nhap_kho`, `dang_nhap_admin` (client đã gắn access token của tài khoản vừa tạo).
"""

import io
import json
import logging
import re
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import pytest_asyncio
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.bao_mat import tao_access_token
from app.core.config import settings
from app.core.db import PhienRequest, get_db, get_engine, tao_engine
from app.core.gioi_han import GioiHanCuaSoTruot, lay_bo_gioi_han_dang_nhap, lay_bo_gioi_han_otp
from app.core.log import BoLocRequestId, JsonFormatter
from app.core.phan_quyen import xoa_cache_quyen
from app.main import create_app
from app.seed.co_ban import seed_co_ban
from app.tich_hop.tin_nhan import lay_kenh_tin_nhan
from scripts.so_sanh_schema import cau_truc_tu_model, chay_alembic, db_tam
from tests.factories import tao_khach, tao_nhan_vien
from tests.ha_tang import don_dep_sau_commit, tao_lai_database


@pytest.fixture(scope="session", autouse=True)
def khoa_jwt_cho_test():
    """Khóa ký token riêng cho test, không phụ thuộc `.env` của máy."""
    cu = settings.JWT_SECRET
    settings.JWT_SECRET = SecretStr("khoa-jwt-chi-dung-trong-test-" + "0" * 32)
    yield
    settings.JWT_SECRET = cu


@pytest.fixture(autouse=True)
def cau_hinh_co_dinh_cho_test(monkeypatch, tmp_path):
    """Ghim các cấu hình ảnh hưởng hành vi mà `backend/.env` của máy dev có thể đổi (ví dụ `COOKIE_SECURE=false`).

    Thư mục lưu file là thư mục tạm của từng test: test upload không bao giờ ghi vào `backend/storage`.
    """
    monkeypatch.setattr(settings, "LUU_TRU_THU_MUC", str(tmp_path / "luu_tru"))
    monkeypatch.setattr(settings, "COOKIE_SECURE", True)
    monkeypatch.setattr(settings, "REFRESH_NGAY", 14)
    monkeypatch.setattr(settings, "JWT_ACCESS_PHUT", 15)
    xoa_cache_quyen()  # cache quyền của process không được sống sót qua các test (id vai trò, dữ liệu mỗi test một khác)
    yield
    xoa_cache_quyen()


# --- Database -------------------------------------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
async def engine_test():
    """Database test của cả phiên: migrate từ đầu, seed vai trò/quyền/cấu hình (không seed dữ liệu mẫu)."""
    await tao_lai_database(settings.DATABASE_URL_TEST)
    engine = tao_engine(settings.DATABASE_URL_TEST)
    try:
        await chay_alembic(engine, "upgrade", "head")
        async with AsyncSession(engine) as session, session.begin():
            await seed_co_ban(session)
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def engine_migration():
    """Database tạm đã `alembic upgrade head` nhưng chưa seed, dùng chung cho cả phiên (test phải tự rollback)."""
    async with db_tam(settings.DATABASE_URL, "nha_thuoc_mig") as engine:
        await chay_alembic(engine, "upgrade", "head")
        yield engine


async def _giao_dich_ngoai(engine: AsyncEngine):
    """Connection với một transaction ngoài; rollback khi xong để test không để lại dấu vết."""
    async with engine.connect() as conn:
        giao_dich = await conn.begin()
        try:
            yield conn
        finally:
            await giao_dich.rollback()


@pytest_asyncio.fixture
async def ket_noi(engine_test):
    async for conn in _giao_dich_ngoai(engine_test):
        yield conn


async def _session_tren(conn):
    session = AsyncSession(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()


@pytest_asyncio.fixture
async def db(ket_noi):
    """Session cho một test: `flush()` thấy dữ liệu, `commit()` chỉ giải phóng savepoint, cuối test rollback hết."""
    async for session in _session_tren(ket_noi):
        yield session


@pytest_asyncio.fixture
async def db_chua_seed(engine_migration):
    """Như `db` nhưng trên database chưa seed (test về seed và migration)."""
    async for conn in _giao_dich_ngoai(engine_migration):
        async for session in _session_tren(conn):
            yield session


@pytest_asyncio.fixture
async def db_that(engine_test):
    """Factory session cho test cần COMMIT THẬT (tranh chấp giữa nhiều session): `async with db_that() as s, s.begin()`.

    Sau test, mọi dữ liệu bị TRUNCATE (giữ vai trò; quyền, phân quyền và cấu hình được seed lại về mặc định). Test dùng `db_that` không được dùng
    đồng thời `db` để đọc kết quả, vì hai bên nằm ở hai transaction khác nhau.
    """
    try:
        yield async_sessionmaker(engine_test, expire_on_commit=False)
    finally:
        await don_dep_sau_commit(engine_test)


@pytest_asyncio.fixture
async def engine_tam():
    """CSDL tạm riêng cho một test: tạo mới trước test, xóa sau test (không đụng DB dev)."""
    async with db_tam(settings.DATABASE_URL, "nha_thuoc_t") as engine:
        yield engine


@pytest_asyncio.fixture
async def engine_co_bang(engine_tam):
    """CSDL tạm đã có đủ 65 bảng tạo từ model (create_all)."""
    await cau_truc_tu_model(engine_tam)
    return engine_tam


# --- Tin nhắn, giới hạn tần suất, thời gian -------------------------------------------------------------------------


class KenhGhiNho:
    """Kênh tin nhắn của test: ghi lại mọi tin thay vì gửi. Đặt `loi` để mô phỏng nhà cung cấp lỗi."""

    def __init__(self) -> None:
        self.sms: list[tuple[str, str]] = []
        self.email: list[tuple[str, str, str]] = []
        self.loi: Exception | None = None

    async def gui_sms(self, so_dien_thoai: str, noi_dung: str) -> None:
        if self.loi:
            raise self.loi
        self.sms.append((so_dien_thoai, noi_dung))

    async def gui_email(self, den: str, tieu_de: str, noi_dung_html: str) -> None:
        if self.loi:
            raise self.loi
        self.email.append((den, tieu_de, noi_dung_html))

    def ma_otp_cuoi(self) -> str:
        """Mã 6 số trong tin SMS gần nhất."""
        khop = re.search(r"\b(\d{6})\b", self.sms[-1][1])
        assert khop, f"SMS không có mã OTP: {self.sms[-1][1]!r}"
        return khop.group(1)

    def ma_otp_email_cuoi(self) -> str:
        """Mã 6 số trong email gần nhất."""
        khop = re.search(r"\b(\d{6})\b", self.email[-1][2])
        assert khop, "Email không có mã OTP"
        return khop.group(1)


@pytest.fixture
def kenh_tin_nhan() -> KenhGhiNho:
    return KenhGhiNho()


class MocThoiGian:
    """Đồng hồ giả cho service dùng `bay_gio_utc` (đã vá): `tien(phut=...)` nhảy tới."""

    def __init__(self, bat_dau: datetime) -> None:
        self.bay_gio = bat_dau

    def __call__(self) -> datetime:
        return self.bay_gio

    def tien(self, **khoang) -> None:
        self.bay_gio += timedelta(**khoang)


@pytest.fixture
def thoi_gian(monkeypatch) -> MocThoiGian:
    """Vá `bay_gio_utc` ở các module tài khoản; trả về đồng hồ để test chủ động tua thời gian.

    Chỉ vá thời gian của server (OTP, khóa tạm, hạn refresh token). Hạn của access token (JWT `exp`) do thư viện JWT
    tính theo đồng hồ thật nên không bị tua.
    """
    moc = MocThoiGian(datetime.now(UTC))
    for module in (
        "app.modules.tai_khoan.otp",
        "app.modules.tai_khoan.dang_ky",
        "app.modules.tai_khoan.dang_nhap",
        "app.modules.tai_khoan.phien",
        "app.modules.tai_khoan.router_cong_khai",
        "app.core.phan_quyen",
    ):
        monkeypatch.setattr(f"{module}.bay_gio_utc", moc, raising=False)
    return moc


@pytest.fixture
def gioi_han_ip() -> GioiHanCuaSoTruot:
    return GioiHanCuaSoTruot()


@pytest.fixture
def gioi_han_dang_nhap() -> GioiHanCuaSoTruot:
    return GioiHanCuaSoTruot()


# --- HTTP -----------------------------------------------------------------------------------------------------------


@pytest.fixture
def app(engine_test, ket_noi, kenh_tin_nhan, gioi_han_ip, gioi_han_dang_nhap):
    """Ứng dụng thật. Session của mỗi request chạy trên cùng transaction ngoài của test, nên thấy dữ liệu factory đã
    `flush()` và mọi thay đổi bị rollback cuối test. Vẫn giữ nguyên ngữ nghĩa của `get_db`: request thành công thì
    "commit" (giải phóng savepoint), request lỗi thì hoàn tác phần của request đó."""

    async def get_db_test():
        phien = PhienRequest(bind=ket_noi, join_transaction_mode="create_savepoint", expire_on_commit=False)
        async with phien, phien.begin():
            yield phien

    ung_dung = create_app()
    ung_dung.dependency_overrides[get_db] = get_db_test
    ung_dung.dependency_overrides[get_engine] = lambda: engine_test
    ung_dung.dependency_overrides[lay_kenh_tin_nhan] = lambda: kenh_tin_nhan
    ung_dung.dependency_overrides[lay_bo_gioi_han_otp] = lambda: gioi_han_ip
    ung_dung.dependency_overrides[lay_bo_gioi_han_dang_nhap] = lambda: gioi_han_dang_nhap
    return ung_dung


class ClientDaDangNhap(httpx.AsyncClient):
    """`AsyncClient` đã gắn access token; `tai_khoan` là `KhachHang` hoặc `NhanVien` tương ứng."""

    tai_khoan: object


def _tao_client(app, token: str | None = None) -> httpx.AsyncClient:
    tieu_de = {"Authorization": f"Bearer {token}"} if token else {}
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers=tieu_de)


@pytest_asyncio.fixture
async def client(app):
    async with _tao_client(app) as c:
        yield c


@pytest_asyncio.fixture
async def client_https(app):
    """Như `client` nhưng gọi qua https: cookie refresh có cờ `Secure` nên chỉ được gửi lại qua https."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as c:
        yield c


async def _dang_nhap(app, tai_khoan, aud):
    c = ClientDaDangNhap(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tao_access_token(tai_khoan.id, aud)}"},
    )
    c.tai_khoan = tai_khoan
    async with c:
        yield c


@pytest_asyncio.fixture
async def dang_nhap_khach(app, db):
    async for c in _dang_nhap(app, await tao_khach(db), "khach"):
        yield c


@pytest_asyncio.fixture
async def dang_nhap_duoc_si(app, db):
    async for c in _dang_nhap(app, await tao_nhan_vien(db, "PHARMACIST"), "noi_bo"):
        yield c


@pytest_asyncio.fixture
async def dang_nhap_kho(app, db):
    async for c in _dang_nhap(app, await tao_nhan_vien(db, "WAREHOUSE"), "noi_bo"):
        yield c


@pytest_asyncio.fixture
async def dang_nhap_admin(app, db):
    async for c in _dang_nhap(app, await tao_nhan_vien(db, "ADMIN"), "noi_bo"):
        yield c


@pytest.fixture
def mo_client():
    """Trả hàm mở httpx client gọi thẳng vào một app ASGI bất kỳ (app dựng riêng trong test)."""

    @asynccontextmanager
    async def _mo(app, **tuy_chon):
        transport = httpx.ASGITransport(app=app, **tuy_chon)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    return _mo


@pytest.fixture
def bat_log():
    """Gắn handler JSON vào logger "app" và trả hàm đọc lại các dòng log đã ghi."""
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(BoLocRequestId())
    logger = logging.getLogger("app")
    cu = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    def doc_dong():
        return [json.loads(d) for d in buf.getvalue().splitlines() if d.strip()]

    yield doc_dong
    logger.removeHandler(handler)
    logger.setLevel(cu)


@pytest_asyncio.fixture
async def clients_theo_vai_tro(app, db):
    """Ba client đã đăng nhập, mỗi vai trò một: `{"PHARMACIST": client, "WAREHOUSE": ..., "ADMIN": ...}`."""
    clients = {}
    for vai_tro in ("PHARMACIST", "WAREHOUSE", "ADMIN"):
        nv = await tao_nhan_vien(db, vai_tro)
        clients[vai_tro] = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {tao_access_token(nv.id, 'noi_bo')}"},
        )
    yield clients
    for c in clients.values():
        await c.aclose()

"""core/db.py: get_db mở transaction theo request, commit trước khi gửi response, rollback khi lỗi."""

import json

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.db import Db, get_engine
from app.core.loi import LoiNghiepVu
from app.main import create_app


@pytest.fixture
async def app_db(engine_tam):
    async with engine_tam.begin() as conn:
        await conn.execute(text("CREATE TABLE thu (id int PRIMARY KEY, ten text)"))
        # Ràng buộc DEFERRED: chỉ báo lỗi lúc COMMIT, dùng để chứng minh commit chạy trước khi gửi response.
        await conn.execute(
            text("CREATE TABLE thu_hoan (k int, CONSTRAINT duy_nhat UNIQUE (k) DEFERRABLE INITIALLY DEFERRED)")
        )

        await conn.execute(text("CREATE TABLE thu_ten (ten text UNIQUE)"))

    app = create_app()
    app.dependency_overrides[get_engine] = lambda: engine_tam

    @app.post("/thu/trung-ten")
    async def trung_ten(db: Db, ten: str):  # giá trị đi vào từ request, như dữ liệu thật của người dùng
        for _ in range(2):  # lần 2 vi phạm UNIQUE, ném IntegrityError không được dịch sang LoiNghiepVu
            await db.execute(text("INSERT INTO thu_ten VALUES (:t)"), {"t": ten})
        return {"ok": True}

    @app.post("/thu/ghi/{id_}")
    async def ghi(id_: int, db: Db):
        await db.execute(text("INSERT INTO thu VALUES (:i, 'a')"), {"i": id_})
        return {"ok": True}

    @app.post("/thu/ghi-roi-loi-nghiep-vu")
    async def ghi_roi_loi_nghiep_vu(db: Db):
        await db.execute(text("INSERT INTO thu VALUES (99, 'a')"))
        raise LoiNghiepVu("HET_HANG", "het hang")

    @app.post("/thu/ghi-roi-no")
    async def ghi_roi_no(db: Db):
        await db.execute(text("INSERT INTO thu VALUES (98, 'a')"))
        raise RuntimeError("hong")

    @app.post("/thu/hoan-trung")
    async def hoan_trung(db: Db):
        await db.execute(text("INSERT INTO thu_hoan VALUES (1), (1)"))  # chưa lỗi, chỉ lỗi khi commit
        return {"ok": True}

    @app.post("/thu/service-lo-commit")
    async def service_lo_commit(db: Db):
        await db.execute(text("INSERT INTO thu VALUES (97, 'a')"))
        await db.commit()  # vi phạm quy tắc: service không được commit
        return {"ok": True}

    @app.post("/thu/service-lo-rollback")
    async def service_lo_rollback(db: Db):
        await db.execute(text("INSERT INTO thu VALUES (96, 'a')"))
        await db.rollback()  # vi phạm quy tắc: muốn hoàn tác thì raise ngoại lệ
        return {"ok": True}

    @app.post("/thu/savepoint")
    async def savepoint(db: Db):
        await db.execute(text("INSERT INTO thu VALUES (1, 'a')"))
        try:
            async with db.begin_nested():  # hoàn tác một phần bằng savepoint là cách hợp lệ
                await db.execute(text("INSERT INTO thu VALUES (1, 'trung')"))
        except IntegrityError:
            pass
        return {"ok": True}

    @app.get("/thu/doc")
    async def doc(db: Db):
        return {"so_dong": await db.scalar(text("SELECT count(*) FROM thu"))}

    return app


async def _dem(engine, bang):
    async with engine.connect() as conn:
        return await conn.scalar(text(f"SELECT count(*) FROM {bang}"))


async def test_commit_khi_thanh_cong(app_db, engine_tam, mo_client):
    async with mo_client(app_db) as c:
        resp = await c.post("/thu/ghi/1")
        assert resp.status_code == 200
        # Nhìn từ một kết nối khác: dữ liệu đã được commit ngay khi nhận response.
        assert await _dem(engine_tam, "thu") == 1
        assert (await c.get("/thu/doc")).json() == {"so_dong": 1}  # request sau là session mới, thấy dữ liệu


async def test_rollback_khi_co_loi_nghiep_vu(app_db, engine_tam, mo_client):
    async with mo_client(app_db) as c:
        resp = await c.post("/thu/ghi-roi-loi-nghiep-vu")
    assert resp.status_code == 409
    assert resp.json()["ma_loi"] == "HET_HANG"
    assert await _dem(engine_tam, "thu") == 0


async def test_rollback_khi_co_loi_bat_ngo(app_db, engine_tam, mo_client):
    async with mo_client(app_db, raise_app_exceptions=False) as c:
        resp = await c.post("/thu/ghi-roi-no")
    assert resp.status_code == 500
    assert await _dem(engine_tam, "thu") == 0


async def test_commit_loi_phai_thanh_500_chu_khong_phai_200(app_db, engine_tam, mo_client):
    """Nếu commit chạy SAU khi response đã gửi, client sẽ nhận 200 dù dữ liệu không lưu được."""
    async with mo_client(app_db, raise_app_exceptions=False) as c:
        resp = await c.post("/thu/hoan-trung")
    assert resp.status_code == 500
    assert resp.json()["ma_loi"] == "LOI_HE_THONG"
    assert await _dem(engine_tam, "thu_hoan") == 0


async def test_moi_request_mot_session_rieng(app_db, engine_tam, mo_client):
    async with mo_client(app_db) as c:
        for i in (1, 2, 3):
            assert (await c.post(f"/thu/ghi/{i}")).status_code == 200
    assert await _dem(engine_tam, "thu") == 3


async def test_service_goi_commit_bi_tu_choi_va_khong_luu_gi(app_db, engine_tam, mo_client):
    """Commit giữa chừng làm mất tính nguyên tử: phần đã commit ở lại dù sau đó có lỗi."""
    async with mo_client(app_db, raise_app_exceptions=False) as c:
        resp = await c.post("/thu/service-lo-commit")
    assert resp.status_code == 500
    assert await _dem(engine_tam, "thu") == 0


async def test_service_goi_rollback_bi_tu_choi(app_db, engine_tam, mo_client):
    async with mo_client(app_db, raise_app_exceptions=False) as c:
        resp = await c.post("/thu/service-lo-rollback")
    assert resp.status_code == 500
    assert await _dem(engine_tam, "thu") == 0


async def test_savepoint_hoan_tac_mot_phan_van_hop_le(app_db, engine_tam, mo_client):
    async with mo_client(app_db) as c:
        resp = await c.post("/thu/savepoint")
    assert resp.status_code == 200
    assert await _dem(engine_tam, "thu") == 1


async def test_log_loi_csdl_khong_chua_tham_so_sql_va_detail_cua_postgres(app_db, mo_client, bat_log):
    """PostgreSQL ghi giá trị vi phạm vào DETAIL, SQLAlchemy ghi tham số vào [parameters]: đều là dữ liệu nhạy cảm."""
    async with mo_client(app_db) as c:
        resp = await c.post("/thu/trung-ten", params={"ten": "GIA-TRI-NHAY-CAM-0912345678"})
    assert resp.status_code == 500
    assert "NHAY-CAM" not in resp.text
    log = json.dumps(bat_log(), ensure_ascii=False)
    assert "IntegrityError" in log  # vẫn đủ thông tin để chẩn đoán
    assert "unique" in log.lower()
    assert "DETAIL: (đã ẩn)" in log  # chứng tỏ bộ che đã chạy chứ không phải log vốn không có DETAIL
    assert "NHAY-CAM" not in log
    assert "0912345678" not in log

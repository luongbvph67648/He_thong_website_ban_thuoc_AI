"""Trả lỗi mà vẫn giữ thay đổi trong transaction (đếm lần thử OTP, lần đăng nhập sai) và thông điệp validate tiếng Việt."""

from typing import Annotated, Literal

import pytest
from fastapi import FastAPI
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select

from app.core.db import Db
from app.core.loi import LoiNghiepVu, dang_ky_xu_ly_loi, tra_loi
from app.models.khach_hang import KhachHang


def test_tra_loi_lay_status_tu_bang_ma_loi_va_cung_dinh_dang_voi_raise():
    phan_hoi = tra_loi("OTP_SAI", "Mã OTP không đúng", {"con_lai": 2})
    assert phan_hoi.status_code == 422
    assert (
        phan_hoi.body
        == b'{"ma_loi":"OTP_SAI","thong_diep":"M\xc3\xa3 OTP kh\xc3\xb4ng \xc4\x91\xc3\xbang","chi_tiet":{"con_lai":2}}'
    )


def test_tra_loi_giu_header_va_chi_tiet_mac_dinh_null():
    phan_hoi = tra_loi("QUA_GIOI_HAN", "Quá nhanh", headers={"Retry-After": "30"})
    assert phan_hoi.status_code == 429 and phan_hoi.headers["retry-after"] == "30"
    assert b'"chi_tiet":null' in phan_hoi.body


def test_tra_loi_tu_choi_ma_loi_chua_khai_bao():
    with pytest.raises(ValueError, match="CHUA_KHAI_BAO"):
        tra_loi("CHUA_KHAI_BAO", "x")


def them_route(app):
    @app.post("/thu/tra-loi")
    async def tra(db: Db):
        db.add(
            KhachHang(ho_ten="Giữ lại", so_dien_thoai="0900000111", mat_khau_hash="x", dong_y_chinh_sach_luc=func.now())
        )
        await db.flush()
        return tra_loi("OTP_SAI", "Sai OTP")  # trả về bình thường => request commit

    @app.post("/thu/raise")
    async def nem(db: Db):
        db.add(
            KhachHang(
                ho_ten="Bị hoàn tác", so_dien_thoai="0900000222", mat_khau_hash="x", dong_y_chinh_sach_luc=func.now()
            )
        )
        await db.flush()
        raise LoiNghiepVu("OTP_SAI", "Sai OTP")  # raise => rollback

    return app


async def so_khach(db) -> int:
    return (await db.execute(select(func.count()).select_from(KhachHang))).scalar_one()


async def test_tra_loi_giu_thay_doi_con_raise_thi_hoan_tac(app, client, db):
    them_route(app)
    r1 = await client.post("/thu/tra-loi")
    assert r1.status_code == 422 and r1.json()["ma_loi"] == "OTP_SAI"
    assert await so_khach(db) == 1  # thay đổi được giữ dù client nhận lỗi 422

    r2 = await client.post("/thu/raise")
    assert r2.status_code == 422 and r2.json() == r1.json() | {"thong_diep": "Sai OTP"}
    assert await so_khach(db) == 1  # lần raise không để lại gì


# --- Thông điệp validate tiếng Việt ----------------------------------------------------------------------------------


class Mau(BaseModel):
    ma: Annotated[str, Field(pattern=r"^\d{6}$")]
    ten: Annotated[str, Field(min_length=2, max_length=5)]
    loai: Literal["a", "b"]
    so: int = Field(ge=1, le=10)

    @field_validator("ten")
    @classmethod
    def khong_phai_xxx(cls, v: str) -> str:
        if v == "xxx":
            raise ValueError("Tên không được là xxx")
        return v


@pytest.fixture
def app_mau():
    ung_dung = FastAPI()
    dang_ky_xu_ly_loi(ung_dung)

    @ung_dung.post("/mau")
    async def mau(du_lieu: Mau):
        return du_lieu

    return ung_dung


async def test_thong_diep_validate_tieng_viet_cho_cac_loai_pho_bien(app_mau, mo_client):
    async with mo_client(app_mau) as c:
        r = await c.post("/mau", json={"ma": "12ab", "ten": "x", "loai": "c", "so": 0})
    loi = {e["truong"]: e["loi"] for e in r.json()["chi_tiet"]}
    assert loi == {
        "ma": "Sai định dạng",
        "ten": "Quá ngắn",
        "loai": "Giá trị không hợp lệ",
        "so": "Phải lớn hơn hoặc bằng 1",
    }


async def test_qua_dai_va_vuot_gioi_han(app_mau, mo_client):
    async with mo_client(app_mau) as c:
        r = await c.post("/mau", json={"ma": "123456", "ten": "quadai", "loai": "a", "so": 11})
    loi = {e["truong"]: e["loi"] for e in r.json()["chi_tiet"]}
    assert loi == {"ten": "Quá dài", "so": "Phải nhỏ hơn hoặc bằng 10"}


async def test_loi_value_error_tu_validator_bo_tien_to_tieng_anh(app_mau, mo_client):
    async with mo_client(app_mau) as c:
        r = await c.post("/mau", json={"ma": "123456", "ten": "xxx", "loai": "a", "so": 5})
    assert r.json()["chi_tiet"] == [{"truong": "ten", "loi": "Tên không được là xxx"}]

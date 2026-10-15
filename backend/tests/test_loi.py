"""core/loi.py: LoiNghiepVu và định dạng lỗi thống nhất (spec 06 mục 4)."""

import re
from pathlib import Path

import pytest
from pydantic import BaseModel, Field

from app.core.loi import MA_LOI, LoiNghiepVu
from app.main import create_app

SPEC_06 = Path(__file__).resolve().parents[2] / "docs" / "spec" / "06-api.md"


class _Dong(BaseModel):
    san_pham_id: int
    so_luong: int = Field(gt=0)


class _Don(BaseModel):
    dong: list[_Dong]


@pytest.fixture
def app_loi():
    app = create_app()

    @app.get("/thu/het-hang")
    async def het_hang():
        raise LoiNghiepVu("HET_HANG", "Sản phẩm X chỉ còn 3 viên", chi_tiet={"san_pham_id": 12, "con_lai": 3})

    @app.get("/thu/khong-chi-tiet")
    async def khong_chi_tiet():
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy đơn hàng")

    @app.get("/thu/qua-gioi-han")
    async def qua_gioi_han():
        raise LoiNghiepVu("QUA_GIOI_HAN", "Bạn thao tác quá nhanh", headers={"Retry-After": "30"})

    @app.post("/thu/don")
    async def tao_don(don: _Don):
        return {"ok": True}

    @app.get("/thu/no")
    async def no():
        raise RuntimeError("mat-khau-bi-mat-khong-duoc-lo")

    return app


# ---------- LoiNghiepVu ----------


def test_http_status_lay_tu_bang_ma_loi():
    assert LoiNghiepVu("HET_HANG", "x").http_status == 409
    assert LoiNghiepVu("OTP_SAI", "x").http_status == 422


def test_cho_phep_truyen_http_status_neu_khop_bang():
    assert LoiNghiepVu("HET_HANG", "x", 409).http_status == 409


def test_tu_choi_http_status_lech_bang():
    with pytest.raises(ValueError, match="HET_HANG"):
        LoiNghiepVu("HET_HANG", "x", 400)


def test_tu_choi_ma_loi_chua_khai_bao():
    with pytest.raises(ValueError, match="MA_LA"):
        LoiNghiepVu("MA_LA", "x")


def test_bang_ma_loi_khop_spec_06():
    """Bảng mã lỗi trong code phải khớp bảng trong spec 06 mục 4 (spec là nguồn sự thật)."""
    spec = SPEC_06.read_text(encoding="utf-8")
    phan = spec.split("**Mã lỗi dùng chung**")[1].split("## 5.")[0]
    trong_spec: dict[str, int] = {}
    for dong in phan.splitlines():
        cot = [c.strip() for c in dong.strip().strip("|").split("|")]
        if dong.startswith("|") and cot[0].isdigit():
            for ma in re.findall(r"`([A-Z_]+)`", cot[1]):
                trong_spec[ma] = int(cot[0])
    assert trong_spec, "không đọc được bảng mã lỗi trong spec 06"
    assert trong_spec == MA_LOI


# ---------- Handler ----------


async def test_loi_nghiep_vu_tra_dung_dinh_dang(app_loi, mo_client):
    async with mo_client(app_loi) as c:
        resp = await c.get("/thu/het-hang")
    assert resp.status_code == 409
    assert resp.json() == {
        "ma_loi": "HET_HANG",
        "thong_diep": "Sản phẩm X chỉ còn 3 viên",
        "chi_tiet": {"san_pham_id": 12, "con_lai": 3},
    }


async def test_chi_tiet_luon_co_mat_dang_null(app_loi, mo_client):
    async with mo_client(app_loi) as c:
        resp = await c.get("/thu/khong-chi-tiet")
    assert resp.status_code == 404
    assert resp.json() == {"ma_loi": "KHONG_TIM_THAY", "thong_diep": "Không tìm thấy đơn hàng", "chi_tiet": None}


async def test_loi_nghiep_vu_giu_header_tuy_chinh(app_loi, mo_client):
    async with mo_client(app_loi) as c:
        resp = await c.get("/thu/qua-gioi-han")
    assert resp.status_code == 429
    assert resp.headers["retry-after"] == "30"
    assert resp.json()["ma_loi"] == "QUA_GIOI_HAN"


async def test_loi_validate_tra_400_va_danh_sach_truong(app_loi, mo_client):
    async with mo_client(app_loi) as c:
        resp = await c.post("/thu/don", json={"dong": [{"san_pham_id": 1, "so_luong": 2}, {"san_pham_id": 2}]})
    assert resp.status_code == 400
    body = resp.json()
    assert body["ma_loi"] == "DU_LIEU_KHONG_HOP_LE"
    assert body["thong_diep"] == "Dữ liệu không hợp lệ"
    assert body["chi_tiet"] == [{"truong": "dong.1.so_luong", "loi": "Bắt buộc nhập"}]


async def test_loi_validate_gia_tri_ngoai_gioi_han(app_loi, mo_client):
    async with mo_client(app_loi) as c:
        resp = await c.post("/thu/don", json={"dong": [{"san_pham_id": 1, "so_luong": 0}]})
    assert resp.status_code == 400
    loi = resp.json()["chi_tiet"]
    assert [e["truong"] for e in loi] == ["dong.0.so_luong"]
    assert loi[0]["loi"]  # có thông điệp, không rỗng


async def test_json_hong_tra_400_truong_body(app_loi, mo_client):
    async with mo_client(app_loi) as c:
        resp = await c.post("/thu/don", content="{khong phai json", headers={"content-type": "application/json"})
    assert resp.status_code == 400
    body = resp.json()
    assert body["ma_loi"] == "DU_LIEU_KHONG_HOP_LE"
    assert body["chi_tiet"][0]["truong"] == "body"


async def test_route_khong_ton_tai_tra_404_dung_dinh_dang(app_loi, mo_client):
    async with mo_client(app_loi) as c:
        resp = await c.get("/thu/khong-co-route-nay")
    assert resp.status_code == 404
    assert resp.json()["ma_loi"] == "KHONG_TIM_THAY"
    assert set(resp.json()) == {"ma_loi", "thong_diep", "chi_tiet"}


async def test_sai_phuong_thuc_tra_405_va_giu_header_allow(app_loi, mo_client):
    async with mo_client(app_loi) as c:
        resp = await c.post("/thu/het-hang")
    assert resp.status_code == 405
    assert resp.json()["ma_loi"] == "PHUONG_THUC_KHONG_DUOC_PHEP"
    assert "GET" in resp.headers["allow"]


async def test_loi_he_thong_khong_lo_chi_tiet_va_co_request_id(app_loi, mo_client):
    async with mo_client(app_loi, raise_app_exceptions=False) as c:
        resp = await c.get("/thu/no")
    assert resp.status_code == 500
    body = resp.json()
    assert body["ma_loi"] == "LOI_HE_THONG"
    assert "mat-khau-bi-mat" not in resp.text
    assert "Traceback" not in resp.text
    assert body["chi_tiet"] == {"request_id": resp.headers["x-request-id"]}

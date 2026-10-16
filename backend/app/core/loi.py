"""Lỗi nghiệp vụ và định dạng lỗi thống nhất (spec 06 mục 4).

Mọi lỗi trả về dạng {"ma_loi", "thong_diep", "chi_tiet"}. Mã lỗi mới phải thêm đồng thời vào
bảng ở spec 06 mục 4 và vào MA_LOI dưới đây; test_bang_ma_loi_khop_spec_06 sẽ báo nếu hai nơi lệch nhau.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic_core import to_jsonable_python
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

MA_LOI: dict[str, int] = {
    "DU_LIEU_KHONG_HOP_LE": 400,
    "CHUA_DANG_NHAP": 401,
    "TOKEN_HET_HAN": 401,
    "SAI_THONG_TIN_DANG_NHAP": 401,
    "KHONG_CO_QUYEN": 403,
    "TAI_KHOAN_BI_KHOA": 403,
    "PHAI_DOI_MAT_KHAU": 403,
    "TU_DUYET_KHONG_DUOC": 403,
    "TU_THAY_DOI_KHONG_DUOC": 403,
    "KHONG_TIM_THAY": 404,
    "PHUONG_THUC_KHONG_DUOC_PHEP": 405,
    "HET_HANG": 409,
    "CHUYEN_TRANG_THAI_KHONG_HOP_LE": 409,
    "DA_CO_NGUOI_XU_LY": 409,
    "GIA_DA_THAY_DOI": 409,
    "TRUNG_DU_LIEU": 409,
    "PHAI_CON_ADMIN": 409,
    "DU_LIEU_DA_THAY_DOI": 409,
    "DANH_MUC_CON_SAN_PHAM": 409,
    "DANH_MUC_CON_DANH_MUC": 409,
    "DU_LIEU_DANG_DUOC_SU_DUNG": 409,
    "THUOC_KE_DON_KHONG_VAO_GIO": 422,
    "VUOT_SO_LUONG_TOI_DA": 422,
    "MA_GIAM_GIA_KHONG_HOP_LE": 422,
    "QUA_THOI_HAN_DOI_TRA": 422,
    "HOAN_VUOT_SO_DA_TRA": 422,
    "OTP_SAI": 422,
    "OTP_HET_HAN": 422,
    "MAT_KHAU_CU_SAI": 422,
    "QUA_GIOI_HAN": 429,
    "LOI_DOI_TAC": 502,
    "LOI_HE_THONG": 500,
}

MA_LOI_THEO_STATUS_HTTP: frozenset[str] = frozenset({"LOI_HTTP"})
"""Mã lỗi không gắn với một HTTP status cố định (giữ nguyên status của lỗi HTTP 4xx do framework phát sinh)."""

THONG_DIEP_LOI_HE_THONG = "Lỗi hệ thống, vui lòng thử lại sau"

# Lỗi HTTP do framework tự phát sinh (route không có, sai phương thức...) quy về mã lỗi của hệ thống.
_MA_LOI_THEO_HTTP = {
    401: "CHUA_DANG_NHAP",
    403: "KHONG_CO_QUYEN",
    404: "KHONG_TIM_THAY",
    405: "PHUONG_THUC_KHONG_DUOC_PHEP",
    429: "QUA_GIOI_HAN",
}
_THONG_DIEP_THEO_HTTP = {
    401: "Bạn chưa đăng nhập",
    403: "Bạn không có quyền thực hiện thao tác này",
    404: "Không tìm thấy",
    405: "Phương thức HTTP không được phép",
    429: "Bạn thao tác quá nhanh, vui lòng thử lại sau",
}

# Thông điệp tiếng Việt cho các loại lỗi validate phổ biến; loại khác dùng nguyên văn của Pydantic.
_LOI_VALIDATE_TIENG_VIET = {
    "missing": "Bắt buộc nhập",
    "string_type": "Phải là chuỗi",
    "int_parsing": "Phải là số nguyên",
    "int_type": "Phải là số nguyên",
    "float_parsing": "Phải là số",
    "bool_parsing": "Phải là true hoặc false",
    "json_invalid": "JSON không hợp lệ",
    "string_too_short": "Quá ngắn",
    "string_too_long": "Quá dài",
    "string_pattern_mismatch": "Sai định dạng",
    "literal_error": "Giá trị không hợp lệ",
    "enum": "Giá trị không hợp lệ",
    "greater_than_equal": "Phải lớn hơn hoặc bằng {ge}",
    "less_than_equal": "Phải nhỏ hơn hoặc bằng {le}",
    "greater_than": "Phải lớn hơn {gt}",
    "less_than": "Phải nhỏ hơn {lt}",
}


class LoiNghiepVu(Exception):  # noqa: N818 - tên theo spec
    """Lỗi do vi phạm quy tắc nghiệp vụ. Service raise, handler đổi thành phản hồi JSON đúng định dạng."""

    def __init__(
        self,
        ma_loi: str,
        thong_diep: str,
        http_status: int | None = None,
        chi_tiet: Any = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        if ma_loi not in MA_LOI:
            raise ValueError(f"Mã lỗi chưa khai báo: {ma_loi}. Thêm vào spec 06 mục 4 và MA_LOI trong core/loi.py")
        if http_status is not None and http_status != MA_LOI[ma_loi]:
            raise ValueError(f"{ma_loi} phải có HTTP {MA_LOI[ma_loi]} theo spec 06, không phải {http_status}")
        super().__init__(thong_diep)
        self.ma_loi = ma_loi
        self.thong_diep = thong_diep
        self.http_status = MA_LOI[ma_loi]
        self.chi_tiet = chi_tiet
        self.headers = headers


def phan_hoi_loi(
    http_status: int, ma_loi: str, thong_diep: str, chi_tiet: Any = None, headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        # to_jsonable_python hiểu Decimal, date, model Pydantic (kể cả kiểu Tien) mà json.dumps thuần không hiểu.
        content={"ma_loi": ma_loi, "thong_diep": thong_diep, "chi_tiet": to_jsonable_python(chi_tiet)},
        headers=headers,
    )


def tra_loi(ma_loi: str, thong_diep: str, chi_tiet: Any = None, headers: dict[str, str] | None = None) -> JSONResponse:
    """Phản hồi lỗi cùng định dạng với `LoiNghiepVu` nhưng được TRẢ VỀ thay vì ném.

    Dùng khi phải giữ thay đổi đã ghi dù trả lỗi (đếm lần thử OTP, đếm lần đăng nhập sai): route trả về bình thường nên
    `get_db` commit; còn `raise LoiNghiepVu` luôn làm request bị rollback.
    """
    if ma_loi not in MA_LOI:
        raise ValueError(f"Mã lỗi chưa khai báo: {ma_loi}. Thêm vào spec 06 mục 4 và MA_LOI trong core/loi.py")
    return phan_hoi_loi(MA_LOI[ma_loi], ma_loi, thong_diep, chi_tiet, headers)


def _truong(loi: dict[str, Any]) -> str:
    if loi["type"] == "json_invalid":
        return "body"
    duong_dan = ".".join(str(phan) for phan in loi["loc"][1:])  # bỏ phần đầu (body/query/path/header)
    return duong_dan or str(loi["loc"][0])


def phan_hoi_loi_he_thong(request_id: str | None) -> JSONResponse:
    """Lỗi 500: không lộ chi tiết, chỉ trả request_id để người dùng báo lại và dev tra log."""
    return phan_hoi_loi(500, "LOI_HE_THONG", THONG_DIEP_LOI_HE_THONG, {"request_id": request_id})


async def _xu_ly_loi_nghiep_vu(request: Request, loi: LoiNghiepVu) -> JSONResponse:
    return phan_hoi_loi(loi.http_status, loi.ma_loi, loi.thong_diep, loi.chi_tiet, loi.headers)


def _thong_diep_validate(loi: dict[str, Any]) -> str:
    mau = _LOI_VALIDATE_TIENG_VIET.get(loi["type"])
    if mau is not None:
        return mau.format(**(loi.get("ctx") or {}))
    # Lỗi từ validator tự viết (ValueError): Pydantic thêm tiền tố tiếng Anh, bỏ đi để giữ nguyên thông điệp tiếng Việt.
    return loi["msg"].removeprefix("Value error, ")


async def _xu_ly_loi_validate(request: Request, loi: RequestValidationError) -> JSONResponse:
    chi_tiet = [{"truong": _truong(e), "loi": _thong_diep_validate(e)} for e in loi.errors()]
    return phan_hoi_loi(400, "DU_LIEU_KHONG_HOP_LE", "Dữ liệu không hợp lệ", chi_tiet)


async def _xu_ly_loi_http(request: Request, loi: StarletteHTTPException) -> JSONResponse:
    ma_loi = _MA_LOI_THEO_HTTP.get(loi.status_code)
    if ma_loi:
        return phan_hoi_loi(
            loi.status_code, ma_loi, _THONG_DIEP_THEO_HTTP[loi.status_code], headers=dict(loi.headers or {})
        )
    if loi.status_code >= 500:  # không echo detail (có thể là thông tin nội bộ) cho client
        logger.warning("HTTPException %s không ánh xạ được: %s", loi.status_code, loi.detail)
        return phan_hoi_loi_he_thong(getattr(request.state, "request_id", None))
    return phan_hoi_loi(loi.status_code, "LOI_HTTP", str(loi.detail), headers=dict(loi.headers or {}))


def dang_ky_xu_ly_loi(app: FastAPI) -> None:
    app.add_exception_handler(LoiNghiepVu, _xu_ly_loi_nghiep_vu)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _xu_ly_loi_validate)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, _xu_ly_loi_http)  # type: ignore[arg-type]
    # Lỗi không bắt được (500) do RequestIdMiddleware xử lý, không đăng ký ở đây: handler cho Exception chạy trong
    # ServerErrorMiddleware, nơi luôn ném lại ngoại lệ sau khi gửi response khiến uvicorn in thêm một traceback thô.

# Backend: quy ước FastAPI

Đọc kèm `docs/spec/01-kien-truc.md` (cấu trúc), `06-api.md` (API) và `10-kiem-thu.md` (test).

## Phân lớp
```
app/modules/<module>/
  router_cong_khai.py   # route không cần đăng nhập (nếu có)
  router_khach.py       # /api/v1/toi/...       Depends(khach_hien_tai)
  router_noi_bo.py      # /api/v1/noi-bo/...    Depends(yeu_cau_quyen(...))
  schemas.py            # Pydantic: <Ten>Tao, <Ten>Sua, <Ten>Doc, <Ten>Loc
  service.py            # nghiệp vụ, transaction, gọi module khác qua service của module đó
  repo.py               # truy vấn SQLAlchemy dùng lại nhiều nơi (không bắt buộc)
```
- **Router mỏng.** Router chỉ nhận request, gọi service và trả schema. Không viết truy vấn hay logic trong router.
- **Service nhận `db: AsyncSession` và tác nhân** (`KhachHang` hoặc `NhanVien`), trả model hoặc schema.
- **Service không commit.** Route khai báo `db: Db` (`from app.core.db import Db`); session này tự commit khi route trả về thành công và rollback khi có ngoại lệ.
  - `db.commit()` và `db.rollback()` bị chặn và raise `RuntimeError`, vì commit giữa chừng làm phần đã commit ở lại dù sau đó request lỗi.
  - Cần ID của dòng vừa thêm: `await db.flush()`. Cần hoàn tác một phần: `async with db.begin_nested():` (savepoint). Muốn hủy cả request: raise `LoiNghiepVu`.
  - Dependency (ví dụ `khach_hien_tai`) dùng `Db` phải là hàm async thường, không `yield`; dependency có `yield` với scope mặc định mà phụ thuộc `Db` sẽ báo `DependencyScopeError` ngay khi dựng app.
  - Luôn dùng alias `Db`, **không** tự viết `Depends(get_db)`: alias đã đặt `scope="function"` để commit chạy **trước** khi gửi response (mặc định commit chạy sau, client nhận 200 dù commit lỗi).
  - Response streaming (SSE) không dùng `db` của request bên trong generator vì session đã đóng; generator tự mở `AsyncSession(engine)` riêng.
  - Việc phải lưu dù request thất bại (ví dụ ghi payload IPN trước khi xử lý) cũng dùng session riêng.
- **Model dùng chung** đặt ở `app/models/` (theo nhóm ERD). Module không tự khai báo model.
- **Gọi chéo module** chỉ qua hàm public trong `service.py` của module kia. Riêng tồn kho và trạng thái đơn bắt buộc đi qua:
  - `modules/kho/ton_kho.py`
  - `modules/ban_hang/trang_thai.py`
- **Đặt tên:**
  - Thực thể, cột và hàm nghiệp vụ dùng tiếng Việt không dấu, giống ERD (`tao_don_hang`, `xac_nhan_don`).
  - Hạ tầng kỹ thuật dùng tiếng Anh (`get_db`, `settings`).

## Xác thực và phân quyền (`app/core/phan_quyen.py`)
```python
@router.post("/don-hang/{ma_don}/xac-nhan", response_model=DonHangDoc)
async def xac_nhan(
    ma_don: str,
    nv: NhanVien = Depends(yeu_cau_quyen("order.confirm")),
    db: AsyncSession = Depends(get_db),
):
    return await service.xac_nhan_don(db, ma_don, nv)

@router.get("/phieu-nhap")                      # Admin chỉ xem: muc="xem"
async def ds_phieu_nhap(nv=Depends(yeu_cau_quyen("stock.import", muc="xem")), ...): ...

@router.get("/don-hang/{ma_don}")              # khách: chỉ đơn của mình, không có thì 404
async def don_cua_toi(ma_don: str, kh: KhachHang = Depends(khach_hien_tai), db=Depends(get_db)):
    return await service.lay_don_cua_khach(db, kh.id, ma_don)
```
- **`muc="xem"`:** vai trò có quyền ở mức `chi_xem` hoặc `day_du` đều qua được.
- **`muc="day_du"` (mặc định):** chỉ vai trò có quyền mức `day_du`.
- **Thêm route nội bộ mới:** phải thêm vào `tests/phan_quyen/registry.py`. Nếu thiếu, test ma trận sẽ fail.
- **Kiểm tra ngoài mã quyền** (tách nhiệm vụ, chủ sở hữu, dữ liệu sức khỏe) viết trong service, lỗi trả qua `LoiNghiepVu`.

## Lỗi
- Raise `LoiNghiepVu("HET_HANG", "Sản phẩm X chỉ còn 3 viên", chi_tiet={...})`, không raise `HTTPException` thô. HTTP status tự lấy từ bảng mã lỗi.
- Mã lỗi viết HOA_KHONG_DAU. Bảng mã lỗi dùng chung ở `docs/spec/06-api.md` mục 4.
- Mã lỗi mới thì thêm vào **cả** bảng đó **và** `MA_LOI` trong `core/loi.py` (test `test_bang_ma_loi_khop_spec_06` báo nếu lệch).
- Lỗi validate của FastAPI, 404, 405 và lỗi không bắt được đều tự trả đúng định dạng `{ma_loi, thong_diep, chi_tiet}`. Lỗi 500 không lộ chi tiết, chỉ trả `request_id`.

## Log
- Log JSON một dòng (`core/log.py`), mọi dòng tự có `request_id`. Dùng `logging.getLogger(__name__)`, không dùng `print`.
- Thêm trường riêng qua `extra={...}`, ví dụ `logger.info("Đã tạo đơn", extra={"ma_don": ma})`.
- **Không ghi** mật khẩu, OTP, token, dữ liệu sức khỏe, và không ghi query string. Log truy cập chỉ ghi **mẫu route** (`/xac-nhan-don/{token}`), không ghi giá trị trong path; log truy cập của uvicorn bị tắt vì nó in cả query string.
- Tạo engine qua `core.db.tao_engine()` (đã bật `hide_parameters`) để lỗi SQL không ghi tham số. Log lỗi tự che các dòng `DETAIL:`/`HINT:`/`CONTEXT:` của PostgreSQL (chứa giá trị vi phạm).
- Lỗi không bắt được do `RequestIdMiddleware` xử lý (log + trả 500), không ném lại cho uvicorn.

## CSDL
- **SQLAlchemy 2 async:** dùng `select()`, không dùng Query API cũ.
- **Tải quan hệ:** dùng `selectinload` rõ ràng, tránh lazy load trong async.
- **Khóa ghi:** `select(LoThuoc).where(...).order_by(LoThuoc.id).with_for_update()`. Luôn khóa theo thứ tự id tăng để tránh deadlock.
- **Xóa mềm:** truy vấn mặc định lọc `deleted_at IS NULL` qua helper `chua_xoa(Model)`.
- **Tiền:** `Decimal`, làm tròn qua `core.tien.lam_tron_vnd()` (half-up). `cong()`/`tru()` cộng trừ rồi làm tròn một lần; hàm tiền từ chối `float`. Trong schema Pydantic dùng kiểu `Tien` (không âm, dưới 10^12, số đồng nguyên, xuất JSON dạng chuỗi `"125000.00"`); chênh lệch có thể âm thì dùng `TienCoDau`.
- **Thời gian:** `core.thoi_gian.bay_gio_utc()`, `hom_nay_vn()`.
- **Phân trang:** route nhận `tp: PhanTrang`, truy vấn đã có `ORDER BY` thì `dong, tong = await lay_trang(db, stmt, tp)`, trả `tao_trang(dong, tong, tp)` với `response_model=Trang[Schema]`.
- **Schema:** thay đổi phải theo `/doi-schema`. Migration mới đặt tên `NNNN_<mo_ta>.py`.

## Job nền (`app/jobs/`)
- Mỗi job là một hàm `async def chay(db)` trong file `htXX_<ten>.py`, đăng ký lịch trong `app/jobs/__main__.py`.
- Bọc bằng `pg_try_advisory_lock(<số cố định của job>)` để không chạy chồng.
- Job phải idempotent: chạy lại không gây sai.

## Test
- Cấu trúc `tests/` giống `app/modules/`. Dùng fixture `client`, `db`, `dang_nhap_khach`, `dang_nhap_duoc_si`, `dang_nhap_kho`, `dang_nhap_admin` và factories trong `tests/factories.py`.
- Test API qua HTTP (`AsyncClient`); test bất biến/tranh chấp gọi service trực tiếp với nhiều session.
- Fixture `engine_tam` tạo một database tạm cho riêng test (xóa sau test); fixture `mo_client(app, raise_app_exceptions=False)` gọi thẳng vào app, dùng tham số `False` khi test lỗi 500.
- Không gọi dịch vụ ngoài: `AI_GIA_LAP=true`, adapter tích hợp ở chế độ `gia`.
- Chạy nhanh một phần: `uv run pytest tests/ban_hang -q -x`.

## Python
- Bật `ruff` (lint + format) cho mọi file.
- Type hint đầy đủ cho hàm public.
- Docstring tiếng Việt một dòng cho service public.
- Không dùng `print`; dùng `logging.getLogger(__name__)`.

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
- **Service không commit.** Session theo request (`core/db.get_db`) tự commit khi thành công và rollback khi có ngoại lệ.
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
- Raise `LoiNghiepVu(ma_loi="HET_HANG", thong_diep="...", http_status=409, chi_tiet={...})`, không raise `HTTPException` thô.
- Mã lỗi viết HOA_KHONG_DAU. Bảng mã lỗi dùng chung ở `docs/spec/06-api.md` mục 4.
- Mã lỗi mới thì thêm vào bảng đó.

## CSDL
- **SQLAlchemy 2 async:** dùng `select()`, không dùng Query API cũ.
- **Tải quan hệ:** dùng `selectinload` rõ ràng, tránh lazy load trong async.
- **Khóa ghi:** `select(LoThuoc).where(...).order_by(LoThuoc.id).with_for_update()`. Luôn khóa theo thứ tự id tăng để tránh deadlock.
- **Xóa mềm:** truy vấn mặc định lọc `deleted_at IS NULL` qua helper `chua_xoa(Model)`.
- **Tiền:** `Decimal`, làm tròn qua `core.tien.lam_tron_vnd()`.
- **Thời gian:** `core.thoi_gian.bay_gio_utc()`, `hom_nay_vn()`.
- **Schema:** thay đổi phải theo `/doi-schema`. Migration mới đặt tên `NNNN_<mo_ta>.py`.

## Job nền (`app/jobs/`)
- Mỗi job là một hàm `async def chay(db)` trong file `htXX_<ten>.py`, đăng ký lịch trong `app/jobs/__main__.py`.
- Bọc bằng `pg_try_advisory_lock(<số cố định của job>)` để không chạy chồng.
- Job phải idempotent: chạy lại không gây sai.

## Test
- Cấu trúc `tests/` giống `app/modules/`. Dùng fixture `client`, `db`, `dang_nhap_khach`, `dang_nhap_duoc_si`, `dang_nhap_kho`, `dang_nhap_admin` và factories trong `tests/factories.py`.
- Test API qua HTTP (`AsyncClient`); test bất biến/tranh chấp gọi service trực tiếp với nhiều session.
- Không gọi dịch vụ ngoài: `AI_GIA_LAP=true`, adapter tích hợp ở chế độ `gia`.
- Chạy nhanh một phần: `uv run pytest tests/ban_hang -q -x`.

## Python
- Bật `ruff` (lint + format) cho mọi file.
- Type hint đầy đủ cho hàm public.
- Docstring tiếng Việt một dòng cho service public.
- Không dùng `print`; dùng `logging.getLogger(__name__)`.

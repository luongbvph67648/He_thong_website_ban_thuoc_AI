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
- **Model** ở `app/models/` (7 file theo nhóm ERD, `from app.models import Base` nạp đủ 65 bảng). Model chỉ khai báo cấu trúc, không có logic nghiệp vụ.
- **Enum:** mỗi enum PostgreSQL có một lớp `StrEnum` cùng tên PascalCase trong `app/models/enums.py` (`TrangThaiDon.cho_xac_nhan`, so sánh bằng `is` hoặc `==`) và một kiểu `KIEU_<TEN>` dùng trong `mapped_column`. Giá trị trả về từ DB đã là thành viên enum.
- **Tải quan hệ:** mọi `relationship` đặt `lazy="raise"`, truy cập quan hệ chưa nạp sẽ báo lỗi thay vì âm thầm chạy truy vấn (không dùng được trong async). Phải nạp rõ ràng: `select(DonHang).options(selectinload(DonHang.chi_tiet))`. Tên quan hệ nhiều-một lấy từ cột khóa ngoại bỏ đuôi `_id` (`DonHang.khach_hang`); quan hệ một-nhiều chọn lọc (`DonHang.chi_tiet`, `SanPham.don_vi_quy_doi`...) xem trong model. Khóa ngoại kép (`ct_don_hang.(don_vi_id, san_pham_id)`) không có quan hệ, dùng join tường minh.
- **Khóa chính** dùng `Identity` (như DDL của ERD), không dùng serial. Giá trị mặc định (`created_at`, trạng thái, số lượng 0...) là `server_default`; sau `flush()`/`refresh()` ORM đọc lại từ DB.
- **Cột tên `metadata`** (`tai_lieu_tri_thuc`) có thuộc tính Python là `metadata_`, vì `metadata` bị `DeclarativeBase` giữ riêng.
- **Khóa ghi:** `select(LoThuoc).where(...).order_by(LoThuoc.id).with_for_update()`. Luôn khóa theo thứ tự id tăng để tránh deadlock. Dùng `ton_kho.khoa_cac_lo(db, ids)`: nó khóa theo id tăng, dedupe, báo `LookupError` nếu thiếu lô và dùng `populate_existing` để đối tượng đã nạp từ trước được làm mới theo dòng vừa khóa (nếu không, `+=` trên số cũ làm mất cập nhật của giao dịch khác).
- **Tồn kho:** chỉ đổi qua `modules/kho/ton_kho.py`. Hiện có `nhap_kho(db, lo, so_luong, ChungTu(loai, id, nhan_vien_id))`; các hàm còn lại (spec 04 mục 3) thêm ở T3.1/T4.x, cùng một khuôn: khóa lô, đổi số, ghi `bien_dong_kho` với `ton_sau`, flush. `so_luong` phải là `int` dương (float/bool/0 bị từ chối).
- **Xóa mềm:** truy vấn mặc định lọc `deleted_at IS NULL` qua helper `chua_xoa(Model)`.
- **Tiền:** `Decimal`, làm tròn qua `core.tien.lam_tron_vnd()` (half-up). `cong()`/`tru()` cộng trừ rồi làm tròn một lần; hàm tiền từ chối `float`. Trong schema Pydantic dùng kiểu `Tien` (không âm, dưới 10^12, số đồng nguyên, xuất JSON dạng chuỗi `"125000.00"`); chênh lệch có thể âm thì dùng `TienCoDau`.
- **Thời gian:** `core.thoi_gian.bay_gio_utc()`, `hom_nay_vn()`.
- **Giữ thay đổi dù trả lỗi:** `raise LoiNghiepVu` luôn rollback. Cần lưu bộ đếm (lần thử OTP, lần đăng nhập sai, khóa tạm) thì route TRẢ VỀ `core.loi.tra_loi("OTP_SAI", "...", chi_tiet)` (cùng định dạng, route kết thúc bình thường nên `get_db` commit). Service trả kết quả (enum/dataclass) thay vì ném, như `otp.kiem_tra_otp`.
- **Chống dò tài khoản:** API công khai không được cho phép phân biệt tài khoản có hay không qua phản hồi, thời điểm hay bộ đếm; xem `otp.py`. Đoạn nghiệp vụ mà hai nhánh phải giống hệt nhau cần test so sánh chuỗi phản hồi của hai nhánh.
- **Giới hạn tần suất:** `core.gioi_han.GioiHanCuaSoTruot` (bộ nhớ, theo IP), giới hạn đọc từ `cau_hinh` mỗi lần; theo SĐT/tài khoản thì đếm trong DB. Dependency để test thay bằng bộ riêng.
- **Tin nhắn:** gửi qua `tich_hop.tin_nhan.KenhTinNhan` (dependency `lay_kenh_tin_nhan`), không tự gọi SMTP/SMS. SĐT chuẩn hóa bằng `core.dien_thoai.chuan_hoa_sdt`, ghi log phải `che_sdt`.
- **Mật khẩu:** `core.bao_mat.bam_mat_khau` / `kiem_tra_mat_khau` (Argon2id; chuỗi băm hỏng trả `False`, không ném lỗi); trong route dùng bản `_async` (`bam_mat_khau_async`, `kiem_tra_mat_khau_async`) vì Argon2 tốn CPU và sẽ chặn vòng lặp sự kiện, `mat_khau_du_manh` (≥ 8 ký tự, có chữ và số). Không tự gọi `argon2` ở nơi khác.
- **Mã chứng từ:** `core.ma_chung_tu.ma_nhan_vien(db)`, `ma_phieu(db, "phieu_nhap")`, `ma_lenh_thu_hoi(db)` lấy số từ sequence (spec 04 mục 7); sequence không rollback nên mã có thể nhảy số, không bao giờ trùng. Mã của khách (`DH...`) dùng ký tự ngẫu nhiên, làm ở T4.x.
- **Slug:** `core.slug.tao_slug("Thuốc ho Bổ phế")` → `thuoc-ho-bo-phe`.
- **Phân trang:** route nhận `tp: PhanTrang`, truy vấn đã có `ORDER BY` thì `dong, tong = await lay_trang(db, stmt, tp)`, trả `tao_trang(dong, tong, tp)` với `response_model=Trang[Schema]`.
- **Schema:** thay đổi phải theo `/doi-schema`. Migration mới đặt tên `NNNN_<mo_ta>.py`. Sau khi sửa model hoặc migration, chạy `uv run python scripts/so_sanh_schema.py` để chắc cả model lẫn kết quả `alembic upgrade head` vẫn khớp DDL của ERD (test `test_model_khop_ddl_cua_erd` và `test_migration_khop_ddl_cua_erd` cũng kiểm tra).
- **Migration (Alembic):** `0001_nen` (bảng, enum, extension) và `0002_rang_buoc` (hàm `f_unaccent`, CHECK, partial unique, index GIN/HNSW, sequence) là bản chụp bất biến, không sửa. Quy ước khi thêm migration mới:
  - Enum tạo bằng `op.execute("CREATE TYPE ...")` và cột dùng `postgresql.ENUM(..., create_type=False)`; autogenerate sinh `sa.Enum` inline sẽ tạo kiểu hai lần.
  - CHECK, partial unique, index biểu thức/GIN/HNSW, hàm và sequence **viết tay bằng SQL** và đặt tên rõ (`ck_<bảng>_<mô tả>`). Model và `alembic check` không biết chúng: `env.py::include_object` bỏ qua index một phần, biểu thức, không phải btree; Alembic không so CHECK/hàm/sequence.
  - Thêm CHECK mới thì thêm một case vào `tests/test_rang_buoc.py` (test `test_moi_check_trong_db_deu_co_test` fail nếu thiếu); thêm partial unique thì thêm vào `CAC_PARTIAL_UNIQUE`.
  - Test chạy Alembic qua `scripts.so_sanh_schema.chay_alembic(engine, "upgrade", "head")` (chạy trong luồng riêng, không ghi đè log). Không gọi `command.upgrade` trực tiếp trong test async vì `env.py` tự dựng vòng lặp asyncio.

## Seed (`app/seed/`)
- `uv run python -m app.seed` (vai trò, quyền, cấu hình mặc định, Admin từ `ADMIN_EMAIL`/`ADMIN_MAT_KHAU`) và `--mau` (dữ liệu mẫu để demo). Chạy lại an toàn.
- `seed_co_ban(db, admin=...)` và `seed_mau(db)` nhận session, **không commit** (CLI bọc transaction). Test dùng trực tiếp hai hàm này.
- Quyền đọc từ `docs/spec/data/quyen.yaml`: danh mục `quyen` đồng bộ theo file (quyền thừa bị gỡ), nhưng cách gán `vai_tro_quyen` chỉ khởi tạo cho quyền MỚI để không hoàn tác chỉnh sửa của Admin (AD18). `cau_hinh` và `vai_tro` chỉ thêm cái còn thiếu. Mọi hàm seed gọi `khoa_seed(db)` (khóa tư vấn) nên hai tiến trình chạy cùng lúc không vi phạm unique. Đổi mặc định ở `seed/co_ban.py::CAU_HINH_MAC_DINH` thì phải khớp bảng ở spec 02 mục 6 (test đối chiếu từng khóa).
- Dữ liệu mẫu ở `seed/du_lieu_mau/catalog.py` (toàn bộ là dữ liệu giả, SKU và số lô có tiền tố `MAU-`); lô hàng luôn nhập qua phiếu nhập + `ton_kho.nhap_kho`, không gán tồn trực tiếp. Tài khoản mẫu dùng chung mật khẩu công khai `MAT_KHAU_MAU`: CLI từ chối `--mau` với CSDL không ở máy cục bộ (trừ `--cho-phep-may-chu-khac`).
- Admin đầu tiên: mật khẩu tối thiểu 12 ký tự, không được là giá trị mẫu (bắt đầu bằng `doi-`); `JWT_SECRET` cũng bị từ chối nếu là giá trị mẫu.
- Ngoại lệ về `print`: CLI `app/seed/__main__.py` in kết quả cho người chạy; không in mật khẩu Admin (chỉ in `MAT_KHAU_MAU`, vốn công khai).

## Job nền (`app/jobs/`)
- Mỗi job là một hàm `async def chay(db)` trong file `htXX_<ten>.py`, đăng ký lịch trong `app/jobs/__main__.py`.
- Bọc bằng `pg_try_advisory_lock(<số cố định của job>)` để không chạy chồng.
- Job phải idempotent: chạy lại không gây sai.

## Test
- Cấu trúc `tests/` giống `app/modules/`. Đọc docstring đầu `tests/conftest.py` để biết đủ fixture.
- **Một event loop cho cả phiên** (`asyncio_default_*_loop_scope = "session"`): fixture async phạm vi phiên dùng chung được với mọi test; không đặt `loop_scope` riêng cho từng module.
- **Database test** ở `DATABASE_URL_TEST` (tên phải có chữ `test`, nếu không `tao_lai_database` từ chối xóa): xóa và tạo lại, `alembic upgrade head`, `seed_co_ban`, một lần mỗi phiên. Cần PostgreSQL với user superuser.
- **Chọn fixture:**
  - `db`: mặc định, session trong transaction ngoài rollback sau test (savepoint, nên `commit()` chỉ giải phóng savepoint). `client`/`app`/`dang_nhap_*` dùng chung transaction đó, request thấy dữ liệu factory đã `flush()`; request lỗi vẫn hoàn tác phần của chính nó như production.
  - `dang_nhap_khach`, `dang_nhap_duoc_si`, `dang_nhap_kho`, `dang_nhap_admin`: client đã gắn access token thật (`aud` đúng) của tài khoản vừa tạo, có thuộc tính `.tai_khoan`. Dùng nhiều fixture trong một test được (mỗi cái một tài khoản riêng).
  - `db_that`: test cần commit thật giữa nhiều session (tranh chấp khóa), trả `async_sessionmaker`; sau test TRUNCATE hết, giữ vai trò/quyền và seed lại cấu hình. Ví dụ `tests/kho/test_ton_kho_tranh_chap.py`.
  - `db_chua_seed`/`engine_migration`: database đã migrate nhưng chưa seed, cho test về seed và migration (`test_rang_buoc.py`, `test_seed.py`). Test dùng `engine_migration` trực tiếp phải tự rollback.
  - `engine_tam`/`engine_co_bang`: database tạm riêng cho một test (có/không có 65 bảng từ `create_all`). `mo_client(app, raise_app_exceptions=False)` gọi vào app dựng riêng, dùng `False` khi test lỗi 500.
- **Factories** `tests/factories.py`: `tao_khach`, `tao_nhan_vien(vai_tro)`, `tao_san_pham(loai, don_vi=[...])`, `tao_lo(san_pham, so_luong, han_su_dung, trang_thai)`, `tao_don(khach, trang_thai, dong=[...])`. Giá trị mặc định hợp lệ, tham số nào cũng ghi đè được. `tao_lo(so_luong=...)` nhập qua `ton_kho.nhap_kho` nên thẻ kho khớp tồn.
- Test API qua HTTP (`AsyncClient`); test bất biến/tranh chấp gọi service trực tiếp với nhiều session. Muốn chèn dòng mà không dựng khóa ngoại: `SET LOCAL session_replication_role = replica` (cần superuser), xem `test_rang_buoc.py`.
- Test có token dùng `settings.JWT_SECRET` do fixture tự đặt (autouse); `tao_access_token`/`giai_ma_access_token` ở `core/bao_mat.py`.
- Không gọi dịch vụ ngoài: `AI_GIA_LAP=true`, adapter tích hợp ở chế độ `gia`.
- Chạy nhanh một phần: `uv run pytest tests/ban_hang -q -x`. CI (`.github/workflows/ci.yml`) chạy ruff, vòng migration lên-xuống-lên + `alembic check`, `scripts/so_sanh_schema.py`, pytest; frontend chạy lint, `tsc`, vitest (khi có script `test`), build.

## Python
- Bật `ruff` (lint + format) cho mọi file.
- Type hint đầy đủ cho hàm public.
- Docstring tiếng Việt một dòng cho service public.
- Không dùng `print`; dùng `logging.getLogger(__name__)`.

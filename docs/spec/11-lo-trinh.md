# 11. Lộ trình triển khai

Một người làm tuần tự, **mỗi phiên Claude Code một task** (lệnh `/tiep-tuc` hoặc `/lam-task Tx.y`).
Thứ tự đã sắp để mỗi task chỉ phụ thuộc task phía trước. Tiêu chí chấp nhận là "hợp đồng" của task: làm đủ và có test cho từng tiêu chí mới được đánh `[x]`. Phần giao diện ghi trong task làm cùng task đó.

Ký hiệu trạng thái ở tiêu đề task:
- `[ ]` chưa làm.
- `[~]` đang làm.
- `[x]` xong.

Khi làm xong task: tích từng tiêu chí, đổi trạng thái, ghi lệch so với spec vào "Ghi chú triển khai".

## Tổng quan

| Giai đoạn | Nội dung | Số task | Chức năng |
|---|---|:-:|---|
| P0 | Nền tảng | 7 | — |
| P1 | Tài khoản & phân quyền | 6 | KVL09, KVL10, NV01, NV02, AD01, AD18, AD02, AD08, AD15 |
| P2 | Sản phẩm & nội dung | 6 | AD03, AD05, AD04, DS10, KVL01, KVL02, KVL03, KVL04, AD07, KVL11 |
| P3 | Kho | 5 | KHO01, KHO02, KHO05, KHO06, HT01, HT02, KHO07, KHO08, KHO09, KHO11, AD12, KHO13 |
| P4 | Bán hàng online | 9 | KVL07, KTV01, HT06, AD06, KTV04, KTV02, KTV03, HT04, HT03, DS01, DS02, DS03, KTV06, KHO03, KHO04, HT05, KTV05, DS07, DS15, HT08, KTV08 |
| P5 | Đơn thuốc & bán tại quầy | 4 | KTV11, KVL08, KTV07, DS04, DS05, DS08 |
| P6 | Sau bán & thu hồi | 7 | KTV09, DS09, KHO10, AD17, KTV10, KTV15, DS11, KTV13, HT07, KTV14, AD13, KHO12, DS13, AD16 |
| P7 | AI | 9 | AD09, AD10, AI01, KVL05, AI02, AI03, AI04, KTV12, DS06, KVL06, AI05, AI06, AI07, AI08, DS12, AD11, AI09, KHO14 |
| P8 | Báo cáo & hoàn thiện | 3 | AD14, DS14 |

## P0 · Nền tảng

_Dựng khung dự án, CSDL đúng ERD, seed, hạ tầng test. Chưa có chức năng nghiệp vụ._

### [x] T0.1 · Khởi tạo monorepo và môi trường dev
- **Phụ thuộc:** —
- **Tiêu chí chấp nhận:**
  - [x] `docker-compose.yml` có `db` (image `pgvector/pgvector:pg16`, volume dữ liệu) và `mailpit` (xem email OTP khi dev).
  - [x] `backend/`: dự án `uv` (Python 3.12), FastAPI app factory `app/main.py`, `GET /api/v1/health` trả `{"trang_thai": "ok", "db": "ok"}` (có truy vấn `SELECT 1`).
  - [x] `frontend/`: Vite + React + TypeScript chạy được `npm run dev`, gọi được `/api/v1/health` qua proxy Vite.
  - [x] `.env.example` ở `backend/` liệt kê đủ biến trong spec 01 (giá trị giả); `.gitignore` loại `.env`, `storage/`, `node_modules/`, `.venv/`.
  - [x] Lệnh trong phần "Lệnh thường dùng" của `CLAUDE.md` chạy được đúng như ghi (cập nhật nếu khác).
- **Ghi chú triển khai:**
  - **Docker chưa chạy thật.** Môi trường làm T0.1 không có Docker daemon. `docker-compose.yml` mới được kiểm bằng `docker compose config -q`. Phần chạy thật dùng PostgreSQL 16 + pgvector cài trên máy, cùng chuỗi kết nối với compose (`postgres:postgres@localhost:5432/nha_thuoc`). Lần đầu chạy trên máy có Docker cần xác nhận lại `docker compose up -d db mailpit`.
  - **Health check:** ngoài trường hợp ok, khi CSDL lỗi thì trả 503 `{"trang_thai": "loi", "db": "loi"}`. Đã bổ sung vào spec 06.
  - **Test thêm sớm:** đã cài `pytest`, `pytest-asyncio`, `httpx` và viết `tests/test_health.py` (2 test). T0.6 sẽ xây `conftest.py`, DB test riêng và CI.
  - **Phần để task sau:** `core/config.py` mới khai báo `DATABASE_URL`, `CORS_ORIGINS`; các biến khác thêm dần khi dùng. `core/db.py` mới có `engine` và `get_engine()`; `get_db` (transaction theo request) để T0.2.
  - **Frontend:** template `create-vite` hiện tại cho Vite 8, React 19, TypeScript 6 và dùng **oxlint** thay ESLint (`npm run lint`). Đã gộp 3 file tsconfig thành 1 để `npx tsc --noEmit` thực sự kiểm tra code; bản template dùng project references nên lệnh này không kiểm tra gì.

### [x] T0.2 · Hạ tầng backend dùng chung
- **Phụ thuộc:** T0.1
- **Tiêu chí chấp nhận:**
  - [x] `core/config.py` (pydantic-settings), `core/db.py` (AsyncEngine, `get_db` mở transaction theo request).
  - [x] `core/loi.py`: `LoiNghiepVu(ma_loi, thong_diep, http_status, chi_tiet)` + handler trả đúng định dạng lỗi trong spec 06; lỗi validate của FastAPI cũng trả cùng định dạng (`ma_loi = "DU_LIEU_KHONG_HOP_LE"`).
  - [x] `core/tien.py` (`lam_tron_vnd`, cộng/trừ Decimal), `core/thoi_gian.py` (`bay_gio_utc`, `hom_nay_vn`), `core/phan_trang.py` (tham số `trang`, `kich_thuoc`, phản hồi `{du_lieu, tong, trang, kich_thuoc}`).
  - [x] Middleware gắn `request_id` vào log (JSON) và header `X-Request-ID`.
  - [x] Test đơn vị cho làm tròn tiền, phân trang, định dạng lỗi.
- **Ghi chú triển khai:**
  - **Commit trước khi gửi response.** `Db = Annotated[..., Depends(get_db, scope="function")]`: mặc định của FastAPI (`scope="request"`) commit sau khi response đã gửi, nên client nhận 200 dù commit có thể lỗi. Đã có test chứng minh (đổi sang `scope="request"` thì test fail với `200 == 500`). Hệ quả: generator của response streaming (SSE) phải tự mở session riêng.
  - **Chặn `commit()`/`rollback()` tay.** SQLAlchemy cho gọi `commit()` trong `begin()` mà không báo lỗi, khiến phần đã commit ở lại DB dù request sau đó lỗi. `PhienRequest` raise `RuntimeError`; savepoint (`begin_nested`) vẫn dùng được. Quy tắc "service không commit" trong `CLAUDE.md` giờ được máy kiểm tra.
  - **Bảng mã lỗi có test đối chiếu với spec 06.** Thêm mã `PHUONG_THUC_KHONG_DUOC_PHEP` (405) vào spec; lỗi HTTP khác của framework dùng `LOI_HTTP`.
  - **Lỗi 500** trả `{"ma_loi": "LOI_HE_THONG", "chi_tiet": {"request_id": ...}}`, không lộ chi tiết. Log lỗi ghi stack trace kèm `request_id`.
  - **Log truy cập** mỗi request chỉ ghi **mẫu route** (`/xac-nhan-don/{token}`), không ghi giá trị trong path hay query string. Log truy cập của uvicorn bị tắt vì nó in cả query string.
  - **Sửa sau rà soát nghiệp vụ** (7 phát hiện, đã tái hiện bằng test trước khi sửa): (1) log lỗi lộ tham số SQL và dòng `DETAIL:` của PostgreSQL → `hide_parameters=True` + che dòng DETAIL/HINT/CONTEXT; lỗi 500 xử lý trong middleware, không ném lại cho uvicorn nên không còn traceback thô thứ hai; (2) `Tien` giới hạn dưới 10^12, không âm (`TienCoDau` cho số âm), chuẩn hóa `-0`, số quá lớn thành lỗi validate thay vì 500; (3) log theo mẫu route; (4) `chi_tiet` của lỗi chứa `Decimal`/`date`/model không còn làm handler nổ; (5) `trang` tối đa 1.000.000; (6) regex `request_id` dùng `fullmatch`; (7) mã `LOI_HTTP` vào bảng spec 06, 5xx lạ không echo `detail`.
  - **Tiền:** `lam_tron_vnd` half-up (2.5 → 3), từ chối `float` và `bool`. Kiểu `Tien` nhận số đồng nguyên, xuất JSON dạng chuỗi `"125000.00"`; đã kiểm OpenAPI sinh `string` cho T0.7.
  - **Phần để task sau:** `core/config.py` chưa thêm biến mới (chưa có chỗ dùng). Chưa làm sắp xếp `sap_xep` của phân trang (làm cùng endpoint danh sách đầu tiên, T1.4). `ruff` cấu hình ở T0.6; đã chạy thử ruff không cấu hình, sạch (trừ B008 với `Depends`, là mẫu chuẩn của FastAPI).
  - **Thêm phụ thuộc `tzdata`** để `zoneinfo` có dữ liệu múi giờ trên Windows.
  - **Fixture test:** `engine_tam` tạo database tạm cho từng test; T0.6 sẽ thay bằng DB test dựng từ migration.

### [x] T0.3 · Model SQLAlchemy cho 65 bảng
- **Phụ thuộc:** T0.2
- **Bảng:** (toàn bộ ERD)
- **Tiêu chí chấp nhận:**
  - [x] `app/models/` chia theo nhóm ERD (`enums.py`, `san_pham.py`, `kho.py`, `ban_hang.py`, `khach_hang.py`, `he_thong.py`, `ai.py`), khớp từng cột/kiểu/nullable/default/khóa ngoại với `docs/database/ERD_da_chinh_sua.dbml`.
  - [x] 33 enum dùng `sqlalchemy.Enum(..., name=<tên enum ERD>, native_enum=True)` với đúng thứ tự giá trị.
  - [x] Cột `embedding` dùng kiểu `Vector(1024)` của gói `pgvector`.
  - [x] Không có logic nghiệp vụ trong model (chỉ khai báo + quan hệ cần thiết).
- **Ghi chú triển khai:**
  - **Cách làm:** model được sinh bằng script từ ERD (khung ban đầu), sau đó bảo trì bằng tay qua `/doi-schema`. Chứng minh khớp bằng `scripts/so_sanh_schema.py`: `create_all()` từ model vào một DB, nạp `ERD_da_chinh_sua.sql` vào DB khác, so sánh qua catalog của PostgreSQL (bảng, cột gồm kiểu/nullable/default/identity, khóa ngoại, index, enum gồm thứ tự giá trị). Kết quả **0 khác biệt**. Test `test_cong_cu_so_sanh_phat_hien_duoc_khac_biet` chứng minh công cụ thật sự bắt được lỗi. T0.4 dùng lại công cụ này.
  - **Lỗi do so sánh bắt được:** lần sinh đầu, tên collection `khuyen_mai.pham_vi` trùng tên cột nên đè mất cột; đã đổi thành `ds_pham_vi`.
  - **Khóa chính dùng `Identity`** (khớp DDL của ERD) thay vì serial.
  - **Enum:** mỗi enum có lớp `StrEnum` và kiểu `KIEU_<TEN>` gắn vào `Base.metadata` (tạo/xóa kiểu ở cấp metadata, không bị lỗi khi nhiều bảng dùng chung một enum).
  - **Quan hệ:** mọi `relationship` có `lazy="raise"` (không lazy load ngầm trong async, phải `selectinload`). Có quan hệ nhiều-một cho mọi khóa ngoại đơn cột và 23 collection một-nhiều chọn lọc (chi tiết đơn, đơn vị quy đổi...). Khóa ngoại kép (`ct_don_hang`, `ct_gio_hang` → `don_vi_quy_doi`) không có quan hệ vì chồng cột với khóa ngoại `san_pham_id`; vẫn tạo ràng buộc ở DB và đã có test chứng minh nó chặn đơn vị của sản phẩm khác.
  - **Chưa có ở model (để T0.4):** CHECK, partial unique, index GIN/HNSW, hàm `f_unaccent`, sequence mã chứng từ (spec 02 mục 4); DBML không biểu diễn được.
  - **Cột `metadata`** của `tai_lieu_tri_thuc` có thuộc tính Python `metadata_` (tránh đè `Base.metadata`).
  - Thêm phụ thuộc `pgvector`. Fixture `engine_co_bang` (DB tạm có đủ 65 bảng) dùng cho test các task sau.

### [x] T0.4 · Migration nền và ràng buộc bổ sung
- **Phụ thuộc:** T0.3
- **Bảng:** (toàn bộ ERD)
- **Tiêu chí chấp nhận:**
  - [x] Migration `0001`: `CREATE EXTENSION IF NOT EXISTS vector, unaccent, pg_trgm` + toàn bộ bảng/enum/khóa ngoại/index sinh từ model (autogenerate rồi rà tay).
  - [x] Migration `0002`: hàm `f_unaccent`, mọi CHECK, partial unique, index GIN/HNSW, sequence mã chứng từ liệt kê ở spec 02 mục 4.
  - [x] `backend/scripts/so_sanh_schema.py`: nạp `docs/database/ERD_da_chinh_sua.sql` vào một database tạm, so sánh với database sau `alembic upgrade head` (bảng, cột, kiểu, nullable, khóa ngoại theo tập cột, unique theo tập cột, giá trị enum) và in danh sách lệch. Kết quả: 0 lệch.
  - [x] `alembic upgrade head` trên DB rỗng thành công; `alembic downgrade base` rồi `upgrade head` lại thành công; `alembic check` không còn thay đổi.
  - [x] Test: chèn dữ liệu vi phạm từng CHECK/partial unique ở mục 4 spec 02 đều bị từ chối.
- **Ghi chú triển khai:**
  - **Migration `0001_nen`** autogenerate từ model rồi rà tay: thêm 3 `CREATE EXTENSION`, tạo 33 enum bằng `CREATE TYPE` (câu lệnh lấy từ DDL của ERD) và cho các cột dùng `postgresql.ENUM(create_type=False)`, vì autogenerate sinh `sa.Enum` inline sẽ tạo kiểu hai lần; thêm `import pgvector.sqlalchemy` cho cột `Vector(1024)`. `downgrade` xóa bảng rồi kiểu enum; ba extension giữ nguyên.
  - **Migration `0002_rang_buoc`** viết tay bằng SQL thuần: hàm `f_unaccent`, 10 index đặc biệt (3 GIN trgm, 1 HNSW, 1 index một phần, 5 partial unique), 42 CHECK, 7 sequence. Tên CHECK theo mẫu `ck_<bảng>_<mô tả>` (spec chỉ ghi biểu thức); tên index đúng như spec 02 mục 4. Dữ liệu CHECK/index nằm ở hai hằng đầu file để test đối chiếu.
  - **`alembic/env.py`:** hàm `include_object` bỏ qua index một phần, index biểu thức và index không phải btree khi so model với DB, nếu không `alembic check` luôn báo lệch vì DBML/model không biểu diễn được chúng. Alembic cũng **không so sánh CHECK, hàm và sequence**; lưới an toàn là `test_moi_check_trong_db_deu_co_test` (số CHECK trong DB phải đúng bằng danh sách case đã test).
  - **`scripts/so_sanh_schema.py`** thêm chế độ `alembic upgrade head` (bỏ `alembic_version` và index đặc biệt khi so). Chạy `uv run python scripts/so_sanh_schema.py` in kết quả cho cả hai nguồn: model và migration đều **0 khác biệt** so với DDL của ERD. Hàm `chay_alembic()` chạy lệnh Alembic trong luồng riêng (env.py tự dựng vòng lặp asyncio) và đặt `configure_logger=False` để không ghi đè cấu hình log JSON.
  - **Test (69 test mới, tổng 210 xanh):**
    - `test_migration.py`: đi/về/đi lại, `alembic check`, về từng bước `0001`, khớp ERD, chuỗi revision một head, công cụ so sánh vẫn bắt được lỗi thật sau khi lọc index, env.py không ghi đè log.
    - `test_rang_buoc.py`: mỗi CHECK thử cả dòng hợp lệ (sát biên) lẫn dòng sai. Khi thử "đúng ràng buộc này" test gỡ các CHECK khác của bảng trong transaction (Postgres báo ràng buộc theo thứ tự tên nên không gỡ thì không phân biệt được `ton_ge_0` với `giu_ge_0`/`giu_le_ton`). Có test cho 5 partial unique (kể cả đơn `da_huy` không chiếm chỗ của yêu cầu đơn thuốc), `f_unaccent` ("Đau đầu" → "Dau dau"), 7 sequence, và `EXPLAIN` chứng minh planner dùng được 5 index tìm kiếm khi viết đúng biểu thức.
    - Test dựng dòng bằng `session_replication_role = replica` (tắt trigger khóa ngoại, cần superuser; `postgres` của compose/CI có quyền) để khỏi dựng cả đồ thị khóa ngoại. CHECK và unique vẫn chạy.
    - Đã kiểm chứng test bằng cách phá thử: sửa `giu_le_ton`, `tong_tien_dung`, `anh_mot_anh_chinh`, `don_thuoc_mot_don_mo` trong migration thì 4 test tương ứng fail; sửa env.py luôn gọi `fileConfig` thì test log fail. Đã hoàn lại.
  - **Cấu hình `ruff` làm sớm** (thuộc T0.6 nhưng cần để lint file mới): `[tool.ruff]` trong `pyproject.toml` (dòng 120, E/F/W/I/B/UP/SIM, `alembic` khai báo third-party vì thư mục `backend/alembic/` trùng tên gói, bỏ qua E501/UP trong `alembic/versions`, `Depends` coi là immutable cho B008). `ruff check` và `ruff format --check` sạch. T0.6 chỉ còn gắn vào CI.
  - **Chưa chạy trên Docker** (không có daemon): kiểm trên PostgreSQL 16 cài máy; migration chỉ dùng extension có sẵn trong image `pgvector/pgvector:pg16` (`vector`, `unaccent`, `pg_trgm` đều có trong contrib).
  - **Bỏ qua `/review-nghiep-vu` ở task này:** không có logic nghiệp vụ, chỉ chép ràng buộc từ spec 02 mục 4 (đã đếm 42 CHECK, 10 index, 7 sequence khớp từng dòng và có test từng mục). Rà soát chạy ở task đầu tiên có logic (T1.x).

### [ ] T0.5 · Seed dữ liệu
- **Phụ thuộc:** T0.4
- **Bảng:** `vai_tro`, `quyen`, `vai_tro_quyen`, `cau_hinh`, `nhan_vien`, (dữ liệu mẫu)
- **Tiêu chí chấp nhận:**
  - [ ] `uv run python -m app.seed`: tạo 3 vai trò, toàn bộ quyền và `vai_tro_quyen` đọc từ `docs/spec/data/quyen.yaml`, các khóa `cau_hinh` mặc định (spec 02 mục 6), tài khoản Admin đầu tiên từ biến môi trường. Chạy lại nhiều lần không nhân bản dữ liệu.
  - [ ] `uv run python -m app.seed --mau`: dữ liệu mẫu đủ để demo: cây danh mục 3 cấp, ~40 sản phẩm phủ đủ 5 loại (có thuốc kê đơn), hoạt chất + thành phần, đơn vị quy đổi hộp/vỉ/viên, vài cặp tương tác hoạt chất, nhà cung cấp, lô với HSD đa dạng (có lô cận hạn, hết hạn), 1 dược sĩ, 1 nhân viên kho, 2 khách hàng, mã giảm giá.
  - [ ] Lô mẫu được tạo qua phiếu nhập mẫu kèm dòng `bien_dong_kho` tương ứng, để bất biến tồn kho (spec 04 mục 3.2) đúng ngay từ đầu.
  - [ ] Test: số dòng `vai_tro_quyen` sau seed bằng số cặp trong `quyen.yaml`.
- **Ghi chú triển khai:** _(trống)_

### [ ] T0.6 · Hạ tầng test và CI
- **Phụ thuộc:** T0.5
- **Tiêu chí chấp nhận:**
  - [ ] `tests/conftest.py`: database test riêng (tạo từ migration một lần mỗi phiên test, mỗi test chạy trong transaction rollback), `AsyncClient` gọi app, fixture đăng nhập sẵn cho từng vai trò (khách, dược sĩ, kho, admin), factories tạo dữ liệu.
  - [ ] Cấu hình `pytest` + `pytest-asyncio`, `ruff` (lint + format).
  - [ ] `.github/workflows/ci.yml`: backend (ruff, pytest với service `pgvector/pgvector:pg16`), frontend (lint, `tsc --noEmit`, vitest, build).
- **Ghi chú triển khai:** _(trống)_

### [ ] T0.7 · Khung frontend 3 khu
- **Phụ thuộc:** T0.1
- **Tiêu chí chấp nhận:**
  - [ ] Ant Design (locale `vi_VN`, dayjs `vi`), React Router, TanStack Query, Zustand.
  - [ ] 3 layout: cửa hàng (`/`), nhân viên (`/nhan-vien`), quản trị (`/quan-tri`) theo spec 09; trang 403/404.
  - [ ] `npm run gen:api` sinh type từ OpenAPI của backend vào `src/api/schema.d.ts`; `src/api/client.ts` dùng `openapi-fetch`, tự gắn access token, tự refresh khi 401 một lần.
  - [ ] Tiện ích `dinhDangTien`, `dinhDangNgay` (múi giờ Asia/Ho_Chi_Minh) có test vitest.
- **Ghi chú triển khai:** _(trống)_

## P1 · Tài khoản & phân quyền

_Đăng ký/đăng nhập 2 loại tài khoản, RBAC, nhật ký, cấu hình._

### [ ] T1.1 · OTP và đăng ký khách hàng
- **Chức năng:** KVL09 (Đăng ký tài khoản)
- **Phụ thuộc:** T0.6, T0.7
- **Bảng:** `khach_hang`, `ma_otp`
- **Tiêu chí chấp nhận:**
  - [ ] Adapter `tin_nhan` (SMS/email) có bản giả ghi ra log và Mailpit (spec 08).
  - [ ] `POST /api/v1/auth/otp` (mục đích `dang_ky`), lưu `ma_otp.ma_hash`, hết hạn 5 phút, tối đa 5 lần thử, giới hạn gửi theo `gioi_han_otp`.
  - [ ] `POST /api/v1/auth/dang-ky`: SĐT bắt buộc (chuẩn hóa 0xxxxxxxxx), email tùy chọn, mật khẩu băm Argon2, lưu `dong_y_chinh_sach_luc`.
  - [ ] Test: OTP sai/hết hạn/quá số lần; SĐT trùng; đăng ký thành công.
- **Giao diện:**
  - [ ] Trang đăng ký 2 bước (nhập SĐT → OTP + thông tin).
- **Ghi chú triển khai:** _(trống)_

### [ ] T1.2 · Đăng nhập khách, phiên và quên mật khẩu
- **Chức năng:** KVL10 (Đăng nhập, quên mật khẩu)
- **Phụ thuộc:** T1.1
- **Bảng:** `khach_hang`, `ma_otp`, `phien_dang_nhap`
- **Tiêu chí chấp nhận:**
  - [ ] `POST /api/v1/auth/dang-nhap`: access JWT (15 phút, `aud = "khach"`) + refresh token trong cookie httpOnly; lưu hash vào `phien_dang_nhap`.
  - [ ] `POST /api/v1/auth/lam-moi` xoay vòng refresh token (token cũ bị thu hồi; dùng lại token đã thu hồi thì thu hồi toàn bộ phiên của tài khoản).
  - [ ] `POST /api/v1/auth/dang-xuat`, quên mật khẩu bằng OTP (mục đích `quen_mat_khau`) → thu hồi mọi phiên.
  - [ ] Khóa tạm sau `so_lan_dang_nhap_sai_toi_da` lần sai (`khoa_den`). Tài khoản `bi_khoa` không đăng nhập/làm mới được.
  - [ ] `GET /api/v1/toi` trả hồ sơ khách. Dependency `khach_hien_tai`, `khach_tuy_chon`.
- **Giao diện:**
  - [ ] Trang đăng nhập, quên mật khẩu; store phiên (Zustand).
- **Ghi chú triển khai:** _(trống)_

### [ ] T1.3 · Xác thực nhân viên, RBAC và nhật ký
- **Chức năng:** NV01 (Đăng nhập, đổi mật khẩu), NV02 (Xem thông báo, cập nhật hồ sơ cá nhân)
- **Phụ thuộc:** T1.2
- **Bảng:** `nhan_vien`, `phien_dang_nhap`, `thong_bao`
- **Tiêu chí chấp nhận:**
  - [ ] `POST /api/v1/noi-bo/auth/dang-nhap` (`aud = "noi_bo"`), bắt đổi mật khẩu lần đầu (`phai_doi_mat_khau`), đổi mật khẩu thu hồi mọi phiên.
  - [ ] `GET /api/v1/noi-bo/toi` trả hồ sơ + danh sách mã quyền và mức (`day_du`/`chi_xem`).
  - [ ] `core/phan_quyen.py`: `yeu_cau_quyen(ma, muc="day_du")` đọc quyền từ DB (cache 60 giây), kiểm tra trạng thái tài khoản mỗi request.
  - [ ] `core/nhat_ky.py`: `ghi_nhat_ky(...)` ghi `nhat_ky_he_thong` (không ghi mật khẩu, OTP, dữ liệu sức khỏe).
  - [ ] Registry endpoint → quyền + test ma trận phân quyền tự sinh từ `quyen.yaml` (spec 10 mục 3); test thất bại nếu có route `/noi-bo` chưa khai báo.
  - [ ] Thông báo nội bộ: `GET /api/v1/noi-bo/thong-bao`, đánh dấu đã đọc; sửa hồ sơ cá nhân.
- **Giao diện:**
  - [ ] Trang đăng nhập nội bộ, đổi mật khẩu bắt buộc, menu theo quyền, chuông thông báo.
- **Ghi chú triển khai:** _(trống)_

### [ ] T1.4 · Quản lý nhân viên, vai trò và quyền
- **Chức năng:** AD01 (Quản lý tài khoản nhân viên), AD18 (Quản lý vai trò & phân quyền)
- **Phụ thuộc:** T1.3
- **Bảng:** `nhan_vien`, `vai_tro`, `phien_dang_nhap`, `nhat_ky_he_thong`, `quyen`, `vai_tro_quyen`
- **Tiêu chí chấp nhận:**
  - [ ] CRUD nhân viên (không xóa cứng), khóa/mở, đặt lại mật khẩu (sinh mật khẩu tạm + `phai_doi_mat_khau`), gán vai trò; khóa → thu hồi phiên.
  - [ ] Chặn tự khóa/tự hạ quyền; luôn còn ≥ 1 Admin hoạt động (`ma_loi = "PHAI_CON_ADMIN"`).
  - [ ] Xem quyền, gán/bỏ quyền cho PHARMACIST/WAREHOUSE; không bỏ quyền của ADMIN. Mọi thay đổi ghi nhật ký.
- **Giao diện:**
  - [ ] Danh sách nhân viên (lọc, tìm), form nhân viên, màn ma trận vai trò - quyền.
- **Ghi chú triển khai:** _(trống)_

### [ ] T1.5 · Quản lý khách hàng
- **Chức năng:** AD02 (Quản lý khách hàng)
- **Phụ thuộc:** T1.3
- **Bảng:** `khach_hang`, `don_hang`, `phien_dang_nhap`
- **Tiêu chí chấp nhận:**
  - [ ] Danh sách khách (tìm theo tên/SĐT/email), xem lịch sử mua (dùng lại API đơn hàng khi có), khóa/mở (thu hồi phiên).
  - [ ] Response không bao giờ chứa `ho_so_suc_khoe`, `di_ung` (test khẳng định).
- **Giao diện:**
  - [ ] Danh sách và chi tiết khách hàng.
- **Ghi chú triển khai:** _(trống)_

### [ ] T1.6 · Cấu hình hệ thống và nhật ký
- **Chức năng:** AD08 (Cấu hình hệ thống), AD15 (Xem nhật ký hệ thống)
- **Phụ thuộc:** T1.3
- **Bảng:** `cau_hinh`, `nhat_ky_he_thong`
- **Tiêu chí chấp nhận:**
  - [ ] Đọc/sửa `cau_hinh` với schema kiểm tra kiểu cho từng khóa (spec 02 mục 6); ghi `nhan_vien_cap_nhat_id`.
  - [ ] Tra cứu nhật ký theo bảng, bản ghi, nhân viên, khoảng thời gian; hiển thị giá trị cũ/mới.
- **Giao diện:**
  - [ ] Trang cấu hình (nhóm theo chủ đề), trang nhật ký.
- **Ghi chú triển khai:** _(trống)_

## P2 · Sản phẩm & nội dung

_Danh mục, sản phẩm, nội dung chuyên môn, trang cửa hàng, tìm kiếm từ khóa, bài viết._

### [ ] T2.1 · Danh mục và dữ liệu dùng chung
- **Chức năng:** AD03 (Quản lý danh mục), AD05 (Quản lý hoạt chất, thương hiệu, nhà sản xuất)
- **Phụ thuộc:** T1.4
- **Bảng:** `danh_muc`, `hoat_chat`, `thuong_hieu`, `nha_san_xuat`, `thanh_phan`
- **Tiêu chí chấp nhận:**
  - [ ] Cây danh mục tối đa 3 cấp (từ chối cấp 4), sắp xếp `thu_tu`, ẩn = xóa mềm; không xóa danh mục còn sản phẩm (`ma_loi = "DANH_MUC_CON_SAN_PHAM"`).
  - [ ] CRUD thương hiệu, nhà sản xuất (unique tên + quốc gia), hoạt chất (tên chuẩn + tên khác).
- **Giao diện:**
  - [ ] Cây danh mục kéo thả, bảng thương hiệu/NSX/hoạt chất.
- **Ghi chú triển khai:** _(trống)_

### [ ] T2.2 · Sản phẩm: thông tin thương mại
- **Chức năng:** AD04 (Quản lý sản phẩm – thông tin thương mại)
- **Phụ thuộc:** T2.1
- **Bảng:** `san_pham`, `don_vi_quy_doi`, `anh_san_pham`
- **Tiêu chí chấp nhận:**
  - [ ] CRUD sản phẩm (SKU, slug tự sinh không dấu, loại, danh mục, thương hiệu, NSX, SĐK, dạng bào chế, quy cách, đối tượng, nổi bật, giới hạn số lượng/đơn, dùng định kỳ).
  - [ ] Đơn vị quy đổi: đúng 1 đơn vị `he_so = 1`, tối đa 1 mặc định, mã vạch; giá theo từng đơn vị. Thành phần (hoạt chất + hàm lượng).
  - [ ] Upload ảnh (spec 08 lưu trữ công khai), đặt ảnh chính, sắp xếp.
  - [ ] Admin không sửa được nội dung chuyên môn (endpoint chuyên môn yêu cầu quyền của dược sĩ).
- **Giao diện:**
  - [ ] Danh sách sản phẩm (lọc loại/danh mục/trạng thái), form sản phẩm nhiều tab.
- **Ghi chú triển khai:** _(trống)_

### [ ] T2.3 · Nội dung chuyên môn, tương tác hoạt chất
- **Chức năng:** DS10 (Biên soạn, duyệt nội dung chuyên môn)
- **Phụ thuộc:** T2.2
- **Bảng:** `thong_tin_chuyen_mon`, `tuong_tac_hoat_chat`, `bai_viet`
- **Tiêu chí chấp nhận:**
  - [ ] Mỗi lần sửa tạo phiên bản mới `thong_tin_chuyen_mon` (trạng thái `nhap`); duyệt → `da_duyet`, ghi `duoc_si_duyet_id`, `ngay_duyet`; phiên bản hiển thị = bản đã duyệt mới nhất.
  - [ ] CRUD `tuong_tac_hoat_chat` (lưu cặp theo thứ tự id tăng dần), hàm `kiem_tra_tuong_tac(ds_san_pham_id)` và `kiem_tra_di_ung(khach_hang_id, ds_san_pham_id)` trả danh sách cảnh báo có mức độ (dùng lại ở DS04, DS05, DS08, AI).
  - [ ] Duyệt bài viết sức khỏe (khi T2.6 xong thì nối vào).
- **Giao diện:**
  - [ ] Màn biên soạn chuyên môn có so sánh phiên bản, màn tương tác hoạt chất.
- **Ghi chú triển khai:** _(trống)_

### [ ] T2.4 · Trang chủ, danh mục, lọc, chi tiết sản phẩm
- **Chức năng:** KVL01 (Xem trang chủ, danh mục), KVL02 (Lọc, sắp xếp sản phẩm), KVL03 (Xem chi tiết sản phẩm)
- **Phụ thuộc:** T2.3
- **Bảng:** `banner`, `danh_muc`, `san_pham`, `anh_san_pham`, `don_vi_quy_doi`, `thuong_hieu`, `thong_tin_chuyen_mon`, `thanh_phan`, `hoat_chat`, `nha_san_xuat`, `lo_thuoc`, `danh_gia`, `hoi_dap`, `lich_su_xem`
- **Tiêu chí chấp nhận:**
  - [ ] API công khai chỉ trả sản phẩm `dang_kinh_doanh`, chưa xóa; giá theo từng đơn vị bán online; tình trạng còn hàng = tồn khả dụng > 0 (spec 04 mục 3).
  - [ ] Lọc: danh mục (gồm danh mục con), loại, thương hiệu, khoảng giá, đối tượng; sắp xếp: mới, giá, bán chạy (đếm `ct_don_hang` 30 ngày).
  - [ ] Chi tiết: nội dung chuyên môn bản đã duyệt, thành phần, ảnh, đánh giá (khi có). Thuốc kê đơn trả cờ `can_tu_van = true` và không có hành động "thêm vào giỏ"; TPCN kèm câu "không phải là thuốc".
  - [ ] Ghi `lich_su_xem` (khách hoặc mã phiên).
- **Giao diện:**
  - [ ] Trang chủ (banner, nổi bật, bán chạy), trang danh mục có bộ lọc, trang chi tiết sản phẩm.
- **Ghi chú triển khai:** _(trống)_

### [ ] T2.5 · Tìm kiếm từ khóa
- **Chức năng:** KVL04 (Tìm kiếm thông minh)
- **Phụ thuộc:** T2.4
- **Bảng:** `san_pham`, `hoat_chat`, `thanh_phan`, `tai_lieu_tri_thuc`, `lich_su_tim_kiem`
- **Tiêu chí chấp nhận:**
  - [ ] Tìm không dấu, sai chính tả, theo tiền tố bằng `word_similarity` (`f_unaccent(lower(:q)) <% f_unaccent(lower(ten))`, spec 02 mục 4.1) trên tên sản phẩm, hoạt chất, tên khác; gợi ý khi gõ (≤ 8 kết quả, < 200 ms trên dữ liệu mẫu). Test: "para" ra Paracetamol, "paracetmol" (gõ sai) ra Paracetamol, "bo phe" ra "Bổ phế".
  - [ ] Xếp hạng: độ khớp, còn hàng trước, bán chạy; thuốc kê đơn có nhãn "Cần tư vấn".
  - [ ] Ghi `lich_su_tim_kiem` (`che_do = tu_khoa`). Phần tìm ngữ nghĩa nối vào ở T7.2.
- **Giao diện:**
  - [ ] Ô tìm kiếm có gợi ý, trang kết quả.
- **Ghi chú triển khai:** _(trống)_

### [ ] T2.6 · Banner, bài viết, chính sách, FAQ
- **Chức năng:** AD07 (Quản lý banner, bài viết, chính sách, FAQ), KVL11 (Xem bài viết sức khỏe, chính sách, FAQ)
- **Phụ thuộc:** T2.3
- **Bảng:** `banner`, `bai_viet`
- **Tiêu chí chấp nhận:**
  - [ ] CRUD banner theo vị trí, thời gian hiển thị. CRUD `bai_viet` theo `loai`; bài `bai_viet` cần dược sĩ duyệt mới công khai; chính sách/FAQ Admin đăng trực tiếp.
  - [ ] API công khai danh sách/chi tiết theo slug; cờ `dua_vao_ai`.
- **Giao diện:**
  - [ ] Quản trị banner/bài viết (editor Markdown), trang bài viết, chính sách, FAQ phía khách.
- **Ghi chú triển khai:** _(trống)_

## P3 · Kho

_Nhập kho theo lô, thẻ kho, cảnh báo, kiểm kê, hủy, xuất trả, báo cáo nhập - xuất - tồn._

### [ ] T3.1 · Nhà cung cấp, phiếu nhập và dịch vụ tồn kho
- **Chức năng:** KHO01 (Quản lý nhà cung cấp), KHO02 (Lập phiếu nhập kho)
- **Phụ thuộc:** T2.2
- **Bảng:** `nha_cung_cap`, `phieu_nhap`, `ct_phieu_nhap`, `lo_thuoc`, `bien_dong_kho`
- **Tiêu chí chấp nhận:**
  - [ ] `kho/ton_kho.py` là nơi DUY NHẤT đổi tồn: `nhap_kho`, `giu_hang`, `nha_giu`, `xuat_theo_phan_bo`, `hoan_nhap`, `vao_biet_tru`, `tru_ton` (hủy/xuất trả/điều chỉnh); khóa lô `FOR UPDATE`, ghi `bien_dong_kho` (spec 04 mục 3).
  - [ ] CRUD nhà cung cấp (ngừng hợp tác = xóa mềm).
  - [ ] Lập phiếu nhập: quy đổi về đơn vị cơ sở; tạo lô mới hoặc cộng vào lô cũ (tính lại giá nhập bình quân gia quyền); cảnh báo HSD < `han_su_dung_toi_thieu_nhap_ngay`, chặn số lô trùng khác HSD; phiếu đã lưu không sửa/xóa.
  - [ ] Test bất biến tồn kho (spec 10 mục 4) cho nhập kho.
- **Giao diện:**
  - [ ] Danh sách nhà cung cấp; form phiếu nhập nhiều dòng có quét mã vạch.
- **Ghi chú triển khai:** _(trống)_

### [ ] T3.2 · Tra cứu tồn, cảnh báo và job lô
- **Chức năng:** KHO05 (Tra cứu tồn kho), KHO06 (Xem cảnh báo), HT01 (Cập nhật trạng thái lô hằng ngày), HT02 (Cảnh báo tồn thấp, cận hạn)
- **Phụ thuộc:** T3.1
- **Bảng:** `lo_thuoc`, `san_pham`, `thong_bao`, `phan_bo_lo`
- **Tiêu chí chấp nhận:**
  - [ ] Worker `uv run python -m app.jobs` (APScheduler, mỗi job giữ `pg_try_advisory_lock` để không chạy chồng).
  - [ ] HT01 hằng ngày 00:05 (giờ VN): lô `dang_ban` có HSD < hôm nay + `nguong_can_han_ngay` → `can_han`; HSD ≤ hôm nay → `het_han` (gỡ khỏi đơn chưa xuất, phân bổ lại FEFO khi có module bán hàng).
  - [ ] HT02: gửi `thong_bao` cho nhân viên kho khi tồn khả dụng < `ton_toi_thieu`, có lô cận hạn/hết hạn (không gửi trùng trong ngày).
  - [ ] Tra cứu tồn theo sản phẩm và theo lô (tồn, giữ, biệt trữ, trạng thái). Dược sĩ chỉ thấy tồn khả dụng, không thấy giá nhập.
- **Giao diện:**
  - [ ] Màn tồn kho (bảng sản phẩm mở rộng ra lô), màn cảnh báo.
- **Ghi chú triển khai:** _(trống)_

### [ ] T3.3 · Kiểm kê và phiếu điều chỉnh
- **Chức năng:** KHO07 (Kiểm kê), KHO08 (Lập phiếu điều chỉnh tồn)
- **Phụ thuộc:** T3.1
- **Bảng:** `phieu_kiem_ke`, `ct_kiem_ke`, `phieu_dieu_chinh`, `ct_phieu_dieu_chinh`
- **Tiêu chí chấp nhận:**
  - [ ] Phiếu kiểm kê (toàn kho hoặc theo danh mục) chụp tồn sổ sách; nhập số thực tế; chốt → tính chênh lệch.
  - [ ] Lập phiếu điều chỉnh từ kết quả kiểm kê (chỉ các dòng lệch), trạng thái chờ duyệt; tồn chưa đổi.
- **Giao diện:**
  - [ ] Màn kiểm kê (nhập nhanh theo lô), màn phiếu điều chỉnh.
- **Ghi chú triển khai:** _(trống)_

### [ ] T3.4 · Phiếu hủy, phiếu xuất trả và duyệt
- **Chức năng:** KHO09 (Lập phiếu hủy hàng), KHO11 (Xuất trả nhà cung cấp), AD12 (Duyệt phiếu hủy, điều chỉnh tồn, xuất trả NCC)
- **Phụ thuộc:** T3.3
- **Bảng:** `phieu_huy`, `ct_phieu_huy`, `phieu_xuat_tra`, `ct_phieu_xuat_tra`, `phieu_dieu_chinh`, `lo_thuoc`, `bien_dong_kho`
- **Tiêu chí chấp nhận:**
  - [ ] Lập phiếu hủy và phiếu xuất trả NCC (chọn lô, khu `kho_ban`/`biet_tru`, số lượng ≤ tồn khu đó); trạng thái chờ duyệt.
  - [ ] Admin duyệt/từ chối phiếu điều chỉnh, hủy, xuất trả: người duyệt ≠ người lập (`ma_loi = "TU_DUYET_KHONG_DUOC"`); chỉ khi duyệt mới gọi `ton_kho` và ghi thẻ kho; từ chối bắt buộc lý do.
  - [ ] Test: tự duyệt bị chặn; duyệt làm tồn đúng; từ chối không đổi tồn.
- **Giao diện:**
  - [ ] Danh sách phiếu chờ duyệt cho Admin; form phiếu hủy/xuất trả.
- **Ghi chú triển khai:** _(trống)_

### [ ] T3.5 · Báo cáo nhập - xuất - tồn
- **Chức năng:** KHO13 (Báo cáo nhập, xuất, tồn)
- **Phụ thuộc:** T3.4
- **Bảng:** `bien_dong_kho`, `lo_thuoc`
- **Tiêu chí chấp nhận:**
  - [ ] Theo kỳ (từ ngày - đến ngày), theo sản phẩm hoặc lô: tồn đầu, nhập, xuất (theo loại biến động), tồn cuối, tính hoàn toàn từ `bien_dong_kho`.
  - [ ] Test: tồn cuối báo cáo = `so_luong_ton` hiện tại khi đến ngày = hôm nay.
  - [ ] Xuất file Excel (`openpyxl`).
- **Giao diện:**
  - [ ] Màn báo cáo có bộ lọc và nút xuất Excel.
- **Ghi chú triển khai:** _(trống)_

## P4 · Bán hàng online

_Giỏ hàng, máy trạng thái, đặt hàng giữ hàng FEFO, thanh toán, xử lý và giao đơn._

### [ ] T4.1 · Giỏ hàng và sổ địa chỉ
- **Chức năng:** KVL07 (Quản lý giỏ hàng), KTV01 (Quản lý hồ sơ, sổ địa chỉ)
- **Phụ thuộc:** T2.4
- **Bảng:** `gio_hang`, `ct_gio_hang`, `san_pham`, `don_vi_quy_doi`, `luat_mua_kem`, `khach_hang`, `dia_chi`
- **Tiêu chí chấp nhận:**
  - [ ] Giỏ của khách vãng lai ở localStorage; `PUT /api/v1/toi/gio-hang/gop` gộp khi đăng nhập (cộng dồn, cắt theo giới hạn).
  - [ ] Từ chối thuốc kê đơn (`ma_loi = "THUOC_KE_DON_KHONG_VAO_GIO"`), đơn vị `ban_online = false`, vượt `so_luong_toi_da_moi_don` (tính theo đơn vị cơ sở).
  - [ ] Gợi ý "thường mua cùng" đọc `luat_mua_kem` (rỗng thì ẩn).
  - [ ] Sổ địa chỉ: CRUD, đúng 1 mặc định; mã tỉnh/xã theo danh mục của đơn vị vận chuyển (spec 08).
- **Giao diện:**
  - [ ] Mini-cart, trang giỏ hàng, quản lý địa chỉ trong trang tài khoản.
- **Ghi chú triển khai:** _(trống)_

### [ ] T4.2 · Máy trạng thái đơn hàng
- **Chức năng:** HT06 (Máy trạng thái đơn hàng)
- **Phụ thuộc:** T3.1
- **Bảng:** `don_hang`, `lich_su_trang_thai`
- **Tiêu chí chấp nhận:**
  - [ ] `ban_hang/trang_thai.py`: bảng chuyển trạng thái dạng dữ liệu đúng bảng 1 spec 04; `chuyen_trang_thai(db, don, den, tac_nhan, nguon, ghi_chu)` kiểm tra hợp lệ + vai trò được phép, ghi `lich_su_trang_thai`, gọi các hook tác động (kho, thanh toán, thông báo) trong cùng transaction.
  - [ ] Không nơi nào khác được gán `don_hang.trang_thai` (thêm test quét mã nguồn tìm phép gán trực tiếp).
  - [ ] Test tham số hóa: mọi dòng trong bảng chuyển hợp lệ; mọi cặp không có trong bảng bị từ chối (`ma_loi = "CHUYEN_TRANG_THAI_KHONG_HOP_LE"`).
- **Ghi chú triển khai:** _(trống)_

### [ ] T4.3 · Khuyến mãi và mã giảm giá
- **Chức năng:** AD06 (Quản lý khuyến mãi, mã giảm giá), KTV04 (Áp dụng mã giảm giá)
- **Phụ thuộc:** T2.2
- **Bảng:** `khuyen_mai`, `khuyen_mai_pham_vi`, `ma_giam_gia`
- **Tiêu chí chấp nhận:**
  - [ ] CRUD khuyến mãi (%/số tiền, trần giảm, đơn tối thiểu, thời gian, tổng lượt, lượt/khách, phạm vi toàn bộ/danh mục/sản phẩm) và sinh mã.
  - [ ] `POST /api/v1/toi/ma-giam-gia/kiem-tra`: trả số tiền giảm dự kiến theo giỏ (thuật toán spec 04 mục 4), lý do nếu không áp dụng được.
  - [ ] Thuốc kê đơn luôn bị loại khỏi phần được giảm.
- **Giao diện:**
  - [ ] Quản trị khuyến mãi; ô nhập mã ở trang thanh toán.
- **Ghi chú triển khai:** _(trống)_

### [ ] T4.4 · Đặt hàng và giữ hàng theo FEFO
- **Chức năng:** KTV02 (Đặt hàng)
- **Phụ thuộc:** T4.1, T4.2, T4.3
- **Bảng:** `gio_hang`, `ct_gio_hang`, `don_hang`, `ct_don_hang`, `phan_bo_lo`, `lo_thuoc`, `dia_chi`, `khuyen_mai`, `khuyen_mai_pham_vi`, `ma_giam_gia`, `lich_su_trang_thai`
- **Tiêu chí chấp nhận:**
  - [ ] `POST /api/v1/toi/don-hang` với header `Idempotency-Key`: kiểm tra lại giá, tồn khả dụng (chỉ lô `dang_ban`), giới hạn số lượng, mã giảm giá (khóa `FOR UPDATE`), tính phí ship (adapter vận chuyển, miễn phí từ `mien_phi_ship_tu`), tạo đơn + chi tiết (bản chụp tên/giá/đơn vị, `giam_gia_phan_bo`) + phân bổ lô giữ hàng.
  - [ ] COD → `cho_xac_nhan`; VNPay/MoMo → `cho_thanh_toan` + `han_thanh_toan`.
  - [ ] Test tranh chấp: 2 khách cùng đặt đơn vị cuối cùng → đúng 1 đơn thành công, đơn kia nhận `ma_loi = "HET_HANG"`, tồn không âm.
- **Giao diện:**
  - [ ] Trang thanh toán (địa chỉ, hình thức nhận, phương thức thanh toán, mã giảm giá, tổng tiền), trang đặt hàng thành công.
- **Ghi chú triển khai:** _(trống)_

### [ ] T4.5 · Thanh toán online và hủy quá hạn
- **Chức năng:** KTV03 (Thanh toán online), HT04 (Xử lý IPN thanh toán), HT03 (Hủy đơn quá hạn)
- **Phụ thuộc:** T4.4
- **Bảng:** `thanh_toan`, `don_hang`, `phan_bo_lo`, `lo_thuoc`, `ma_giam_gia`
- **Tiêu chí chấp nhận:**
  - [ ] Adapter VNPay, MoMo (spec 08) + bản giả có trang "cổng giả" để bấm thành công/thất bại khi dev.
  - [ ] IPN: kiểm chữ ký, kiểm số tiền khớp `tong_tien`, chống xử lý trùng bằng `ma_giao_dich_cong`, chuyển trạng thái qua HT06; trả đúng định dạng phản hồi cổng yêu cầu.
  - [ ] HT03 mỗi phút: hủy đơn quá `han_thanh_toan`/`han_xac_nhan`, nhả giữ hàng, trả lượt mã giảm giá.
  - [ ] Test: IPN gửi 2 lần chỉ xử lý 1 lần; IPN sai chữ ký bị từ chối; IPN đến sau khi đơn đã bị hủy quá hạn → tạo giao dịch hoàn tiền chờ xác nhận.
- **Giao diện:**
  - [ ] Chuyển hướng sang cổng, trang kết quả thanh toán (đọc trạng thái từ backend, không tin tham số URL).
- **Ghi chú triển khai:** _(trống)_

### [ ] T4.6 · Xử lý đơn của dược sĩ và khách hủy đơn
- **Chức năng:** DS01 (Xem, lọc danh sách đơn hàng), DS02 (Xác nhận đơn hàng), DS03 (Hủy đơn hàng), KTV06 (Hủy đơn hàng)
- **Phụ thuộc:** T4.4
- **Bảng:** `don_hang`, `ct_don_hang`, `lich_su_trang_thai`, `phan_bo_lo`, `lo_thuoc`, `bien_dong_kho`, `thanh_toan`, `ma_giam_gia`
- **Tiêu chí chấp nhận:**
  - [ ] Danh sách đơn nội bộ: lọc trạng thái, ngày, phương thức thanh toán, kênh; chi tiết đơn có dòng thời gian trạng thái.
  - [ ] Xác nhận đơn; hủy đơn có lý do (trước khi rời kho, hoàn nhập đúng lô nếu đã chốt lô); khách tự hủy theo spec 04.
  - [ ] Hủy đơn đã thanh toán → tạo `thanh_toan` loại `hoan_tien` (`khoi_tao`), `trang_thai_tt = cho_hoan_tien` (Admin xác nhận ở T6.3).
  - [ ] Khách chỉ xem/hủy đơn của chính mình (truy cập đơn người khác → 404).
- **Giao diện:**
  - [ ] Màn quản lý đơn cho dược sĩ; trang "Đơn hàng của tôi" có nút hủy.
- **Ghi chú triển khai:** _(trống)_

### [ ] T4.7 · Soạn hàng, đóng gói, vận chuyển, theo dõi đơn
- **Chức năng:** KHO03 (Soạn hàng, xuất kho theo đơn), KHO04 (Đóng gói, bàn giao vận chuyển), HT05 (Nhận webhook vận chuyển), KTV05 (Theo dõi đơn hàng)
- **Phụ thuộc:** T4.6
- **Bảng:** `don_hang`, `phan_bo_lo`, `lo_thuoc`, `bien_dong_kho`, `van_don`, `thanh_toan`, `lich_su_trang_thai`
- **Tiêu chí chấp nhận:**
  - [ ] Danh sách đơn chờ soạn; gợi ý lô FEFO; đổi lô bắt buộc lý do; chuyển `dang_soan_hang` → chốt lô, trừ tồn, ghi thẻ kho; in phiếu soạn hàng.
  - [ ] Đóng gói: adapter GHN tạo vận đơn (giao tận nơi) → `cho_lay_hang`; đơn nhận tại nhà thuốc chỉ đóng gói.
  - [ ] Webhook GHN (HT05): kiểm token, ánh xạ trạng thái đối tác → trạng thái đơn qua HT06; COD giao thành công ghi `thanh_toan` COD.
  - [ ] Khách xem dòng thời gian trạng thái và mã vận đơn.
- **Giao diện:**
  - [ ] Màn soạn hàng cho kho (quét mã vạch xác nhận), in phiếu/nhãn; trang chi tiết đơn của khách.
- **Ghi chú triển khai:** _(trống)_

### [ ] T4.8 · Đơn qua điện thoại và nhận tại nhà thuốc
- **Chức năng:** DS07 (Tạo đơn hộ khách), DS15 (Giao đơn nhận tại nhà thuốc)
- **Phụ thuộc:** T4.7
- **Bảng:** `don_hang`, `ct_don_hang`, `phan_bo_lo`, `thanh_toan`, `lich_su_trang_thai`
- **Tiêu chí chấp nhận:**
  - [ ] Dược sĩ lập đơn cho khách (tìm khách theo SĐT hoặc nhập người nhận), cùng quy tắc với KTV02, chặn thuốc kê đơn; COD → `da_xac_nhan`, online → `cho_thanh_toan` + gửi link.
  - [ ] Giao đơn nhận tại quầy: tìm theo mã đơn/SĐT, thu tiền nếu chưa thanh toán, chuyển `da_giao`.
- **Giao diện:**
  - [ ] Màn tạo đơn hộ; màn giao hàng tại quầy.
- **Ghi chú triển khai:** _(trống)_

### [ ] T4.9 · Tự hoàn tất đơn và lịch sử mua
- **Chức năng:** HT08 (Tự hoàn tất đơn, nhả khóa), KTV08 (Lịch sử mua, mua lại)
- **Phụ thuộc:** T4.7
- **Bảng:** `don_hang`, `yeu_cau_don_thuoc`, `yeu_cau_doi_tra`, `hoi_thoai`, `ct_don_hang`, `gio_hang`, `ct_gio_hang`
- **Tiêu chí chấp nhận:**
  - [ ] HT08 (mỗi 15 phút): `da_giao` quá `thoi_han_doi_tra_ngay` và không có yêu cầu đổi trả mở → `hoan_tat`; đơn nhận tại quầy quá `thoi_han_nhan_tai_quay_ngay` → hủy + hoàn nhập. (Các phần nhả khóa đơn thuốc, đóng chat bổ sung ở T5.3, T7.4.)
  - [ ] Lịch sử mua có phân trang; "Mua lại" đưa các dòng còn bán vào giỏ, bỏ qua thuốc kê đơn và báo lý do.
- **Giao diện:**
  - [ ] Trang lịch sử mua có nút "Mua lại".
- **Ghi chú triển khai:** _(trống)_

## P5 · Đơn thuốc & bán tại quầy

_Hồ sơ sức khỏe, gửi và duyệt đơn thuốc, tạo đơn từ đơn thuốc, POS._

### [ ] T5.1 · Hồ sơ sức khỏe và dị ứng
- **Chức năng:** KTV11 (Hồ sơ sức khỏe)
- **Phụ thuộc:** T2.3
- **Bảng:** `ho_so_suc_khoe`, `di_ung`, `hoat_chat`
- **Tiêu chí chấp nhận:**
  - [ ] Khách xem/sửa/xóa hồ sơ; chỉ lưu khi `dong_y_su_dung = true` (ghi `dong_y_luc`); `benh_nen` mã hóa mức ứng dụng (Fernet, khóa trong `.env`).
  - [ ] Hàm cổng `duoc_doc_ho_so_suc_khoe(nhan_vien, khach_hang_id)` theo spec 03 mục 5; mọi lần dược sĩ đọc ghi nhật ký (không ghi nội dung).
  - [ ] Test: Admin không đọc được; dược sĩ không được gán không đọc được.
- **Giao diện:**
  - [ ] Trang hồ sơ sức khỏe có màn đồng ý, chọn hoạt chất dị ứng.
- **Ghi chú triển khai:** _(trống)_

### [ ] T5.2 · Gửi yêu cầu tư vấn đơn thuốc
- **Chức năng:** KVL08 (Gửi yêu cầu tư vấn đơn thuốc), KTV07 (Gửi yêu cầu tư vấn đơn thuốc)
- **Phụ thuộc:** T5.1
- **Bảng:** `yeu_cau_don_thuoc`, `ct_yeu_cau_don_thuoc`, `ma_otp`, `don_hang`
- **Tiêu chí chấp nhận:**
  - [ ] Upload ảnh đơn vào lưu trữ riêng tư (spec 08), tính `hash_anh`; khách vãng lai xác thực SĐT bằng OTP (`don_thuoc_khach`).
  - [ ] Khách thành viên xem danh sách/trạng thái yêu cầu của mình, hủy khi còn `cho_duyet`/`dang_tu_van`.
  - [ ] Ảnh chỉ xem được qua URL ký có hạn bởi chủ yêu cầu hoặc dược sĩ đang xử lý.
- **Giao diện:**
  - [ ] Trang gửi đơn thuốc (chụp/tải ảnh), trang "Đơn thuốc của tôi".
- **Ghi chú triển khai:** _(trống)_

### [ ] T5.3 · Duyệt đơn thuốc và tạo đơn từ đơn thuốc
- **Chức năng:** DS04 (Duyệt yêu cầu đơn thuốc), DS05 (Tạo đơn hàng từ đơn thuốc)
- **Phụ thuộc:** T5.2, T4.4
- **Bảng:** `yeu_cau_don_thuoc`, `ct_yeu_cau_don_thuoc`, `ho_so_suc_khoe`, `di_ung`, `tuong_tac_hoat_chat`, `lo_thuoc`, `don_hang`, `ct_don_hang`, `phan_bo_lo`
- **Tiêu chí chấp nhận:**
  - [ ] Hàng chờ; nhận xử lý = khóa (`duoc_si_id`, `khoa_luc`), HT08 tự nhả quá `thoi_gian_khoa_don_thuoc_phut`.
  - [ ] Màn duyệt: ảnh đơn, tồn kho, hồ sơ dị ứng (qua hàm cổng), cảnh báo trùng `hash_anh`, cảnh báo tương tác/dị ứng; checklist (spec 04 mục 6) bắt buộc đủ trước khi chấp nhận; từ chối bắt buộc lý do.
  - [ ] Tạo đơn từ đơn thuốc → `cho_khach_xac_nhan`, `han_xac_nhan`, link có mã truy cập cho khách vãng lai (SMS); khách xác nhận/chọn thanh toán (phần còn lại của KTV07).
  - [ ] `da_su_dung` chỉ bật khi đơn sang `dang_soan_hang`; đơn hủy trước đó → yêu cầu quay lại `dang_tu_van`, tạo lại đơn được.
- **Giao diện:**
  - [ ] Màn hàng chờ và màn duyệt đơn thuốc cho dược sĩ; trang xác nhận đơn cho khách (cả link không cần đăng nhập).
- **Ghi chú triển khai:** _(trống)_

### [ ] T5.4 · Bán tại quầy (POS)
- **Chức năng:** DS08 (Bán tại quầy – POS)
- **Phụ thuộc:** T5.3
- **Bảng:** `don_hang`, `ct_don_hang`, `phan_bo_lo`, `lo_thuoc`, `bien_dong_kho`, `thanh_toan`, `yeu_cau_don_thuoc`, `tuong_tac_hoat_chat`
- **Tiêu chí chấp nhận:**
  - [ ] Quét mã vạch/tìm sản phẩm, chọn đơn vị (bán lẻ theo viên); dùng được lô cận hạn; xuất kho FEFO ngay, ghi thẻ kho; đơn `tai_quay` → `hoan_tat`.
  - [ ] Thuốc kê đơn: bắt buộc tạo yêu cầu đơn thuốc kênh `tai_quay` (ảnh + người bệnh) trước khi thanh toán; hiện cảnh báo tương tác.
  - [ ] Thanh toán tiền mặt (tính tiền thừa)/chuyển khoản; gắn khách theo SĐT nếu có tài khoản; in hóa đơn (HTML in được).
- **Giao diện:**
  - [ ] Màn POS tối ưu bàn phím/máy quét.
- **Ghi chú triển khai:** _(trống)_

## P6 · Sau bán & thu hồi

_Đổi trả, biệt trữ, hoàn tiền, đánh giá, hỏi đáp, thông báo, thu hồi lô._

### [ ] T6.1 · Yêu cầu đổi trả và duyệt
- **Chức năng:** KTV09 (Yêu cầu đổi trả), DS09 (Xử lý yêu cầu đổi trả)
- **Phụ thuộc:** T4.9
- **Bảng:** `yeu_cau_doi_tra`, `ct_yeu_cau_doi_tra`, `van_don`, `thanh_toan`, `don_hang`
- **Tiêu chí chấp nhận:**
  - [ ] Khách tạo yêu cầu trong thời hạn, chọn dòng + số lượng (tổng đã trả không vượt đã mua), lý do, ảnh/video; COD/tiền mặt nhập tài khoản nhận hoàn.
  - [ ] Dược sĩ duyệt/từ chối; duyệt → tạo vận đơn `tra_hang` (adapter vận chuyển) gửi mã cho khách.
  - [ ] Sau khi kho nhận: chọn hoàn tiền (tạo giao dịch hoàn, số tiền theo spec 04 mục 5) hoặc gửi hàng thay thế (đơn 0đ `don_hang_goc_id`, trạng thái `da_xac_nhan`).
- **Giao diện:**
  - [ ] Form đổi trả trong chi tiết đơn; màn xử lý đổi trả cho dược sĩ.
- **Ghi chú triển khai:** _(trống)_

### [ ] T6.2 · Nhận hàng trả, hàng hoàn và biệt trữ
- **Chức năng:** KHO10 (Nhận hàng trả về, hàng hoàn)
- **Phụ thuộc:** T6.1
- **Bảng:** `yeu_cau_doi_tra`, `ct_yeu_cau_doi_tra`, `lo_thuoc`, `phan_bo_lo`, `bien_dong_kho`
- **Tiêu chí chấp nhận:**
  - [ ] Hàng đổi trả: ghi `lo_id`, `so_luong_nhan`, kết quả kiểm; cộng `so_luong_biet_tru` (thẻ kho `nhan_tra_ve`).
  - [ ] Đơn `hoan_ve_kho`: kiểm hàng; nguyên niêm phong → hoàn nhập đúng lô; hư hỏng → biệt trữ; chuyển `da_huy` qua HT06; đã thanh toán → tạo hoàn tiền.
- **Giao diện:**
  - [ ] Màn nhận hàng trả/hoàn cho kho.
- **Ghi chú triển khai:** _(trống)_

### [ ] T6.3 · Xác nhận hoàn tiền
- **Chức năng:** AD17 (Xác nhận hoàn tiền)
- **Phụ thuộc:** T6.1
- **Bảng:** `thanh_toan`, `don_hang`, `yeu_cau_doi_tra`
- **Tiêu chí chấp nhận:**
  - [ ] Danh sách giao dịch hoàn tiền `khoi_tao`; VNPay/MoMo gọi API hoàn tiền của adapter theo `thanh_toan_goc_id`; COD/tiền mặt: nhập chứng từ chuyển khoản.
  - [ ] Người xác nhận ≠ dược sĩ duyệt đổi trả; cập nhật `trang_thai_tt` (`da_hoan_tien`/`hoan_tien_mot_phan`), thông báo khách, ẩn danh hóa `thong_tin_nhan_hoan` sau khi xong.
- **Giao diện:**
  - [ ] Màn hoàn tiền cho Admin.
- **Ghi chú triển khai:** _(trống)_

### [ ] T6.4 · Đánh giá và hỏi đáp sản phẩm
- **Chức năng:** KTV10 (Đánh giá sản phẩm), KTV15 (Đặt câu hỏi về sản phẩm), DS11 (Kiểm duyệt đánh giá, hỏi đáp)
- **Phụ thuộc:** T4.9
- **Bảng:** `danh_gia`, `ct_don_hang`, `hoi_dap`
- **Tiêu chí chấp nhận:**
  - [ ] Đánh giá 1-5 sao cho dòng đơn `da_giao`/`hoan_tat`, mỗi dòng 1 lần, có ảnh; câu hỏi sản phẩm (cần đăng nhập).
  - [ ] Dược sĩ ẩn đánh giá/câu hỏi vi phạm, trả lời câu hỏi (thông báo cho khách).
- **Giao diện:**
  - [ ] Khối đánh giá và hỏi đáp trên trang chi tiết; màn kiểm duyệt cho dược sĩ.
- **Ghi chú triển khai:** _(trống)_

### [ ] T6.5 · Thông báo và nhắc mua lại
- **Chức năng:** KTV13 (Nhận thông báo), HT07 (Gửi thông báo, nhắc mua lại), KTV14 (Nhắc mua lại)
- **Phụ thuộc:** T4.9
- **Bảng:** `thong_bao`, `ct_don_hang`, `san_pham`
- **Tiêu chí chấp nhận:**
  - [ ] Dịch vụ `thong_bao.gui(...)`: ghi bảng `thong_bao` + gửi email/SMS qua adapter theo loại sự kiện (đơn hàng, đơn thuốc, đổi trả, thu hồi).
  - [ ] HT07 hằng ngày 08:00: với sản phẩm `dung_dinh_ky`, ngày hết dự kiến = ngày giao + số lượng cơ sở × `so_ngay_dung_moi_don_vi`; nhắc trước 3 ngày, không nhắc trùng.
- **Giao diện:**
  - [ ] Chuông thông báo và trang thông báo của khách.
- **Ghi chú triển khai:** _(trống)_

### [ ] T6.6 · Thu hồi lô
- **Chức năng:** AD13 (Khởi tạo lệnh thu hồi lô), KHO12 (Thực hiện thu hồi lô), DS13 (Liên hệ khách khi thu hồi lô)
- **Phụ thuộc:** T6.2
- **Bảng:** `lenh_thu_hoi`, `ct_lenh_thu_hoi`, `lo_thuoc`, `phan_bo_lo`, `thong_bao`, `phieu_xuat_tra`, `phieu_huy`
- **Tiêu chí chấp nhận:**
  - [ ] Admin tạo lệnh thu hồi (một lô hoặc mọi lô của sản phẩm): lô → `thu_hoi`, gỡ khỏi đơn chưa xuất (phân bổ lại hoặc báo hết hàng), sinh `ct_lenh_thu_hoi` từ `phan_bo_lo` đã xuất, gửi thông báo khách.
  - [ ] Kho gom tồn + hàng khách trả, lập phiếu xuất trả/hủy (đi duyệt AD12); dược sĩ cập nhật kết quả liên hệ.
  - [ ] Đóng lệnh khi mọi dòng đã xử lý.
- **Giao diện:**
  - [ ] Màn lệnh thu hồi (Admin), danh sách khách cần liên hệ (dược sĩ).
- **Ghi chú triển khai:** _(trống)_

### [ ] T6.7 · Màn xem tổng hợp cho Admin
- **Chức năng:** AD16 (Xem đơn hàng, chứng từ kho, nội dung chuyên môn)
- **Phụ thuộc:** T6.6
- **Bảng:** `don_hang`, `phieu_nhap`, `phieu_kiem_ke`, `thong_tin_chuyen_mon`
- **Tiêu chí chấp nhận:**
  - [ ] Màn gộp chứng từ kho (`GET /api/v1/noi-bo/chung-tu-kho`: phiếu nhập, kiểm kê, điều chỉnh, hủy, xuất trả) yêu cầu `stock_doc.view`; màn nội dung chuyên môn chỉ xem yêu cầu `content.view`; màn chi tiết dùng lại API nội bộ sẵn có ở mức `chi_xem` (đơn hàng: `order.view`).
  - [ ] Admin không thao tác được: nút ghi bị ẩn, gọi API ghi trả 403 (có test cho từng loại).
- **Ghi chú triển khai:** _(trống)_

## P7 · AI

_Kho tri thức, tìm kiếm lai, chatbot RAG, chuyển dược sĩ, đọc ảnh, gợi ý, dự báo._

### [ ] T7.1 · Hạ tầng AI và kho tri thức
- **Chức năng:** AD09 (Cấu hình AI), AD10 (Đồng bộ kho tri thức AI)
- **Phụ thuộc:** T2.6
- **Bảng:** `cau_hinh`, `tai_lieu_tri_thuc`, `thong_tin_chuyen_mon`, `bai_viet`
- **Tiêu chí chấp nhận:**
  - [ ] `ai/claude.py`: client `AsyncAnthropic`, hàm `goi_json` và `stream_chat` theo spec 07 mục 2 (fallbacks, xử lý refusal, ghi usage); `ai/gia_lap.py` client giả cho dev/test (`AI_GIA_LAP=true`).
  - [ ] `ai/embedding.py`: BGE-M3 (sentence-transformers, chuẩn hóa vector) + bản giả sinh vector xác định từ hash.
  - [ ] AD10: đồng bộ `tai_lieu_tri_thuc` từ nội dung chuyên môn đã duyệt + bài viết `dua_vao_ai`; chia đoạn theo trường; bỏ qua đoạn có `hash_noi_dung` không đổi; xóa đoạn của nguồn đã gỡ; chạy theo yêu cầu và hằng đêm.
  - [ ] AD09: bật/tắt từng module AI, danh sách dấu hiệu nguy hiểm, ngưỡng chuyển dược sĩ (đọc từ `cau_hinh`).
- **Giao diện:**
  - [ ] Màn cấu hình AI và nút đồng bộ kho tri thức (hiển thị số đoạn thêm/sửa/xóa).
- **Ghi chú triển khai:** _(trống)_

### [ ] T7.2 · Tìm kiếm lai
- **Chức năng:** AI01 (Tìm kiếm thông minh)
- **Phụ thuộc:** T7.1, T2.5
- **Bảng:** `san_pham`, `tai_lieu_tri_thuc`, `lich_su_tim_kiem`
- **Tiêu chí chấp nhận:**
  - [ ] Kết hợp kết quả trigram (T2.5) và vector (`<=>` cosine trên `tai_lieu_tri_thuc`) bằng Reciprocal Rank Fusion (k = 60); tìm được theo triệu chứng/công dụng.
  - [ ] AI lỗi hoặc tắt → tự quay về chỉ từ khóa (test bằng client giả ném lỗi). Ghi `che_do = hybrid`.
- **Ghi chú triển khai:** _(trống)_

### [ ] T7.3 · Chatbot tư vấn (RAG)
- **Chức năng:** KVL05 (Chat với trợ lý AI), AI02 (Phân loại ý định, phát hiện dấu hiệu nguy hiểm), AI03 (Trả lời bằng RAG)
- **Phụ thuộc:** T7.2
- **Bảng:** `hoi_thoai`, `tin_nhan`, `tai_lieu_tri_thuc`, `danh_gia_cau_tra_loi`, `cau_hinh`, `ho_so_suc_khoe`, `di_ung`, `tuong_tac_hoat_chat`
- **Tiêu chí chấp nhận:**
  - [ ] `POST /api/v1/tu-van/chat` trả SSE; lưu `hoi_thoai`, `tin_nhan` (ý định, sản phẩm gợi ý, cờ nguy hiểm, token).
  - [ ] AI02: phân loại ý định + dấu hiệu nguy hiểm (từ khóa cấu hình chạy trước, rồi Claude) → nguy hiểm thì trả mẫu cố định khuyên đi khám/gọi 115 và gắn cờ.
  - [ ] AI03: tool chỉ đọc theo spec 07 mục 4; mọi tool lọc bỏ thuốc kê đơn và (nếu khách đồng ý) sản phẩm chứa hoạt chất dị ứng ở tầng SQL.
  - [ ] Giới hạn lượt theo phiên/IP; nút báo sai → `danh_gia_cau_tra_loi`.
  - [ ] Bộ câu hỏi đánh giá (spec 07 mục 8) chạy được bằng lệnh riêng; test tự động dùng client giả.
- **Giao diện:**
  - [ ] Widget chat nổi trên mọi trang cửa hàng, hiển thị stream, thẻ sản phẩm, nút "Gặp dược sĩ", nút báo sai.
- **Ghi chú triển khai:** _(trống)_

### [ ] T7.4 · Chuyển dược sĩ và chat trực tiếp
- **Chức năng:** AI04 (Tóm tắt, chuyển dược sĩ), KTV12 (Chat trực tiếp với dược sĩ), DS06 (Tư vấn trực tiếp)
- **Phụ thuộc:** T7.3
- **Bảng:** `hoi_thoai`, `tin_nhan`
- **Tiêu chí chấp nhận:**
  - [ ] AI04: tóm tắt hội thoại (`goi_json`) khi chuyển; trong giờ làm việc → `cho_duoc_si`, ngoài giờ → `cho_goi_lai` + SĐT.
  - [ ] WebSocket `/api/v1/tu-van/ws` cho khách và dược sĩ (xác thực bằng token, chỉ thành viên phiên mới vào được); dược sĩ nhận phiên → `duoc_si_dang_xu_ly`.
  - [ ] HT08 đóng phiên không hoạt động.
- **Giao diện:**
  - [ ] Hàng chờ chat và cửa sổ chat cho dược sĩ; widget chat chuyển chế độ "đang chat với dược sĩ".
- **Ghi chú triển khai:** _(trống)_

### [ ] T7.5 · Tra cứu thuốc bằng ảnh
- **Chức năng:** KVL06 (Tra cứu thuốc bằng ảnh), AI05 (Nhận diện hộp thuốc từ ảnh)
- **Phụ thuộc:** T7.1
- **Bảng:** `san_pham`, `thong_tin_chuyen_mon`
- **Tiêu chí chấp nhận:**
  - [ ] `POST /api/v1/tra-cuu-anh`: ảnh base64 → `goi_json` trích tên, hoạt chất, hàm lượng, SĐK; khớp theo SĐK rồi tên (trigram); không khớp → trả thông tin đọc được + cảnh báo "chưa xác minh".
  - [ ] Giới hạn kích thước ảnh (≤ 5 MB, tự thu nhỏ cạnh dài ≤ 1568 px), giới hạn lượt.
- **Giao diện:**
  - [ ] Nút chụp ảnh tra cứu trên thanh tìm kiếm (mobile).
- **Ghi chú triển khai:** _(trống)_

### [ ] T7.6 · Đọc ảnh đơn thuốc hỗ trợ dược sĩ
- **Chức năng:** AI06 (Đọc ảnh đơn thuốc)
- **Phụ thuộc:** T7.1, T5.3
- **Bảng:** `yeu_cau_don_thuoc`, `ct_yeu_cau_don_thuoc`
- **Tiêu chí chấp nhận:**
  - [ ] Khi yêu cầu đơn thuốc được tạo: job đọc ảnh → `ket_qua_ai`, `ct_yeu_cau_don_thuoc` (tên trên đơn, hàm lượng, số lượng kê, `do_tin_cay_ai`, gợi ý `san_pham_id`).
  - [ ] Màn duyệt DS04 hiển thị gợi ý kèm độ tin cậy, dược sĩ sửa/xác nhận (`do_duoc_si_nhap`). AI không tự duyệt.
- **Ghi chú triển khai:** _(trống)_

### [ ] T7.7 · Gợi ý sản phẩm và mua kèm
- **Chức năng:** AI07 (Gợi ý sản phẩm tương tự, dành cho bạn), AI08 (Gợi ý mua kèm)
- **Phụ thuộc:** T7.1, T4.9
- **Bảng:** `san_pham`, `thanh_phan`, `lich_su_xem`, `di_ung`, `luat_mua_kem`, `ct_don_hang`
- **Tiêu chí chấp nhận:**
  - [ ] AI07: sản phẩm tương tự (cùng hoạt chất → cùng danh mục → gần vector), "dành cho bạn" theo `lich_su_xem`; loại thuốc kê đơn và hoạt chất dị ứng.
  - [ ] AI08 job hằng tuần: luật kết hợp từ `ct_don_hang` đơn `hoan_tat` 180 ngày (support ≥ 0.005, confidence ≥ 0.1, lift > 1), ghi đè `luat_mua_kem`.
- **Ghi chú triển khai:** _(trống)_

### [ ] T7.8 · Đánh giá và giám sát AI
- **Chức năng:** DS12 (Đánh giá câu trả lời AI), AD11 (Giám sát hội thoại AI)
- **Phụ thuộc:** T7.3
- **Bảng:** `danh_gia_cau_tra_loi`, `tin_nhan`, `hoi_thoai`, `lich_su_tim_kiem`
- **Tiêu chí chấp nhận:**
  - [ ] Dược sĩ xem hội thoại bị gắn cờ, đánh dấu đúng/sai, ghi chú nội dung đúng.
  - [ ] Admin xem hội thoại đã ẩn danh (che SĐT, email, tên), thống kê câu hỏi phổ biến (theo `y_dinh`), tỉ lệ chuyển dược sĩ, chi phí token, truy vấn tìm kiếm không có kết quả.
- **Giao diện:**
  - [ ] Màn đánh giá câu trả lời; dashboard AI cho Admin.
- **Ghi chú triển khai:** _(trống)_

### [ ] T7.9 · Dự báo nhu cầu và đề xuất nhập hàng
- **Chức năng:** AI09 (Dự báo nhu cầu, đề xuất nhập hàng), KHO14 (Xem đề xuất nhập hàng từ AI)
- **Phụ thuộc:** T7.1, T3.5
- **Bảng:** `de_xuat_nhap_hang`, `ct_don_hang`, `lo_thuoc`
- **Tiêu chí chấp nhận:**
  - [ ] Job hằng tuần: dự báo 30 ngày tới theo sản phẩm (trung bình trượt có trọng số; Holt-Winters khi đủ ≥ 12 tuần dữ liệu), tính MAPE trên 4 tuần gần nhất, ghi `de_xuat_nhap_hang`.
  - [ ] Kho xem đề xuất, đánh dấu đã xử lý khi lập phiếu nhập.
- **Giao diện:**
  - [ ] Màn đề xuất nhập hàng có biểu đồ lịch sử bán và dự báo.
- **Ghi chú triển khai:** _(trống)_

## P8 · Báo cáo & hoàn thiện

_Báo cáo tổng hợp, rà soát bảo mật/hiệu năng, dữ liệu demo, tài liệu nộp._

### [ ] T8.1 · Báo cáo tổng hợp và báo cáo ca
- **Chức năng:** AD14 (Báo cáo thống kê tổng hợp), DS14 (Báo cáo bán hàng của ca)
- **Phụ thuộc:** T6.3, T7.8
- **Bảng:** `don_hang`, `ct_don_hang`, `phan_bo_lo`, `thanh_toan`, `lo_thuoc`, `hoi_thoai`, `yeu_cau_don_thuoc`
- **Tiêu chí chấp nhận:**
  - [ ] AD14: doanh thu (trừ hoàn tiền), lợi nhuận gộp (giá vốn từ `phan_bo_lo`), sản phẩm bán chạy, giá trị tồn kho, thuốc cận hạn, hiệu quả AI; lọc theo kỳ; xuất Excel.
  - [ ] DS14: số liệu của chính dược sĩ trong khoảng thời gian, tiền mặt thu tại quầy; không có giá vốn.
- **Giao diện:**
  - [ ] Dashboard Admin (biểu đồ), màn báo cáo ca.
- **Ghi chú triển khai:** _(trống)_

### [ ] T8.2 · Rà soát bảo mật và hiệu năng
- **Phụ thuộc:** T8.1
- **Tiêu chí chấp nhận:**
  - [ ] Chạy `/security-review` và `/review-nghiep-vu` trên toàn bộ mã; sửa hết lỗi mức cao.
  - [ ] Kiểm tra: rate limit, CORS, cookie `Secure/HttpOnly/SameSite`, header bảo mật, upload (kiểu MIME, kích thước), không lộ stack trace, log không chứa dữ liệu nhạy cảm.
  - [ ] `EXPLAIN ANALYZE` các truy vấn nóng (danh sách sản phẩm, tìm kiếm, danh sách đơn) với dữ liệu mẫu ×10; thêm index nếu cần qua `/doi-schema`.
- **Ghi chú triển khai:** _(trống)_

### [ ] T8.3 · Dữ liệu demo, e2e và tài liệu nộp
- **Phụ thuộc:** T8.2
- **Tiêu chí chấp nhận:**
  - [ ] Kịch bản Playwright cho luồng chính: khách đặt hàng COD → dược sĩ xác nhận → kho soạn/giao → hoàn tất; gửi đơn thuốc → duyệt → xác nhận; đổi trả → hoàn tiền; chat AI → chuyển dược sĩ.
  - [ ] Seed demo đẹp (ảnh sản phẩm, đơn hàng nhiều trạng thái, dữ liệu báo cáo 3 tháng).
  - [ ] `README.md` gốc: giới thiệu, ảnh chụp màn hình, cách chạy, tài khoản demo; hướng dẫn deploy đơn giản (docker compose prod).
- **Ghi chú triển khai:** _(trống)_

## Việc phát sinh

Lỗi hoặc việc phát hiện trong lúc làm nhưng nằm ngoài phạm vi task đang làm. Ghi một dòng `- [ ] (Tx.y) mô tả`, xử lý sau.

- _(chưa có)_

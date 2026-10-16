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
  - **Phần để task sau:** `core/config.py` chưa thêm biến mới (chưa có chỗ dùng). Chưa làm sắp xếp `sap_xep` của phân trang (đã làm ở T1.4: `core/phan_trang.sap_xep_theo` + `SapXepQuery`). `ruff` cấu hình ở T0.6; đã chạy thử ruff không cấu hình, sạch (trừ B008 với `Depends`, là mẫu chuẩn của FastAPI).
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

### [x] T0.5 · Seed dữ liệu
- **Phụ thuộc:** T0.4
- **Bảng:** `vai_tro`, `quyen`, `vai_tro_quyen`, `cau_hinh`, `nhan_vien`, (dữ liệu mẫu)
- **Tiêu chí chấp nhận:**
  - [x] `uv run python -m app.seed`: tạo 3 vai trò, toàn bộ quyền và `vai_tro_quyen` đọc từ `docs/spec/data/quyen.yaml`, các khóa `cau_hinh` mặc định (spec 02 mục 6), tài khoản Admin đầu tiên từ biến môi trường. Chạy lại nhiều lần không nhân bản dữ liệu.
  - [x] `uv run python -m app.seed --mau`: dữ liệu mẫu đủ để demo: cây danh mục 3 cấp, ~40 sản phẩm phủ đủ 5 loại (có thuốc kê đơn), hoạt chất + thành phần, đơn vị quy đổi hộp/vỉ/viên, vài cặp tương tác hoạt chất, nhà cung cấp, lô với HSD đa dạng (có lô cận hạn, hết hạn), 1 dược sĩ, 1 nhân viên kho, 2 khách hàng, mã giảm giá.
  - [x] Lô mẫu được tạo qua phiếu nhập mẫu kèm dòng `bien_dong_kho` tương ứng, để bất biến tồn kho (spec 04 mục 3.2) đúng ngay từ đầu.
  - [x] Test: số dòng `vai_tro_quyen` sau seed bằng số cặp trong `quyen.yaml`.
- **Ghi chú triển khai:**
  - **Cấu trúc:** `app/seed/co_ban.py` (`seed_co_ban(db, admin=...)`), `app/seed/du_lieu_mau/` (`catalog.py` là bảng dữ liệu, `nap.py` là `seed_mau(db)`), `app/seed/__main__.py` (CLI). Hai hàm seed nhận session và không commit; CLI bọc transaction. Test T0.6 dùng thẳng `seed_co_ban` cho DB test (spec 10 mục 2: seed vai trò/quyền/cấu hình, không seed mẫu).
  - **Đồng bộ theo `quyen.yaml`:** 3 vai trò, 51 quyền, 69 cặp vai trò-quyền (`day_du` lưu `gioi_han = NULL`, `chi_xem` lưu `'chi_xem'`). Quyền hoặc cặp không còn trong yaml bị gỡ. Khóa `cau_hinh` chỉ thêm khi còn thiếu, không ghi đè giá trị Admin đã sửa. Test đọc bảng `cau_hinh` ngay từ spec 02 mục 6 và so từng khóa (19 khóa), nên sửa spec mà quên seed sẽ bị fail.
  - **Admin:** `ADMIN_EMAIL`, `ADMIN_MAT_KHAU` kiểm tra (email hợp lệ, mật khẩu ≥ 8 ký tự có chữ và số) **trước khi** đụng DB; tạo mới với `phai_doi_mat_khau = true`, đã có thì giữ nguyên (không đặt lại mật khẩu). Thiếu hoặc sai thì CLI thoát mã 2, không in mật khẩu (`TaiKhoanAdmin.__repr__` che mật khẩu, `ADMIN_MAT_KHAU` là `SecretStr`).
  - **Dữ liệu mẫu (toàn bộ là dữ liệu giả):** 33 danh mục 3 cấp, 42 sản phẩm (7 kê đơn, 14 không kê đơn, 8 TPCN, 5 dược mỹ phẩm, 8 thiết bị y tế), 31 hoạt chất, 6 cặp tương tác, 3 nhà cung cấp, 67 lô qua 3 phiếu nhập mẫu, 1 dược sĩ, 1 nhân viên kho, 2 khách (3 địa chỉ), 3 mã giảm giá (1 đã hết hạn). Có sẵn các tình huống demo: hết hàng (không lô), chỉ còn lô hết hạn, chỉ còn lô cận hạn (chỉ bán tại quầy), sản phẩm ngừng kinh doanh, lô hết hạn còn hàng chờ phiếu hủy. Hạn sử dụng tính từ ngày chạy; chạy lại không dịch hạn của lô đã có.
  - **Bất biến tồn kho đúng ngay từ đầu:** mọi lô nhập qua phiếu nhập + `ton_kho.nhap_kho`; test kiểm `so_luong_ton` = tổng thẻ kho khu `kho_ban`, `ton_sau` của thẻ cuối = tồn hiện tại, `so_luong_giu = 0`, tổng phiếu nhập = tổng dòng, số lượng cơ sở = số lượng × hệ số. Phá thử bằng cách gán thẳng `so_luong_ton` trong seed thì test fail.
  - **Làm sớm hơn lộ trình:** `modules/kho/ton_kho.py` (mới có `nhap_kho` và `khoa_cac_lo`; T3.1 thêm các hàm còn lại) vì quy tắc 2 cấm đổi tồn ở nơi khác; `core/bao_mat.py` (Argon2id, T1.x thêm JWT); `core/ma_chung_tu.py` (mã nhân viên, mã phiếu, lệnh thu hồi từ sequence); `core/slug.py`; `tests/factories.py` (T0.6 mở rộng); fixture `engine_migration` và `db` trong `conftest.py` (phạm vi module, T0.6 thay bằng một DB cho cả phiên).
  - **Test tranh chấp đầu tiên** (`tests/kho/test_ton_kho_tranh_chap.py`): giao dịch B nạp lô trước, A giữ khóa và commit, B phải chờ rồi tính `ton_sau` trên tồn mới. Bỏ `FOR UPDATE` hoặc `populate_existing` thì test fail.
  - **Quy ước ranh giới trạng thái lô:** hết hạn khi `han_su_dung <= hôm nay` (khớp truy vấn FEFO ở spec 04 mục 3.1, lô có HSD đúng hôm nay không bán), cận hạn khi còn **dưới** ngưỡng ngày. Hàm `trang_thai_lo` đang nằm trong seed; T3.2 (HT01) dùng lại và nên chuyển vào `modules/kho`.
  - **Chưa có:** ảnh sản phẩm và `thong_tin_chuyen_mon` (làm ở T2.x, tránh nội dung y khoa chưa thẩm định); mã tỉnh/huyện/xã của địa chỉ mẫu là mã giả cho adapter vận chuyển giả. Dữ liệu tương tác thuốc chỉ minh họa luồng cảnh báo.
  - **Cảnh báo an toàn:** tài khoản mẫu dùng chung mật khẩu công khai `MAT_KHAU_MAU`; CLI in cảnh báo "chỉ dùng cục bộ". Không chạy `--mau` trên môi trường thật.
  - Thêm phụ thuộc `argon2-cffi`, `pyyaml`; `ruff` (cấu hình đã làm ở T0.4).
  - **Sửa sau rà soát nghiệp vụ** (không có lỗi nghiêm trọng; 4 mức trung bình và vài mức nhẹ, đã sửa kèm test, phá thử thấy test fail):
    - Mật khẩu mẫu của `.env.example` (`doi-mat-khau-nay-123`) qua được kiểm tra nên Admin có thể bị tạo với mật khẩu công khai → Admin cần ≥ 12 ký tự và bị từ chối nếu bắt đầu bằng `doi-`; `JWT_SECRET` mẫu cũng bị từ chối. Email Admin trùng nhân viên khác vai trò bị từ chối thay vì báo "đã có sẵn".
    - `--mau` không có chặn nào khi chạy nhầm trên môi trường thật → CLI từ chối nếu máy chủ CSDL không phải `localhost`, `127.0.0.1`, `::1`, `db` (trừ `--cho-phep-may-chu-khac`); SKU và số lô mẫu có tiền tố `MAU-` nên không đụng hàng thật (trước đây `SP0008` thật bị gắn tồn giả).
    - Seed ghi đè chỉnh sửa phân quyền của Admin (AD18) → `vai_tro_quyen` chỉ khởi tạo cho quyền mới, `vai_tro` chỉ thêm còn thiếu. Spec 02 mục 6 đã ghi rõ.
    - Số lô mẫu chứa năm nên chạy lại sang năm mới nhân đôi lô và tồn → bỏ năm khỏi số lô.
    - Nhẹ: khóa tư vấn cho seed (hai tiến trình cùng lúc từng lỗi unique); địa chỉ khách chỉ thêm khi khách mới, nhà sản xuất nhận diện theo tên (sửa dữ liệu mẫu rồi chạy lại không còn lỗi); ngày sản xuất không ở tương lai; thẻ kho nhập mẫu mang ngày của phiếu nhập (`nhap_kho(luc=...)`); CLI chỉ bắt buộc ADMIN_* khi hệ thống chưa có Admin; test mới cho ranh giới trạng thái lô, thứ tự `ORDER BY id ... FOR UPDATE` của `khoa_cac_lo`, chạy lại khác ngày/năm; bỏ test khuyến mãi theo phạm vi vì luôn đúng một cách vô nghĩa (dữ liệu mẫu không có phạm vi).
    - Ghi vào docstring `nhap_kho`: phiếu nhiều dòng phải `khoa_cac_lo` tất cả id trước; tính lại giá bình quân và kiểm tra trạng thái lô thuộc dịch vụ phiếu nhập (T3.1).

### [x] T0.6 · Hạ tầng test và CI
- **Phụ thuộc:** T0.5
- **Tiêu chí chấp nhận:**
  - [x] `tests/conftest.py`: database test riêng (tạo từ migration một lần mỗi phiên test, mỗi test chạy trong transaction rollback), `AsyncClient` gọi app, fixture đăng nhập sẵn cho từng vai trò (khách, dược sĩ, kho, admin), factories tạo dữ liệu.
  - [x] Cấu hình `pytest` + `pytest-asyncio`, `ruff` (lint + format).
  - [x] `.github/workflows/ci.yml`: backend (ruff, pytest với service `pgvector/pgvector:pg16`), frontend (lint, `tsc --noEmit`, vitest, build).
- **Ghi chú triển khai:**
  - **Một event loop cho cả phiên** (`asyncio_default_fixture_loop_scope` và `asyncio_default_test_loop_scope = "session"`): bỏ cách tạm của T0.4/T0.5 (fixture phạm vi module + `loop_scope="module"` ở từng file test). Fixture `engine_test`, `engine_migration` giờ phạm vi phiên.
  - **Database test:** `engine_test` xóa và tạo lại `DATABASE_URL_TEST`, chạy `alembic upgrade head` và `seed_co_ban` một lần mỗi phiên (không seed mẫu). `tao_lai_database` chỉ chấp nhận tên có chữ `test` (và chỉ gồm chữ/số/gạch dưới) để biến môi trường trỏ nhầm vào DB dev không xóa được dữ liệu; có test cho các tên nguy hiểm, kể cả chuỗi chèn SQL.
  - **Cô lập từng test:** `ket_noi` mở transaction ngoài, `db` là session `create_savepoint` trên đó, rollback cuối test. `app` ghi đè `get_db` bằng một `PhienRequest` trên cùng connection và vẫn bọc `begin()` nên giữ ngữ nghĩa production: request thành công thì "commit" (giải phóng savepoint), request lỗi chỉ hoàn tác phần của chính nó, `commit()` tay vẫn bị chặn. Có test cho cả ba.
  - **`db_that`** (spec 10 gọi là fixture commit thật): trả `async_sessionmaker`, dọn bằng `TRUNCATE ... RESTART IDENTITY` mọi bảng trừ `vai_tro`, `quyen`, `vai_tro_quyen` rồi seed lại cấu hình (`cau_hinh` có khóa ngoại tới `nhan_vien` nên phải truncate cùng). Test tranh chấp của T0.5 chuyển sang dùng nó.
  - **Fixture đăng nhập:** `dang_nhap_khach`, `dang_nhap_duoc_si`, `dang_nhap_kho`, `dang_nhap_admin` tạo tài khoản bằng factory và gắn access token thật. Để làm được, **access token JWT được làm ở đây thay vì T1.2**: `core/bao_mat.py::tao_access_token`, `giai_ma_access_token` (HS256, claim `sub/aud/exp/iat/jti` theo spec 06 mục 3, `aud` chỉ `khach` hoặc `noi_bo`, từ chối `alg=none`, từ chối khi `JWT_SECRET` thiếu hoặc ngắn hơn 32 ký tự; không có giá trị mặc định). Chưa có endpoint đăng nhập, refresh token, cookie, dependency `khach_hien_tai`/`nhan_vien_hien_tai`: vẫn ở T1.x. Thêm phụ thuộc `pyjwt`, cấu hình `JWT_SECRET`, `JWT_ACCESS_PHUT`, `DATABASE_URL_TEST`.
  - **Factories** (`tests/factories.py`): `tao_khach`, `tao_nhan_vien(vai_tro)`, `tao_san_pham(loai, don_vi=[...])`, `tao_lo(san_pham, so_luong, han_su_dung, trang_thai)` (nhập qua `nhap_kho`, trạng thái mặc định suy từ hạn sử dụng), `tao_don(khach, trang_thai, dong=[...])` (tổng tiền khớp CHECK, không giữ hàng). `tao_don` là chỗ duy nhất ngoài `chuyen_trang_thai()` tạo đơn ở trạng thái tùy ý, chỉ dành cho test; bộ test quét mã nguồn ở T4.x chỉ quét `app/`.
  - **Chưa làm** (thuộc task sau): `kiem_tra_bat_bien(db)` autouse cho module kho/ban_hang (T3.1, vì cần dữ liệu phân bổ), `tests/phan_quyen/registry.py` (T1.3).
  - **CI** (`.github/workflows/ci.yml`, chạy khi push lên `main`/`claude/**`, mở PR, hoặc thủ công): job backend với service `pgvector/pgvector:pg16` chạy `uv sync --locked`, `ruff check`, `ruff format --check`, migration lên-xuống-lên + `alembic check`, `scripts/so_sanh_schema.py`, pytest; job frontend chạy `npm ci`, lint, `tsc --noEmit`, `npm test --if-present -- --run`, build. **Đã chạy thật trên GitHub Actions và xanh** (lần chạy cho commit `488e1ab`, cả hai job). `concurrency` hủy lần chạy cũ của cùng nhánh nên push liên tiếp chỉ giữ lần mới nhất. Từ T0.7 job frontend tự chạy vitest.
  - **Kiểm chứng hạ tầng bằng phá thử:** để transaction ngoài commit thay vì rollback thì 5 test fail; `db_that` không dọn thì test dọn fail; request không bọc transaction thì test commit fail.
  - Tổng 337 test xanh; `ruff check` và `ruff format --check` sạch.

### [x] T0.7 · Khung frontend 3 khu
- **Phụ thuộc:** T0.1
- **Tiêu chí chấp nhận:**
  - [x] Ant Design (locale `vi_VN`, dayjs `vi`), React Router, TanStack Query, Zustand.
  - [x] 3 layout: cửa hàng (`/`), nhân viên (`/nhan-vien`), quản trị (`/quan-tri`) theo spec 09; trang 403/404.
  - [x] `npm run gen:api` sinh type từ OpenAPI của backend vào `src/api/schema.d.ts`; `src/api/client.ts` dùng `openapi-fetch`, tự gắn access token, tự refresh khi 401 một lần.
  - [x] Tiện ích `dinhDangTien`, `dinhDangNgay` (múi giờ Asia/Ho_Chi_Minh) có test vitest.
- **Ghi chú triển khai:**
  - **Thư viện:** Ant Design 6 (`vi_VN`), `react-router-dom` 7, TanStack Query 5, Zustand 5, dayjs (locale `vi`, múi giờ mặc định Asia/Ho_Chi_Minh, `lib/dayjs.ts`), `openapi-fetch`, `openapi-typescript`, vitest + Testing Library. `openapi-typescript` khai peer TypeScript 5 còn dự án dùng TypeScript 6 nên `package.json` có `overrides` để npm chấp nhận (công cụ chỉ chạy dòng lệnh, không nằm trong bundle; đã chạy thử sinh type thành công).
  - **Ba khu và bảng route theo spec:** `khu/cua-hang/trang.ts`, `khu/nhan-vien/menu.ts`, `khu/quan-tri/menu.ts` là bảng dữ liệu (đường dẫn, nhãn, mã quyền, mã chức năng); `router.tsx` sinh route và `components/xayMenu.tsx` sinh menu từ cùng bảng. Các trang chưa làm là `TrangDangXayDung` ghi mã chức năng. **Test đối chiếu từng dòng với `docs/spec/09-frontend.md` mục 2.1, 2.2, 2.3 và với `quyen.yaml`** (sửa spec mà quên bảng sẽ fail). Trang 403, 404 (404 nằm trong layout của khu), đăng nhập nội bộ giữ chỗ ở `/nhan-vien/dang-nhap`.
  - **Phân luồng và guard (QĐ-10):** `YeuCauQuyen` (route: chưa đăng nhập nội bộ thì chuyển tới đăng nhập kèm địa chỉ cũ trong `state.tu`, thiếu quyền thì 403 tại chỗ; nút: ẩn hẳn). Phiên khách không tính là đăng nhập nội bộ. Admin vào `/nhan-vien` bị chuyển sang `/quan-tri`; không phải Admin vào `/quan-tri` thấy 403 và không dựng khung. `/nhan-vien` tự chuyển tới mục đầu tiên được phép, hoặc báo "chưa được cấp quyền nào".
  - **Client API (QĐ-08):** `api/client.ts` (typed bằng `schema.d.ts` sinh từ OpenAPI, `npm run gen:api`), `api/xacThuc.ts` là middleware gắn Bearer và làm mới khi 401: đúng một lần, nhiều request lỗi cùng lúc dùng chung một lần làm mới, request đến muộn thì dùng token đã làm mới, gọi lại vẫn 401 hoặc làm mới thất bại thì đăng xuất, không làm mới cho khách vãng lai và cho các endpoint `dang-nhap`, `dang-ky`, `lam-moi`, `dang-xuat`, `quen-mat-khau`, `otp`; thân JSON của request POST được gửi lại nguyên vẹn. **Giả định đã ghi vào spec 06 mục 3:** đăng nhập và làm mới trả `{"access_token": "<jwt>"}`; T1.2, T1.3 phải khớp. Store `usePhien` chỉ ở bộ nhớ (không persist).
  - **Sửa backend nhỏ:** `GET /api/v1/health` khai `response_model` (`SucKhoe`) để type sinh ra có dữ liệu thay vì `{}`; `schema.d.ts` được commit.
  - **Tiện ích:** `dinhDangTien` (BigInt, không qua float, làm tròn half-up như backend, không hiện `-0`/`NaN`, ví dụ `125.000 ₫` với khoảng trắng không ngắt dòng), `dinhDangNgay` (đổi UTC sang giờ Việt Nam; ngày thuần `YYYY-MM-DD` như hạn sử dụng không bị dịch múi giờ; chuỗi giờ không kèm múi giờ hiểu là UTC), `coQuyen`, `coMotTrong`. Test chạy xanh ở các múi giờ UTC, Los_Angeles, Auckland.
  - **Giao diện kiểm bằng trình duyệt thật:** chụp ảnh khu cửa hàng ở 1280px và 360px với backend thật qua proxy Vite (trang chủ hiện "Backend: ok · CSDL: ok", không cuộn ngang, không cảnh báo console); đã sửa các prop Ant Design 6 bị cảnh báo là deprecated (`Alert.message`, `Space.split`).
  - **Chưa làm (thuộc task sau):** menu danh mục 3 cấp ở header và số lượng trên giỏ hàng (cần API, T2.x/T4.x), widget chat nổi (T6.x), thông báo thật của chuông (NV02, T1.3), form đăng nhập (T1.2, T1.3), guard `/tai-khoan/*` cho khách (T1.2), lazy-load từng khu để giảm bundle (hiện ~918 kB, antd chiếm phần lớn).
  - Tổng 83 test vitest xanh; `oxlint` sạch, `tsc --noEmit` sạch, `npm run build` thành công.

## P1 · Tài khoản & phân quyền

_Đăng ký/đăng nhập 2 loại tài khoản, RBAC, nhật ký, cấu hình._

### [x] T1.1 · OTP và đăng ký khách hàng
- **Chức năng:** KVL09 (Đăng ký tài khoản)
- **Phụ thuộc:** T0.6, T0.7
- **Bảng:** `khach_hang`, `ma_otp`
- **Tiêu chí chấp nhận:**
  - [x] Adapter `tin_nhan` (SMS/email) có bản giả ghi ra log và Mailpit (spec 08).
  - [x] `POST /api/v1/auth/otp` (mục đích `dang_ky`), lưu `ma_otp.ma_hash`, hết hạn 5 phút, tối đa 5 lần thử, giới hạn gửi theo `gioi_han_otp`.
  - [x] `POST /api/v1/auth/dang-ky`: SĐT bắt buộc (chuẩn hóa 0xxxxxxxxx), email tùy chọn, mật khẩu băm Argon2, lưu `dong_y_chinh_sach_luc`.
  - [x] Test: OTP sai/hết hạn/quá số lần; SĐT trùng; đăng ký thành công.
- **Giao diện:**
  - [x] Trang đăng ký 2 bước (nhập SĐT → OTP + thông tin).
- **Ghi chú triển khai:**
  - **Adapter tin nhắn** (`app/tich_hop/tin_nhan/`): giao diện `KenhTinNhan` (`gui_sms`, `gui_email`), bản giả (SMS ghi ra log với số điện thoại che dạng `091***678` và có cả mã OTP, chỉ ở chế độ giả; email gửi thật qua SMTP tới Mailpit, nếu Mailpit chưa chạy thì chỉ cảnh báo và vẫn ghi nội dung vào log để dev đọc mã), bản thật là khung báo lỗi rõ ràng vì chưa chọn nhà cung cấp (ghi QĐ khi deploy). Chọn bằng `TIN_NHAN_CHE_DO`; mẫu SMS không dấu, gọn trong một tin 160 ký tự. Test email gửi qua một máy chủ SMTP thật trong tiến trình test (`aiosmtpd`), kiểm tra tiêu đề tiếng Việt và nội dung HTML.
  - **OTP** (`modules/tai_khoan/otp.py`): 6 chữ số từ `secrets`, lưu **HMAC-SHA256 có khóa** gắn với (mục đích, SĐT, mã) chứ không phải Argon2 (mã 6 số sống 5 phút; Argon2 chỉ làm chậm server; có khóa bí mật suy từ `JWT_SECRET` qua `khoa_hmac("otp")` nên lộ DB không cho phép dò ngoại tuyến). Hiệu lực 5 phút, tối đa 5 lần thử, chỉ mã mới nhất còn hiệu lực. Giới hạn gửi đọc từ `cau_hinh.gioi_han_otp` mỗi lần (Admin đổi là áp dụng ngay): theo SĐT đếm chính xác trong DB, theo IP bằng bộ đếm cửa sổ trượt trong bộ nhớ (`core/gioi_han.py`; **không dùng slowapi** như spec 01 ghi vì giới hạn lấy từ DB lúc chạy chứ không cố định lúc import). `429 QUA_GIOI_HAN` kèm `Retry-After`. Khóa tư vấn theo (mục đích, SĐT) tuần tự hóa các thao tác OTP cùng số.
  - **Chống dò tài khoản (spec 06 mục 3), kiểm tra đến mức hành vi:** `POST /auth/otp` trả y hệt dù số đã đăng ký hay chưa; số đã đăng ký nhận SMS "đã có tài khoản" thay cho mã và vẫn có dòng OTP giữ chỗ với "mã" không khớp được, nên bộ đếm lần thử, hết hạn và khóa hành xử giống hệt số chưa đăng ký (test so sánh chuỗi phản hồi của hai loại số; phá thử bằng dòng "đã dùng" thì test fail). Số đã đăng ký cũng bị tính giới hạn gửi để không bị dùng làm máy gửi SMS.
  - **Bộ đếm lần thử phải sống qua lỗi:** `raise LoiNghiepVu` làm `get_db` rollback nên lần thử sai sẽ không được ghi và có thể dò mã vô hạn. Thêm `core.loi.tra_loi(...)` (trả về phản hồi lỗi cùng định dạng thay vì ném) để route commit rồi mới trả 422. Dùng lại cho đếm đăng nhập sai ở T1.2. Phá thử bằng `raise` thì 3 test fail.
  - **Đăng ký** (`POST /auth/dang-ky`): xác thực OTP trước (khóa dòng FOR UPDATE nên hai đăng ký đồng thời cùng một mã chỉ một cái thành công, có test hai request thật song song), rồi mới kiểm tra trùng SĐT/email (không cho dò email khi chưa có OTP đúng). OTP chỉ bị tiêu thụ khi tạo được tài khoản: lỗi trùng email thì rollback, người dùng sửa email rồi gửi lại cùng mã. Mật khẩu băm Argon2id ở luồng riêng (`bam_mat_khau_async`, vì Argon2 tốn vài chục ms CPU sẽ chặn vòng lặp sự kiện). Lưu `dong_y_chinh_sach_luc`; bắt buộc `dong_y_chinh_sach = true`. Email tùy chọn, chuẩn hóa chữ thường, trùng không phân biệt hoa thường. Phản hồi 201 chỉ có `id, ho_ten, so_dien_thoai, email`.
  - **Chuẩn hóa SĐT** (`core/dien_thoai.py`): `+84 912 345 678`, `0912.345.678`... về `0912345678`; chỉ nhận di động (03x, 05x, 07x, 08x, 09x) và chỉ chữ số ASCII (test bắt được lỗi `\d` của Python nhận cả chữ số Ả Rập). Frontend có bản chuẩn hóa tương ứng, test cùng bảng ca.
  - **Thông điệp validate tiếng Việt:** bổ sung ánh xạ cho lỗi quá ngắn/quá dài/sai định dạng/ngoài khoảng và bỏ tiền tố "Value error," của validator tự viết (`core/loi.py`).
  - **Giao diện** (`/dang-ky`): 2 bước; kiểm tra phía client giống backend; hiện số lần thử còn lại, hết hạn, giới hạn tần suất ("thử lại sau N phút"), lỗi theo từng trường (email trùng hiện dưới ô email); gửi lại mã bị khóa 60 giây; bấm đăng ký hai lần chỉ gửi một request; email tự cắt khoảng trắng. **Lỗi thật test bắt được:** hai `Form` Ant Design cùng vị trí không có `key` bị React dùng lại một phiên bản nên giữ instance `form` cũ, `setFields` rơi vào instance không gắn với form nào và lỗi không hiện (nay mỗi bước một `key`). Đã chạy luồng thật trong Chromium (420px, không cuộn ngang, không cảnh báo console): nhập số, đọc OTP từ log SMS giả, nhập sai một lần (thấy "còn 4 lần thử", bộ đếm lưu trong DB), nhập đúng, tài khoản tạo với `$argon2id$`.
  - **Phụ thuộc mới:** `aiosmtpd` (dev), `pyjwt` đã có từ T0.6. Fixture test mới: `kenh_tin_nhan` (ghi nhớ tin gửi, `ma_otp_cuoi()`), `gioi_han_ip` (bộ đếm IP riêng mỗi test), `thoi_gian` (vá `bay_gio_utc` để tua thời gian). Env: `TIN_NHAN_CHE_DO`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_NGUOI_GUI`.
  - **Chưa làm:** mục đích OTP `quen_mat_khau` (T1.2) và `don_thuoc_khach` (T5.x); chế độ `that` của kênh tin nhắn.

### [x] T1.2 · Đăng nhập khách, phiên và quên mật khẩu
- **Chức năng:** KVL10 (Đăng nhập, quên mật khẩu)
- **Phụ thuộc:** T1.1
- **Bảng:** `khach_hang`, `ma_otp`, `phien_dang_nhap`
- **Tiêu chí chấp nhận:**
  - [x] `POST /api/v1/auth/dang-nhap`: access JWT (15 phút, `aud = "khach"`) + refresh token trong cookie httpOnly; lưu hash vào `phien_dang_nhap`.
  - [x] `POST /api/v1/auth/lam-moi` xoay vòng refresh token (token cũ bị thu hồi; dùng lại token đã thu hồi thì thu hồi toàn bộ phiên của tài khoản).
  - [x] `POST /api/v1/auth/dang-xuat`, quên mật khẩu bằng OTP (mục đích `quen_mat_khau`) → thu hồi mọi phiên.
  - [x] Khóa tạm sau `so_lan_dang_nhap_sai_toi_da` lần sai (`khoa_den`). Tài khoản `bi_khoa` không đăng nhập/làm mới được.
  - [x] `GET /api/v1/toi` trả hồ sơ khách. Dependency `khach_hien_tai`, `khach_tuy_chon`.
- **Giao diện:**
  - [x] Trang đăng nhập, quên mật khẩu; store phiên (Zustand).
- **Ghi chú triển khai:**
  - **Backend** (`modules/tai_khoan/{phien,dang_nhap,cookie,router_cong_khai,router_khach}.py`, `core/phan_quyen.py`): đủ 5 endpoint của spec 06 mục 3.2 (`dang-nhap`, `lam-moi`, `dang-xuat`, `dat-lai-mat-khau`, `otp` mở rộng `quen_mat_khau` + `kenh`) và `GET /api/v1/toi`. `khach_hien_tai` đọc tài khoản từ DB mỗi request nên khóa tài khoản có hiệu lực ngay. Mọi bộ đếm cần ở lại sau lỗi (lần sai, khóa tạm, thu hồi phiên khi dùng lại token) đều do route TRẢ VỀ lỗi bằng `tra_loi`, không raise.
  - **Chống dò tài khoản:** sai mật khẩu, số lạ, đã xóa, định danh vô nghĩa cho cùng phản hồi và cùng một lần băm Argon2 (test đếm số lần băm); OTP `quen_mat_khau` cho số lạ vẫn tạo dòng giữ chỗ đếm lần thử và gửi SMS "chưa có tài khoản" (test so sánh chuỗi phản hồi hai nhánh). **Giới hạn đã chấp nhận:** khóa tạm lộ tài khoản có thật sau 5 lần sai (QĐ-11).
  - **Phiên:** refresh token 256 bit, lưu SHA-256, xoay vòng, dùng lại thì thu hồi toàn bộ; hạn tính từ lần làm mới gần nhất (`REFRESH_NGAY` = 14); token của loại tài khoản khác bị từ chối mà không thu hồi nhầm; đặt lại mật khẩu thu hồi mọi phiên và xóa khóa tạm nhưng không mở khóa tài khoản Admin đã khóa. Biến mới `COOKIE_SECURE` (mặc định `true`; `.env.example` đặt `false` cho dev http). Giới hạn đăng nhập theo IP: 20 lần/10 phút (`lay_bo_gioi_han_dang_nhap`).
  - **Test** (backend 566 xanh, thêm 79 so với T1.1): `test_dang_nhap.py`, `test_phien.py` (kể cả tranh chấp hai lần làm mới đồng thời bằng `db_that`), `test_quen_mat_khau.py`, `test_khach_hien_tai.py` (kể cả test duyệt OpenAPI: mọi route `/api/v1/toi*` không token thì 401). Fixture mới: `gioi_han_dang_nhap`, `client_https` (giữ cookie `Secure`), `KenhGhiNho.ma_otp_email_cuoi`, `thoi_gian` vá thêm các module phiên/đăng nhập; autouse `cau_hinh_co_dinh_cho_test` ghim `COOKIE_SECURE`, `REFRESH_NGAY`, `JWT_ACCESS_PHUT` để test không phụ thuộc `.env` (một lần suýt sai vì cookie không `Secure` bị jar tự gửi lại; helper `lam_moi(client, None)` giờ xóa jar). Đã sửa test T1.1 từng khẳng định `quen_mat_khau` bị từ chối.
  - **Kiểm chứng bằng phá thử:** 17 đột biến (raise thay vì return làm mất bộ đếm, bỏ thu hồi toàn bộ khi dùng lại, bỏ `FOR UPDATE`, đặt lại không thu hồi phiên/không mở khóa tạm, số lạ không băm, bỏ kiểm tra khóa tạm, bộ đếm không reset, guard bỏ kiểm tra khóa, `/toi` không đòi đăng nhập, cookie không HttpOnly, nhận refresh token của loại khác, làm mới không kiểm tra khóa, đăng xuất không thu hồi, bỏ giới hạn IP, `quen_mat_khau` coi như đăng ký) đều bị ít nhất một test bắt.
  - **Frontend:** trang `/dang-nhap` (`?tiep=` chỉ nhận đường dẫn nội bộ), `/quen-mat-khau` (2 bước, chọn SMS/email), nút Đăng xuất và tên khách ở header, `api/goi.ts` dùng chung với đăng ký, `useDemNguoc`. Khôi phục phiên khi tải trang (`api/khoiPhuc.ts`): có "gợi ý" `phien_goi_y` trong localStorage (chỉ `khach`/`noi_bo`, không token, không hồ sơ) thì làm mới + lấy `/toi`; chạy đúng một lần mỗi lần tải; header chờ `daKhoiPhuc` để không nhấp nháy "Đăng nhập". Làm mới tuần tự giữa các tab bằng Web Locks (QĐ-11). `api/client.ts` thêm `credentials: 'include'`. 199 test vitest xanh (cả khi `TZ=America/Los_Angeles`), `tsc`, oxlint, build sạch.
  - **Đã chạy thật trên Chromium (390px) với backend + Vite + seed mẫu, 24/24 kiểm tra đạt:** vãng lai không gọi làm mới; sai mật khẩu; đăng nhập quay lại `?tiep=`; cookie `refresh_token` HttpOnly/SameSite=Lax/Path=/api/v1/auth, localStorage chỉ có `phien_goi_y`, `document.cookie` không thấy token; tải lại khôi phục phiên với đúng 1 lần làm mới và token xoay vòng; 4 tab mở cùng lúc đều còn đăng nhập (tắt Web Locks thì chỉ 1/4); đăng xuất xóa cookie và gợi ý; quên mật khẩu bằng OTP SMS (đọc mã từ log SMS giả), mật khẩu cũ bị từ chối, mật khẩu mới đăng nhập được; `?tiep=//trang-lua-dao.example` bị bỏ qua; không cuộn ngang.
  - **Chưa làm / để task sau:** trang `/tai-khoan` vẫn là trang giữ chỗ (T2.x–T4.x), khôi phục phiên nội bộ cùng đăng nhập nội bộ (T1.3), `don_thuoc_khach` cho OTP (T5.x). Chạy `/review-nghiep-vu` gộp T1.1–T1.3 sau T1.3 (phần phân quyền thật nằm ở T1.3).


### [x] T1.3 · Xác thực nhân viên, RBAC và nhật ký
- **Chức năng:** NV01 (Đăng nhập, đổi mật khẩu), NV02 (Xem thông báo, cập nhật hồ sơ cá nhân)
- **Phụ thuộc:** T1.2
- **Bảng:** `nhan_vien`, `phien_dang_nhap`, `thong_bao`
- **Tiêu chí chấp nhận:**
  - [x] `POST /api/v1/noi-bo/auth/dang-nhap` (`aud = "noi_bo"`), bắt đổi mật khẩu lần đầu (`phai_doi_mat_khau`), đổi mật khẩu thu hồi mọi phiên.
  - [x] `GET /api/v1/noi-bo/toi` trả hồ sơ + danh sách mã quyền và mức (`day_du`/`chi_xem`).
  - [x] `core/phan_quyen.py`: `yeu_cau_quyen(ma, muc="day_du")` đọc quyền từ DB (cache 60 giây), kiểm tra trạng thái tài khoản mỗi request.
  - [x] `core/nhat_ky.py`: `ghi_nhat_ky(...)` ghi `nhat_ky_he_thong` (không ghi mật khẩu, OTP, dữ liệu sức khỏe).
  - [x] Registry endpoint → quyền + test ma trận phân quyền tự sinh từ `quyen.yaml` (spec 10 mục 3); test thất bại nếu có route `/noi-bo` chưa khai báo.
  - [x] Thông báo nội bộ: `GET /api/v1/noi-bo/thong-bao`, đánh dấu đã đọc; sửa hồ sơ cá nhân.
- **Giao diện:**
  - [x] Trang đăng nhập nội bộ, đổi mật khẩu bắt buộc, menu theo quyền, chuông thông báo.
- **Ghi chú triển khai:**
  - **Backend:** `core/phan_quyen.py` (`nhan_vien_hien_tai`, `yeu_cau_quyen(ma, muc, *, ke_ca_chua_doi_mat_khau)`, cache quyền 60 giây bằng đồng hồ đơn điệu, `xoa_cache_quyen`), `core/danh_muc_quyen.py` (mã quyền hợp lệ đọc từ `quyen.yaml`, sai mã thì lỗi ngay lúc dựng route), `core/nhat_ky.py`, module `modules/nhan_vien/` (`/noi-bo/auth/*`, `/noi-bo/toi`) và `modules/thong_bao/`. Phần làm mới/đăng xuất/giới hạn IP/cookie của khách và nhân viên tách ra `modules/tai_khoan/phien_http.py` + `cookie.py` dùng chung (không viết logic nhạy cảm hai lần); `dang_nhap.py` tách `kiem_tra_mat_khau_va_khoa` dùng chung cho đăng nhập và đổi mật khẩu. Mã lỗi mới `MAT_KHAU_CU_SAI` (422). Chi tiết hợp đồng: spec 06 mục 3.3; quyết định: QĐ-12.
  - **Phân quyền:** thao tác ghi luôn cần `day_du` dù route khai báo `muc="xem"`; `gioi_han` lạ coi là chỉ xem; trạng thái tài khoản, vai trò và quyền đọc từ DB mỗi request nên khóa/đổi vai trò có hiệu lực ngay. Route nội bộ viết `Annotated[NhanVien, Depends(yeu_cau_quyen(...))]` (ruff B008).
  - **Test** (backend 736 xanh, thêm 170 so với T1.2): `tests/phan_quyen/` (guard, registry, ma trận), `tests/nhan_vien/` (đăng nhập, phiên, đổi mật khẩu, hồ sơ), `tests/thong_bao/`, `tests/test_nhat_ky.py`. `registry.py` + `ma_tran.py` duyệt cây route THẬT (kể cả router include lồng của FastAPI 0.143) và đối chiếu từng route với dependency `yeu_cau_quyen` gắn trên nó; ma trận 3 vai trò × mọi route sinh từ `quyen.yaml`. Vì `profile.self` ai cũng có nên ma trận thật chưa phân biệt được vai trò, nên có thêm ma trận trên route thử dùng nhiều mã quyền khác nhau và các test chứng minh bộ kiểm tra bắt được: route chưa vào registry, quên `yeu_cau_quyen`, dùng nhầm mã/mức, ghi khai báo `xem`, registry lỗi thời, route công khai có quyền, bật cờ bỏ qua đổi mật khẩu sai chỗ, route quên kiểm tra quyền (kho và Admin lọt vào), route chặn nhầm người đúng quyền.
  - **Kiểm chứng bằng phá thử:** 24 đột biến (bỏ kiểm tra quyền, ghi lọt qua mức xem, bỏ bắt đổi mật khẩu, cache không hết hạn, guard bỏ kiểm tra khóa, `gioi_han` lạ thành đầy đủ, nhận token khách, đổi mật khẩu không thu hồi phiên / không bỏ cờ / khóa không thu hồi, thông báo không lọc chủ sở hữu ở cả bốn truy vấn, `lien_ket` ngoài ứng dụng, làm mới không kiểm tra khóa, cookie trùng tên khách, giới hạn IP dùng chung, đăng nhập không ghi nhật ký, nhật ký không che, hồ sơ nhận email, ghi số điện thoại đầy đủ, route dùng nhầm mã quyền) đều bị ít nhất một test bắt.
  - **Frontend:** `/nhan-vien/dang-nhap` thật (quay lại `state.tu` nếu là đường dẫn nội bộ; Admin vào `/quan-tri`), trang `/nhan-vien/tai-khoan` (hồ sơ + đổi mật khẩu, chuyển bắt buộc từ mọi trang nội bộ khi `phaiDoiMatKhau`), `ChuongThongBao` (số chưa đọc làm mới mỗi phút, 10 thông báo mới nhất, bấm để đọc và đi tới liên kết nội bộ; không dùng antd `List` vì đã deprecated), đăng xuất gọi API nội bộ. Khôi phục phiên nội bộ khi tải trang (`api/khoiPhuc.ts`) lấy lại cả quyền và cờ bắt đổi mật khẩu từ `/noi-bo/toi`, làm mới tuần tự giữa các tab bằng Web Locks như phiên khách. 253 test vitest xanh (cả khi `TZ=America/Los_Angeles`), `tsc`, oxlint, build sạch.
  - **Đã chạy thật trên Chromium với backend + Vite, 34/34 kiểm tra đạt:** vào `/quan-tri` khi chưa đăng nhập bị chuyển; Admin lần đầu bị đưa sang đổi mật khẩu từ mọi URL nội bộ và tải lại vẫn bị bắt; cookie `refresh_token_noi_bo` HttpOnly Path=/api/v1/noi-bo/auth, localStorage chỉ có gợi ý; đổi mật khẩu sai/yếu/đúng, đổi xong vào thẳng khu quản trị với refresh token mới; tải lại khôi phục phiên và quyền; sửa hồ sơ (SĐT `+84 912 345 678` lưu thành `0912345678`) và tải lại thấy đúng; đăng xuất xóa cookie và gợi ý; mật khẩu cũ bị từ chối, mật khẩu mới vào được; dược sĩ thấy chuông 3 chưa đọc, bấm thông báo sang liên kết nội bộ và còn 2, đánh dấu tất cả; 4 tab nội bộ mở cùng lúc đều còn đăng nhập; khách đã đăng nhập vẫn bị chặn ở khu nội bộ. (Nhờ phép kiểm này phát hiện và bỏ antd `List` deprecated, sửa tiêu đề thông báo dính liền giờ.)
  - **Rà soát nghiệp vụ T1.1–T1.3 (agent `nghiep-vu-reviewer`):** không có lỗi mức Cao; 2 phát hiện Trung bình đã sửa kèm test, 8 phát hiện Thấp ghi vào "Việc phát sinh". (1) Làm mới xoay vòng token rồi mới kiểm tra khóa nên khóa tạm (người lạ gửi sai mật khẩu 5 lần) làm chủ tài khoản mất mọi phiên, trái QĐ-12: nay `lam_moi_phien` kiểm tra trạng thái trong lần khóa tài khoản, khóa tạm trả 403 mà không xoay vòng/thu hồi/xóa cookie, Admin khóa/xóa mềm thì thu hồi tất cả; frontend không xóa gợi ý phiên khi 403 khóa tạm. (2) Làm mới chạy đồng thời với đổi/đặt lại mật khẩu: tái hiện được thành `DeadlockDetectedError` (500) vì làm mới chỉ khóa dòng phiên còn hai luồng kia khóa tài khoản trước; nay làm mới khóa tài khoản trước, phiên sau (QĐ-12). Phá thử 4 đột biến của phần sửa đều bị bắt; backend 742 test, frontend 253 test xanh.
  - **Chưa làm / để task sau:** Admin đặt lại mật khẩu và khóa/mở tài khoản nhân viên, kèm thu hồi phiên (T1.4); thông báo của khách (KTV13); gửi thông báo từ các nghiệp vụ (đơn mới, chat, kho: HT07 và các task nghiệp vụ, dùng `thong_bao.service.gui_cho_nhan_vien`). Chạy `/review-nghiep-vu` gộp T1.1–T1.3 ngay sau commit này.


### [x] T1.4 · Quản lý nhân viên, vai trò và quyền
- **Chức năng:** AD01 (Quản lý tài khoản nhân viên), AD18 (Quản lý vai trò & phân quyền)
- **Phụ thuộc:** T1.3
- **Bảng:** `nhan_vien`, `vai_tro`, `phien_dang_nhap`, `nhat_ky_he_thong`, `quyen`, `vai_tro_quyen`
- **Tiêu chí chấp nhận:**
  - [x] CRUD nhân viên (không xóa cứng), khóa/mở, đặt lại mật khẩu (sinh mật khẩu tạm + `phai_doi_mat_khau`), gán vai trò; khóa → thu hồi phiên.
  - [x] Chặn tự khóa/tự hạ quyền; luôn còn ≥ 1 Admin hoạt động (`ma_loi = "PHAI_CON_ADMIN"`).
  - [x] Xem quyền, gán/bỏ quyền cho PHARMACIST/WAREHOUSE; không bỏ quyền của ADMIN. Mọi thay đổi ghi nhật ký.
- **Giao diện:**
  - [x] Danh sách nhân viên (lọc, tìm), form nhân viên, màn ma trận vai trò - quyền.
- **Ghi chú triển khai:**
  - **Backend:** `modules/nhan_vien/{quan_tri,router_quan_tri,schemas_quan_tri}.py` (AD01) và `modules/vai_tro/*` (AD18); API ở spec 06 mục 3.4, 3.5. Quyết định ở QĐ-13: mã lỗi mới `TU_THAY_DOI_KHONG_DUOC` (403, đã thêm vào spec 06 và `core/loi.py`); khóa mọi dòng Admin theo id tăng dần trong một câu để "luôn còn ≥ 1 Admin" đúng cả khi hai Admin làm nhau đồng thời; ADMIN bất biến, `profile.self` bắt buộc, quyền chuyên môn chỉ PHARMACIST; đổi vai trò thu hồi phiên, đổi quyền vai trò thì không (giao diện đồng bộ qua `/noi-bo/toi`).
  - **Phần dùng chung thêm vào:** `core/phan_trang.sap_xep_theo` + `SapXepQuery` (tham số `sap_xep` của spec 06 mục 5, danh sách trường cho phép theo endpoint, khóa phụ `id`; áp cho `GET /noi-bo/nhan-vien`, giao diện chưa có cột bấm sắp xếp), `core/bao_mat.tao_mat_khau_tam()` (CSPRNG), `core/tham_so.py` (`IdInt`, `IdBigInt`), `core/phan_quyen.xoa_cache_quyen_sau_commit(db)`; fixture `clients_theo_vai_tro` chuyển lên `tests/conftest.py`; registry và ma trận phân quyền mở rộng cho route AD01/AD18 (ca id `2000000000`, vai trò `KHONG_CO_VAI_TRO`).
  - **Giao diện:** `/quan-tri/nhan-vien` (bảng lọc đồng bộ URL, form tạo/sửa, mật khẩu tạm một lần) và `/quan-tri/vai-tro` (ma trận quyền, hộp xác nhận liệt kê thay đổi); `useDongBoPhienNoiBo` cập nhật quyền của phiên đang mở. Lệch spec 09: hàng `/nhan-vien`, `/vai-tro` của bảng 2.3 tách làm hai dòng (mỗi trang một mã quyền).
  - **Lỗi chỉ lộ khi chạy trên Chromium thật, đã sửa:** `goi()` coi `data === undefined` là thất bại nên `DELETE → 204` báo nhầm "không kết nối được máy chủ" và không tải lại danh sách (test đơn vị dùng mock không có `response.ok` nên bỏ sót); cảnh báo antd `maskClosable` đã lỗi thời. Kiểm chứng trình duyệt 27/27 (tạo, mật khẩu tạm một lần, trùng email, tìm không dấu, đổi mật khẩu lần đầu, khóa → mất phiên, đặt lại, đổi quyền → menu phiên đang mở cập nhật không cần đăng nhập lại, xóa mềm).
  - **Kiểm thử:** backend 848 test; frontend 290 test (cả `TZ=America/Los_Angeles`). 26 đột biến (bỏ khóa dòng Admin, bỏ kiểm tra tự thay đổi, bỏ xóa cache sau commit, bỏ thu hồi phiên, …) đều bị test bắt.
  - **Rà soát nghiệp vụ (agent `nghiep-vu-reviewer`): không có mức Cao; 3 Trung bình đã sửa trong cùng task, 7 Thấp ghi ở "Việc phát sinh".** M1: `staff.manage`/`role.manage` gán được cho vai trò khác nên người nhận tự tạo Admin hoặc tự cấp quyền (đã chạy thử); M2: gán `refund.confirm` cho dược sĩ phá tách nhiệm vụ; sửa cả hai bằng một quy tắc (18 quyền chỉ ADMIN không gán được cho vai trò khác, đọc từ `quyen.yaml`) cộng chốt "người thực hiện là ADMIN" ở service. M3: `PUT` thay toàn bộ nên trang cũ ngầm cấp lại quyền vừa bị gỡ; thêm khóa lạc quan `phien_ban` (`409 DU_LIEU_DA_THAY_DOI`). Quyết định ở QĐ-13. 11 đột biến của phần sửa đều bị test bắt; Chromium thật 14/14 (quyền chỉ Admin bị khóa trên giao diện, kịch bản trang cũ nhận 409, tải lại bản mới, giữ thay đổi của người dùng).
  - **Lỗi hạ tầng test tìm thấy:** `db_that` dọn bằng TRUNCATE nhưng giữ `vai_tro_quyen`, mà seed cố ý không ghi đè phân quyền đã có, nên test AD18 commit thật để lại ma trận lệch cho test sau (test viết sau bị lỗi giả). Sửa: TRUNCATE cả `quyen`, `vai_tro_quyen` rồi seed lại; có test hồi quy (`test_db_that_3/4`).
  - **Việc để task sau:** nút CLI khôi phục Admin duy nhất (đã ghi ở "Việc phát sinh").

### [x] T1.5 · Quản lý khách hàng
- **Chức năng:** AD02 (Quản lý khách hàng)
- **Phụ thuộc:** T1.3
- **Bảng:** `khach_hang`, `don_hang`, `phien_dang_nhap`
- **Tiêu chí chấp nhận:**
  - [x] Danh sách khách (tìm theo tên/SĐT/email), xem lịch sử mua (dùng lại API đơn hàng khi có), khóa/mở (thu hồi phiên).
  - [x] Response không bao giờ chứa `ho_so_suc_khoe`, `di_ung` (test khẳng định).
- **Giao diện:**
  - [x] Danh sách và chi tiết khách hàng.
- **Ghi chú triển khai:**
  - **Backend:** `modules/tai_khoan/{quan_tri_khach,router_quan_tri_khach,schemas_quan_tri_khach}.py`; API ở spec 06 mục 3.6, quyết định ở QĐ-14. Danh sách có tìm (tên không dấu, email, số điện thoại gõ kiểu `+84 902-345-678`), lọc trạng thái, `sap_xep`; chi tiết; lịch sử mua tóm tắt (đọc thẳng `don_hang` vì API đơn hàng của Admin chưa có, dùng lại ở T4.x); khóa (thu hồi mọi phiên, có hiệu lực ngay, lý do chỉ ghi nhật ký) và mở khóa (gỡ cả khóa tạm). Không đổi schema CSDL.
  - **Không lộ dữ liệu sức khỏe:** schema khai báo từng trường; test gieo hồ sơ sức khỏe và dị ứng thật rồi quét mọi khóa và giá trị ở danh sách, chi tiết, lịch sử mua và phản hồi khóa.
  - **Phần dùng chung thêm vào:** `core/phan_trang.sap_xep_theo` + `SapXepQuery` (nợ từ T0.2, xem T1.4), `core/tim_kiem.mau_tim_like` (AD01 chuyển sang dùng), `lib/trangThai.ts` + `NhanTrangThai` (spec 09 mục 3, 4; test đối chiếu enum của OpenAPI), `khu/quan-tri/khach-hang/*`. Lệch spec 09: dòng `/khach-hang` của bảng 2.3 thêm `/khach-hang/:id`.
  - **Lỗi chỉ lộ trên Chromium thật, đã sửa:** liên kết `to="/khach-hang/1"` bỏ mất tiền tố `/quan-tri` (đưa người dùng ra khu cửa hàng), test đơn vị chạy ở gốc nên không thấy; nay dựng từ đường dẫn hiện tại và có test chạy dưới tiền tố. Kiểm chứng trình duyệt 24/24: tìm kiếm/sắp xếp/lọc trên URL, chi tiết và lịch sử mua không lộ người nhận, địa chỉ, hồ sơ sức khỏe; khách đang đăng nhập bị khóa thì mất phiên ngay, đăng nhập báo tài khoản bị khóa, mở khóa đăng nhập lại được; id vượt int32 và id không tồn tại.
  - **Kiểm thử:** backend 37 test riêng cho AD02 (gồm hai Admin khóa cùng lúc chỉ ghi một nhật ký, khóa đồng thời với làm mới phiên không deadlock và không để lại phiên sống); frontend 28 test trang + 6 test nhãn trạng thái. 17 đột biến backend và 10 đột biến frontend đều bị test bắt.
  - **Rà soát nghiệp vụ (agent `nghiep-vu-reviewer`): không có mức Cao; 1 Trung bình đã sửa, 5 Thấp ghi ở "Việc phát sinh" hoặc spec/QĐ.** M1: nút chuyển trang ở danh sách khách không hoạt động (antd gọi `Table.onChange` sau `pagination.onChange` và xử lý sắp xếp xóa mất `trang` vừa đặt; test cũ chỉ mở sẵn `?trang=2`); sửa bằng cách chỉ xử lý khi `extra.action === 'sort'`, có test bấm trang 1, 2, 3 và đổi sắp xếp ở trang 2. L2 (mở khóa làm access token cũ dùng lại được tối đa 15 phút) và L3 (`ly_do` không được kiểm tra nội dung) ghi thành giới hạn ở spec 06 mục 3.6 và QĐ-14.
  - **Việc để task sau:** trang Nhân viên (AD01) chưa có cột bấm sắp xếp dù API hỗ trợ `sap_xep`; làm giống trang Khách hàng (đã ghi ở "Việc phát sinh").

### [x] T1.6 · Cấu hình hệ thống và nhật ký
- **Chức năng:** AD08 (Cấu hình hệ thống), AD15 (Xem nhật ký hệ thống)
- **Phụ thuộc:** T1.3
- **Bảng:** `cau_hinh`, `nhat_ky_he_thong`
- **Tiêu chí chấp nhận:**
  - [x] Đọc/sửa `cau_hinh` với schema kiểm tra kiểu cho từng khóa (spec 02 mục 6); ghi `nhan_vien_cap_nhat_id`.
  - [x] Tra cứu nhật ký theo bảng, bản ghi, nhân viên, khoảng thời gian; hiển thị giá trị cũ/mới.
- **Giao diện:**
  - [x] Trang cấu hình (nhóm theo chủ đề), trang nhật ký.
- **Ghi chú triển khai:**
  - **Backend:** `modules/he_thong/{cau_hinh_service,nhat_ky_service,router_cau_hinh,router_nhat_ky,schemas}.py` và `core/cau_hinh_khoa.py`; API ở spec 06 mục 3.7, 3.8; quyết định ở QĐ-15. Spec 02 mục 6 thêm bảng "Kiểu và giới hạn" (trước đó roadmap viết "schema kiểm tra kiểu" nhưng spec chưa nêu kiểu và khoảng từng khóa). AD08: 15 khóa, kiểm tra kiểu và khoảng, khóa lạc quan `phien_ban`, ghi người cập nhật và nhật ký, có hiệu lực ngay; bốn khóa `ai_*` để AD09. AD15: lọc theo bảng, bản ghi, người thực hiện, hành động, khoảng ngày (giờ Việt Nam, gồm hai đầu), phân trang ổn định, danh sách giá trị lọc; chỉ đọc.
  - **Dữ liệu sức khỏe không lộ qua nhật ký:** `ghi_nhat_ky` bỏ giá trị của `ho_so_suc_khoe`, `di_ung` ngay lúc ghi, AD15 che lại lúc đọc (dòng cũ lỡ có vẫn không hiện), thêm bốn khóa nhạy cảm vào danh sách che. Xử lý xong mục "Việc phát sinh" T1.3-rv về `che_du_lieu_nhay_cam`.
  - **Phần dùng chung:** `dinhDangNgay(..., 'ngayGioGiay')`; `lib/cauHinh.ts` (kiểm tra giá trị phía client, so sánh nội dung, nhóm theo chủ đề), `lib/nhatKy.ts` (nhãn hành động, so sánh cũ/mới), `khu/quan-tri/{cau-hinh,nhat-ky}/*`. Không đổi schema CSDL.
  - **Lỗi chỉ lộ khi chạy thật:** `InputNumber` của antd có `min`/`max` âm thầm ép giá trị (gõ 99 thành 20) nên không báo lỗi: bỏ `min`/`max`, tự kiểm tra và tắt nút Lưu.
  - **Kiểm thử:** backend 160 test riêng (86 test bảng kiểu/giới hạn gồm đối chiếu spec 02 và mọi giá trị mặc định của seed; 74 test API AD08/AD15 gồm hai Admin sửa cùng khóa chỉ một bên thắng, dữ liệu sức khỏe và bí mật không lộ, khoảng ngày biên giờ Việt Nam, NUL trong tham số); frontend 68 test. 22 đột biến backend và 19 đột biến frontend đều bị bắt (một đột biến tương đương: `Checkbox.Group` vốn trả giá trị theo thứ tự lựa chọn). Chromium thật 28/28 (kiểm tra khoảng và định dạng tiền, 409 giữ giá trị đang gõ, nhật ký lọc/mở rộng cũ→mới, dòng sức khỏe và khóa bí mật không lộ).
  - **Rà soát nghiệp vụ (agent `nghiep-vu-reviewer`): không có mức Cao hay Trung bình; 5 Thấp.** Hai điểm mâu thuẫn trực tiếp với quy tắc đã ghi ở chính task này được sửa kèm test: L1 (`den_ngay=9999-12-31` và `tu_ngay=0001-01-01` trả 500 thay vì 400: giới hạn miền ngày 2000..2100 ở router và ở giao diện) và L2 (ô tiền xóa trắng thành 0 vẫn cho Lưu vì `Number('')` là 0, mà 0 ở `mien_phi_ship_tu` nghĩa là luôn miễn phí vận chuyển). L3, L4, L5 ghi ở "Việc phát sinh"; câu chữ spec 06 mục 3.7 về nhật ký `tao` đã sửa.
  - **Việc để task sau:** index cho truy vấn chỉ lọc theo `created_at`/`hanh_dong` và `DISTINCT` của danh sách giá trị lọc khi nhật ký lớn (ghi ở "Việc phát sinh").

## P2 · Sản phẩm & nội dung

_Danh mục, sản phẩm, nội dung chuyên môn, trang cửa hàng, tìm kiếm từ khóa, bài viết._

### [x] T2.1 · Danh mục và dữ liệu dùng chung
- **Chức năng:** AD03 (Quản lý danh mục), AD05 (Quản lý hoạt chất, thương hiệu, nhà sản xuất)
- **Phụ thuộc:** T1.4
- **Bảng:** `danh_muc`, `hoat_chat`, `thuong_hieu`, `nha_san_xuat`, `thanh_phan`
- **Tiêu chí chấp nhận:**
  - [x] Cây danh mục tối đa 3 cấp (từ chối cấp 4), sắp xếp `thu_tu`, ẩn khỏi cửa hàng hoặc xóa mềm (QĐ-16); không xóa danh mục còn sản phẩm (`ma_loi = "DANH_MUC_CON_SAN_PHAM"`) hoặc còn danh mục con (`DANH_MUC_CON_DANH_MUC`).
  - [x] CRUD thương hiệu, nhà sản xuất (unique tên + quốc gia), hoạt chất (tên chuẩn + tên khác).
- **Giao diện:**
  - [x] Cây danh mục kéo thả, bảng thương hiệu/NSX/hoạt chất.
- **Ghi chú triển khai:**
  - **Quyết định ở QĐ-16** (cần người xác nhận mục đầu): "ẩn" (`dang_hien_thi`, đảo ngược được, ẩn cả cây con khỏi cửa hàng) khác "xóa mềm" (`deleted_at`); xóa danh mục bị chặn khi còn sản phẩm (`DANH_MUC_CON_SAN_PHAM`) hoặc còn danh mục con (mã mới `DANH_MUC_CON_DANH_MUC`); đổi tên không đổi `slug`; chuyển cha và sắp xếp là một thao tác `PUT .../vi-tri`; AD05 xóa cứng dựa vào khóa ngoại (`409 DU_LIEU_DANG_DUOC_SU_DUNG`, mã mới, thông điệp chung không nói ai dùng). Spec 05 (AD03), 06 mục 3.9, 3.10 và bảng mã lỗi, 09 đã sửa theo.
  - **Rà soát nghiệp vụ (agent `nghiep-vu-reviewer`): không có mức Cao; 3 Trung bình đã sửa kèm test, 5 Thấp (4 sửa vì cùng hàm/cùng quy tắc, 1 là việc quy trình).** M1: xóa hoạt chất là kênh dò dị ứng của khách (tạo hoạt chất mồi rồi thử xóa: 409 = có khách dị ứng; kể cả vai trò được ủy `master_data.manage`), QĐ-16 bản đầu đã mô tả thấp hơn thực tế ("một bit tổng hợp"): nay hoạt chất không có `DELETE` (405 giống hệt cho mọi hoạt chất, giao diện bỏ nút Xóa). M2: JSON `"\ud800"` (surrogate đơn lẻ) làm 500 ở mọi trường chuỗi: bị chặn cùng ký tự điều khiển. M3: hộp thoại danh mục xóa chữ đã gõ khi máy chủ báo lỗi vì effect phụ thuộc đối tượng dựng mới mỗi lần render (đã tái hiện, sửa bằng khóa ổn định, test và Chromium). Thấp đã sửa: ký tự định dạng vô hình (U+200B...) qua mặt kiểm tra trùng tên, `/\host` lọt quy tắc "không `//host`", thông điệp tiếng Anh cho tên rỗng/quá dài (`too_long`, `too_short`), sắp xếp lại không cập nhật `updated_at` của anh em và nhật ký chỉ có một dòng. Thấp còn lại: `bo_dau()` tách ra mà chưa ai dùng ngoài `slug.py`, `KHONG_NUL` còn nhân đôi ở `router_nhat_ky.py`. **Việc quy trình cho người dùng:** QĐ-16 mục "ẩn khác xóa mềm" cần người xác nhận (CLAUDE.md: spec mơ hồ thì hỏi); tôi chọn và ghi lại để không dừng cả lộ trình.
  - **Chạy lại sau sửa:** test mới cho surrogate, ký tự vô hình, `/\host`, hoạt chất 405 giống hệt nhau, `updated_at` anh em, giữ chữ đang gõ; backend 1351 test, frontend 442 test (cả `TZ=America/Los_Angeles`), build, `scripts/so_sanh_schema.py`, migration lên-xuống-lên và ruff không bộ nhớ đệm; Chromium thật 32/32 (kể cả giữ chữ đang gõ và `DELETE` hoạt chất là 405).
  - **Backend:** `modules/san_pham/{danh_muc,du_lieu_chung}.py` + hai router, schema riêng; ghi cây tuần tự hóa bằng khóa tư vấn, xóa khóa dòng trước khi đếm sản phẩm (đã tái hiện đua nhau bằng test đồng thời); trùng tên AD05 không phân biệt hoa thường/dấu, tuần tự hóa theo nhóm (DB unique không đủ vì `quoc_gia` NULL và hoa thường). Mới dùng chung: `core/kieu_du_lieu.py` (tên, đường dẫn, văn bản tùy chọn, từ chối ký tự điều khiển kể cả NUL), `core/tham_so.tu_khoa_tim` (tham số `q` chặn NUL), `lay_trang(nhieu_cot=True)` (lỗi 500 khi truy vấn chọn thêm cột đếm), `factories.tao_danh_muc`.
  - **Frontend:** `khu/quan-tri/danh-muc/` (antd `Tree` kéo thả; phép tính vị trí/chống vòng/giới hạn 3 cấp tách thành hàm thuần `cayDanhMuc.ts` có test) và `khu/quan-tri/du-lieu-chung/` (ba tab dùng chung một bảng và một form dựng từ cấu hình nhóm); `lib/duLieuChung.ts` kiểm tra ô nhập cùng bảng ca với backend. Test truy vấn `ByRole` trong bảng antd phải dùng `hidden: true`: không có thì mỗi lần gọi mất cả chục giây (jsdom tính `getComputedStyle` cho từng phần tử).
  - **Đã chạy thật (trước rà soát):** backend 1335 test, frontend 441 test, build, `scripts/so_sanh_schema.py`. 50 đột biến vào service/schema/router của AD03 và AD05: 41 bị bắt ngay, 4 mutant sống do thiếu test (cắt vòng cho thông điệp riêng, kẹp chỉ số vị trí, POST có trường lạ, đua đổi tên) đã bổ sung test và bị bắt, 5 còn lại tương đương (`LIKE` mặc định của PostgreSQL đã thoát bằng `\`, `cot == None` tự thành `IS NULL`, `yeu_cau_quyen` đã ép `day_du` cho thao tác ghi, nhánh `raise` lại `IntegrityError` không phải khóa ngoại không có đường vào, kiểm tra vòng dư với giới hạn 3 cấp nhưng cho thông điệp đúng). Chromium thật 32/32 (kéo thả bằng chuột thật vào trong/trước/sau, kéo vào cây con của chính nó và vượt 3 cấp bị chặn mà không gọi API, ẩn/hiện, xóa, trùng tên, tìm không dấu, xóa hoạt chất đang dùng).
  - **Chưa làm:** trang xem cho dược sĩ (khu `/nhan-vien` chưa có mục dữ liệu chung; dược sĩ chỉ đọc qua API, đã có test, và dùng ở bộ chọn của form sản phẩm T2.2); áp `dang_hien_thi` của danh mục (và tổ tiên) vào danh sách công khai (T2.4).

### [x] T2.2 · Sản phẩm: thông tin thương mại
- **Chức năng:** AD04 (Quản lý sản phẩm – thông tin thương mại)
- **Phụ thuộc:** T2.1
- **Bảng:** `san_pham`, `don_vi_quy_doi`, `anh_san_pham`
- **Tiêu chí chấp nhận:**
  - [x] CRUD sản phẩm (SKU, slug tự sinh không dấu, loại, danh mục, thương hiệu, NSX, SĐK, dạng bào chế, quy cách, đối tượng, nổi bật, giới hạn số lượng/đơn, dùng định kỳ).
  - [x] Đơn vị quy đổi: đúng 1 đơn vị `he_so = 1`, tối đa 1 mặc định, mã vạch; giá theo từng đơn vị. Thành phần (hoạt chất + hàm lượng).
  - [x] Upload ảnh (spec 08 lưu trữ công khai), đặt ảnh chính, sắp xếp.
  - [x] Admin không sửa được nội dung chuyên môn (endpoint chuyên môn yêu cầu quyền của dược sĩ). *Phần của AD04 xong: mọi body từ chối trường lạ (`chi_dinh`, `lieu_dung_tham_khao`... là 400, có test); endpoint chuyên môn của dược sĩ là việc của T2.3.*
- **Giao diện:**
  - [x] Danh sách sản phẩm (lọc loại/danh mục/trạng thái), form sản phẩm nhiều tab.
- **Ghi chú triển khai:**
  - **Quyết định ở QĐ-17:** AD04 chỉ thông tin thương mại và chỉ ADMIN ghi; một `phien_ban` (khóa lạc quan) cho cả sản phẩm dùng chung cho thông tin, đơn vị, thành phần và ảnh; SKU hoa, trùng không phân biệt hoa thường kể cả đã xóa, slug sinh một lần; SKU/slug và mã vạch tuần tự hóa bằng khóa tư vấn (DB không có unique cho mã vạch); thuốc kê đơn không đặt nổi bật (chặn ở service); đơn vị thay cả danh sách theo pha, chặn xóa/đổi hệ số khi đã được tham chiếu hoặc đã có lô; xóa sản phẩm là xóa mềm, bị chặn khi còn tồn/giữ/biệt trữ (`409 SAN_PHAM_CON_TON_KHO`); gán danh mục khóa `FOR SHARE` (việc T2.1 để lại); ảnh nằm ở vùng công khai `GET /api/v1/tep/<khóa>` (`413 TEP_QUA_LON`), không có endpoint upload chung. Spec 06 mục 3.11, 4, 7; spec 08 mục 6; spec 09 mục 2.3 đã sửa theo.
  - **Backend:** `modules/san_pham/{san_pham,san_pham_don_vi,san_pham_anh,schemas_san_pham,router_san_pham}.py`, `modules/tep/router_cong_khai.py`, `core/luu_tru.py` (nhận dạng ảnh bằng magic bytes, ghi/đọc/xóa tệp, dọn tệp mồ côi theo `after_soft_rollback` và xóa tệp sau `after_commit`); 11 route dưới `/noi-bo/san-pham` đã vào registry phân quyền; `LUU_TRU_THU_MUC` (test ghi vào thư mục tạm của từng test); phụ thuộc mới `python-multipart`.
  - **Frontend:** `khu/quan-tri/san-pham/` (danh sách, trang thêm một form, trang sửa bốn tab; `lib/sanPham.ts`, `thongTin.ts`, `anh.ts` là hàm thuần có test cùng quy tắc với backend). Chi tiết không tự làm mới khi focus lại cửa sổ; form thông tin chỉ gửi trường đã đổi; gặp 409 thì tải bản mới, giữ chữ đang gõ.
  - **Rà soát nghiệp vụ (agent `nghiep-vu-reviewer`): không có mức Cao; 4 Trung bình và 6 Thấp đã sửa kèm test (đều đã tái hiện bằng chạy thật), 2 Thấp ghi lại.** M1: sau 409 ở tab Đơn vị/Thành phần form giữ danh sách cũ, lưu lại với `phien_ban` mới xóa im lặng đơn vị người kia vừa thêm: nay form được thay bằng danh sách mới của máy chủ (QĐ-17). M2: Starlette đọc cả multipart vào tệp tạm TRƯỚC xác thực (30 MB không token: 401 nhưng đã ghi 31 MB): middleware `GioiHanKichThuocThan` trả `413` từ `Content-Length` hoặc khi đếm đủ byte, test duyệt OpenAPI bắt route multipart mới thiếu quy tắc. M3: xóa sản phẩm đã đọc "không còn hàng" rồi commit trong khi nhập kho vào lô sẵn có (tồn 0) chen giữa làm tồn 100 mắc kẹt dưới sản phẩm đã xóa (mục "Việc phát sinh" ghi hướng sửa chưa đủ): nay xóa khóa mọi lô `FOR UPDATE` trước khi đếm và `ton_kho.kiem_tra_san_pham_chua_xoa` chặn mọi hàm tăng tồn (test đồng thời cả hai chiều). M4: mã vạch của sản phẩm đã xóa chặn tạo lại mãi mãi: sản phẩm đã xóa không giữ chỗ nữa. Thấp: symlink từ `cong_khai/` sang `rieng_tu/` được phục vụ (so với vùng công khai); tên đơn vị trùng tên tạm `~id` gây 500 (tên tạm chứa ký tự điều khiển); tạo sản phẩm đua với xóa thương hiệu/nhà sản xuất gây 500 (`FOR SHARE` khi kiểm tra tồn tại); đơn vị giá lẻ trong DB làm 500 cả chi tiết lẫn danh sách (schema đọc dùng `TienDoc`); tải lại lỗi sau 409 thay cả trang bằng cảnh báo; danh sách đơn vị/thành phần không giới hạn (nay tối đa 50); đọc tệp vừa bị xóa trả 500 và dọn tệp thất bại không để lại dấu vết (nay 404 và log cảnh báo); `ban_ghi_id` của nhật ký ảnh/đơn vị không nhất quán (chốt quy ước ở spec 06). Ghi lại, không sửa: ảnh đã xóa còn nằm ở bộ nhớ đệm trình duyệt một năm (`immutable`, đánh đổi có chủ ý), và polyglot `\xff\xd8\xff<html>` qua được nhận dạng magic bytes (phục vụ đúng `image/jpeg` kèm `nosniff` nên không thực thi được; kiểm cấu trúc ảnh bằng Pillow và bỏ EXIF là việc tùy chọn).
  - **Đã chạy thật:** backend 1583 test, frontend 544 test (cả `TZ=America/Los_Angeles`), lint, `tsc`, build. 47 đột biến vào service/schema/router/lưu trữ của AD04: 43 bị bắt ngay; 3 mutant sống do thiếu test (SKU chữ thường nhập thẳng vào DB, khóa tư vấn của mã vạch khi hai sản phẩm khác nhau đặt cùng mã, đổi đơn vị cơ sở của sản phẩm đã có lô) và 1 mutant thứ tự áp hệ số khi hoán đổi đơn vị cơ sở (test đầu cho đúng thứ tự gửi nên không phân biệt) đã bổ sung test và bị bắt; 1 tương đương (savepoint khi xóa đơn vị: lỗi khóa ngoại luôn kết thúc bằng `raise LoiNghiepVu` nên request rollback hết, giữ để giao dịch không bị hỏng nếu sau này bắt lỗi rồi chạy tiếp). Cơ chế "hệ số tạm" cho hoán đổi đơn vị cơ sở bị bỏ vì thừa với thứ tự áp. Chromium thật 26/26: tạo (form trống báo lỗi, SKU hoa, tên gộp khoảng trắng), sửa thông tin, xung đột phiên bản (DB đổi ngoài giao diện: báo, giữ chữ đang gõ, lưu lại không ghi đè trường người kia), đơn vị và giá, mã vạch trùng, thành phần, tải ảnh thật (tệp không phải ảnh bị từ chối; ảnh hiện qua `/api/v1/tep`, file nằm trong vùng công khai), đặt ảnh chính, đổi thứ tự, xóa ảnh (file bị xóa), danh sách, xóa sản phẩm, mở sản phẩm đã xóa.

### [x] T2.3 · Nội dung chuyên môn, tương tác hoạt chất
- **Chức năng:** DS10 (Biên soạn, duyệt nội dung chuyên môn)
- **Phụ thuộc:** T2.2
- **Bảng:** `thong_tin_chuyen_mon`, `tuong_tac_hoat_chat`, `bai_viet`
- **Tiêu chí chấp nhận:**
  - [x] Mỗi lần sửa tạo phiên bản mới `thong_tin_chuyen_mon` (trạng thái `nhap`); duyệt → `da_duyet`, ghi `duoc_si_duyet_id`, `ngay_duyet`; phiên bản hiển thị = bản đã duyệt mới nhất.
  - [x] CRUD `tuong_tac_hoat_chat` (lưu cặp theo thứ tự id tăng dần), hàm `kiem_tra_tuong_tac(ds_san_pham_id)` và `kiem_tra_di_ung(khach_hang_id, ds_san_pham_id)` trả danh sách cảnh báo có mức độ (dùng lại ở DS04, DS05, DS08, AI).
  - [x] Duyệt bài viết sức khỏe (khi T2.6 xong thì nối vào). *Phần dược sĩ xong (danh sách chờ duyệt, xem, duyệt, nhật ký); soạn bài, đăng và giao diện duyệt nối vào ở T2.6.*
- **Giao diện:**
  - [x] Màn biên soạn chuyên môn có so sánh phiên bản, màn tương tác hoạt chất.
- **Ghi chú triển khai:**
  - **Quyết định ở QĐ-18** (cần người xác nhận mục "tự duyệt"): mỗi sản phẩm tối đa MỘT bản `da_duyet` (bản hiển thị), duyệt bản mới đưa bản cũ sang `luu_tru`, KHÔNG duyệt lùi (bản nháp cũ hơn bản đang hiển thị bị từ chối); `phien_ban_co_so` bắt buộc trong body để hai dược sĩ soạn cùng lúc không bỏ qua bản của nhau; chỉ dược sĩ ghi ở hai lớp (`yeu_cau_quyen` và `dam_bao_la_duoc_si`); **người soạn có thể tự duyệt bản của mình** (spec 03 mục 7 không nhắc; một dược sĩ duy nhất thì không đăng được gì nếu cấm); `kiem_tra_tuong_tac` chỉ báo hai hoạt chất ở hai sản phẩm KHÁC nhau; `kiem_tra_di_ung` chỉ trả cảnh báo mức `chong_chi_dinh`, không `ghi_chu`, không log. Spec 03 mục 7, 06 mục 3.12, 09 mục 2.2 đã sửa theo.
  - **Backend:** `modules/chuyen_mon/` (`noi_dung.py`, `tuong_tac.py`, `canh_bao.py`, `bai_viet_duyet.py`, schemas và ba router; 13 route mới đã vào registry phân quyền), `core/phan_quyen.dam_bao_la_duoc_si`. `noi_dung.noi_dung_da_duyet(db, san_pham_id)` là nơi duy nhất khách và AI đọc nội dung chuyên môn (T2.4, T7.x).
  - **Frontend:** `khu/nhan-vien/chuyen-mon/` (danh sách lọc theo tình trạng, trang soạn ba tab Soạn bản mới / Phiên bản / So sánh, bảng và hộp thoại tương tác; `noiDung.ts`, `tuongTac.ts` là hàm thuần có test cùng quy tắc với backend); `ChonDuLieuChung` chuyển lên `components/` vì dùng ở cả hai khu; nhãn `noi_dung` và `muc_do_tuong_tac` ở `lib/trangThai.ts` (test đối chiếu enum API).
  - **Đã chạy thật:** backend 1705 test, frontend 599 test (cả `TZ=America/Los_Angeles`), lint, `tsc`, build; Chromium thật 24/24: soạn bản 1, duyệt, bản 2 điền sẵn từ bản đang hiển thị, xung đột phiên bản thật (DB chèn bản 3 giữa chừng: báo, giữ chữ đang gõ, lưu lại thành bản 4 và bản của người kia còn nguyên), so sánh hai bản, duyệt bản 4 đưa bản 1 sang lưu trữ, duyệt bản 2 cũ hơn bị từ chối, bỏ bản nháp; tương tác: thêm cặp (thứ tự id tăng dần), thêm lại đảo thứ tự bị 409, tìm, sửa gặp xung đột, xóa.
  - **Chưa làm:** dữ liệu mẫu chuyên môn và tương tác cho `seed --mau` (làm ở T2.4 cùng trang chi tiết sản phẩm); đồng bộ nội dung đã duyệt vào kho tri thức AI (T7.x); giao diện Admin xem nội dung chuyên môn (AD16, T6.7); giao diện duyệt bài viết (đã làm ở T2.6).
  - **Rà soát nghiệp vụ (agent `nghiep-vu-reviewer`): không có mức Cao; 2 Trung bình đã sửa kèm test, 1 Thấp sửa, 2 Thấp ghi cho task sau, 1 chuyển lên chốt chung.** M1: `noi_dung_da_duyet` không lọc sản phẩm đã xóa mềm nên T2.4/T7.x gọi theo id vẫn nhận nội dung thuốc đã gỡ (đã tái hiện): nay join `san_pham` với `deleted_at IS NULL`. M2: duyệt một bản trống hoàn toàn xóa sạch chống chỉ định đang hiển thị (đã tái hiện): nay bản không có mục nào là `400` (bỏ riêng một mục vẫn được). L1: dữ liệu nhập tay có hai bản `da_duyet` làm trang khách và nút duyệt 500: nay đọc lấy bản mới nhất, duyệt gỡ hết bản cũ. L3: thân JSON không bị giới hạn trước xác thực (lỗi có sẵn của mọi route ghi): thêm trần chung 2 MiB cho `POST/PUT/PATCH/DELETE` dưới `/api/v1` trong `GioiHanKichThuocThan`, mã lỗi mới `413 THAN_QUA_LON` (spec 06 mục 4). Backend 1711 test xanh.

### [x] T2.4 · Trang chủ, danh mục, lọc, chi tiết sản phẩm
- **Chức năng:** KVL01 (Xem trang chủ, danh mục), KVL02 (Lọc, sắp xếp sản phẩm), KVL03 (Xem chi tiết sản phẩm)
- **Phụ thuộc:** T2.3
- **Bảng:** `banner`, `danh_muc`, `san_pham`, `anh_san_pham`, `don_vi_quy_doi`, `thuong_hieu`, `thong_tin_chuyen_mon`, `thanh_phan`, `hoat_chat`, `nha_san_xuat`, `lo_thuoc`, `danh_gia`, `hoi_dap`, `lich_su_xem`
- **Tiêu chí chấp nhận:**
  - [x] API công khai chỉ trả sản phẩm `dang_kinh_doanh`, chưa xóa; giá theo từng đơn vị bán online; tình trạng còn hàng = tồn khả dụng > 0 (spec 04 mục 3).
  - [x] Lọc: danh mục (gồm danh mục con), loại, thương hiệu, khoảng giá, đối tượng; sắp xếp: mới, giá, bán chạy (đếm `ct_don_hang` 30 ngày).
  - [x] Chi tiết: nội dung chuyên môn bản đã duyệt, thành phần, ảnh, đánh giá (khi có). Thuốc kê đơn trả cờ `can_tu_van = true` và không có hành động "thêm vào giỏ"; TPCN kèm câu "không phải là thuốc".
  - [x] Ghi `lich_su_xem` (khách hoặc mã phiên).
- **Giao diện:**
  - [x] Trang chủ (banner, nổi bật, bán chạy), trang danh mục có bộ lọc, trang chi tiết sản phẩm.
- **Ghi chú triển khai:**
  - **Quyết định ở QĐ-19:** "hiển thị với khách" = chưa xóa + đang kinh doanh + danh mục và mọi tổ tiên đang hiện (áp cả cho chi tiết: 404); giá thẻ = đơn vị bán online mặc định; còn hàng = tồn khả dụng > 0 ở lô `dang_ban` còn hạn (chi tiết: theo từng đơn vị, `>= he_so`); thuốc kê đơn có trong danh sách và chi tiết nhưng bị loại khỏi nổi bật, bán chạy và sản phẩm tương tự ngay ở truy vấn; bán chạy = số dòng `ct_don_hang` đơn không hủy 30 ngày; lịch sử xem theo token hoặc `X-Ma-Phien`, dedupe 30 phút; bộ lọc có route riêng `GET /bo-loc-san-pham`.
  - **Backend:** `modules/cua_hang/` (`hien_thi.py` điều kiện dùng chung, `danh_muc.py`, `danh_sach.py`, `chi_tiet.py`, `schemas.py`, `router.py`; 7 route công khai, spec 06 mục 3.13). Seed mẫu thêm 4 banner (ảnh SVG ở `frontend/public/banner/`) và nội dung chuyên môn đã duyệt cho 7 sản phẩm (có một thuốc kê đơn), nạp lại an toàn và không đè phiên bản dược sĩ đã soạn.
  - **Frontend:** `khu/cua-hang/` (`TrangChu`, `TrangDanhMuc` + `BoLocSanPham`, `TrangChiTietSanPham`, `TheSanPham`, `MenuDanhMuc`, `cuaHang.ts` logic thuần có test bảng ca), `lib/lienKet.ts` (chỉ `/...` hoặc `http(s)://host` vào href/src), `lib/maPhien.ts`. Nút "Thêm vào giỏ" của sản phẩm thường bị khóa tới T4.1; thuốc kê đơn không bao giờ có nút này.
  - **Đã chạy thật:** backend 1763 test, frontend 686 test (cả `TZ=America/Los_Angeles` cho `lib/` và `khu/cua-hang/`), lint, `tsc`, build; Chromium thật 41/41 trên dữ liệu mẫu (banner tải được, nổi bật không có kê đơn, lọc loại/thương hiệu/giá/sắp xếp trên URL, đổi đơn vị đổi giá, kê đơn không có nút giỏ và có nút tư vấn, TPCN có dòng "không phải là thuốc", ẩn danh mục cha làm sản phẩm con biến mất và bật lại thì hiện lại, lịch sử xem theo mã phiên và theo khách đăng nhập, không tràn ngang ở 360px, không lỗi console). Phát hiện khi chạy thật và đã sửa: trang chi tiết tải khi khách chưa lấy lại xong phiên thì ghi lịch sử xem thành vãng lai (nay chờ `daKhoiPhuc`).
  - **Chưa làm:** hỏi đáp (KTV15) và tạo đánh giá (KTV10, T5.x); giỏ hàng (T4.1); số lượng tối đa mỗi đơn hiển thị ở chi tiết (T4.1 cùng giỏ).
  - **Rà soát nghiệp vụ (agent `nghiep-vu-reviewer`): không có mức Cao; 2 Trung bình và 3 Thấp đã sửa kèm test, 2 Thấp chấp nhận/ghi nhận.** M1: `lich_su_xem` phình khi client quay `X-Ma-Phien`: giới hạn 120 lượt ghi/10 phút/IP (vượt thì vẫn trả sản phẩm, không ghi); index `(ma_phien, san_pham_id, created_at)` ghi vào "Việc phát sinh" vì cần `/doi-schema`. M2: "bán chạy" dùng truy vấn con tương quan (đo ở 20.000 sản phẩm × 300.000 dòng: trang chủ 2,4 s, sắp xếp 5,0 s): nay gộp một lần rồi nối (`ban_chay_30_ngay`). L2: tên người đánh giá một từ hoặc có chữ số/"@" không còn lộ SĐT, email. L3: slug sai mẫu (400) hiện trang 404 thay vì lỗi thử lại. L4: `?trang=` vượt số trang hiện nút "Về trang 1". L1 (kiểm tra rồi ghi, hai request đồng thời có thể ghi hai dòng) và L5 (`con_hang` không xét đơn vị online) ghi vào QĐ-19 là chấp nhận. Backend 1767 test, frontend 689 test xanh.


### [x] T2.5 · Tìm kiếm từ khóa
- **Chức năng:** KVL04 (Tìm kiếm thông minh)
- **Phụ thuộc:** T2.4
- **Bảng:** `san_pham`, `hoat_chat`, `thanh_phan`, `tai_lieu_tri_thuc`, `lich_su_tim_kiem`
- **Tiêu chí chấp nhận:**
  - [x] Tìm không dấu, sai chính tả, theo tiền tố bằng `word_similarity` (`f_unaccent(lower(:q)) <% f_unaccent(lower(ten))`, spec 02 mục 4.1) trên tên sản phẩm, hoạt chất, tên khác; gợi ý khi gõ (≤ 8 kết quả, < 200 ms trên dữ liệu mẫu). Test: "para" ra Paracetamol, "paracetmol" (gõ sai) ra Paracetamol, "bo phe" ra "Bổ phế".
  - [x] Xếp hạng: độ khớp, còn hàng trước, bán chạy; thuốc kê đơn có nhãn "Cần tư vấn".
  - [x] Ghi `lich_su_tim_kiem` (`che_do = tu_khoa`). Phần tìm ngữ nghĩa nối vào ở T7.2.
- **Giao diện:**
  - [x] Ô tìm kiếm có gợi ý, trang kết quả.
- **Ghi chú triển khai:**
  - **Quyết định ở QĐ-20:** khớp bằng `word_similarity` trên tên sản phẩm, hoạt chất và tên khác (kiểm `EXPLAIN ANALYZE` trên 20.000 sản phẩm: index GIN được dùng, 2,6 ms); xếp hạng độ khớp làm tròn 0,1 → còn hàng → bán chạy; từ khóa dưới 2 ký tự trả rỗng; lịch sử tìm kiếm ghi ở trang 1, dedupe 30 phút, giới hạn 120 lượt/10 phút/IP; chưa tìm theo triệu chứng/công dụng (ngữ nghĩa, T7.2).
  - **Backend:** `modules/cua_hang/tim_kiem.py`, `GET /tim-kiem` và `GET /tim-kiem/goi-y` (spec 06 mục 3.13). **Frontend:** `OTimKiem` (AutoComplete ở header, trễ 250 ms), `TrangTimKiem`, `timKiem.ts`.
  - **Đã chạy thật:** backend 1805 test, frontend 706 test, lint, `tsc`, build; Chromium thật 17/17 ("para", "paracetmol" gõ sai, "bo phe" không dấu, "acetaminophen" là tên khác của hoạt chất, kê đơn kèm "Cần tư vấn", không kết quả, gợi ý ≤ 8 kèm nhãn Hoạt chất, chọn gợi ý mở chi tiết, API gợi ý 35 ms, `lich_su_tim_kiem` ghi cả `so_ket_qua = 0`, 360px không tràn ngang, không lỗi console).
  - **Chưa làm:** tìm theo triệu chứng/công dụng và `tai_lieu_tri_thuc` (T7.2); cập nhật bán chạy/còn hàng theo thời gian thực không có cache nên mỗi lượt gõ là một truy vấn (đo ~30 ms).
  - **Rà soát nghiệp vụ (agent `nghiep-vu-reviewer`): không có mức Cao; 2 Trung bình và 4 Thấp đã sửa kèm test, 2 Thấp ghi nhận.** M1: điều kiện `OR` giữa khớp tên và `IN (subquery)` hoạt chất làm PostgreSQL quét tuần tự (đo 20.000 sản phẩm: 330 ms mỗi lần gõ) và ghi chú "index được dùng" chỉ đúng khi tắt seqscan: nay gộp bằng UNION (2,6 ms, đã kiểm `EXPLAIN` mặc định), gợi ý bỏ câu đếm, `GET /tim-kiem/goi-y` giới hạn 240 lượt/phút/IP. M2: từ khóa nhiều từ có từ cuối đang gõ dở ("para 5", "vit c") mất kết quả: nay khớp theo từng từ. L1: khách vãng lai không mã phiên bị dedupe nhầm với khách đăng nhập. L3: chọn gợi ý hoạt chất để lại "X (hoạt chất)" trong ô (giá trị nội bộ nay là khóa, ô giữ tên thật; Enter khi đang tô sáng một gợi ý hủy lượt tìm đầy đủ, đã kiểm bằng Chromium thật). L4: danh sách gợi ý nháy trống mỗi lần đổi từ khóa. L5: mã hóa slug trong đường dẫn gợi ý. L6 (ranh giới nhóm làm tròn) chấp nhận, ghi QĐ-20. L2 (mã phiên do client chọn, IP sau proxy, job dọn, xóa tài khoản) ghi "Việc phát sinh".


### [x] T2.6 · Banner, bài viết, chính sách, FAQ
- **Chức năng:** AD07 (Quản lý banner, bài viết, chính sách, FAQ), KVL11 (Xem bài viết sức khỏe, chính sách, FAQ)
- **Phụ thuộc:** T2.3
- **Bảng:** `banner`, `bai_viet`
- **Tiêu chí chấp nhận:**
  - [x] CRUD banner theo vị trí, thời gian hiển thị. CRUD `bai_viet` theo `loai`; bài `bai_viet` cần dược sĩ duyệt mới công khai; chính sách/FAQ Admin đăng trực tiếp.
  - [x] API công khai danh sách/chi tiết theo slug; cờ `dua_vao_ai`.
- **Giao diện:**
  - [x] Quản trị banner/bài viết (editor Markdown), trang bài viết, chính sách, FAQ phía khách.
- **Ghi chú triển khai:**
  - **Quyết định ở QĐ-21:** chỉ Admin soạn/đăng (`cms.manage` + `dam_bao_la_admin`), dược sĩ duyệt bài sức khỏe qua `content.approve`; sửa bài sức khỏe đã duyệt (tiêu đề, nội dung, ảnh bìa) đưa bài về chờ duyệt và ẩn khỏi website; `loai` bất biến (không vòng qua dược sĩ); chính sách và FAQ đăng thẳng; gỡ bài là `luu_tru` (giữ slug), đăng lại đi lại đúng quy trình; banner xóa hẳn; Markdown lưu nguyên văn và làm sạch khi hiển thị (react-markdown, không HTML thô); ảnh tải lên trước khi có bản ghi nên có thể mồ côi.
  - **Việc T2.3 để lại đã làm:** `POST /noi-bo/bai-viet-cho-duyet/{id}/duyet` nhận `{phien_ban}` (dấu vân tay nội dung đã đọc), lệch là `409` (thay đổi hợp đồng của route T2.3).
  - **Backend:** `modules/noi_dung_web/` (`banner.py`, `bai_viet.py`, `anh.py`, `cong_khai.py`, hai router; spec 06 mục 3.14); 12 route nội bộ đã vào registry phân quyền, 2 route công khai; quy tắc thân request cho hai route tải ảnh. Seed mẫu thêm 8 bài (3 bài sức khỏe, 2 chính sách, 3 FAQ).
  - **Frontend:** `/quan-tri/noi-dung` (Banner, Bài viết, Chính sách, Hỏi đáp; trình soạn Markdown có xem trước), `/nhan-vien/bai-viet-cho-duyet`, `/bai-viet`, `/bai-viet/:slug`, `/chinh-sach/:slug`, `/hoi-dap`, chân trang động; `components/NoiDungMarkdown`, `lib/anhTep.ts`. Thêm phụ thuộc `react-markdown@10.1.0`.
  - **Đã chạy thật:** backend 1924 test, frontend 785 test (lint, `tsc`, build xanh); Chromium 30/30 (danh sách và đọc bài mẫu, FAQ, chính sách ở chân trang; thêm banner có tải ảnh, chặn liên kết `javascript:`, tắt và xóa; soạn bài sức khỏe → chờ duyệt → khách 404 → Admin sửa giữa chừng khiến duyệt 409 → dược sĩ đọc lại rồi duyệt → khách đọc được; sửa bài đã đăng thì biến mất tới khi duyệt lại; nội dung `<script>`, `onerror`, `javascript:` hiện thành chữ, không chạy; chính sách và FAQ đăng thẳng rồi gỡ; không tràn ngang ở 360px; không lỗi console).
  - **Rà soát nghiệp vụ (agent `nghiep-vu-reviewer`): không có mức Cao; 3 Trung bình và 4 Thấp đã sửa kèm test (`tests/noi_dung_web/test_nd_ra_soat.py`, đã tái hiện lỗi trước khi sửa).** M1: regex `tom_tat` bậc hai trên toàn văn (100.000 ký tự `[` chặn tiến trình 27 giây, mà chân trang gọi danh sách ở mọi trang) → cắt 1.500 ký tự đầu ngay ở SQL (`left`), thêm chặn trên cho các nhóm lặp; M2: sửa nội dung cùng độ dài trả 200 nhưng không lưu → nhật ký thêm dấu vân tay nội dung và luôn `flush` trước khi nạp lại; M3: thời điểm banner năm 0001 / 9999 làm danh sách Admin 500 vĩnh viễn → giới hạn năm 2000–2100; L1: NUL, surrogate lẻ, ký tự vô hình trong bài viết → `400` (dùng chung `chuan_hoa_van_ban`); L2: `phien_ban` banner lệch theo múi giờ client → đổi về UTC khi nhận; L3: danh sách công khai và Admin kéo toàn văn → `left`/`defer`, `kem_noi_dung` tối đa 50 dòng (trang Hỏi đáp đổi từ 100 xuống 50); L4: "Gỡ"/"Đăng lại" ngầm lấy `phien_ban` mới nhất → chỉ gửi khi bài vẫn như dòng đang xem.
  - **Chưa làm:** đồng bộ `dua_vao_ai` vào kho tri thức (T7.x); dọn ảnh mồ côi (T3.2).


## P3 · Kho

_Nhập kho theo lô, thẻ kho, cảnh báo, kiểm kê, hủy, xuất trả, báo cáo nhập - xuất - tồn._

### [x] T3.1 · Nhà cung cấp, phiếu nhập và dịch vụ tồn kho
- **Chức năng:** KHO01 (Quản lý nhà cung cấp), KHO02 (Lập phiếu nhập kho)
- **Phụ thuộc:** T2.2
- **Bảng:** `nha_cung_cap`, `phieu_nhap`, `ct_phieu_nhap`, `lo_thuoc`, `bien_dong_kho`
- **Tiêu chí chấp nhận:**
  - [x] `kho/ton_kho.py` là nơi DUY NHẤT đổi tồn: `nhap_kho`, `giu_hang`, `nha_giu`, `xuat_theo_phan_bo`, `hoan_nhap`, `vao_biet_tru`, `tru_ton` (hủy/xuất trả/điều chỉnh); khóa lô `FOR UPDATE`, ghi `bien_dong_kho` (spec 04 mục 3).
  - [x] CRUD nhà cung cấp (ngừng hợp tác = xóa mềm).
  - [x] Lập phiếu nhập: quy đổi về đơn vị cơ sở; tạo lô mới hoặc cộng vào lô cũ (tính lại giá nhập bình quân gia quyền); cảnh báo HSD < `han_su_dung_toi_thieu_nhap_ngay`, chặn số lô trùng khác HSD; phiếu đã lưu không sửa/xóa.
  - [x] Test bất biến tồn kho (spec 10 mục 4) cho nhập kho.
- **Giao diện:**
  - [x] Danh sách nhà cung cấp; form phiếu nhập nhiều dòng có quét mã vạch.
- **Ghi chú triển khai:**
  - Quyết định ở QĐ-22 (cùng số lô khác HSD bị chặn, cảnh báo HSD ngắn cần xác nhận, giá vốn làm tròn đồng, `giu_hang_nhieu`). Thêm hàm `giu_hang_nhieu` và `dieu_chinh` ngoài danh sách tiêu chí.
  - Backend: `modules/kho/` (`ton_kho`, `nha_cung_cap`, `phieu_nhap`, `lo`), 9 route nội bộ trong registry, spec 06 mục 3.15. `tests/bat_bien/kiem_tra.py` (bất biến 1 đến 3) tự chạy cuối mọi test `tests/kho` (fixture `db` ghi đè); test tranh chấp giữ hàng (lô còn 1, khóa ngược thứ tự).
  - Frontend: `/nhan-vien/nha-cung-cap`, `/phieu-nhap`, `/phieu-nhap/tao` (quét mã vạch bằng Enter ở ô tìm; hạn ngắn hỏi xác nhận).
  - Chưa làm: gửi phiếu nhập trùng do bấm hai lần (chưa có `Idempotency-Key`, nút lưu có trạng thái loading); rà soát nghiệp vụ gộp sau T3.5.


### [x] T3.2 · Tra cứu tồn, cảnh báo và job lô
- **Chức năng:** KHO05 (Tra cứu tồn kho), KHO06 (Xem cảnh báo), HT01 (Cập nhật trạng thái lô hằng ngày), HT02 (Cảnh báo tồn thấp, cận hạn)
- **Phụ thuộc:** T3.1
- **Bảng:** `lo_thuoc`, `san_pham`, `thong_bao`, `phan_bo_lo`
- **Tiêu chí chấp nhận:**
  - [x] Worker `uv run python -m app.jobs` (APScheduler, mỗi job giữ `pg_try_advisory_lock` để không chạy chồng).
  - [x] HT01 hằng ngày 00:05 (giờ VN): lô `dang_ban` có HSD < hôm nay + `nguong_can_han_ngay` → `can_han`; HSD ≤ hôm nay → `het_han` (gỡ khỏi đơn chưa xuất, phân bổ lại FEFO khi có module bán hàng).
  - [x] HT02: gửi `thong_bao` cho nhân viên kho khi tồn khả dụng < `ton_toi_thieu`, có lô cận hạn/hết hạn (không gửi trùng trong ngày).
  - [x] Tra cứu tồn theo sản phẩm và theo lô (tồn, giữ, biệt trữ, trạng thái). Dược sĩ chỉ thấy tồn khả dụng, không thấy giá nhập.
- **Giao diện:**
  - [x] Màn tồn kho (bảng sản phẩm mở rộng ra lô), màn cảnh báo.
- **Ghi chú triển khai:**
  - Spec 06 mục 3.16. Worker `app/jobs/` (`__main__.py` lịch giờ VN, `chay.py` khóa `pg_try_advisory_lock` trên kết nối riêng, `cong_viec.py`): `ht01_lo` 00:05, `ht02_canh_bao_kho` 07:00 (sau HT01), `don_lich_su` 03:30 (xóa `lich_su_xem`, `lich_su_tim_kiem` quá 90 ngày; làm xong mục phát sinh T2.4/T2.5).
  - HT01 chuyển cả hai chiều giữa `dang_ban` và `can_han` theo ngưỡng hiện hành, không đụng lô `khoa`/`thu_hoi`; lô hết hạn: nhả phân bổ `dang_giu` rồi giữ lại FEFO (đơn tại quầy được dùng lô cận hạn), đơn thiếu hàng thì báo nhân viên kho kèm mã đơn. Chưa có đơn thật nên test dựng bằng `tao_don` + `giu_hang`.
  - Dược sĩ xem tồn nhưng `gia_nhap`, tồn, đang giữ, biệt trữ là `null` (quyết định theo quyền `stock.import`, không theo tên vai trò).
  - Giao diện: `/nhan-vien/ton-kho` (mở rộng ra lô), `/nhan-vien/canh-bao`.
  - Chưa làm: dọn ảnh mồ côi của banner, bài viết (ghi lại ở "Việc phát sinh"); worker chưa có gói chạy (T8.3).


### [x] T3.3 · Kiểm kê và phiếu điều chỉnh
- **Chức năng:** KHO07 (Kiểm kê), KHO08 (Lập phiếu điều chỉnh tồn)
- **Phụ thuộc:** T3.1
- **Bảng:** `phieu_kiem_ke`, `ct_kiem_ke`, `phieu_dieu_chinh`, `ct_phieu_dieu_chinh`
- **Tiêu chí chấp nhận:**
  - [x] Phiếu kiểm kê (toàn kho hoặc theo danh mục) chụp tồn sổ sách; nhập số thực tế; chốt → tính chênh lệch.
  - [x] Lập phiếu điều chỉnh từ kết quả kiểm kê (chỉ các dòng lệch), trạng thái chờ duyệt; tồn chưa đổi.
- **Giao diện:**
  - [x] Màn kiểm kê (nhập nhanh theo lô), màn phiếu điều chỉnh.
- **Ghi chú triển khai:**
  - Spec 06 mục 3.17. Kiểm kê chụp `so_luong_ton` khu bán của lô còn tồn (khóa lô khi chụp); chênh lệch tính theo số sổ sách lúc chụp nên điều chỉnh là thay đổi TƯƠNG ĐỐI, vẫn đúng nếu có bán trong lúc kiểm. Phiếu điều chỉnh đòi người lập có `stock_adjust.create` (chỉ kho); lập từ kiểm kê (chỉ dòng lệch, mỗi phiếu kiểm kê một phiếu điều chỉnh còn hiệu lực) hoặc lập tay cho các sai sót khác (vd nhập sai số lượng, vì phiếu nhập không sửa được).
  - Thêm ngoài tiêu chí: xóa phiếu kiểm kê đang kiểm, lập điều chỉnh lập tay.
  - Giao diện: `/nhan-vien/kiem-ke` (lập phiếu, nhập nhanh theo lô, lọc dòng lệch, chốt, lập điều chỉnh), `/nhan-vien/dieu-chinh` (danh sách, chi tiết). Duyệt ở T3.4.
  - Chưa làm: ghi nhận hàng tìm thấy ở lô đang tồn 0 (kiểm kê chỉ gồm lô còn tồn; dùng điều chỉnh lập tay).


### [x] T3.4 · Phiếu hủy, phiếu xuất trả và duyệt
- **Chức năng:** KHO09 (Lập phiếu hủy hàng), KHO11 (Xuất trả nhà cung cấp), AD12 (Duyệt phiếu hủy, điều chỉnh tồn, xuất trả NCC)
- **Phụ thuộc:** T3.3
- **Bảng:** `phieu_huy`, `ct_phieu_huy`, `phieu_xuat_tra`, `ct_phieu_xuat_tra`, `phieu_dieu_chinh`, `lo_thuoc`, `bien_dong_kho`
- **Tiêu chí chấp nhận:**
  - [x] Lập phiếu hủy và phiếu xuất trả NCC (chọn lô, khu `kho_ban`/`biet_tru`, số lượng ≤ tồn khu đó); trạng thái chờ duyệt.
  - [x] Admin duyệt/từ chối phiếu điều chỉnh, hủy, xuất trả: người duyệt ≠ người lập (`ma_loi = "TU_DUYET_KHONG_DUOC"`); chỉ khi duyệt mới gọi `ton_kho` và ghi thẻ kho; từ chối bắt buộc lý do.
  - [x] Test: tự duyệt bị chặn; duyệt làm tồn đúng; từ chối không đổi tồn.
- **Giao diện:**
  - [x] Danh sách phiếu chờ duyệt cho Admin; form phiếu hủy/xuất trả.
- **Ghi chú triển khai:**
  - Spec 06 mục 3.18. Lập: `/noi-bo/phieu-huy` (`disposal.create`), `/noi-bo/xuat-tra` (`supplier_return.create`), dòng `{lo_id, tu_khu, so_luong}` kiểm `so_luong` ≤ tồn khu lúc lập (khu bán trừ hàng đang giữ). Duyệt: `/noi-bo/duyet-phieu` (`stock_doc.approve`), danh sách gộp ba loại, `POST /{loai}/{id}/duyet|tu-choi` (`modules/kho/duyet_phieu.py`, loại `dieu-chinh|huy|xuat-tra`).
  - Duyệt khóa phiếu `FOR UPDATE`, kiểm tra người duyệt khác người lập rồi trạng thái `cho_duyet`, khóa mọi lô theo id tăng dần rồi mới gọi `ton_kho.dieu_chinh`/`tru_ton` (số lượng kiểm tra lại, thiếu thì `HET_HANG` và rollback cả phiếu). `TU_DUYET_KHONG_DUOC` áp cả cho TỪ CHỐI (CHECK CSDL `nguoi_duyet_id <> nguoi_lap_id` áp cả hai). Người lập nhận thông báo `phieu_kho_da_duyet`/`phieu_kho_tu_choi`.
  - Giao diện: `/nhan-vien/phieu-huy`, `/nhan-vien/xuat-tra` (danh sách, chi tiết, form lập), `/quan-tri/duyet-phieu` (danh sách chờ duyệt gộp ba loại, duyệt/từ chối có lý do).
  - Chưa làm: `bien_ban_url` của phiếu hủy (chưa có route tải tệp), `lenh_thu_hoi_id` và ghi nhận NCC đã nhận hàng `da_xac_nhan` (T6.6). Hai nhánh lỗi duyệt đồng thời cùng một phiếu dựa vào khóa dòng phiếu, chưa có test tranh chấp nhiều session riêng.

- **Ghi chú chuẩn bị (từ T3.1–T3.3, đọc trước khi làm):**
  - Kiến trúc kho hiện có (`backend/app/modules/kho/`):
    - `ton_kho.py`: mọi hàm đổi tồn (`tru_ton`, `dieu_chinh`, `giu_hang_nhieu`...) khóa lô `FOR UPDATE` theo id tăng dần, ghi `bien_dong_kho` cùng transaction. Chứng từ truyền vào bằng `ChungTu('phieu_dieu_chinh'|'phieu_huy'|'phieu_xuat_tra', id, nguoi_thuc_hien_id)`.
    - `dieu_chinh.py`/`kiem_ke.py`: phiếu điều chỉnh đã lập ở trạng thái chờ duyệt, tồn chưa đổi (T3.3). Chênh lệch là thay đổi tương đối so với sổ sách lúc chụp. Mã phiếu qua `core/ma_chung_tu.ma_phieu(db, 'phieu_huy'|'phieu_xuat_tra'|...)`.
    - Router nằm ở `router_*.py`; mọi route `/noi-bo/*` dùng `Depends(yeu_cau_quyen(ma, muc))` và phải thêm vào `tests/phan_quyen/registry.py`.
    - `tests/kho/conftest.py` chạy `kiem_tra_bat_bien(db)` sau mỗi test (bất biến 1–3); test cố ý phá bất biến gắn `@pytest.mark.khong_kiem_bat_bien`.
  - Việc cần làm ở T3.4:
    1. Viết spec 06 mục 3.18 trước, thêm mã lỗi `TU_DUYET_KHONG_DUOC` vào cả `core/loi.py::MA_LOI` và bảng lỗi spec 06 mục 4.
    2. Test trước: người duyệt = người lập → `TU_DUYET_KHONG_DUOC`; duyệt đúng thì tồn/thẻ kho đổi đúng; từ chối bắt buộc lý do và không đổi tồn.
    3. Duyệt phải khóa phiếu, kiểm tra còn ở trạng thái chờ duyệt (tránh duyệt hai lần), rồi mới gọi `ton_kho`. Số lượng được kiểm tra lại tại thời điểm duyệt vì tồn có thể đã đổi sau khi lập.
    4. Phiếu hủy/xuất trả chọn khu `kho_ban`/`biet_tru`; chỉ Admin có quyền duyệt (AD12), kho lập (KHO09/KHO11). Admin không đọc dữ liệu sức khỏe nhưng phiếu kho không dính phần này.
    5. Giao diện: danh sách chờ duyệt cho Admin (gộp 3 loại phiếu) + form phiếu hủy/xuất trả; đăng ký route ở `src/router.tsx` (`TRANG_NHAN_VIEN_THAT`) và `menu.ts`.
  - Quy ước làm tiết kiệm token: chỉ chạy test phần bị ảnh hưởng khi đang làm, chạy full một lần cuối task; `nghiep-vu-reviewer` chạy gộp một lần sau T3.5 (QĐ-22). `LoiNghiepVu` truyền `chi_tiet=` bằng keyword. Mỗi khi đổi backend phải restart uvicorn trước `npm run gen:api`.

### [x] T3.5 · Báo cáo nhập - xuất - tồn
- **Chức năng:** KHO13 (Báo cáo nhập, xuất, tồn)
- **Phụ thuộc:** T3.4
- **Bảng:** `bien_dong_kho`, `lo_thuoc`
- **Tiêu chí chấp nhận:**
  - [x] Theo kỳ (từ ngày - đến ngày), theo sản phẩm hoặc lô: tồn đầu, nhập, xuất (theo loại biến động), tồn cuối, tính hoàn toàn từ `bien_dong_kho`.
  - [x] Test: tồn cuối báo cáo = `so_luong_ton` hiện tại khi đến ngày = hôm nay.
  - [x] Xuất file Excel (`openpyxl`).
- **Giao diện:**
  - [x] Màn báo cáo có bộ lọc và nút xuất Excel.
- **Ghi chú triển khai:**
  - Spec 06 mục 3.19. Cột theo từng loại biến động là tổng có dấu (nhập dương, xuất âm); tồn cuối = tồn đầu + tổng; mặc định khu `kho_ban` (khớp `so_luong_ton`), chọn được `biet_tru`. Nhóm theo sản phẩm hoặc theo lô.
  - Excel: `openpyxl`, tối đa 20.000 dòng, chặn chuỗi công thức. Giao diện `/nhan-vien/bao-cao-nxt` (bộ lọc kỳ, nhóm, khu, tìm kiếm, nút xuất Excel).
  - Chưa làm: báo cáo theo giá trị tiền (chỉ số lượng, đơn vị cơ sở).


## P4 · Bán hàng online

_Giỏ hàng, máy trạng thái, đặt hàng giữ hàng FEFO, thanh toán, xử lý và giao đơn._

### [x] T4.1 · Giỏ hàng và sổ địa chỉ
- **Chức năng:** KVL07 (Quản lý giỏ hàng), KTV01 (Quản lý hồ sơ, sổ địa chỉ)
- **Phụ thuộc:** T2.4
- **Bảng:** `gio_hang`, `ct_gio_hang`, `san_pham`, `don_vi_quy_doi`, `luat_mua_kem`, `khach_hang`, `dia_chi`
- **Tiêu chí chấp nhận:**
  - [x] Giỏ của khách vãng lai ở localStorage; `PUT /api/v1/toi/gio-hang/gop` gộp khi đăng nhập (cộng dồn, cắt theo giới hạn).
  - [x] Từ chối thuốc kê đơn (`ma_loi = "THUOC_KE_DON_KHONG_VAO_GIO"`), đơn vị `ban_online = false`, vượt `so_luong_toi_da_moi_don` (tính theo đơn vị cơ sở).
  - [x] Gợi ý "thường mua cùng" đọc `luat_mua_kem` (rỗng thì ẩn).
  - [x] Sổ địa chỉ: CRUD, đúng 1 mặc định; mã tỉnh/xã theo danh mục của đơn vị vận chuyển (spec 08).
- **Giao diện:**
  - [x] Mini-cart, trang giỏ hàng, quản lý địa chỉ trong trang tài khoản.
- **Ghi chú triển khai:**
  - Spec 06 mục 3.20, QĐ-23. Giỏ không giữ hàng; thuốc kê đơn bị chặn ở service cho mọi đường vào giỏ (thêm, sửa, gộp), dòng đã lưu mà sản phẩm đổi loại thì `mua_duoc = false`. Giới hạn mua cộng mọi đơn vị của sản phẩm quy về đơn vị cơ sở; gộp giỏ cắt theo giới hạn và báo `bo_qua`.
  - Danh mục tỉnh/xã là bản giả (JSON) ở `tich_hop/van_chuyen/`; bản GHN làm ở T4.7. Địa chỉ lưu `ma_tinh`/`ma_phuong_xa`, tên do máy chủ điền, `ma_quan_huyen` để trống.
  - Giao diện: mini-cart ở header (số lượng + popover), `/gio-hang` (đổi số lượng, đổi đơn vị, xóa, "Thường mua cùng" tự ẩn khi rỗng), nút "Thêm vào giỏ" ở trang sản phẩm, `/tai-khoan` có sổ địa chỉ. `test/render.tsx` nay bọc `<App>` của antd.
  - Chưa làm: sửa hồ sơ cá nhân và đổi mật khẩu của khách (chưa có API), Idempotency-Key cho thêm giỏ không cần (cộng dồn là thao tác của người dùng).


### [x] T4.2 · Máy trạng thái đơn hàng
- **Chức năng:** HT06 (Máy trạng thái đơn hàng)
- **Phụ thuộc:** T3.1
- **Bảng:** `don_hang`, `lich_su_trang_thai`
- **Tiêu chí chấp nhận:**
  - [x] `ban_hang/trang_thai.py`: bảng chuyển trạng thái dạng dữ liệu đúng bảng 1 spec 04; `chuyen_trang_thai(db, don, den, tac_nhan, nguon, ghi_chu)` kiểm tra hợp lệ + vai trò được phép, ghi `lich_su_trang_thai`, gọi các hook tác động (kho, thanh toán, thông báo) trong cùng transaction.
  - [x] Không nơi nào khác được gán `don_hang.trang_thai` (thêm test quét mã nguồn tìm phép gán trực tiếp).
  - [x] Test tham số hóa: mọi dòng trong bảng chuyển hợp lệ; mọi cặp không có trong bảng bị từ chối (`ma_loi = "CHUYEN_TRANG_THAI_KHONG_HOP_LE"`).
- **Ghi chú triển khai:**
  - Spec 04 mục 1.1 (phần Cài đặt), QĐ-24. Hai điểm vào `khoi_tao_trang_thai` (tạo đơn) và `chuyen_trang_thai`; bảng chuyển là dữ liệu, kiểm cả tác nhân, nguồn và điều kiện (kể cả chặn thuốc kê đơn ở dòng 1, 2, 4, 5 bằng SQL). Tác động kho (nhả giữ, xuất kho, hoàn nhập) đã nối; tác động khác gắn bằng `dang_ky_hook` ở task sau.
  - Test: mọi dòng chạy với từng tác nhân hợp lệ, 13x12 cặp trừ bảng bị từ chối, sai tác nhân/nguồn, khách khác 404, hạn, lý do, hook lỗi hoàn tác, bấm hai lần không xuất kho hai lần, quét AST không nơi nào khác gán trạng thái.
  - Chưa làm: hook cho dòng 27 (KHO10), thanh toán/hoàn tiền/mã giảm giá/vận đơn/thông báo (T4.3, T4.5–T4.7).


### [x] T4.3 · Khuyến mãi và mã giảm giá
- **Chức năng:** AD06 (Quản lý khuyến mãi, mã giảm giá), KTV04 (Áp dụng mã giảm giá)
- **Phụ thuộc:** T2.2
- **Bảng:** `khuyen_mai`, `khuyen_mai_pham_vi`, `ma_giam_gia`
- **Tiêu chí chấp nhận:**
  - [x] CRUD khuyến mãi (%/số tiền, trần giảm, đơn tối thiểu, thời gian, tổng lượt, lượt/khách, phạm vi toàn bộ/danh mục/sản phẩm) và sinh mã.
  - [x] `POST /api/v1/toi/ma-giam-gia/kiem-tra`: trả số tiền giảm dự kiến theo giỏ (thuật toán spec 04 mục 4), lý do nếu không áp dụng được.
  - [x] Thuốc kê đơn luôn bị loại khỏi phần được giảm.
- **Giao diện:**
  - [x] Quản trị khuyến mãi; ô nhập mã ở trang thanh toán.
- **Ghi chú triển khai:**
  - Spec 06 mục 3.21, QĐ-25. `khuyen_mai/tinh.py` (thuật toán spec 04 mục 4: % làm tròn nửa lên, trần, số tiền cố định, chia theo sàn dồn phần dư vào dòng hợp lệ cuối), `ap_dung.py` (`kiem_tra_ma` chỉ đọc, `dung_ma` khóa `khuyen_mai` FOR UPDATE rồi tăng lượt, `tra_luot_khi_huy` gắn hook các dòng 9, 12, 14, 15, 19, 21, 27), `quan_tri.py` (CRUD, sinh mã, khóa lạc quan `phien_ban`).
  - Kiểm tra mã giới hạn tần suất theo khách (cửa sổ trượt); thuốc kê đơn bị loại khỏi cơ sở giảm ở tầng tính.
  - Test: 49 backend (tính giảm, phạm vi, lượt, hạn, kê đơn, phân quyền, hook trả lượt); frontend 6 (trang quản trị, ô nhập mã). Ô nhập mã `OMaGiamGia` đã có ở giỏ hàng; gắn vào trang thanh toán ở T4.4 (`dung_ma` gọi lúc đặt đơn).


### [x] T4.4 · Đặt hàng và giữ hàng theo FEFO
- **Chức năng:** KTV02 (Đặt hàng)
- **Phụ thuộc:** T4.1, T4.2, T4.3
- **Bảng:** `gio_hang`, `ct_gio_hang`, `don_hang`, `ct_don_hang`, `phan_bo_lo`, `lo_thuoc`, `dia_chi`, `khuyen_mai`, `khuyen_mai_pham_vi`, `ma_giam_gia`, `lich_su_trang_thai`
- **Tiêu chí chấp nhận:**
  - [x] `POST /api/v1/toi/don-hang` với header `Idempotency-Key`: kiểm tra lại giá, tồn khả dụng (chỉ lô `dang_ban`), giới hạn số lượng, mã giảm giá (khóa `FOR UPDATE`), tính phí ship (adapter vận chuyển, miễn phí từ `mien_phi_ship_tu`), tạo đơn + chi tiết (bản chụp tên/giá/đơn vị, `giam_gia_phan_bo`) + phân bổ lô giữ hàng.
  - [x] COD → `cho_xac_nhan`; VNPay/MoMo → `cho_thanh_toan` + `han_thanh_toan`.
  - [x] Test tranh chấp: 2 khách cùng đặt đơn vị cuối cùng → đúng 1 đơn thành công, đơn kia nhận `ma_loi = "HET_HANG"`, tồn không âm.
- **Giao diện:**
  - [x] Trang thanh toán (địa chỉ, hình thức nhận, phương thức thanh toán, mã giảm giá, tổng tiền), trang đặt hàng thành công.
- **Ghi chú triển khai:**
  - Spec 06 mục 3.22, QĐ-26. `modules/ban_hang/dat_hang.py` (`_tinh_don` dùng chung cho `xem_truoc` và `dat_hang`), `core/idempotency.py`, `core/ma_chung_tu.ma_don_hang`, `tich_hop/van_chuyen` (`DonViVanChuyen.tinh_phi`, bản giả `VanChuyenGia`), `gio_hang/dich_vu.lay_dong_de_dat`. Đơn dựng từ giỏ đã lưu của khách, không nhận dòng hàng từ client.
  - Thêm ngoài tiêu chí: `POST /toi/don-hang/xem-truoc` (trang thanh toán cần phí ship và tổng trước khi đặt) và `GET /toi/don-hang/{ma_don}` (trang kết quả đọc lại từ máy chủ). Trang kết quả dùng `/thanh-toan/ket-qua?ma=...` (route đã có trong spec 09), T4.5 mở rộng cho kết quả cổng thanh toán.
  - Bất biến 4 và 5 đã thêm vào `tests/bat_bien/kiem_tra.py` (`co_don_hang=False` cho test kho dựng đơn bằng factory).
  - Test: 23 backend mới (đặt COD/VNPay/MoMo, FEFO tách lô và bỏ qua lô cận hạn/hết hạn, giữ hàng và mã giảm giá hoàn tác khi `HET_HANG`, `GIA_DA_THAY_DOI`, idempotency, kê đơn lọt giỏ, vượt giới hạn, địa chỉ người khác, hai khách tranh đơn vị cuối, hai lần đặt đồng thời của một khách); 15 frontend.
  - Chưa làm: phí ship thật qua GHN (T4.7); khối lượng sản phẩm chưa có trong schema nên gửi adapter ước lượng 20 g mỗi đơn vị cơ sở; thanh toán online thật và `han_thanh_toan` hết hạn (T4.5); khách vãng lai không đặt được (chỉ qua đơn thuốc, T5.x).


### [x] T4.5 · Thanh toán online và hủy quá hạn
- **Chức năng:** KTV03 (Thanh toán online), HT04 (Xử lý IPN thanh toán), HT03 (Hủy đơn quá hạn)
- **Phụ thuộc:** T4.4
- **Bảng:** `thanh_toan`, `don_hang`, `phan_bo_lo`, `lo_thuoc`, `ma_giam_gia`
- **Tiêu chí chấp nhận:**
  - [x] Adapter VNPay, MoMo (spec 08) + bản giả có trang "cổng giả" để bấm thành công/thất bại khi dev.
  - [x] IPN: kiểm chữ ký, kiểm số tiền khớp `tong_tien`, chống xử lý trùng bằng `ma_giao_dich_cong`, chuyển trạng thái qua HT06; trả đúng định dạng phản hồi cổng yêu cầu.
  - [x] HT03 mỗi phút: hủy đơn quá `han_thanh_toan`/`han_xac_nhan`, nhả giữ hàng, trả lượt mã giảm giá.
  - [x] Test: IPN gửi 2 lần chỉ xử lý 1 lần; IPN sai chữ ký bị từ chối; IPN đến sau khi đơn đã bị hủy quá hạn → tạo giao dịch hoàn tiền chờ xác nhận.
- **Giao diện:**
  - [x] Chuyển hướng sang cổng, trang kết quả thanh toán (đọc trạng thái từ backend, không tin tham số URL).
- **Ghi chú triển khai:**
  - Spec 06 mục 3.23 và 8, QĐ-27. `tich_hop/thanh_toan/` (`CongThanhToan` Protocol, VNPay HMAC-SHA512, MoMo HMAC-SHA256, cổng giả ký khóa giả) chọn theo `THANH_TOAN_CHE_DO` (`gia` mặc định, `sandbox` gọi cổng thật). `modules/thanh_toan/dich_vu.py` giữ `tao_thanh_toan` (KTV03, `Idempotency-Key`) và `xu_ly_ipn` (HT04: chữ ký, tìm giao dịch `ma_don-id`, số tiền, chống trùng, cập nhật; khóa giao dịch rồi đơn `FOR UPDATE`). Hook dòng 10, 11 đặt `trang_thai_tt = da_thanh_toan`. IPN thất bại: giao dịch `that_bai`, đơn giữ chờ thanh toán. IPN thành công nhưng đơn không còn chờ thanh toán (đã hủy quá hạn hoặc trả hai lần): ghi `thanh_cong` và tạo `hoan_tien` (`khoi_tao`) + `trang_thai_tt = cho_hoan_tien`.
  - HT03: `ban_hang/het_han.py::huy_don_qua_han` hủy qua `chuyen_trang_thai` (savepoint từng đơn, nhả hàng và trả lượt mã nhờ hook dòng 9, 12); `app/jobs` thêm lịch theo phút (`LICH_PHUT`, mỗi phút) dùng chung `chay_job` với `pg_try_advisory_lock`.
  - Giao diện: đặt hàng VNPay/MoMo tạo giao dịch rồi chuyển sang cổng; `/thanh-toan/ket-qua` hỏi lại mỗi 3 giây khi còn chờ thanh toán, có "Thanh toán lại"; `/thanh-toan-gia` là cổng giả.
  - Test: 25 backend (`tests/thanh_toan/`: tạo giao dịch, idempotency, IPN VNPay/MoMo/giả, hai IPN tuần tự và đồng thời chỉ xử lý một lần, sai chữ ký/số tiền, đến muộn, HT03, route cổng giả chỉ ở chế độ giả), 11 frontend.
  - Chưa làm: hoàn tiền thật qua VNPay/MoMo (`hoan_tien` ném `NotImplementedError`, làm ở T6.3); thông báo cho khách khi đơn bị hủy quá hạn (T4.7); dòng 9 "yêu cầu đơn thuốc quay lại Đang tư vấn" (T5.x).


### [x] T4.6 · Xử lý đơn của dược sĩ và khách hủy đơn
- **Chức năng:** DS01 (Xem, lọc danh sách đơn hàng), DS02 (Xác nhận đơn hàng), DS03 (Hủy đơn hàng), KTV06 (Hủy đơn hàng)
- **Phụ thuộc:** T4.4
- **Bảng:** `don_hang`, `ct_don_hang`, `lich_su_trang_thai`, `phan_bo_lo`, `lo_thuoc`, `bien_dong_kho`, `thanh_toan`, `ma_giam_gia`
- **Tiêu chí chấp nhận:**
  - [x] Danh sách đơn nội bộ: lọc trạng thái, ngày, phương thức thanh toán, kênh; chi tiết đơn có dòng thời gian trạng thái.
  - [x] Xác nhận đơn; hủy đơn có lý do (trước khi rời kho, hoàn nhập đúng lô nếu đã chốt lô); khách tự hủy theo spec 04.
  - [x] Hủy đơn đã thanh toán → tạo `thanh_toan` loại `hoan_tien` (`khoi_tao`), `trang_thai_tt = cho_hoan_tien` (Admin xác nhận ở T6.3).
  - [x] Khách chỉ xem/hủy đơn của chính mình (truy cập đơn người khác → 404).
- **Giao diện:**
  - [x] Màn quản lý đơn cho dược sĩ; trang "Đơn hàng của tôi" có nút hủy.
- **Ghi chú triển khai:**
  - Spec 06 mục 3.24, QĐ-28. `modules/ban_hang/dich_vu_don.py` + `router_noi_bo.py`: `GET /noi-bo/don-hang` (lọc trạng thái, ngày giờ VN, phương thức, kênh, `q`), `GET /noi-bo/don-hang/{id}` (chi tiết, dòng thời gian có người thực hiện, giao dịch), `POST .../xac-nhan` (dòng 13), `POST .../huy` (lý do bắt buộc; dòng 15, 19). Khách: `GET /toi/don-hang` (danh sách), `POST /toi/don-hang/{ma}/huy`; chi tiết thêm `lich_su` và `ly_do_huy`.
  - Hook mới `_tao_hoan_tien_khi_huy` cho dòng 14, 15, 19, 21, 27: đơn đã thanh toán thì tạo `hoan_tien` (`khoi_tao`, trỏ giao dịch gốc) + `cho_hoan_tien`. Nhả giữ, hoàn nhập đúng lô và trả lượt mã đã có từ T3.x/T4.3, ở đây chỉ kiểm chứng bằng test.
  - Kho chỉ thấy đơn từ "Đã xác nhận" (SQL, 404 cho đơn khác) và không thấy giao dịch/`khach_hang_id`; Admin chỉ xem. Registry phân quyền thêm 4 route.
  - Test: 12 backend (`tests/ban_hang/test_xu_ly_don.py`: hủy trả lượt mã và nhả giữ, đơn người khác 404, hủy khi đang soạn bị chặn, hoàn tiền khi hủy đơn đã thanh toán và không hoàn khi chưa trả, hoàn nhập đúng lô, lý do bắt buộc, phân quyền kho/Admin, lọc, kho giới hạn đơn); 11 frontend + `lib/donHang`.
  - Chưa làm: thông báo cho khách khi dược sĩ hủy (T4.7 cùng hệ thống thông báo); trang Admin xem đơn (AD16); mua lại, đổi trả ở trang đơn của khách (KTV08, KTV09).

### [x] T4.7 · Soạn hàng, đóng gói, vận chuyển, theo dõi đơn
- **Chức năng:** KHO03 (Soạn hàng, xuất kho theo đơn), KHO04 (Đóng gói, bàn giao vận chuyển), HT05 (Nhận webhook vận chuyển), KTV05 (Theo dõi đơn hàng)
- **Phụ thuộc:** T4.6
- **Bảng:** `don_hang`, `phan_bo_lo`, `lo_thuoc`, `bien_dong_kho`, `van_don`, `thanh_toan`, `lich_su_trang_thai`
- **Tiêu chí chấp nhận:**
  - [x] Danh sách đơn chờ soạn; gợi ý lô FEFO; đổi lô bắt buộc lý do; chuyển `dang_soan_hang` → chốt lô, trừ tồn, ghi thẻ kho; in phiếu soạn hàng.
  - [x] Đóng gói: adapter GHN tạo vận đơn (giao tận nơi) → `cho_lay_hang`; đơn nhận tại nhà thuốc chỉ đóng gói.
  - [x] Webhook GHN (HT05): kiểm token, ánh xạ trạng thái đối tác → trạng thái đơn qua HT06; COD giao thành công ghi `thanh_toan` COD.
  - [x] Khách xem dòng thời gian trạng thái và mã vận đơn.
- **Giao diện:**
  - [x] Màn soạn hàng cho kho (quét mã vạch xác nhận), in phiếu/nhãn; trang chi tiết đơn của khách.
- **Ghi chú triển khai:**
  - Spec 06 mục 3.25, spec 08 mục 5, QĐ-29. `modules/ban_hang/soan_hang.py` + `router_kho.py` (`/noi-bo/soan-hang/{id}`: chi tiết kèm lô giữ và gợi ý FEFO, `doi-lo`, `bat-dau`, `dong-goi`), `ton_kho.doi_lo` (khóa cả hai lô id tăng dần, lý do bắt buộc).
  - Adapter vận chuyển: `tich_hop/van_chuyen/` thêm `tao_van_don`, `huy_van_don`, `xac_thuc_webhook`; bản giả (`gia.py`) và GHN (`ghn.py`, httpx, **chưa thử với sandbox thật**: tên trường theo tài liệu GHN v2, cần đối chiếu khi bật `VAN_CHUYEN_CHE_DO=ghn`); chọn theo `VAN_CHUYEN_CHE_DO`. `anh_xa.py` ánh xạ trạng thái đối tác và tìm đường đi qua các bước hợp lệ.
  - HT05: `modules/van_chuyen/` (`POST /webhook/ghn` kiểm token, `POST /webhook/gia-van-chuyen` chỉ ở chế độ giả); hook dòng 23 ghi COD `thanh_cong` + `da_thanh_toan`.
  - Khách thấy `lich_su` và `van_don` ở chi tiết đơn; kho có hàng đợi `/soan-hang`, phiếu `/soan-hang/:id` (quét mã vạch, đổi lô, in phiếu, nút giả lập vận chuyển).
  - Test: 34 backend (`test_soan_hang.py`, `test_van_chuyen.py`), 8 frontend.
  - Chưa làm: thông báo cho khách ở dòng 18, 24 (hệ thống thông báo khách là KTV13, task sau); tạo lại vận đơn khi giao thất bại (dòng 25 phía kho); báo kho khi GHN hủy vận đơn (hiện chỉ ghi `van_don`); nhãn vận chuyển in từ GHN (hiện in phiếu soạn có mã vận đơn).

### [x] T4.8 · Đơn qua điện thoại và nhận tại nhà thuốc
- **Chức năng:** DS07 (Tạo đơn hộ khách), DS15 (Giao đơn nhận tại nhà thuốc)
- **Phụ thuộc:** T4.7
- **Bảng:** `don_hang`, `ct_don_hang`, `phan_bo_lo`, `thanh_toan`, `lich_su_trang_thai`
- **Tiêu chí chấp nhận:**
  - [x] Dược sĩ lập đơn cho khách (tìm khách theo SĐT hoặc nhập người nhận), cùng quy tắc với KTV02, chặn thuốc kê đơn; COD → `da_xac_nhan`, online → `cho_thanh_toan` + gửi link.
  - [x] Giao đơn nhận tại quầy: tìm theo mã đơn/SĐT, thu tiền nếu chưa thanh toán, chuyển `da_giao`.
- **Giao diện:**
  - [x] Màn tạo đơn hộ; màn giao hàng tại quầy.
- **Ghi chú triển khai:**
  - API và quyết định: spec 06 mục 3.26, QĐ-30. Đơn hộ dùng chung `tinh_tien` và kiểm dòng của giỏ với KTV02 (đã tách hàm dùng chung), vào máy trạng thái dòng 4/5; giữ hàng FEFO, idempotency theo dược sĩ.
  - Khách tra bằng đúng SĐT; đơn online bắt buộc khách có tài khoản, khách vãng lai chỉ COD (link mã truy cập là T5.3). Link thanh toán trả trong phản hồi, gửi SMS tự động là KTV13.
  - Giao tại quầy: tìm theo mã đơn/SĐT, thu tiền mặt/chuyển khoản cùng transaction với dòng 20. Quá hạn nhận tại quầy (dòng 21) là HT08 ở T4.9.
  - Giao diện: `/don-hang/tao` (tìm khách, tìm sản phẩm qua `/tim-kiem`, chọn đơn vị, địa chỉ tỉnh/xã) và `/giao-tai-quay`.
  - Chưa làm: đọc sổ địa chỉ của khách để điền sẵn (API đã trả `dia_chi`, giao diện chưa dùng).

### [x] T4.9 · Tự hoàn tất đơn và lịch sử mua
- **Chức năng:** HT08 (Tự hoàn tất đơn, nhả khóa), KTV08 (Lịch sử mua, mua lại)
- **Phụ thuộc:** T4.7
- **Bảng:** `don_hang`, `yeu_cau_don_thuoc`, `yeu_cau_doi_tra`, `hoi_thoai`, `ct_don_hang`, `gio_hang`, `ct_gio_hang`
- **Tiêu chí chấp nhận:**
  - [x] HT08 (mỗi 15 phút): `da_giao` quá `thoi_han_doi_tra_ngay` và không có yêu cầu đổi trả mở → `hoan_tat`; đơn nhận tại quầy quá `thoi_han_nhan_tai_quay_ngay` → hủy + hoàn nhập. (Các phần nhả khóa đơn thuốc, đóng chat bổ sung ở T5.3, T7.4.)
  - [x] Lịch sử mua có phân trang; "Mua lại" đưa các dòng còn bán vào giỏ, bỏ qua thuốc kê đơn và báo lý do.
- **Giao diện:**
  - [x] Trang lịch sử mua có nút "Mua lại".
- **Ghi chú triển khai:**
  - HT08 (`ban_hang/tu_hoan_tat.py`, QĐ-31): job `ht08_tu_hoan_tat` mỗi 15 phút; dòng 29 và dòng 21 đi qua `chuyen_trang_thai` trong savepoint riêng. Mốc hạn lấy từ lịch sử trạng thái; yêu cầu đổi trả chưa `tu_choi`/`hoan_tat` chặn tự hoàn tất.
  - Phần nhả khóa đơn thuốc quá hạn làm ở T5.3, đóng chat không hoạt động ở T7.4.
  - Lịch sử mua dùng lại `GET /toi/don-hang` (KTV06, đã phân trang). Thêm `POST /toi/don-hang/{ma_don}/mua-lai` (spec 06 mục 3.27) dựa trên `gop_gio`; dòng bỏ qua trả kèm lý do.
  - Giao diện: nút "Mua lại" ở danh sách và chi tiết đơn; hộp thoại liệt kê dòng không thêm được (có tên sản phẩm ở trang chi tiết). `NHAN_LY_DO` chuyển sang `gio-hang/gioHang.ts` dùng chung.

## P5 · Đơn thuốc & bán tại quầy

_Hồ sơ sức khỏe, gửi và duyệt đơn thuốc, tạo đơn từ đơn thuốc, POS._

### [x] T5.1 · Hồ sơ sức khỏe và dị ứng
- **Chức năng:** KTV11 (Hồ sơ sức khỏe)
- **Phụ thuộc:** T2.3
- **Bảng:** `ho_so_suc_khoe`, `di_ung`, `hoat_chat`
- **Tiêu chí chấp nhận:**
  - [x] Khách xem/sửa/xóa hồ sơ; chỉ lưu khi `dong_y_su_dung = true` (ghi `dong_y_luc`); `benh_nen` mã hóa mức ứng dụng (Fernet, khóa trong `.env`).
  - [x] Hàm cổng `duoc_doc_ho_so_suc_khoe(nhan_vien, khach_hang_id)` theo spec 03 mục 5; mọi lần dược sĩ đọc ghi nhật ký (không ghi nội dung).
  - [x] Test: Admin không đọc được; dược sĩ không được gán không đọc được.
- **Giao diện:**
  - [x] Trang hồ sơ sức khỏe có màn đồng ý, chọn hoạt chất dị ứng.
- **Ghi chú triển khai:** Module mới `modules/suc_khoe` (`dich_vu`, `router`, `schemas`) và `core/ma_hoa.py` (Fernet, khóa `KHOA_MA_HOA`, thêm phụ thuộc `cryptography`). API ở spec 06 mục 3.28: xem/lưu/xóa hồ sơ, gợi ý hoạt chất. Thu hồi đồng ý = xóa hồ sơ (QĐ-32). Hàm cổng `duoc_doc_ho_so_suc_khoe` kèm `doc_ho_so_cho_duoc_si`, chưa có route nội bộ (T5.3 và T7.x sẽ gọi). Giao diện `/tai-khoan/suc-khoe` (màn đồng ý, chọn hoạt chất dị ứng, xóa). Ghi chú từng dị ứng có ở API nhưng chưa có ô nhập trên giao diện. Test `tests/suc_khoe` (15) và `TrangSucKhoe.test.tsx` (4). `/review-nghiep-vu` gộp theo pha P5.

### [x] T5.2 · Gửi yêu cầu tư vấn đơn thuốc
- **Chức năng:** KVL08 (Gửi yêu cầu tư vấn đơn thuốc), KTV07 (Gửi yêu cầu tư vấn đơn thuốc)
- **Phụ thuộc:** T5.1
- **Bảng:** `yeu_cau_don_thuoc`, `ct_yeu_cau_don_thuoc`, `ma_otp`, `don_hang`
- **Tiêu chí chấp nhận:**
  - [x] Upload ảnh đơn vào lưu trữ riêng tư (spec 08), tính `hash_anh`; khách vãng lai xác thực SĐT bằng OTP (`don_thuoc_khach`).
  - [x] Khách thành viên xem danh sách/trạng thái yêu cầu của mình, hủy khi còn `cho_duyet`/`dang_tu_van`.
  - [x] Ảnh chỉ xem được qua URL ký có hạn bởi chủ yêu cầu hoặc dược sĩ đang xử lý.
- **Giao diện:**
  - [x] Trang gửi đơn thuốc (chụp/tải ảnh), trang "Đơn thuốc của tôi".
- **Ghi chú triển khai:** Module `modules/don_thuoc` (`dich_vu`, `router`, `schemas`); vùng riêng tư và URL ký trong `core/luu_tru.py`, endpoint `GET /tep-rieng/...` ở `modules/tep`. API ở spec 06 mục 3.29, quyết định ở QĐ-33. OTP thêm mục đích `don_thuoc_khach`. Trang `/gui-don-thuoc` (OTP cho khách vãng lai) và `/tai-khoan/don-thuoc` (danh sách, xem ảnh, hủy). SMS kết quả và AI06 đọc ảnh làm ở T5.3 và T7.6. Test `tests/don_thuoc` (15), `DonThuoc.test.tsx` (5).

### [x] T5.3 · Duyệt đơn thuốc và tạo đơn từ đơn thuốc
- **Chức năng:** DS04 (Duyệt yêu cầu đơn thuốc), DS05 (Tạo đơn hàng từ đơn thuốc)
- **Phụ thuộc:** T5.2, T4.4
- **Bảng:** `yeu_cau_don_thuoc`, `ct_yeu_cau_don_thuoc`, `ho_so_suc_khoe`, `di_ung`, `tuong_tac_hoat_chat`, `lo_thuoc`, `don_hang`, `ct_don_hang`, `phan_bo_lo`
- **Tiêu chí chấp nhận:**
  - [x] Hàng chờ; nhận xử lý = khóa (`duoc_si_id`, `khoa_luc`), HT08 tự nhả quá `thoi_gian_khoa_don_thuoc_phut`.
  - [x] Màn duyệt: ảnh đơn, tồn kho, hồ sơ dị ứng (qua hàm cổng), cảnh báo trùng `hash_anh`, cảnh báo tương tác/dị ứng; checklist (spec 04 mục 6) bắt buộc đủ trước khi chấp nhận; từ chối bắt buộc lý do.
  - [x] Tạo đơn từ đơn thuốc → `cho_khach_xac_nhan`, `han_xac_nhan`, link có mã truy cập cho khách vãng lai (SMS); khách xác nhận/chọn thanh toán (phần còn lại của KTV07).
  - [x] `da_su_dung` chỉ bật khi đơn sang `dang_soan_hang`; đơn hủy trước đó → yêu cầu quay lại `dang_tu_van`, tạo lại đơn được.
- **Giao diện:**
  - [x] Màn hàng chờ và màn duyệt đơn thuốc cho dược sĩ; trang xác nhận đơn cho khách (cả link không cần đăng nhập).
- **Ghi chú triển khai:** Module `modules/don_thuoc` thêm `duyet.py` (DS04, DS05), `xac_nhan.py` (KTV07), hai router; hook `trang_thai.py` cho `da_su_dung` (dòng 16) và trả yêu cầu về `dang_tu_van` (dòng 9, 12, 14, 15, 19, 21, 27); HT08 nhả khóa. API ở spec 06 mục 3.30, quyết định ở QĐ-34 (thuốc kê đơn chỉ vào đơn qua DS05, phí ship tính khi khách xác nhận, link mã truy cập, thanh toán online của khách vãng lai). Giao diện: hàng chờ `/don-thuoc`, màn duyệt `/don-thuoc/:id`, `/xac-nhan-don/:token`, panel xác nhận trong chi tiết đơn của thành viên. Test `tests/don_thuoc` (`test_duyet_don_thuoc`, `test_xac_nhan_don_thuoc`) và 3 file vitest mới. Chưa có: nhập tay thuốc trên đơn, gợi ý thuốc thay thế.

### [x] T5.4 · Bán tại quầy (POS)
- **Chức năng:** DS08 (Bán tại quầy – POS)
- **Phụ thuộc:** T5.3
- **Bảng:** `don_hang`, `ct_don_hang`, `phan_bo_lo`, `lo_thuoc`, `bien_dong_kho`, `thanh_toan`, `yeu_cau_don_thuoc`, `tuong_tac_hoat_chat`
- **Tiêu chí chấp nhận:**
  - [x] Quét mã vạch/tìm sản phẩm, chọn đơn vị (bán lẻ theo viên); dùng được lô cận hạn; xuất kho FEFO ngay, ghi thẻ kho; đơn `tai_quay` → `hoan_tat`.
  - [x] Thuốc kê đơn: bắt buộc tạo yêu cầu đơn thuốc kênh `tai_quay` (ảnh + người bệnh) trước khi thanh toán; hiện cảnh báo tương tác.
  - [x] Thanh toán tiền mặt (tính tiền thừa)/chuyển khoản; gắn khách theo SĐT nếu có tài khoản; in hóa đơn (HTML in được).
- **Giao diện:**
  - [x] Màn POS tối ưu bàn phím/máy quét.
- **Ghi chú triển khai:** `ban_hang/pos.py`, `router_pos.py`, `schemas_pos.py`; API ở spec 06 mục 3.31, quyết định QĐ-35 (không giỏ hàng, không mã giảm giá, đơn vào `hoan_tat` rồi giữ và xuất kho có lô cận hạn trong một transaction, thuốc kê đơn cần yêu cầu `tai_quay` của chính dược sĩ, tiền thối chỉ có lúc bán). Giao diện `/pos` (ô quét mã vạch tự thêm đúng đơn vị, cảnh báo, lập yêu cầu đơn thuốc, hóa đơn 80 mm in bằng `window.print`). Test `tests/ban_hang/test_pos.py` (15), `TrangPos.test.tsx` (4), `pos.test.ts` (3).

## P6 · Sau bán & thu hồi

_Đổi trả, biệt trữ, hoàn tiền, đánh giá, hỏi đáp, thông báo, thu hồi lô._

### [x] T6.1 · Yêu cầu đổi trả và duyệt
- **Chức năng:** KTV09 (Yêu cầu đổi trả), DS09 (Xử lý yêu cầu đổi trả)
- **Phụ thuộc:** T4.9
- **Bảng:** `yeu_cau_doi_tra`, `ct_yeu_cau_doi_tra`, `van_don`, `thanh_toan`, `don_hang`
- **Tiêu chí chấp nhận:**
  - [x] Khách tạo yêu cầu trong thời hạn, chọn dòng + số lượng (tổng đã trả không vượt đã mua), lý do, ảnh/video; COD/tiền mặt nhập tài khoản nhận hoàn.
  - [x] Dược sĩ duyệt/từ chối; duyệt → tạo vận đơn `tra_hang` (adapter vận chuyển) gửi mã cho khách.
  - [x] Sau khi kho nhận: chọn hoàn tiền (tạo giao dịch hoàn, số tiền theo spec 04 mục 5) hoặc gửi hàng thay thế (đơn 0đ `don_hang_goc_id`, trạng thái `da_xac_nhan`).
- **Giao diện:**
  - [x] Form đổi trả trong chi tiết đơn; màn xử lý đổi trả cho dược sĩ.
- **Ghi chú triển khai:** `modules/doi_tra/` (`dich_vu`, `xu_ly`, `router`, `schemas`); API ở spec 06 mục 3.32; quyết định QĐ-36 (không đổi schema, tài khoản nhận hoàn nhập sau khi có giao dịch hoàn, tính số tiền hoàn, dòng 30 cho đơn thay thế). Hàng đổi trả sau khi kho nhận (`ket_qua_kiem_hang`, `so_luong_nhan`) do T6.2. Test `tests/doi_tra/test_doi_tra.py` (16), `TrangXuLyDoiTra.test.tsx`, `doiTra.test.ts`; giao diện `DoiTraNut`, `TrangDoiTraCuaToi`, `TrangXuLyDoiTra`.

### [x] T6.2 · Nhận hàng trả, hàng hoàn và biệt trữ
- **Chức năng:** KHO10 (Nhận hàng trả về, hàng hoàn)
- **Phụ thuộc:** T6.1
- **Bảng:** `yeu_cau_doi_tra`, `ct_yeu_cau_doi_tra`, `lo_thuoc`, `phan_bo_lo`, `bien_dong_kho`
- **Tiêu chí chấp nhận:**
  - [x] Hàng đổi trả: ghi `lo_id`, `so_luong_nhan`, kết quả kiểm; cộng `so_luong_biet_tru` (thẻ kho `nhan_tra_ve`).
  - [x] Đơn `hoan_ve_kho`: kiểm hàng; nguyên niêm phong → hoàn nhập đúng lô; hư hỏng → biệt trữ; chuyển `da_huy` qua HT06; đã thanh toán → tạo hoàn tiền.
- **Giao diện:**
  - [x] Màn nhận hàng trả/hoàn cho kho.
- **Ghi chú triển khai:** `doi_tra/kho.py`, `schemas_kho.py`, 4 route `/noi-bo/nhan-hang/...` (spec 06 mục 3.33), quyết định QĐ-37 (đơn vị theo dòng đơn, hàng khách trả luôn vào biệt trữ, hoàn tiền theo số thực nhận). Hàng hoàn: hoàn nhập đúng lô hoặc biệt trữ, rồi dòng 27 qua HT06 (hook tạo hoàn tiền). Giao diện `/hang-tra-ve`. Test `tests/doi_tra/test_nhan_hang_tra.py` (8), `TrangHangTraVe.test.tsx` (2).

### [x] T6.3 · Xác nhận hoàn tiền
- **Chức năng:** AD17 (Xác nhận hoàn tiền)
- **Phụ thuộc:** T6.1
- **Bảng:** `thanh_toan`, `don_hang`, `yeu_cau_doi_tra`
- **Tiêu chí chấp nhận:**
  - [x] Danh sách giao dịch hoàn tiền `khoi_tao`; VNPay/MoMo gọi API hoàn tiền của adapter theo `thanh_toan_goc_id`; COD/tiền mặt: nhập chứng từ chuyển khoản.
  - [x] Người xác nhận ≠ dược sĩ duyệt đổi trả; cập nhật `trang_thai_tt` (`da_hoan_tien`/`hoan_tien_mot_phan`), thông báo khách, ẩn danh hóa `thong_tin_nhan_hoan` sau khi xong.
- **Giao diện:**
  - [x] Màn hoàn tiền cho Admin.
- **Ghi chú triển khai:** `modules/hoan_tien/` (`dich_vu`, `router`, `schemas`); API spec 06 mục 3.34; QĐ-38 (hoàn do hủy đơn không bắt buộc tài khoản khách, ẩn danh hóa còn 4 số cuối, cổng lỗi giữ `khoi_tao`). Sửa bản giả của cổng: mã hoàn có hậu tố ngẫu nhiên (hoàn một phần nhiều lần bị trùng `ma_giao_dich_cong`). Giao diện `/quan-tri/hoan-tien`. Test `tests/hoan_tien/test_xac_nhan_hoan_tien.py` (6), `TrangHoanTien.test.tsx` (3).

### [x] T6.4 · Đánh giá và hỏi đáp sản phẩm
- **Chức năng:** KTV10 (Đánh giá sản phẩm), KTV15 (Đặt câu hỏi về sản phẩm), DS11 (Kiểm duyệt đánh giá, hỏi đáp)
- **Phụ thuộc:** T4.9
- **Bảng:** `danh_gia`, `ct_don_hang`, `hoi_dap`
- **Tiêu chí chấp nhận:**
  - [x] Đánh giá 1-5 sao cho dòng đơn `da_giao`/`hoan_tat`, mỗi dòng 1 lần, có ảnh; câu hỏi sản phẩm (cần đăng nhập).
  - [x] Dược sĩ ẩn đánh giá/câu hỏi vi phạm, trả lời câu hỏi (thông báo cho khách).
- **Giao diện:**
  - [x] Khối đánh giá và hỏi đáp trên trang chi tiết; màn kiểm duyệt cho dược sĩ.
- **Ghi chú triển khai:** `modules/danh_gia/`; API spec 06 mục 3.35; QĐ-39 (hậu kiểm, giới hạn 10 câu hỏi/ngày, chỉ dược sĩ kiểm duyệt). Giao diện: tab Hỏi đáp và ảnh đánh giá ở trang sản phẩm, `/tai-khoan/danh-gia`, `/nhan-vien/kiem-duyet`. Test `tests/danh_gia` (7), `TrangKiemDuyet.test.tsx` (2).

### [x] T6.5 · Thông báo và nhắc mua lại
- **Chức năng:** KTV13 (Nhận thông báo), HT07 (Gửi thông báo, nhắc mua lại), KTV14 (Nhắc mua lại)
- **Phụ thuộc:** T4.9
- **Bảng:** `thong_bao`, `ct_don_hang`, `san_pham`
- **Tiêu chí chấp nhận:**
  - [x] Dịch vụ `thong_bao.gui(...)`: ghi bảng `thong_bao` + gửi email/SMS qua adapter theo loại sự kiện (đơn hàng, đơn thuốc, đổi trả, thu hồi).
  - [x] HT07 hằng ngày 08:00: với sản phẩm `dung_dinh_ky`, ngày hết dự kiến = ngày giao + số lượng cơ sở × `so_ngay_dung_moi_don_vi`; nhắc trước 3 ngày, không nhắc trùng.
- **Giao diện:**
  - [x] Chuông thông báo và trang thông báo của khách.
- **Ghi chú triển khai:** `thong_bao/service.gui_cho_khach` (+SMS/email theo loại), `router_khach.py`, `nhac_mua_lai.py`; hook báo khách đổi trạng thái đơn trong `trang_thai._ghi`; job `ht07_nhac_mua_lai` 08:00; API spec 06 mục 3.36; QĐ-40. Giao diện: chuông thông báo của khách ở header (dùng lại `ChuongThongBao`), trang `/tai-khoan/thong-bao`. Test `tests/thong_bao/test_thong_bao_khach.py` (6), `TrangThongBao.test.tsx`.

### [x] T6.6 · Thu hồi lô
- **Chức năng:** AD13 (Khởi tạo lệnh thu hồi lô), KHO12 (Thực hiện thu hồi lô), DS13 (Liên hệ khách khi thu hồi lô)
- **Phụ thuộc:** T6.2
- **Bảng:** `lenh_thu_hoi`, `ct_lenh_thu_hoi`, `lo_thuoc`, `phan_bo_lo`, `thong_bao`, `phieu_xuat_tra`, `phieu_huy`
- **Tiêu chí chấp nhận:**
  - [x] Admin tạo lệnh thu hồi (một lô hoặc mọi lô của sản phẩm): lô → `thu_hoi`, gỡ khỏi đơn chưa xuất (phân bổ lại hoặc báo hết hàng), sinh `ct_lenh_thu_hoi` từ `phan_bo_lo` đã xuất, gửi thông báo khách.
  - [x] Kho gom tồn + hàng khách trả, lập phiếu xuất trả/hủy (đi duyệt AD12); dược sĩ cập nhật kết quả liên hệ.
  - [x] Đóng lệnh khi mọi dòng đã xử lý.
- **Giao diện:**
  - [x] Màn lệnh thu hồi (Admin), danh sách khách cần liên hệ (dược sĩ).
- **Ghi chú triển khai:** `modules/thu_hoi/` (`dich_vu`, `router`, `schemas`); `PhieuXuatTraTao.lenh_thu_hoi_id`; API spec 06 mục 3.37; QĐ-41. Giao diện: `/quan-tri/thu-hoi`, `/nhan-vien/thuc-hien-thu-hoi`, `/nhan-vien/thu-hoi`. Test `tests/thu_hoi/test_thu_hoi.py` (6), `ThuHoi.test.tsx`.

### [x] T6.7 · Màn xem tổng hợp cho Admin
- **Chức năng:** AD16 (Xem đơn hàng, chứng từ kho, nội dung chuyên môn)
- **Phụ thuộc:** T6.6
- **Bảng:** `don_hang`, `phieu_nhap`, `phieu_kiem_ke`, `thong_tin_chuyen_mon`
- **Tiêu chí chấp nhận:**
  - [x] Màn gộp chứng từ kho (`GET /api/v1/noi-bo/chung-tu-kho`: phiếu nhập, kiểm kê, điều chỉnh, hủy, xuất trả) yêu cầu `stock_doc.view`; màn nội dung chuyên môn chỉ xem yêu cầu `content.view`; màn chi tiết dùng lại API nội bộ sẵn có ở mức `chi_xem` (đơn hàng: `order.view`).
  - [x] Admin không thao tác được: nút ghi bị ẩn, gọi API ghi trả 403 (có test cho từng loại).
- **Ghi chú triển khai:** `kho/chung_tu_kho.py` + `router_chung_tu.py` (API spec 06 mục 3.38); màn đơn hàng và chuyên môn của Admin tái dùng trang nhân viên với route `/quan-tri/xem/...` (thêm hai dòng chi tiết `:id` vào bảng spec 09). Test `tests/kho/test_chung_tu_kho_admin.py` (4: gộp/lọc/phân trang, vai trò khác `403`, Admin gọi API ghi `403` cho từng loại).

## P7 · AI

_Kho tri thức, tìm kiếm lai, chatbot RAG, chuyển dược sĩ, đọc ảnh, gợi ý, dự báo._

### [x] T7.1 · Hạ tầng AI và kho tri thức
- **Chức năng:** AD09 (Cấu hình AI), AD10 (Đồng bộ kho tri thức AI)
- **Phụ thuộc:** T2.6
- **Bảng:** `cau_hinh`, `tai_lieu_tri_thuc`, `thong_tin_chuyen_mon`, `bai_viet`
- **Tiêu chí chấp nhận:**
  - [x] `ai/claude.py`: client `AsyncAnthropic`, hàm `goi_json` và `stream_chat` theo spec 07 mục 2 (fallbacks, xử lý refusal, ghi usage); `ai/gia_lap.py` client giả cho dev/test (`AI_GIA_LAP=true`).
  - [x] `ai/embedding.py`: BGE-M3 (sentence-transformers, chuẩn hóa vector) + bản giả sinh vector xác định từ hash.
  - [x] AD10: đồng bộ `tai_lieu_tri_thuc` từ nội dung chuyên môn đã duyệt + bài viết `dua_vao_ai`; chia đoạn theo trường; bỏ qua đoạn có `hash_noi_dung` không đổi; xóa đoạn của nguồn đã gỡ; chạy theo yêu cầu và hằng đêm.
  - [x] AD09: bật/tắt từng module AI, danh sách dấu hiệu nguy hiểm, ngưỡng chuyển dược sĩ (đọc từ `cau_hinh`).
- **Giao diện:**
  - [x] Màn cấu hình AI và nút đồng bộ kho tri thức (hiển thị số đoạn thêm/sửa/xóa).
- **Ghi chú triển khai:** `app/ai/{claude,gia_lap,embedding}.py`, `modules/ai_quan_tri/{cau_hinh_ai,tri_thuc,router}.py`, job `ai_dong_bo_tri_thuc`; API spec 06 mục 3.39; QĐ-43. Giao diện `/quan-tri/cau-hinh-ai`, `/quan-tri/tri-thuc-ai`. Test `tests/ai/test_claude.py` (11), `tests/ai/test_tri_thuc.py` (7), `ai.test.tsx` (3). Chưa chạy BGE-M3 thật và chưa gọi Claude thật (cần khóa và nhóm `ai-local`).

### [x] T7.2 · Tìm kiếm lai
- **Chức năng:** AI01 (Tìm kiếm thông minh)
- **Phụ thuộc:** T7.1, T2.5
- **Bảng:** `san_pham`, `tai_lieu_tri_thuc`, `lich_su_tim_kiem`
- **Tiêu chí chấp nhận:**
  - [x] Kết hợp kết quả trigram (T2.5) và vector (`<=>` cosine trên `tai_lieu_tri_thuc`) bằng Reciprocal Rank Fusion (k = 60); tìm được theo triệu chứng/công dụng.
  - [x] AI lỗi hoặc tắt → tự quay về chỉ từ khóa (test bằng client giả ném lỗi). Ghi `che_do = hybrid`.
- **Ghi chú triển khai:** `cua_hang/tim_kiem_lai.py` (`tim_lai`, `ghep_rrf`, `id_ngu_nghia`); route `/tim-kiem` dùng nó; API spec 06 mục 3.40. Chưa thêm điểm thưởng "bán chạy" vào RRF (chỉ cộng nhỏ cho còn hàng). Test `tests/ai/test_tim_kiem_lai.py` (7).

### [x] T7.3 · Chatbot tư vấn (RAG)
- **Chức năng:** KVL05 (Chat với trợ lý AI), AI02 (Phân loại ý định, phát hiện dấu hiệu nguy hiểm), AI03 (Trả lời bằng RAG)
- **Phụ thuộc:** T7.2
- **Bảng:** `hoi_thoai`, `tin_nhan`, `tai_lieu_tri_thuc`, `danh_gia_cau_tra_loi`, `cau_hinh`, `ho_so_suc_khoe`, `di_ung`, `tuong_tac_hoat_chat`
- **Tiêu chí chấp nhận:**
  - [x] `POST /api/v1/tu-van/chat` trả SSE; lưu `hoi_thoai`, `tin_nhan` (ý định, sản phẩm gợi ý, cờ nguy hiểm, token).
  - [x] AI02: phân loại ý định + dấu hiệu nguy hiểm (từ khóa cấu hình chạy trước, rồi Claude) → nguy hiểm thì trả mẫu cố định khuyên đi khám/gọi 115 và gắn cờ.
  - [x] AI03: tool chỉ đọc theo spec 07 mục 4; mọi tool lọc bỏ thuốc kê đơn và (nếu khách đồng ý) sản phẩm chứa hoạt chất dị ứng ở tầng SQL.
  - [x] Giới hạn lượt theo phiên/IP; nút báo sai → `danh_gia_cau_tra_loi`.
  - [x] Bộ câu hỏi đánh giá (spec 07 mục 8) chạy được bằng lệnh riêng; test tự động dùng client giả.
- **Giao diện:**
  - [x] Widget chat nổi trên mọi trang cửa hàng, hiển thị stream, thẻ sản phẩm, nút "Gặp dược sĩ", nút báo sai.
- **Ghi chú triển khai:** `ai/chatbot.py` (AI02, AI03, 6 tool, `chay_luot`), `ai/dau_hieu.py`, `ai/prompts/`, `modules/tu_van/`, `ai/danh_gia.py` + `tests/ai/bo_cau_hoi.yaml` (40 câu); `core/db.lay_tao_phien` cho SSE; API spec 06 mục 3.41; QĐ-44. Giao diện `WidgetChat` trên mọi trang cửa hàng (stream, thẻ sản phẩm, báo sai; nút "Gặp dược sĩ" nối ở T7.4). Test `tests/ai/test_chatbot.py` (17), `test_danh_gia.py` (3), `WidgetChat.test.tsx`, `sse.test.ts`. CHƯA chạy được với Claude thật; nhóm cần chạy `python -m app.ai.danh_gia` để đo hai nhóm bắt buộc 100%.

### [x] T7.4 · Chuyển dược sĩ và chat trực tiếp
- **Chức năng:** AI04 (Tóm tắt, chuyển dược sĩ), KTV12 (Chat trực tiếp với dược sĩ), DS06 (Tư vấn trực tiếp)
- **Phụ thuộc:** T7.3
- **Bảng:** `hoi_thoai`, `tin_nhan`
- **Tiêu chí chấp nhận:**
  - [x] AI04: tóm tắt hội thoại (`goi_json`) khi chuyển; trong giờ làm việc → `cho_duoc_si`, ngoài giờ → `cho_goi_lai` + SĐT.
  - [x] WebSocket `/api/v1/tu-van/ws` cho khách và dược sĩ (xác thực bằng token, chỉ thành viên phiên mới vào được); dược sĩ nhận phiên → `duoc_si_dang_xu_ly`.
  - [x] HT08 đóng phiên không hoạt động.
- **Giao diện:**
  - [x] Hàng chờ chat và cửa sổ chat cho dược sĩ; widget chat chuyển chế độ "đang chat với dược sĩ".
- **Ghi chú triển khai:** `ai/tom_tat.py` (AI04, dự phòng theo luật), `modules/tu_van/{chuyen_duoc_si,hub,ws,router_noi_bo}.py`, `POST /tu-van/gap-duoc-si`, WebSocket `/tu-van/ws`, `/noi-bo/tu-van/*` (5 route vào registry phân quyền); HT08 đóng phiên không hoạt động nằm trong `tu_hoan_tat`. API spec 06 mục 3.42; QĐ-45. Giao diện: `lib/phongChat.ts` (hook WebSocket), `khu/nhan-vien/tu-van/TrangTuVan.tsx` (hàng chờ + chat), nút "Gặp dược sĩ" và chế độ chat trực tiếp trong `WidgetChat`; Vite proxy bật `ws`. Test `tests/ai/test_chuyen_duoc_si.py` (11), `phongChat.test.tsx`, `TrangTuVan.test.tsx`, `WidgetChat.test.tsx`. Hub một process (xem QĐ-45).

### [x] T7.5 · Tra cứu thuốc bằng ảnh
- **Chức năng:** KVL06 (Tra cứu thuốc bằng ảnh), AI05 (Nhận diện hộp thuốc từ ảnh)
- **Phụ thuộc:** T7.1
- **Bảng:** `san_pham`, `thong_tin_chuyen_mon`
- **Tiêu chí chấp nhận:**
  - [x] `POST /api/v1/tra-cuu-anh`: ảnh base64 → `goi_json` trích tên, hoạt chất, hàm lượng, SĐK; khớp theo SĐK rồi tên (trigram); không khớp → trả thông tin đọc được + cảnh báo "chưa xác minh".
  - [x] Giới hạn kích thước ảnh (≤ 5 MB, tự thu nhỏ cạnh dài ≤ 1568 px), giới hạn lượt.
- **Giao diện:**
  - [x] Nút chụp ảnh tra cứu trên thanh tìm kiếm (mobile).
- **Ghi chú triển khai:** `ai/anh.py` (Pillow, dùng lại cho T7.6), `ai/doc_anh.py` + `ai/prompts/doc_anh_hop_thuoc.md` (AI05), `modules/tra_cuu_anh/{dich_vu,router,schemas}.py`, API spec 06 mục 3.43, QĐ-46. LỆCH spec: ảnh gửi bằng multipart thay vì base64 (QĐ-46); chi phí lượt tra ảnh chưa cộng vào ngân sách ngày của chat. Giao diện `/tra-cuu-anh` (chụp/chọn ảnh, xem trước, kết quả, cảnh báo) và nút máy ảnh cạnh ô tìm kiếm. Test `tests/ai/test_tra_cuu_anh.py` (20), `TrangTraCuuAnh.test.tsx`. CHƯA thử với ảnh hộp thuốc thật và Claude thật.

### [x] T7.6 · Đọc ảnh đơn thuốc hỗ trợ dược sĩ
- **Chức năng:** AI06 (Đọc ảnh đơn thuốc)
- **Phụ thuộc:** T7.1, T5.3
- **Bảng:** `yeu_cau_don_thuoc`, `ct_yeu_cau_don_thuoc`
- **Tiêu chí chấp nhận:**
  - [x] Khi yêu cầu đơn thuốc được tạo: job đọc ảnh → `ket_qua_ai`, `ct_yeu_cau_don_thuoc` (tên trên đơn, hàm lượng, số lượng kê, `do_tin_cay_ai`, gợi ý `san_pham_id`).
  - [x] Màn duyệt DS04 hiển thị gợi ý kèm độ tin cậy, dược sĩ sửa/xác nhận (`do_duoc_si_nhap`). AI không tự duyệt.
- **Ghi chú triển khai:** `ai/doc_don_thuoc.py` + `ai/prompts/doc_don_thuoc.md` (AI06), `modules/don_thuoc/doc_anh_ai.py` (job `ai06_doc_don_thuoc` mỗi phút, gợi ý `san_pham_id`), `duyet.luu_thuoc_tren_don` + `PUT /noi-bo/don-thuoc/{id}/thuoc-tren-don` (vào registry phân quyền). API spec 06 mục 3.44; QĐ-47. Giao diện `ThuocTrenDon.tsx` trong màn DS04 (độ tin cậy, sửa/thêm/xóa dòng, nút tìm sản phẩm, lưu). Test `tests/ai/test_doc_don_thuoc.py` (13), `ThuocTrenDon.test.tsx` (11). CHƯA thử với ảnh đơn thuốc thật và Claude thật. LƯU Ý: `tao_don` vẫn nhận dòng sản phẩm do dược sĩ chọn ở DS05, không tự lấy từ gợi ý AI.

### [x] T7.7 · Gợi ý sản phẩm và mua kèm
- **Chức năng:** AI07 (Gợi ý sản phẩm tương tự, dành cho bạn), AI08 (Gợi ý mua kèm)
- **Phụ thuộc:** T7.1, T4.9
- **Bảng:** `san_pham`, `thanh_phan`, `lich_su_xem`, `di_ung`, `luat_mua_kem`, `ct_don_hang`
- **Tiêu chí chấp nhận:**
  - [x] AI07: sản phẩm tương tự (cùng hoạt chất → cùng danh mục → gần vector), "dành cho bạn" theo `lich_su_xem`; loại thuốc kê đơn và hoạt chất dị ứng.
  - [x] AI08 job hằng tuần: luật kết hợp từ `ct_don_hang` đơn `hoan_tat` 180 ngày (support ≥ 0.005, confidence ≥ 0.1, lift > 1), ghi đè `luat_mua_kem`.
- **Ghi chú triển khai:** `cua_hang/goi_y.py` (AI07: `san_pham_tuong_tu` thay bản trong `chi_tiet.py`, `danh_cho_ban`), `cua_hang/loc_an_toan.py` (bộ lọc kê đơn/dị ứng chuyển từ `ai/chatbot.py`), `gio_hang/luat_mua_kem.py` + job `ai08_luat_mua_kem` (Chủ nhật 03:00, `LICH_TUAN`), `GET /goi-y/danh-cho-ban`. API spec 06 mục 3.45; QĐ-48. Giao diện: khu "Dành cho bạn" ở trang chủ (ẩn khi rỗng). LỆCH nhỏ: "tương tự" đổi từ "chung một hoạt chất" sang đúng spec (cùng TẬP hoạt chất), test T1.3 đã cập nhật. Test `tests/ai/test_goi_y.py` (13), `TrangChu.test.tsx`.

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

- [ ] (T0.5) `QUYEN_YAML` nằm ngoài `backend/` (`docs/spec/data/quyen.yaml`): khi đóng image Docker ở T8.3 nếu chỉ copy `backend/` thì `python -m app.seed` lỗi `FileNotFoundError`. Khi đóng gói, copy file này vào image hoặc đặt đường dẫn qua biến môi trường.
- [ ] (T1.3) Admin duy nhất quên mật khẩu thì không có đường khôi phục (nhân viên không có "quên mật khẩu" tự phục vụ, Admin khác đặt lại ở T1.4): thêm lệnh CLI `python -m app.seed --dat-lai-admin` hoặc tương đương khi làm T1.4/T8.3.
- [ ] (T1.3) `nhat_ky_he_thong` "chỉ INSERT" mới được bảo đảm bằng việc ứng dụng không có route sửa/xóa; thêm trigger chặn UPDATE/DELETE ở DB qua migration mới (`/doi-schema`) khi rà soát bảo mật T8.2.
- [x] (T1.3-rv) `core/nhat_ky.py::che_du_lieu_nhay_cam` còn thiếu khóa `dang_mang_thai`, `dang_cho_con_bu`, `nam_sinh`, `ghi_chu` (của `di_ung`), `hoat_chat_id`, `thong_tin_nhan_hoan`; và `ghi_nhat_ky` nên bỏ hẳn giá trị cũ/mới khi `bang` là `ho_so_suc_khoe`/`di_ung` (spec 03 mục 5.1 chỉ ghi `bang` + `ban_ghi_id`). Chưa có nơi gọi nên chưa rò; làm trước task đầu tiên ghi nhật ký dữ liệu sức khỏe (T4.x/T5.x). **Đã xử lý ở T1.6** (QĐ-15): bảng sức khỏe bỏ giá trị lúc ghi và che lúc đọc; thêm `dang_mang_thai`, `dang_cho_con_bu`, `nam_sinh`, `thong_tin_nhan_hoan` vào danh sách che.
- [ ] (T1.6-rv, Thấp) `cau_hinh_service.cap_nhat` so `cu == moi` bằng `==` của Python nên không sửa được giá trị sai kiểu đã nằm sẵn trong DB do ghi ngoài AD08 (`90.0` so với `90`, `true` so với `1`: `PUT 90` trả 200 mà DB vẫn `90.0`). Đổi sang `dau_van_tay(cu) == dau_van_tay(moi)` (phân biệt hai trường hợp này); thêm test.
- [ ] (T1.6-rv, Thấp) Phòng thủ nhật ký cho dữ liệu sức khỏe chưa kín với người gọi tương lai (hiện 15 chỗ gọi `ghi_nhat_ky` đều không ghi dữ liệu sức khỏe): (a) nhận diện bảng sức khỏe bằng khớp chuỗi chính xác, nên chuẩn hóa tên bảng (`strip().lower()`) và coi mọi bảng có `suc_khoe` hay `di_ung` là bảng sức khỏe; (b) `ban_ghi_id` của bảng sức khỏe phải là id khách (chuỗi số, spec 03 mục 5.1), nếu không `di_ung` với khóa kép `khach:hoat_chat` làm AD15 hiện hoạt chất dị ứng; che `ban_ghi_id` khi đọc nếu không phải số; (c) thêm vào `DOAN_KHOA_NHAY_CAM` các khóa còn thiếu (`matKhau`, `pwd`, `passwd`, `authorization`, `api_key`, `ma_phien`, `so_tai_khoan`, `ngan_hang`, `stk`, `tien_su_benh`, `chan_doan`, `ghi_chu` của dị ứng); (d) `che_du_lieu_nhay_cam` đệ quy không giới hạn độ sâu (JSON 2000 tầng gây `RecursionError`); (e) thêm test quét mọi lời gọi `ghi_nhat_ky(` trong `app/` hoặc cho mỗi bảng ghi nhật ký danh sách trường được phép. Làm trước task đầu tiên ghi nhật ký cho dữ liệu sức khỏe (T4.x/T5.x).
- [ ] (T2.3, T4.x) **Nơi dùng `kiem_tra_tuong_tac` và `kiem_tra_di_ung`** (`modules/chuyen_mon/canh_bao.py`): DS04/DS05 (duyệt đơn thuốc, mức `nghiem_trong`/`chong_chi_dinh` bắt buộc ghi chú tư vấn, spec 04 mục 6), DS07/DS08 (tạo đơn hộ, POS), cảnh báo trong giỏ hàng cho khách và lọc gợi ý của AI. Hàm chỉ trả cảnh báo; người gọi quyết định ai được thấy (khách của mình, dược sĩ qua `duoc_doc_ho_so_suc_khoe`). Mỗi nơi thêm test "không lộ `ghi_chu` dị ứng" như `test_canh_bao_di_ung_khong_lo_ghi_chu_hay_ho_so_suc_khoe`.
- [ ] (T2.6) **T3.2 (job nền):** dọn ảnh mồ côi trong `luu_tru/cong_khai/banner/` và `bai-viet/` (ảnh được tải lên trước khi lưu form nên bỏ dở form là để lại tệp): so với `banner.anh_url` và `bai_viet.anh_bia_url`, chỉ xóa tệp quá 24 giờ không được tham chiếu.
- [ ] (T2.6, Thấp) **Sửa nhỏ không cần duyệt lại:** hiện sửa bất kỳ chữ nào của bài sức khỏe đang đăng cũng ẩn bài tới khi dược sĩ duyệt lại (QĐ-21). Nếu thực tế gây phiền, thêm cờ "sửa nhỏ" do DƯỢC SĨ (không phải Admin) đặt khi duyệt, ghi QĐ.
- [ ] (T2.6, T7.x) Đồng bộ kho tri thức AI: chỉ bài `da_duyet` có `dua_vao_ai = true` (bài sức khỏe đã qua dược sĩ); bài bị sửa về `nhap` hoặc gỡ `luu_tru` phải bị gỡ khỏi kho tri thức trong lần đồng bộ kế (T7.1).
- [ ] (T2.5-rv, Thấp) **T3.2 (job nền) và triển khai:** (1) job dọn `lich_su_tim_kiem` và `lich_su_xem` theo thời hạn lưu (mỗi IP ghi được tối đa ~17 nghìn dòng/ngày dù có giới hạn); (2) kiểm cấu hình IP khách khi chạy sau reverse proxy (`request.client.host` là IP của proxy thì mọi khách chung hạn mức ghi lịch sử, gợi ý và OTP: dùng `--proxy-headers`/`X-Forwarded-For` có danh sách tin cậy ở T8.3); (3) KTV01/AD02 xóa tài khoản khách phải ẩn danh hoặc xóa `lich_su_tim_kiem` và `lich_su_xem` của khách (từ khóa tìm có thể gợi ý bệnh).
- [x] (T2.3-rv, Thấp) **T2.6 (AD07, soạn bài):** duyệt bài viết hiện không gắn với nội dung dược sĩ đã xem (đã làm ở T2.6: body `{phien_ban}`). Khi Admin được sửa bài `nhap`, `POST /noi-bo/bai-viet-cho-duyet/{id}/duyet` phải nhận dấu vân tay nội dung (hoặc `updated_at`) mà `GET` trả về và trả `409 DU_LIEU_DA_THAY_DOI` nếu lệch; nếu không, dược sĩ duyệt bản Admin vừa sửa mà chưa đọc.
- [ ] (T2.3-rv, Thấp) **T4.x, T5.x:** `canh_bao.kiem_tra_di_ung(khach_hang_id, ...)` không tự kiểm quyền (chỉ trả tên hoạt chất, không `ghi_chu`, không log). Route dược sĩ nào gọi nó phải gọi cổng `duoc_doc_ho_so_suc_khoe` trước và có test khẳng định; route của khách chỉ lấy `khach_hang_id` từ token; Admin và kho không được gọi.
- [ ] (T2.4) **T4.1 (giỏ hàng)** nối nút "Thêm vào giỏ" vào `KhuMuaHang` ở `TrangChiTietSanPham.tsx` (đang khóa, kèm Tooltip) và nút trên thẻ nếu có; dịch vụ giỏ phải TỰ chặn thuốc kê đơn ở service/SQL (quy tắc 6), không dựa vào việc giao diện không có nút. Hiển thị thêm `so_luong_toi_da_moi_don` theo đơn vị.
- [ ] (T2.4) **T2.5 (tìm kiếm)** phải dùng cùng `modules/cua_hang/hien_thi.py` (`nap_cay_hien_thi`, `la_hien_thi`) để kết quả không lộ sản phẩm trong nhánh ẩn, và dùng lại `dung_the` cho thẻ kết quả (thuốc kê đơn hiện nhãn "Cần tư vấn").
- [ ] (T2.4, Thấp) Khu "Bán chạy" của trang chủ trống cho tới khi có đơn thật (seed mẫu không tạo đơn vì đơn chỉ đi qua `chuyen_trang_thai`); làm dữ liệu mẫu đơn khi T4.x xong để demo.
- [ ] (T2.4-rv, Thấp) **`/doi-schema`:** thêm index `lich_su_xem(ma_phien, san_pham_id, created_at)`: truy vấn chống trùng của khách vãng lai lọc theo `ma_phien` mà chỉ có index `(khach_hang_id, created_at)` và `(san_pham_id)`, nên mỗi lượt xem quét mọi dòng của sản phẩm (đo 50.000 dòng/sản phẩm: ~20 ms mỗi lượt, tăng tuyến tính).
- [ ] (T2.4, Thấp) `lich_su_xem` không có job dọn: bảng chỉ lớn lên (mỗi khách/phiên một dòng mỗi 30 phút mỗi sản phẩm). Thêm vào job HT dọn dữ liệu cũ (T3.2) với thời hạn giữ (ví dụ 12 tháng) và ghi vào QĐ.
- [ ] (T2.3, Thấp) "Mỗi sản phẩm tối đa một bản `da_duyet`" chỉ được bảo đảm ở service (khóa dòng sản phẩm). Thêm partial unique `thong_tin_chuyen_mon (san_pham_id) WHERE trang_thai = 'da_duyet'` qua `/doi-schema` để DB cũng từ chối (nhập tay hay job sau này không phá được quy tắc).
- [ ] (T2.3, **cần người xác nhận**) Dược sĩ soạn có thể tự duyệt bản của mình (QĐ-18). Nếu cần kiểm tra chéo, thêm điều kiện `nguoi_soan_id != actor.id` vào `noi_dung.duyet` (và dòng ở spec 03 mục 7); khi chỉ có một dược sĩ thì không đăng được nội dung nào.
- [ ] (T2.2) **Mọi hàm TĂNG tồn mới ở T3.1/T4.x (phiếu nhập, hoàn nhập đổi trả, điều chỉnh tăng, ra khỏi biệt trữ) phải gọi `ton_kho.kiem_tra_san_pham_chua_xoa(db, lo)` sau khi khóa lô** (đã có cho `nhap_kho`; xóa sản phẩm khóa lô `FOR UPDATE` rồi mới đếm, QĐ-17). Phiếu nhập tạo lô mới cũng nên kiểm sản phẩm chưa xóa ở service; thêm test đồng thời cho từng hàm tăng tồn mới theo mẫu `test_xoa_san_pham_dua_voi_nhap_kho_vao_lo_san_co...` ở `tests/san_pham/test_sp_san_pham.py`.
- [x] (T2.2, T2.4) Danh sách sản phẩm NỔI BẬT của trang chủ phải lọc thêm `loai_san_pham <> 'thuoc_ke_don'` ở truy vấn: DB không có ràng buộc "kê đơn thì không nổi bật" (chỉ service AD04 chặn), nên dòng nhập ngoài API có thể làm lộ thuốc kê đơn ở khu quảng bá (CLAUDE.md quy tắc 6).
- [x] (T2.2) **T2.3 làm endpoint nội dung chuyên môn cho dược sĩ** (quyền riêng, Admin chỉ xem): AD04 từ chối trường lạ nên Admin không có đường vòng, nhưng chỉ khi T2.3 có endpoint thì tiêu chí "endpoint chuyên môn yêu cầu quyền của dược sĩ" mới đủ. *Xong ở T2.3 (`/noi-bo/chuyen-mon`, `content.professional.edit` + `dam_bao_la_duoc_si`).*
- [ ] (T2.2) T7.x (banner, bài viết): làm endpoint upload riêng cùng khuôn `san_pham_anh.py` (magic bytes, 5 MB, ghi tệp rồi dọn nếu rollback, xóa tệp sau commit) với `cms.manage`, dùng lại `core/luu_tru.py` và `GET /api/v1/tep/...`.
- [ ] (T2.2) **T8.3 (nginx):** thêm `client_max_body_size 6m` cho `POST .../anh` làm lớp ngoài (middleware `GioiHanKichThuocThan` đã chặn ở ứng dụng, nhưng nginx từ chối trước khi tới uvicorn); và lệnh/job dọn tệp công khai không còn bản ghi tham chiếu (tiến trình chết giữa lúc ghi tệp và commit để lại tệp mồ côi, hook chỉ dọn khi giao dịch hủy trong cùng process; `_xoa_dong_bo` đã log cảnh báo khi không xóa được).
- [ ] (T2.2) Danh sách `ChonDuLieuChung` chỉ lấy 20 kết quả đầu theo từ khóa; thương hiệu có tên gần giống nhau ở đầu bảng chữ cái vẫn tìm được bằng cách gõ thêm. Nếu cần chọn nhanh theo tần suất dùng thì thêm sắp xếp `so_san_pham` giảm dần vào ô chọn.
- [ ] (T2.2) `TrangCauHinh.tsx` còn dùng `<Space direction="vertical">` (antd 6 cảnh báo `direction` đã lỗi thời, dùng `orientation`); đổi hai chỗ khi đụng vào file.
- [x] (T2.1) **T2.2 phải khóa dòng danh mục khi gán cho sản phẩm:** `SELECT ... FROM danh_muc WHERE id = ? AND deleted_at IS NULL FOR SHARE` rồi mới ghi `danh_muc_id` (tạo và đổi danh mục của sản phẩm), nếu không có thể gắn sản phẩm vào danh mục vừa bị xóa mềm (QĐ-16). *Xong ở T2.2 (`_gan_danh_muc`, test đồng thời cả hai chiều).*
- [x] (T2.1) **T2.4** phải lọc danh sách công khai theo `dang_hien_thi` của danh mục VÀ mọi tổ tiên (QĐ-16).
- [ ] (T2.1) `core/tham_so.tu_khoa_tim` (tham số `q` chặn NUL) mới áp cho AD05; áp tiếp cho `q` của AD01, AD02 và mọi danh sách mới (xử lý luôn mục T1.5-rv về NUL bên dưới).
- [ ] (T2.1) Hoạt chất hiện không có thao tác gỡ (chặn kênh dò dị ứng, QĐ-16). Nếu cần gỡ hoạt chất nhập nhầm: thêm cột cờ "ngừng dùng" cho `hoat_chat` qua `/doi-schema` (ẩn khỏi bộ chọn của form sản phẩm, vẫn giữ trong `di_ung` và `thanh_phan` đã có); không bao giờ cho xóa cứng vì kết quả lộ dị ứng của khách.
- [ ] (T2.1) Kiểm tra ký tự điều khiển, vô hình và surrogate đơn lẻ (`core/kieu_du_lieu.py`) mới áp cho AD03 và AD05: các schema nhập chuỗi của AD01 (họ tên, email, ghi chú), AD02 (`ly_do` khóa), AD08, bộ lọc nhật ký có thể còn 500 với `"\ud800"`; dùng chung `kieu_ten`/`van_ban_tuy_chon` khi làm lại các schema đó.
- [ ] (T1.6-rv, Thấp, **cần người quyết định**) Spec 05 mục AD08 liệt kê "mức tồn tối thiểu" là một cấu hình hệ thống, nhưng spec 02 mục 6 và `core/cau_hinh_khoa.py` không có khóa này; thực tế `ton_toi_thieu` là cột theo từng sản phẩm (`san_pham`, AD04/KHO06). Chọn một: sửa mô tả AD08 (bỏ "mức tồn tối thiểu", vì đã cấu hình theo sản phẩm) hoặc thêm khóa mặc định `ton_toi_thieu_mac_dinh` cho sản phẩm chưa đặt. Ghi quyết định vào `12-quyet-dinh.md` (CLAUDE.md: spec mơ hồ thì hỏi, không tự đoán). Hiện chưa làm gì để không đoán.
- [ ] (T1.6-rv, Thấp) Giao diện/biên nhỏ: ô lọc "Người thực hiện" của nhật ký chỉ nạp 100 nhân viên chưa xóa (không lọc được theo nhân viên đã xóa mềm hay quá 100 người: dùng ô tìm có tìm phía máy chủ); `PUT /noi-bo/cau-hinh/{khoa}` với đối tượng 50.000 khóa thừa trả phản hồi lỗi khoảng 3 MB vì liệt kê hết các trường thừa (giới hạn số lỗi trả về); số nguyên 5000 chữ số hay JSON lồng 100.000 tầng trả 400 `LOI_HTTP` thay vì `DU_LIEU_KHONG_HOP_LE`. Ngoài ra khoảng giá trị chưa có ràng buộc chéo: `so_lan_dang_nhap_sai_toi_da = 20` cùng `thoi_gian_khoa_dang_nhap_phut = 1` cho phép khoảng 28.800 lần thử mỗi ngày mỗi tài khoản, và `nguong_can_han_ngay` có thể lớn hơn `han_su_dung_toi_thieu_nhap_ngay` (lô vừa nhập đã cận hạn mà không có cảnh báo nhập); nếu muốn chặt hơn thì sửa bảng ở spec 02 mục 6 trước.
- [ ] (T1.6) `GET /noi-bo/nhat-ky` sắp theo `created_at` giảm dần và đếm tổng trên cả bảng; index hiện có là `(bang, ban_ghi_id)` và `(nhan_vien_id, created_at)` nên truy vấn chỉ lọc theo khoảng ngày hoặc `hanh_dong` (và `SELECT DISTINCT` của `gia-tri-loc` cho `hanh_dong`) sẽ quét cả bảng khi nhật ký lớn. Đo khi có dữ liệu thật, thêm index `(created_at)` và `(hanh_dong, created_at)` qua `/doi-schema`, hoặc đếm gần đúng.
- [ ] (T1.5) Trang Nhân viên (AD01) chưa có cột bấm để sắp xếp dù `GET /noi-bo/nhan-vien` đã hỗ trợ `sap_xep` (`created_at`, `ma_nhan_vien`, `ho_ten`, `email`): làm giống `TrangKhachHang.tsx` (sorter trên cột, `sap_xep` trên URL, bỏ giá trị lạ), nhớ chỉ xử lý `Table.onChange` khi `extra.action === 'sort'` (nếu không nút chuyển trang bị vô hiệu, lỗi M1 của T1.5).
- [ ] (T1.5-rv, Thấp) Ký tự NUL (`\u0000`) trong `q` (`GET /noi-bo/khach-hang?q=a%00b`, `GET /noi-bo/nhan-vien?q=a%00b`) hay `ly_do` khóa khách gây 500 thay vì 400 (asyncpg/JSONB từ chối byte 0x00). Thêm kiểu `Query` dùng chung có `pattern=r"^[^\x00]*$"` cho `q` ở AD01 và AD02, và validator cấm ký tự điều khiển cho `KhoaKhachYeuCau.ly_do`; thêm test.
- [ ] (T1.5-rv, Thấp) Chặn hẳn access token cũ sau khi khóa rồi mở khóa nhanh: thêm mốc "token hợp lệ từ" (cột mới ở `khach_hang`/`nhan_vien`, qua `/doi-schema`) và so `iat` của token ở guard; đồng thời xử lý cho đổi/đặt lại mật khẩu (QĐ-12). Làm khi rà soát bảo mật T8.2.
- [ ] (T1.5-rv, Thấp) `schemas_quan_tri_khach.DonHangCuaKhach.tong_tien: Tien` làm cả trang lịch sử mua trả 500 nếu một đơn có tiền lẻ đồng (`Tien` chỉ nhận số đồng nguyên, còn CHECK ở DB cho phép `NUMERIC(16,2)`). Hiện không code nào tạo đơn lẻ đồng nên là gia cố: dùng kiểu xuất không validate (chỉ `PlainSerializer`) cho model đọc, hoặc bắt lỗi theo từng dòng. *(T2.2 đã thêm `core.tien.TienDoc` cho schema ĐỌC: đổi sang kiểu đó là xong.)*
- [ ] (T1.5-rv, Thấp) Giao diện AD02: (a) ô tìm kiếm chưa có `maxLength=100` và `?trang=2.5` trên URL bị API từ chối 400 rồi trang báo lỗi chung "Không tải được danh sách" (nên chuẩn hóa tham số URL trước khi gửi); (b) `dangKhoaTam` so `khoa_den` với đồng hồ trình duyệt nên máy Admin chạy chậm vẫn hiện "Khóa tạm" và mất nút Khóa (dùng thời gian máy chủ hoặc chỉ dựa vào `trang_thai`).
- [ ] (T1.4-rv, Thấp) `quan_tri.py`: người thực hiện chỉ được kiểm tra ở dependency, TRƯỚC khi chờ khóa dòng. Admin B đang chờ khóa trong lúc Admin A commit khóa B vẫn thực hiện xong (đã chạy thử: B nhận mật khẩu tạm). Thêm dòng người thực hiện vào tập khóa và kiểm tra lại `hoat_dong`, chưa xóa, còn ADMIN sau khi có khóa (khi đó người thua nhận 403 thay vì `PHAI_CON_ADMIN`, cập nhật test đồng thời).
- [ ] (T1.4-rv, Thấp) `quan_tri.dat_lai_mat_khau` băm Argon2 khi đang giữ khóa mọi dòng Admin (vài chục đến vài trăm ms chặn đăng nhập, làm mới, thao tác Admin khác). Sinh và băm mật khẩu tạm trước khi gọi `_khoa_dich_va_cac_admin`.
- [ ] (T1.4-rv, Thấp) `TrangNhanVien.tsx` hộp thoại mật khẩu tạm: (a) đóng được bằng Esc hoặc nút X (spec 09 ghi "chỉ đóng bằng nút"): đặt `closable={false}` và `keyboard={false}`; (b) `await lamMoi()` chạy TRƯỚC `setMatKhauTam`, nên danh sách tải chậm/lỗi hoặc rời trang giữa chừng thì tài khoản đã tạo mà mật khẩu không bao giờ hiện: hiện mật khẩu trước, `void lamMoi()` sau; (c) `luu.data`/`hanhDong.data` giữ `mat_khau_tam` trong bộ nhớ (MutationCache `gcTime` 5 phút): gọi `reset()` sau khi đọc; (d) thêm `Cache-Control: no-store` cho phản hồi tạo/đặt lại và `field(repr=False)` cho `KetQuaCoMatKhauTam.mat_khau_tam`.
- [ ] (T1.4-rv, Thấp) `core/phan_quyen.py` cache quyền: còn cửa sổ hẹp một request đọc quyền cũ trước COMMIT của AD18 nhưng chỉ chạy tiếp sau hook `after_commit` thì ghi bản cũ vào cache 60 giây. Thêm bộ đếm thế hệ, chỉ ghi cache khi thế hệ không đổi so với lúc bắt đầu đọc. Kèm: `xoa_cache_quyen_sau_commit(db)` thiếu type hint cho `db`.
- [ ] (T1.4-rv, Thấp) `useDongBoPhienNoiBo` có thể áp bản `/noi-bo/toi` cũ (còn trong cache 30 giây) lên hồ sơ vừa sửa ở `/nhan-vien/tai-khoan` (trang này nằm ngoài `KhungNoiBo`): sau khi sửa hồ sơ, cập nhật hoặc vô hiệu hóa query `['noi-bo', 'toi']`. Chỉ ảnh hưởng hiển thị tên, quyền vẫn do backend quyết định.
- [ ] (T1.3-rv) `POST /noi-bo/thong-bao/{id}/da-doc` với id vượt int64 trả 500 thay vì 404 (asyncpg `value out of int64 range`). Kiểu dùng chung đã có ở `core/tham_so.py` (`IdInt`, `IdBigInt`, T1.4, đang dùng cho AD01): đổi `thong_bao_id: int` thành `IdBigInt` và áp cho mọi route `{id}` mới từ T1.5 trở đi.
- [ ] (T1.3-rv) PyJWT kiểm `exp` trước `aud`: token nội bộ hết hạn gửi tới route `khach_tuy_chon` bị trả `TOKEN_HET_HAN` (đáng lẽ coi là vãng lai), token khách hết hạn gửi tới `/noi-bo` cũng vậy (đáng lẽ `CHUA_DANG_NHAP`). Giải mã với `verify_exp=False`, kiểm `aud` rồi tự kiểm `exp` trong `giai_ma_access_token`.
- [ ] (T1.3-rv) `thong_bao.service.kiem_tra_lien_ket` chưa chặn ký tự điều khiển (`"/\t/evil.com"` thành `//evil.com` khi trình duyệt phân tích); frontend đã chặn nên chưa khai thác được, nhưng phía server cần tương đương `?tiep=` (QĐ-11).
- [ ] (T1.3-rv) Giới hạn theo IP (`core/gioi_han.py`, `phien_http.dia_chi_ip`): gom IPv6 theo /64 (mỗi địa chỉ trong một dải có bộ đếm riêng nên lách được) và cấu hình `--proxy-headers`/`forwarded-allow-ips` khi chạy sau nginx (T8.3), nếu không cả site dùng chung một bộ đếm theo IP của proxy.
- [ ] (T1.3-rv) `POST /auth/otp` với `kenh=email`: gửi email (chậm hơn) chỉ xảy ra với tài khoản có thật nên độ trễ phản hồi có thể lộ tài khoản; cân bằng thời gian hoặc đưa gửi tin nhắn vào tác vụ nền (T3.2/T6.x).
- [ ] (T1.3-rv) Mặc định thiên về dev: `TIN_NHAN_CHE_DO=gia` (OTP ghi vào log nếu quên đặt `that`), `.env.example` đặt `COOKIE_SECURE=false`; thêm chốt khi khởi động ở môi trường production và đưa vào checklist deploy (T8.2/T8.3).
- [ ] (T1.3-rv) Registry/ma trận phân quyền: `tests/phan_quyen/ma_tran.py` bỏ qua route không có `methods` (WebSocket `/tu-van/ws`, T6.x); các guard hiện nhận `Request` nên chưa dùng được cho WebSocket. Route thật chưa có ca bị chặn nào vì chỉ có `profile.self`: từ T3.1 trở đi mỗi route nội bộ mới tự đưa ca bị chặn vào ma trận.
- [ ] (T3.2) Job dọn ảnh mồ côi (banner, ảnh bìa bài viết, ảnh sản phẩm tải lên nhưng bản ghi không lưu): quét `storage/cong-khai`, xóa file không được bản ghi nào tham chiếu và cũ hơn 24 giờ.
- [ ] (T4.1) Khách thành viên chưa sửa được hồ sơ cá nhân (họ tên, email) và đổi mật khẩu trong trang tài khoản (KTV01): spec 06 chưa có `PATCH /toi` và `POST /toi/doi-mat-khau`; cần bổ sung spec rồi làm.
- [ ] (T4.1) Giỏ hàng dùng số tồn khả dụng chỉ để cảnh báo; chưa có test tranh chấp nhiều session cho `them_dong`/`gop_gio` cùng một giỏ (đã tuần tự hóa bằng khóa dòng `gio_hang`).
- **T4.3:** chưa có test đồng thời cho `dung_ma` (hai đơn cùng dùng lượt cuối); mới dựa vào khóa FOR UPDATE.
- **T4.4:** khóa Idempotency-Key nằm trong bộ nhớ tiến trình (mất khi khởi động lại, không dùng chung giữa nhiều tiến trình); đủ cho đồ án một tiến trình, cần bảng hoặc Redis nếu chạy nhiều worker.
- **T4.5:** hoàn tiền thật qua cổng: `hoan_tien` của VNPay/MoMo chưa cài (T6.3); kiểm lại tên trường và bảng mã với tài liệu VNPay/MoMo hiện hành khi chạy sandbox thật (QĐ-27) và ghi phiên bản API.

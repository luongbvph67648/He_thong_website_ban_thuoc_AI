# 01. Kiến trúc

## 1. Tổng thể
```mermaid
flowchart LR
  subgraph Trinh_duyet[Trình duyệt]
    CH[Khu cửa hàng /]
    NV[Khu nhân viên /nhan-vien]
    QT[Khu quản trị /quan-tri]
  end
  CH & NV & QT -->|REST /api/v1, SSE, WebSocket| API[FastAPI]
  API --> DB[(PostgreSQL 16\npgvector, unaccent, pg_trgm)]
  JOB[Worker APScheduler\nHT01-HT08, AI08, AI09, AD10] --> DB
  API --> AI[app/ai\nClaude API + BGE-M3]
  JOB --> AI
  API --> TH[app/tich_hop\nVNPay, MoMo, GHN, SMS, email, lưu file]
  VNPAY[(Cổng VNPay/MoMo)] -->|IPN| API
  GHN[(GHN)] -->|webhook| API
```
- **Một backend, ba khu giao diện.** Tách theo loại token (`aud = khach` hoặc `noi_bo`) và theo mã quyền.
- **Worker job nền** là process riêng, dùng chung code và CSDL với API.
- **Mọi dịch vụ ngoài** đi qua adapter trong `app/tich_hop/` hoặc `app/ai/`. Mỗi adapter có bản giả.

## 2. Cấu trúc thư mục
```
backend/
  pyproject.toml  uv.lock  alembic.ini  .env.example
  alembic/versions/            # 0001_nen.py, 0002_rang_buoc.py, ...
  scripts/so_sanh_schema.py    # so DB sau migration với ERD_da_chinh_sua.sql
  app/
    main.py                    # create_app(): router, middleware, handler lỗi, CORS
    core/                      # config, db, bao_mat (JWT, Argon2), phan_quyen, loi, tien,
                               # thoi_gian, phan_trang, nhat_ky, gioi_han (rate limit), luu_tru
    models/                    # enums, san_pham, kho, ban_hang, khach_hang, he_thong, ai
    modules/<module>/          # router_*.py, schemas.py, service.py, repo.py
    tich_hop/                  # thanh_toan/, van_chuyen/, tin_nhan/ (base + that + gia)
    ai/                        # claude, gia_lap, embedding, tri_thuc, tim_kiem, chatbot,
                               # doc_anh, goi_y, du_bao, an_toan, prompts/
    jobs/                      # __main__.py (lịch), ht01_lo.py ... ai09_du_bao.py
    seed/                      # __main__.py, du_lieu_mau/
  tests/                       # giống app/modules + phan_quyen/, bat_bien/
frontend/
  src/ (xem frontend/CLAUDE.md)
  e2e/                         # Playwright
docker-compose.yml
```

## 3. Module backend
| Module (`app/modules/`) | Bảng chính | Chức năng |
|---|---|---|
| `tai_khoan` | khach_hang, nhan_vien, vai_tro, quyen, vai_tro_quyen, phien_dang_nhap, ma_otp, dia_chi | KVL09, KVL10, NV01, NV02, AD01, AD02, AD18, KTV01 |
| `suc_khoe` | ho_so_suc_khoe, di_ung | KTV11 + hàm cổng đọc dữ liệu sức khỏe |
| `san_pham` | danh_muc, thuong_hieu, nha_san_xuat, hoat_chat, san_pham, thanh_phan, don_vi_quy_doi, thong_tin_chuyen_mon, anh_san_pham, tuong_tac_hoat_chat | AD03, AD04, AD05, DS10, KVL01–KVL04 |
| `noi_dung` | banner, bai_viet | AD07, KVL11 |
| `kho` | nha_cung_cap, lo_thuoc, bien_dong_kho, phieu_nhap, phieu_kiem_ke, phieu_dieu_chinh, phieu_huy, phieu_xuat_tra (+ ct_*), lenh_thu_hoi, ct_lenh_thu_hoi | KHO01, KHO02, KHO05–KHO09, KHO11–KHO13, AD12, AD13, DS13, HT01, HT02 |
| `ban_hang` | gio_hang, ct_gio_hang, don_hang, ct_don_hang, phan_bo_lo, lich_su_trang_thai, thanh_toan, van_don, khuyen_mai, khuyen_mai_pham_vi, ma_giam_gia | KVL07, KTV02–KTV06, KTV08, DS01–DS03, DS07, DS08, DS15, KHO03, KHO04, AD06, AD17, HT03–HT06, HT08 |
| `don_thuoc` | yeu_cau_don_thuoc, ct_yeu_cau_don_thuoc | KVL08, KTV07, DS04, DS05 |
| `sau_ban` | yeu_cau_doi_tra, ct_yeu_cau_doi_tra, danh_gia, hoi_dap | KTV09, KTV10, KTV15, DS09, DS11, KHO10 |
| `he_thong` | cau_hinh, nhat_ky_he_thong, thong_bao | AD08, AD15, KTV13, HT07, KTV14 |
| `tu_van` | hoi_thoai, tin_nhan, danh_gia_cau_tra_loi | KVL05, KTV12, DS06, DS12, AD11 |
| `bao_cao` | (chỉ đọc nhiều bảng) | AD14, AD16, DS14 |
| `app/ai` (không phải module route) | tai_lieu_tri_thuc, lich_su_tim_kiem, lich_su_xem, luat_mua_kem, de_xuat_nhap_hang | AI01–AI09, AD09, AD10, KVL06, KHO14 |

**Quy tắc phụ thuộc giữa các module:**
- `ban_hang`, `don_thuoc` và `sau_ban` được gọi `kho.ton_kho`.
- Mọi module được gọi `he_thong.thong_bao` và `core.nhat_ky`.
- Không module nào ghi thẳng vào bảng của module khác.

## 4. Thành phần dùng chung
| Thành phần | Vị trí | Ghi chú |
|---|---|---|
| Cấu hình | `core/config.py` | `Settings` (pydantic-settings) đọc `.env`; truy cập qua `settings` |
| Phiên DB | `core/db.py` | Alias `Db`: mỗi request một session + một transaction, commit **trước** khi gửi response, rollback khi lỗi; cấm `commit()`/`rollback()` tay |
| Tiền và thời gian | `core/tien.py`, `core/thoi_gian.py` | `lam_tron_vnd`, `cong`, `tru`, kiểu `Tien`; `bay_gio_utc`, `hom_nay_vn` |
| Phân trang | `core/phan_trang.py` | `PhanTrang`, `Trang[T]`, `lay_trang` (spec 06 mục 5) |
| Log và request id | `core/log.py`, `core/middleware.py` | Log JSON có `request_id`; header `X-Request-ID`; log truy cập mỗi request (không ghi query string) |
| Bảo mật | `core/bao_mat.py` | Argon2 (argon2-cffi), JWT (PyJWT, HS256), hash refresh token bằng SHA-256 |
| Phân quyền | `core/phan_quyen.py` | `khach_hien_tai`, `khach_tuy_chon`, `nhan_vien_hien_tai`, `yeu_cau_quyen` (spec 03) |
| Lỗi | `core/loi.py` | `LoiNghiepVu` + handler (spec 06 mục 4) |
| Nhật ký | `core/nhat_ky.py` | `ghi_nhat_ky(db, nhan_vien, hanh_dong, bang, ban_ghi_id, cu, moi, ip)` |
| Máy trạng thái | `modules/ban_hang/trang_thai.py` | HT06, bảng chuyển ở spec 04 mục 1.1 |
| Tồn kho | `modules/kho/ton_kho.py` | Nơi duy nhất đổi tồn (spec 04 mục 3) |
| Thông báo | `modules/he_thong/thong_bao.py` | Ghi `thong_bao` + email/SMS qua adapter |
| Lưu file | `core/luu_tru.py` | Công khai (ảnh sản phẩm) và riêng tư (ảnh đơn thuốc, ảnh đổi trả); URL ký có hạn (spec 08 mục 6) |
| Giới hạn tần suất | `core/gioi_han.py` | slowapi, bộ nhớ trong process; khóa theo IP, phiên, SĐT |
| Job nền | `app/jobs/` | APScheduler `AsyncIOScheduler`, advisory lock theo job |
| AI | `app/ai/` | Spec 07; mọi lời gọi Claude qua `ai/claude.py` |

## 5. Biến môi trường (`backend/.env.example`)
| Biến | Ví dụ / mặc định | Ghi chú |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/nha_thuoc` | |
| `DATABASE_URL_TEST` | `postgresql+asyncpg://postgres:postgres@localhost:5432/nha_thuoc_test` | |
| `JWT_SECRET` | (chuỗi ngẫu nhiên ≥ 32 ký tự) | |
| `JWT_ACCESS_PHUT` | `15` | |
| `REFRESH_NGAY` | `14` | Hạn refresh token (ngày), tính từ lần làm mới gần nhất |
| `MOI_TRUONG` | `dev` | `dev` hoặc `production`; `production` từ chối khởi động khi còn cổng/vận chuyển/SMS giả, thiếu bí mật hoặc `COOKIE_SECURE=false` (QĐ-53) |
| `COOKIE_SECURE` | `true` | Cờ `Secure` của cookie refresh token; chỉ đặt `false` khi dev qua http |
| `FRONTEND_URL`, `CORS_ORIGINS` | `http://localhost:5173` | |
| `ADMIN_EMAIL`, `ADMIN_MAT_KHAU` | | Dùng cho seed Admin đầu tiên |
| `KHOA_MA_HOA` | (khóa Fernet) | Mã hóa `ho_so_suc_khoe.benh_nen` |
| `ANTHROPIC_API_KEY` | | Chỉ cần khi `AI_GIA_LAP=false` |
| `CLAUDE_MODEL` | `claude-opus-5-5` | |
| `AI_GIA_LAP` | `true` | `true` = dùng client giả (`ai/gia_lap.py`) |
| `AI_GIA_INPUT`, `AI_GIA_OUTPUT`, `AI_GIA_CACHE_READ` | `4`, `20`, `0.20` | USD / 1 triệu token của model đang dùng, để tính `hoi_thoai.chi_phi` |
| `AI_NGAN_SACH_NGAY_USD` | `2` | Vượt ngưỡng thì tạm tắt chat AI trong ngày |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | |
| `EMBEDDING_GIA_LAP` | `true` | `true` = vector giả xác định; `false` cần cài nhóm phụ thuộc `ai-local` |
| `THANH_TOAN_CHE_DO` | `gia` | `gia` hoặc `sandbox` |
| `VNPAY_TMN_CODE`, `VNPAY_HASH_SECRET`, `VNPAY_URL`, `VNPAY_RETURN_URL` | | Chế độ sandbox |
| `MOMO_PARTNER_CODE`, `MOMO_ACCESS_KEY`, `MOMO_SECRET_KEY`, `MOMO_ENDPOINT` | | Chế độ sandbox |
| `VAN_CHUYEN_CHE_DO` | `gia` | `gia` hoặc `ghn` |
| `GHN_TOKEN`, `GHN_SHOP_ID`, `GHN_URL`, `GHN_WEBHOOK_TOKEN` | | |
| `TIN_NHAN_CHE_DO` | `gia` | `gia` = log + Mailpit; `that` = nhà cung cấp SMS/SMTP |
| `SMTP_HOST`, `SMTP_PORT` | `localhost`, `1025` | Mailpit khi dev |
| `LUU_TRU_THU_MUC` | `./storage` | |

## 6. Chạy dev bằng docker-compose
`docker-compose.yml` chỉ chứa hạ tầng:
- **`db`:** image `pgvector/pgvector:pg16`, cổng 5432, volume `pgdata`, healthcheck `pg_isready`.
- **`mailpit`:** image `axllent/mailpit`, cổng 1025 (SMTP) và 8025 (giao diện xem mail).

Backend, worker và frontend chạy trực tiếp trên máy để reload nhanh (lệnh trong `CLAUDE.md`).

Bản deploy (T8.3) dùng `docker-compose.prod.yml`, thêm service `migrate` (chạy một lần), `api`, `worker` và `web` (nginx phục vụ bản build frontend và proxy `/api`, cấu hình ở `deploy/nginx.conf`). Biến môi trường `MOI_TRUONG` (dev | production) bật chốt cấu hình an toàn (QĐ-53).

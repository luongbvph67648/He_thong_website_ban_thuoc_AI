# 06. API

## 1. Nguyên tắc
- REST JSON, tiền tố `/api/v1`. Tên đường dẫn là tiếng Việt không dấu, nối bằng gạch ngang (`/don-hang`, `/phieu-nhap`).
- Tên trường JSON giữ đúng tên cột ERD (snake_case không dấu). Tiền trả về dạng **chuỗi số** (`"125000.00"`) để không mất chính xác. Frontend định dạng lại khi hiển thị.
- Thời gian trả về ISO 8601 có múi giờ UTC (`2026-10-15T03:00:00Z`). Ngày (HSD) trả về `YYYY-MM-DD`.
- Với khách, tài nguyên được định danh bằng mã (`ma_don`, `ma_yeu_cau`) thay vì `id`. Nội bộ được dùng `id`.
- OpenAPI tự sinh tại `/docs` và `/openapi.json`. Mỗi route có `summary` tiếng Việt kèm mã chức năng, ví dụ `"Xác nhận đơn hàng (DS02)"`.

## 2. Nhóm route
| Tiền tố | Ai gọi | Xác thực |
|---|---|---|
| `/api/v1/auth/*` | Khách | Đăng ký, đăng nhập, làm mới, đăng xuất, OTP, quên mật khẩu |
| `/api/v1/noi-bo/auth/*` | Nhân viên | Đăng nhập, làm mới, đăng xuất, đổi mật khẩu |
| `/api/v1/san-pham`, `/danh-muc`, `/tim-kiem`, `/bai-viet`, `/banner`, `/hoat-chat` | Công khai | `khach_tuy_chon` |
| `/api/v1/don-thuoc` (POST), `/api/v1/xac-nhan-don/{token}` | Khách vãng lai | OTP hoặc mã truy cập trong link |
| `/api/v1/tu-van/*` (chat SSE, WebSocket), `/api/v1/tra-cuu-anh` | Khách (cả vãng lai) | `khach_tuy_chon` + giới hạn tần suất |
| `/api/v1/toi/*` | Khách thành viên | `khach_hien_tai`; mọi dữ liệu lọc theo khách trong token |
| `/api/v1/noi-bo/*` | Nhân viên | `yeu_cau_quyen(...)` |
| `/api/v1/webhook/*` | VNPay, MoMo, GHN | Chữ ký hoặc token của đối tác (spec 08) |
| `/api/v1/health` | Hạ tầng | Không. Trả 200 `{"trang_thai": "ok", "db": "ok"}`; CSDL không truy vấn được thì 503 `{"trang_thai": "loi", "db": "loi"}` (không lộ chi tiết lỗi) |

**Ví dụ đường dẫn chuẩn:**
- Khách:
  - `GET /api/v1/toi/don-hang`
  - `GET /api/v1/toi/don-hang/{ma_don}`
  - `POST /api/v1/toi/don-hang/{ma_don}/huy`
- Nội bộ:
  - `GET /api/v1/noi-bo/don-hang?trang_thai=cho_xac_nhan`
  - `POST /api/v1/noi-bo/don-hang/{id}/xac-nhan`
  - `POST /api/v1/noi-bo/phieu-huy/{id}/duyet`
- Hành động nghiệp vụ dùng `POST /<tài nguyên>/{id}/<động từ>` (`/xac-nhan`, `/huy`, `/duyet`, `/tu-choi`, `/nhan-xu-ly`), không dùng `PATCH trang_thai`.

## 3. Xác thực
- **Access token:** JWT HS256.
  - Claim: `sub` (id), `aud` (`khach` | `noi_bo`), `exp` (15 phút), `jti`.
  - Gửi qua header `Authorization: Bearer <token>`.
  - Không lưu quyền trong token. Quyền đọc từ DB (spec 03 mục 8).
- **Refresh token:**
  - Chuỗi ngẫu nhiên 256 bit, đặt trong cookie `HttpOnly; Secure; SameSite=Lax`, `Path=/api/v1/auth` (khách) hoặc `/api/v1/noi-bo/auth` (nhân viên).
  - Lưu SHA-256 vào `phien_dang_nhap`.
  - Xoay vòng mỗi lần làm mới. Dùng lại một token đã thu hồi thì thu hồi toàn bộ phiên của tài khoản đó (phát hiện bị đánh cắp).
- **Mật khẩu:** Argon2id. Tối thiểu 8 ký tự, có chữ và số.
- **OTP:** 6 chữ số, lưu hash, hết hạn 5 phút, tối đa 5 lần thử.
  - `muc_dich`: `dang_ky`, `quen_mat_khau`, `don_thuoc_khach`.
  - Phản hồi giống nhau dù SĐT có tồn tại hay không, để chống dò tài khoản.

## 4. Định dạng phản hồi và lỗi
- **Thành công:** trả đối tượng hoặc trang dữ liệu (mục 5).
- **Lỗi:** luôn trả dạng:
  ```json
  {"ma_loi": "HET_HANG", "thong_diep": "Sản phẩm Paracetamol 500mg chỉ còn 3 viên", "chi_tiet": {"san_pham_id": 12, "con_lai": 3}}
  ```

**Mã lỗi dùng chung** (thêm mã mới vào bảng này khi tạo):

| HTTP | `ma_loi` | Khi nào |
|---|---|---|
| 400 | `DU_LIEU_KHONG_HOP_LE` | Validate thất bại; `chi_tiet` là danh sách `{truong, loi}` |
| 401 | `CHUA_DANG_NHAP`, `TOKEN_HET_HAN`, `SAI_THONG_TIN_DANG_NHAP` | |
| 403 | `KHONG_CO_QUYEN`, `TAI_KHOAN_BI_KHOA`, `PHAI_DOI_MAT_KHAU`, `TU_DUYET_KHONG_DUOC` | |
| 404 | `KHONG_TIM_THAY` | Kể cả khi tài nguyên tồn tại nhưng thuộc khách khác |
| 405 | `PHUONG_THUC_KHONG_DUOC_PHEP` | Gọi sai phương thức HTTP; giữ header `Allow` |
| 409 | `HET_HANG`, `CHUYEN_TRANG_THAI_KHONG_HOP_LE`, `DA_CO_NGUOI_XU_LY`, `GIA_DA_THAY_DOI`, `TRUNG_DU_LIEU`, `PHAI_CON_ADMIN`, `DANH_MUC_CON_SAN_PHAM` | |
| 422 | `THUOC_KE_DON_KHONG_VAO_GIO`, `VUOT_SO_LUONG_TOI_DA`, `MA_GIAM_GIA_KHONG_HOP_LE`, `QUA_THOI_HAN_DOI_TRA`, `HOAN_VUOT_SO_DA_TRA`, `OTP_SAI`, `OTP_HET_HAN` | Vi phạm quy tắc nghiệp vụ |
| 429 | `QUA_GIOI_HAN` | Giới hạn tần suất; kèm header `Retry-After` |
| 502 | `LOI_DOI_TAC` | Cổng thanh toán hoặc vận chuyển lỗi |
| 500 | `LOI_HE_THONG` | Không lộ stack trace; `chi_tiet` là `{"request_id": "..."}`, log có `request_id` |

**Quy ước thực thi** (`core/loi.py`, `core/middleware.py`):
- Danh sách mã lỗi trong code (`MA_LOI`) phải khớp bảng này. Test `test_bang_ma_loi_khop_spec_06` báo lỗi nếu lệch; thêm mã mới thì sửa cả hai nơi.
- `LoiNghiepVu(ma_loi, thong_diep, chi_tiet=...)` tự lấy HTTP status từ bảng. `chi_tiet` luôn có mặt trong phản hồi (giá trị `null` nếu không có).
- Lỗi validate (400): `chi_tiet` là danh sách `{"truong": "dong.1.so_luong", "loi": "Bắt buộc nhập"}`. `truong` là đường dẫn phân cách bằng dấu chấm (bỏ phần `body`/`query`), JSON hỏng thì `truong = "body"`.
- Lỗi HTTP khác do framework phát sinh (ví dụ 413) dùng `ma_loi = "LOI_HTTP"` và giữ nguyên status.
- Mọi phản hồi (kể cả lỗi) có header `X-Request-ID`. Client có thể tự gửi header này (8–64 ký tự `A-Za-z0-9._-`), không hợp lệ thì server tự sinh. Trình duyệt đọc được header nhờ `Access-Control-Expose-Headers`.
- Ngoại lệ về định dạng: `GET /api/v1/health` dùng body riêng (mục 2).

## 5. Phân trang, lọc, sắp xếp
- **Tham số:**
  - Phân trang: `trang` (từ 1), `kich_thuoc` (mặc định 20, tối đa 100).
  - Sắp xếp: `sap_xep=-created_at` (dấu `-` là giảm dần; chỉ nhận trường nằm trong danh sách cho phép của endpoint).
  - Lọc: tên trường làm tham số, ví dụ `trang_thai=cho_xac_nhan&tu_ngay=2026-10-01&den_ngay=2026-10-15`.
- **Phản hồi:** `{"du_lieu": [...], "tong": 135, "trang": 1, "kich_thuoc": 20}`.

## 6. Idempotency
- `POST /api/v1/toi/don-hang` và các API tạo giao dịch thanh toán/hoàn tiền nhận header `Idempotency-Key` (UUID do client sinh).
- Server lưu khóa cùng kết quả 24 giờ trong bộ nhớ đệm (bảng tạm hoặc cache in-process cho đồ án). Gửi lại cùng khóa thì trả lại đúng kết quả cũ.
- IPN và webhook chống xử lý trùng bằng mã giao dịch của đối tác (spec 08).

## 7. Upload file
- **Ảnh sản phẩm, banner, bài viết** (công khai): `POST /api/v1/noi-bo/tep` (multipart). Trả `url` công khai.
- **Ảnh đơn thuốc, ảnh/video đổi trả** (riêng tư):
  - Upload kèm request nghiệp vụ.
  - Lưu khóa file trong jsonb (`anh_don_thuoc`, `anh`).
  - Đọc qua `GET /api/v1/.../tep/{khoa}` để nhận URL ký có hạn 10 phút. Chỉ chủ sở hữu hoặc người được phép (spec 03 mục 6) nhận được URL.
- **Kiểm tra file:** kiểu MIME thật (đọc magic bytes); ảnh tối đa 5 MB (jpeg, png, webp); video đổi trả tối đa 30 MB (mp4); đổi tên file thành UUID.

## 8. Webhook và IPN
| Endpoint | Đối tác | Xử lý |
|---|---|---|
| `GET /api/v1/webhook/vnpay-ipn` | VNPay | Kiểm chữ ký → kiểm số tiền → chống trùng → HT04 → trả JSON `RspCode` theo tài liệu VNPay |
| `POST /api/v1/webhook/momo-ipn` | MoMo | Kiểm chữ ký → kiểm số tiền → chống trùng → HT04 → trả đúng mã phản hồi MoMo yêu cầu |
| `POST /api/v1/webhook/ghn` | GHN | Kiểm token → ghi `van_don.du_lieu_webhook` → ánh xạ trạng thái → HT05/HT06 |

- Trang "kết quả thanh toán" phía frontend **không** tin tham số trên URL trả về. Trang này hỏi lại backend trạng thái đơn.

## 9. SSE và WebSocket
- **Chat AI:** `POST /api/v1/tu-van/chat` với body `{ma_phien, noi_dung}`, trả `text/event-stream`. Các loại sự kiện:
  - `van_ban` (đoạn chữ).
  - `the_san_pham` (danh sách sản phẩm gợi ý).
  - `chuyen_duoc_si`.
  - `nguy_hiem`.
  - `ket_thuc` (kèm `tin_nhan_id`).
  - `loi`.
- **Chat dược sĩ:** WebSocket `/api/v1/tu-van/ws?ma_phien=...`.
  - Xác thực bằng access token gửi trong message đầu tiên, sau đó server kiểm tra quyền vào phiên.
  - Message JSON `{loai: "tin_nhan"|"dang_go"|"he_thong", ...}`.
  - Hub kết nối giữ trong bộ nhớ process (đồ án chạy 1 process API; muốn chạy nhiều process thì cần Redis pub/sub, ngoài phạm vi).

## 10. OpenAPI và client frontend
- Mọi route khai báo `response_model` và schema lỗi.
- Frontend chạy `npm run gen:api` (dùng `openapi-typescript`) để sinh `src/api/schema.d.ts`, gọi qua `openapi-fetch`. Không tự viết type trùng với API.
- Đổi schema API thì phải sinh lại type và sửa lỗi TypeScript trong cùng task.

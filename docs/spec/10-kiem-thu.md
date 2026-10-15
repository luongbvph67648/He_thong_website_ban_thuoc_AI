# 10. Kiểm thử

## 1. Nguyên tắc
- Mỗi tiêu chí chấp nhận trong lộ trình có ít nhất 1 test tự động.
- Nghiệp vụ lõi (tồn kho, trạng thái, tiền, phân quyền, dữ liệu sức khỏe) viết test **trước** khi code.
- **Test chạy trên PostgreSQL thật** (docker, cùng image với dev), không dùng SQLite. Ràng buộc, enum, `FOR UPDATE` và trigram phải được kiểm tra trên DB thật.
- **Test không gọi mạng:** `AI_GIA_LAP=true`, `EMBEDDING_GIA_LAP=true`, các `*_CHE_DO=gia`.
- **Test chạy độc lập theo thứ tự:** mỗi test rollback; không phụ thuộc dữ liệu seed mẫu, tự tạo dữ liệu bằng factories.

## 2. Hạ tầng backend
- `pytest` + `pytest-asyncio`, `httpx.AsyncClient(transport=ASGITransport(app))`.
- **DB test:** `DATABASE_URL_TEST`. Mỗi phiên test chạy `alembic upgrade head` một lần, kèm seed vai trò/quyền/cấu hình (không seed dữ liệu mẫu).
  - Mỗi test mở connection + transaction ngoài.
  - Session của app dùng `join_transaction_mode="create_savepoint"`.
  - Rollback sau mỗi test.
- **Test tranh chấp** (mục 4) cần **commit thật** nên dùng fixture riêng `db_that`: tạo dữ liệu, commit, chạy, rồi dọn bằng `TRUNCATE ... CASCADE` các bảng liên quan.
- **`tests/factories.py`:** hàm async `tao_khach(...)`, `tao_nhan_vien(vai_tro=...)`, `tao_san_pham(loai=..., don_vi=[...])`, `tao_lo(san_pham, so_luong, han_su_dung, trang_thai)`, `tao_don(...)`... Giá trị mặc định hợp lệ, tham số nào cũng ghi đè được.
- **Fixture đăng nhập:** `dang_nhap_khach`, `dang_nhap_duoc_si`, `dang_nhap_kho`, `dang_nhap_admin` trả client đã gắn token.

## 3. Test ma trận phân quyền (`tests/phan_quyen/`)
- **`registry.py`:** từ điển `{(METHOD, path_template): (ma_quyen, muc)}` cho **mọi** route `/api/v1/noi-bo/*`, kèm `CONG_KHAI` (ba route xác thực không cần quyền) và `CHO_PHEP_KHI_CHUA_DOI_MAT_KHAU` (đúng hai route được miễn việc bắt đổi mật khẩu).
- **`test_registry_day_du`:** duyệt cây route (kể cả router include lồng nhau) kèm cây dependency thật; route nội bộ nào không có trong registry, không gắn đúng một `yeu_cau_quyen`, hoặc khai báo (mã quyền, mức) khác với route thật thì fail. Thao tác ghi khai báo mức `xem`, mã quyền không có trong yaml, registry lỗi thời (không còn route) đều fail. Có test chứng minh bộ kiểm tra bắt được từng loại lỗi này trên route thử.
- **`test_ma_tran`:** tham số hóa theo (route, vai trò) từ `docs/spec/data/quyen.yaml`.
  - Vai trò không có quyền: phải nhận **403** `KHONG_CO_QUYEN`.
  - Vai trò có quyền: **không** được nhận 403. Có thể là 404 hoặc 422 vì dữ liệu giả.
  - Mức `chi_xem` gọi route ghi: 403.
- **Test riêng:**
  - Khách A truy cập đơn, địa chỉ, đơn thuốc, đổi trả, hội thoại của khách B → 404.
  - Token khách gọi `/noi-bo` và token nội bộ gọi `/toi` → 401.
  - Response nội bộ cho Admin/kho không chứa khóa `ho_so_suc_khoe`, `di_ung`, `benh_nen`. Response cho dược sĩ không chứa `gia_nhap`, `gia_von`.
  - Hàm cổng sức khỏe: 4 trường hợp đúng/sai theo spec 03 mục 5.1, kèm kiểm tra có ghi nhật ký.
  - Tách nhiệm vụ: tự duyệt phiếu điều chỉnh/hủy/xuất trả bị chặn; Admin tự khóa hoặc tự hạ quyền bị chặn; khóa Admin cuối cùng bị chặn (`PHAI_CON_ADMIN`).

## 4. Bất biến tồn kho và tranh chấp (`tests/bat_bien/`)
- **Hàm `kiem_tra_bat_bien(db)`:** chạy 5 bất biến ở spec 04 mục 3.2 bằng SQL, trả danh sách vi phạm. Gọi ở cuối **mọi** test thuộc module `kho`, `ban_hang`, `don_thuoc`, `sau_ban` (fixture autouse).
- **Tranh chấp:**
  - Lô còn 1 đơn vị, 2 coroutine đặt hàng song song (2 session thật) → đúng 1 thành công, 1 nhận `HET_HANG`.
  - Giữ hàng song song trên 2 lô theo thứ tự ngược nhau → không deadlock (khóa theo id tăng).
  - 2 dược sĩ cùng nhận một yêu cầu đơn thuốc → 1 nhận được, 1 nhận `DA_CO_NGUOI_XU_LY`.
  - Mã giảm giá còn 1 lượt, 2 đơn song song → chỉ 1 đơn dùng được.

## 5. Máy trạng thái (`tests/ban_hang/test_trang_thai.py`)
- **Tham số hóa từ bảng chuyển trong code** (chính là bảng 1.1 spec 04). Với mỗi dòng: tạo đơn ở trạng thái nguồn, thực hiện bằng đúng tác nhân, rồi kiểm tra:
  - Trạng thái đích.
  - Dòng `lich_su_trang_thai`.
  - Tác động kho/thanh toán ghi ở cột "Tác động dữ liệu".
- **Mọi cặp (nguồn, đích) không có trong bảng** → `CHUYEN_TRANG_THAI_KHONG_HOP_LE`.
- **Tác nhân sai** (ví dụ khách gọi hủy khi đơn đang `dang_soan_hang`) → bị từ chối.
- **Test quét mã nguồn:** không có phép gán `.trang_thai =` lên `DonHang` ngoài `trang_thai.py`.

## 6. Tiền (`tests/ban_hang/test_tinh_tien.py`)
Theo spec 04 mục 4–5:
- Phân bổ giảm giá: tổng phân bổ = tiền giảm, dòng cuối nhận phần dư, không dòng nào âm.
- Thuốc kê đơn không được giảm.
- Trần `giam_toi_da`, `don_toi_thieu`.
- Miễn phí ship đúng ngưỡng.
- Tiền hoàn một phần, hoàn toàn bộ (kèm phí ship), không hoàn vượt số đã trả.
- Dùng `hypothesis` cho phân bổ giảm giá với giỏ ngẫu nhiên.

## 7. AI và tích hợp
- **AI:** xem spec 07 mục 9.
- **Thanh toán:** chữ ký đúng/sai, IPN trùng, số tiền lệch, IPN đến khi đơn đã hủy.
- **Vận chuyển:** ánh xạ từng trạng thái GHN, webhook sai token.
- **OTP:** hết hạn, quá số lần, giới hạn gửi.

## 8. Frontend và end-to-end
- **Vitest + Testing Library:**
  - `dinhDangTien`, `dinhDangNgay`.
  - Giỏ hàng local và gộp giỏ.
  - `YeuCauQuyen`.
  - Hiển thị thuốc kê đơn (không có nút thêm vào giỏ).
  - Form thanh toán.
- **Playwright** (`frontend/e2e/`), chạy với backend thật + seed mẫu + mọi adapter giả. Luồng tối thiểu:
  1. Khách đăng ký → thêm giỏ → đặt COD → dược sĩ xác nhận → kho soạn và đóng gói → giả lập GHN giao → khách thấy "Đã giao".
  2. Đặt hàng VNPay giả → "Thành công" → đơn sang chờ xác nhận.
  3. Khách vãng lai gửi đơn thuốc → dược sĩ duyệt, tạo đơn → khách mở link xác nhận.
  4. Đổi trả → kho nhận → Admin xác nhận hoàn tiền.
  5. Chat AI hỏi sản phẩm → bấm "Gặp dược sĩ" → dược sĩ trả lời qua WebSocket.

## 9. CI (`.github/workflows/ci.yml`)
- **Job `backend`:**
  - Service `pgvector/pgvector:pg16`.
  - `uv sync`, `ruff check`, `ruff format --check`, `pytest -q`.
  - Chạy `scripts/so_sanh_schema.py` (phải 0 lệch).
- **Job `frontend`:** `npm ci`, `npm run lint`, `npx tsc --noEmit`, `npm test -- --run`, `npm run build`.
- E2E chạy tay trước mỗi mốc (không bắt buộc trong CI).

## 10. Definition of Done của một task
- [ ] Mọi tiêu chí chấp nhận trong lộ trình đã đánh dấu, mỗi tiêu chí có test.
- [ ] `ruff`, `pytest`, `tsc`, `vitest` xanh. Không skip, không xóa test cũ để cho qua.
- [ ] Route nội bộ mới đã có trong registry phân quyền. Mã lỗi mới đã thêm vào spec 06.
- [ ] Không còn `TODO` chưa ghi vào mục "Việc phát sinh" của lộ trình.
- [ ] Spec đã được cập nhật nếu cách làm khác spec, và quyết định đã ghi vào `12-quyet-dinh.md`.
- [ ] Đã chạy `/review-nghiep-vu` (task đụng đơn hàng, kho, tiền, phân quyền, dữ liệu sức khỏe).
- [ ] Commit có mã task.

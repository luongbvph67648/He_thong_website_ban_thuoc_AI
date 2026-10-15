# 12. Nhật ký quyết định

Mỗi quyết định ảnh hưởng đến thiết kế, nghiệp vụ hoặc công nghệ được ghi một mục theo mẫu dưới đây. Quyết định mới thêm vào **cuối file**, không sửa mục cũ. Nếu đổi ý thì viết mục mới và ghi "Thay thế QĐ-xx".

```
## QĐ-xx: <tiêu đề ngắn> (YYYY-MM-DD, task Tx.y)
- Bối cảnh: ...
- Quyết định: ...
- Hệ quả: ... (file spec / code bị ảnh hưởng)
```

## QĐ-01: Phạm vi 3 tác nhân, 1 nhà thuốc = 1 kho (2026-10-15)
- **Bối cảnh:** Đồ án kiểu Long Châu nhưng thu gọn phạm vi.
- **Quyết định:**
  - 3 tác nhân Khách hàng / Nhân viên / Quản trị, chia thành 5 nhóm người dùng.
  - Nhân viên chia vai trò bằng RBAC; mỗi nhân viên có 1 vai trò.
  - Không làm chi nhánh hay chuyển kho.
- **Hệ quả:** spec 00, 03. `nhan_vien.vai_tro_id` giữ quan hệ N-1.

## QĐ-02: ERD đã chỉnh sửa là nguồn sự thật (2026-10-15)
- **Bối cảnh:** ERD gốc có 1 lỗi cú pháp và thiếu chỗ lưu một số nghiệp vụ (biệt trữ, thẻ kho, vận đơn trả hàng, hoàn tiền...).
- **Quyết định:** dùng `docs/database/ERD_da_chinh_sua.dbml` (65 bảng). Mọi thay đổi ghi `[DBxx]`, đối chiếu sheet "Đánh giá Database" trong file Excel.
- **Hệ quả:** spec 02. Lệnh `/doi-schema`.

## QĐ-03: Backend FastAPI + SQLAlchemy async (2026-10-15)
- **Bối cảnh:** Sheet chỉ ghi "Python".
- **Quyết định:**
  - FastAPI, SQLAlchemy 2 async (asyncpg), Alembic, Pydantic v2, `uv`.
  - Job nền: APScheduler ở process riêng.
  - Chat dược sĩ: WebSocket. Chat AI: SSE.
- **Hệ quả:** spec 01, 06; `backend/CLAUDE.md`.

## QĐ-04: Frontend React + Vite + Ant Design (2026-10-15)
- **Quyết định:**
  - TypeScript, Ant Design (`vi_VN`), TanStack Query, React Router, Zustand.
  - Client API sinh từ OpenAPI (`openapi-typescript` + `openapi-fetch`).
  - Một ứng dụng duy nhất chia 3 khu theo đường dẫn.
- **Hệ quả:** spec 09; `frontend/CLAUDE.md`.

## QĐ-05: Claude API cho LLM, BGE-M3 tự host cho embedding (2026-10-15)
- **Quyết định:**
  - Model `claude-opus-5-5` (biến `CLAUDE_MODEL`), đặt `effort` rõ ràng cho từng tác vụ.
  - Bật `fallbacks: "default"` (beta `server-side-fallback-2026-07-01`) để tự chạy lại khi bị bộ lọc an toàn từ chối.
  - Embedding `BAAI/bge-m3`, 1024 chiều, khớp `vector(1024)` của ERD.
- **Hệ quả:** spec 07. Đổi model là quyết định chi phí của nhóm, phải ghi một QĐ mới.

## QĐ-06: Mọi tích hợp ngoài có adapter giả (2026-10-15)
- **Quyết định:**
  - VNPay, MoMo, GHN, SMS/email đi qua interface có bản giả chạy offline.
  - Dev và test mặc định dùng bản giả; sandbox thật bật bằng biến môi trường.
- **Hệ quả:** spec 08. Có thể demo đầy đủ luồng mà không cần tài khoản đối tác.

## QĐ-07: Lịch sử chat gửi lại Claude chỉ gồm text (2026-10-15)
- **Bối cảnh:** `tin_nhan` chỉ lưu nội dung text. Trên Opus 5.5, thinking blocks gắn với đúng hội thoại đã tạo ra chúng.
- **Quyết định:**
  - Giữa các lượt, chỉ gửi lại text của các lượt trước.
  - Trong cùng một lượt có gọi tool, append nguyên `response.content`.
  - System prompt và danh sách tool cố định.
- **Hệ quả:** spec 07 mục 2. Không cần cột lưu nội dung thô của Claude.

## QĐ-08: Access token chỉ ở bộ nhớ trình duyệt, làm mới bằng cookie refresh (2026-10-15, task T0.6, T0.7)
- **Quyết định:**
  - Frontend giữ access token và hồ sơ trong store Zustand, KHÔNG persist (không localStorage/sessionStorage). Tải lại trang thì lấy lại token bằng refresh token trong cookie httpOnly.
  - Client API gặp 401 thì làm mới đúng một lần (nhiều request lỗi cùng lúc dùng chung một lần làm mới) rồi gọi lại request gốc đúng một lần; gọi lại vẫn 401 hoặc làm mới thất bại thì đăng xuất. Chỉ làm mới khi request gốc có kèm token; các endpoint `dang-nhap`, `dang-ky`, `lam-moi`, `dang-xuat`, `quen-mat-khau`, `otp` không bao giờ kích hoạt làm mới.
  - Thân phản hồi đăng nhập/làm mới là `{"access_token": "<jwt>"}` (spec 06 mục 3).
  - Hàm tạo/kiểm tra JWT (`core/bao_mat.py`) làm ở T0.6 để fixture đăng nhập của test dùng token thật; endpoint đăng nhập và refresh token vẫn ở T1.x.
- **Hệ quả:** spec 06 mục 3; `frontend/CLAUDE.md`; T1.2, T1.3 phải trả đúng thân phản hồi trên.

## QĐ-09: Seed không hoàn tác chỉnh sửa của Admin; Admin đầu tiên cần mật khẩu mạnh (2026-10-15, task T0.5)
- **Bối cảnh:** rà soát nghiệp vụ T0.5 tìm thấy seed ghi đè việc Admin gán/bỏ quyền (AD18) và chấp nhận mật khẩu mẫu công khai của `.env.example` cho Admin.
- **Quyết định:**
  - Seed chỉ cấp mặc định cho quyền MỚI; quyền đã có giữ nguyên cách gán hiện tại. Danh mục `quyen` vẫn đồng bộ theo `quyen.yaml`. `vai_tro` và `cau_hinh` chỉ thêm cái còn thiếu.
  - Admin đầu tiên: mật khẩu tối thiểu 12 ký tự (chặt hơn mức chung 8), không được bắt đầu bằng `doi-` (giá trị mẫu); `JWT_SECRET` cũng không được là giá trị mẫu.
  - `--mau` chỉ chạy với CSDL ở máy cục bộ, trừ khi có `--cho-phep-may-chu-khac`; SKU và số lô mẫu có tiền tố `MAU-`.
- **Hệ quả:** spec 02 mục 6; `backend/CLAUDE.md`.

## QĐ-10: Phân luồng ba khu và guard quyền trên UI (2026-10-15, task T0.7)
- **Quyết định:**
  - Route guard khu nội bộ dùng mức `xem` (quyền chỉ xem vẫn vào được trang xem); nút thao tác bọc `<YeuCauQuyen kieu="nut">` mức đầy đủ và ẩn hẳn khi thiếu.
  - Phiên của khách không được coi là đã đăng nhập nội bộ. Chưa đăng nhập nội bộ thì mọi route `/nhan-vien` và `/quan-tri` chuyển tới `/nhan-vien/dang-nhap`.
  - Admin vào `/nhan-vien` bị chuyển sang `/quan-tri`; không phải Admin vào `/quan-tri` thấy 403. Mỗi trang con vẫn kiểm tra mã quyền riêng.
  - Bảng route và menu nằm ở `khu/nhan-vien/menu.ts`, `khu/quan-tri/menu.ts`, `khu/cua-hang/trang.ts`, có test đối chiếu từng dòng với spec 09 mục 2 và với `quyen.yaml`.
- **Hệ quả:** spec 09; `frontend/CLAUDE.md`.


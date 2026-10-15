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

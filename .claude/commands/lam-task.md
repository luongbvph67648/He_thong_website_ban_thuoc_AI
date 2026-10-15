---
description: Thực hiện một task trong lộ trình theo quy trình chuẩn
argument-hint: <mã task, ví dụ T4.4>
---
Thực hiện task **$ARGUMENTS** trong `docs/spec/11-lo-trinh.md`.

1. **Đọc trước khi code**
   - Mục của task trong lộ trình: tiêu chí chấp nhận, giao diện, phụ thuộc. Phụ thuộc chưa xong thì dừng và báo.
   - Mục của từng mã chức năng trong `docs/spec/05-chuc-nang.md`: mô tả, mã quyền, phạm vi dữ liệu, bảng.
   - Các spec được tiêu chí nhắc tới (03 phân quyền, 04 nghiệp vụ, 06 API, 07 AI, 08 tích hợp, 09 frontend...), và `CLAUDE.md` của thư mục sẽ sửa.
   - Code hiện có của module liên quan, để dùng lại hàm sẵn có thay vì viết mới.
2. **Lập kế hoạch**
   - Task chạm hơn 3 file: trình bày kế hoạch ngắn (file sẽ tạo/sửa, API, test) trước khi code.
   - Chỗ nào spec mơ hồ thì hỏi người dùng, không đoán.
3. **Code kèm test**
   - Nghiệp vụ lõi (tồn kho, trạng thái, tiền, phân quyền, dữ liệu sức khỏe): viết test trước.
   - Mỗi tiêu chí chấp nhận có ít nhất 1 test. Route `/noi-bo` mới phải thêm vào `tests/phan_quyen/registry.py`.
   - Giao diện ghi trong task được làm trong cùng task. Sau khi đổi API, chạy `npm run gen:api`.
4. **Kiểm tra**
   - Backend: `uv run ruff check . && uv run ruff format --check . && uv run pytest -q`.
   - Frontend: `npm run lint && npx tsc --noEmit && npm test -- --run`.
   - Phải xanh hết. Không skip test, không nới lỏng test để cho qua.
   - Task đụng đơn hàng, kho, tiền, phân quyền hoặc dữ liệu sức khỏe: chạy `/review-nghiep-vu` và sửa mọi vấn đề mức cao.
5. **Cập nhật tài liệu**
   - Trong lộ trình: tích các tiêu chí đã đạt, đổi trạng thái task thành `[x]`, ghi lệch so với spec vào "Ghi chú triển khai" của task.
   - Lỗi hoặc việc ngoài phạm vi: ghi vào mục "Việc phát sinh" cuối lộ trình.
   - Quyết định thiết kế mới: ghi vào `docs/spec/12-quyet-dinh.md`.
   - Cập nhật phần "Lệnh thường dùng" trong `CLAUDE.md` nếu lệnh thay đổi.
6. **Commit**
   - Commit nhỏ, message tiếng Việt, bắt đầu bằng mã task, ví dụ `T4.4: đặt hàng giữ hàng FEFO`.
   - Tóm tắt cho người dùng: đã làm gì, test nào chứng minh, còn gì cần họ quyết định.

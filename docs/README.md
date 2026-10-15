# Tài liệu dự án

## Đặc tả (`spec/`): nguồn sự thật cho code
| File | Nội dung |
|---|---|
| [00-tong-quan.md](spec/00-tong-quan.md) | Mục tiêu, tác nhân, phạm vi, giả định, thuật ngữ |
| [01-kien-truc.md](spec/01-kien-truc.md) | Kiến trúc, cấu trúc thư mục, module, biến môi trường |
| [02-database.md](spec/02-database.md) | Quy trình schema, ràng buộc bổ sung, khóa, seed |
| [03-phan-quyen.md](spec/03-phan-quyen.md) | Vai trò, ma trận phân quyền, phạm vi dữ liệu, dữ liệu nhạy cảm |
| [04-nghiep-vu.md](spec/04-nghiep-vu.md) | Bảng chuyển trạng thái, tồn kho, tính tiền, hoàn tiền, đơn thuốc |
| [05-chuc-nang.md](spec/05-chuc-nang.md) | Danh mục 92 chức năng |
| [06-api.md](spec/06-api.md) | Quy ước API, xác thực, lỗi, webhook |
| [07-ai.md](spec/07-ai.md) | Claude API, embedding, chatbot, tìm kiếm lai, đọc ảnh, gợi ý, dự báo |
| [08-tich-hop.md](spec/08-tich-hop.md) | VNPay, MoMo, GHN, SMS/email, lưu file |
| [09-frontend.md](spec/09-frontend.md) | Ba khu giao diện, bản đồ trang, quy tắc hiển thị |
| [10-kiem-thu.md](spec/10-kiem-thu.md) | Chiến lược test, CI, Definition of Done |
| [11-lo-trinh.md](spec/11-lo-trinh.md) | Lộ trình 9 giai đoạn, tiêu chí chấp nhận từng task |
| [12-quyet-dinh.md](spec/12-quyet-dinh.md) | Nhật ký quyết định |
| [data/quyen.yaml](spec/data/quyen.yaml) | Ma trận quyền dạng máy đọc (seed + test) |

## Cơ sở dữ liệu (`database/`)
Xem [database/README.md](database/README.md).

## Dùng với Claude Code
- `CLAUDE.md` ở gốc repo được nạp ở mọi phiên. `backend/CLAUDE.md` và `frontend/CLAUDE.md` được nạp khi làm việc trong thư mục tương ứng.
- **Lệnh:**
  - `/tiep-tuc`: làm task chưa xong đầu tiên.
  - `/lam-task T4.4`: làm một task cụ thể.
  - `/doi-schema <mô tả>`: đổi schema đúng quy trình.
  - `/review-nghiep-vu`: rà soát thay đổi theo quy tắc nghiệp vụ.

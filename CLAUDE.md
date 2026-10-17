# Hệ thống website bán thuốc tích hợp AI

Đồ án: website nhà thuốc trực tuyến kiểu Long Châu, quy mô 1 nhà thuốc = 1 kho. Có 3 tác nhân:
- **Khách hàng**: vãng lai và thành viên.
- **Nhân viên**: dược sĩ bán hàng và nhân viên kho.
- **Quản trị (Admin)**.

Tài liệu đặc tả ở `docs/spec/`, là **nguồn sự thật**. Code phải khớp spec. Nếu spec sai thì sửa spec trước, sau đó mới sửa code.

## Stack
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2 (async, asyncpg), Alembic, Pydantic v2, quản lý gói bằng `uv`.
- **CSDL:** PostgreSQL 16 kèm `vector`, `unaccent`, `pg_trgm`, chạy bằng docker image `pgvector/pgvector:pg16`.
- **Frontend:** React + Vite + TypeScript, Ant Design (`vi_VN`), TanStack Query, React Router, Zustand.
- **AI:**
  - Claude API qua SDK `anthropic`, model đọc từ biến `CLAUDE_MODEL`, mặc định `claude-opus-5-5`.
  - Embedding BGE-M3 tự host, 1024 chiều.
- **Job nền:** APScheduler, chạy ở process riêng.
- **Tích hợp:** VNPay, MoMo, GHN, SMS/email. Mọi tích hợp đều có adapter giả để dev và test.

## Cấu trúc
```
backend/      FastAPI (app/core, app/models, app/modules/<module>, app/tich_hop, app/ai, app/jobs, app/seed), tests/
frontend/     React (src/khu/{cua-hang,nhan-vien,quan-tri}, src/api, src/components, src/lib)
docs/spec/    Đặc tả 00-12 + data/quyen.yaml
docs/database ERD (DBML/SQL) và file Excel đánh giá
.claude/      Lệnh /tiep-tuc, /lam-task, /doi-schema, /review-nghiep-vu và agent reviewer
```
Mỗi thư mục `backend/` và `frontend/` có `CLAUDE.md` riêng ghi quy ước chi tiết.

## Lệnh thường dùng
Lệnh có ghi `(từ Tx.y)` chỉ chạy được sau khi task đó xong. Nếu lệnh thực tế khác thì cập nhật lại mục này.

Lần đầu chạy: sao chép `backend/.env.example` thành `backend/.env`.

```bash
docker compose up -d db mailpit                       # Postgres + Mailpit (http://localhost:8025)
cd backend && uv sync                                 # cài phụ thuộc
cd backend && uv run alembic upgrade head             # migration (từ T0.4)
cd backend && uv run python -m app.seed --mau         # seed + dữ liệu mẫu (từ T0.5)
cd backend && uv run python -m app.seed --demo        # như --mau, thêm ảnh và ~190 đơn trong 3 tháng (từ T8.3)
cd backend && uv run uvicorn app.main:app --reload    # API http://localhost:8000/docs
cd backend && uv run python -m app.jobs               # worker job nền (từ T3.2)
cd backend && uv run ruff check . && uv run ruff format --check .   # (từ T0.6)
cd backend && uv run pytest -q                        # cần db đang chạy
cd frontend && npm install && npm run dev             # http://localhost:5173, proxy /api → :8000
cd frontend && npm run gen:api                        # sinh type từ OpenAPI, backend phải đang chạy (từ T0.7)
cd frontend && npm run lint && npx tsc --noEmit       # lint bằng oxlint
cd frontend && npm test -- --run                      # vitest một lần (từ T0.7)
cd frontend && npm run build
./scripts/e2e.sh                                       # e2e Playwright trên CSDL nha_thuoc_e2e (từ T8.3)
```

## Quy tắc bắt buộc
Vi phạm bất kỳ quy tắc nào dưới đây đều tính là lỗi nghiêm trọng.

1. **Trạng thái đơn hàng** chỉ được đổi qua `modules/ban_hang/trang_thai.py::chuyen_trang_thai()` (HT06), đúng bảng chuyển trạng thái ở `docs/spec/04-nghiep-vu.md`. Không gán `don_hang.trang_thai` ở bất kỳ chỗ nào khác.
2. **Tồn kho** gồm `so_luong_ton`, `so_luong_giu`, `so_luong_biet_tru`.
   - Chỉ được đổi qua `modules/kho/ton_kho.py`.
   - Hàm đổi tồn phải khóa lô bằng `SELECT … FOR UPDATE`, khóa theo id tăng dần.
   - Mọi thay đổi `so_luong_ton` và `so_luong_biet_tru` phải ghi `bien_dong_kho` trong cùng transaction.
3. **API của khách** lấy `khach_hang_id` từ token, không bao giờ nhận id khách từ client. Truy cập tài nguyên của người khác thì trả **404**.
4. **Endpoint `/api/v1/noi-bo/*`** phải khai báo `Depends(yeu_cau_quyen("<mã>", muc=...))` với mã có trong `docs/spec/data/quyen.yaml`, và phải được thêm vào registry của test ma trận phân quyền.
5. **Tiền và thời gian.**
   - Tiền dùng `Decimal` và cột NUMERIC, làm tròn đến đồng bằng `core/tien.py`. Cấm dùng `float`.
   - Thời gian lưu UTC (`timestamptz`), hiển thị theo Asia/Ho_Chi_Minh. Hạn sử dụng là `date`, so với ngày hiện tại theo giờ VN.
6. **Thuốc kê đơn** (`loai_san_pham = thuoc_ke_don`):
   - Không vào giỏ hàng, không được giảm giá, không bán qua kênh điện thoại.
   - AI không được gợi ý.
   - Phải chặn ở tầng service/SQL, không chỉ ở UI hay prompt.
7. **Dữ liệu sức khỏe** (`ho_so_suc_khoe`, `di_ung`):
   - Admin không được đọc.
   - Dược sĩ chỉ đọc qua hàm cổng `duoc_doc_ho_so_suc_khoe()` (spec 03 mục 5).
   - Không ghi dạng rõ vào log hay nhật ký.
8. **Tách nhiệm vụ:**
   - Phiếu điều chỉnh, phiếu hủy, phiếu xuất trả: người lập khác người duyệt.
   - Dược sĩ duyệt đổi trả khác Admin xác nhận hoàn tiền.
9. **Schema** chỉ đổi theo lệnh `/doi-schema`: DBML → model → migration mới → spec. Không sửa migration đã commit.
10. **Bí mật:** không commit bí mật (khóa để trong `backend/.env`, đã gitignore). Test không gọi dịch vụ thật (Claude, cổng thanh toán, GHN, SMS).

## Quy trình mỗi phiên làm việc
1. Mở `docs/spec/11-lo-trinh.md`, chọn task bằng `/tiep-tuc` (task chưa xong đầu tiên) hoặc `/lam-task T4.4`. Mỗi phiên chỉ làm **một task**.
2. Đọc phần spec liên quan (bảng bên dưới) và mục chức năng tương ứng trong `05-chuc-nang.md`.
3. Task có hơn 3 file thay đổi thì lập kế hoạch (plan mode) trước khi code.
4. Viết code kèm test.
   - Nghiệp vụ lõi (tồn kho, trạng thái, tiền, phân quyền): viết test trước.
   - Mỗi tiêu chí chấp nhận phải có ít nhất 1 test.
5. Chạy lint, typecheck và test của phần bị ảnh hưởng. Tất cả phải xanh.
6. Chạy `/review-nghiep-vu` nếu task đụng tới đơn hàng, kho, tiền, phân quyền hoặc dữ liệu sức khỏe.
7. Tích checkbox tiêu chí trong lộ trình, đổi trạng thái task thành `[x]`, ghi lệch so với spec (nếu có) vào phần "Ghi chú triển khai" của task.
8. Commit nhỏ, message tiếng Việt, có mã task, ví dụ: `T4.4: đặt hàng giữ hàng FEFO`.

## Cần gì thì đọc gì
| Việc | Đọc |
|---|---|
| Phạm vi, thuật ngữ | `docs/spec/00-tong-quan.md` |
| Cấu trúc code, module, biến môi trường | `docs/spec/01-kien-truc.md` |
| Schema, ràng buộc, seed, đổi schema | `docs/spec/02-database.md`, `docs/database/ERD_da_chinh_sua.dbml` |
| Ai được làm gì, phạm vi dữ liệu | `docs/spec/03-phan-quyen.md`, `docs/spec/data/quyen.yaml` |
| Trạng thái, tồn kho, tính tiền, hoàn tiền, đơn thuốc | `docs/spec/04-nghiep-vu.md` |
| Mô tả từng chức năng (mã KVL, KTV, DS, KHO, AD, HT, AI) | `docs/spec/05-chuc-nang.md` |
| Quy ước API, xác thực, lỗi | `docs/spec/06-api.md` |
| AI (Claude, embedding, chatbot, OCR, gợi ý, dự báo) | `docs/spec/07-ai.md` |
| VNPay, MoMo, GHN, OTP, lưu file | `docs/spec/08-tich-hop.md` |
| Giao diện | `docs/spec/09-frontend.md` |
| Cách test, Definition of Done | `docs/spec/10-kiem-thu.md` |
| Lộ trình, tiêu chí chấp nhận | `docs/spec/11-lo-trinh.md` |
| Quyết định đã chốt | `docs/spec/12-quyet-dinh.md` |

## Khi viết code gọi Claude API
Gọi skill `/claude-api` để lấy cú pháp SDK Python hiện hành trước khi viết. Tuân thủ spec 07 mục 1 (an toàn) và mục 2 (wrapper chung). Không gọi SDK trực tiếp ngoài `app/ai/claude.py`.

## Khi không chắc chắn
- **Spec mơ hồ hoặc mâu thuẫn:** dừng lại và hỏi người dùng, không tự đoán. Sau khi được trả lời, ghi quyết định vào `docs/spec/12-quyet-dinh.md`.
- **Phát hiện lỗi ngoài phạm vi task:** ghi vào mục "Việc phát sinh" cuối lộ trình, không sửa lan sang chỗ khác.

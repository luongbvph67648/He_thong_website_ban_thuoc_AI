---
description: Thay đổi schema CSDL đúng quy trình (DBML → model → migration → spec)
argument-hint: <mô tả thay đổi>
---
Thay đổi schema theo yêu cầu: **$ARGUMENTS**

1. Đọc `docs/spec/02-database.md` mục 1, 3, 4 và các bảng liên quan trong `docs/database/ERD_da_chinh_sua.dbml`.
2. Trình bày đề xuất cho người dùng **trước khi sửa**:
   - Bảng, cột, kiểu, ràng buộc, index.
   - Ảnh hưởng tới dữ liệu đang có (cần backfill không).
   - Chức năng và spec bị ảnh hưởng.

   Chờ người dùng đồng ý.
3. Sửa DBML, thêm chú thích ngắn, rồi sinh lại SQL:
   `npx -y -p @dbml/cli dbml2sql docs/database/ERD_da_chinh_sua.dbml --postgres -o docs/database/ERD_da_chinh_sua.sql`
4. Sửa model trong `backend/app/models/`.
5. Tạo migration mới: `cd backend && uv run alembic revision --autogenerate -m "<mo_ta>"`.
   - Rà file sinh ra: enum mới cần `ALTER TYPE`, có backfill nếu cột NOT NULL, có `downgrade`.
   - CHECK, partial unique, index đặc biệt viết tay bằng `op.execute`.
   - Tuyệt đối không sửa migration cũ.
6. Chạy `uv run alembic upgrade head`, `uv run python scripts/so_sanh_schema.py` (phải 0 lệch), `uv run alembic check`, `uv run pytest -q`.
7. Cập nhật spec:
   - 02 mục 4 nếu thêm ràng buộc.
   - 03, 04, 05 nếu ảnh hưởng quyền, nghiệp vụ hoặc chức năng.
8. Ghi quyết định vào `docs/spec/12-quyet-dinh.md`. Commit với message `schema: <mô tả>`.

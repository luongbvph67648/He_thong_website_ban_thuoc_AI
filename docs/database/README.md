# Thiết kế CSDL & phân quyền

| File | Nội dung |
|---|---|
| `ERD_PhanQuyen_da_chinh_sua.xlsx` | Bảng tính đã chỉnh sửa: tổng hợp đánh giá, chức năng (cột Thay đổi/Ghi chú), ma trận phân quyền (RBAC), luồng nghiệp vụ, đánh giá database. Import vào Google Sheets: Tệp → Nhập → Tải lên. |
| `ERD_da_chinh_sua.dbml` | ERD đã sửa, dán vào dbdiagram.io. Mọi thay đổi có chú thích `[DBxx]`, đối chiếu sheet "Đánh giá Database". |
| `ERD_da_chinh_sua.sql` | DDL PostgreSQL sinh từ DBML, đã nạp thử thành công vào PostgreSQL 16 (65 bảng, 33 enum, 123 khóa ngoại). |
| `ERD_goc.dbml` | ERD gốc trước khi sửa (có 1 lỗi cú pháp ở bảng `yeu_cau_don_thuoc`). |

Các CHECK, partial unique index và index GIN/HNSW không biểu diễn được bằng DBML; danh sách nằm trong `Project.Note` của `ERD_da_chinh_sua.dbml` và cần viết trong migration.

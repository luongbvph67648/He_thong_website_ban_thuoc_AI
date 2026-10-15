# 00. Tổng quan

## 1. Mục tiêu
Xây dựng website nhà thuốc trực tuyến tích hợp AI (tham khảo Long Châu, Pharmacity) ở quy mô đồ án. Hệ thống cần:
- Bán thuốc và sản phẩm sức khỏe online, quản lý kho theo lô và hạn dùng.
- Xử lý đơn thuốc kê đơn qua dược sĩ.
- Hỗ trợ tư vấn bằng AI có kiểm soát an toàn.

## 2. Tác nhân và nhóm người dùng
| Tác nhân | Nhóm người dùng | Loại tài khoản | Mô tả |
|---|---|---|---|
| Khách hàng | Khách vãng lai | (không đăng nhập) | Xem, tìm kiếm, chat AI, gửi đơn thuốc bằng SĐT đã xác thực OTP |
| Khách hàng | Khách thành viên | `khach_hang` | Kế thừa quyền vãng lai; đặt hàng, thanh toán, đổi trả, hồ sơ sức khỏe |
| Nhân viên | Dược sĩ bán hàng | `nhan_vien`, vai trò `PHARMACIST` | Xử lý đơn, duyệt đơn thuốc, tư vấn, bán tại quầy, nội dung chuyên môn |
| Nhân viên | Nhân viên kho | `nhan_vien`, vai trò `WAREHOUSE` | Nhập kho, soạn hàng, kiểm kê, hủy, xuất trả, thu hồi |
| Quản trị | Admin | `nhan_vien`, vai trò `ADMIN` | Tài khoản, danh mục, giá, khuyến mãi, cấu hình, duyệt phiếu, hoàn tiền, báo cáo |

Ngoài ra còn tác vụ hệ thống (HT01–HT08) và module AI (AI01–AI09). Chúng không phải tác nhân và chạy bằng tài khoản dịch vụ.

## 3. Phạm vi
**Trong phạm vi:** toàn bộ 92 chức năng ở `05-chuc-nang.md`.

**Ngoài phạm vi:**
- Nhiều chi nhánh hoặc nhiều kho; chuyển kho.
- Kế toán, hóa đơn điện tử, công nợ nhà cung cấp.
- Tích điểm thành viên.
- Kết nối Cổng dữ liệu Dược quốc gia.
- Telehealth.
- Ứng dụng di động native.

## 4. Giả định
- **Một nhà thuốc, một kho.** "Nhận tại nhà thuốc" là nhận tại chính nhà thuốc này.
- **Tồn kho** lưu theo lô và theo đơn vị cơ sở (viên, gói, ống, chai). Giá bán đặt theo từng đơn vị quy đổi (hộp/vỉ/viên).
- **Tiền** là VND, không có phần lẻ.
- **Thời gian** lưu UTC, hiển thị giờ Việt Nam.
- **Địa chỉ** dùng mô hình hành chính 2 cấp (tỉnh – xã) từ 01/07/2025; `ma_quan_huyen` có thể để trống.
- **Môi trường dev và test** không cần khóa thật của bất kỳ dịch vụ ngoài nào, nhờ adapter giả.

## 5. Thuật ngữ
| Thuật ngữ | Nghĩa trong hệ thống |
|---|---|
| Lô (`lo_thuoc`) | Một số lô của nhà sản xuất cho một sản phẩm, có HSD, giá nhập và tồn riêng |
| Đơn vị cơ sở | Đơn vị nhỏ nhất (`he_so = 1`); mọi số lượng tồn tính theo đơn vị này |
| Tồn khả dụng | `so_luong_ton - so_luong_giu` của các lô được phép bán |
| Giữ hàng | Đặt trước số lượng trên lô cho đơn chưa xuất kho (`so_luong_giu`, `phan_bo_lo.dang_giu`) |
| Chốt lô | Lúc đơn sang "Đang soạn hàng": trừ tồn thật theo phân bổ |
| FEFO | First Expired, First Out: xuất lô có HSD gần nhất trước |
| Cận hạn | Lô có HSD còn dưới ngưỡng cấu hình; không bán online, vẫn bán tại quầy |
| Biệt trữ | Khu hàng không được bán (khách trả, hư hỏng), chờ hủy hoặc trả nhà cung cấp (`so_luong_biet_tru`) |
| Hoàn nhập | Đưa hàng chưa rời kho, hoặc hàng hoàn còn nguyên niêm phong, trở lại tồn bán đúng lô |
| Thẻ kho | Bảng `bien_dong_kho`: mỗi lần tồn đổi là một dòng |
| Thuốc kê đơn (Rx) | `loai_san_pham = thuoc_ke_don`; chỉ bán qua luồng duyệt đơn thuốc hoặc tại quầy khi có đơn |
| Yêu cầu đơn thuốc | Khách gửi ảnh đơn để dược sĩ tư vấn và tạo đơn hàng |
| Mã quyền | Chuỗi như `order.confirm`, seed vào bảng `quyen`, gán cho vai trò ở `vai_tro_quyen` |
| HT06 | Service máy trạng thái đơn hàng, nơi duy nhất được đổi `don_hang.trang_thai` |

## 6. Tài liệu nguồn
- **ERD:** `docs/database/ERD_da_chinh_sua.dbml` (dán vào dbdiagram.io để xem sơ đồ), `ERD_da_chinh_sua.sql`.
- **File Excel:** `docs/database/ERD_PhanQuyen_da_chinh_sua.xlsx` gồm tổng hợp đánh giá, chức năng, ma trận phân quyền, luồng nghiệp vụ, đánh giá database.

Các file spec trong thư mục này được sinh từ cùng nguồn dữ liệu với file Excel. Khi hai bên lệch nhau, **spec là chuẩn**.

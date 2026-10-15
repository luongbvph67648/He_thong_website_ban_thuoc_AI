# 03. Phân quyền

## 1. Mô hình
- **3 tác nhân, 5 nhóm người dùng** (spec 00 mục 2).
- **2 loại tài khoản, 2 loại token:**
  - `khach_hang`: JWT có `aud = "khach"`.
  - `nhan_vien`: JWT có `aud = "noi_bo"`.
  - Token loại này không dùng được ở nhóm route của loại kia.
- **Khách hàng:** quyền kiểm tra trong code theo trạng thái đăng nhập và quyền sở hữu dữ liệu. Không lưu trong bảng `quyen`.
- **Nhân viên:** RBAC.
  - `nhan_vien.vai_tro_id` → `vai_tro_quyen` → `quyen`.
  - Mỗi cặp vai trò – quyền có mức `day_du` (`gioi_han` = NULL) hoặc `chi_xem` (`gioi_han = 'chi_xem'`).
  - Dữ liệu chuẩn nằm ở [`data/quyen.yaml`](data/quyen.yaml), được sinh từ ma trận dưới đây.

## 2. Vai trò và mức quyền
| Vai trò | Mã | Phạm vi chính |
|---|---|---|
| Dược sĩ bán hàng | `PHARMACIST` | Đơn hàng, đơn thuốc, tư vấn, POS, nội dung chuyên môn, kiểm duyệt |
| Nhân viên kho | `WAREHOUSE` | Nhà cung cấp, lô, phiếu kho, soạn/giao hàng, thu hồi (thực hiện) |
| Quản trị | `ADMIN` | Tài khoản, danh mục, giá, khuyến mãi, cấu hình, AI, duyệt phiếu, hoàn tiền, báo cáo, xem mọi chứng từ |

- **`muc="xem"`:** chỉ cho các thao tác GET.
- **Mọi thao tác ghi** (POST/PUT/PATCH/DELETE) đều cần mức `day_du`.
- Ô "Duyệt" trong ma trận là tham chiếu sang chức năng duyệt tương ứng (AD12, DS10). Ô này **không** cấp quyền lập chứng từ.

## 3. Ma trận theo chức năng
Ký hiệu:
- ✔ = được thực hiện.
- Xem = chỉ xem.
- Duyệt = phê duyệt qua chức năng duyệt.
- trống = không có quyền.

Khách thành viên kế thừa toàn bộ quyền của khách vãng lai.

#### Khách vãng lai

| Mã | Chức năng | Mã quyền | Vãng lai | Thành viên | Dược sĩ | Kho | Admin | Phạm vi dữ liệu / điều kiện |
|---|---|---|:-:|:-:|:-:|:-:|:-:|---|
| KVL01 | Xem trang chủ, danh mục | (công khai) | ✔ | ✔ |  |  |  | Chỉ sản phẩm đang kinh doanh, chưa xóa. |
| KVL02 | Lọc, sắp xếp sản phẩm | (công khai) | ✔ | ✔ |  |  |  | Như KVL01. |
| KVL03 | Xem chi tiết sản phẩm | (công khai) | ✔ | ✔ |  |  |  | Chỉ nội dung chuyên môn phiên bản đã duyệt. |
| KVL04 | Tìm kiếm thông minh | (công khai) | ✔ | ✔ |  |  |  | Thuốc kê đơn hiển thị nhưng gắn nhãn "Cần tư vấn". |
| KVL05 | Chat với trợ lý AI | (công khai) | ✔ | ✔ |  |  |  | Giới hạn lượt theo phiên/IP (ip_hash). |
| KVL06 | Tra cứu thuốc bằng ảnh | (công khai) | ✔ | ✔ |  |  |  | Giới hạn lượt theo phiên/IP. |
| KVL07 | Quản lý giỏ hàng | (công khai) | ✔ | ✔ |  |  |  | Vãng lai: localStorage; thành viên: giỏ của chính mình. |
| KVL08 | Gửi yêu cầu tư vấn đơn thuốc | (công khai) | ✔ | ✔ |  |  |  | SĐT xác thực OTP; giới hạn số yêu cầu/SĐT/ngày. |
| KVL09 | Đăng ký tài khoản | (công khai) | ✔ |  |  |  |  | Giới hạn gửi OTP theo SĐT/IP. |
| KVL10 | Đăng nhập, quên mật khẩu | (công khai) | ✔ | ✔ |  |  |  | Khóa tạm sau nhiều lần sai. |
| KVL11 | Xem bài viết sức khỏe, chính sách, FAQ | (công khai) | ✔ | ✔ |  |  |  | Chỉ bài đã duyệt. |

#### Khách thành viên (kế thừa toàn bộ quyền khách vãng lai)

| Mã | Chức năng | Mã quyền | Vãng lai | Thành viên | Dược sĩ | Kho | Admin | Phạm vi dữ liệu / điều kiện |
|---|---|---|:-:|:-:|:-:|:-:|:-:|---|
| KTV01 | Quản lý hồ sơ, sổ địa chỉ | (kiểm tra trong code) |  | ✔ |  |  |  | Chỉ dữ liệu của chính mình: khach_hang_id lấy từ token, không nhận từ client. |
| KTV02 | Đặt hàng | (kiểm tra trong code) |  | ✔ |  |  |  | Chỉ dữ liệu của chính mình: khach_hang_id lấy từ token, không nhận từ client. Không đặt được thuốc kê đơn. |
| KTV03 | Thanh toán online | (kiểm tra trong code) |  | ✔ |  |  |  | Chỉ dữ liệu của chính mình: khach_hang_id lấy từ token, không nhận từ client. |
| KTV04 | Áp dụng mã giảm giá | (kiểm tra trong code) |  | ✔ |  |  |  | Giới hạn lượt/khách. |
| KTV05 | Theo dõi đơn hàng | (kiểm tra trong code) |  | ✔ |  |  |  | Chỉ dữ liệu của chính mình: khach_hang_id lấy từ token, không nhận từ client. |
| KTV06 | Hủy đơn hàng | (kiểm tra trong code) |  | ✔ |  |  |  | Chỉ dữ liệu của chính mình: khach_hang_id lấy từ token, không nhận từ client. Chỉ trước "Đang soạn hàng". |
| KTV07 | Gửi yêu cầu tư vấn đơn thuốc | (kiểm tra trong code) |  | ✔ |  |  |  | Chỉ dữ liệu của chính mình: khach_hang_id lấy từ token, không nhận từ client. |
| KTV08 | Lịch sử mua, mua lại | (kiểm tra trong code) |  | ✔ |  |  |  | Chỉ dữ liệu của chính mình: khach_hang_id lấy từ token, không nhận từ client. |
| KTV09 | Yêu cầu đổi trả | (kiểm tra trong code) |  | ✔ |  |  |  | Chỉ dữ liệu của chính mình: khach_hang_id lấy từ token, không nhận từ client. Trong thời hạn đổi trả. |
| KTV10 | Đánh giá sản phẩm | (kiểm tra trong code) |  | ✔ |  |  |  | Chỉ dòng đơn của mình đã giao/hoàn tất. |
| KTV11 | Hồ sơ sức khỏe | (kiểm tra trong code) |  | ✔ |  |  |  | Chỉ dữ liệu của chính mình: khach_hang_id lấy từ token, không nhận từ client. Xóa được bất kỳ lúc nào. |
| KTV12 | Chat trực tiếp với dược sĩ | (kiểm tra trong code) |  | ✔ |  |  |  | Chỉ dữ liệu của chính mình: khach_hang_id lấy từ token, không nhận từ client. |
| KTV13 | Nhận thông báo | (kiểm tra trong code) |  | ✔ |  |  |  | Chỉ dữ liệu của chính mình: khach_hang_id lấy từ token, không nhận từ client. |
| KTV14 | Nhắc mua lại | (kiểm tra trong code) |  | ✔ |  |  |  | Chỉ dữ liệu của chính mình: khach_hang_id lấy từ token, không nhận từ client. |
| KTV15 | Đặt câu hỏi về sản phẩm | (kiểm tra trong code) |  | ✔ |  |  |  | Sửa/xóa câu hỏi của chính mình khi chưa được trả lời. |

#### Nhân viên (chung cho Dược sĩ, Nhân viên kho, Admin)

| Mã | Chức năng | Mã quyền | Vãng lai | Thành viên | Dược sĩ | Kho | Admin | Phạm vi dữ liệu / điều kiện |
|---|---|---|:-:|:-:|:-:|:-:|:-:|---|
| NV01 | Đăng nhập, đổi mật khẩu | `profile.self` |  |  | ✔ | ✔ | ✔ | Tài khoản của chính mình. |
| NV02 | Xem thông báo, cập nhật hồ sơ cá nhân | `profile.self` |  |  | ✔ | ✔ | ✔ | Thông báo gửi cho chính mình. |

#### Dược sĩ bán hàng

| Mã | Chức năng | Mã quyền | Vãng lai | Thành viên | Dược sĩ | Kho | Admin | Phạm vi dữ liệu / điều kiện |
|---|---|---|:-:|:-:|:-:|:-:|:-:|---|
| DS01 | Xem, lọc danh sách đơn hàng | `order.view` |  |  | ✔ | Xem | Xem | Kho chỉ thấy đơn từ "Đã xác nhận" trở đi và thông tin giao hàng của khách (tên, SĐT, địa chỉ). |
| DS02 | Xác nhận đơn hàng | `order.confirm` |  |  | ✔ |  |  | Đơn ở "Chờ xác nhận". |
| DS03 | Hủy đơn hàng | `order.cancel` |  |  | ✔ |  |  | Trước khi hàng rời kho; bắt buộc lý do. |
| DS04 | Duyệt yêu cầu đơn thuốc | `rx_request.review` |  |  | ✔ |  |  | Chỉ yêu cầu đang khóa cho mình; xem hồ sơ sức khỏe của khách trong lúc xử lý. |
| DS05 | Tạo đơn hàng từ đơn thuốc | `rx_order.create` |  |  | ✔ |  |  | Từ yêu cầu mình đang xử lý. |
| DS06 | Tư vấn trực tiếp | `chat.handle` |  |  | ✔ |  |  | Phiên được chuyển cho mình; xem hồ sơ sức khỏe nếu khách đã đồng ý. |
| DS07 | Tạo đơn hộ khách | `order.create_phone` |  |  | ✔ |  |  | Không áp dụng thuốc kê đơn. |
| DS08 | Bán tại quầy – POS | `pos.sell` |  |  | ✔ |  |  | Được bán lô cận hạn; thuốc kê đơn cần yêu cầu kênh tại quầy. |
| DS09 | Xử lý yêu cầu đổi trả | `return.review` |  |  | ✔ |  |  | Không tự xác nhận chuyển tiền (AD17). |
| DS10 | Biên soạn, duyệt nội dung chuyên môn | `content.professional.edit`, `content.approve` |  |  | ✔ |  | Xem | Admin chỉ xem nội dung chuyên môn. |
| DS11 | Kiểm duyệt đánh giá, hỏi đáp | `review.moderate`, `qa.answer` |  |  | ✔ |  |  |  |
| DS12 | Đánh giá câu trả lời AI | `ai_answer.review` |  |  | ✔ |  | Xem | Hội thoại bị gắn cờ. |
| DS13 | Liên hệ khách khi thu hồi lô | `recall.contact` |  |  | ✔ |  | Xem | Chỉ khách thuộc lệnh thu hồi đang mở. |
| DS14 | Báo cáo bán hàng của ca | `report.shift` |  |  | ✔ |  |  | Số liệu do chính mình xử lý; không có giá vốn/lợi nhuận. |
| DS15 | Giao đơn nhận tại nhà thuốc | `order.pickup_handover` |  |  | ✔ |  |  | Đơn nhận tại nhà thuốc ở "Chờ lấy hàng". |

#### Nhân viên kho

| Mã | Chức năng | Mã quyền | Vãng lai | Thành viên | Dược sĩ | Kho | Admin | Phạm vi dữ liệu / điều kiện |
|---|---|---|:-:|:-:|:-:|:-:|:-:|---|
| KHO01 | Quản lý nhà cung cấp | `supplier.manage` |  |  |  | ✔ | Xem | Ngừng giao dịch = xóa mềm. |
| KHO02 | Lập phiếu nhập kho | `stock.import` |  |  |  | ✔ | Xem | Phiếu đã lưu không sửa/xóa. |
| KHO03 | Soạn hàng, xuất kho theo đơn | `order.pick` |  |  |  | ✔ |  | Đơn "Đã xác nhận"; đổi lô phải ghi lý do. |
| KHO04 | Đóng gói, bàn giao vận chuyển | `shipment.create` |  |  |  | ✔ |  |  |
| KHO05 | Tra cứu tồn kho | `stock.view` |  |  | Xem | ✔ | Xem | Dược sĩ xem tồn khả dụng, không xem giá nhập. |
| KHO06 | Xem cảnh báo | `stock.alert.view` |  |  |  | ✔ | Xem |  |
| KHO07 | Kiểm kê | `stocktake.manage` |  |  |  | ✔ | Xem |  |
| KHO08 | Lập phiếu điều chỉnh tồn | `stock_adjust.create` |  |  |  | ✔ | Duyệt | Người lập không tự duyệt. |
| KHO09 | Lập phiếu hủy hàng | `disposal.create` |  |  |  | ✔ | Duyệt | Người lập không tự duyệt. |
| KHO10 | Nhận hàng trả về, hàng hoàn | `return.receive` |  |  |  | ✔ |  | Yêu cầu đổi trả đã duyệt, đơn hoàn về kho. |
| KHO11 | Xuất trả nhà cung cấp | `supplier_return.create` |  |  |  | ✔ | Duyệt | Người lập không tự duyệt. |
| KHO12 | Thực hiện thu hồi lô | `recall.execute` |  |  |  | ✔ | Xem | Lệnh thu hồi đang mở. |
| KHO13 | Báo cáo nhập, xuất, tồn | `report.inventory` |  |  |  | ✔ | Xem |  |
| KHO14 | Xem đề xuất nhập hàng từ AI | `forecast.view` |  |  |  | ✔ | Xem |  |

#### Admin

| Mã | Chức năng | Mã quyền | Vãng lai | Thành viên | Dược sĩ | Kho | Admin | Phạm vi dữ liệu / điều kiện |
|---|---|---|:-:|:-:|:-:|:-:|:-:|---|
| AD01 | Quản lý tài khoản nhân viên | `staff.manage` |  |  |  |  | ✔ | Không tự khóa/hạ quyền chính mình; luôn còn ≥ 1 Admin. |
| AD02 | Quản lý khách hàng | `customer.manage` |  |  |  |  | ✔ | Không xem hồ sơ sức khỏe, dị ứng. |
| AD03 | Quản lý danh mục | `category.manage` |  |  |  |  | ✔ |  |
| AD04 | Quản lý sản phẩm – thông tin thương mại | `product.commercial.manage` |  |  |  |  | ✔ | Không sửa nội dung chuyên môn. |
| AD05 | Quản lý hoạt chất, thương hiệu, nhà sản xuất | `master_data.manage` |  |  | Xem |  | ✔ |  |
| AD06 | Quản lý khuyến mãi, mã giảm giá | `promotion.manage` |  |  |  |  | ✔ | Không áp dụng cho thuốc kê đơn. |
| AD07 | Quản lý banner, bài viết, chính sách, FAQ | `cms.manage` |  |  | Duyệt |  | ✔ | Bài sức khỏe cần dược sĩ duyệt. |
| AD08 | Cấu hình hệ thống | `config.manage` |  |  |  |  | ✔ |  |
| AD09 | Cấu hình AI | `ai.config` |  |  |  |  | ✔ |  |
| AD10 | Đồng bộ kho tri thức AI | `ai.knowledge.sync` |  |  |  |  | ✔ | Chỉ nội dung đã duyệt; không đưa giá/tồn vào vector. |
| AD11 | Giám sát hội thoại AI | `ai.monitor` |  |  |  |  | ✔ | Hội thoại đã ẩn danh. |
| AD12 | Duyệt phiếu hủy, điều chỉnh tồn, xuất trả NCC | `stock_doc.approve` |  |  |  |  | ✔ | Người duyệt khác người lập. |
| AD13 | Khởi tạo lệnh thu hồi lô | `recall.create` |  |  |  |  | ✔ |  |
| AD16 | Xem đơn hàng, chứng từ kho, nội dung chuyên môn | `order.view`, `stock_doc.view`, `content.view` |  |  |  |  | Xem | Chỉ xem, không sửa. |
| AD14 | Báo cáo thống kê tổng hợp | `report.all` |  |  |  |  | ✔ |  |
| AD15 | Xem nhật ký hệ thống | `audit.view` |  |  |  |  | ✔ |  |
| AD17 | Xác nhận hoàn tiền | `refund.confirm` |  |  |  |  | ✔ | Người xác nhận khác dược sĩ duyệt đổi trả. |
| AD18 | Quản lý vai trò & phân quyền | `role.manage` |  |  |  |  | ✔ | Không bỏ quyền của vai trò ADMIN. |

#### Hệ thống - tác vụ tự động (không phải tác nhân)

| Mã | Chức năng | Mã quyền | Vãng lai | Thành viên | Dược sĩ | Kho | Admin | Phạm vi dữ liệu / điều kiện |
|---|---|---|:-:|:-:|:-:|:-:|:-:|---|
| HT01 | Cập nhật trạng thái lô hằng ngày | (tài khoản dịch vụ) |  |  |  |  |  |  |
| HT02 | Cảnh báo tồn thấp, cận hạn | (tài khoản dịch vụ) |  |  |  |  |  |  |
| HT03 | Hủy đơn quá hạn | (tài khoản dịch vụ) |  |  |  |  |  |  |
| HT04 | Xử lý IPN thanh toán | (tài khoản dịch vụ) |  |  |  |  |  | Xác thực chữ ký cổng thanh toán. |
| HT05 | Nhận webhook vận chuyển | (tài khoản dịch vụ) |  |  |  |  |  | Xác thực token webhook. |
| HT06 | Máy trạng thái đơn hàng | (tài khoản dịch vụ) |  |  |  |  |  |  |
| HT07 | Gửi thông báo, nhắc mua lại | (tài khoản dịch vụ) |  |  |  |  |  |  |
| HT08 | Tự hoàn tất đơn, nhả khóa | (tài khoản dịch vụ) |  |  |  |  |  |  |

#### Module AI (dùng chung, gắn vào các chức năng)

| Mã | Chức năng | Mã quyền | Vãng lai | Thành viên | Dược sĩ | Kho | Admin | Phạm vi dữ liệu / điều kiện |
|---|---|---|:-:|:-:|:-:|:-:|:-:|---|
| AI01 | Tìm kiếm thông minh | (tài khoản dịch vụ) |  |  |  |  |  |  |
| AI02 | Phân loại ý định, phát hiện dấu hiệu nguy hiểm | (tài khoản dịch vụ) |  |  |  |  |  |  |
| AI03 | Trả lời bằng RAG | (tài khoản dịch vụ) |  |  |  |  |  | Chỉ đọc hồ sơ sức khỏe khi khách đã đồng ý. |
| AI04 | Tóm tắt, chuyển dược sĩ | (tài khoản dịch vụ) |  |  |  |  |  |  |
| AI05 | Nhận diện hộp thuốc từ ảnh | (tài khoản dịch vụ) |  |  |  |  |  |  |
| AI06 | Đọc ảnh đơn thuốc | (tài khoản dịch vụ) |  |  |  |  |  |  |
| AI07 | Gợi ý sản phẩm tương tự, dành cho bạn | (tài khoản dịch vụ) |  |  |  |  |  |  |
| AI08 | Gợi ý mua kèm | (tài khoản dịch vụ) |  |  |  |  |  |  |
| AI09 | Dự báo nhu cầu, đề xuất nhập hàng | (tài khoản dịch vụ) |  |  |  |  |  |  |

## 4. Danh sách mã quyền
| Mã quyền | Chức năng | PHARMACIST | WAREHOUSE | ADMIN |
|---|---|:-:|:-:|:-:|
| `profile.self` | NV01, NV02 | day_du | day_du | day_du |
| `order.view` | DS01, AD16 | day_du | chi_xem | chi_xem |
| `order.confirm` | DS02 | day_du |  |  |
| `order.cancel` | DS03 | day_du |  |  |
| `rx_request.review` | DS04 | day_du |  |  |
| `rx_order.create` | DS05 | day_du |  |  |
| `chat.handle` | DS06 | day_du |  |  |
| `order.create_phone` | DS07 | day_du |  |  |
| `pos.sell` | DS08 | day_du |  |  |
| `return.review` | DS09 | day_du |  |  |
| `content.professional.edit` | DS10 | day_du |  | chi_xem |
| `content.approve` | DS10 | day_du |  | chi_xem |
| `review.moderate` | DS11 | day_du |  |  |
| `qa.answer` | DS11 | day_du |  |  |
| `ai_answer.review` | DS12 | day_du |  | chi_xem |
| `recall.contact` | DS13 | day_du |  | chi_xem |
| `report.shift` | DS14 | day_du |  |  |
| `order.pickup_handover` | DS15 | day_du |  |  |
| `supplier.manage` | KHO01 |  | day_du | chi_xem |
| `stock.import` | KHO02 |  | day_du | chi_xem |
| `order.pick` | KHO03 |  | day_du |  |
| `shipment.create` | KHO04 |  | day_du |  |
| `stock.view` | KHO05 | chi_xem | day_du | chi_xem |
| `stock.alert.view` | KHO06 |  | day_du | chi_xem |
| `stocktake.manage` | KHO07 |  | day_du | chi_xem |
| `stock_adjust.create` | KHO08 |  | day_du |  |
| `disposal.create` | KHO09 |  | day_du |  |
| `return.receive` | KHO10 |  | day_du |  |
| `supplier_return.create` | KHO11 |  | day_du |  |
| `recall.execute` | KHO12 |  | day_du | chi_xem |
| `report.inventory` | KHO13 |  | day_du | chi_xem |
| `forecast.view` | KHO14 |  | day_du | chi_xem |
| `staff.manage` | AD01 |  |  | day_du |
| `customer.manage` | AD02 |  |  | day_du |
| `category.manage` | AD03 |  |  | day_du |
| `product.commercial.manage` | AD04 |  |  | day_du |
| `master_data.manage` | AD05 | chi_xem |  | day_du |
| `promotion.manage` | AD06 |  |  | day_du |
| `cms.manage` | AD07 |  |  | day_du |
| `config.manage` | AD08 |  |  | day_du |
| `ai.config` | AD09 |  |  | day_du |
| `ai.knowledge.sync` | AD10 |  |  | day_du |
| `ai.monitor` | AD11 |  |  | day_du |
| `stock_doc.approve` | AD12 |  |  | day_du |
| `recall.create` | AD13 |  |  | day_du |
| `stock_doc.view` | AD16 |  |  | chi_xem |
| `content.view` | AD16 |  |  | chi_xem |
| `report.all` | AD14 |  |  | day_du |
| `audit.view` | AD15 |  |  | day_du |
| `refund.confirm` | AD17 |  |  | day_du |
| `role.manage` | AD18 |  |  | day_du |

Tổng: 51 mã quyền, 69 cặp vai trò – quyền (`day_du` = được thao tác, `chi_xem` = chỉ xem).

## 5. Dữ liệu nhạy cảm
### 5.1 Hồ sơ sức khỏe (`ho_so_suc_khoe`, `di_ung`)
Đây là dữ liệu cá nhân nhạy cảm theo Nghị định 13/2023/NĐ-CP.

- **Khách hàng:** toàn quyền với hồ sơ của mình. Xóa thì xóa cứng hai bảng này.
- **Admin, nhân viên kho:** không bao giờ đọc được. Mọi response nội bộ không chứa các trường này. Có test khẳng định.
- **Dược sĩ:** chỉ được đọc qua hàm cổng `suc_khoe.service.duoc_doc_ho_so_suc_khoe(db, nhan_vien, khach_hang_id) -> bool`. Hàm trả `True` khi **đồng thời**:
  1. Nhân viên có vai trò `PHARMACIST`.
  2. Hồ sơ của khách có `dong_y_su_dung = true`.
  3. Có ít nhất một trong hai điều kiện sau:
     - `yeu_cau_don_thuoc` của khách đó đang `dang_tu_van` với `duoc_si_id = nhan_vien.id`.
     - `hoi_thoai` của khách đó đang `duoc_si_dang_xu_ly` với `duoc_si_id = nhan_vien.id`.
- **Mỗi lần đọc qua hàm cổng:** ghi `nhat_ky_he_thong` (`hanh_dong = 'doc_suc_khoe'`, `bang = 'ho_so_suc_khoe'`, `ban_ghi_id = khach_hang_id`, không ghi giá trị).
- **Kiểm tra tự động** như `kiem_tra_di_ung(...)` hay lọc gợi ý AI được đọc dữ liệu bên trong service, nhưng chỉ trả **cảnh báo** (ví dụ "chứa Amoxicillin – khách khai dị ứng"), không trả hồ sơ.
- **`benh_nen`** mã hóa mức ứng dụng (Fernet, khóa `KHOA_MA_HOA`).

### 5.2 Dữ liệu kinh doanh
- **`lo_thuoc.gia_nhap`, `phan_bo_lo.gia_von`, lợi nhuận:** chỉ `WAREHOUSE` và `ADMIN` thấy. Schema response cho `PHARMACIST` bỏ các trường này.
- **`thanh_toan.thong_tin_nhan_hoan`:** chỉ Admin thấy khi xử lý hoàn tiền. Ẩn danh hóa sau khi hoàn tất.

## 6. Phạm vi dữ liệu
| Dữ liệu | Khách | Dược sĩ | Nhân viên kho | Admin |
|---|---|---|---|---|
| Đơn hàng | Của mình (đơn người khác → 404) | Tất cả | Từ `da_xac_nhan` trở đi; với khách chỉ thấy tên, SĐT, địa chỉ giao | Xem tất cả |
| Yêu cầu đơn thuốc và ảnh | Của mình | Hàng chờ + yêu cầu mình đang/đã xử lý; ảnh qua URL ký có hạn | Không | Không |
| Hồ sơ sức khỏe | Của mình | Qua hàm cổng (mục 5.1) | Không | Không |
| Hội thoại tư vấn | Của mình (theo `ma_phien` hoặc tài khoản) | Phiên chuyển cho mình; phiên bị gắn cờ (DS12) | Không | Bản đã ẩn danh (AD11) |
| Thông tin liên hệ khách | Của mình | Có (để tư vấn, giao, thu hồi) | Trên đơn cần giao | Có |
| Chứng từ kho | Không | Không | Tất cả | Xem tất cả + duyệt |
| Nhật ký hệ thống | Không | Không | Không | Có |

Khách vãng lai gửi đơn thuốc (KVL08) chỉ xem lại được kết quả qua link có mã truy cập gửi bằng SMS.

## 7. Tách nhiệm vụ
| Quy tắc | Thực thi |
|---|---|
| Phiếu điều chỉnh, hủy, xuất trả: người duyệt ≠ người lập | CHECK trong DB + service trả `TU_DUYET_KHONG_DUOC` |
| Hoàn tiền: Admin xác nhận ≠ dược sĩ đã duyệt đổi trả (`yeu_cau_doi_tra.duoc_si_id`) | Mỗi nhân viên có 1 vai trò nên điều này được bảo đảm sẵn. Service AD17 vẫn kiểm tra, phòng khi sau này cho phép kiêm nhiệm |
| Admin không sửa nội dung chuyên môn; bài viết sức khỏe phải được dược sĩ duyệt | Quyền `content.professional.edit` và `content.approve` chỉ PHARMACIST có |
| Admin chỉ xem đơn hàng và chứng từ kho, không thao tác | Mức `chi_xem` |
| Admin không tự khóa/hạ quyền chính mình; luôn còn ≥ 1 Admin hoạt động | Service AD01, AD18 (`PHAI_CON_ADMIN`) |
| AI không thực hiện thao tác ghi nghiệp vụ | Tool của chatbot chỉ đọc (spec 07 mục 4) |

## 8. Thực thi trong code
- **`core/phan_quyen.py` cung cấp:**
  - `khach_hien_tai`: bắt buộc đăng nhập, `aud = khach`, tài khoản `hoat_dong`, không bị `khoa_den`.
  - `khach_tuy_chon`: cho route công khai cần biết khách nếu có.
  - `nhan_vien_hien_tai`: `aud = noi_bo`, tài khoản hoạt động, không `phai_doi_mat_khau` (trừ route đổi mật khẩu).
  - `yeu_cau_quyen(ma: str, muc: Literal["xem", "day_du"] = "day_du")`: dependency trả `NhanVien`. Quyền của vai trò đọc từ DB, cache trong process 60 giây. Thiếu quyền → 403 `KHONG_CO_QUYEN`.
- **Trạng thái tài khoản kiểm tra ở mỗi request**, nên khóa tài khoản có hiệu lực ngay, không chờ access token hết hạn. Đồng thời mọi `phien_dang_nhap` của tài khoản bị thu hồi.
- **Kiểm tra sở hữu:** service nhận `khach_hang_id` từ dependency và lọc trong truy vấn (`WHERE khach_hang_id = :id`). Không lấy ra rồi mới so sánh.
- **Frontend** đọc danh sách quyền từ `GET /api/v1/noi-bo/toi` để ẩn/hiện menu và nút. Đây chỉ là lớp phụ.

## 9. Kiểm thử
Xem spec 10 mục 3, gồm:
- Test ma trận tự sinh từ `quyen.yaml` cho mọi route `/noi-bo`.
- Test 404 khi truy cập dữ liệu của khách khác.
- Test không lộ dữ liệu sức khỏe và giá vốn.
- Test tách nhiệm vụ.

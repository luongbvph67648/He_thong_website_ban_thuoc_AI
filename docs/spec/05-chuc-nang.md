# 05. Danh mục chức năng

> Sinh tự động từ sheet "Chức năng & Database" (bản đã chỉnh sửa) và ma trận phân quyền. Sửa mô tả ở đây thì cập nhật cả ma trận (spec 03) nếu quyền hoặc phạm vi thay đổi.

Tổng cộng 92 chức năng:
- 75 chức năng của tác nhân.
- 8 tác vụ hệ thống.
- 9 module AI.

Mỗi chức năng ghi: ai thực hiện, mô tả, mã quyền, phạm vi dữ liệu, bảng dữ liệu và task triển khai trong `11-lo-trinh.md`.

## Khách vãng lai

### KVL01 · Xem trang chủ, danh mục
- **Thực hiện:** Khách vãng lai, Khách thành viên
- **Mô tả:** Hiển thị banner, sản phẩm nổi bật, bán chạy; duyệt sản phẩm theo cây danh mục nhiều cấp.
- **Mã quyền:** (công khai)
- **Phạm vi / điều kiện:** Chỉ sản phẩm đang kinh doanh, chưa xóa.
- **Bảng:** `banner`, `danh_muc`, `san_pham`, `anh_san_pham`, `don_vi_quy_doi`
- **Task:** T2.4

### KVL02 · Lọc, sắp xếp sản phẩm
- **Thực hiện:** Khách vãng lai, Khách thành viên
- **Mô tả:** Lọc theo danh mục, loại sản phẩm, thương hiệu, khoảng giá, đối tượng sử dụng; sắp xếp danh sách kết quả.
- **Mã quyền:** (công khai)
- **Phạm vi / điều kiện:** Như KVL01.
- **Bảng:** `san_pham`, `danh_muc`, `thuong_hieu`, `don_vi_quy_doi`
- **Task:** T2.4

### KVL03 · Xem chi tiết sản phẩm
- **Thực hiện:** Khách vãng lai, Khách thành viên
- **Mô tả:** Hiển thị thông tin có cấu trúc (hoạt chất, hàm lượng, chỉ định, chống chỉ định, liều tham khảo, bảo quản), giá theo từng đơn vị tính, tình trạng còn hàng, đánh giá, sản phẩm tương tự. Thuốc kê đơn không có nút thêm vào giỏ mà thay bằng nút "Cần tư vấn từ dược sĩ"; thực phẩm chức năng có dòng lưu ý "không phải là thuốc".
- **Mã quyền:** (công khai)
- **Phạm vi / điều kiện:** Chỉ nội dung chuyên môn phiên bản đã duyệt.
- **Bảng:** `san_pham`, `thong_tin_chuyen_mon`, `thanh_phan`, `hoat_chat`, `nha_san_xuat`, `don_vi_quy_doi`, `anh_san_pham`, `lo_thuoc`, `danh_gia`, `hoi_dap`, `lich_su_xem`
- **Task:** T2.4

### KVL04 · Tìm kiếm thông minh
- **Thực hiện:** Khách vãng lai, Khách thành viên
- **Mô tả:** Tìm được khi gõ không dấu, sai chính tả, theo hoạt chất, theo triệu chứng hoặc công dụng; gợi ý từ khóa khi đang gõ. Kết quả ưu tiên sản phẩm còn hàng, bán chạy; thuốc kê đơn vẫn hiển thị nhưng gắn nhãn "Cần tư vấn". Khi dịch vụ AI lỗi, hệ thống tự quay về tìm theo từ khóa.
- **Mã quyền:** (công khai)
- **Phạm vi / điều kiện:** Thuốc kê đơn hiển thị nhưng gắn nhãn "Cần tư vấn".
- **Bảng:** `san_pham`, `hoat_chat`, `thanh_phan`, `tai_lieu_tri_thuc`, `lich_su_tim_kiem`
- **Task:** T2.5

### KVL05 · Chat với trợ lý AI
- **Thực hiện:** Khách vãng lai, Khách thành viên
- **Mô tả:** Hỏi đáp 24/7 về sản phẩm, cách dùng, triệu chứng nhẹ, chính sách. AI không chẩn đoán, không đưa liều cá nhân hóa, không gợi ý thuốc kê đơn; phát hiện dấu hiệu nguy hiểm thì dừng tư vấn và khuyên đi khám hoặc gọi 115. Có nút "Gặp dược sĩ" và nút báo câu trả lời sai. Giới hạn số câu hỏi theo phiên/IP để chống lạm dụng chi phí AI.
- **Mã quyền:** (công khai)
- **Phạm vi / điều kiện:** Giới hạn lượt theo phiên/IP (ip_hash).
- **Bảng:** `hoi_thoai`, `tin_nhan`, `tai_lieu_tri_thuc`, `danh_gia_cau_tra_loi`
- **Task:** T7.3

### KVL06 · Tra cứu thuốc bằng ảnh
- **Thực hiện:** Khách vãng lai, Khách thành viên
- **Mô tả:** Chụp ảnh hộp thuốc, hệ thống đọc tên, hoạt chất, hàm lượng, số đăng ký rồi đối chiếu CSDL để mở trang sản phẩm kèm tóm tắt dễ hiểu. Nếu không có trong CSDL thì chỉ hiển thị thông tin đọc được kèm cảnh báo chưa xác minh. Giới hạn số lượt tra cứu theo phiên/IP.
- **Mã quyền:** (công khai)
- **Phạm vi / điều kiện:** Giới hạn lượt theo phiên/IP.
- **Bảng:** `san_pham`, `thong_tin_chuyen_mon`
- **Task:** T7.5

### KVL07 · Quản lý giỏ hàng
- **Thực hiện:** Khách vãng lai, Khách thành viên
- **Mô tả:** Thêm, sửa số lượng, đổi đơn vị tính, xóa sản phẩm. Khách vãng lai lưu giỏ trên trình duyệt (localStorage); khi đăng nhập, giỏ được gộp vào giỏ của tài khoản. Không thêm được thuốc kê đơn; mỗi sản phẩm bị giới hạn số lượng tối đa mỗi đơn theo cấu hình của sản phẩm. Hiển thị gợi ý "Thường được mua cùng".
- **Mã quyền:** (công khai)
- **Phạm vi / điều kiện:** Vãng lai: localStorage; thành viên: giỏ của chính mình.
- **Bảng:** `gio_hang`, `ct_gio_hang`, `san_pham`, `don_vi_quy_doi`, `luat_mua_kem`
- **Task:** T4.1

### KVL08 · Gửi yêu cầu tư vấn đơn thuốc
- **Thực hiện:** Khách vãng lai, Khách thành viên
- **Mô tả:** Tải ảnh đơn thuốc, nhập họ tên, SĐT và ghi chú mà không cần tài khoản; SĐT phải xác thực bằng OTP để chống spam. Yêu cầu vào hàng chờ ở trạng thái "Chờ duyệt"; kết quả và link xác nhận đơn hàng (nếu có) được gửi qua SMS.
- **Mã quyền:** (công khai)
- **Phạm vi / điều kiện:** SĐT xác thực OTP; giới hạn số yêu cầu/SĐT/ngày.
- **Bảng:** `yeu_cau_don_thuoc`, `ct_yeu_cau_don_thuoc`, `ma_otp`
- **Task:** T5.2

### KVL09 · Đăng ký tài khoản
- **Thực hiện:** Khách vãng lai
- **Mô tả:** Đăng ký bằng SĐT (bắt buộc, xác thực bằng mã OTP); email tùy chọn, dùng để nhận thông báo và lấy lại mật khẩu.
- **Mã quyền:** (công khai)
- **Phạm vi / điều kiện:** Giới hạn gửi OTP theo SĐT/IP.
- **Bảng:** `khach_hang`, `ma_otp`
- **Task:** T1.1

### KVL10 · Đăng nhập, quên mật khẩu
- **Thực hiện:** Khách vãng lai, Khách thành viên
- **Mô tả:** Đăng nhập bằng tài khoản đã đăng ký, khóa tạm khi nhập sai nhiều lần; lấy lại mật khẩu qua OTP gửi email hoặc SMS.
- **Mã quyền:** (công khai)
- **Phạm vi / điều kiện:** Khóa tạm sau nhiều lần sai.
- **Bảng:** `khach_hang`, `ma_otp`, `phien_dang_nhap`
- **Task:** T1.2

### KVL11 · Xem bài viết sức khỏe, chính sách, FAQ
- **Thực hiện:** Khách vãng lai, Khách thành viên
- **Mô tả:** Đọc bài viết sức khỏe đã được dược sĩ duyệt, các trang chính sách (đổi trả, giao hàng, bảo mật) và câu hỏi thường gặp. Cùng nguồn dữ liệu với kho tri thức AI.
- **Mã quyền:** (công khai)
- **Phạm vi / điều kiện:** Chỉ bài đã duyệt.
- **Bảng:** `bai_viet`
- **Task:** T2.6

## Khách thành viên (kế thừa toàn bộ quyền khách vãng lai)

### KTV01 · Quản lý hồ sơ, sổ địa chỉ
- **Thực hiện:** Khách thành viên
- **Mô tả:** Cập nhật thông tin cá nhân, đổi mật khẩu; thêm, sửa, xóa nhiều địa chỉ nhận hàng và chọn địa chỉ mặc định.
- **Mã quyền:** (kiểm tra trong code)
- **Phạm vi / điều kiện:** Chỉ dữ liệu của chính mình: khach_hang_id lấy từ token, không nhận từ client.
- **Bảng:** `khach_hang`, `dia_chi`
- **Task:** T4.1

### KTV02 · Đặt hàng
- **Thực hiện:** Khách thành viên
- **Mô tả:** Chọn giao tận nơi hoặc nhận tại nhà thuốc, chọn phương thức thanh toán (COD, VNPay, MoMo), xem phí ship tính qua API vận chuyển. Máy chủ kiểm tra lại tồn khả dụng (chỉ lô đang bán, không dùng lô cận hạn), giá, khuyến mãi và giới hạn số lượng tại thời điểm đặt, rồi tạo đơn và giữ hàng trên lô theo FEFO. Đơn COD vào "Chờ xác nhận", đơn thanh toán online vào "Chờ thanh toán".
- **Mã quyền:** (kiểm tra trong code)
- **Phạm vi / điều kiện:** Chỉ dữ liệu của chính mình: khach_hang_id lấy từ token, không nhận từ client. Không đặt được thuốc kê đơn.
- **Bảng:** `gio_hang`, `ct_gio_hang`, `don_hang`, `ct_don_hang`, `phan_bo_lo`, `lo_thuoc`, `dia_chi`, `khuyen_mai`, `khuyen_mai_pham_vi`, `ma_giam_gia`, `lich_su_trang_thai`
- **Task:** T4.4

### KTV03 · Thanh toán online
- **Thực hiện:** Khách thành viên
- **Mô tả:** Thanh toán qua VNPay hoặc MoMo, kết quả được xác nhận qua IPN phía máy chủ. Đơn quá thời hạn chờ thanh toán tự hủy và nhả hàng đã giữ.
- **Mã quyền:** (kiểm tra trong code)
- **Phạm vi / điều kiện:** Chỉ dữ liệu của chính mình: khach_hang_id lấy từ token, không nhận từ client.
- **Bảng:** `thanh_toan`, `don_hang`
- **Task:** T4.5

### KTV04 · Áp dụng mã giảm giá
- **Thực hiện:** Khách thành viên
- **Mô tả:** Nhập mã, hệ thống kiểm tra điều kiện (giá trị đơn tối thiểu, thời hạn, số lượt còn lại); không áp dụng cho thuốc kê đơn. Mỗi mã giới hạn số lượt cho mỗi khách (đếm theo các đơn chưa hủy); phần giảm giá được phân bổ vào từng dòng đơn để tính tiền hoàn khi trả một phần; đơn bị hủy thì trả lại lượt dùng.
- **Mã quyền:** (kiểm tra trong code)
- **Phạm vi / điều kiện:** Giới hạn lượt/khách.
- **Bảng:** `ma_giam_gia`, `khuyen_mai`, `khuyen_mai_pham_vi`
- **Task:** T4.3

### KTV05 · Theo dõi đơn hàng
- **Thực hiện:** Khách thành viên
- **Mô tả:** Xem dòng thời gian trạng thái đơn và mã vận đơn; các trạng thái giao hàng được cập nhật tự động từ đơn vị vận chuyển.
- **Mã quyền:** (kiểm tra trong code)
- **Phạm vi / điều kiện:** Chỉ dữ liệu của chính mình: khach_hang_id lấy từ token, không nhận từ client.
- **Bảng:** `don_hang`, `lich_su_trang_thai`, `van_don`
- **Task:** T4.7

### KTV06 · Hủy đơn hàng
- **Thực hiện:** Khách thành viên
- **Mô tả:** Khách hủy được khi đơn ở "Chờ khách xác nhận", "Chờ thanh toán", "Chờ xác nhận" hoặc "Đã xác nhận" (chưa sang "Đang soạn hàng"). Hệ thống nhả hàng giữ, trả lại lượt mã giảm giá; nếu đã thanh toán online thì tạo giao dịch hoàn tiền chờ Admin xác nhận (AD17).
- **Mã quyền:** (kiểm tra trong code)
- **Phạm vi / điều kiện:** Chỉ dữ liệu của chính mình: khach_hang_id lấy từ token, không nhận từ client. Chỉ trước "Đang soạn hàng".
- **Bảng:** `don_hang`, `phan_bo_lo`, `lo_thuoc`, `thanh_toan`, `ma_giam_gia`, `lich_su_trang_thai`
- **Task:** T4.6

### KTV07 · Gửi yêu cầu tư vấn đơn thuốc
- **Thực hiện:** Khách thành viên
- **Mô tả:** Như KVL08 nhưng gắn với tài khoản; theo dõi trạng thái (Chờ duyệt, Đang tư vấn, Đã tạo đơn hàng, Từ chối, Khách hủy), xem lại lịch sử đơn thuốc và xác nhận, thanh toán đơn hàng do dược sĩ tạo. Khi xác nhận đơn do dược sĩ tạo, khách chọn phương thức thanh toán; hàng chỉ được giữ đến hạn xác nhận.
- **Mã quyền:** (kiểm tra trong code)
- **Phạm vi / điều kiện:** Chỉ dữ liệu của chính mình: khach_hang_id lấy từ token, không nhận từ client.
- **Bảng:** `yeu_cau_don_thuoc`, `ct_yeu_cau_don_thuoc`, `don_hang`
- **Task:** T5.2

### KTV08 · Lịch sử mua, mua lại
- **Thực hiện:** Khách thành viên
- **Mô tả:** Xem danh sách đơn đã mua; bấm "Mua lại" để đưa nhanh sản phẩm từ đơn cũ vào giỏ (thuốc kê đơn vẫn phải qua luồng duyệt đơn).
- **Mã quyền:** (kiểm tra trong code)
- **Phạm vi / điều kiện:** Chỉ dữ liệu của chính mình: khach_hang_id lấy từ token, không nhận từ client.
- **Bảng:** `don_hang`, `ct_don_hang`, `gio_hang`, `ct_gio_hang`
- **Task:** T4.9

### KTV09 · Yêu cầu đổi trả
- **Thực hiện:** Khách thành viên
- **Mô tả:** Gửi yêu cầu trong thời hạn quy định: chọn sản phẩm và số lượng muốn trả (trả được một phần), lý do, ảnh/video mở hàng. Chỉ chấp nhận khi lỗi thuộc về nhà thuốc (giao sai sản phẩm, sai số lượng, hư hỏng, hết hạn hoặc cận hạn quá ngưỡng). Khi được duyệt, khách nhận mã vận đơn để gửi trả hàng; đơn đã trả bằng COD/tiền mặt thì khách nhập tài khoản nhận hoàn tiền. Theo dõi trạng thái yêu cầu.
- **Mã quyền:** (kiểm tra trong code)
- **Phạm vi / điều kiện:** Chỉ dữ liệu của chính mình: khach_hang_id lấy từ token, không nhận từ client. Trong thời hạn đổi trả.
- **Bảng:** `yeu_cau_doi_tra`, `ct_yeu_cau_doi_tra`, `van_don`, `thanh_toan`
- **Task:** T6.1

### KTV10 · Đánh giá sản phẩm
- **Thực hiện:** Khách thành viên
- **Mô tả:** Chấm sao và viết nhận xét cho sản phẩm thuộc đơn ở trạng thái "Đã giao" hoặc "Hoàn tất"; mỗi dòng đơn đánh giá một lần.
- **Mã quyền:** (kiểm tra trong code)
- **Phạm vi / điều kiện:** Chỉ dòng đơn của mình đã giao/hoàn tất.
- **Bảng:** `danh_gia`, `ct_don_hang`
- **Task:** T6.4

### KTV11 · Hồ sơ sức khỏe
- **Thực hiện:** Khách thành viên
- **Mô tả:** Khai báo dị ứng hoạt chất, bệnh nền, tình trạng mang thai hoặc cho con bú sau khi đồng ý sử dụng dữ liệu; xóa được bất kỳ lúc nào. Dữ liệu dùng để AI lọc gợi ý và dược sĩ đối chiếu khi duyệt đơn. Đây là dữ liệu cá nhân nhạy cảm: Admin không xem; dược sĩ chỉ xem khi đang xử lý yêu cầu đơn thuốc hoặc phiên chat của chính khách đó; AI chỉ dùng khi khách đã đồng ý. Hồ sơ dùng để cảnh báo dị ứng và tương tác thuốc.
- **Mã quyền:** (kiểm tra trong code)
- **Phạm vi / điều kiện:** Chỉ dữ liệu của chính mình: khach_hang_id lấy từ token, không nhận từ client. Xóa được bất kỳ lúc nào.
- **Bảng:** `ho_so_suc_khoe`, `di_ung`, `hoat_chat`
- **Task:** T5.1

### KTV12 · Chat trực tiếp với dược sĩ
- **Thực hiện:** Khách thành viên
- **Mô tả:** Chat thời gian thực khi AI chuyển tiếp hoặc khách chủ động yêu cầu; ngoài giờ làm việc thì tạo yêu cầu gọi lại.
- **Mã quyền:** (kiểm tra trong code)
- **Phạm vi / điều kiện:** Chỉ dữ liệu của chính mình: khach_hang_id lấy từ token, không nhận từ client.
- **Bảng:** `hoi_thoai`, `tin_nhan`
- **Task:** T7.4

### KTV13 · Nhận thông báo
- **Thực hiện:** Khách thành viên
- **Mô tả:** Nhận thông báo trên web và qua email, SMS về trạng thái đơn, kết quả duyệt đơn thuốc, thông báo thu hồi lô thuốc đã mua.
- **Mã quyền:** (kiểm tra trong code)
- **Phạm vi / điều kiện:** Chỉ dữ liệu của chính mình: khach_hang_id lấy từ token, không nhận từ client.
- **Bảng:** `thong_bao`
- **Task:** T6.5

### KTV14 · Nhắc mua lại
- **Thực hiện:** Khách thành viên
- **Mô tả:** Hệ thống tự nhắc khi sản phẩm dùng định kỳ sắp hết theo thời gian dự tính.
- **Mã quyền:** (kiểm tra trong code)
- **Phạm vi / điều kiện:** Chỉ dữ liệu của chính mình: khach_hang_id lấy từ token, không nhận từ client.
- **Bảng:** `thong_bao`, `san_pham`
- **Task:** T6.5

### KTV15 · Đặt câu hỏi về sản phẩm
- **Thực hiện:** Khách thành viên
- **Mô tả:** Đặt câu hỏi trên trang sản phẩm và nhận thông báo khi dược sĩ trả lời; câu hỏi và câu trả lời hiển thị công khai, dược sĩ có thể ẩn nội dung vi phạm.
- **Mã quyền:** (kiểm tra trong code)
- **Phạm vi / điều kiện:** Sửa/xóa câu hỏi của chính mình khi chưa được trả lời.
- **Bảng:** `hoi_dap`
- **Task:** T6.4

## Nhân viên (chung cho Dược sĩ, Nhân viên kho, Admin)

### NV01 · Đăng nhập, đổi mật khẩu
- **Thực hiện:** Dược sĩ, Nhân viên kho, Admin
- **Mô tả:** Đăng nhập tài khoản nội bộ do Admin cấp; bắt buộc đổi mật khẩu ở lần đăng nhập đầu tiên. Khóa tạm khi nhập sai nhiều lần; đổi mật khẩu hoặc bị khóa thì mọi phiên đăng nhập bị thu hồi.
- **Mã quyền:** `profile.self`
- **Phạm vi / điều kiện:** Tài khoản của chính mình.
- **Bảng:** `nhan_vien`, `phien_dang_nhap`
- **Task:** T1.3

### NV02 · Xem thông báo, cập nhật hồ sơ cá nhân
- **Thực hiện:** Dược sĩ, Nhân viên kho, Admin
- **Mô tả:** Nhận thông báo công việc (đơn mới, phiên chat chuyển tới, cảnh báo kho...), cập nhật thông tin cá nhân.
- **Mã quyền:** `profile.self`
- **Phạm vi / điều kiện:** Thông báo gửi cho chính mình.
- **Bảng:** `nhan_vien`, `thong_bao`
- **Task:** T1.3

## Dược sĩ bán hàng

### DS01 · Xem, lọc danh sách đơn hàng
- **Thực hiện:** Dược sĩ, Nhân viên kho (xem), Admin (xem)
- **Mô tả:** Lọc theo trạng thái, ngày đặt, phương thức thanh toán; xem chi tiết từng đơn.
- **Mã quyền:** `order.view`
- **Phạm vi / điều kiện:** Kho chỉ thấy đơn từ "Đã xác nhận" trở đi và thông tin giao hàng của khách (tên, SĐT, địa chỉ).
- **Bảng:** `don_hang`, `ct_don_hang`, `lich_su_trang_thai`
- **Task:** T4.6

### DS02 · Xác nhận đơn hàng
- **Thực hiện:** Dược sĩ
- **Mô tả:** Kiểm tra đơn ở trạng thái "Chờ xác nhận", gọi xác nhận với khách khi cần, chuyển sang "Đã xác nhận" để kho soạn hàng.
- **Mã quyền:** `order.confirm`
- **Phạm vi / điều kiện:** Đơn ở "Chờ xác nhận".
- **Bảng:** `don_hang`, `lich_su_trang_thai`
- **Task:** T4.6

### DS03 · Hủy đơn hàng
- **Thực hiện:** Dược sĩ
- **Mô tả:** Hủy đơn kèm lý do. Trước "Đang soạn hàng": hệ thống nhả hàng giữ. Từ "Đang soạn hàng" đến "Chờ lấy hàng" (hàng chưa rời kho): hàng được hoàn nhập đúng lô. Đơn đã thanh toán thì tạo giao dịch hoàn tiền chờ Admin xác nhận; thông báo cho khách.
- **Mã quyền:** `order.cancel`
- **Phạm vi / điều kiện:** Trước khi hàng rời kho; bắt buộc lý do.
- **Bảng:** `don_hang`, `phan_bo_lo`, `lo_thuoc`, `bien_dong_kho`, `thanh_toan`, `lich_su_trang_thai`
- **Task:** T4.6

### DS04 · Duyệt yêu cầu đơn thuốc
- **Thực hiện:** Dược sĩ
- **Mô tả:** Nhận yêu cầu (khóa cho một dược sĩ xử lý), xem ảnh đơn, danh sách thuốc AI gợi ý kèm độ tin cậy, tồn kho, hồ sơ dị ứng của khách. Hoàn thành checklist (thông tin người bệnh, chữ ký bác sĩ, ngày kê và hiệu lực, đơn chưa dùng, tương tác thuốc), rồi chấp nhận hoặc từ chối kèm lý do. Hệ thống cảnh báo nếu ảnh trùng đơn đã dùng. Khóa tự nhả nếu quá thời gian xử lý cấu hình (HT08). Hệ thống tự đối chiếu dị ứng và tương tác giữa các hoạt chất trong đơn (bảng tương tác hoạt chất).
- **Mã quyền:** `rx_request.review`
- **Phạm vi / điều kiện:** Chỉ yêu cầu đang khóa cho mình; xem hồ sơ sức khỏe của khách trong lúc xử lý.
- **Bảng:** `yeu_cau_don_thuoc`, `ct_yeu_cau_don_thuoc`, `ho_so_suc_khoe`, `di_ung`, `tuong_tac_hoat_chat`, `lo_thuoc`
- **Task:** T5.3

### DS05 · Tạo đơn hàng từ đơn thuốc
- **Thực hiện:** Dược sĩ
- **Mô tả:** Chọn sản phẩm, số lượng (hoặc thuốc thay thế cùng hoạt chất khi thiếu hàng), gửi link xác nhận và thanh toán cho khách (khách vãng lai nhận link có mã truy cập qua SMS); hàng được giữ đến hạn xác nhận. Đơn thuốc chỉ được đánh dấu đã sử dụng khi đơn chuyển sang "Đang soạn hàng"; nếu đơn bị hủy hoặc hết hạn trước đó thì được tạo lại đơn từ cùng yêu cầu.
- **Mã quyền:** `rx_order.create`
- **Phạm vi / điều kiện:** Từ yêu cầu mình đang xử lý.
- **Bảng:** `don_hang`, `ct_don_hang`, `phan_bo_lo`, `yeu_cau_don_thuoc`
- **Task:** T5.3

### DS06 · Tư vấn trực tiếp
- **Thực hiện:** Dược sĩ
- **Mô tả:** Nhận phiên chat do AI chuyển sang kèm bản tóm tắt hội thoại trước đó và tiếp tục tư vấn thời gian thực.
- **Mã quyền:** `chat.handle`
- **Phạm vi / điều kiện:** Phiên được chuyển cho mình; xem hồ sơ sức khỏe nếu khách đã đồng ý.
- **Bảng:** `hoi_thoai`, `tin_nhan`
- **Task:** T7.4

### DS07 · Tạo đơn hộ khách
- **Thực hiện:** Dược sĩ
- **Mô tả:** Lập đơn cho khách đặt qua điện thoại, áp dụng đầy đủ quy tắc đặt hàng như kênh online (không áp dụng cho thuốc kê đơn - phải qua DS04/DS05). Đơn COD chuyển thẳng "Đã xác nhận"; đơn thanh toán online gửi link và vào "Chờ thanh toán".
- **Mã quyền:** `order.create_phone`
- **Phạm vi / điều kiện:** Không áp dụng thuốc kê đơn.
- **Bảng:** `don_hang`, `ct_don_hang`, `phan_bo_lo`
- **Task:** T4.8

### DS08 · Bán tại quầy – POS
- **Thực hiện:** Dược sĩ
- **Mô tả:** Quét mã vạch hoặc tìm sản phẩm, chọn đơn vị (được bán lẻ theo viên); thuốc kê đơn bắt buộc lập yêu cầu đơn thuốc kênh "tại quầy" (ảnh đơn, thông tin người bệnh) trước khi thanh toán, hệ thống cảnh báo tương tác. Được bán lô cận hạn. Thanh toán tiền mặt hoặc chuyển khoản, hệ thống tự xuất kho theo FEFO, in hóa đơn, có thể gắn đơn với khách theo SĐT đã đăng ký. Đơn POS hoàn tất ngay.
- **Mã quyền:** `pos.sell`
- **Phạm vi / điều kiện:** Được bán lô cận hạn; thuốc kê đơn cần yêu cầu kênh tại quầy.
- **Bảng:** `don_hang`, `ct_don_hang`, `phan_bo_lo`, `lo_thuoc`, `bien_dong_kho`, `thanh_toan`, `yeu_cau_don_thuoc`, `tuong_tac_hoat_chat`
- **Task:** T5.4

### DS09 · Xử lý yêu cầu đổi trả
- **Thực hiện:** Dược sĩ
- **Mô tả:** Duyệt hoặc từ chối yêu cầu kèm lý do; khi duyệt, hệ thống tạo vận đơn trả hàng. Sau khi kho nhận và kiểm đạt: chọn hoàn tiền (tạo giao dịch hoàn tiền, Admin xác nhận chuyển tiền - AD17) hoặc gửi hàng thay thế (tạo đơn thay thế 0đ liên kết đơn gốc, đi luồng soạn hàng bình thường).
- **Mã quyền:** `return.review`
- **Phạm vi / điều kiện:** Không tự xác nhận chuyển tiền (AD17).
- **Bảng:** `yeu_cau_doi_tra`, `ct_yeu_cau_doi_tra`, `van_don`, `thanh_toan`, `don_hang`
- **Task:** T6.1

### DS10 · Biên soạn, duyệt nội dung chuyên môn
- **Thực hiện:** Dược sĩ, Admin (xem)
- **Mô tả:** Nhập, sửa các trường chuyên môn (chỉ định, chống chỉ định, liều tham khảo, tác dụng phụ, tương tác, đối tượng đặc biệt...). Chỉ nội dung đã duyệt mới hiển thị và được đồng bộ vào kho tri thức AI; hệ thống lưu ngày duyệt gần nhất. Duyệt bài viết sức khỏe trước khi đăng; biên soạn dữ liệu tương tác giữa các hoạt chất.
- **Mã quyền:** `content.professional.edit`, `content.approve`
- **Phạm vi / điều kiện:** Admin chỉ xem nội dung chuyên môn.
- **Bảng:** `thong_tin_chuyen_mon`, `tuong_tac_hoat_chat`, `bai_viet`
- **Task:** T2.3

### DS11 · Kiểm duyệt đánh giá, hỏi đáp
- **Thực hiện:** Dược sĩ
- **Mô tả:** Ẩn đánh giá vi phạm; trả lời và kiểm duyệt câu hỏi khách gửi trên trang sản phẩm (KTV15).
- **Mã quyền:** `review.moderate`, `qa.answer`
- **Bảng:** `danh_gia`, `hoi_dap`
- **Task:** T6.4

### DS12 · Đánh giá câu trả lời AI
- **Thực hiện:** Dược sĩ, Admin (xem)
- **Mô tả:** Xem các hội thoại bị khách hoặc hệ thống gắn cờ, đánh dấu đúng hoặc sai và ghi chú nội dung cần sửa.
- **Mã quyền:** `ai_answer.review`
- **Phạm vi / điều kiện:** Hội thoại bị gắn cờ.
- **Bảng:** `danh_gia_cau_tra_loi`, `tin_nhan`, `hoi_thoai`
- **Task:** T7.8

### DS13 · Liên hệ khách khi thu hồi lô
- **Thực hiện:** Dược sĩ, Admin (xem)
- **Mô tả:** Xem danh sách khách đã mua lô bị thu hồi (truy vết qua bảng phân bổ lô), liên hệ hướng dẫn hoàn trả và ghi nhận kết quả liên hệ.
- **Mã quyền:** `recall.contact`
- **Phạm vi / điều kiện:** Chỉ khách thuộc lệnh thu hồi đang mở.
- **Bảng:** `lenh_thu_hoi`, `ct_lenh_thu_hoi`, `phan_bo_lo`
- **Task:** T6.6

### DS14 · Báo cáo bán hàng của ca
- **Thực hiện:** Dược sĩ
- **Mô tả:** Xem doanh thu, số đơn, số đơn thuốc đã duyệt do chính mình xử lý trong khoảng thời gian (ca) đã chọn, kèm tiền mặt thu tại quầy để đối chiếu cuối ca. Không xem giá vốn, lợi nhuận.
- **Mã quyền:** `report.shift`
- **Phạm vi / điều kiện:** Số liệu do chính mình xử lý; không có giá vốn/lợi nhuận.
- **Bảng:** `don_hang`, `thanh_toan`, `yeu_cau_don_thuoc`
- **Task:** T8.1

### DS15 · Giao đơn nhận tại nhà thuốc
- **Thực hiện:** Dược sĩ
- **Mô tả:** Khách đến quầy đọc mã đơn hoặc SĐT; dược sĩ đối chiếu, thu tiền nếu chưa thanh toán, bàn giao hàng và chuyển đơn "Chờ lấy hàng" sang "Đã giao". Quá hạn nhận (cấu hình) thì hệ thống hủy đơn và hoàn nhập đúng lô.
- **Mã quyền:** `order.pickup_handover`
- **Phạm vi / điều kiện:** Đơn nhận tại nhà thuốc ở "Chờ lấy hàng".
- **Bảng:** `don_hang`, `thanh_toan`, `lich_su_trang_thai`
- **Task:** T4.8

## Nhân viên kho

### KHO01 · Quản lý nhà cung cấp
- **Thực hiện:** Nhân viên kho, Admin (xem)
- **Mô tả:** Thêm, sửa, tra cứu thông tin nhà cung cấp, ngừng giao dịch (xóa mềm).
- **Mã quyền:** `supplier.manage`
- **Phạm vi / điều kiện:** Ngừng giao dịch = xóa mềm.
- **Bảng:** `nha_cung_cap`
- **Task:** T3.1

### KHO02 · Lập phiếu nhập kho
- **Thực hiện:** Nhân viên kho, Admin (xem)
- **Mô tả:** Chọn nhà cung cấp, số hóa đơn; mỗi dòng nhập số lô, NSX, HSD, số lượng, giá nhập, hệ thống quy đổi về đơn vị cơ sở. Cảnh báo khi HSD dưới ngưỡng tối thiểu hoặc số lô trùng nhưng khác HSD; lưu phiếu thì tạo lô mới hoặc cộng vào lô cũ và tăng tồn. Cộng vào lô cũ thì giá nhập của lô được tính lại theo bình quân gia quyền. Phiếu đã lưu không sửa/xóa; sai sót xử lý bằng phiếu điều chỉnh. Mỗi dòng ghi thẻ kho.
- **Mã quyền:** `stock.import`
- **Phạm vi / điều kiện:** Phiếu đã lưu không sửa/xóa.
- **Bảng:** `phieu_nhap`, `ct_phieu_nhap`, `lo_thuoc`, `bien_dong_kho`
- **Task:** T3.1

### KHO03 · Soạn hàng, xuất kho theo đơn
- **Thực hiện:** Nhân viên kho
- **Mô tả:** Nhận đơn đã xác nhận, hệ thống gợi ý lô theo FEFO (đổi lô phải ghi lý do), in phiếu soạn hàng. Khi chuyển "Đang soạn hàng", hệ thống chốt lô, trừ tồn thật, ghi bảng phân bổ lô và thẻ kho; lô cận hạn không dùng cho đơn online.
- **Mã quyền:** `order.pick`
- **Phạm vi / điều kiện:** Đơn "Đã xác nhận"; đổi lô phải ghi lý do.
- **Bảng:** `don_hang`, `phan_bo_lo`, `lo_thuoc`, `bien_dong_kho`
- **Task:** T4.7

### KHO04 · Đóng gói, bàn giao vận chuyển
- **Thực hiện:** Nhân viên kho
- **Mô tả:** Gọi API GHN/GHTK tạo vận đơn, in nhãn, chuyển đơn sang "Chờ lấy hàng". Đơn nhận tại nhà thuốc chỉ đóng gói và chuyển "Chờ lấy hàng", không tạo vận đơn.
- **Mã quyền:** `shipment.create`
- **Bảng:** `van_don`, `don_hang`
- **Task:** T4.7

### KHO05 · Tra cứu tồn kho
- **Thực hiện:** Dược sĩ (xem), Nhân viên kho, Admin (xem)
- **Mô tả:** Xem tồn theo sản phẩm (tổng các lô đang bán) và chi tiết từng lô: số lô, HSD, số lượng tồn, số lượng giữ, số lượng biệt trữ, trạng thái.
- **Mã quyền:** `stock.view`
- **Phạm vi / điều kiện:** Dược sĩ xem tồn khả dụng, không xem giá nhập.
- **Bảng:** `lo_thuoc`, `san_pham`
- **Task:** T3.2

### KHO06 · Xem cảnh báo
- **Thực hiện:** Nhân viên kho, Admin (xem)
- **Mô tả:** Danh sách sản phẩm tồn dưới mức tối thiểu, lô cận hạn theo ngưỡng cấu hình, lô hết hạn (tự khóa bán bởi job chạy hằng ngày).
- **Mã quyền:** `stock.alert.view`
- **Bảng:** `lo_thuoc`, `san_pham`, `thong_bao`
- **Task:** T3.2

### KHO07 · Kiểm kê
- **Thực hiện:** Nhân viên kho, Admin (xem)
- **Mô tả:** Lập phiếu kiểm kê, nhập số lượng thực tế, hệ thống tự tính chênh lệch so với sổ sách.
- **Mã quyền:** `stocktake.manage`
- **Bảng:** `phieu_kiem_ke`, `ct_kiem_ke`
- **Task:** T3.3

### KHO08 · Lập phiếu điều chỉnh tồn
- **Thực hiện:** Nhân viên kho, Admin (duyệt)
- **Mô tả:** Lập phiếu từ kết quả kiểm kê; tồn chỉ thay đổi sau khi Admin duyệt.
- **Mã quyền:** `stock_adjust.create`
- **Phạm vi / điều kiện:** Người lập không tự duyệt.
- **Bảng:** `phieu_dieu_chinh`, `ct_phieu_dieu_chinh`
- **Task:** T3.3

### KHO09 · Lập phiếu hủy hàng
- **Thực hiện:** Nhân viên kho, Admin (duyệt)
- **Mô tả:** Lập phiếu cho hàng hết hạn, hư hỏng, hàng trả về (lấy từ khu bán hoặc khu biệt trữ); chờ Admin duyệt mới trừ tồn.
- **Mã quyền:** `disposal.create`
- **Phạm vi / điều kiện:** Người lập không tự duyệt.
- **Bảng:** `phieu_huy`, `ct_phieu_huy`
- **Task:** T3.4

### KHO10 · Nhận hàng trả về, hàng hoàn
- **Thực hiện:** Nhân viên kho
- **Mô tả:** Nhận hàng khách trả (đổi trả) và hàng hoàn do giao thất bại, kiểm tra và ghi kết quả. Hàng hoàn còn nguyên niêm phong, chưa qua tay khách: hoàn nhập đúng lô. Hàng khách trả hoặc hư hỏng: đưa vào khu biệt trữ (không bán), chờ hủy hoặc trả nhà cung cấp.
- **Mã quyền:** `return.receive`
- **Phạm vi / điều kiện:** Yêu cầu đổi trả đã duyệt, đơn hoàn về kho.
- **Bảng:** `yeu_cau_doi_tra`, `ct_yeu_cau_doi_tra`, `lo_thuoc`, `phan_bo_lo`, `bien_dong_kho`
- **Task:** T6.2

### KHO11 · Xuất trả nhà cung cấp
- **Thực hiện:** Nhân viên kho, Admin (duyệt)
- **Mô tả:** Lập phiếu xuất trả hàng cận hạn, lỗi hoặc thu hồi cho nhà cung cấp (từ khu bán hoặc khu biệt trữ); chờ Admin duyệt mới trừ tồn; ghi nhận khi nhà cung cấp xác nhận đã nhận.
- **Mã quyền:** `supplier_return.create`
- **Phạm vi / điều kiện:** Người lập không tự duyệt.
- **Bảng:** `phieu_xuat_tra`, `ct_phieu_xuat_tra`
- **Task:** T3.4

### KHO12 · Thực hiện thu hồi lô
- **Thực hiện:** Nhân viên kho, Admin (xem)
- **Mô tả:** Thực hiện lệnh thu hồi: lô đã bị khóa, gom hàng tồn và hàng khách gửi trả, sau đó xuất trả nhà cung cấp hoặc lập phiếu hủy.
- **Mã quyền:** `recall.execute`
- **Phạm vi / điều kiện:** Lệnh thu hồi đang mở.
- **Bảng:** `lenh_thu_hoi`, `ct_lenh_thu_hoi`, `phieu_xuat_tra`, `phieu_huy`
- **Task:** T6.6

### KHO13 · Báo cáo nhập, xuất, tồn
- **Thực hiện:** Nhân viên kho, Admin (xem)
- **Mô tả:** Thống kê nhập, xuất, tồn theo kỳ, theo sản phẩm, theo lô, tổng hợp từ thẻ kho: tồn đầu kỳ + nhập - xuất = tồn cuối kỳ.
- **Mã quyền:** `report.inventory`
- **Bảng:** `bien_dong_kho`, `lo_thuoc`
- **Task:** T3.5

### KHO14 · Xem đề xuất nhập hàng từ AI
- **Thực hiện:** Nhân viên kho, Admin (xem)
- **Mô tả:** Xem dự báo nhu cầu và số lượng đề xuất nhập dựa trên lịch sử bán. Kết quả lưu theo kỳ; đánh dấu đã xử lý khi đã lập phiếu nhập.
- **Mã quyền:** `forecast.view`
- **Bảng:** `de_xuat_nhap_hang`
- **Task:** T7.9

## Admin

### AD01 · Quản lý tài khoản nhân viên
- **Thực hiện:** Admin
- **Mô tả:** Tạo, khóa, đặt lại mật khẩu, gán vai trò (dược sĩ, nhân viên kho, admin). Không tự khóa hoặc hạ quyền chính mình; hệ thống luôn còn ít nhất một Admin hoạt động. Khóa tài khoản thì thu hồi mọi phiên đăng nhập.
- **Mã quyền:** `staff.manage`
- **Phạm vi / điều kiện:** Không tự khóa/hạ quyền chính mình; luôn còn ≥ 1 Admin.
- **Bảng:** `nhan_vien`, `vai_tro`, `phien_dang_nhap`, `nhat_ky_he_thong`
- **Task:** T1.4

### AD02 · Quản lý khách hàng
- **Thực hiện:** Admin
- **Mô tả:** Xem danh sách và lịch sử mua, khóa tài khoản vi phạm; không xem được hồ sơ sức khỏe của khách. Khóa tài khoản thì thu hồi mọi phiên đăng nhập của khách.
- **Mã quyền:** `customer.manage`
- **Phạm vi / điều kiện:** Không xem hồ sơ sức khỏe, dị ứng.
- **Bảng:** `khach_hang`, `don_hang`, `phien_dang_nhap`
- **Task:** T1.5

### AD03 · Quản lý danh mục
- **Thực hiện:** Admin
- **Mô tả:** Thêm, sửa, ẩn (xóa mềm), sắp xếp cây danh mục tối đa 3 cấp; không xóa được danh mục đang có sản phẩm.
- **Mã quyền:** `category.manage`
- **Bảng:** `danh_muc`
- **Task:** T2.1

### AD04 · Quản lý sản phẩm – thông tin thương mại
- **Thực hiện:** Admin
- **Mô tả:** Quản lý tên, ảnh, loại sản phẩm, đơn vị tính và hệ số quy đổi, giá bán theo từng đơn vị, trạng thái kinh doanh. Phần nội dung chuyên môn Admin chỉ được xem. Đánh dấu sản phẩm nổi bật và đặt giới hạn số lượng tối đa mỗi đơn.
- **Mã quyền:** `product.commercial.manage`
- **Phạm vi / điều kiện:** Không sửa nội dung chuyên môn.
- **Bảng:** `san_pham`, `don_vi_quy_doi`, `anh_san_pham`
- **Task:** T2.2

### AD05 · Quản lý hoạt chất, thương hiệu, nhà sản xuất
- **Thực hiện:** Dược sĩ (xem), Admin
- **Mô tả:** Quản lý dữ liệu dùng chung để gắn vào sản phẩm, phục vụ tìm kiếm theo hoạt chất và lọc theo dị ứng.
- **Mã quyền:** `master_data.manage`
- **Bảng:** `hoat_chat`, `thuong_hieu`, `nha_san_xuat`, `thanh_phan`
- **Task:** T2.1

### AD06 · Quản lý khuyến mãi, mã giảm giá
- **Thực hiện:** Admin
- **Mô tả:** Tạo khuyến mãi theo % hoặc số tiền, điều kiện đơn tối thiểu, giới hạn lượt dùng, thời gian hiệu lực; không áp dụng cho thuốc kê đơn.
- **Mã quyền:** `promotion.manage`
- **Phạm vi / điều kiện:** Không áp dụng cho thuốc kê đơn.
- **Bảng:** `khuyen_mai`, `khuyen_mai_pham_vi`, `ma_giam_gia`
- **Task:** T4.3

### AD07 · Quản lý banner, bài viết, chính sách, FAQ
- **Thực hiện:** Dược sĩ (duyệt), Admin
- **Mô tả:** Quản lý banner trang chủ, bài viết sức khỏe, trang chính sách và câu hỏi thường gặp; bài viết sức khỏe phải được dược sĩ duyệt (DS10) mới đăng; nội dung có thể đưa vào kho tri thức AI.
- **Mã quyền:** `cms.manage`
- **Phạm vi / điều kiện:** Bài sức khỏe cần dược sĩ duyệt.
- **Bảng:** `banner`, `bai_viet`
- **Task:** T2.6

### AD08 · Cấu hình hệ thống
- **Thực hiện:** Admin
- **Mô tả:** Thiết lập phí ship, ngưỡng cận hạn, mức tồn tối thiểu, thời hạn đổi trả, thời hạn chờ thanh toán. Thêm: giờ làm việc của dược sĩ, thời hạn khách nhận hàng tại quầy, thời gian khóa yêu cầu đơn thuốc, giới hạn lượt chat AI.
- **Mã quyền:** `config.manage`
- **Bảng:** `cau_hinh`
- **Task:** T1.6

### AD09 · Cấu hình AI
- **Thực hiện:** Admin
- **Mô tả:** Bật, tắt từng module AI; chỉnh lời nhắc hệ thống, danh sách dấu hiệu nguy hiểm, ngưỡng chuyển sang dược sĩ.
- **Mã quyền:** `ai.config`
- **Bảng:** `cau_hinh`
- **Task:** T7.1

### AD10 · Đồng bộ kho tri thức AI
- **Thực hiện:** Admin
- **Mô tả:** Tạo lại embedding khi dữ liệu thuốc đã duyệt thay đổi; giá và tồn kho không đưa vào vector mà truy vấn trực tiếp từ CSDL.
- **Mã quyền:** `ai.knowledge.sync`
- **Phạm vi / điều kiện:** Chỉ nội dung đã duyệt; không đưa giá/tồn vào vector.
- **Bảng:** `tai_lieu_tri_thuc`, `thong_tin_chuyen_mon`, `bai_viet`
- **Task:** T7.1

### AD11 · Giám sát hội thoại AI
- **Thực hiện:** Admin
- **Mô tả:** Xem, lọc hội thoại đã ẩn danh, thống kê câu hỏi phổ biến, tỉ lệ chuyển dược sĩ; xem các truy vấn tìm kiếm không có kết quả để bổ sung dữ liệu, từ đồng nghĩa.
- **Mã quyền:** `ai.monitor`
- **Phạm vi / điều kiện:** Hội thoại đã ẩn danh.
- **Bảng:** `hoi_thoai`, `tin_nhan`, `danh_gia_cau_tra_loi`, `lich_su_tim_kiem`
- **Task:** T7.8

### AD12 · Duyệt phiếu hủy, điều chỉnh tồn, xuất trả NCC
- **Thực hiện:** Admin
- **Mô tả:** Duyệt hoặc từ chối phiếu hủy, phiếu điều chỉnh tồn, phiếu xuất trả nhà cung cấp do nhân viên kho lập (người lập khác người duyệt); tồn kho chỉ cập nhật sau khi duyệt.
- **Mã quyền:** `stock_doc.approve`
- **Phạm vi / điều kiện:** Người duyệt khác người lập.
- **Bảng:** `phieu_dieu_chinh`, `phieu_huy`, `phieu_xuat_tra`, `lo_thuoc`, `bien_dong_kho`
- **Task:** T3.4

### AD13 · Khởi tạo lệnh thu hồi lô
- **Thực hiện:** Admin
- **Mô tả:** Tạo lệnh thu hồi gắn với sản phẩm và số lô khi có thông báo đình chỉ; hệ thống tự khóa lô, gỡ khỏi đơn chưa xuất kho, liệt kê đơn đã giao có lô đó và gửi thông báo cho khách. Đóng lệnh khi hoàn tất. Có thể thu hồi một lô hoặc toàn bộ các lô của sản phẩm.
- **Mã quyền:** `recall.create`
- **Bảng:** `lenh_thu_hoi`, `ct_lenh_thu_hoi`, `lo_thuoc`, `phan_bo_lo`, `thong_bao`
- **Task:** T6.6

### AD16 · Xem đơn hàng, chứng từ kho, nội dung chuyên môn
- **Thực hiện:** Admin (xem)
- **Mô tả:** Chỉ xem (không sửa) đơn hàng, phiếu nhập, xuất, kiểm kê và nội dung chuyên môn của thuốc.
- **Mã quyền:** `order.view`, `stock_doc.view`, `content.view`
- **Phạm vi / điều kiện:** Chỉ xem, không sửa.
- **Bảng:** `don_hang`, `phieu_nhap`, `phieu_kiem_ke`, `thong_tin_chuyen_mon`
- **Task:** T6.7

### AD14 · Báo cáo thống kê tổng hợp
- **Thực hiện:** Admin
- **Mô tả:** Doanh thu, lợi nhuận gộp (giá vốn tính theo lô), sản phẩm bán chạy, giá trị tồn kho, thuốc cận hạn, hiệu quả AI.
- **Mã quyền:** `report.all`
- **Bảng:** `don_hang`, `ct_don_hang`, `phan_bo_lo`, `thanh_toan`, `lo_thuoc`, `hoi_thoai`
- **Task:** T8.1

### AD15 · Xem nhật ký hệ thống
- **Thực hiện:** Admin
- **Mô tả:** Tra cứu ai thao tác gì, lúc nào, trên dữ liệu nào, giá trị cũ và giá trị mới.
- **Mã quyền:** `audit.view`
- **Bảng:** `nhat_ky_he_thong`
- **Task:** T1.6

### AD17 · Xác nhận hoàn tiền
- **Thực hiện:** Admin
- **Mô tả:** Danh sách giao dịch hoàn tiền chờ xử lý (do hủy đơn đã thanh toán hoặc đổi trả). VNPay/MoMo: gọi API hoàn tiền theo giao dịch gốc; COD/tiền mặt: chuyển khoản theo tài khoản khách cung cấp và đính kèm chứng từ. Cập nhật trạng thái thanh toán của đơn và thông báo cho khách.
- **Mã quyền:** `refund.confirm`
- **Phạm vi / điều kiện:** Người xác nhận khác dược sĩ duyệt đổi trả.
- **Bảng:** `thanh_toan`, `don_hang`, `yeu_cau_doi_tra`
- **Task:** T6.3

### AD18 · Quản lý vai trò & phân quyền
- **Thực hiện:** Admin
- **Mô tả:** Xem danh sách quyền, gán hoặc bỏ quyền cho vai trò Dược sĩ, Nhân viên kho; không được bỏ quyền quản trị của vai trò Admin. Mọi thay đổi ghi nhật ký hệ thống.
- **Mã quyền:** `role.manage`
- **Phạm vi / điều kiện:** Không bỏ quyền của vai trò ADMIN.
- **Bảng:** `vai_tro`, `quyen`, `vai_tro_quyen`
- **Task:** T1.4

## Hệ thống - tác vụ tự động (không phải tác nhân)

### HT01 · Cập nhật trạng thái lô hằng ngày
- **Thực hiện:** Hệ thống (tài khoản dịch vụ)
- **Mô tả:** Job hằng ngày: lô có HSD còn dưới ngưỡng chuyển "Cận hạn" (ngừng bán online), lô hết HSD chuyển "Hết hạn" (khóa bán); gỡ lô hết hạn khỏi các đơn chưa xuất kho và phân bổ lại theo FEFO.
- **Mã quyền:** (tài khoản dịch vụ)
- **Bảng:** `lo_thuoc`, `phan_bo_lo`
- **Task:** T3.2

### HT02 · Cảnh báo tồn thấp, cận hạn
- **Thực hiện:** Hệ thống (tài khoản dịch vụ)
- **Mô tả:** Gửi thông báo cho nhân viên kho khi tồn khả dụng dưới mức tối thiểu, có lô cận hạn hoặc hết hạn.
- **Mã quyền:** (tài khoản dịch vụ)
- **Bảng:** `lo_thuoc`, `san_pham`, `thong_bao`
- **Task:** T3.2

### HT03 · Hủy đơn quá hạn
- **Thực hiện:** Hệ thống (tài khoản dịch vụ)
- **Mô tả:** Hủy đơn "Chờ thanh toán" quá hạn thanh toán và đơn "Chờ khách xác nhận" quá hạn xác nhận; nhả hàng giữ, trả lượt mã giảm giá.
- **Mã quyền:** (tài khoản dịch vụ)
- **Bảng:** `don_hang`, `phan_bo_lo`, `lo_thuoc`, `ma_giam_gia`
- **Task:** T4.5

### HT04 · Xử lý IPN thanh toán
- **Thực hiện:** Hệ thống (tài khoản dịch vụ)
- **Mô tả:** Nhận IPN VNPay/MoMo, kiểm chữ ký, chống xử lý trùng theo mã giao dịch cổng; cập nhật giao dịch và chuyển trạng thái đơn qua HT06.
- **Mã quyền:** (tài khoản dịch vụ)
- **Phạm vi / điều kiện:** Xác thực chữ ký cổng thanh toán.
- **Bảng:** `thanh_toan`, `don_hang`
- **Task:** T4.5

### HT05 · Nhận webhook vận chuyển
- **Thực hiện:** Hệ thống (tài khoản dịch vụ)
- **Mô tả:** Nhận trạng thái từ GHN/GHTK (đã lấy, đang giao, đã giao, giao thất bại, hoàn hàng) và ghi lịch sử; đơn COD giao thành công thì ghi nhận đã thu tiền.
- **Mã quyền:** (tài khoản dịch vụ)
- **Phạm vi / điều kiện:** Xác thực token webhook.
- **Bảng:** `van_don`, `don_hang`, `thanh_toan`
- **Task:** T4.7

### HT06 · Máy trạng thái đơn hàng
- **Thực hiện:** Hệ thống (tài khoản dịch vụ)
- **Mô tả:** Service duy nhất được đổi trạng thái đơn: kiểm tra chuyển trạng thái hợp lệ (sheet Luồng nghiệp vụ) và quyền người thực hiện; ghi lịch sử trạng thái cùng các tác động kho, thanh toán trong một transaction.
- **Mã quyền:** (tài khoản dịch vụ)
- **Bảng:** `don_hang`, `lich_su_trang_thai`
- **Task:** T4.2

### HT07 · Gửi thông báo, nhắc mua lại
- **Thực hiện:** Hệ thống (tài khoản dịch vụ)
- **Mô tả:** Gửi thông báo web/email/SMS theo sự kiện; job hằng ngày tính ngày dự kiến hết thuốc từ số lượng đã mua để nhắc mua lại (KTV14).
- **Mã quyền:** (tài khoản dịch vụ)
- **Bảng:** `thong_bao`, `ct_don_hang`, `san_pham`
- **Task:** T6.5

### HT08 · Tự hoàn tất đơn, nhả khóa
- **Thực hiện:** Hệ thống (tài khoản dịch vụ)
- **Mô tả:** Chuyển đơn "Đã giao" sang "Hoàn tất" khi hết thời hạn đổi trả và không còn yêu cầu đổi trả mở; nhả khóa yêu cầu đơn thuốc quá thời gian; hủy đơn nhận tại quầy quá hạn; đóng phiên chat không hoạt động.
- **Mã quyền:** (tài khoản dịch vụ)
- **Bảng:** `don_hang`, `yeu_cau_don_thuoc`, `yeu_cau_doi_tra`, `hoi_thoai`
- **Task:** T4.9

## Module AI (dùng chung, gắn vào các chức năng)

### AI01 · Tìm kiếm thông minh
- **Thực hiện:** Hệ thống (tài khoản dịch vụ)
- **Mô tả:** Kết hợp tìm từ khóa (unaccent + pg_trgm) và tìm ngữ nghĩa (pgvector); xếp hạng ưu tiên còn hàng, bán chạy; lỗi AI thì chỉ dùng từ khóa. Phục vụ KVL04.
- **Mã quyền:** (tài khoản dịch vụ)
- **Bảng:** `san_pham`, `tai_lieu_tri_thuc`, `lich_su_tim_kiem`
- **Task:** T7.2

### AI02 · Phân loại ý định, phát hiện dấu hiệu nguy hiểm
- **Thực hiện:** Hệ thống (tài khoản dịch vụ)
- **Mô tả:** Phân loại câu hỏi (sản phẩm, cách dùng, triệu chứng, chính sách, cần dược sĩ...) và phát hiện dấu hiệu nguy hiểm theo danh sách cấu hình để dừng tư vấn, khuyên đi khám hoặc gọi 115. Phục vụ KVL05.
- **Mã quyền:** (tài khoản dịch vụ)
- **Bảng:** `tin_nhan`, `cau_hinh`
- **Task:** T7.3

### AI03 · Trả lời bằng RAG
- **Thực hiện:** Hệ thống (tài khoản dịch vụ)
- **Mô tả:** Truy xuất kho tri thức đã duyệt; giá và tồn lấy trực tiếp từ CSDL; không gợi ý thuốc kê đơn, không đưa liều cá nhân hóa; lọc theo dị ứng và tương tác khi khách có hồ sơ sức khỏe và đã đồng ý. Phục vụ KVL05.
- **Mã quyền:** (tài khoản dịch vụ)
- **Phạm vi / điều kiện:** Chỉ đọc hồ sơ sức khỏe khi khách đã đồng ý.
- **Bảng:** `tai_lieu_tri_thuc`, `tin_nhan`, `ho_so_suc_khoe`, `di_ung`, `tuong_tac_hoat_chat`
- **Task:** T7.3

### AI04 · Tóm tắt, chuyển dược sĩ
- **Thực hiện:** Hệ thống (tài khoản dịch vụ)
- **Mô tả:** Khi vượt ngưỡng không chắc chắn, phát hiện dấu hiệu nguy hiểm hoặc khách yêu cầu: tóm tắt hội thoại và đưa vào hàng chờ dược sĩ (KTV12, DS06); ngoài giờ thì tạo yêu cầu gọi lại.
- **Mã quyền:** (tài khoản dịch vụ)
- **Bảng:** `hoi_thoai`, `tin_nhan`
- **Task:** T7.4

### AI05 · Nhận diện hộp thuốc từ ảnh
- **Thực hiện:** Hệ thống (tài khoản dịch vụ)
- **Mô tả:** Đọc tên, hoạt chất, hàm lượng, số đăng ký từ ảnh và đối chiếu sản phẩm theo số đăng ký (KVL06).
- **Mã quyền:** (tài khoản dịch vụ)
- **Bảng:** `san_pham`
- **Task:** T7.5

### AI06 · Đọc ảnh đơn thuốc
- **Thực hiện:** Hệ thống (tài khoản dịch vụ)
- **Mô tả:** Trích danh sách thuốc, hàm lượng, số lượng kê kèm độ tin cậy và gợi ý khớp sản phẩm; chỉ để dược sĩ tham khảo (DS04).
- **Mã quyền:** (tài khoản dịch vụ)
- **Bảng:** `yeu_cau_don_thuoc`, `ct_yeu_cau_don_thuoc`
- **Task:** T7.6

### AI07 · Gợi ý sản phẩm tương tự, dành cho bạn
- **Thực hiện:** Hệ thống (tài khoản dịch vụ)
- **Mô tả:** Gợi ý theo hoạt chất, danh mục, lịch sử xem; loại bỏ thuốc kê đơn và sản phẩm chứa hoạt chất khách dị ứng (KVL03, trang chủ).
- **Mã quyền:** (tài khoản dịch vụ)
- **Bảng:** `san_pham`, `thanh_phan`, `lich_su_xem`, `di_ung`
- **Task:** T7.7

### AI08 · Gợi ý mua kèm
- **Thực hiện:** Hệ thống (tài khoản dịch vụ)
- **Mô tả:** Job định kỳ tính luật kết hợp (support, confidence, lift) từ chi tiết đơn hàng (KVL07).
- **Mã quyền:** (tài khoản dịch vụ)
- **Bảng:** `luat_mua_kem`, `ct_don_hang`
- **Task:** T7.7

### AI09 · Dự báo nhu cầu, đề xuất nhập hàng
- **Thực hiện:** Hệ thống (tài khoản dịch vụ)
- **Mô tả:** Job định kỳ dự báo nhu cầu theo lịch sử bán và tính số lượng đề xuất nhập (KHO14).
- **Mã quyền:** (tài khoản dịch vụ)
- **Bảng:** `de_xuat_nhap_hang`, `ct_don_hang`, `lo_thuoc`
- **Task:** T7.9

# Hướng dẫn demo cho giảng viên

Tài liệu này đi từng kịch bản để kiểm tra các chức năng chính của hệ thống. Điều kiện: backend chạy ở http://localhost:8000 và giao diện ở http://localhost:5173 (xem `README.md` mục "Chạy thử nhanh").

Các kịch bản 1 đến 5 đã được kiểm chứng bằng kịch bản tự động (Playwright). Kịch bản 6 trở đi tôi soạn theo mã nguồn, chưa chạy lại từng bước trên giao diện, nên tên nút có thể lệch chút ít; nếu không thấy nút đúng tên thì chọn nút gần nghĩa nhất.

## 0. Chuẩn bị

### Tài khoản

Mật khẩu chung của tài khoản mẫu: `Mau@12345`

| Vai trò | Tên đăng nhập | Trang đăng nhập |
|---|---|---|
| Khách hàng | `0900000001` (hoặc `0900000002`) | http://localhost:5173/dang-nhap |
| Dược sĩ | `duocsi@example.com` | http://localhost:5173/nhan-vien/dang-nhap |
| Nhân viên kho | `kho@example.com` | http://localhost:5173/nhan-vien/dang-nhap |
| Admin | `admin@example.com` + mật khẩu `ADMIN_MAT_KHAU` đã đặt trong `backend\.env` | http://localhost:5173/nhan-vien/dang-nhap |

Lần đầu đăng nhập Admin, hệ thống bắt đổi mật khẩu. Đổi xong dùng mật khẩu mới.

### Mở nhiều người dùng cùng lúc

Mỗi vai trò cần một phiên đăng nhập riêng. Cách đơn giản:
- **Chrome thường**: khách hàng.
- **Chrome ẩn danh** (Ctrl+Shift+N): dược sĩ.
- **Edge** (hoặc Firefox): nhân viên kho.
- **Admin**: đăng xuất người đang dùng rồi đăng nhập Admin (hoặc dùng thêm một trình duyệt khác).

Hai cửa sổ ẩn danh mở cùng lúc dùng chung phiên với nhau, nên đừng dùng hai cửa sổ ẩn danh cho hai người khác nhau.

### Các địa chỉ hữu ích

| Địa chỉ | Dùng để |
|---|---|
| http://localhost:5173 | Website |
| http://localhost:8000/docs | Tài liệu API, nơi giả lập shipper giao hàng và thử API |
| http://localhost:8025 | Hộp thư email giả (Mailpit) |

### Lấy mã OTP (khi đăng ký hoặc quên mật khẩu)

Hệ thống không gửi SMS thật. Mã OTP in ra **cửa sổ PowerShell đang chạy backend**. Tìm dòng có chữ `SMS giả` và lấy dãy 6 số trong dòng đó.

---

## Kịch bản 1. Mua hàng từ đặt hàng đến giao thành công

Mục đích: cho thấy toàn bộ vòng đời một đơn hàng COD qua 3 vai trò, có kiểm soát tồn kho theo lô.

1. **Khách** (Chrome thường): đăng nhập `0900000001`. Gõ `Paracetamol` vào ô tìm kiếm, bấm sản phẩm đầu tiên, bấm **Thêm vào giỏ**.
2. Bấm **Giỏ hàng**, rồi **Tiến hành thanh toán**, rồi **Đặt hàng** (mặc định là giao tận nơi, thanh toán khi nhận hàng). Màn hình hiện mã đơn dạng `DHxxxxxxxx`. **Ghi lại.**
3. **Dược sĩ** (ẩn danh): đăng nhập, vào **Quản lý đơn**, bấm mã đơn, bấm **Xác nhận đơn**.
4. **Kho** (Edge): đăng nhập, vào **Soạn hàng, đóng gói**, bấm đơn, bấm **Bắt đầu soạn hàng**. Bấm **Xác nhận tay** ở từng dòng. Bấm **Đóng gói & tạo vận đơn**.
5. **Khách**: **Tài khoản**, **Đơn hàng của tôi**, bấm đơn. Thấy "Chờ lấy hàng" và mã vận đơn dạng `GIA123456789`. **Ghi lại.**
6. **Giả lập shipper**: mở http://localhost:8000/docs, mở mục `POST /api/v1/webhook/gia-van-chuyen`, bấm **Try it out**, dán vào ô nội dung (đổi mã vận đơn cho đúng):
   ```json
   {"ma_van_don": "GIA123456789", "trang_thai_doi_tac": "picked"}
   ```
   bấm **Execute**. Làm lại lần nữa với `"delivered"`.
7. **Khách**: tải lại trang đơn, thấy **Đã giao** và **Đã thanh toán**, kèm dòng thời gian các trạng thái.

Điểm để nói: dược sĩ xác nhận, kho soạn theo lô gần hết hạn trước (FEFO), tiền COD chỉ ghi nhận khi giao thành công.

## Kịch bản 2. Thanh toán online (cổng giả lập VNPay và MoMo)

Giao diện mô phỏng cổng thật (có dòng cảnh báo vàng "môi trường mô phỏng, không có tiền thật"). Chi tiết ở `docs/BAT_AI_THAT.md`.

**VNPay**
1. **Khách**: thêm sản phẩm vào giỏ, vào thanh toán, chọn **VNPay**, bấm **Đặt hàng**.
2. Hộp thoại **Quét mã để thanh toán** hiện mã QR, mã đơn, số tiền và hạn thanh toán. Bấm **Mở trang thanh toán** (mở tab mới). Trang cổng VNPay hiện số tiền, mã đơn và đồng hồ đếm ngược. Chọn **Thẻ nội địa và tài khoản ngân hàng**, bấm **Tiếp tục**.
3. Nhập thẻ thử nghiệm (bảng gợi ý có ngay trên trang): số thẻ `9704198526191432198`, tên `NGUYEN VAN A`, ngày phát hành `07/15`. **Tiếp tục**.
4. Nhập OTP `123456`, bấm **Xác nhận**. Hiện "Giao dịch thành công", rồi tự quay về trang đơn: **Thanh toán thành công**.
5. Thử thất bại: dùng thẻ `9704195798459170488` (không đủ số dư) rồi OTP `123456`. Đơn vẫn chờ thanh toán, bấm **Thanh toán lại** (cũng có nút **Thanh toán** ở trang chi tiết đơn trong Đơn hàng của tôi).

**MoMo**
1. Chọn **MoMo** khi đặt hàng, bấm **Mở trang thanh toán** ở hộp thoại QR. Tab mới hiện mã QR.
2. Bấm **Mô phỏng: mở ứng dụng MoMo và quét mã**, nhập PIN `123456`, bấm **Xác nhận**.

Điểm để nói: kết quả được báo cho server bằng IPN có chữ ký (không tin trình duyệt), server kiểm tra chữ ký, số tiền và chống xử lý trùng
rồi mới đổi trạng thái đơn; quá hạn thanh toán thì job nền tự hủy đơn và nhả hàng.

## Kịch bản 3. Chatbot AI rồi chuyển sang dược sĩ

1. **Khách** (không cần đăng nhập): bấm nút tròn xanh có biểu tượng tin nhắn ở **góc dưới bên phải**.
2. Gõ một câu hỏi, ví dụ "Tôi bị đau đầu nhẹ, nên làm gì?", bấm Enter. Chatbot trả lời bằng bản giả có kịch bản sẵn.
3. Bấm **Gặp dược sĩ**.
4. **Dược sĩ**: vào **Tư vấn khách**, bấm **Nhận tư vấn**, gõ trả lời ở ô "Tin nhắn cho khách", bấm nút gửi.
5. **Khách** thấy tin nhắn của dược sĩ hiện ngay. Khách nhắn lại, dược sĩ thấy ngay.
6. Dược sĩ bấm **Kết thúc tư vấn**.

Điểm để nói: AI chỉ tư vấn tham khảo, có cảnh báo không thay thế dược sĩ, và không bao giờ gợi ý thuốc kê đơn. Muốn dùng Claude thật thì đặt `AI_GIA_LAP=false` và `ANTHROPIC_API_KEY` trong `backend\.env`.

## Kịch bản 4. Đơn thuốc kê đơn (dược sĩ duyệt)

1. **Khách**: mở một thuốc kê đơn (ví dụ tìm `Amoxicillin`). Thấy **không có nút Thêm vào giỏ**, thay bằng nút cần tư vấn từ dược sĩ.
2. Menu **Gửi đơn thuốc**: điền họ tên người bệnh, số điện thoại, chọn một ảnh bất kỳ trên máy, bấm **Gửi đơn thuốc**.
3. **Dược sĩ**: vào **Duyệt đơn thuốc**, bấm **Nhận xử lý**.
4. Bấm **Thêm thuốc**, gõ tên thuốc (ví dụ `Metformin`), hàm lượng `500mg`, số lượng `60 viên`. Bấm **Lưu danh sách thuốc**.
5. Ở ô "Tìm theo tên thuốc hoặc hoạt chất" gõ `Metformin`, bấm **Thêm**.
6. Tích hết các ô trong "Checklist trước khi tạo đơn", bấm **Tạo đơn gửi khách**.
7. **Khách**: **Tài khoản**, **Đơn hàng của tôi**, mở đơn mới ("Chờ khách xác nhận"). Chọn **Nhận tại nhà thuốc**, bấm **Xác nhận đơn**. Đơn chuyển sang **Đã xác nhận**.

Điểm để nói: thuốc kê đơn chỉ mua được qua dược sĩ, có checklist an toàn và cảnh báo tương tác/dị ứng trước khi tạo đơn.

## Kịch bản 5. Đổi trả và hoàn tiền (tách nhiệm vụ)

Cần một đơn đã **Đã giao** (làm xong kịch bản 1).

1. **Khách**: mở đơn đã giao, bấm **Yêu cầu đổi trả**. Điền số lượng trả `1`, chọn lý do (ví dụ "Giao sai sản phẩm"), tải một ảnh bất kỳ, bấm **Gửi yêu cầu**.
2. **Dược sĩ**: **Đổi trả**, hàng của yêu cầu, bấm **Xử lý**, bấm **Duyệt, tạo vận đơn trả**.
3. **Kho**: **Nhận hàng trả về**, hàng của yêu cầu, bấm **Nhận hàng**, gõ kết quả kiểm hàng (ví dụ "Đúng mô tả, hàng nguyên niêm phong"), bấm **Xác nhận đã nhận**.
4. **Dược sĩ**: **Đổi trả**, **Xử lý**, bấm **Tạo giao dịch hoàn tiền**.
5. **Khách**: mở trang chi tiết đổi trả (**Tài khoản**, mục đổi trả), nhập tài khoản ngân hàng nhận hoàn (ngân hàng, số tài khoản, chủ tài khoản).
6. **Admin**: đăng nhập, vào **Hoàn tiền**, bấm **Xác nhận** ở hàng của đơn, tải một ảnh chứng từ, bấm **Đã chuyển khoản**.
7. **Khách**: yêu cầu đổi trả hiển thị **Hoàn tất**.

Điểm để nói: người duyệt đổi trả (dược sĩ) khác người xác nhận hoàn tiền (Admin). Hệ thống chặn nếu cùng một người làm cả hai.

## Kịch bản 6. Bán tại quầy (POS)

1. **Dược sĩ**: vào **Bán tại quầy**.
2. Ở ô tìm kiếm gõ tên thuốc (ví dụ `Paracetamol`), bấm Enter, chọn đơn vị và số lượng, bấm **Thêm**.
3. Thêm vài sản phẩm. Dòng nào không cần có thể bấm **Bỏ**.
4. Chọn hình thức thu (tiền mặt hoặc chuyển khoản). Với tiền mặt nhập "Tiền khách đưa" lớn hơn tổng tiền để thấy tiền thối lại.
5. Bấm **Thanh toán và in hóa đơn**. Hóa đơn hiện ra, có thể in.
6. Thử thêm một thuốc kê đơn: hệ thống yêu cầu gắn với yêu cầu đơn thuốc đã duyệt (nút **Lập yêu cầu đơn thuốc** hoặc **Chọn ảnh đơn**).

Điểm để nói: hệ thống tự cảnh báo tương tác thuốc và dị ứng khi bán, và trừ kho theo lô gần hết hạn.

## Kịch bản 7. Quản lý kho

Đăng nhập **kho**. Các menu:
- **Tồn kho**: xem tồn theo sản phẩm và theo lô, hạn dùng, trạng thái lô (đang bán, cận hạn, hết hạn).
- **Cảnh báo kho**: danh sách lô cận hạn, hết hạn, hàng dưới mức tồn tối thiểu.
- **Nhà cung cấp** và **Nhập kho**: lập phiếu nhập hàng mới (chọn nhà cung cấp, thêm dòng sản phẩm kèm số lô, hạn dùng, số lượng, giá nhập). Sau khi lưu, tồn kho tăng và thẻ kho ghi lại.
- **Báo cáo nhập - xuất - tồn**: chọn khoảng ngày, xem tồn đầu, nhập, xuất, tồn cuối, có nút xuất Excel.
- **Kiểm kê**: tạo đợt kiểm kê, nhập số đếm thực tế.

Điểm để nói: mọi thay đổi tồn kho đều ghi thẻ kho (bảng biến động), và báo cáo nhập xuất tồn được tính hoàn toàn từ thẻ kho.

## Kịch bản 8. Duyệt phiếu kho (tách nhiệm vụ lập và duyệt)

1. **Kho**: vào **Điều chỉnh tồn**, lập phiếu điều chỉnh (chọn lô, số lượng mới, lý do). Hoặc vào **Phiếu hủy** để lập phiếu hủy hàng hết hạn.
2. Kho thử tự duyệt phiếu của chính mình: không có quyền hoặc bị từ chối.
3. **Admin**: vào **Duyệt phiếu kho**, bấm **Duyệt** (hoặc **Từ chối**) phiếu.
4. Quay lại **Tồn kho**: số lượng đã thay đổi theo phiếu được duyệt.

Điểm để nói: người lập phiếu khác người duyệt, và phiếu chỉ làm đổi tồn sau khi được duyệt.

## Kịch bản 9. Admin: báo cáo và quản trị

Đăng nhập **Admin**:
- **Tổng quan**: doanh thu, hoàn tiền, lợi nhuận gộp, số đơn hoàn tất, giá trị tồn kho, biểu đồ doanh thu theo ngày (3 tháng dữ liệu demo), sản phẩm bán chạy. Đổi khoảng ngày ở ô trên cùng. Bấm **Xuất Excel** để tải báo cáo.
- **Nhân viên**: tạo tài khoản nhân viên mới, khóa hoặc mở khóa, đặt lại mật khẩu.
- **Vai trò và phân quyền**: bảng quyền của từng vai trò, có thể thay đổi.
- **Khách hàng**: danh sách khách, lịch sử mua. Lưu ý Admin không đọc được hồ sơ sức khỏe của khách.
- **Sản phẩm**, **Danh mục**, **Khuyến mãi**, **Nội dung website**: quản lý hàng hóa, mã giảm giá, banner, bài viết.
- **Cấu hình**: các tham số hệ thống như số lần đăng nhập sai tối đa, thời hạn đổi trả.
- **Nhật ký hệ thống**: ai đã làm gì, lúc nào. Nhật ký không thể sửa hoặc xóa (cả ở mức cơ sở dữ liệu).

## Kịch bản 10. Phân quyền theo vai trò

1. Đăng nhập **dược sĩ**, rồi gõ thẳng http://localhost:5173/quan-tri vào thanh địa chỉ. Hệ thống chặn (không có quyền).
2. So sánh menu bên trái của dược sĩ, kho và Admin: mỗi vai trò chỉ thấy chức năng của mình.
3. Dược sĩ vào **Nhật ký hệ thống** hoặc **Nhân viên** qua đường dẫn trực tiếp cũng bị chặn.

Điểm để nói: phân quyền được kiểm tra ở backend (không chỉ ẩn nút ở giao diện), và có test tự động kiểm toàn bộ ma trận quyền.

## Kịch bản 11. Đăng ký tài khoản khách mới và OTP

1. Ở trang chủ bấm **Đăng nhập**, chọn **Đăng ký**.
2. Nhập họ tên, số điện thoại mới (ví dụ `0988123456`), mật khẩu. Bấm gửi mã OTP.
3. Mở cửa sổ PowerShell chạy backend, tìm dòng `SMS giả` và lấy mã 6 số.
4. Nhập OTP, hoàn tất đăng ký, đăng nhập bằng tài khoản mới.
5. Thử **Quên mật khẩu** với cùng số điện thoại để thấy luồng OTP đặt lại mật khẩu.

Điểm để nói: OTP có hạn 5 phút, giới hạn số lần thử, và tài khoản bị khóa tạm sau 5 lần đăng nhập sai.

## Kịch bản 12. Tra cứu thuốc bằng ảnh và hồ sơ sức khỏe

- **Tra cứu bằng ảnh**: bấm biểu tượng **camera** cạnh ô tìm kiếm trên đầu trang, tải một ảnh bất kỳ. Bản giả trả về kết quả mẫu. Với Claude thật, hệ thống đọc tên thuốc trên hộp rồi gợi ý sản phẩm tương ứng.
- **Hồ sơ sức khỏe** (khách đăng nhập): **Tài khoản**, **Hồ sơ sức khỏe**, nhập bệnh nền và dị ứng. Khi mua thuốc có hoạt chất gây dị ứng, hệ thống cảnh báo. Dữ liệu này được mã hóa trong cơ sở dữ liệu và Admin không đọc được.

## Chạy lại từ đầu

Nếu dữ liệu bị lộn xộn sau nhiều lần thử, dừng backend (Ctrl+C) rồi chạy trong thư mục dự án:

```powershell
docker compose down -v
docker compose up -d db mailpit
cd backend
uv run alembic upgrade head
uv run python -m app.seed --demo
uv run uvicorn app.main:app --reload
```

Cách này xóa toàn bộ dữ liệu cũ và nạp lại dữ liệu demo như ban đầu. Admin sẽ lại phải đổi mật khẩu ở lần đăng nhập đầu.

## Gặp sự cố thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| Trang trắng hoặc báo "Không tải được" | Backend đã tắt. Mở lại cửa sổ PowerShell của backend |
| Báo bị khóa sau khi đăng nhập sai | Đợi 15 phút, hoặc dừng backend (Ctrl+C) rồi chạy lại để xóa khóa |
| Đăng nhập một vai trò làm vai trò kia bị đăng xuất | Hai vai trò đang dùng chung một cửa sổ trình duyệt. Dùng cửa sổ ẩn danh hoặc trình duyệt khác |
| Không thấy mã OTP | Cuộn cửa sổ backend, tìm chữ `SMS giả` |
| Đơn mới không hiện ở màn hình của người khác | Tải lại trang (F5) |

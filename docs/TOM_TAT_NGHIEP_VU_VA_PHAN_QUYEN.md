# Tóm tắt vai trò, phân quyền và nghiệp vụ

Bản tóm tắt để ôn bảo vệ. Nguồn sự thật đầy đủ: `docs/spec/03-phan-quyen.md`, `docs/spec/04-nghiep-vu.md`, `docs/spec/data/quyen.yaml`.

## 1. Ai dùng hệ thống

| Tác nhân | Loại tài khoản | Cách kiểm soát quyền |
|---|---|---|
| Khách vãng lai | Không có tài khoản | Chỉ route công khai. Giỏ hàng lưu trên trình duyệt. |
| Khách thành viên | `khach_hang` (token `aud=khach`) | Kiểm tra trong code: `khach_hang_id` lấy từ token, không bao giờ nhận từ client. Tài nguyên của người khác trả **404**. |
| Dược sĩ bán hàng (`PHARMACIST`) | `nhan_vien` (token `aud=noi_bo`) | RBAC: vai trò → quyền, mỗi quyền có mức `day_du` hoặc `chi_xem`. |
| Nhân viên kho (`WAREHOUSE`) | như trên | như trên |
| Quản trị (`ADMIN`) | như trên | như trên |
| Hệ thống (job, IPN, webhook) | Tài khoản dịch vụ | Không phải con người; xác thực bằng chữ ký hoặc token webhook. |

Token khách không dùng được ở route nội bộ và ngược lại. Trạng thái tài khoản được kiểm tra ở **mỗi request**, nên khóa tài khoản có hiệu lực ngay.

## 2. Vai trò làm gì

**Khách vãng lai:** xem trang chủ, danh mục, chi tiết sản phẩm (chỉ nội dung chuyên môn đã duyệt), tìm kiếm thông minh, chat với trợ lý AI, tra cứu thuốc bằng ảnh, giỏ hàng, gửi đơn thuốc (xác thực OTP qua SĐT), đăng ký, đăng nhập, đọc bài viết. Thuốc kê đơn vẫn hiện nhưng gắn nhãn "Cần tư vấn".

**Khách thành viên (thêm so với vãng lai):** hồ sơ và sổ địa chỉ; đặt hàng (COD, VNPay, MoMo); mã giảm giá; theo dõi, hủy đơn (trước "Đang soạn hàng"); lịch sử và mua lại; đổi trả; đánh giá (chỉ dòng đơn đã giao); hồ sơ sức khỏe (xóa được bất kỳ lúc nào); chat với dược sĩ; thông báo và nhắc mua lại; hỏi đáp sản phẩm.

**Dược sĩ:** xem, xác nhận, hủy đơn (hủy bắt buộc lý do); duyệt yêu cầu đơn thuốc và tạo đơn từ đơn thuốc; tư vấn trực tiếp; tạo đơn hộ khách qua điện thoại; bán tại quầy (POS, được bán lô cận hạn); xử lý đổi trả; biên soạn và duyệt nội dung chuyên môn; kiểm duyệt đánh giá, hỏi đáp; đánh giá câu trả lời AI bị gắn cờ; liên hệ khách khi thu hồi lô; báo cáo ca của chính mình; giao đơn nhận tại nhà thuốc. Chỉ xem tồn khả dụng, **không thấy giá nhập, giá vốn, lợi nhuận**.

**Nhân viên kho:** nhà cung cấp; lập phiếu nhập; soạn hàng và xuất kho; đóng gói, tạo vận đơn; tra cứu tồn, cảnh báo; kiểm kê; lập phiếu điều chỉnh, hủy hàng, xuất trả nhà cung cấp (đều cần Admin duyệt); nhận hàng trả về; thực hiện thu hồi lô; báo cáo nhập, xuất, tồn; xem đề xuất nhập hàng từ AI. Chỉ thấy đơn từ "Đã xác nhận" trở đi, và với khách chỉ thấy tên, SĐT, địa chỉ giao.

**Admin:** quản lý tài khoản nhân viên, khách hàng, danh mục, sản phẩm (thông tin thương mại), hoạt chất, thương hiệu, nhà sản xuất, khuyến mãi, mã giảm giá, banner, bài viết, chính sách, FAQ; cấu hình hệ thống và AI; đồng bộ kho tri thức; giám sát hội thoại AI (đã ẩn danh); duyệt phiếu kho; khởi tạo thu hồi lô; báo cáo tổng hợp; nhật ký hệ thống; **xác nhận hoàn tiền**; quản lý vai trò và phân quyền. Với đơn hàng, chứng từ kho, nội dung chuyên môn thì **chỉ xem**.

## 3. Phân quyền chi tiết (51 mã quyền, 69 cặp vai trò – quyền)

`D` = đầy đủ (được thao tác), `X` = chỉ xem. Mọi thao tác ghi (POST, PUT, PATCH, DELETE) đều cần `D`, kể cả khi route khai nhầm mức xem.

| Nhóm | Mã quyền | Dược sĩ | Kho | Admin |
|---|---|:-:|:-:|:-:|
| Chung | `profile.self` | D | D | D |
| Đơn hàng | `order.view` | D | X | X |
| | `order.confirm`, `order.cancel`, `order.create_phone`, `order.pickup_handover` | D | | |
| | `order.pick`, `shipment.create` | | D | |
| Đơn thuốc, tư vấn | `rx_request.review`, `rx_order.create`, `chat.handle`, `pos.sell` | D | | |
| Đổi trả | `return.review` | D | | |
| | `return.receive` | | D | |
| | `refund.confirm` | | | D |
| Nội dung chuyên môn | `content.professional.edit`, `content.approve` | D | | X |
| Kiểm duyệt | `review.moderate`, `qa.answer` | D | | |
| AI | `ai_answer.review` | D | | X |
| | `ai.config`, `ai.knowledge.sync`, `ai.monitor` | | | D |
| Thu hồi lô | `recall.contact` | D | | X |
| | `recall.execute` | | D | X |
| | `recall.create` | | | D |
| Báo cáo | `report.shift` | D | | |
| | `report.inventory`, `forecast.view` | | D | X |
| | `report.all` | | | D |
| Kho | `supplier.manage`, `stock.import`, `stock.alert.view`, `stocktake.manage` | | D | X |
| | `stock.view` | X | D | X |
| | `stock_adjust.create`, `disposal.create`, `supplier_return.create` | | D | |
| | `stock_doc.approve` (duyệt phiếu) | | | D |
| | `stock_doc.view`, `content.view` | | | X |
| Danh mục, thương mại | `category.manage`, `product.commercial.manage`, `promotion.manage`, `cms.manage` | | | D |
| | `master_data.manage` | X | | D |
| Quản trị | `staff.manage`, `customer.manage`, `config.manage`, `audit.view`, `role.manage` | | | D |

18 quyền chỉ ADMIN giữ (ví dụ `staff.manage`, `role.manage`, `refund.confirm`) và Admin không gán được cho vai trò khác, để không ai tự cấp quyền cho mình. Vai trò ADMIN là bất biến (không bỏ được quyền của nó). Đổi quyền dùng khóa lạc quan `phien_ban`, trang cũ lưu đè sẽ nhận 409.

## 4. Tách nhiệm vụ và dữ liệu nhạy cảm

| Quy tắc | Cách thực thi |
|---|---|
| Phiếu điều chỉnh, hủy, xuất trả: người duyệt khác người lập | CHECK trong DB và lỗi `TU_DUYET_KHONG_DUOC` |
| Hoàn tiền: Admin xác nhận khác dược sĩ đã duyệt đổi trả | Dược sĩ duyệt, Admin chuyển tiền; service còn kiểm lại |
| Admin không sửa nội dung chuyên môn; bài sức khỏe phải dược sĩ duyệt | Mọi hàm ghi của DS10 kiểm "người thực hiện là dược sĩ" |
| Admin không tự khóa, tự xóa, tự đổi vai trò mình; luôn còn ít nhất 1 Admin | Khóa mọi dòng Admin theo id tăng dần trong cùng câu lệnh |
| AI không thực hiện thao tác ghi nghiệp vụ | Tool của chatbot chỉ đọc |

**Hồ sơ sức khỏe và dị ứng** (dữ liệu nhạy cảm theo Nghị định 13/2023): khách toàn quyền, xóa là xóa cứng. Admin và kho **không bao giờ** đọc được (có test quét response). Dược sĩ chỉ đọc qua hàm cổng khi **đồng thời** có vai trò dược sĩ, khách đã đồng ý dùng hồ sơ, và đang xử lý đúng yêu cầu đơn thuốc hoặc phiên chat của khách đó; mỗi lần đọc ghi nhật ký (không ghi giá trị). Bệnh nền mã hóa mức ứng dụng (Fernet).

**Giá nhập, giá vốn, lợi nhuận:** chỉ kho và Admin thấy; schema trả cho dược sĩ bỏ các trường này.

## 5. Vòng đời đơn hàng (máy trạng thái, 30 dòng chuyển)

Trạng thái: Chờ khách xác nhận, Chờ thanh toán, Chờ xác nhận, Đã xác nhận, Đang soạn hàng, Chờ lấy hàng, Đang giao, Giao thất bại, Hoàn về kho, Đã giao, **Hoàn tất**, **Đã hủy** (hai trạng thái cuối). Mọi chuyển trạng thái chỉ đi qua một hàm duy nhất, ghi lịch sử, và chuyển ngoài bảng thì bị từ chối.

| Luồng | Diễn biến |
|---|---|
| Khách đặt COD | Chờ xác nhận → (dược sĩ xác nhận) Đã xác nhận |
| Khách đặt VNPay/MoMo | Chờ thanh toán → (IPN thành công) Chờ xác nhận. Quá hạn thanh toán thì job tự hủy, nhả hàng. |
| Đơn từ đơn thuốc | Chờ khách xác nhận → khách xác nhận (COD thì Đã xác nhận, online thì Chờ thanh toán). Khách vãng lai dùng link mã truy cập gửi SMS. |
| Đơn qua điện thoại | Dược sĩ tạo, COD thì Đã xác nhận ngay |
| Bán tại quầy (POS) | Vào thẳng Hoàn tất; xuất kho và thanh toán ngay |
| Giao tận nơi | Đã xác nhận → Đang soạn (kho chốt lô, trừ tồn) → Chờ lấy hàng (tạo vận đơn) → Đang giao → Đã giao (COD ghi nhận tiền) → Hoàn tất sau hết thời hạn đổi trả |
| Nhận tại nhà thuốc | Chờ lấy hàng → dược sĩ giao (thu tiền nếu chưa trả) → Đã giao; quá hạn nhận thì tự hủy và hoàn nhập |
| Giao thất bại | Giao lại hoặc hoàn về kho; kho kiểm: nguyên niêm phong thì hoàn nhập đúng lô, hư hỏng thì vào khu biệt trữ |
| Hủy | Khách hủy được trước "Đang soạn hàng"; dược sĩ hủy được khi hàng chưa rời kho (bắt buộc lý do). Đã thanh toán thì tạo hoàn tiền tự động. |

## 6. Tồn kho

- Mỗi lô có `so_luong_ton`, `so_luong_giu` (đơn đã đặt chưa xuất), `so_luong_biet_tru` (hàng khách trả, hàng hư; không bán).
- **Tồn khả dụng** = tồn trừ giữ của các lô đang bán (đơn online); POS dùng thêm lô cận hạn.
- **FEFO:** giữ lô có hạn dùng gần nhất trước, một dòng đơn có thể tách nhiều lô. Không đủ thì `HET_HANG`, cả đơn rollback.
- **Giữ hàng** khi tạo đơn (không ghi thẻ kho); **chốt lô** khi bắt đầu soạn (trừ tồn thật, ghi thẻ kho `xuat_ban`); **nhả giữ** khi hủy sớm; **hoàn nhập** đúng lô khi hủy sau xuất.
- Chỉ một module (`ton_kho.py`) được đổi số lượng: khóa lô `FOR UPDATE` theo id tăng dần, và mọi thay đổi ghi `bien_dong_kho` trong cùng transaction.
- Bất biến kiểm tự động: `0 ≤ giữ ≤ tồn`; giữ của lô bằng tổng phân bổ đang giữ; tồn bằng tổng thẻ kho; đơn từ "Đang soạn hàng" không còn phân bổ đang giữ; mỗi dòng đơn đủ phân bổ.
- **Lô:** Đang bán → Cận hạn (dưới ngưỡng, ngừng bán online, quầy vẫn bán) → Hết hạn (khóa, gỡ khỏi đơn chưa xuất, phân bổ lại FEFO). Admin có thể Khóa hoặc Thu hồi (gỡ khỏi đơn chưa xuất, liệt kê khách đã mua để dược sĩ liên hệ).
- **Phiếu điều chỉnh, hủy, xuất trả:** kho lập (chưa đổi tồn) → Admin duyệt (người duyệt khác người lập) mới đổi tồn.

## 7. Tiền

- Dùng `Decimal` và cột NUMERIC, làm tròn về đồng; cấm `float`.
- Thứ tự tính: tạm tính → chọn dòng được giảm (**thuốc kê đơn không bao giờ được giảm**) → kiểm điều kiện mã (đang hoạt động, còn lượt, lượt mỗi khách, đơn tối thiểu) → số giảm (phần trăm có trần, hoặc số tiền) → phân bổ giảm vào từng dòng, phần dư dồn dòng cuối → phí vận chuyển (miễn phí từ ngưỡng, adapter lỗi dùng phí mặc định) → tổng.
- Mã giảm giá khóa dòng khi dùng; hủy đơn thì trả lượt.
- Giá đổi giữa lúc xem và lúc đặt: server tính lại và trả `GIA_DA_THAY_DOI`.
- **Thanh toán online:** kết quả báo bằng IPN có chữ ký (không tin trình duyệt); kiểm chữ ký, số tiền, chống xử lý trùng, rồi mới đổi trạng thái.
- **Hoàn tiền:** hủy đơn đã trả → hoàn toàn bộ; trả một phần → hoàn theo dòng trả; trả toàn bộ **do lỗi nhà thuốc** → cộng thêm phí ship; gửi hàng thay thế → 0. Tổng hoàn không vượt tổng đã trả. Dược sĩ duyệt, Admin xác nhận chuyển tiền.

## 8. Thuốc kê đơn

- Không vào giỏ, không đặt online, không giảm giá, không bán qua điện thoại, AI không gợi ý. Chặn ở tầng service và SQL (không chỉ giao diện hay prompt).
- Chỉ bán qua hai đường: dược sĩ tạo đơn từ yêu cầu đơn thuốc đã duyệt, hoặc POS có yêu cầu kênh tại quầy của chính dược sĩ đó.
- Quy trình: khách gửi ảnh → AI06 đọc gợi ý → dược sĩ nhận (khóa) → checklist 5 mục (thông tin người bệnh, thông tin bác sĩ, ngày kê còn hiệu lực, đơn chưa dùng, đã kiểm tra tương tác) → cảnh báo tương tác và dị ứng (mức nghiêm trọng bắt buộc ghi chú tư vấn) → tạo đơn → khách xác nhận.
- Ảnh đơn trùng đơn đã dùng thì cảnh báo; ảnh lưu vùng riêng tư, chỉ đọc qua URL ký có hạn 10 phút.

## 9. Đổi trả

Khách gửi (đơn Đã giao, trong thời hạn, kèm ảnh hoặc video) → dược sĩ duyệt và chọn hướng (hoàn tiền hoặc gửi hàng thay thế) → kho nhận và kiểm hàng (hàng trả vào khu biệt trữ) → hoàn tiền: dược sĩ tạo giao dịch, **Admin xác nhận**; hoặc tạo đơn thay thế 0đ đi lại luồng soạn hàng. Kiểm không đạt thì từ chối kèm bằng chứng.

## 10. AI

| Mã | Chức năng | Ghi chú an toàn |
|---|---|---|
| AI01 | Tìm kiếm thông minh | Quay về tìm kiếm thường khi AI lỗi |
| AI02, AI03 | Phân loại ý định, phát hiện dấu hiệu nguy hiểm; trả lời bằng RAG | Luật nguy hiểm chạy **trước** Claude; chỉ trích tri thức đã duyệt và không phải thuốc kê đơn; chỉ dùng hồ sơ sức khỏe khi khách đồng ý |
| AI04 | Tóm tắt và chuyển dược sĩ | Ngoài giờ làm việc thì tạo yêu cầu gọi lại |
| AI05 | Nhận diện hộp thuốc từ ảnh | Ảnh bỏ EXIF; kết quả chỉ là chuỗi, khớp sản phẩm bằng SQL |
| AI06 | Đọc ảnh đơn thuốc | Chỉ gợi ý, dược sĩ quyết định từng dòng |
| AI07, AI08 | Gợi ý sản phẩm tương tự, mua kèm | Loại thuốc kê đơn, loại sản phẩm dị ứng |
| AI09 | Dự báo nhu cầu, đề xuất nhập hàng | Tính từ dữ liệu xuất kho theo tuần |

Tool của chatbot chỉ đọc, kiểm đầu vào bằng Pydantic, lấy `khach_hang_id` từ token. Giới hạn lượt theo phiên và IP; có ngân sách chi phí theo ngày.

## 11. Job nền (hệ thống)

HT01 cập nhật trạng thái lô hằng ngày; HT02 cảnh báo tồn thấp và cận hạn; HT03 hủy đơn quá hạn (mỗi phút); HT04 xử lý IPN; HT05 nhận webhook vận chuyển; HT06 máy trạng thái; HT07 thông báo và nhắc mua lại; HT08 tự hoàn tất đơn, nhả khóa yêu cầu đơn thuốc, đóng hội thoại không hoạt động. Mỗi job idempotent và có khóa chống chạy chồng.

## 12. Mã chứng từ

Đơn `DH` + 8 ký tự ngẫu nhiên; yêu cầu đơn thuốc `YC`; đổi trả `DT`; phiếu nhập, kiểm kê, điều chỉnh, hủy, xuất trả `PN`, `KK`, `DC`, `PH`, `XT` + năm + 6 số; thu hồi `TH`; nhân viên `NV` + 4 số. Mã của khách ngẫu nhiên để không đoán được thứ tự.

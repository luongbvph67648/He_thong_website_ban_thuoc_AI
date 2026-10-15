# 09. Frontend

Quy ước code ở `frontend/CLAUDE.md`. File này mô tả **trang nào, cho ai, làm gì**.

## 1. Ba khu
| Khu | Đường dẫn gốc | Người dùng | Layout |
|---|---|---|---|
| Cửa hàng | `/` | Khách vãng lai, khách thành viên | Header (logo, tìm kiếm có gợi ý, giỏ hàng, tài khoản), menu danh mục 3 cấp, footer chính sách; widget chat nổi |
| Nhân viên | `/nhan-vien` | Dược sĩ, nhân viên kho | Sider menu theo quyền, header (chuông thông báo, tài khoản) |
| Quản trị | `/quan-tri` | Admin | Như khu nhân viên, menu quản trị |

Đăng nhập nội bộ tại `/nhan-vien/dang-nhap`, dùng chung cho cả ba vai trò. Sau khi đăng nhập:
- Admin vào `/quan-tri`.
- Dược sĩ và nhân viên kho vào `/nhan-vien`.
- Đang định vào một trang nội bộ khác (đã bị chuyển tới đăng nhập) thì quay lại đúng trang đó (chỉ nhận đường dẫn nội bộ).

Trang tài khoản cá nhân `/nhan-vien/tai-khoan` (hồ sơ: họ tên, số điện thoại; đổi mật khẩu) nằm ngoài hai layout và dùng chung cho cả ba vai trò. Tài khoản còn `phai_doi_mat_khau` (lần đăng nhập đầu, hoặc Admin vừa đặt lại) bị chuyển tới đây từ MỌI trang nội bộ và chỉ còn form đổi mật khẩu cho tới khi đổi xong. Header khu nội bộ có chuông thông báo (số chưa đọc, 10 thông báo mới nhất, đánh dấu đã đọc) và menu tài khoản (hồ sơ và đổi mật khẩu, đăng xuất).

## 2. Bản đồ trang
### 2.1 Cửa hàng
| Đường dẫn | Trang | Chức năng |
|---|---|---|
| `/` | Trang chủ | KVL01 |
| `/danh-muc/:slug` | Danh sách theo danh mục + bộ lọc | KVL02 |
| `/san-pham/:slug` | Chi tiết sản phẩm, đánh giá, hỏi đáp | KVL03, KTV10, KTV15 |
| `/tim-kiem?q=` | Kết quả tìm kiếm | KVL04 |
| `/gio-hang` | Giỏ hàng | KVL07 |
| `/thanh-toan` | Thanh toán | KTV02, KTV03, KTV04 |
| `/thanh-toan/ket-qua` | Kết quả thanh toán (hỏi lại backend) | KTV03 |
| `/gui-don-thuoc` | Gửi đơn thuốc (vãng lai có bước OTP) | KVL08, KTV07 |
| `/xac-nhan-don/:token` | Khách vãng lai xác nhận đơn từ đơn thuốc | DS05, KTV07 |
| `/tra-cuu-anh` | Chụp ảnh tra cứu thuốc | KVL06 |
| `/bai-viet`, `/bai-viet/:slug`, `/chinh-sach/:slug`, `/hoi-dap` | Nội dung | KVL11 |
| `/dang-ky`, `/dang-nhap`, `/quen-mat-khau` | Tài khoản | KVL09, KVL10 |
| `/tai-khoan` | Hồ sơ, đổi mật khẩu, sổ địa chỉ | KTV01 |
| `/tai-khoan/don-hang`, `/tai-khoan/don-hang/:ma` | Đơn hàng, theo dõi, hủy, mua lại, đổi trả | KTV05, KTV06, KTV08, KTV09 |
| `/tai-khoan/don-thuoc` | Đơn thuốc của tôi | KTV07 |
| `/tai-khoan/suc-khoe` | Hồ sơ sức khỏe | KTV11 |
| `/tai-khoan/thong-bao` | Thông báo | KTV13, KTV14 |
| (widget) | Chat AI + chat dược sĩ | KVL05, KTV12 |

### 2.2 Nhân viên (`/nhan-vien`)
| Đường dẫn | Trang | Chức năng | Quyền |
|---|---|---|---|
| `/don-hang`, `/don-hang/:id` | Quản lý đơn | DS01, DS02, DS03 | `order.view` |
| `/don-hang/tao` | Tạo đơn hộ | DS07 | `order.create_phone` |
| `/giao-tai-quay` | Giao đơn nhận tại nhà thuốc | DS15 | `order.pickup_handover` |
| `/don-thuoc`, `/don-thuoc/:id` | Hàng chờ, duyệt đơn thuốc | DS04, DS05 | `rx_request.review` |
| `/pos` | Bán tại quầy | DS08 | `pos.sell` |
| `/tu-van` | Hàng chờ chat, cửa sổ chat | DS06 | `chat.handle` |
| `/doi-tra` | Xử lý đổi trả | DS09 | `return.review` |
| `/noi-dung-chuyen-mon`, `/tuong-tac` | Biên soạn và duyệt nội dung chuyên môn | DS10 | `content.professional.edit` |
| `/kiem-duyet` | Đánh giá, hỏi đáp | DS11 | `review.moderate` |
| `/danh-gia-ai` | Đánh giá câu trả lời AI | DS12 | `ai_answer.review` |
| `/thu-hoi` | Liên hệ khách thu hồi lô | DS13 | `recall.contact` |
| `/bao-cao-ca` | Báo cáo ca | DS14 | `report.shift` |
| `/nha-cung-cap` | Nhà cung cấp | KHO01 | `supplier.manage` |
| `/phieu-nhap`, `/phieu-nhap/tao` | Nhập kho | KHO02 | `stock.import` |
| `/soan-hang` | Soạn hàng, đóng gói | KHO03, KHO04 | `order.pick`, `shipment.create` |
| `/ton-kho`, `/canh-bao` | Tồn kho, cảnh báo | KHO05, KHO06 | `stock.view`, `stock.alert.view` |
| `/kiem-ke`, `/dieu-chinh` | Kiểm kê, điều chỉnh | KHO07, KHO08 | `stocktake.manage`, `stock_adjust.create` |
| `/phieu-huy`, `/xuat-tra` | Hủy, xuất trả | KHO09, KHO11 | `disposal.create`, `supplier_return.create` |
| `/hang-tra-ve` | Nhận hàng trả/hoàn | KHO10 | `return.receive` |
| `/thuc-hien-thu-hoi` | Thực hiện thu hồi | KHO12 | `recall.execute` |
| `/bao-cao-nxt` | Báo cáo nhập - xuất - tồn | KHO13 | `report.inventory` |
| `/de-xuat-nhap` | Đề xuất nhập từ AI | KHO14 | `forecast.view` |

### 2.3 Quản trị (`/quan-tri`)
| Đường dẫn | Chức năng | Quyền |
|---|---|---|
| `/` (dashboard) | AD14 | `report.all` |
| `/nhan-vien` | AD01 | `staff.manage` |
| `/vai-tro` | AD18 | `role.manage` |
| `/khach-hang` | AD02 | `customer.manage` |
| `/danh-muc`, `/san-pham`, `/du-lieu-chung` | AD03, AD04, AD05 | `category.manage`, `product.commercial.manage`, `master_data.manage` |
| `/khuyen-mai` | AD06 | `promotion.manage` |
| `/noi-dung` | AD07 | `cms.manage` |
| `/cau-hinh`, `/cau-hinh-ai`, `/tri-thuc-ai`, `/giam-sat-ai` | AD08, AD09, AD10, AD11 | `config.manage`, `ai.config`, `ai.knowledge.sync`, `ai.monitor` |
| `/duyet-phieu` | AD12 | `stock_doc.approve` |
| `/thu-hoi` | AD13 | `recall.create` |
| `/hoan-tien` | AD17 | `refund.confirm` |
| `/nhat-ky` | AD15 | `audit.view` |
| `/xem/don-hang`, `/xem/chung-tu-kho`, `/xem/chuyen-mon` | AD16 | `order.view`, `stock_doc.view`, `content.view` (mức xem) |

#### Trang quản lý nhân viên (`/quan-tri/nhan-vien`, AD01) và vai trò, phân quyền (`/quan-tri/vai-tro`, AD18)
- **Nhân viên:** bảng lọc theo tên/email/mã (tìm không phân biệt dấu), vai trò, trạng thái; bộ lọc và số trang nằm trên URL (`?q=&vai_tro=&trang_thai=&trang=`) nên tải lại hay chia sẻ liên kết vẫn giữ nguyên. Hàng của chính mình tắt Khóa, Đặt lại mật khẩu, Xóa kèm giải thích (backend cũng chặn). Khóa, đặt lại mật khẩu, xóa đều hỏi xác nhận; nút thao tác bọc `YeuCauQuyen` nên chỉ hiện với mức đầy đủ.
- **Mật khẩu tạm** (sau khi tạo hoặc đặt lại) hiện trong một hộp thoại chỉ đóng bằng nút "Đã ghi lại, đóng" (không đóng khi bấm ra ngoài); đóng xong là phần tử biến khỏi DOM, giao diện không giữ mật khẩu ở đâu khác và không có cách xem lại.
- **Ma trận quyền:** chọn vai trò, mỗi mã quyền một nhóm lựa chọn (Không có / Chỉ xem / Đầy đủ) gom theo nhóm; vai trò ADMIN, `profile.self` ("Không có" và "Chỉ xem" bị khóa) và quyền chỉ dành cho một vai trò hiển thị tắt kèm lý do. Bấm lưu mở hộp xác nhận liệt kê từng thay đổi (cũ → mới) trước khi gọi `PUT`.
- **Đồng bộ quyền cho phiên đang mở** (`useDongBoPhienNoiBo` trong khung nội bộ): gọi `GET /noi-bo/toi` khi cửa sổ được focus lại và mỗi 5 phút, cập nhật vai trò, quyền và cờ đổi mật khẩu vào store phiên, nên Admin đổi phân quyền thì menu của nhân viên đang đăng nhập đổi theo mà không cần đăng nhập lại. Chỉ là lớp giao diện: backend kiểm tra quyền thật ở mỗi request.

## 3. Quy tắc hiển thị nghiệp vụ
- **Thuốc kê đơn:**
  - Có nhãn đỏ "Thuốc kê đơn".
  - Không có ô số lượng hay nút "Thêm vào giỏ".
  - Có nút "Cần tư vấn từ dược sĩ" (mở gửi đơn thuốc hoặc chat).
- **Thực phẩm chức năng:** luôn kèm dòng "Thực phẩm này không phải là thuốc, không có tác dụng thay thế thuốc chữa bệnh".
- **Giá và đơn vị:** giá hiển thị theo đơn vị đang chọn. Chọn đơn vị bằng nút (Hộp | Vỉ | Viên); chỉ hiện đơn vị có `ban_online = true`.
- **Trạng thái:** đơn hàng, đơn thuốc, đổi trả, lô hiển thị bằng nhãn màu thống nhất (`lib/trangThai.ts`). Chi tiết đơn có dòng thời gian từ `lich_su_trang_thai`.
- **Thông báo lỗi:** hiện `thong_diep` từ API. Riêng `GIA_DA_THAY_DOI` hiển thị giỏ đã tính lại và yêu cầu xác nhận lại.
- **Dữ liệu nhạy cảm:** màn duyệt đơn thuốc chỉ hiện hồ sơ dị ứng khi API trả về (đã qua hàm cổng). Không lưu dữ liệu sức khỏe trong localStorage.
- **AI:**
  - Câu trả lời stream từng đoạn. Thẻ sản phẩm hiện sau sự kiện `the_san_pham`.
  - Luôn có dòng "chỉ mang tính tham khảo".
  - Sự kiện `nguy_hiem` hiện khung đỏ có nút gọi 115.

## 4. Thành phần dùng chung (`src/components`)
| Thành phần | Dùng ở |
|---|---|
| `BangLoc`: bảng Ant Design có bộ lọc đồng bộ URL query, phân trang server | Mọi danh sách nội bộ |
| `GiaTien`, `NhanTrangThai`, `DongThoiGian` | Mọi nơi |
| `TaiAnh`: upload ảnh có nén phía client (cạnh dài ≤ 1568 px) và xem trước | Sản phẩm, đơn thuốc, đổi trả, tra cứu ảnh |
| `ChonSanPham`: tìm nhanh sản phẩm + chọn đơn vị + quét mã vạch | Phiếu nhập, POS, tạo đơn hộ, DS05 |
| `YeuCauQuyen`: guard route/nút theo mã quyền và mức | Khu nội bộ |
| `WidgetChat`: SSE (AI) và WebSocket (dược sĩ) | Khu cửa hàng |
| `InPhieu`: trang in (phiếu soạn hàng, hóa đơn POS, phiếu nhập) dùng CSS `@media print` | Kho, POS |

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
| `/noi-dung-chuyen-mon`, `/noi-dung-chuyen-mon/:id`, `/tuong-tac` | Biên soạn và duyệt nội dung chuyên môn, tương tác hoạt chất | DS10 | `content.professional.edit` |
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
| `/khach-hang`, `/khach-hang/:id` | AD02 | `customer.manage` |
| `/danh-muc`, `/du-lieu-chung` | AD03, AD05 | `category.manage`, `master_data.manage` |
| `/san-pham`, `/san-pham/moi`, `/san-pham/:id` | AD04 | `product.commercial.manage` |
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
- **Khách hàng (`/quan-tri/khach-hang`, `/quan-tri/khach-hang/:id`, AD02):** bảng tìm theo tên/email/số điện thoại, lọc trạng thái, bấm tiêu đề cột để sắp xếp (`sap_xep`), tất cả nằm trên URL. Tên khách là liên kết tới chi tiết. Chi tiết có thông tin liên hệ, trạng thái, lịch sử mua phân trang (nhãn trạng thái ở `lib/trangThai.ts`, tiền `dinhDangTien`) và một dòng nhắc hồ sơ sức khỏe, dị ứng không hiển thị với quản trị viên. Khóa mở hộp thoại xác nhận có ô lý do không bắt buộc; mở khóa hỏi xác nhận; khách bị khóa tạm (`khoa_den` ở tương lai) cũng có nút Mở khóa. **Liên kết trong khu quản trị luôn giữ tiền tố `/quan-tri`** (dựng từ đường dẫn hiện tại hoặc `relative="path"`, không viết cứng `/khach-hang/...`, nếu không người dùng bị đưa ra khu cửa hàng).
- **Cấu hình (`/quan-tri/cau-hinh`, AD08):** các khóa nhóm theo chủ đề (thẻ gập), mỗi khóa một ô nhập đúng kiểu (số có đơn vị và khoảng cho phép, tiền, nhóm số, giờ làm việc) dựng từ `kieu`/`toi_thieu`/`toi_da`/`truong` của API, kèm "cập nhật bởi ... lúc ...". Chỉ khóa nào đã sửa mới có nút Lưu; lưu gửi kèm `phien_ban`, gặp `409` thì tải lại bản mới, giữ giá trị người dùng đang gõ và báo rõ.
- **Nhật ký (`/quan-tri/nhat-ky`, AD15):** bộ lọc bảng, hành động, bản ghi, nhân viên, khoảng ngày; tất cả nằm trên URL. Mỗi dòng mở rộng ra hiện giá trị cũ và mới (so từng trường, trường đổi được tô nổi bật); dòng của dữ liệu sức khỏe ghi rõ "giá trị không được lưu".
- **Danh mục (`/quan-tri/danh-muc`, AD03):** cây tối đa 3 cấp, kéo thả để sắp xếp trong cùng cha hoặc chuyển sang cha khác (gọi `PUT .../vi-tri`, hiển thị cây mới trả về). Mỗi nút có số sản phẩm trực tiếp, nhãn "Đang ẩn" khi `dang_hien_thi = false`; thao tác thêm danh mục con (tắt ở cấp 3), sửa (tên, ảnh, hiển thị), ẩn/hiện, xóa (hỏi xác nhận, hiện thông điệp `409` của máy chủ khi còn sản phẩm hoặc danh mục con). Thả không hợp lệ (quá 3 cấp, vào chính nó) bị chặn ngay trên giao diện và máy chủ vẫn kiểm tra lại.
- **Dữ liệu dùng chung (`/quan-tri/du-lieu-chung`, AD05):** ba thẻ Thương hiệu, Nhà sản xuất, Hoạt chất; mỗi thẻ là bảng có tìm kiếm, sắp xếp, phân trang trên URL, hộp thoại thêm/sửa, xóa có xác nhận (thương hiệu và nhà sản xuất; tắt nút khi còn sản phẩm, báo thông điệp của máy chủ khi số liệu đã cũ). Hoạt chất không có nút Xóa (QĐ-16). Cột "Số sản phẩm" cho biết bản ghi đang gắn với bao nhiêu sản phẩm.
- **Sản phẩm (`/quan-tri/san-pham`, `/san-pham/moi`, `/san-pham/:id`, AD04):** danh sách có ảnh chính, SKU, tên (liên kết tới chi tiết), loại, danh mục, thương hiệu, giá mặc định và trạng thái; tìm theo tên/SKU, lọc loại, danh mục (gồm danh mục con) và trạng thái, sắp xếp theo cột, tất cả nằm trên URL. Thêm sản phẩm là MỘT form (thông tin, đơn vị, thành phần) gửi trong một lần; ảnh tải lên được sau khi tạo. Trang sửa có bốn tab: Thông tin (chỉ gửi trường đã đổi), Đơn vị và giá, Thành phần, Ảnh (tải lên, đặt ảnh chính, đổi thứ tự, xóa); tab nào lưu bằng lời gọi riêng kèm `phien_ban` đã thấy. Chi tiết KHÔNG tự làm mới khi focus lại cửa sổ (bản đã thấy mới là bản để so xung đột); gặp `409` thì tải bản mới nhưng giữ giá trị đang gõ. Thương hiệu, nhà sản xuất, hoạt chất chọn bằng ô tìm kiếm phía máy chủ. Chọn thuốc kê đơn thì hiện cảnh báo, tắt "nổi bật" và vẫn kiểm tra lại ở máy chủ. Chỉ Admin sửa được (`day_du`); mức chỉ xem thấy dữ liệu nhưng không có nút lưu, tải ảnh, xóa.
- **Nội dung chuyên môn và tương tác (`/nhan-vien/noi-dung-chuyen-mon`, `/noi-dung-chuyen-mon/:id`, `/tuong-tac`, DS10):** danh sách sản phẩm lọc theo tình trạng (tất cả, chờ duyệt, đã có nội dung duyệt, chưa có) và tìm tên/SKU, tất cả trên URL. Trang một sản phẩm có ba tab: **Soạn bản mới** (mười ô chữ nhiều dòng và ô đường dẫn tờ hướng dẫn gốc, điền sẵn từ bản còn hiệu lực mới nhất; mỗi lần lưu là một bản nháp mới, không lưu được khi không đổi gì), **Phiên bản** (bảng số bản, trạng thái, người soạn, người duyệt; nút Duyệt cho `content.approve`, Bỏ bản nháp cho `content.professional.edit`, đều hỏi xác nhận) và **So sánh** (chọn hai bản, từng trường cũ bên trái, mới bên phải, mặc định chỉ hiện trường khác nhau). Trang không tự làm mới khi focus lại cửa sổ: `phien_ban_co_so` là số bản người soạn ĐÃ THẤY; gặp `409` thì tải lại danh sách phiên bản nhưng giữ chữ đang gõ (phiên bản là append-only nên lưu tiếp không làm mất bản của người kia). Tương tác: bảng nặng nhất trước, lọc mức độ và tìm tên hoạt chất, hộp thoại thêm/sửa (sửa thì cặp hoạt chất cố định), xóa có xác nhận; sửa gặp `409` thì lấy bản mới, giữ chữ đang gõ và báo rõ rằng lưu nữa là ghi đè. Admin chỉ xem nên không thấy nút ghi.
- **Cửa hàng: trang chủ, danh mục, chi tiết sản phẩm (`/`, `/danh-muc/:slug`, `/san-pham/:slug`, KVL01–KVL03, T2.4):** thanh danh mục 3 cấp dưới header (ẩn khi tải lỗi, không chặn trang). Trang chủ: banner chính (carousel) và phụ, danh mục gốc, khu "Sản phẩm nổi bật" và "Bán chạy" (khu rỗng thì ẩn cả khu), có `h1` ẩn về mặt thị giác. Trang danh mục: đường dẫn, danh mục con, bộ lọc (loại, thương hiệu, đối tượng, khoảng giá bấm "Áp dụng giá" mới lọc, chỉ còn hàng), sắp xếp, phân trang 12 sản phẩm; MỌI bộ lọc nằm trên URL (`loai`, `thuong_hieu` lặp, `gia_tu`, `gia_den`, `doi_tuong`, `con_hang=1`, `sap_xep`, `trang`), giá trị lạ trên URL bị bỏ qua và đổi bộ lọc đưa về trang 1. Danh mục không có hoặc đang ẩn là trang 404. Trang chi tiết: thư viện ảnh, chọn đơn vị bằng nút (chỉ đơn vị bán online; giá và "còn hàng" theo đơn vị đang chọn), các tab Thông tin, Thành phần, "Chỉ định, liều dùng" (chỉ nội dung đã duyệt, không có tên người soạn), Đánh giá (điểm trung bình tính ở trình duyệt từ tổng sao), sản phẩm tương tự. Nút "Thêm vào giỏ" của sản phẩm thường đang KHÓA cho đến khi có giỏ hàng (T4.1); thuốc kê đơn không bao giờ có nút này (chỉ "Cần tư vấn từ dược sĩ" dẫn tới `/gui-don-thuoc`). Liên kết do dữ liệu quyết định (banner, hướng dẫn sử dụng) đi qua `lib/lienKet.ts` (chỉ `/...` hoặc `http(s)://host`). Khách vãng lai gửi header `X-Ma-Phien` (`lib/maPhien.ts`, mã ngẫu nhiên trong localStorage) để ghi lịch sử xem; trang chi tiết chờ `daKhoiPhuc` rồi mới gọi API để khách đã đăng nhập không bị ghi thành vãng lai.
- **Tìm kiếm từ khóa (`/tim-kiem?q=`, KVL04, T2.5):** ô tìm kiếm ở header là `AutoComplete` (`OTimKiem.tsx`): gợi ý sau 250 ms từ 2 ký tự gõ vào (tối đa 8, sản phẩm có nhãn "Cần tư vấn" nếu kê đơn, hoạt chất có nhãn "Hoạt chất"); chọn sản phẩm mở thẳng chi tiết (`?nguon=tim_kiem`), chọn hoạt chất hoặc bấm Enter/nút tìm đi tới `/tim-kiem?q=...`; từ khóa dưới 2 ký tự không điều hướng. Trang kết quả (`TrangTimKiem.tsx`) có từ khóa và `trang` trên URL, thẻ sản phẩm như danh mục, thông báo rõ khi không có kết quả hay trang vượt số trang; chờ `daKhoiPhuc` rồi mới gọi API (lịch sử tìm kiếm ghi đúng người) và gửi `X-Ma-Phien`. Lỗi tải gợi ý bị bỏ qua, không làm hỏng ô tìm kiếm.
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
